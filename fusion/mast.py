# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Selected anonymous Zarr2/3 chunks; source metadata is frozen separately."""

from pathlib import Path
from itertools import product
import json, hashlib, math, shutil
from concurrent.futures import ThreadPoolExecutor
import numpy as np, pandas as pd, xarray as xr, zarr
from .acquisition import MAST_ROOT, LICENSE_MAST
from esae.scanner import no_symlink

ALLOWED_SIGNALS = {
    "magnetics/ip": ("time", None),
    "magnetics/b_field_pol_probe_omv_voltage": ("time_mirnov", 0),
    "amc/plasma_current": ("time", None),
}


class MastConnector:
    def __init__(self, cache):
        self.cache = cache

    def catalog(self, level=2, offline=False):
        if level not in (1, 2):
            raise ValueError("MAST level1 or2 required")
        p, record = self.cache.fetch(
            MAST_ROOT + f"fairmast-meta/l{level}_shots.parquet", offline
        )
        frame = pd.read_parquet(p)
        if not {"shot_id", "campaign", "url"} <= set(frame):
            raise ValueError("MAST shot catalog schema changed")
        return frame, record

    def select(self, count=5, offline=False):
        if not 1 <= count <= 20:
            raise ValueError("Shot sample bound1..20")
        frame, record = self.catalog(2, offline)
        selected = frame[
            (frame.campaign == "M9")
            & (frame.divertor_config == "Conventional")
            & (frame.plasma_shape == "Lower Single Null")
            & (frame.current_range == "700 kA")
        ].copy()
        selected["distance"] = (selected.shot_id - 30421).abs()
        selected = selected.sort_values(["distance", "shot_id"]).head(
            min(count + 7, 30)
        )
        cols = [
            "shot_id",
            "campaign",
            "timestamp",
            "url",
            "divertor_config",
            "plasma_shape",
            "current_range",
        ]
        rows = []
        for _, r in selected.iterrows():
            rows.append({c: (int(r[c]) if c == "shot_id" else str(r[c])) for c in cols})
        return rows, record, len(frame)

    def metadata(self, shot, level=2, offline=False):
        if (
            isinstance(shot, bool)
            or not 1000 <= int(shot) <= 999999
            or level not in (1, 2)
        ):
            raise ValueError("Invalid MAST identity")
        base = MAST_ROOT + f"level{level}/shots/{shot}.zarr/"
        path, record = self.cache.fetch(
            base + ("zarr.json" if level == 2 else ".zmetadata"), offline
        )
        obj = json.loads(path.read_text())
        if level == 2:
            if (
                obj.get("zarr_format") != 3
                or obj.get("consolidated_metadata", {}).get("kind") != "inline"
            ):
                raise ValueError("Consolidated Zarr3 metadata required")
            meta = obj["consolidated_metadata"]["metadata"]
        else:
            if obj.get("zarr_consolidated_format") != 1:
                raise ValueError("Consolidated Zarr2 metadata required")
            meta = obj["metadata"]
        return base, obj, meta, record

    def signal(self, shot, name, folder, window=(0.05, 0.35), level=2, offline=False):
        if name not in ALLOWED_SIGNALS or (level == 1) != (name.startswith("amc/")):
            raise ValueError("Known diagnostic and level required")
        a, b = map(float, window)
        if not -1 <= a < b <= 10 or b - a > 2:
            raise ValueError("Bounded diagnostic time interval required")
        base, obj, meta, record = self.metadata(shot, level, offline)
        group, variable = name.split("/")
        time_name, channel = ALLOWED_SIGNALS[name]
        entry = meta.get(name if level == 2 else name + "/.zarray")
        if not entry:
            raise ValueError("Selected diagnostic unavailable in shot")
        dims = (
            entry.get("dimension_names")
            if level == 2
            else meta[name + "/.zattrs"].get("_ARRAY_DIMENSIONS")
        )
        shape = entry["shape"]
        if not dims or time_name not in dims or len(shape) not in (1, 2):
            raise ValueError("Unsupported diagnostic dimensions")
        wanted = {name, group + "/" + time_name}
        other = [d for d in dims if d != time_name]
        if other:
            wanted.add(group + "/" + other[0])
        target = no_symlink(Path(folder) / f"level{level}-{shot}-{variable}")
        target.mkdir(parents=True, exist_ok=True)
        sources = [record]
        layouts = {}

        def layout(n):
            e = meta.get(n if level == 2 else n + "/.zarray")
            if e is None:
                raise ValueError("Diagnostic coordinate absent")
            shape = e["shape"]
            chunks = (
                e["chunk_grid"]["configuration"]["chunk_shape"]
                if level == 2
                else e["chunks"]
            )
            dtype = e["data_type"] if level == 2 else e["dtype"]
            if (
                not 1 <= len(shape) <= 2
                or any(not isinstance(x, int) or x < 1 or x > 2_000_000 for x in shape)
                or len(chunks) != len(shape)
                or math.prod(chunks) * 8 > 16_000_000
                or math.prod(shape) > 20_000_000
            ):
                raise ValueError("Array/chunk bounds exceeded")
            codecs = (
                [c["name"] for c in e.get("codecs", [])]
                if level == 2
                else [e.get("compressor", {}).get("id")]
                + [c.get("id") for c in e.get("filters") or []]
            )
            if any(
                c not in ("bytes", "zstd", "blosc", "vlen-utf8", None) for c in codecs
            ):
                raise ValueError("Unsupported safe codec")
            if dtype not in [
                "float32",
                "float64",
                "int16",
                "int32",
                "int64",
                "uint16",
                "uint32",
                "uint64",
                "string",
                "<f4",
                "<f8",
                "<i4",
                "<i8",
                "<u2",
                "|O",
            ]:
                raise ValueError("Unsupported array type")
            layouts[n] = (shape, chunks)
            return e

        subset = {}
        if level == 2:
            subset[group] = meta[group]
            for n in wanted:
                subset[n] = layout(n)
            local = dict(
                obj,
                consolidated_metadata={
                    "kind": "inline",
                    "must_understand": False,
                    "metadata": subset,
                },
            )
            (target / "zarr.json").write_text(json.dumps(local))
            for n, e in subset.items():
                dest = target / n / "zarr.json"
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(json.dumps(e))
        else:
            for n in ["", group]:
                for key in [".zgroup", ".zattrs"]:
                    k = (n + "/" if n else "") + key
                    if k in meta:
                        subset[k] = meta[k]
            for n in wanted:
                layout(n)
                for key in [".zarray", ".zattrs"]:
                    subset[n + "/" + key] = meta[n + "/" + key]
            (target / ".zmetadata").write_text(
                json.dumps({"zarr_consolidated_format": 1, "metadata": subset})
            )
            for n, e in subset.items():
                dest = target / n
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(json.dumps(e))

        def chunks(n, slices=None):
            shape, cs = layouts[n]
            ranges = []
            for i, (length, width) in enumerate(zip(shape, cs)):
                lo, hi = slices[i] if slices else (0, length)
                ranges.append(range(lo // width, (hi - 1) // width + 1))
            keys = list(product(*ranges))
            if len(keys) > 128:
                raise ValueError("Selected chunk-count bound exceeded")
            planned = [
                (
                    "c/" + ("/".join(map(str, ix)))
                    if level == 2
                    else ".".join(map(str, ix))
                )
                for ix in keys
            ]

            def obtain(key):
                return key, self.cache.fetch(base + n + "/" + key, offline)

            with ThreadPoolExecutor(max_workers=2) as pool:
                acquired = list(pool.map(obtain, planned))
            for key, (src, r) in acquired:
                sources.append(r)
                dest = target / n / key
                no_symlink(dest)
                dest.parent.mkdir(parents=True, exist_ok=True)
                if not dest.exists():
                    shutil.copyfile(src, dest)
                if self.cache.transport.file_hash(dest) != r["sha256"]:
                    raise ValueError("Mirrored chunk hash differs")

        tpath = group + "/" + time_name
        chunks(tpath)
        times = np.asarray(
            zarr.open_array(str(target / tpath), mode="r")[:], dtype=float
        )
        if (
            times.ndim != 1
            or not np.isfinite(times).all()
            or (np.diff(times) <= 0).any()
        ):
            raise ValueError(
                "Invalid/nonmonotonic time coordinate; no sorting or interpolation"
            )
        lo = int(np.searchsorted(times, a, "left"))
        hi = int(np.searchsorted(times, b, "right"))
        if hi - lo < 256:
            raise ValueError("Insufficient selected temporal samples")
        selection = [
            (lo, hi) if d == time_name else (channel, channel + 1) for d in dims
        ]
        chunks(name, selection)
        for n in wanted - {name, tpath}:
            chunks(n)
        ds = xr.open_zarr(
            str(target),
            group=group,
            consolidated=True,
            chunks="auto",
            decode_times=False,
            mask_and_scale=False,
        )
        index = {time_name: slice(lo, hi)}
        if other:
            index[other[0]] = channel
        array = ds[variable].isel(index).compute(scheduler="single-threaded")
        values = np.asarray(array.values, dtype=float)
        ts = np.asarray(array[time_name].values, dtype=float)
        attrs = dict(ds[variable].attrs)
        groupattrs = dict(ds.attrs)
        timeattrs = dict(ds[time_name].attrs)
        ds.close()
        license = groupattrs.get("license_url", LICENSE_MAST)
        if license.rstrip("/") != LICENSE_MAST.rstrip("/"):
            raise ValueError("Unexpected per-dataset license; review before analysis")
        if len(values) != hi - lo or values.ndim != 1:
            raise ValueError("Unexpected selected signal dimensions")
        result = {
            "shot_id": int(shot),
            "diagnostic": name,
            "level": level,
            "channel_index": channel,
            "channel_label": (
                str(array.coords[other[0]].item())
                if other and other[0] in array.coords
                else None
            ),
            "time_unit": timeattrs.get("units"),
            "unit": attrs.get("units"),
            "source_attributes": attrs,
            "group_attributes": groupattrs,
            "source_url": base,
            "license": license,
            "selection": {
                "requested_seconds": [a, b],
                "indices": [lo, hi],
                "samples": len(values),
                "coordinate_samples": len(times),
                "partial_chunks_only": True,
            },
            "sources": sources,
            "quantity_kind": "source_processed_experimental_diagnostic_not_direct_equilibrium_reconstruction",
            "calibration_uncertainty": None,
            "quality_label": attrs.get("quality", "Not provided at level2"),
            "time_origin": "Source-provided relative diagnostic time; no cross-shot physical phase alignment established",
        }
        return ts, values, result

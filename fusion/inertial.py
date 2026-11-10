# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Safe inventory and generic detector-frame statistics; no implosion design."""

from pathlib import Path, PurePosixPath
from collections import Counter
import stat, re, zipfile, hashlib, json, subprocess, sys
import numpy as np
from scipy import ndimage
from .signals import clean, describe
from .acquisition import STFC_ITEM, STFC_ZIP, LICENSE_STFC

MAX_EXPANDED = 200_000_000
MAX_MEMBER = 32_000_000


def inspect_archive(path):
    rows = []
    names = set()
    expanded = 0
    with zipfile.ZipFile(path) as z:
        if len(z.infolist()) > 2048:
            raise ValueError("Archive entry count limit")
        for entry in z.infolist():
            name = entry.filename
            p = PurePosixPath(name)
            mode = entry.external_attr >> 16
            if (
                p.is_absolute()
                or ".." in p.parts
                or "\\" in name
                or "\0" in name
                or ":" in name
                or name in names
                or stat.S_ISLNK(mode)
                or (stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR))
            ):
                raise ValueError("Unsafe ZIP member path/type")
            names.add(name)
            expanded += entry.file_size
            if (
                entry.flag_bits & 1
                or entry.file_size > MAX_MEMBER
                or expanded > MAX_EXPANDED
                or (
                    entry.file_size > 1_000_000
                    and entry.file_size / max(1, entry.compress_size) > 1000
                )
            ):
                raise ValueError("Unsafe ZIP expansion/encryption bound")
            diagnostic = (
                "xray_detector"
                if "SLOS-TRXI/" in name
                else (
                    "neutron_temporal"
                    if "Neutron Temporal Diagnostic/" in name
                    else (
                        "proton_spectrometer"
                        if "Wedge Range Filter/" in name
                        else (
                            "source_nuclear_report"
                            if "Nuclear Reports/" in name
                            else "dataset_documentation"
                        )
                    )
                )
            )
            selected = bool(
                re.fullmatch(
                    r"DataRepo/SLOS-TRXI/Raw Data/slos_trxi_s\d+_trxi_-1-\[phosphor\]\.hdf",
                    name,
                )
            )
            shot = re.search(r"(?:s|_|/)(109\d{3})(?:_|\.|/)", name)
            excluded = (
                "Target Specifications/" in name
                or name.endswith("Datasheet.csv")
                or diagnostic
                in ["neutron_temporal", "proton_spectrometer", "source_nuclear_report"]
            )
            rows.append(
                {
                    "file": name,
                    "format": p.suffix.lower().removeprefix(".")
                    or ("directory" if entry.is_dir() else "unknown"),
                    "bytes": entry.file_size,
                    "compressed_bytes": entry.compress_size,
                    "crc32": f"{entry.CRC:08x}",
                    "directory": entry.is_dir(),
                    "diagnostic": diagnostic,
                    "shot_id": shot.group(1) if shot else None,
                    "selected_raw_image": selected,
                    "measurement": (
                        "Raw detector frame"
                        if selected
                        else "Catalog only; not numerically analyzed"
                    ),
                    "unit": "uncalibrated raw detector units" if selected else None,
                    "calibration": "No object-plane calibration or validated uncertainty inferred",
                    "validation": "bounded archive path/type metadata checked",
                    "scope_exclusion": bool(excluded),
                    "content_executed": False,
                }
            )
    return {
        "entries": rows,
        "counts": {
            "entries": len(rows),
            "files": sum(not r["directory"] for r in rows),
            "directories": sum(r["directory"] for r in rows),
            "expanded_bytes": expanded,
            "formats": dict(Counter(r["format"] for r in rows if not r["directory"])),
            "selected_raw_hdf_files": sum(r["selected_raw_image"] for r in rows),
            "recognized_diagnostic_families": len(
                {
                    r["diagnostic"]
                    for r in rows
                    if r["diagnostic"]
                    in {"xray_detector", "neutron_temporal", "proton_spectrometer"}
                }
            ),
        },
        "limits": {
            "max_members": 2048,
            "max_expanded_bytes": MAX_EXPANDED,
            "max_member_bytes": MAX_MEMBER,
        },
        "scope": "Inventory only for reports/targets/operating metadata. Quantitative analysis limited to raw detector-frame quality and pixel-domain method robustness.",
    }


def load_hdf(path, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    from esae.runner import run_tool

    out = out.resolve()
    path = Path(path).resolve()
    r = run_tool(
        [
            sys.executable,
            str(Path(__file__).with_name("hdf_worker.py").resolve()),
            str(path),
            str(out),
        ],
        out,
        timeout=60,
        sandbox=True,
        output_limit=128000,
        read_roots=(Path(__file__).parent.resolve(),),
    )
    if r.returncode or r.error:
        raise ValueError("Bounded HDF reader failed: " + (r.error or r.stderr)[-1000:])
    metadata = json.loads((out / "metadata.json").read_text())
    names = metadata["array_parts"]
    if not 1 <= len(names) <= 64 or any(
        not re.fullmatch(r"gel_raw-\d{4}\.npy", n) for n in names
    ):
        raise ValueError("Invalid detector chunk manifest")
    parts = []
    for name in names:
        p = out / name
        if p.is_symlink() or p.stat().st_size > 4_100_000:
            raise ValueError("Detector chunk bound exceeded")
        parts.append(np.load(p, allow_pickle=False, mmap_mode="r"))
    arr = np.concatenate(parts, axis=0)
    if (
        list(arr.shape) != metadata["array_shape"]
        or str(arr.dtype) != metadata["array_dtype"]
    ):
        raise ValueError("Detector chunk shape/type mismatch")
    return arr, metadata


def roi_array(image, roi="full"):
    h, w = image.shape
    if roi == "full":
        return np.asarray(image, float), (0, 0)
    if roi == "central80":
        a = h // 10
        b = w // 10
        return np.asarray(image[a : h - a, b : w - b], float), (b, a)
    raise ValueError("Known fixed ROI required")


def image_metrics(image, border_quantile=0.5, roi="full"):
    image = np.asarray(image)
    if (
        image.ndim != 2
        or image.size > 16_000_000
        or image.size < 100
        or image.dtype.kind not in "uif"
    ):
        raise ValueError("Bounded numeric detector plane required")
    if border_quantile not in (0.25, 0.5, 0.75):
        raise ValueError("Declared background quantile required")
    values, offset = roi_array(image, roi)
    finite = np.isfinite(values)
    valid = values[finite]
    if not len(valid):
        return {"status": "inconclusive", "reason": "No finite detector pixels"}
    h, w = values.shape
    bw = max(1, min(h, w) // 10)
    mask = np.zeros_like(values, bool)
    mask[:bw] = True
    mask[-bw:] = True
    mask[:, :bw] = True
    mask[:, -bw:] = True
    edge = values[mask & finite]
    background = float(np.quantile(edge, border_quantile))
    weights = np.where(finite, np.maximum(values - background, 0), 0)
    total = weights.sum()
    column = weights.sum(axis=0)
    row = weights.sum(axis=1)
    centroid = (
        {
            "x_px": float(np.dot(np.arange(w), column) / total + offset[0]),
            "y_px": float(np.dot(np.arange(h), row) / total + offset[1]),
        }
        if total > 0
        else None
    )
    bg_mad = float(np.median(np.abs(edge - np.median(edge))))
    noise = 1.4826 * bg_mad
    signallevel = float(np.quantile(valid, 0.95) - background)
    return clean(
        {
            "status": "computed",
            "roi": roi,
            "roi_origin_px": offset,
            "shape": values.shape,
            "dtype_original": str(image.dtype),
            "pixels": values.size,
            "valid_pixels": len(valid),
            "invalid_pixels": int((~finite).sum()),
            "invalid_fraction": 1 - finite.mean(),
            "raw_intensity": describe(valid),
            "quantiles": {
                "p01": np.quantile(valid, 0.01),
                "p50": np.quantile(valid, 0.5),
                "p99": np.quantile(valid, 0.99),
            },
            "fraction_at_observed_maximum": np.mean(valid == valid.max()),
            "sensor_saturation": "Unknown without independently verified sensor limits; observed max fraction is not proof of clipping",
            "background": {
                "region": "outer10percentborder of selected fixedROI",
                "quantile": border_quantile,
                "value": background,
                "robust_noise_scale": noise,
                "pixels": len(edge),
            },
            "contrast_p95_minus_p05": np.quantile(valid, 0.95)
            - np.quantile(valid, 0.05),
            "snr_descriptor": signallevel / noise if noise > 0 else None,
            "snr_definition": "(P95 - selected border background)/(1.4826*borderMAD); descriptive detector contrast, not radiometric SNR",
            "centroid_detector_px": centroid,
            "centroid_definition": "Positive (raw-background) intensity weights over fixed detector ROI; not a physical plasma position/size reconstruction",
            "profiles": {
                "column_sum": column,
                "row_sum": row,
                "unit": "raw detector units summed along orthogonal detector pixels",
            },
            "unit": "uncalibrated raw detector units",
            "geometry_unit": "detector pixel",
            "physical_scale_conversion": False,
            "uncertainty": {
                "pixel_discretization_half_pixel": 0.5,
                "calibration_standard_uncertainty": None,
                "systematic_uncertainty": None,
                "interpretation": "Pixel-grid discretization and parameter sensitivity are not total physical measurement error",
            },
        }
    )


def analyze_image(image, identity):
    baseline = image_metrics(image)
    sensitivity = []
    for roi in ["full", "central80"]:
        for q in [0.25, 0.5, 0.75]:
            m = image_metrics(image, q, roi)
            sensitivity.append(
                {
                    "roi": roi,
                    "background_quantile": q,
                    "centroid_detector_px": m.get("centroid_detector_px"),
                    "background": m.get("background", {}).get("value"),
                    "raw_mean": m.get("raw_intensity", {}).get("mean"),
                    "valid_pixels": m.get("valid_pixels"),
                    "status": m["status"],
                }
            )
    points = [
        x["centroid_detector_px"] for x in sensitivity if x.get("centroid_detector_px")
    ]
    delta = None
    if points:
        delta = {
            "x_range_px": max(x["x_px"] for x in points)
            - min(x["x_px"] for x in points),
            "y_range_px": max(x["y_px"] for x in points)
            - min(x["y_px"] for x in points),
            "method": "All6declared background/fixedROI combinations; range is preprocessing sensitivity, not a confidence interval or physical shot-to-shot difference",
        }
    array = np.asarray(image)
    thumb = np.asarray(
        array[
            :: max(1, math_ceil(array.shape[0] / 500)),
            :: max(1, math_ceil(array.shape[1] / 500)),
        ],
        float,
    )
    result = {
        "identity": identity,
        "baseline": baseline,
        "sensitivity": sensitivity,
        "robustness": delta,
        "evidence_type": "DERIVED",
        "classification": "generic_detector_image_characterization",
        "source_array_sha256": hashlib.sha256(array.tobytes(order="C")).hexdigest(),
        "source_array_dtype": str(array.dtype),
        "source_array_shape": array.shape,
        "limits": [
            "Original HDF contains both raw gel detector values and processed PSL data; only gel_raw is analyzed.",
            "No object-plane scale, magnification, exposure response, calibration uncertainty or physical plasma parameter is inferred.",
            "No operating parameters, target specifications, implosion performance, yield, shock timing or ignition optimization are analyzed.",
            "Raw versus processed display uses explicit border subtraction/linear quantile scaling; display pixels are not new radiometric measurements.",
        ],
        "display_raw": thumb,
    }
    return clean(result)


def math_ceil(x):
    return int(np.ceil(x))

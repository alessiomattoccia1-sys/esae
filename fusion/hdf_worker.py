# SPDX-License-Identifier: Apache-2.0
"""Bounded isolated HDF4 detector reader; never executes archive content."""

import sys, json, resource
from pathlib import Path
import numpy as np
from pyhdf.SD import SD, SDC


def main():
    resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
    source = Path(sys.argv[1])
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    if (
        source.is_symlink()
        or not source.is_file()
        or source.stat().st_size > 32_000_000
        or source.read_bytes()[:4] != b"\x0e\x03\x13\x01"
    ):
        raise ValueError("Known bounded HDF4 file required")
    f = SD(str(source), SDC.READ)
    try:
        inventory = {
            k: {"dimensions": list(v[0]), "shape": list(v[1]), "type": v[2]}
            for k, v in f.datasets().items()
        }
        dataset = f.select("gel_raw")
        name, rank, shape, kind, nattrs = dataset.info()
        if (
            rank != 2
            or any(x < 1 or x > 10000 for x in shape)
            or np.prod(shape) > 16_000_000
            or kind not in [SDC.UINT16, SDC.INT16, SDC.FLOAT32, SDC.FLOAT64]
        ):
            raise ValueError("Unexpected detector array layout")
        attrs = dataset.attributes()
        kept = {
            k: (v.item() if isinstance(v, np.generic) else v)
            for k, v in attrs.items()
            if k
            in [
                "bitDepth",
                "timestamp",
                "timestamp_str",
                "instrument",
                "shotNum",
                "sourceType",
            ]
        }
        array = np.asarray(dataset.get())
        parts = []
        # Preserve the existing native-runner8MB/file bound: emit bounded row chunks.
        rows = max(1, min(512, 4_000_000 // (array.shape[1] * array.dtype.itemsize)))
        for i, a in enumerate(range(0, len(array), rows)):
            name = f"gel_raw-{i:04d}.npy"
            np.save(out / name, array[a : a + rows], allow_pickle=False)
            parts.append(name)
        (out / "metadata.json").write_text(
            json.dumps(
                {
                    "format": "HDF4",
                    "datasets": inventory,
                    "selected": "gel_raw",
                    "array_parts": parts,
                    "array_shape": list(array.shape),
                    "array_dtype": str(array.dtype),
                    "attributes": kept,
                    "pixel_scale": "Detector pixel coordinates only; no object-plane conversion",
                    "processed_PSL_dataset_used": False,
                },
                indent=2,
            )
            + "\n"
        )
    finally:
        f.end()


if __name__ == "__main__":
    main()

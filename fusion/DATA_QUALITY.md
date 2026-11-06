# Data quality

Signals: count total/finite/missing samples, duplicate and nonmonotonic timestamps, gaps, median step, maximum relative jitter, longest finite run, degeneracy and repeated extrema. Unknown sensor full-scale bounds mean repeated extrema are flags, not demonstrated saturation. Irregular or insufficient segments cannot produce a nominal spectrum.

Images: preserve raw shape/dtype and pixel-byte hash, count all finite/invalid pixels, quantify raw distribution and fraction at observed maximum. Unknown detector response and object-plane calibration stay unknown. The declared contrast/noise descriptor is not an absolute radiometric SNR.

ZIP imports reject traversal, absolute/backslash paths, symlinks, encrypted members, duplicate names, excessive expansion/count and corrupt selected payloads. Numerical readers are bounded and execute no dataset code. Dataset errors and shot exclusions are visible; invalid originals are retained, not silently deleted.

FAIR-MAST processing corrections are documented upstream; ingestion commit and timestamp identify the acquired source. Separate object GETs do not provide a transactional snapshot of the entire remote store. Frozen acquired bytes permit exact local replay but cannot prove upstream calibration correctness.


Original software © 2026 Mattoccia Labs, Apache License 2.0. Scientific data and derived artifacts retain the separate source licenses.

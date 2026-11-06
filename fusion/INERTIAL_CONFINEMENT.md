# Inertial Fusion Lab

This laboratory inventories the official STFC archive and analyzes raw detector arrays. Seven SLOS-TRXI HDF4 files contain original gel_raw and separate processed PSL datasets; v0.1 reads only gel_raw. A mandatory sandboxed helper denies network and limits CPU/time/file output, emitting validated row chunks rather than relaxing the existing 8 MB file limit.

Explore each frame, source metadata, explicit raw P01–P99 display, separately labeled positive-background-subtracted display, intensity statistics, full-frame detector centroids/profiles and all six fixed ROI/background cases. Display scaling is not a new radiometric measurement.

No object-plane magnification or calibration uncertainty is established; results remain detector pixels and raw instrument units. Neutron/proton families are recognized in the inventory, not numerically interpreted. No physical yield, temperature, pressure, areal density or target/drive/implosion optimization is implemented. ICF-03 explicitly substitutes same-measurement robustness for comparisons between different implosion performances.


Original software © 2026 Mattoccia Labs, Apache License 2.0. Scientific data and derived artifacts retain the separate source licenses.

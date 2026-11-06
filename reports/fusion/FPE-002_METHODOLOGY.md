# FPE-002 — scientific methodology

Real experimental retrospective data. Configuration:

```json
{}
```

The complete ZIP inventory is validated for traversal, absolute/backslash paths, symlinks, duplicate paths, encryption and expansion limits. Only7raw SLOS-TRXI HDF4 files are selected by a fixed filename rule; target/operating/performance files are cataloged without numerical analysis. A bounded sandboxed native reader reads only gel_raw; processed PSL is not substituted for raw measurement.

Original uint16 detector arrays remain unchanged. All finite/invalid pixels and raw statistics are counted. Detector backgrounds use outer10percent borders and quantiles25/50/75. Positive raw-minus-background weights define full-frame detector centroids and profiles in pixels. Whole-frame and fixed central80percent ROIs yield6predeclared cases per image. Their ranges measure preprocessing sensitivity, not confidence intervals or total physical uncertainty. No object-plane conversion, magnification, radiometry, yield, temperature, areal density or implosion-performance inference is performed. ICF03 explicitly uses same-measurement robustness instead of cross-implosion comparison.

Observed data, derived quantities, statistical descriptions and unverified hypotheses remain distinct. Source licenses and modifications are documented separately from original-code Apache2.0.

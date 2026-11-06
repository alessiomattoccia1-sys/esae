# Verified results

Both studies use real retrospective experimental data. Six computational findings were generated, not physical discoveries. Full source replay and independent numerical checks passed.

| Study | Coverage | Verified result fingerprint |
|---|---|---|
| FPE-001 | {"catalog_shots":11573,"selected_shots":5,"selected_diagnostic_types":2,"signals":10,"samples":757500,"valid_samples":757500,"candidate_shots_examined":5,"excluded_candidates":0,"computed_signals":10,"inconclusive_signals":0} | eda30cddda1943f19425d2b9472d4e773f62c100e298191538fee6b13330a8bd |
| FPE-002 | {"entries":74,"files":63,"directories":11,"expanded_bytes":81949600,"formats":{"txt":15,"csv":25,"hdf":7,"pdf":8,"xlsx":1,"ps":7},"selected_raw_hdf_files":7,"recognized_diagnostic_families":3,"raw_images_analyzed":7,"selected_measurements":7,"detector_pixels":28000000,"valid_detector_pixels":28000000,"source_processed_PSL_arrays_not_analyzed":7,"inconclusive_images":0} | 01e944055fa62c6996f2ba3e435043563ee897ea2f1749f61c327598f09a6ccc |

## MAST measurements

| Shot | Diagnostic | RMS / source-normalized unit | Welch peak / Hz | Half bin / Hz | Candidate events |
|---|---|---|---|---|---|
| 30421 | magnetics/ip | 592831.292 A | 19.53125 | 9.765625 | 1 |
| 30421 | magnetics/b_field_pol_probe_omv_voltage | 0.00636104405 V | 366.210937 | 61.0351562 | 0 |
| 30424 | magnetics/ip | 591866.502 A | 19.53125 | 9.765625 | 2 |
| 30424 | magnetics/b_field_pol_probe_omv_voltage | 0.00634499755 V | 244.140625 | 61.0351562 | 0 |
| 30417 | magnetics/ip | 595148.164 A | 19.53125 | 9.765625 | 5 |
| 30417 | magnetics/b_field_pol_probe_omv_voltage | 0.00652867044 V | 366.210937 | 61.0351562 | 1 |
| 30425 | magnetics/ip | 589717.858 A | 19.53125 | 9.765625 | 3 |
| 30425 | magnetics/b_field_pol_probe_omv_voltage | 0.00635386408 V | 122.070312 | 61.0351562 | 0 |
| 30426 | magnetics/ip | 591115.214 A | 19.53125 | 9.765625 | 0 |
| 30426 | magnetics/b_field_pol_probe_omv_voltage | 0.00638302136 V | 366.210937 | 61.0351562 | 0 |

Shot 30421 current mean: 584899.409 A. Conditional moving-block 95% interval [558023.614, 615017.309] A, 499 replicates, blocks of 38 samples, seed 20261106. This is variability under the stated dependence/stability assumptions; unknown calibration/systematic error is not included. Dominant low-frequency content is not a physical-mode identification.

## STFC detector measurements

| Shot | Mean raw detector value | Centroid X / px | Centroid Y / px | Six-case X range / px | Six-case Y range / px |
|---|---|---|---|---|---|
| 109090 | 1562.06412 | 1086.23926 | 790.422165 | 8.48299379 | 27.4933431 |
| 109092 | 1706.34739 | 1071.93148 | 724.150856 | 19.6623042 | 31.1869012 |
| 109093 | 1601.22468 | 999.172012 | 780.992257 | 0.865605344 | 4.96707326 |
| 109094 | 1597.88693 | 1091.70513 | 800.572108 | 5.88245498 | 19.3965333 |
| 109098 | 1593.38204 | 1082.8356 | 743.394051 | 18.0815847 | 37.7201572 |
| 109099 | 1617.09001 | 989.382716 | 783.219615 | 0.804703863 | 4.76241825 |
| 109103 | 1653.85512 | 1087.17912 | 807.320063 | 4.8279746 | 8.30158508 |

These are detector-coordinate and processing-sensitivity descriptors. No plasma dimension, physical yield, temperature or implosion-performance difference is inferred. ICF-03 explicitly substitutes same-measurement robustness for cross-implosion comparison.

## Validation and inconclusive scope

246 automated tests passed, zero failed/errors/skips. Two dependency warnings remain: the existing Starlette HTTPX deprecation and Zarr3 consolidated-metadata specification warning. 67 of the 68 frozen runtime/API/UI/shared files remained byte-identical. The sole reviewed change fixes an exited-child EPERM race in the shared native runner, preserving sandbox/resource limits and failing closed if the child remains active. Zarr2 Level1 access was separately verified on shot 30421 (1500 samples, kA normalized to A), without equating its processing to Level2.

Physical calibration/systematic uncertainties, physical-mode identification and literature-result reproduction remain not determined. Neutron/proton numeric interpretation, LLNL, PlasmaPy-based derived physical quantities and apparatus control are not implemented. All seven ICF images and ten selected magnetic signals were numerically usable.

An earlier final regression attempt hit a transient PermissionError while the pre-existing output-limit test tried to signal an exiting child. The isolated recheck passed and the full 244-test final run passed. A subsequent clean-artifact run reproduced it. The shared runner now waits at most 250 ms after EPERM and tolerates it only when child exit is confirmed. A live denial still raises. Two new controls and full regressions cover the change; all earlier failures are retained.

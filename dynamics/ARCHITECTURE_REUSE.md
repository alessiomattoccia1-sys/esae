# Architecture reuse

| Component | Classification | Intervention |
|---|---|---|
| PublicCache | Direct reuse with source policy | Official metadata/small files; independent Dynamics cache |
| Large ZIP range ingestion | New adapter | Bounded HTTP ranges, stable validators, member CRC/hash and safe paths; never silently download whole archives |
| JobStore / OperationLock | Direct reuse | Separate Dynamics SQLite registry, explicit cancellation/resume |
| API boundary | Direct reuse | Local Host/Origin/mutation guards and strict CSP |
| Optional hypothesis helper | Direct reuse/adaptation | Referenced metric subsets, numbers external to prose, no cloud |
| Dashboard base CSS / DOM/SVG/canvas | Adaptation | Seven Dynamics areas, model catalog and actual simulation playback |
| Scientific report pattern | Adaptation | Three experiments, observed/estimated/predicted/simulated distinctions |
| C/C++ / genomics / materials / finance / plasma algorithms | Specific; independent | No edits or domain-equivalence assumptions |
| State-space and stochastic models | New generic core | Units, transition/observation, estimators, covariance and probability validation |
| Simulation clock / interactions / recorder | New generic core | Abstract2D/3D agents; no aircraft-control concepts |
| Civil trajectory normalization / model benchmark | New application layer | Verified source schemas, full-flight splits, common horizons and held-out test |
| Website | Existing stack; new family | New master/engine routes, independent numbering and navigation; preserve Research Engines content |

No aircraft, radar, RF or flight-controller live connections are implemented. Real data remains historical. No operational intent labels, pursuit, interception, weapon interaction or sensor-placement optimization is part of the application.

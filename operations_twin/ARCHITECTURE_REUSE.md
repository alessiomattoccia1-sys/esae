# Architecture reuse

Creator: Codex per Alessio, 6 November 2026. PROJECT; retain until explicit retirement.

| Component | Classification | Intervention |
|---|---|---|
| Shared PublicCache | Reusable without modification | Inject strict official 4TU/conference source policy; independent cache and byte limits |
| JobStore / OperationLock | Reusable without modification | Separate Operations SQLite metadata and resumable bounded stages |
| Host/Origin/CSP API boundary | Reusable without modification | Independent loopback API; no public analysis backend |
| Local AI hypothesis helper | Reusable with selected evidence | Optional Ollama, referenced public aggregates only; no invented measures or cloud |
| Dynamics numeric clean/fingerprint | Reusable without modification | Typed Python JSON and verified public export; no JS numeric normalization |
| Dynamics Gaussian state models, flight parsers | Drone-specific | Keep unchanged; no artificial mapping of flight state to business process |
| Fixed-step simulator | Existing shared interface, no DES capability | Add generic SimPy discrete-event adapter in `dynamics/events.py`; preserve existing `simulation.py` |
| Seeded experiments/statistical validation | Reusable through minimal generic extension | Callback-based paired seeds and confidence/distribution metrics, independent of domain |
| Dashboard styling/report conventions | Adaptation | Existing typography, themes, local DOM/canvas and report lineage; business views |
| XES/CSV/JSON/Parquet ingestion | New Operations module | Streaming, safe XML, columnar batches, data-quality audit and pseudonymization |
| DFG/variants/performance | New Operations module | Original deterministic algorithms/DuckDB; no AGPL source or PM4Py dependency |
| Empirical calibration / queue models | New Operations module | Separate data-derived elapsed-time twin and hypothetical resource-capacity scenarios |
| Website family page | Adapt existing master | Add Engine02 and Operations route; preserve Drone and five Research engine content |

No database migration, API rewrite, global frontend change, app source access, ERP/CRM connection or individual employee evaluation is required.

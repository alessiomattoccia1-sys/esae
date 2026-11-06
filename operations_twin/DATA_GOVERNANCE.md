# Data governance and security

Only the public BPI2019source is used for the published experiments. Private future logs require local authorization and remain separate. Original files, normalized data, models and results are distinct. All artifacts are PROJECT/EVIDENCE retained until explicit retirement; no automatic deletion is introduced.

Public-source identifiers become HMAC tokens. Using the public dataset hash as the default key supports reproducibility; this is not a secret anonymity guarantee. Authorized private imports use a private random local key with0600permissions and drop resource IDs. Keys never enter manifests or reports. No person rankings, psychological models or financial savings are produced.

XML uses defusedxml with DTD/entities/external access prohibited, an8MiBper-trace/metadata read window,5Mevent limit,20kevents per trace, bounded attribute counts/values and1GBoriginal-file limit. CSV fields, JSON sizes, record counts and Parquet columns/batches are bounded. No input script is executed. Symlink paths are rejected. Required-field failures are counted, not silently repaired. Exact duplicate candidates remain by default because absent event IDs prevent proving they are errors.

The local API permits literal loopback hosts/origins only, validates request schemas, requires a same-origin mutation header, caps request bodies16KB and exposes only whitelisted exports. It does not offer arbitrary path reads or SQL execution. Import files must already be in the configured imports directory. No cloud uploads, browser telemetry or automatic AI model download. Ollama is explicitly configured, optional, local and references only selected aggregates.

DuckDB query memory is512MB; total process RSS is measured rather than claimed to equal this setting. Event/time/wall/record budgets and cancellation boundaries prevent unbounded simulations. Source SHA256 pins and partition checks prevent silent vintage/cache substitution. Original data remain preserved after cancellation.

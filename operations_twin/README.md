# Operations Twin Engine — v0.1

**English source distribution · v0.1.1**

A project by **Alessio Mattoccia**.

Dynamics Lab / Engine02. **Understand the Process. Model the System. Test the Change.**

A local computational laboratory for reconstructing real business event logs, testing empirical process twins on independent time periods, and simulating explicitly hypothetical capacity and service assumptions. It extends the existing Dynamics family and preserves Drone Dynamics and all five Research Engines.

## Run

Qualified on native Apple M1, macOS27, Python3.12. A hashed lock installs an isolated environment; it does not change other engines. Windows/Linux execution is not qualified in this release.

```sh
python3.12 operations_twin/setup.py
.venv-ote/bin/python -m operations_twin.cli run OTE-001 --data .local/operations-twin-data
.venv-ote/bin/python -m operations_twin.cli run OTE-002 --data .local/operations-twin-data --offline
.venv-ote/bin/python -m operations_twin.cli run OTE-003 --data .local/operations-twin-data --offline
.venv-ote/bin/python -m operations_twin.cli serve --data .local/operations-twin-data
```

Open **http://127.0.0.1:4207**. The public website uses static reports and a replay; it does not expose this API. First acquisition needs Internet and approximately1GB available disk for the original XES, compressed cache, partitions and analytical database. This is not an installer bundling AI models; Ollama is optional and no model is required for numerical research.

```sh
.venv-ote/bin/python -m operations_twin.cli reproduce OTE-002 --data .local/operations-twin-data
.venv-ote/bin/python -m operations_twin.cli what-if --cases 150 --replicates 5 --offline --data .local/operations-twin-data
.venv-ote/bin/python -m pytest operations_twin/tests -q
```

Reproduction requires the original pinned source version and cached inputs. A changed source hash or missing vintage is an error, never a silent synthetic substitution. Completed jobs and manifests persist. Interrupted imports resume at verified complete-trace partitions; interrupted simulations rerun deterministically from configuration and seed rather than serializing live Python generators.

## Implemented

Streaming safe XES, CSV, Parquet, JSON/NDJSON; UTC validation; quality audits and original-event duplicate candidates; HMAC identifier pseudonyms; category-aware cases, variants and Directly-Follows Graph; elapsed-duration statistics and observed-interval WIP proxy; document-disjoint temporal cohorts; pooled/category whole-trace bootstrap and semi-Markov models; SimPy FIFO resources, events and bounded records; paired Monte Carlo and sensitivity; local persistent jobs/cancellation; seven dashboard areas; standalone HTML/JSON/CSV reports and reproducibility manifests; optional referenced loopback Ollama interpretation.

Optional empirical/Poisson/piecewise-Poisson arrival generators and empirical/exponential/gamma/lognormal/Weibull interval utilities are tested. The published study uses observed arrival schedules and empirical elapsed gaps, rather than imposing a Poisson or service-time interpretation.

## Measured scope

The full official BPI2019 log has been acquired and reconstructed: **1,595,923events,251,734cases(line items),76,349purchase documents,42activities**. Detailed reports distinguish observed data, computed model results and hypothetical scenarios. The independent comparison does **not** establish full digital twin validation: the predefined route-frequency criterion fails. Quantitative error metrics and negative findings remain visible. Do not present the simulator as a validated predictor of all company operations.

No costs/savings, employee rankings, ERP connections or cloud AI are implemented. The dataset does not identify real service times, waiting times or capacity. Repeated invoices/receipts can be legitimate installments.

## Authorised local logs

Copy a file into `imports/` inside the configured data directory, then import it from the dashboard. Default mapping: `case_id,activity,timestamp,resource,lifecycle,category,document_id`; the import API supports explicit field mappings. Timestamps require an explicit timezone. Private imports use a private local HMAC key and drop resource identifiers. They create a separate normalized dataset; automatic calibration/generalization to a new company's process is not implemented. The public BPI reproduction remains pinned and independent.

## License

Original software: Apache License2.0; full [LICENSE](LICENSE). Original algorithms, not PM4Py or copied AGPL code. Dependencies retain their licences; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [DEPENDENCIES.json](DEPENDENCIES.json). BPI2019 data and attributed derived dataset material retain **CC BY4.0**, Boudewijn van Dongen / 4TU.ResearchData. Raw data are not bundled in the source distribution.

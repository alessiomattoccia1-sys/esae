<!-- SPDX-License-Identifier: Apache-2.0 -->

# Third-party components and source data

No third-party binaries or model weights are bundled. Dependencies are installed separately from the exact hash lock. Existing engine licenses are preserved. Metadata audit of the runtime dependencies:

| Package | Version | License metadata |
|---|---|---|
| fastapi | 0.162.0 | MIT |
| starlette | 1.10.0 | BSD-3-Clause |
| uvicorn | 0.54.0 | BSD-3-Clause |
| httpx | 0.28.1 | License :: OSI Approved :: BSD License |
| PyYAML | 6.0.3 | License :: OSI Approved :: MIT License |
| numpy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| scipy | 1.18.1 | License :: OSI Approved :: BSD License |
| pandas | 3.1.1 | BSD-3-Clause |
| statsmodels | 0.15.0 | BSD-3-Clause |
| duckdb | 2.0.0 | License :: OSI Approved :: MIT License |
| pyarrow | 26.0.1 | Apache-2.0 |
| jarvis-tools | 2026.6.12 | MIT |
| pydantic | 2.14.3 | MIT |
| formulaic | 1.2.2 | MIT |
| patsy | 1.0.3 | License :: OSI Approved :: BSD License |
| wrapt | 2.5.2 | BSD-2-Clause |
| interface_meta | 2.0.1 | MIT |

NumPy/SciPy binary distributions carry additional permissive third-party notices (including linked numerical libraries); their upstream license files remain applicable. Package metadata is an inventory, not a substitute for those full license texts. No third-party code is relicensed automatically. Black is a development-only formatter, not a runtime or bundled dependency.

Institutional data are governed by DATA_SOURCES.md, DATA_GOVERNANCE.md and reports/financial/DATA_NOTICE.md. No source dataset, chart, mark or publication is represented as original Apache-licensed software. New York Fed reference-rate attribution/disclaimers accompany SOFR-derived results.

# Materials Discovery Engine — MDE 0.1.0

A project by **Alessio Mattoccia**.

**Research Engines / CODE · LIFE · MATTER**. This third engine shares the existing repository and minimal research core with ESAE0.1.1 and GEE0.1.0. It acquires real public NIST JARVIS-DFT data, validates crystals and units, and performs deterministic photovoltaic screening. It is not a chatbot or a DFT simulator.

Qualified platform: Mac mini M1, macOS27, Python3.12. Windows/Linux are not qualified. Python3.11+ is the code target; the exact tested wheels/lock are for Python3.12/macOSarm64. No service, model or global package is installed automatically.

## Run locally

1. Download and extract `Research-Engines-0.2.0-source.zip` from the existing repository release `research-engines-v0.2.0`.
2. In the extracted directory: `python3.12 scripts/setup_materials.py`. This creates `.venv-mde` separately from ESAE/GEE.
3. Run `.venv-mde/bin/python -m materials.cli serve`.
4. Open http://127.0.0.1:4202/ in a browser. Opening the dashboard performs no acquisition.
5. Press **Avvia screening reale** to acquire the pinned official snapshot (48,447,610bytes). Cache, SQLite, structures and computation stay in `.local/materials`. The dashboard shows progress and restores saved studies after refresh.
6. Explore all six areas, filter materials, open details and export HTML/JSON/CSV/manifest. Close the terminal with Ctrl+C. Results persist locally.

Alternatively run `.venv-mde/bin/python -m materials.cli run --data .local/materials`. The JSON output includes a job ID. Raw verification: `.venv-mde/bin/python -m materials.cli verify --data .local/materials --job JOB_ID`.

For network-free numeric replay of the published study:

```sh
.venv-mde/bin/python -m materials.replay --input reports/materials/MDE-001_INPUT.json.gz --report reports/materials/MDE-001_RESULTS.json
```

The published descriptors omit full atom coordinates. This replay checks analysis, not fresh acquisition or raw crystal parsing. Full verification reacquires/verifies the original frozen source archive and runs `materials.cli verify`.

## Implemented

Pinned HTTPS JARVIS connector, strict source/redirect allowlist, resumable bounded downloads, verified cache, streaming ZIP/JSON parsing, formula/structure validation, missingness/unit normalization, identity deduplication, local SQLite, progress/history and interrupted-job replay, configurable gap/hull/composition/dielectric/SLME filters, three transparent rankings, 12-condition sensitivity, Pearson/Spearman/IQR descriptions, six-area local dashboard and five scientific report formats.

Optional Ollama is explicitly configured with `--ollama-url http://127.0.0.1:PORT --ollama-model MODEL`. No model is downloaded. The model receives only selected public evidence and returns referenced, unverified hypotheses. Deterministic analysis works without it. Materials Project is **not implemented** and no key was present. No 3D crystal viewer is claimed; the dashboard exposes validated cell/coordinate data.

## Scientific result

MDE-001:93,902valid uniqueJIDs;21,559TB-mBJgaps;2,561gap-screened;415gap+hull and415gap+hull+SLME candidates.95remain eligible across all12alternative criteria. These are existing database materials selected for follow-up, not newly discovered materials or validated devices.

The three official detail pages were retrieved separately: two report SLME values differing from the fixed snapshot. These discrepancies are retained in the report; per-record optical thickness/temperature are not encoded in the bulk dataset. Do not treat the optical ranking as independent confirmation.

## License

Original software: **Apache License2.0**, full text in the root [LICENSE](../LICENSE); attribution in [NOTICE](NOTICE). NIST data: **CC BY4.0**, separately attributed and modified; see [DATA_SOURCES.md](DATA_SOURCES.md). Dependencies retain their own licenses. No raw archive, model weights or third-party executable is bundled.

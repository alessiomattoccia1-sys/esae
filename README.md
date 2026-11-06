# Embedded Software Analysis Engine — ESAE v0.1.1

Part of **Research Engines**: this existing repository also contains the
independent [Genomics Evidence Engine 0.1](GENOMICS_README.md),
[Materials Discovery Engine 0.1](materials/README.md), public-source
ClinVar/Ensembl analysis, real JARVIS photovoltaic screening and a small shared research core. Existing ESAE
algorithms, APIs, local UI and native sandbox are preserved. See
[architecture/reuse assessment](ARCHITECTURE_REUSE.md).

Real, local C/C++ analysis. A small engineering prototype by **Mattoccia Labs**.
Cppcheck and clang-tidy produce actual diagnostics; embedded heuristics and optional
local AI explanations stay visibly separate. No synthetic analysis results.

**This is not a certified tool for safety-critical, avionics or military software.**
It does not compute WCET, prove race freedom, certify standards or control devices.
Read [LIMITATIONS.md](LIMITATIONS.md) and [SECURITY.md](SECURITY.md).

## Quick start — macOS Apple Silicon

Qualified platform: Mac mini M1, macOS 27, Python 3.12. Other macOS versions are
not claimed as tested. Linux/Windows installation/OS isolation are not qualified.
This release is a **source prototype**, not an Appunti-style signed installer.

1. Download the `ESAE-0.1.1-source.zip` from the GitHub release and extract it.
2. Provide **Python 3.12** and Apple's Command Line Tools. Check:
   `python3.12 --version` and `xcrun --find clang++`.
   If the tools are missing, install them personally with `xcode-select --install`.
3. In Terminal, enter the extracted ESAE directory and run:

   ```sh
   python3.12 scripts/setup.py
   ```

   This explicit setup installs hashed Python wheels in `.venv`, obtains the
   SHA256-pinned public Cppcheck source, and compiles it in `.toolchain`. It does
   not install global packages, open ports externally or create a login service.
   First setup needs Internet; scans and the dashboard work offline afterwards.

4. Start:

   ```sh
   ./Avvia-ESAE.command
   ```

5. Open **http://127.0.0.1:4196/** in your browser. The owned sensor demo is selected.
   Press **Analizza repository**, then explore Overview, Findings, Architecture
   and AI Insights. Export JSON or HTML using the report links.
6. Close with **Ctrl+C** in Terminal. `.local` results persist. Refreshing the
   browser or reopening ESAE restores saved scans; interrupted work is labeled.

The site presents ESAE and links documentation/downloads. **GitHub/static hosting
does not run FastAPI or clang-tidy.** No private repository crosses the VPS.
There is no public upload service or exposed Mini API.

## Authorize another local repository

Stop the local engine, then explicitly allow the repository:

```sh
./Avvia-ESAE.command --allow-root /absolute/path/to/repository
```

Paste that path in the dashboard. Paths outside authorized roots are refused.
Use a normal directory, not a symbolic link. Default exclusions: `.git`, `.venv`,
`node_modules`, `build`, `dist`, `vendor`, `third_party`, `external`, `generated`.
Change exclusion patterns in the form if needed. Original source files are never
modified. Private evidence snapshots/results stay in `.local`, excluded from Git.

Provide `compile_commands.json` in the repository root or `build/`. ESAE **never
runs its compiler commands**: it reconstructs only accepted language, standard,
macro and internal include options. A missing database uses a clearly reported
standalone fallback. Rejected options/configurations produce coverage errors.

For the owned demo, `scripts/demo_database.py` supplies a portable database without
executing any build. A CMake project is also provided for voluntary manual building:

```sh
cmake -S demo -B demo/build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build demo/build
./demo/build/sensor_demo
```

Only the correct sensor/communication path is invoked by `main`; intentionally
defective functions are documented in `demo/DEFECTS.json` and never called.
Do not execute unknown repository build scripts to prepare a scan.

## CLI / explicit tools

```sh
.venv/bin/python -m esae.cli doctor
.venv/bin/python -m esae.cli scan
.venv/bin/python -m esae.cli scan /path/repo --allow-root /path/repo
.venv/bin/python -m esae.cli serve --cppcheck /trusted/bin/cppcheck --clang-tidy /trusted/bin/clang-tidy
```

Executables are fixed by the operator, version/hash checked at startup, not
selected through repository input or API requests. Missing tools are explicit;
the scanner, heuristics, dependency graph and reports still work partially.

## Optional Ollama

ESAE works without it. Install/run Ollama separately and prepare a licensed local
model yourself. Then explicitly opt in:

```sh
./Avvia-ESAE.command --ollama-url http://127.0.0.1:11434 --ollama-model qwen3:4b
```

Open a finding and press **Spiega con IA locale**. Only that finding and a bounded
source context go to the configured loopback endpoint. No automatic request,
download or cloud fallback. Timeout/unavailability is visible. Each explanation
retains the finding ID and **AI hypothesis / not verified** classification.
No edits or model-weight training are performed.

## Architecture

| Component | Module |
|---|---|
| Repository Scanner / evidence snapshots | `esae/scanner.py`, `compilation.py` |
| Static Analysis Engine / process boundary | `esae/tools.py`, `runner.py`, `safeexec.py` |
| Embedded Risk Analyzer | `esae/risks.py` |
| Optional AI Analysis Engine | `esae/ai.py` |
| Dependency Analyzer / future AST boundary | `esae/dependencies.py` |
| Report Engine / persistence | `esae/report.py`, `storage.py` |
| Orchestration, local API, dashboard | `service.py`, `api.py`, `static/` |

Each normalized finding includes ID, scan ID, file, line, column, severity,
category, rule, source tool, evidence, confidence type, verification status,
optional AI explanation and all contributing tool reports. Tool severities are
mapped high/medium/low/info. A count is not a count of uniquely proven defects.

## Tests and real demonstration

```sh
.venv/bin/python -m pytest -q --basetemp=.local/pytest-new-run
```

Use a **new** basetemp path for each retained evidence run (pytest clears its
explicit basetemp). Unit tests cover scanner/limits, compilation filtering,
parsing, deduplication, risk rules, include cycles, SQLite, API/CSRF/paths/exports,
Ollama unavailable/schema and process sandbox/deadlines. Integration tests execute
the installed native tools against the owned demo, including known defect matches.

Actual demo JSON/HTML and validation matrix are delivered in `reports/`, with
source hashes and tool versions. They contain no private project input. Original
private test logs stay in `evidence/` and are not distributed. No mock output is
substituted when an analyzer or Ollama fails.

## License and conservation

Original source/demo: **Apache-2.0**, chosen by the owner. Third-party analyzers
are separate and retain their licenses; see [THIRD_PARTY.md](THIRD_PARTY.md).
ESAE release archives contain original source, owned demo and sanitized reports,
not third-party binaries, models or local archives. Dependencies use exact
versions/hashes on the qualified platform.

Sources/distribution are PROJECT, verification reports are EVIDENCE and policy is
CANONICAL; retained until explicit retirement. No broad cleanup or midnight
deletion. Temporary files, when needed, belong in TMPDIR and only owned unused
files may be removed. See [STORAGE.json](STORAGE.json).

## Real workload qualification / checkpointed benchmark

The owned 106-line demo is a defect-detection regression, not a scale claim.
The `benchmarks/` example reproduces a separate real C++ workload: the CLI/core
build of Cppcheck 2.22.0, with 186 unique source/header files, 134,737 physical
lines and 85 original translation units. GUI/tests/addons are excluded. Headers
reused by different units are counted once in the unique-input figure.

**Measured on Mac mini M1 / 16 GiB / macOS 27:** 85/85 translation units,
both analyzers completed, zero execution/configuration errors; **689.715 seconds
(11.5 minutes)**. Analyzer peak RSS **540 MiB**, controller peak **143 MiB**
(separate process high-water marks, not simultaneous system total). The two
slowest units repeated with identical diagnostic signatures; checkpoint/resume
was separately exercised with the public command. **53 tests passed**.
See [full conditions and results](reports/scalability.html) and
[machine-readable measurements](reports/scalability.json).

Run the explicit local profile (downloads only SHA256-pinned public source):

```sh
.venv/bin/python -m benchmarks.reproduce_cppcheck --output .local/cppcheck-benchmark
```

Use `--max-new-units 5` to stop after five new units; rerun the same command to
resume. The checkpoint is reused only when profile, engine sources, toolchain
and work-source hashes match. One unit at a time, 120s maximum per native process
(the existing API maximum), 300s native budget per unit; all input/sandbox limits
remain in force. Ctrl+C reaps the owned native process.

This is a selected macOS arm64 C++11 configuration with recorded compiler macros,
not all possible platform/configuration combinations. Cppcheck follows the
selected compilation configuration instead of exploring unrelated alternatives.
No whole-program CTU result across separate units, WCET/race-freedom proof,
verified bug count or universal maximum line count is claimed. The standard
single-job profile and checkpointed profile have different coverage/runtime.
The initial pre-correction single-job baseline stopped partially at 305.215s;
the later run also corrected target macros/configuration selection, so this is
not a controlled speedup comparison. This is the largest workload qualified so
far here, not a maximum established across arbitrary C++ repositories.

## ENGINE 04 — MARKETS

Financial Systems Intelligence Engine 0.1.0 adds official Treasury/Chicago/New York Fed acquisition, DuckDB/Parquet storage, dependence-aware statistics, a real FSIE-001 study, seven-area local dashboard and a separate synthetic 20-million-row benchmark. See [financial/README.md](financial/README.md). Code Apache 2.0; institutional data terms separate. Original runtime files of CODE, LIFE and MATTER are preserved.


## ENGINE 05 — Fusion Plasma Research Engine

FPRE 0.1.0 adds two independent local laboratories for public experimental diagnostics. Five real MAST shots (ten signals, 757,500 valid samples) and seven original STFC detector frames (28 million valid pixels) produce six reproducible computational findings. Exact raw-source replay, independent numerical checks and all 246 tests pass; prior engine algorithms/APIs remain unchanged; the shared runner has one bounded exited-child handling fix.

Read [FPRE setup](fusion/README.md), [scientific results](fusion/RESULTS.md), [architecture reuse](fusion/ARCHITECTURE_REUSE.md), [source rights](fusion/DATA_SOURCES.md) and [limitations](fusion/LIMITATIONS.md). Start with `python3.12 scripts/setup_fusion.py`, then `.venv-fpre/bin/python -m fusion.cli serve`. The browser dashboard is loopback-only; no service or model is installed automatically.

Original code is Apache 2.0. MAST scientific derivatives remain CC BY-SA 4.0; STFC detector derivatives remain CC BY 4.0. This is retrospective measurement characterization, without apparatus control, implosion optimization or a claim of a new physical discovery. Exact historical replay needs the original manifest-matching cache.

# Embedded Software Analysis Engine — ESAE v0.1

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

1. Download the `ESAE-0.1.0-source.zip` from the GitHub release and extract it.
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

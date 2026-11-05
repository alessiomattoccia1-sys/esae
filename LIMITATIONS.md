# Technical limits — v0.1

This is a working research prototype, **not a certified verification tool** for
avionics, military, industrial or safety-critical deployment. It can analyze C/C++
source from these domains with appropriate authorization, but it does not assess
their operational safety or control devices.

## Implemented scope

- C/C++ inventory (.c/.h/.cpp/.hpp/.cc/.cxx), physical/nonblank line counts, directory
  structure, CMake/Make/compilation-database detection and configurable exclusions.
- Real Cppcheck and clang-tidy execution, structured diagnostics with file/line,
  conservative deduplication retaining all contributing tools, SQLite persistence.
- Local dashboard with scan history, overview, filters, actual source context,
  interactive include graph, opt-in AI explanations and JSON/HTML downloads.
- Real but **lexical** embedded-risk rules: allocation, potentially blocking calls,
  name-based ISR candidates, file-local direct/mutual recursion, global volatile
  candidates, narrow arithmetic and platform constructs. These can be false positives.
- Optional Ollama JSON explanations connected to existing finding IDs, explicitly
  labeled unverified; core features work with Ollama missing/stopped.

## Partial / deliberately bounded

- First accepted compilation configuration per translation unit. Complicated
  cross-compilers, forced headers, modules, response files, custom SDKs and external
  dependencies are rejected or omitted with errors/notes. Host SDK is trusted
  operator configuration; v0.1 demo uses the Mini's SDK, not an MCU target.
- Both analyzers can report the same problem at different columns/trace nodes;
  these are retained separately rather than merged speculatively. Exact specific
  cross-tool location/category groups retain individual reports. Counts are
  **diagnostics/groups**, not a count of uniquely proven defects.
- A static warning is **reported by a tool**, not manually verified by default.
  Demo acceptance matches intentionally inserted defects; this is not universal
  sensitivity/specificity measurement. No claims about unseen projects.
- Include graph resolves literal paths relative to file/root/include, records
  unresolved/system includes and SCC cycles; it does not evaluate all conditional
  preprocessor configurations, macro includes or every compiler search path.
  Dashboard shows at most 80 nodes; complete graph is in the JSON report.
- Function heuristics do not resolve C++ overloads, templates, macros or cross-file
  symbols. A volatile object is a shared-data candidate, **not proof of a race**.
- One active operation, 1000 files / 50MB, 2MB/file, traversal caps, 30s/process
  default, 300s total native budget. No background daemon installed. Interrupted
  scans remain visible as interrupted and are not silently replayed.
- Source snapshots are private and persist; refreshing the browser restores the
  newest saved scan. Work is not an atomic snapshot against concurrent owner edits.
- macOS Apple Silicon qualified. No Windows installer or Windows/Linux GUI/native
  qualification. Reproducible Python source distribution, not a notarized app.
- WebKit 2370 emits a style-src-attr CSP warning for its native select controls
  (also reproduced with a minimal select and no application JavaScript). Filters,
  history and exports work in the functional tests. This warning is preserved in
  evidence; strict CSP is retained, and zero browser console messages is not claimed.

## Not implemented / not verified

- Full Clang AST integration, complete call graph, interprocedural embedded/RTOS
  concurrency model, hardware-in-loop, target emulation and device control.
- WCET computation, absence of race conditions, formal proof of correctness,
  memory safety guarantee or compliance/certification (MISRA/CERT/DO-178C/etc.).
- Automatic code editing/fixes, autonomous repository builds, cloud IA, remote
  multi-user scanning, upload service, paid APIs, external telemetry.
- Exhaustive false-positive evaluation or detection of every possible vulnerability.
- Online learning/fine-tuning of Ollama. Explanations do not modify model weights.

The public website presents documentation and an owned-demo report. GitHub hosts
source/downloads. **Neither static hosting nor GitHub runs FastAPI/clang-tidy**;
scans execute on the user's explicitly launched local engine.

# Third-party components

ESAE's original source and owned demo use Apache-2.0 (owner choice, 5 November
2026). This does not relicense the analyzers, Python libraries or optional models.

- **Cppcheck 2.22.0**: GPL-3.0-or-later, separately invoked executable. Official
  source: https://github.com/cppcheck-opensource/cppcheck/releases/tag/2.22.0 .
  The setup downloads the unchanged source, verifies SHA256, then compiles locally.
  Source/checksum and original COPYING remain in `.toolchain`. No binary bundled
  in ESAE's archives. See https://cppcheck.sourceforge.io/manual.html .
- **LLVM/clang-tidy 23.1.4**: Apache-2.0 with LLVM exceptions and notices in the
  third-party package. macOS arm64 wheel assembled by
  https://github.com/ssciwr/clang-tidy-wheel, downloaded from PyPI with a locked
  SHA256; this is a community wheel, not an Apple or Mattoccia binary. Original
  LLVM: https://github.com/llvm/llvm-project .
- **Python runtime**: supplied by the operator, not bundled. FastAPI, Starlette,
  Uvicorn, HTTPX, Pydantic, PyYAML and their dependencies retain their respective
  installed package licenses. Exact versions/hashes are in the lock files.
  Pytest and build tooling are development dependencies.
- **Ollama**: optional, separately installed local runtime. ESAE neither bundles
  nor downloads Ollama/models. The operator chooses and licenses their local
  model. No OpenAI API/key, paid cloud or inference service is required.
- **Web dashboard**: original HTML/CSS/JS and SVG icons, system fonts only;
  no remote font/CDN/telemetry dependency.

Redistributing a future all-in-one installer containing these third-party
executables or model weights requires reviewing and delivering their notices,
licenses and any source obligations. This v0.1 distribution avoids that bundle.

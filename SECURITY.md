# Security boundary of v0.1

Use only on the local computer, with an up-to-date OS and native analyzers. No
security or safety certification. An analyzer is a complex native parser and can
contain vulnerabilities; this prototype is not a hardened multi-tenant service.

## Data and execution

- Uvicorn binds **127.0.0.1 only**. No public uploads, tunnel or remote scan API.
- Every scan must be within a root explicitly authorized by the operator at
  launch (`--allow-root PATH`); default is the owned demo only.
- No source upload, automatic telemetry, cloud fallback, script/build execution,
  compiler executable from a compilation database or automatic source correction.
- Bounded regular UTF-8 source files only. Symbolic links/parent symlinks are
  rejected, external/generated directories excluded. Binary files are not parsed.
- Captured snapshots have read-only source files. Originals are never passed to
  native analyzers; hashes are rechecked after a scan. Concurrent edits can occur;
  reports describe the captured hashes. This is not an atomic filesystem snapshot.
- Compilation database is parsed as JSON/shlex data, never executed. Only safe
  language/standard/macro and in-snapshot include options survive. Plugins,
  response files, forced includes, modules, VFS overlays and arbitrary sysroots
  are rejected. Compiler paths/outputs and other flags are discarded with notes.
  Missing/rejected configurations produce explicit coverage errors, not fake success.
- `--config` supplied by ESAE prevents loading repository clang-tidy config;
  fixes are exported only as diagnostic evidence and never applied.
- Processes use `shell=False`, minimal environment, no stdin, CPU/file descriptor/
  output-file/core limits, wall deadlines and group termination on timeout/output
  overflow. One scan or AI request at a time; total native analysis budget 300s.
- **macOS** sandbox mandatory: no network; reads limited to captured input, the
  selected tools/Python, system libraries and SDK; writes limited to the current
  tool's private output directory. Root directory literal access is required by
  macOS 27's loader and is not a recursive `/` grant. Boundary tests attempt
  external reads/writes and socket creation and require permission failures.
- Non-macOS operation does not provide this OS sandbox. v0.1 is qualified on
  macOS Apple Silicon only. Linux/Windows require separate isolation and testing
  before using hostile repositories; do not expose the engine as a server.
- HTTP boundary: trusted localhost Host, exact local Origin, custom mutation
  header (no permissive CORS), bounded body, no directory listing, UUID scan IDs,
  inventory allowlist for source reads, CSP and text-only rendering of all input.

## Optional AI

Ollama must be explicitly configured using a literal **loopback IP**. No DNS,
credentials, proxy environment or redirects. Only the selected finding and a
bounded source context go to that local endpoint on an explicit user action.
No automatic model download. Prompt treats code/comments as untrusted data;
the output is always marked **AI hypothesis / not verified**. Prompt injection
cannot be proven impossible; AI has no tool or edit capability.

## Retention and distribution

`.local` contains private source snapshots, SQLite findings, logs and reports.
It persists after browser refresh and process restart; no midnight deletion.
The public chat's separate retention policy is unaffected. Local directories
and DB use private modes where supported. External SSD permissions/encryption
remain the operator's responsibility; no OS security settings are changed.

Never publish a report from a private repository without review. Only the owned
demo and sanitized demo results are in the public release. Raw evidence/toolchain,
private paths, credentials and local state are excluded by explicit archive allowlist.
ESAE does not autonomously activate or control any industrial/military device.

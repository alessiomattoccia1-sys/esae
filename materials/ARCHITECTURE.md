# Architecture / MDE0.1

Existing repository, independent `materials` package. No ESAE or GEE algorithm/API/UI rewrite. Existing engine environments remain separate.

| Layer | Actual implementation |
|---|---|
| Acquisition | `materials.connectors.JarvisConnector` + shared `PublicCache`, pinned version/file, allowlisted HTTPS/redirects, retries/backoff/ranges/hash/size validation |
| Parsing | Bounded single-member ZIP and streaming JSON; source nonfinite constants become missing; normalized composition and validated lattice/coordinates |
| Persistence | Shared JobStore extended by MaterialsStore; separate SQLite archive, unique(job_id,JID), filter index, 500record transactions |
| Orchestration | Shared file lock, persisted jobs/phases/progress, explicit local run/resume; idempotent raw import |
| Analysis | Domain-only `materials.analysis`: no genomics/embedded concepts reused as physical evidence |
| AI | New small shared loopback-only hypothesis helper; optional schema/ref validation; quantities remain deterministic |
| API/UI | Existing FastAPI/local-boundary pattern and original ESAE CSS; six materials areas and safe DOM rendering |
| Reporting | Domain-specific HTML/CSV/JSON/method/manifest; qualified static export and normalized offline replay |
| Website | Static verified artifacts only; no public Mini API, local database, acquisition job or model service |

`research_core/http.py` adds optional policy/organization/parser/user-agent injection. Its defaults preserve GEE semantics. The domain source URL allowlist remains in MDE. Source files, dataset hashes, parser/method/software versions and configuration are recorded in each manifest.

Downloads:80MB/response,200MB configured cache/networkbudget; extracted input500MB,150,000records,4Mcharacters/record,512atoms/cell. Identical duplicate JIDs are counted, conflicting duplicate identities fail the study, polymorphs retain separate JIDs. No arbitrary remote URL/upload connector. Full cache and SQLite stay local. Reports do not execute data-supplied code/HTML.

There is no new external backend, daemon or cloudAI transport. Materials Project/other sources are registry entries only, not operational connectors. The separate `.venv-mde` prevents numerical dependency installation from changing earlier runtime environments.

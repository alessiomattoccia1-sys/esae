<!-- SPDX-License-Identifier: Apache-2.0 -->
# Research Engines — architecture reuse assessment

Creator: Codex per Alessio / Mattoccia Labs, 6 November 2026. PROJECT/EVIDENCE;
retain until explicit retirement. Assessment completed before new product code.

## Actual baseline

Existing repository: `alessiomattoccia1-sys/esae`, original Apache-2.0 code,
commit `444493406f9e59c1e2b5cd18ebbd37d6614c7e4a`, ESAE 0.1.1.
Local source remains in the established `esae/` repository; no parallel clone,
replacement repository or source relocation. New independent `genomics/` and
`research_core/` packages will be added here. ESAE algorithms, APIs, CLI,
dashboard and native sandbox remain unchanged.

Baseline: **53 tests passed**, 0 failed/skipped, real Cppcheck 2.22.0 and
clang-tidy 23.1.4 on the owned demo, 2.35s. The first invocation from the parent
workspace could not import the nested package; it was corrected by using the
repository working directory. This was not a passing test run.
Receipt: parent `operations/research-engines-20261106/ESAE-BASELINE-TESTS.xml`.

## Components and decisions

| Actual component | Classification | Reuse decision |
|---|---|---|
| `esae/models.py:now` | Reusable unchanged | UTC timestamp helper imported by shared core; no edits |
| `esae/ai.py:validate_ollama` | Reusable unchanged | Same literal-loopback-only endpoint gate for GEE |
| `esae/static/style.css` | Reusable unchanged | Served directly as shared local dashboard stylesheet, not copied |
| `esae/static/app.js` DOM/table/icon patterns | Reusable through adaptation | Small shared safe-DOM helpers; GEE-specific views, no duplicated full dashboard |
| `esae/service.py:Engine` / threading lock | Reusable through adaptation | Generic job/evidence envelope and optional embedded adapter call original API; do not refactor existing engine |
| `esae/storage.py:Store` | Reusable through adaptation | Generic SQLite jobs/evidence core; separate genomics schema, no migration of ESAE database |
| `esae/api.py` local boundary | Reusable through adaptation | New GEE app with same local-only/Origin/size/CSP principles and its own endpoints |
| `esae/report.py` HTML escaping/export approach | Reusable through adaptation | Domain-neutral evidence helpers and separate genomic report; software severity never reused as a biological score |
| `esae/ai.py:explain` engineering schema | Reusable through adaptation | Separate evidence-referenced genomic hypothesis schema, bounded local transport; no cloud |
| `scanner.py`, `compilation.py` | Specific to C/C++ | Keep unchanged; not a genomic parser |
| `tools.py`, `runner.py`, `safeexec.py` | Specific to C/C++ | Preserve analyzers and process isolation; genomic ingestion does not execute commands |
| `risks.py`, `dependencies.py` | Specific to C/C++ | No reuse as variant/pathogenicity logic |
| ClinVar TSV/VCV/RCV/SCV parsing | To implement for genomics | Validate current official schemas, stable IDs, source scope and missing fields |
| GRCh37/38 representation / Ensembl VEP | To implement for genomics | Exact reference/coordinate/allele or HGVS identity, never gene-name-only matching |
| Scientific conflict analysis | To implement for genomics | Separate aggregate conflicts, same-condition submission differences, condition/date effects and insufficient context |
| GEE SQLite explorer/report/dashboard | To implement for genomics | Variant/submission/condition provenance, real denominators and explicit limitations |

## Site and deployment assessment

The existing website is React + esbuild. Shared sources are under `site/`,
`design/labs-hierarchy-20261102` and the isolated research overlay in
`design/research-prototypes-20261105`. ESAE's current public route is
`/ricerca/esae/`; source78 adds only two decorative concept backgrounds to the
qualified source77 presentation. Keep that route and its reports/downloads.
Introduce `/research-engines/` and `/research-engines/genomics/`; link the existing
ESAE page rather than duplicating it. Existing TRACE/Sentinel research remains.
Use existing Labs brand, language and appearance controls, IT/EN/DE, responsive
CSS and isolated hashed assets. No global redesign or generic chatbot UI.

Static deployment uses the installed Mini → VPS TCP2223 client documented in
parent `PUBLISHING.md`. Read fresh inventory/baseline, reproduce affected public
inputs, qualify only the allowlisted delta, publish atomically, then verify all
outside-delta hashes and live HTTPS/browser behavior. General site build contains
unqualified work and is excluded. No Netcup/SSH22, backend or service changes.

## Data and experiment design gates

Public ClinVar/Ensembl only. Official TSV availability and actual headers have
been inspected through bounded HTTPS range reads. Archive-wide TSV downloads are
not automatically necessary: prefer a documented reproducible filtered sample
with versioned VCV/RCV detail where possible. Preserve full response hashes,
release metadata, selection IDs, exclusion counts, parser version and raw local
cache. A prefix hash is explicitly not a full-file hash.

No result is publishable until live acquisition, deterministic analysis, expected
fixture tests, identifier/condition checks and real cross-source matching pass.
Missing access or fields remain visible. No clinical recommendations, personal
genetic data, invented confidence score, model-weight learning or cloud transport.
Rerun ESAE's existing regressions after integration; original runtime file hashes
will be compared against this baseline before release.

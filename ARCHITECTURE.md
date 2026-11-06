<!-- SPDX-License-Identifier: Apache-2.0 -->
# Research Engines architecture

Original software: Apache-2.0. Two independent domain engines in the existing
repository, with a deliberately small common layer. See ARCHITECTURE_REUSE.md
for the preimplementation audit and baseline regression evidence.

```
research_core/              shared contracts, local job persistence, HTTP cache,
                            cross-process operation lease, loopback web boundary
esae/                      original C/C++ scanner, native analyzers, risks,
                            dependency graph, API, SQLite and local dashboard
genomics/                  ClinVar/Ensembl connectors, public-data parsers,
                            variant/condition/SCV model, scientific comparisons,
                            separate SQLite schema, API/dashboard/reports
```

## Compatibility boundary

No existing `esae/*.py` or `esae/static/*` file needs changing. Existing URLs,
request schemas, algorithms, native process sandbox and data retention remain.
`research_core.EmbeddedAdapter` delegates to an existing ESAE Engine's original
Store and wraps its report in a generic evidence envelope. It neither rewrites
the report nor migrates its database. The original test suite and native demo
are rerun alongside the genomic suite; runtime hashes are checked against the
assessment snapshot.

GEE directly reuses ESAE's UTC helper, literal-loopback Ollama validation and
the original dashboard stylesheet, served from its existing location. Domain
rules, schemas, result labels and UI behavior remain separate. A software
warning, a ClinVar aggregate conflict and an SCV classification difference are
not interchangeable concepts.

## Genomic flow

1. Explicit owner/user request starts one bounded local job, not a daemon.
2. Official gene-filtered ClinVar searches produce a frozen list of numeric
   Variation IDs, before fetching classifications. New jobs use their own cache;
   resuming an incomplete job preserves its selection and acquired source files.
3. Full VCV API responses are streamed to disk with size/time/quota checks,
   HTTPS validation, rate limiting and retries. Resume ranges require a matching
   ETag/Last-Modified validator. Completed cache objects are SHA256-verified.
4. The parser whitelists variant, organization and classification metadata.
   Sample/ObservedData and free-text patient/clinical narratives are not indexed
   or exported. VCV, RCV and SCV accessions retain versions and scope.
5. SQLite stores jobs, normalized variants, submissions and dataset manifests.
   Import UPSERTs do not multiply records on replay. Completed results persist.
6. Deterministic analysis compares only current germline SCVs with exact NCBI
   MedGen condition-set mappings and independent organization IDs. Official
   aggregate conflict labels and source classifications are never reassigned.
7. A fixed compatible SNV subset is annotated by Ensembl VEP. Matching requires
   GRCh38, chromosome, 1-based position, forward strand, reference and alternate
   alleles, plus independently resolved Ensembl gene IDs. No gene-only join.
8. Selected versioned RCV details are checked against the VCV condition summary.
9. JSON/HTML and a reproducibility manifest are written locally. Offline verify
   reparses cached VCVs, verifies all source hashes and recomputes the analysis.
10. Optional Ollama receives only bounded selected variant evidence, never a
    database dump; returned accession references are validated. Outputs remain
    unverified AI hypotheses. No cloud fallback, model download or training.

## Local interfaces

ESAE remains `http://127.0.0.1:4196`. GEE defaults to
`http://127.0.0.1:4198`. GEE provides `/api/jobs`, job reports, filtered variant
summaries, individual variant detail, sources, JSON/HTML/manifest export,
explicit offline verification and optional explanation. The API rejects
arbitrary URLs, file uploads and personal-genetic-data request fields.

Both follow a local-only boundary: no remote client, foreign Origin or arbitrary
Host; same-origin mutation header, small request limits, strict CSP, no CORS,
no telemetry. GEE's cross-process lease prevents simultaneous operations on the
same archive and distinguishes a live job from one interrupted by process exit.

## Public site boundary

The existing React/esbuild site presents `/research-engines/` and
`/research-engines/genomics/`, linking the existing `/ricerca/esae/` page.
Only a qualified static export, real screenshots, source/release links and
reports are published. SQLite, raw cache, internal APIs and filesystem paths
remain on the user's computer. The VPS performs no genomic or C++ calculation.
Deployment remains the established allowlisted static TCP2223 pipeline.

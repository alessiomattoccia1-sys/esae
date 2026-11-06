<!-- SPDX-License-Identifier: Apache-2.0 -->
# GEE 0.1 qualification — 6 November 2026

Qualified environment: Mac mini M1, 16 GiB, macOS 27, Python 3.12. Native C++
checks use Cppcheck 2.22.0 and clang-tidy 23.1.4 under the unchanged ESAE sandbox.
Windows/Linux execution has not been qualified. This is an experimental source
release, not a medical product or universal benchmark.

## Automated regression

- Existing ESAE baseline: **53 passed**, before adding genomic modules.
- Final combined suite: **113 passed**, no skips/failures. One preexisting
  Starlette TestClient/httpx deprecation warning; no dependency changes to hide it.
- Original ESAE runtime modules and static assets retain their assessment hashes.
- Dedicated tests exercise VCV/RCV/SCV scope, conditions, independence, incomplete
  records, gzip limits, cache validators, job recovery, SQLite, exports, API
  boundaries, public projections and optional AI schema/reference/measurement gates.
- Synthetic fixtures explicitly define expected results and never count as live
  acquisition. Initial test harness mistakes and restricted nested-sandbox runs
  were retained as failed evidence before corrected qualification.

## Real GEE-001

Job: `6b81e408-e25f-4fdd-99ca-31de2bcf3855`. Fixed first 40 ascending Variation IDs
per official BRCA1/BRCA2 single-gene query, selected before classifications.
Query populations: 14,132 / 22,046 IDs. This sample is nonrandom and describes
neither all ClinVar nor a clinical/population prevalence.

- **80** unique variants, **543** RCVs, **1,770** current germline SCVs,
  **164** distinct submitter organization IDs.
- Official aggregate conflict: **12/80 (15%)**.
- Same-condition cross-band submission differences: **28/75 comparable variants**
  (**37.333%**), distinct from the official aggregate conflict metric.
- Expert-panel VCVs: **52/80 (65%)**. Criteria/date/citation metadata use SCV
  denominators, not variants; see report.json for all ratios and missingness.
- **12/12** attempted compatible exact GRCh38 SNVs matched Ensembl VEP,
  **12/80** imported-variant coverage, release **116**.
- **6** exact-version RCV detail checks matched their VCV summary classifications.
- All **103** complete source responses rehashed and all **80** VCVs reparsed
  offline. Deterministic analysis SHA256:
  `7a8667032c123a7bd4841d34769d179e3a2f8dd7c7d876a5c180dc6c38b9e1b0`.
- Independent format checks: four VCV XML/ClinVar ESummary classifications and
  review labels agreed; two GRCh38 reference bases agreed with Ensembl sequence.
- Initial acquisition had one Ensembl timeout. That partial attempt is retained;
  resume used the frozen sample/cache and completed all annotations. Errors were
  not silently omitted from an allegedly successful run.

Examples include `VCV000037388.28`, `VCV000037398.31` (BRCA1) and
`VCV000037715.26` (BRCA2), with versioned SCVs and exact MedGen condition sets.
Full JSON/HTML, manifest and attributed normalized replay input are in
`reports/genomics/`. Complete raw responses remain local, never in the release.

## Optional AI and user interface

A real explicitly requested local qwen3:4b explanation completed in **19.473 s**
for `VCV000037388.28`. Only the selected public metadata reached the literal
loopback Ollama instance. No cloud, model download or training occurred.
Observations and numbers are constructed by deterministic code; model prose
remains an unverified hypothesis, even after schema/reference validation.
Invalid numeric prose and unknown references were rejected during qualification.
This single explanation test is not a general scientific accuracy evaluation.

The local dashboard restores completed studies and saved insights after refresh.
Real WebKit layout verification covers five areas, desktop/mobile and light/dark.
A known WebKit native-select CSP warning also occurs in the original ESAE UI;
strict CSP remains enabled. This is recorded separately from JavaScript failures.

## Reproduce public numeric results without network

```sh
python3.12 scripts/setup_genomics.py
.venv/bin/python -m genomics.replay \
  --input reports/genomics/gee-001-input.json.gz \
  --report reports/genomics/report.json
```

This verifies analysis of the public normalized snapshot. It is not an independent
raw-source verification. For the latter, retain/reacquire the exact versioned
source responses and use the local engine's `verify` operation as documented in
GENOMICS_README.md. Future source snapshots may legitimately differ.

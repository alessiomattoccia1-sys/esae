<!-- SPDX-License-Identifier: Apache-2.0 -->
# MDE — assessment and reuse matrix

Creator: Codex per Alessio / Mattoccia Labs, 6 November 2026. PROJECT/EVIDENCE;
retain until explicit retirement. Written after inspection and baseline tests,
before product implementation. Existing operational repository `esae`, commit
`d167f251b6a955daa871258151137ea2f9abc82c`. No clone or replacement repository.
ESAE 0.1.1 and GEE 0.1.0 are implemented. Initial suite: **113 passed**, no
failures/skips, one existing Starlette HTTPX TestClient deprecation warning.

| Component | Actual reuse | Intervention |
|---|---|---|
| Ingestion | `research_core.http.PublicCache`: streaming, hashes, quotas, retries, validator-based resume | Minimal optional source-policy/metadata extension with existing defaults preserved; NIST/Figshare allowlist separate from ClinVar |
| Database | `research_core.jobs.JobStore`: SQLite, explicit commit/close, recovery | Separate materials archive/schema; no migrations to ESAE/GEE databases |
| Orchestration | `OperationLock`, job persistence and phase/progress patterns | Materials-specific async/resume controller, frozen source metadata and parameters |
| Local AI | `esae.ai.validate_ollama`; GEE transport/schema pattern | Domain-specific bounded hypotheses, exact JID references, deterministic observations/values outside LLM; no cloud/model download |
| Dashboard | Original ESAE CSS, safe DOM/SVG patterns, local-boundary FastAPI | Six materials areas with real tables/filters/distributions; no full UI copy or new framework |
| Report | Escaped static HTML and qualified export pattern | Material-specific JSON/CSV/HTML/method/manifest and offline raw replay |
| Provenance | SHA256 cache records and job/source contracts | Dataset DOI/version/file hash, CC BY attribution, field units/methods and exclusion reasons |
| Charts | Small original SVG charts; no Plotly dependency currently present | Reuse safe SVG bars/scatter from actual numeric arrays, no synthetic data |

The existing C++ scanner/AST/native sandbox/risk rules and genomic condition/
classification algorithms remain domain-specific and unchanged. Formation energy
is not hull energy; optical efficiency is not an experimental device efficiency.

## Scientific source assessment

Official JARVIS documentation links Figshare article6815699. Its live metadata
(version11, DOI10.6084/m9.figshare.6815699.v11) lists the2025-09-24 snapshot,
file64391379,48447610bytes, MD5c3179161ef0d029cf1fa70da463aac6e and **CC BY4.0**.
The official jarvis-tools source currently maps `dft_3d` to an older2022 file;
the prototype will pin and document the newer official article file after schema
inspection, not silently pretend the package mapping and snapshot are identical.
Full archive is bounded under50MB; a whole-dataset descriptive study avoids biased
record sampling. JSON/ZIP parsing streams, with explicit decompression/row limits.
Source cache, original metadata and license evidence stay on the authorized SSD.

JARVIS-tools will supply tested composition/structure utilities if dependency
qualification succeeds. NumPy/SciPy support explicit statistics, not learned
predictions. A separate project-local MDE virtual environment preserves the two
existing engines' dependency environment. No global packages, services or models.
Materials Project is optional and no API key is currently configured. Do not
claim a functioning second-source comparison without real access and ID/structure/
method compatibility checks.

## Website integration

Existing React/esbuild static site, current source82. Master `/research-engines/`,
ESAE `/ricerca/esae/`, GEE `/research-engines/genomics/`. Extend the existing master
with CODE/LIFE/MATTER and evidence-backed Latest Research; add `/research-engines/materials/`.
Preserve the qualified benchmark priority, both copy revisions, controlled-case
appendices, dark/light themes, IT/EN/DE and canonical Apps/defense backgrounds.
Use only the registered static TCP2223 pipeline, fresh baseline and allowlisted
delta. No public analysis backend, database, raw cache, credentials or filesystem
paths. No general site build, Netcup, SSH22 or ATENA/Appunti/mail changes.

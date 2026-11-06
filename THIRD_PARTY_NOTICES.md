<!-- SPDX-License-Identifier: Apache-2.0 -->
# Research Engines — third-party software and data

Original Research Engines / GEE code and ESAE original code: Apache-2.0,
Copyright 2026 Alessio Mattoccia / Mattoccia Labs. No license change to upstream
components or existing third-party works. See LICENSE and NOTICE.

Existing ESAE analyzer/dependency notices remain in THIRD_PARTY.md: Cppcheck
GPL-3.0-or-later, LLVM Apache-2.0 with LLVM exceptions, community clang-tidy wheel,
Python and framework dependencies. No analyzer binary or model is bundled in
this source distribution. GEE does not run the C++ analyzers.

GEE uses the existing Python standard library, FastAPI (MIT), Starlette (BSD-3-Clause), HTTPX
(BSD-3-Clause), Uvicorn (BSD-3-Clause), Pydantic (MIT) and their locked dependency
chain. Runtime license metadata are audited in the retained release evidence.
The original dashboard CSS and small utility patterns are reused under the
project's own Apache-2.0 license; no external frontend framework or CDN added.

**NCBI ClinVar** is the source of public variant assertions and classifications.
Attribute ClinVar on reports/web pages and cite the versioned accessions and
source policy: https://www.ncbi.nlm.nih.gov/clinvar/docs/maintenance_use/ .
The data are not intended for direct diagnostic/medical decision-making without
appropriate professional review. NIH does not independently verify all submitted
assertions. The software's Apache license is not applied to those datasets.
No individual patient observations, Sample/ObservedData objects or full clinical
narratives are included in normalized exports or the public source package.

**Ensembl / EMBL-EBI** supplies gene/transcript IDs and molecular consequence
annotations: https://rest.ensembl.org/ and
https://www.ensembl.org/about/articles/ensembl-content-disclaimer . Retain provider attribution,
live release/response hashes and exact representation checks. This project
excludes restricted third-party colocated annotations, including HGMD fields,
from exported VEP results. No genome sequences or complete articles are bundled.

Future dbSNP, NCBI Gene and GEO connectors are not implemented. Their licensing,
access and attribution requirements must be assessed before adding them.

Only qualified public variant/organization metadata, aggregate reports and original source are distributed; complete raw source responses
stay in the operator's local reproducibility archive. Neither upstream sources
nor their organizations endorse this experimental engine.

Primary terms checked 6 November 2026: https://www.ensembl.org/about/articles/ensembl-content-disclaimer and https://www.ebi.ac.uk/about/terms-of-use/ (revised 14 October 2026). Ensembl-generated data are available for reuse; third-party restrictions remain applicable. This project exports no restricted colocated records.

## Materials Discovery Engine

Original MDE software is Apache-2.0. NIST JARVIS data are CC BY4.0 with separate
attribution and declared normalization/screening modifications, not Apache data.
See [materials/THIRD_PARTY_NOTICES.md](materials/THIRD_PARTY_NOTICES.md),
[materials/DATA_SOURCES.md](materials/DATA_SOURCES.md) and the installed dependency
license metadata/hashes in materials/DEPENDENCY_LICENSES.json. No raw archive,
third-party wheel, model or executable is bundled.


## Fusion Plasma Research Engine

The isolated FPRE environment and exact upstream license-file hashes are documented in fusion/DEPENDENCY-LICENSE-AUDIT.json and fusion/THIRD_PARTY_NOTICES.md. No native reader binary, external scientific paper, complete MAST archive or STFC ZIP is bundled. FAIR-MAST derivatives remain CC BY-SA 4.0 and STFC derivatives CC BY 4.0 with source authors/changes identified. Original FPRE code remains Apache 2.0.

<!-- SPDX-License-Identifier: Apache-2.0 -->
# Data sources, provenance and reuse

The Apache-2.0 license covers original Research Engines software, not upstream
databases, scientific papers or every field returned by a third-party service.
No complete scientific article is copied into this project.

## NCBI ClinVar — implemented

- Official downloads: https://www.ncbi.nlm.nih.gov/clinvar/docs/downloads/
- Official file directory: https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/
- Current README: https://ftp.ncbi.nlm.nih.gov/pub/clinvar/README.txt
- API/use/attribution: https://www.ncbi.nlm.nih.gov/clinvar/docs/maintenance_use/
- Review status: https://www.ncbi.nlm.nih.gov/clinvar/docs/review_status/

Availability and actual headers of `variant_summary.txt.gz`,
`submission_summary.txt.gz` and `summary_of_conflicting_interpretations.txt`
were inspected live through bounded 131,072-byte HTTPS range reads. Their
reported complete sizes were 457,862,838 / 406,785,046 / 2,071,933,144 bytes,
with Last-Modified dates of 1 November 2026. These are schema/availability probes,
not complete downloads or import success claims. A prefix hash is not the full
archive hash. The parsers support their actual header conventions, metadata
comments, compression, row validation, ID filtering and deduplication.

GEE-001 uses a much smaller official E-utilities acquisition: full filtered
search-index responses, selected VCV XML, and versioned RCV detail. This avoids
blindly downloading multi-gigabyte all-gene exports for a bounded study. Every
complete acquired API response has a full SHA256, URL, UTC acquisition time,
organization, server metadata where present, parser version and import counts.
VCV/RCV/SCV versions are recorded. An API response without a release date is
labeled accordingly; acquisition time is not invented as a release date.

ClinVar asks for source attribution when data are copied/distributed, including
on websites. Attribute **NCBI ClinVar** and link the source policy. Data are not
intended for direct diagnostic/medical decisions without appropriate review;
NIH does not independently verify all submitted assertions. Source submitter
classifications remain their assertions, not this project's conclusions.
Only bounded variant/organization metadata are normalized/exported. No
individual Sample/ObservedData objects or free-text clinical narratives enter
the indexed study. Raw public responses remain local for reproducibility.

## Ensembl REST / VEP — implemented for exact GRCh38 SNVs

- Endpoints/documentation: https://rest.ensembl.org/
- VEP region API: https://rest.ensembl.org/documentation/info/vep_region_get
- Data/code terms: https://www.ensembl.org/about/articles/ensembl-content-disclaimer

The provider's live data release is obtained from `info/data`, and gene stable
IDs/assembly from `lookup/symbol/homo_sapiens`. The current assessment returned
release 116; each experiment records its own server response/hash, not this
hardcoded value. VEP annotations retain only consequence terms, transcript/gene
stable IDs, biotype and canonical flags, with exact representation checks.
Molecular consequence is not clinical pathogenicity. Do not distribute
third-party restricted colocated annotations (for example HGMD fields) merely
because they appear in a raw VEP response; this parser excludes them.
Attribute **Ensembl / EMBL-EBI**; no endorsement is implied. No genome sequence
or full paper is redistributed. Review upstream terms again before a different
data redistribution or future bundled dataset release.

## Future provider interfaces — not implemented

`EvidenceConnector` describes the boundary. dbSNP, NCBI Gene and GEO are explicitly
listed as future/not implemented. Their presence in a registry is not an
operational connector, a successful test or an analysis result.

Primary terms checked 6 November 2026: https://www.ensembl.org/about/articles/ensembl-content-disclaimer and https://www.ebi.ac.uk/about/terms-of-use/ (revised 14 October 2026). Ensembl-generated data are available for reuse; third-party restrictions remain applicable. This project exports no restricted colocated records.

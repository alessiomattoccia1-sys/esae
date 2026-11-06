<!-- SPDX-License-Identifier: Apache-2.0 -->
# GEE-001 — methodology version gee-001-1.0

Research question: which source-reported aggregate conflicts, condition-matched
submission differences and documentary limitations occur in a reproducible
public BRCA1/BRCA2 sample? This is descriptive research, not diagnosis or a new
clinical classification.

## Selection, frozen before observing results

Run the official ClinVar queries `BRCA1[gene] AND single_gene[prop]` and
`BRCA2[gene] AND single_gene[prop]`, retaining every returned numeric ID when the
query is complete. Sort numeric IDs ascending and choose the first N per gene.
The initial full experiment fixes **N=40**, at most 80 unique VCVs. Record query
counts, exact selected IDs and all unselected counts. A new query snapshot may
change over time; the frozen manifest/cache provide exact replay.

This is **not random**, not representative and not a population conflict
frequency estimate. Older low-ID variants may be more studied. Changing N after
seeing results is a separate documented experiment, not a hidden sample change.

## Import and exclusion rules

Require a current classified human SimpleAllele record with one requested gene,
a valid Variation ID and matching requested VCV identity. Exclude incompatible
haplotype/included/nonclassified or different-gene records, retaining reason
counts. Acquisition/parse failures remain errors, not biological exclusions.
SCVs retain only current germline assertions; removed/somatic-only records and
duplicate accession versions have separate counts. No clinical narratives or
patient observations are indexed. No general left-normalization/lift-over of
arbitrary indels is claimed. GRCh37 and GRCh38 locations remain separate.

## Units and denominators

- **Variant / VCV:** one unique Variation ID, not one row per assembly.
- **RCV:** one versioned aggregate for a variant-condition relationship.
- **SCV:** one current versioned submitter assertion, scoped to its variant.
- **Submitter:** organization ID, deduplicated across submission records.
- Every percentage has a machine-readable numerator/denominator; zero
  denominator produces `null`, never a synthetic zero-percent result.
- Official conflict ratio uses variants with an available germline aggregate.
- Same-condition difference ratio uses variants with at least one comparable
  group, not all VCVs/RCVs/SCVs interchangeably.
- Documentary criteria/date/citation fractions use current germline SCVs.
- Organization categories are reported both per distinct organization ID and
  SCV-weighted, with those denominators kept separate.
- VEP match fraction uses attempted compatible variants; annotation coverage is
  separately calculated over all imported variants.

## Discordance rules

1. Preserve ClinVar's germline VCV classification/review status. A label
   containing “conflicting” is an **official aggregate conflict**, not our new
   assertion about pathogenicity.
2. Build SCV condition sets using ClinVar's explicit TraitMapping → MedGen CUI
   records, or direct MedGen identifiers. Compare only identical complete sets.
   Generic “not provided/not specified” or unmapped conditions are insufficient.
   Shared words/gene names or partly overlapping condition sets are not joins.
3. Require at least two distinct organization IDs and current germline SCVs.
   Group P/LP together, B/LB together, VUS separately. P versus LP alone is a
   likelihood-label difference, not a cross-band disagreement. Other assertions
   (risk factor, drug response, association) are not forced into these bands.
4. Report all eligible current-SCV differences and, separately, differences
   among SCVs explicitly contributing to the aggregate. Expert-panel precedence
   can leave a source aggregate without “conflicting” while raw differences
   remain. Do not relabel that aggregate as an official conflict.
5. Retain different conditions, unknown contexts and evaluation-date
   heterogeneity separately. Dates do not establish why classifications differ.
6. Fetch a bounded set of exact versioned RCVs for source-summary/detail checks.

## Cross-source subset

Choose at most 12 exact GRCh38 SNVs in a round-robin by gene and ascending
selected Variation ID, before observing VEP responses. Query forward genomic
coordinates and alternate allele. Require equal assembly, chromosome, start/end,
strand and reference/alternate allele string, plus overlap with gene stable IDs
resolved independently from Ensembl. Failed/unsupported representations remain
failed/incompatible; no gene-only matching or implicit assembly conversion.
Only molecular consequences/transcript annotations are retained, independent
of source clinical classification. No causal inference is made.

## Reproducibility and validation

Record full API source hashes and accessions/versions, parser/method versions,
selection, code hashes and all excluded/error counts. Offline verify rehashes
every cached response, reparses VCVs and recomputes the deterministic analysis
hash. Expected synthetic fixtures test both positive and negative comparisons;
they are not presented as live experiments. Real-source acquisition is tested
separately. Numeric results are produced by these algorithms, never an LLM.

Optional local AI outputs are labeled **AI hypothesis / not verified**, cite
only supplied accessions and expose the subset size. They cannot change stored
classifications, deterministic metrics or dataset provenance. No model training.

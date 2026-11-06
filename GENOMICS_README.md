<!-- SPDX-License-Identifier: Apache-2.0 -->
# Research Engines · Genomics Evidence Engine 0.1

Experimental, local analysis of **public** human variant evidence. ClinVar data,
deterministic comparisons, exact Ensembl SNV annotation, provenance and real
reports. **Not a diagnostic product. No personal genetic data or clinical advice.**

This is the same operational repository as ESAE. Existing ESAE 0.1.1, APIs,
dashboard, native sandbox and source downloads remain available. See
[reuse assessment](ARCHITECTURE_REUSE.md), [architecture](ARCHITECTURE.md),
[method](METHODOLOGY.md), [sources](DATA_SOURCES.md) and [limits](LIMITATIONS.md).

## Start locally — qualified on Mac mini M1 / macOS 27 / Python 3.12

Download and extract the Research Engines source release. If ESAE is already
prepared in this repository, its `.venv` is sufficient. For GEE only:

```sh
python3.12 scripts/setup_genomics.py
.venv/bin/python -m genomics.cli serve --data .local/genomics
```

Open **http://127.0.0.1:4198/**. Press **Avvia studio reale** to acquire the
documented BRCA1/BRCA2 sample. Nothing is downloaded merely by opening an empty
dashboard. Use Overview, Genomic Explorer, Evidence Analysis, Research Findings
and optional AI Insights. Each variant opens actual VCV/RCV/SCV/coordinate detail.
Filter by gene, variant, classification, review, condition or annotated source.

The initial full scientific run uses 40 variants per gene, 12 compatible
Ensembl annotations and up to 6 versioned RCV detail checks. These are bounded
subset limits, not a whole-genome or clinical validation claim. Transient source
errors remain visible and make the job partial, never silently successful.

CLI equivalents:

```sh
.venv/bin/python -m genomics.cli run --data .local/genomics --per-gene 40 --ensembl-limit 12 --detail-limit 6
.venv/bin/python -m genomics.cli verify --data .local/genomics --job JOB_ID
.venv/bin/python -m genomics.cli run --data .local/genomics --resume JOB_ID
```

The CLI prints the actual job ID. `verify` rehashes sources and recomputes from
the retained raw cache without network. `resume` is for interrupted/partial/failed
jobs; it preserves the selection and completed source downloads. Finished jobs
are not overwritten. One operation per archive across processes. Closing the
browser does not stop the local process; Ctrl+C stops the process. Archives
persist, and refresh/restart restores saved studies. No startup service installed.

## Source/cache limits

Only official allowlisted HTTPS ClinVar/Ensembl endpoints, no arbitrary URL/file
upload interface. Defaults: 200 MB per acquisition/cache, 12 MB per API response,
at most 100 variants per requested gene, 30 annotations and 12 RCV checks.
Downloads stream to disk, validate responses/hash and retry eligible failures
with bounded backoff/rate limits. Range resumes require a matching validator.
TSV/gzip parsers stream records with decompressed byte/row/line limits.
The complete large TSVs are not fetched automatically for this bounded study.

## Optional Ollama

```sh
.venv/bin/python -m genomics.cli serve --data .local/genomics \
  --ollama-url http://127.0.0.1:11434 --ollama-model YOUR_EXISTING_LOCAL_MODEL
```

Explicit action from variant detail sends only that selected bounded evidence
subset to the literal-loopback runtime. No cloud, automatic model download,
fine-tuning or database “learning”. Returned references must match supplied
accessions; output is an unverified hypothesis. The entire deterministic product
works without Ollama. Source records are data, never operational instructions.

## Tests and public results

```sh
.venv/bin/python -m pytest -q --basetemp=.local/research-tests-NEW
```

Use a fresh evidence path because pytest clears its explicit basetemp. Includes
the original ESAE regression/native tests and dedicated genomic tests. Fixture
results have known expected counts and are separate from live-source evidence.
Public scientific report/manifest and source-release links are published only
after live acquisition and deterministic replay pass. Raw caches, SQLite and
internal API are never deployed to the static site/VPS.

## License

Original software: **Apache License 2.0**, full text in [LICENSE](LICENSE),
attribution in [NOTICE](NOTICE). Third-party data/software retain their terms:
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Attribute NCBI ClinVar and
Ensembl. No claim of endorsement, diagnostic validation or pathogenicity scoring.

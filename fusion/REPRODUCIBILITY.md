# Reproducibility

Install the exact hash-locked environment using scripts/setup_fusion.py. Run each experiment explicitly, then use its persistent job ID with fusion.cli reproduce. The replay first rehashes every acquired source object against the manifest, rebuilds selected chunk stores/native arrays in a fresh owned folder, recomputes all deterministic findings and compares the complete results fingerprint. It uses no network and refuses missing/changed originals.

A fresh acquisition is a new study if upstream source bytes change, even at the same URL. Keep the original immutable cache and manifest for exact historical replay; public release does not include the full STFC archive or remote catalog stores. Offline run uses only already available objects; it never substitutes another source version. Algorithm version, source Git commit, working-source file hashes, exact dependencies, environment and random seed are recorded.

The public package includes original source, reports, source identities/hashes and method parameters. It does not bundle a model, third-party binary or full raw archive. Exact dataset-vintage access may therefore depend on the matching locally retained source cache. Selected scientific figures are derived artifacts with source licenses, not substitutes for raw replay.


Original software © 2026 Mattoccia Labs, Apache License 2.0. Scientific data and derived artifacts retain the separate source licenses.

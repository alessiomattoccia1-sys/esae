# Reproducibility

Use the exact source commit/hash and hashed macOSarm64Python3.12 dependency lock. Acquire the official metadata and gzip once; verify original XES size/MD5/SHA256. Every experiment records source versions, cache acquisition timestamps, parser, parameters, fixed seed20261106, dependency versions, hardware, source-file hashes, output hashes and scientific result fingerprint.

```sh
.venv-ote/bin/python -m operations_twin.cli reproduce OTE-001 --data .local/operations-twin-data
.venv-ote/bin/python -m operations_twin.cli reproduce OTE-002 --data .local/operations-twin-data
.venv-ote/bin/python -m operations_twin.cli reproduce OTE-003 --data .local/operations-twin-data
```

CLI replay recomputes results offline and compares typed canonical Python JSON hashes, excluding timings/environment/job IDs. It rejects changed code or changed source bytes. Missing data/version is an error. Whitespace-only JSON export must preserve numeric types and Python representations; do not compact scientific JSON with JavaScript JSON.stringify. The public downloaded JSON fingerprints are checked after deployment.

Partition resume verifies committed hashes and replays/skips complete source traces; uncommitted in-memory records are reparsed. Interrupted SimPy generators are not pickled or resumed in place; their full simulations deterministically rerun from saved seed/configuration. Models and source logs are not substituted by synthetic data. Pure synthetic queue controls in tests are separate from BPI acquisition and historical findings.

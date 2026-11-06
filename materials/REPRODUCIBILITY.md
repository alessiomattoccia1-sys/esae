# Reproducibility

Exact environment:Python3.12/macOSarm64; `requirements-materials-macos-arm64-py312.lock` lists hashes for all resolved wheels. Install using `scripts/setup_materials.py`. The original `.venv` for ESAE/GEE is not changed.

## Published numeric replay — no network

```sh
.venv-mde/bin/python -m materials.replay --input reports/materials/MDE-001_INPUT.json.gz --report reports/materials/MDE-001_RESULTS.json
```

Expected analysisSHA256: `1ae88ce32871d91d0ba984a557d92c84be508584ca015bf9716f0817d261eec7`. Public descriptors retain all93,902material records used for the analysis. Runtime dates/durations/HTTPdates are not part of the deterministic analysis hash. The manifest separately binds raw source, configuration, methods, source code and software versions.

## Reacquire and verify original source

```sh
.venv-mde/bin/python -m materials.cli run --data .local/materials-reproduction
.venv-mde/bin/python -m materials.cli verify --data .local/materials-reproduction --job JOB_ID
```

The connector pins Figshare article6815699/version11/file64391379. It verifies HTTPS, size, officialMD5 and wholeSHA256, then streams the full ZIP member. Identical source/configuration/method reproduce the analysis hash. If official source availability/bytes change, record the failure; do not replace the pinned dataset and reuse old results.

For an interrupted download, retry against the same cache; HTTPRange requires a compatible validator. For an interrupted job, restart the same engine/archive and use `run --data ARCHIVE --resume JOB_ID`. The input is reparsed idempotently using cache, not trusted from half-computed counters. Completed studies are immutable history; a changed configuration starts a new study. Keep a matching source version when resuming historical jobs.

## Tests

```sh
.venv-mde/bin/python -m pytest -q
```

The complete family suite also requires separately installed Cppcheck and clang-tidy (see the ESAE README). MDE itself does not need native C/C++ analyzers. For MDE-only tests, use `pytest -q tests/test_materials.py tests/test_materials_ai.py`.

Synthetic fixtures test known counts/missingness/filters/correlations. They are not evidence of live database acquisition. The published live study, raw-source replay, normalized replay, browser QA and original-environment113-test regression are separate evidence. Full raw cache and operational QA logs remain local, excluded from distribution.

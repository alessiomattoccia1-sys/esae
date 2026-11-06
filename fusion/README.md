# Fusion Plasma Research Engine 0.1.0

FPRE is the fifth member of Research Engines: CODE · LIFE · MATTER · MARKETS · FUSION. It is a local computational laboratory for retrospective experimental diagnostics, with independent magnetic and inertial algorithms and a shared evidence pipeline.

## Use

Qualified platform: macOS Apple Silicon, Python 3.12. Windows and Linux have not been qualified. This is a source distribution, not a signed installer or apparatus-control system.

```sh
python3.12 scripts/setup_fusion.py
.venv-fpre/bin/python -m fusion.cli serve --data .local/fusion --port 4205
```

Open http://127.0.0.1:4205/. Select a laboratory and start an explicit acquisition. No dataset or language model is downloaded merely by opening the dashboard. Jobs and completed results remain in the local archive across page reloads. An interrupted job can resume from its journaled immutable source objects.

```sh
.venv-fpre/bin/python -m fusion.cli run --experiment FPE-001 --data .local/fusion
.venv-fpre/bin/python -m fusion.cli run --experiment FPE-002 --data .local/fusion
.venv-fpre/bin/python -m fusion.cli reproduce --experiment FPE-001 --job JOB_ID --data .local/fusion
```

Keep the manifest and original cache for exact offline replay. Fresh upstream downloads can have different content at the same URL. See REPRODUCIBILITY.md and the qualified reports under reports/fusion/.

## Implemented scope

FAIR-MAST Parquet catalog and selected Zarr2/3 diagnostic chunks; source units; quality gates; temporal statistics, derivatives, filters, FFT/Welch/STFT; unclassified transients; same-shot descriptive correlations; cross-shot distributions; bounded STFC ZIP inventory and sandboxed raw HDF4 detector reader; image intensity statistics, detector-pixel centroids/profiles and six preprocessing sensitivity cases; SQLite registry; local API; eight-area dashboard; two standalone HTML reports with JSON/CSV/manifests; exact acquired-byte replay.

The ICF study characterizes detector arrays. It does not reconstruct plasma geometry or analyze target settings, laser sequences, yield or implosion performance. ICF-03 uses same-measurement method robustness rather than cross-implosion comparison. Numerical reproducibility is not confirmation of a new physical discovery.

Optional Ollama is explicitly configured with --ollama-url http://127.0.0.1:PORT and --ollama-model MODEL. All scientific calculations work without it. There are no cloud AI calls or apparatus connections.

## License

Original code: [Apache 2.0](LICENSE). FAIR-MAST derived reports/data/plots: CC BY-SA 4.0; STFC derived detector reports/plots: CC BY 4.0. See NOTICE, DATA_SOURCES.md and THIRD_PARTY_NOTICES.md.


Original software © 2026 Mattoccia Labs, Apache License 2.0. Scientific data and derived artifacts retain the separate source licenses.

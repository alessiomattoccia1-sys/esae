# Reproduce FPE-001

From the original source release, on qualified macOS Apple Silicon/Python3.12:

```sh
python3.12 scripts/setup_fusion.py
.venv-fpre/bin/python -m fusion.cli run --experiment FPE-001 --data .local/fusion
.venv-fpre/bin/python -m fusion.cli reproduce --experiment FPE-001 --job JOB_ID --data .local/fusion
```

Initial run acquires official data explicitly. Keep source responses and manifest. Reproduce rehashes original bytes and recomputes without network; missing or modified source objects cause a visible failure. Upstream may replace Zarr objects at the same URL, so fresh acquisition is not automatically the original version. A qualified selected-input public replay is separately labeled; it cannot replace full raw-source validation. No model, apparatus access or cloud is required. Other operating systems are not qualified.

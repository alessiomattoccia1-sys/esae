# Reproducing FSIE-001

1. Extract the original Research Engines source release.
2. On the qualified macOS Apple Silicon / Python 3.12 environment, run `python3.12 scripts/setup_financial.py`.
3. Run `.venv-fsie/bin/python -m financial.cli run --data .local/financial --start 2000-01-01 --end 2026-11-06`. Acquisition is explicit and subject to official source terms.
4. Preserve the full immutable response cache and manifest. Use `.venv-fsie/bin/python -m financial.cli verify --data .local/financial --job JOB_ID` for network-free replay from those original bytes.
5. Compare the analysis SHA-256, source SHA-256, parser/method/software versions and configuration. Sources, especially NFCI, revise; a fresh acquisition is a new study and need not reproduce an older vintage. A changed source must not be presented as the old study.

The distributed source does not indiscriminately redistribute institutional raw time-series archives. A new user may reproduce the algorithm and current official acquisition; an exact historical numeric replay requires the manifest-matching source snapshot. The original complete frozen cache was replayed locally before publication. No artificial source values are supplied to make a hash match.

Dashboard: `.venv-fsie/bin/python -m financial.cli serve`, then http://127.0.0.1:4204/. No cloud or persistent service. Windows/Linux unqualified. The complete regression suite additionally needs the separately installed ESAE C++ analyzers; FSIE itself does not.

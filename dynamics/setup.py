# SPDX-License-Identifier: Apache-2.0
"""Create only Dynamics' own qualified environment; no services or models."""

from pathlib import Path
import sys, platform, subprocess, os, shutil

root = Path(__file__).resolve().parents[1]
if __name__ == "__main__":
    if (
        sys.version_info[:2] != (3, 12)
        or platform.system() != "Darwin"
        or platform.machine() != "arm64"
    ):
        raise SystemExit(
            "Qualified setup requires Python3.12/macOS Apple Silicon; other platforms unqualified."
        )
    if shutil.disk_usage(root).free < 3_000_000_000:
        raise SystemExit("At least3GB free required")
    os.umask(0o077)
    venv = root / ".venv-dynamics"
    python = venv / "bin/python"
    if not python.exists():
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    subprocess.run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--require-hashes",
            "-r",
            str(root / "dynamics/requirements-macos-arm64-py312.lock"),
        ],
        check=True,
        timeout=600,
        env=dict(
            os.environ,
            PIP_CACHE_DIR=str(root / ".local/dynamics-setup-cache"),
            PIP_DISABLE_PIP_VERSION_CHECK="1",
        ),
    )
    subprocess.run(
        [
            str(python),
            "-c",
            'from dynamics.service import DynamicsEngine; from dynamics.api import create_app; print("Dynamics imports OK")',
        ],
        cwd=root,
        check=True,
    )
    print(
        "Start: .venv-dynamics/bin/python -m dynamics.cli serve\nOpen http://127.0.0.1:4206/\nNo dataset, model or background service installed."
    )

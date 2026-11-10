# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Reproducible, isolated setup; never changes existing engine environments."""

from pathlib import Path
import os, sys, platform, subprocess, venv


def main():
    if (
        sys.version_info[:2] != (3, 12)
        or sys.platform != "darwin"
        or platform.machine() != "arm64"
    ):
        raise SystemExit(
            "This hashed wheel lock is qualified for macOS Apple Silicon / Python3.12. Other platforms are not qualified by this release."
        )
    root = Path(__file__).resolve().parents[1]
    dest = root / ".venv-ote"
    if dest.is_symlink():
        raise SystemExit("Symlink environment refused")
    if not dest.exists():
        venv.EnvBuilder(with_pip=True).create(dest)
    env = {
        **os.environ,
        "PIP_CACHE_DIR": str(root / ".local/operations-twin-setup-cache"),
    }
    subprocess.run(
        [
            str(dest / "bin/python"),
            "-m",
            "pip",
            "install",
            "--require-hashes",
            "-r",
            str(Path(__file__).parent / "requirements-macos-arm64-py312.lock"),
        ],
        check=True,
        env=env,
    )
    print("Setup complete. Run .venv-ote/bin/python -m operations_twin.cli serve")


if __name__ == "__main__":
    main()

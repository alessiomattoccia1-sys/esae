# SPDX-License-Identifier: Apache-2.0
"""Deterministic independent-family source artifact, never a repository clone."""

from pathlib import Path
import json, hashlib, zipfile, io, re, subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    names = []
    for folder in ["dynamics", "reports/dynamics"]:
        for p in (ROOT / folder).rglob("*"):
            if p.is_symlink():
                raise ValueError("Symlink in distribution")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
                names.append(p.relative_to(ROOT).as_posix())
    names += ["tests/test_dynamics.py", "scripts/package_dynamics.py"]
    names += [
        "research_core/" + n + ".py"
        for n in ["__init__", "http", "jobs", "locking", "web", "local_ai"]
    ]
    names += ["esae/" + n + ".py" for n in ["__init__", "scanner", "models", "ai"]] + [
        "esae/static/style.css"
    ]
    data = {n: (ROOT / n).read_bytes() for n in sorted(names)}
    data["README.md"] = data["dynamics/README.md"]
    data["LICENSE"] = data["dynamics/LICENSE"]
    data["NOTICE"] = data["dynamics/NOTICE"]
    for n, b in data.items():
        if (
            re.search(rb"/(?:Users|Volumes)/[A-Za-z0-9_-]+", b)
            or b"-----BEGIN " + b"PRIVATE KEY-----" in b
            or re.search(rb"[\w.+-]+@(?:gmail|icloud|yahoo)\.com", b)
        ):
            raise ValueError("Private marker " + n)
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    manifest = {
        "family": "DYNAMICS LAB",
        "engine": "Drone Dynamics Engine",
        "version": "0.1.0",
        "git_commit": commit,
        "classification": "PROJECT",
        "creator": "Codex per Alessio",
        "deletion_condition": "Explicit retirement",
        "original_code_license": "Apache-2.0",
        "source_data_derivatives_license": "CC BY4.0 with source-specific authors/version in reports; synthetic data separately labelled",
        "raw_archives_included": False,
        "models_included": False,
        "private_paths_included": False,
        "files": {n: hashlib.sha256(b).hexdigest() for n, b in data.items()},
    }
    data["DISTRIBUTION.json"] = (json.dumps(manifest, indent=2) + "\n").encode()

    def pack():
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for n, b in sorted(data.items()):
                i = zipfile.ZipInfo("Dynamics-Lab-0.1.0/" + n, (2026, 11, 6, 0, 0, 0))
                i.compress_type = zipfile.ZIP_DEFLATED
                i.external_attr = 0o100644 << 16
                z.writestr(i, b)
        return out.getvalue()

    b = pack()
    assert b == pack()
    sha = hashlib.sha256(b).hexdigest()
    d = ROOT / "dist/dynamics-lab-0.1.0"
    d.mkdir(parents=True, exist_ok=True)
    dest = d / "Dynamics-Lab-0.1.0-source.zip"
    if dest.exists() and dest.read_bytes() != b:
        old = dest.read_bytes()
        hist = d / "history" / hashlib.sha256(old).hexdigest() / dest.name
        hist.parent.mkdir(parents=True, exist_ok=True)
        hist.write_bytes(old)
    dest.write_bytes(b)
    (d / "SHA256SUMS").write_text(sha + "  " + dest.name + "\n")
    (d / "DISTRIBUTION.json").write_bytes(data["DISTRIBUTION.json"])
    r = {
        "sha256": sha,
        "bytes": len(b),
        "members": len(data),
        "deterministic": True,
        "commit": commit,
    }
    (d / "PACKAGE.json").write_text(json.dumps(r, indent=2) + "\n")
    print(json.dumps(r))


if __name__ == "__main__":
    main()

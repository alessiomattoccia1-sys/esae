# SPDX-License-Identifier: Apache-2.0
"""Publish original computed results, not institutional raw series or databases."""

from pathlib import Path
import json, hashlib, re, shutil
from research_core import now

ARTIFACTS = [
    "FSIE-001_REPORT.html",
    "FSIE-001_RESULTS.json",
    "FSIE-001_FINDINGS.csv",
    "FSIE-001_MANIFEST.json",
    "FSIE-001_METHODOLOGY.md",
    "FSIE-001_REPRODUCIBILITY.md",
]


def checked_bytes(path):
    b = Path(path).read_bytes()
    if (
        re.search(rb"/(?:Users|Volumes)/[A-Za-z0-9_-]+", b)
        or re.search(rb"[\w.+-]+@(?:gmail|icloud|yahoo)\.com", b)
        or b"-----BEGIN " + b"PRIVATE KEY-----" in b
    ):
        raise ValueError("Private marker in public export")
    return b


def export(engine, job_id, destination, benchmark_path=None):
    r = engine.report(job_id)
    verification = engine.verify(job_id)
    if not verification["passed"]:
        raise ValueError("Raw replay must pass before public export")
    if any(
        s.get("http_status") != 200
        or s.get("acquisition_kind", "").startswith("manual")
        for s in r["sources"]
    ):
        raise ValueError(
            "Public study requires verified real official HTTP acquisition"
        )
    dest = Path(destination)
    if dest.is_symlink():
        raise ValueError("No linked public destination")
    dest.mkdir(parents=True, exist_ok=True)
    files = {}
    for name in ARTIFACTS:
        b = checked_bytes(engine.store.directory(job_id) / name)
        files[name] = b
    benchmark = None
    if benchmark_path:
        b = checked_bytes(benchmark_path)
        benchmark = json.loads(b)
        if (
            benchmark.get("passed") is not True
            or benchmark.get("classification")
            != "SYNTHETIC_TECHNICAL_ONLY_NOT_FINANCIAL_RESEARCH"
        ):
            raise ValueError("Qualified explicitly synthetic benchmark required")
        files["FSIE-BENCHMARK.json"] = b
    summary = {
        "status": "QUALIFIED",
        "engine_version": "0.1.0",
        "experiment": "FSIE-001",
        "analysis_sha256": r["analysis_sha256"],
        "completed_at": r["completed_at"],
        "period": r["study_period"],
        "coverage": r["coverage"],
        "series_count": len(r["series_metadata"]),
        "verification": verification,
        "yield_curve": {
            k: {
                "valid_sessions": v["valid_sessions"],
                "inverted_sessions": v["inverted_sessions"],
                "episodes": len(v["episodes"]),
                "distribution_bp": v["distribution_bp"],
            }
            for k, v in r["yield_curve"].items()
        },
        "lag_test_summary": r["lag_test_summary"],
        "contemporaneous_correlations": r["contemporaneous_correlations"],
        "anomaly_flags": len(r["anomalies"]),
        "anomaly_examples": r["anomalies"][:6],
        "money_market_supplement": r["money_market_supplement"],
        "sources": [
            {
                "source_id": s["source_id"],
                "url": s["url"],
                "sha256": s["sha256"],
                "acquired_at": s["acquired_at"],
                "release_date": s.get("release_date"),
            }
            for s in r["sources"]
        ],
        "benchmark": benchmark,
        "rights_scope": "Original computed research findings and source links. No raw/full institutional time-series archive; data terms separate from software Apache2.0.",
        "nyfed_notice": r["nyfed_notice"],
        "ai_numeric_results": False,
    }
    files["summary.json"] = (json.dumps(summary, indent=2) + "\n").encode()
    files["DATA_NOTICE.md"] = (
        """# Financial source attribution and rights\n\nOriginal FSIE code is Apache 2.0. This does not relicense institutional data.\n\nTreasury: U.S. Department of the Treasury, official par-yield feeds and historical archive.\nChicago: Federal Reserve Bank of Chicago, NFCI/ANFCI and source-defined subindices. Historical indices can revise; calculations by Mattoccia Labs do not imply endorsement. Raw files and full normalized institution series are not included in this distribution. Source terms: https://www.chicagofed.org/utilities/legal-notices.\nNew York Fed: SOFR. """
        + r["nyfed_notice"]
        + """\n\nPublic results are original computed aggregates, correlations, anomaly calculations and derived Treasury spreads. Statistical values are not investment recommendations. Exact historical replay requires the manifest-matching original frozen response cache, kept locally; new official downloads may represent a different vintage.\n\nECB USD/EUR is a separately qualified connector and is not an FSIE-001 input. No ECB observations are redistributed here. FRED/ALFRED and SEC are not implemented.\n"""
    ).encode()
    for name, b in files.items():
        p = dest / name
        if p.exists() and p.read_bytes() != b:
            prior = p.read_bytes()
            saved = dest / "history" / hashlib.sha256(prior).hexdigest() / name
            saved.parent.mkdir(parents=True, exist_ok=True)
            if not saved.exists():
                saved.write_bytes(prior)
        p.write_bytes(b)
    result = {
        "passed": True,
        "exported_at": now(),
        "verification": verification,
        "raw_responses_included": False,
        "full_institutional_series_included": False,
        "files": {n: hashlib.sha256(b).hexdigest() for n, b in files.items()},
    }
    (dest / "EXPORT.json").write_text(json.dumps(result, indent=2) + "\n")
    return result

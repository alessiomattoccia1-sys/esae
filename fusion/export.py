# SPDX-License-Identifier: Apache-2.0
"""Export only qualified scientific derivatives, not whole experimental archives."""

from pathlib import Path
import hashlib, json, re, shutil
from research_core import now
from .service import FusionEngine

ARTIFACTS = [
    f"{exp}_{suffix}"
    for exp in ["FPE-001", "FPE-002"]
    for suffix in [
        "REPORT.html",
        "RESULTS.json",
        "FINDINGS.csv",
        "MANIFEST.json",
        "METHODOLOGY.md",
        "REPRODUCIBILITY.md",
    ]
]


def public_check(data):
    b = data if isinstance(data, bytes) else json.dumps(data).encode()
    if (
        re.search(
            rb"/(?:Users|Volumes)/[A-Za-z0-9_-]+|192\.168\.68\.|[\w.+-]+@(?:gmail|icloud|yahoo)\.com",
            b,
        )
        or b"-----BEGIN " + b"PRIVATE KEY-----" in b
    ):
        raise ValueError("Private marker in public export")


def export(root, qualification, destination):
    e = FusionEngine(root)
    q = json.loads(Path(qualification).read_text())
    if (
        not q.get("passed")
        or q.get("previous_runtime_files_unchanged", 0)
        + len(q.get("reviewed_shared_changes", {}))
        != 68
    ):
        raise ValueError("Full experiment and regression qualification required")
    dest = Path(destination)
    dest.mkdir(parents=True, exist_ok=True)
    summaries = {}
    output = {}
    for exp in ["FPE-001", "FPE-002"]:
        check = q[exp]
        if (
            not check["passed"]
            or not check["raw_replay"]["passed"]
            or not all(c["passed"] for c in check["independent_checks"])
        ):
            raise ValueError("Real-source replay and independent checks required")
        folder = e.store.directory(check["job_id"])
        r = e.report(check["job_id"])
        m = json.loads((folder / (exp + "_MANIFEST.json")).read_text())
        if r["results_sha256"] != check["raw_replay"]["actual_results_sha256"]:
            raise ValueError("Qualified result changed")
        m.update(
            validation_status="computationally_verified_not_new_physical_discovery",
            qualification={
                "raw_replay": check["raw_replay"],
                "independent_numeric_checks": check["independent_checks"],
                "algorithm_and_regression_tests": q["regression_tests"],
                "source_archive_redistributed": False,
            },
        )
        m.update(
            data_source=r["dataset"]["source"],
            dataset=r["dataset"],
            dataset_version={
                "source_sha256": {v["url"]: v["sha256"] for v in m["sources"]},
                "upstream_ingestion": sorted(
                    {
                        v["identity"]["group_attributes"].get("ingested_at", "unknown")
                        for v in r.get("signals", [])
                    }
                ),
            },
            acquisition_dates=sorted({v["acquired_at"] for v in m["sources"]}),
            algorithms={
                "version": r["method_version"],
                "details": exp + "_METHODOLOGY.md",
            },
            parameters=r["configuration"],
            exporter_source_sha256=hashlib.sha256(
                Path(__file__).read_bytes()
            ).hexdigest(),
        )
        m["output_artifacts_sha256"] = {
            name: hashlib.sha256((folder / name).read_bytes()).hexdigest()
            for name in [
                n
                for n in ARTIFACTS
                if n.startswith(exp) and not n.endswith("MANIFEST.json")
            ]
            + [f["file"] for f in m["figures"]]
        }
        for name in ARTIFACTS:
            if name.startswith(exp):
                output[name] = (
                    (json.dumps(m, indent=2) + "\n").encode()
                    if name.endswith("MANIFEST.json")
                    else (folder / name).read_bytes()
                )
        for f in m["figures"]:
            output[f["file"]] = (folder / f["file"]).read_bytes()
        summaries[exp] = {
            "experiment": exp,
            "title": r["title"],
            "counts": r["counts"],
            "dataset": r["dataset"],
            "configuration": r["configuration"],
            "completed_at": m["completed_at"],
            "git_commit": m["git_commit_at_execution"],
            "analysis_sha256": r["results_sha256"],
            "findings": r["findings"],
            "performance": m["performance"],
            "independent_verification": True,
            "raw_replay": check["raw_replay"],
            "data_derivative_license": r["data_derivative_license"],
            "limitations": r["limitations"],
        }
        if exp == "FPE-001":
            summaries[exp]["measurements"] = [
                {
                    "shot_id": s["identity"]["shot_id"],
                    "diagnostic": s["identity"]["diagnostic"],
                    "unit": s["identity"]["unit"],
                    "samples": s["quality"]["samples"],
                    "valid": s["quality"]["valid_samples"],
                    "mean": s["statistics"]["mean"],
                    "rms": s["statistics"]["rms"],
                    "peak_hz": s["spectral"]["dominant_non_dc_hz"],
                    "frequency_half_bin_hz": s["spectral"][
                        "frequency_resolution_half_bin_hz"
                    ],
                    "mean_interval": s["mean_block_interval"],
                    "candidate_events": len(s.get("events", [])),
                    "event_threshold_sensitivity": s["event_threshold_sensitivity"],
                    "source_ingestion": s["identity"]["group_attributes"].get(
                        "ingested_at"
                    ),
                    "source_commit": s["identity"]["group_attributes"].get(
                        "commit_url"
                    ),
                }
                for s in r["signals"]
            ]
        else:
            summaries[exp]["measurements"] = [
                {
                    "shot_id": s["identity"]["shot_id"],
                    "shape": s["baseline"]["shape"],
                    "valid_pixels": s["baseline"]["valid_pixels"],
                    "mean_raw": s["baseline"]["raw_intensity"]["mean"],
                    "centroid_detector_px": s["baseline"]["centroid_detector_px"],
                    "method_sensitivity": s["robustness"],
                }
                for s in r["images"]
            ]
    output["summary.json"] = (
        json.dumps(
            {
                "status": "QUALIFIED",
                "engine_version": "0.1.0",
                "experiments": summaries,
                "findings": 6,
                "original_code_license": "Apache-2.0",
                "raw_archive_included": False,
                "simulation_used_as_experiment": False,
            },
            indent=2,
        )
        + "\n"
    ).encode()
    output["DATA_NOTICE.md"] = ("""# Scientific artifact licenses and attribution

Original FPRE software: Apache License 2.0.
FPE-001 results, figures and report: UKAEA FAIR-MAST and source contributors, modified by Mattoccia Labs (selected diagnostics/time/channel, unit normalization, statistics and visualizations), CC BY-SA 4.0, https://creativecommons.org/licenses/by-sa/4.0/ . No source endorsement.
FPE-002 results, figures and report: STFC eData OMEAG_SAI-23A, DOI https://doi.org/10.5286/edata/944, all source authors listed in FPE-002_RESULTS.json dataset metadata, modified by Mattoccia Labs (generic detector statistics, fixed background/ROI processing and explicitly scaled images), CC BY 4.0, https://creativecommons.org/licenses/by/4.0/ . No source endorsement.

The archive and operating/performance data are not redistributed. Exact acquired-vintage offline replay requires the manifest-matching original cache. The public release contains derived reports, identifiers, hashes and original reproduction code. No simulated data is presented as experimental measurement. Computation does not establish a new physical discovery or physical calibration.
""").encode()
    # Explicit first-party output list; preserve prior evidence if exported again.
    hashes = {}
    for name, b in output.items():
        public_check(b)
        p = dest / name
        if p.is_symlink():
            raise ValueError("Symlink export rejected")
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() and p.read_bytes() != b:
            old = p.read_bytes()
            saved = dest / "history" / hashlib.sha256(old).hexdigest() / name
            saved.parent.mkdir(parents=True, exist_ok=True)
            if not saved.exists():
                saved.write_bytes(old)
        p.write_bytes(b)
        hashes[name] = hashlib.sha256(b).hexdigest()
    result = {
        "passed": True,
        "exported_at": now(),
        "artifacts": hashes,
        "experiments": {k: v["analysis_sha256"] for k, v in summaries.items()},
        "raw_archive_included": False,
    }
    (dest / "EXPORT.json").write_text(json.dumps(result, indent=2) + "\n")
    return result

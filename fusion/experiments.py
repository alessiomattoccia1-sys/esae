# SPDX-License-Identifier: Apache-2.0
"""Two independent experimental analyses, share provenance and validation only."""

from pathlib import Path
import json, zipfile, hashlib, math, time
import numpy as np
from .mast import MastConnector
from .acquisition import STFC_ITEM, STFC_ZIP, LICENSE_MAST, LICENSE_STFC
from .signals import analyze_signal, describe, clean, pair_correlation
from .inertial import inspect_archive, load_hdf, analyze_image
from .physics import normalize_signal


def fingerprint(report):
    report = clean(report)
    report["results_sha256"] = hashlib.sha256(
        json.dumps(
            report, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()
    return report


def magnetic(cache, folder, config, progress=None, cancel=None):
    start = time.monotonic()
    mast = MastConnector(cache)
    candidates, cat, total = mast.select(
        config["shot_count"], config.get("offline", False)
    )
    selection = []
    excluded = []
    results = []
    pairs = []
    signals = {}
    acquisition_seconds = 0.0
    analysis_seconds = 0.0
    rawdir = Path(folder) / "normalized"
    rawdir.mkdir(parents=True, exist_ok=True)
    for candidate in candidates:
        if len(selection) >= config["shot_count"]:
            break
        if cancel and cancel():
            raise InterruptedError("Cancelled explicitly between bounded acquisitions")
        shot = candidate["shot_id"]
        acquired = []
        try:
            for diagnostic in [
                "magnetics/ip",
                "magnetics/b_field_pol_probe_omv_voltage",
            ]:
                tick = time.monotonic()
                t, x, identity = mast.signal(
                    shot,
                    diagnostic,
                    Path(folder) / "selected-zarr",
                    config["window_seconds"],
                    2,
                    config.get("offline", False),
                )
                acquisition_seconds += time.monotonic() - tick
                identity["shot_catalog_metadata"] = candidate
                path = rawdir / f'{shot}-{diagnostic.split("/")[-1]}.npz'
                np.savez_compressed(path, time=t, value=x)
                acquired.append((t, x, identity))
        except (ValueError, OSError) as e:
            excluded.append({"shot_id": shot, "reason": str(e)[:300]})
            continue
        selection.append(candidate)
        for t, x, identity in acquired:
            tick = time.monotonic()
            r = analyze_signal(t, x, identity)
            analysis_seconds += time.monotonic() - tick
            results.append(r)
            signals[(shot, identity["diagnostic"])] = (t, x, identity)
        t1, x1, m1 = acquired[0]
        t2, x2, m2 = acquired[1]
        nt1, nx1, _ = normalize_signal(t1, x1, m1)
        nt2, nx2, _ = normalize_signal(t2, x2, m2)
        pairs.append(
            {
                "shot_id": shot,
                "diagnostics": [m1["diagnostic"], m2["diagnostic"]],
                "result": pair_correlation(nt1, nx1, nt2, nx2),
            }
        )
        if progress:
            progress(
                "Characterizing magnetic diagnostics",
                len(selection),
                config["shot_count"],
            )
    if len(selection) < min(5, config["shot_count"]):
        raise ValueError(
            "Insufficient comparable accessible shots; no successful FPE-001 claim"
        )
    counts = {
        "catalog_shots": total,
        "selected_shots": len(selection),
        "selected_diagnostic_types": 2,
        "signals": len(results),
        "samples": sum(r["quality"]["samples"] for r in results),
        "valid_samples": sum(r["quality"]["valid_samples"] for r in results),
        "candidate_shots_examined": len(selection) + len(excluded),
        "excluded_candidates": len(excluded),
        "computed_signals": sum(r["status"] == "computed" for r in results),
        "inconclusive_signals": sum(r["status"] != "computed" for r in results),
    }
    cross = []
    for diag in ["magnetics/ip", "magnetics/b_field_pol_probe_omv_voltage"]:
        relevant = [r for r in results if r["identity"]["diagnostic"] == diag]
        cross.append(
            {
                "diagnostic": diag,
                "unit": relevant[0]["identity"]["unit"],
                "shot_ids": [r["identity"]["shot_id"] for r in relevant],
                "rms_distribution": describe(
                    [r["statistics"]["rms"] for r in relevant]
                ),
                "mean_distribution": describe(
                    [r["statistics"]["mean"] for r in relevant]
                ),
                "dominant_frequency_distribution_hz": describe(
                    [
                        r.get("spectral", {}).get("dominant_non_dc_hz", np.nan)
                        for r in relevant
                    ]
                ),
                "event_counts": [
                    {
                        "shot_id": r["identity"]["shot_id"],
                        "count": len(r.get("events", [])),
                    }
                    for r in relevant
                ],
                "shots_with_candidate_events": sum(
                    bool(r.get("events")) for r in relevant
                ),
                "denominator_shots": len(relevant),
                "interpretation": "Same catalog campaign/shape/current category, not controlled identical experiments; no phase alignment, performance ranking or causal inference.",
            }
        )
    figures = []
    findings = [
        {
            "id": "MCF-01",
            "experiment": "FPE-001",
            "kind": "DERIVED",
            "title": "Coverage and quality of comparable MAST diagnostics",
            "method": "Catalog selection fixed before values; explicit unit conversion and finite/regular-sampling checks",
            "numerical_result": counts,
            "unit": "shots/signals/samples",
            "evidence": ["selection", "signals.quality"],
            "uncertainty": "Missingness is counted; source calibration uncertainty unknown",
            "verification": "computationally_verified",
            "limits": "Source Level2 diagnostic processing release retained; instrument/physics validation is not asserted.",
        },
        {
            "id": "MCF-02",
            "experiment": "FPE-001",
            "kind": "DERIVED",
            "title": "Temporal and spectral characterization of source measurements",
            "method": "Finite contiguous regular segments, SciPy FFT/Welch/STFT, explicit Hann/overlap/resolution, derivative excursions",
            "numerical_result": [
                {
                    "shot_id": r["identity"]["shot_id"],
                    "diagnostic": r["identity"]["diagnostic"],
                    "unit": r["identity"]["unit"],
                    "rms": r["statistics"].get("rms"),
                    "peak_hz": r.get("spectral", {}).get("dominant_non_dc_hz"),
                    "resolution_hz": r.get("spectral", {}).get("frequency_bin_hz"),
                    "candidate_events": len(r.get("events", [])),
                }
                for r in results
            ],
            "unit": "A/V,Hz,s",
            "evidence": [
                "signals.spectral",
                "signals.events",
                "signals.filter_sensitivity",
            ],
            "uncertainty": "Frequency-bin and time-grid resolution; window/filter/threshold sensitivity; no total calibration error",
            "verification": "computationally_verified",
            "limits": "Peaks and transients are not identified MHD modes, ELMs or disruptions.",
        },
        {
            "id": "MCF-03",
            "experiment": "FPE-001",
            "kind": "STATISTICAL",
            "title": "Cross-shot spread and parameter sensitivity",
            "method": "Report all selected shots and all declared spectral/filter/event settings; same-shot descriptive correlation only",
            "numerical_result": cross,
            "unit": "A/V,Hz,counts",
            "evidence": ["cross_shot", "within_shot_correlations"],
            "uncertainty": "Observed cross-shot dispersion and method sensitivity; small selected cohort, not population inference",
            "verification": "computationally_verified",
            "limits": "Differences may reflect unmeasured experimental settings or processing; no causal plasma conclusion.",
        },
    ]
    result = fingerprint(
        {
            "experiment": "FPE-001",
            "engine_version": "0.1.0",
            "method_version": "fpre-mcf-1.0",
            "title": "Magnetic Plasma Dynamics — Quantitative Analysis of Public MAST Discharges",
            "dataset": {
                "source": "UKAEA FAIR-MAST",
                "catalog_url": cat["url"],
                "catalog_sha256": cat["sha256"],
                "license": LICENSE_MAST,
                "data_level": 2,
                "type": "real_experimental_diagnostic_data_source_processed",
            },
            "configuration": {k: v for k, v in config.items() if k != "offline"},
            "selection": selection,
            "excluded": excluded,
            "counts": counts,
            "signals": results,
            "cross_shot": cross,
            "within_shot_correlations": pairs,
            "findings": findings,
            "limitations": [
                "Legacy mastapp JSON service timed out; current official documentation points to the public S3 Parquet catalogs actually used.",
                "Level2 magnetics metadata identifies source ingestion commit/release; a processed diagnostic is not a direct equilibrium reconstruction.",
                "No interpolation, missing-to-zero conversion or sorting of bad time axes; spectral analysis uses declared contiguous segments.",
                "Sample deliberately matches catalog categories, not all physical operating conditions; no cross-shot phase alignment.",
                "Source release documents ongoing corrections; quality metrics and source-version metadata accompany every result.",
                "No new instability, confinement improvement, disruption forecast, physical law or causal effect established.",
                "Statistical block intervals and discretization/sensitivity do not quantify unknown instrument/calibration systematics.",
            ],
            "ai_used_for_numbers": False,
            "data_derivative_license": "CC-BY-SA-4.0",
        }
    )
    return result, {
        "acquisition_selection_seconds": acquisition_seconds,
        "analysis_seconds": analysis_seconds,
        "total_before_report_seconds": time.monotonic() - start,
    }


def inertial(cache, folder, config, progress=None, cancel=None):
    start = time.monotonic()
    tick = time.monotonic()
    metadata_path, item = cache.fetch(STFC_ITEM, config.get("offline", False))
    archive_path, archive = cache.fetch(STFC_ZIP, config.get("offline", False))
    acquisition = time.monotonic() - tick
    metadata = json.loads(metadata_path.read_text())
    rights = [v["value"] for v in metadata["metadata"].get("dc.rights.uri", [])]
    if LICENSE_STFC not in rights:
        raise ValueError("STFC per-item data license not verified")
    tick = time.monotonic()
    inventory = inspect_archive(archive_path)
    parsing = time.monotonic() - tick
    selected = sorted(
        [r for r in inventory["entries"] if r["selected_raw_image"]],
        key=lambda r: r["file"],
    )
    images = []
    excluded = []
    analysis = 0.0
    rawdir = Path(folder) / "detector-inputs"
    rawdir.mkdir(parents=True, exist_ok=True)
    if len(selected) > 20:
        raise ValueError("HDF sample bound exceeded; explicit study amendment required")
    with zipfile.ZipFile(archive_path) as z:
        for i, row in enumerate(selected):
            if cancel and cancel():
                raise InterruptedError("Cancelled between detector files")
            shot = row["shot_id"]
            dest = rawdir / (str(shot) + ".hdf")
            digest = hashlib.sha256()
            with z.open(row["file"]) as source, dest.open("wb") as out:
                size = 0
                while block := source.read(131072):
                    size += len(block)
                    if size > row["bytes"]:
                        raise ValueError("ZIP member expansion changed")
                    digest.update(block)
                    out.write(block)
            tick = time.monotonic()
            array, hdfmeta = load_hdf(dest, rawdir / str(shot))
            parsing += time.monotonic() - tick
            identity = {
                "shot_id": shot,
                "file": row["file"],
                "member_sha256": digest.hexdigest(),
                "diagnostic": "SLOS-TRXI raw detector frame",
                "source_doi": "10.5286/edata/944",
                "license": LICENSE_STFC,
                "hdf": hdfmeta,
                "measured_quantity": "stored gel_raw detector values",
                "calibration_status": "Detector-scale metadata not used as object-plane calibration; no physical conversion",
                "source_category": "real_experimental_detector_array",
            }
            tick = time.monotonic()
            r = analyze_image(array, identity)
            analysis += time.monotonic() - tick
            # Display arrays are stored separately; JSON profiles/metrics retain numeric measurements.
            thumb = np.asarray(r.pop("display_raw"))
            np.save(rawdir / (str(shot) + "-display.npy"), thumb, allow_pickle=False)
            r["display_file"] = str(shot) + "-display.npy"
            images.append(r)
            if progress:
                progress("Characterizing raw detector frames", i + 1, len(selected))
    if not images:
        raise ValueError("No interpretable raw HDF detector arrays; FPE-002 incomplete")
    counts = dict(
        inventory["counts"],
        raw_images_analyzed=len(images),
        selected_measurements=len(images),
        detector_pixels=sum(r["baseline"]["pixels"] for r in images),
        valid_detector_pixels=sum(r["baseline"]["valid_pixels"] for r in images),
        source_processed_PSL_arrays_not_analyzed=len(images),
        inconclusive_images=sum(r["baseline"]["status"] != "computed" for r in images),
    )
    findings = [
        {
            "id": "ICF-01",
            "experiment": "FPE-002",
            "kind": "OBSERVED",
            "title": "Verified experimental diagnostic inventory",
            "method": "Bounded ZIP path/type/size validation, hashes, original HDF4 layout inspection",
            "numerical_result": counts,
            "unit": "files/arrays/pixels",
            "evidence": ["inventory", "images.identity"],
            "uncertainty": "Inventory counts exact for the acquired archive; calibration completeness not assumed",
            "verification": "computationally_verified",
            "limits": "Only raw detector image arrays analyzed numerically; target/operating/performance and processed nuclear diagnostics excluded.",
        },
        {
            "id": "ICF-02",
            "experiment": "FPE-002",
            "kind": "DERIVED",
            "title": "Raw detector-frame intensity and coordinate characterization",
            "method": "Original gel_raw arrays, finite pixels, declared border background and positive detector-intensity weights",
            "numerical_result": [
                {
                    "shot_id": r["identity"]["shot_id"],
                    "shape": r["baseline"]["shape"],
                    "mean_raw": r["baseline"]["raw_intensity"]["mean"],
                    "invalid_pixels": r["baseline"]["invalid_pixels"],
                    "centroid_detector_px": r["baseline"]["centroid_detector_px"],
                }
                for r in images
            ],
            "unit": "uncalibrated detector units and detector pixels",
            "evidence": ["images.baseline", "images.source_array_sha256"],
            "uncertainty": "Pixel-grid half-pixel descriptor; total calibration/systematic error not available",
            "verification": "computationally_verified",
            "limits": "No physical plasma size, object-plane geometry, temperature, yield or implosion performance reconstructed.",
        },
        {
            "id": "ICF-03",
            "experiment": "FPE-002",
            "kind": "DERIVED",
            "title": "Same-measurement preprocessing robustness",
            "method": "All6fixed combinations of borderquantile25/50/75 and whole/central80percentROI; no outcome optimization",
            "numerical_result": [
                {"shot_id": r["identity"]["shot_id"], "sensitivity": r["robustness"]}
                for r in images
            ],
            "unit": "detector pixels; sensitivity range, not confidence interval",
            "evidence": ["images.sensitivity"],
            "uncertainty": "Observed parameter-sensitivity spread; not total physical uncertainty",
            "verification": "computationally_verified",
            "limits": "Explicit substitution for cross-implosion/performance comparison. No operating-parameter joins or best-performing shot ranking.",
        },
    ]
    authors = [
        v["value"] for v in metadata["metadata"].get("dc.contributor.author", [])
    ]
    issued = [v["value"] for v in metadata["metadata"].get("dc.date.issued", [])]
    result = fingerprint(
        {
            "experiment": "FPE-002",
            "engine_version": "0.1.0",
            "method_version": "fpre-icf-1.0",
            "title": "Inertial Fusion Diagnostics — Quantitative Assessment of Published Experimental Measurements",
            "dataset": {
                "source": "STFC eData OMEAG_SAI-23A",
                "doi": "10.5286/edata/944",
                "item_uuid": metadata["uuid"],
                "authors": authors,
                "issued": issued,
                "archive_sha256": archive["sha256"],
                "archive_bytes": archive["bytes"],
                "license": LICENSE_STFC,
                "type": "real_experimental_detector_data",
            },
            "configuration": {k: v for k, v in config.items() if k != "offline"},
            "inventory": inventory,
            "counts": counts,
            "images": images,
            "excluded": excluded,
            "findings": findings,
            "limitations": [
                "Instrument detector values and pixel coordinates only; no conversion to physical plasma dimensions or radiometric quantities.",
                "Processed PSL images, neutron/proton performance diagnostics, target specifications and operating parameters are not analyzed.",
                "Raw gel and source-processed PSL arrays remain distinct; originals remain unchanged.",
                "No absolute yield, temperature, areal density, ignition, implosion model or performance optimization inferred.",
                "ICF03 is methodological robustness of the same measurements, explicitly replacing cross-implosion comparison.",
                "Sensor full scale, calibration errors and systematic uncertainties remain unknown.",
            ],
            "ai_used_for_numbers": False,
            "data_derivative_license": "CC-BY-4.0",
        }
    )
    return result, {
        "acquisition_cached_seconds": acquisition,
        "parsing_seconds": parsing,
        "analysis_seconds": analysis,
        "total_before_report_seconds": time.monotonic() - start,
    }

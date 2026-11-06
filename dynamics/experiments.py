# SPDX-License-Identifier: Apache-2.0
"""Three separated studies: historical IDF, source-status AERPAW, synthetic agents."""

from pathlib import Path
from collections import defaultdict
import json, hashlib, time, resource, itertools
import numpy as np, pandas as pd
from scipy.stats import chi2
from .flights import acquire_idf, aerpaw_status
from .validation import (
    MODELS,
    HORIZONS,
    windows,
    predict_windows,
    summarize,
    calibrate,
    fit_ensemble,
    mix,
    bootstrap,
    motion_features,
)
from .mathematical import GaussianHMM, registry, monte_carlo
from .simulation import Simulation, SCENARIOS


def clean(v):
    if isinstance(v, dict):
        return {str(k): clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, np.ndarray)):
        return [clean(x) for x in v]
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, (int, np.integer)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return float(v) if np.isfinite(v) else None
    return v


def fingerprint(r):
    r = clean(r)
    numeric = {k: v for k, v in r.items() if k not in ("performance", "results_sha256")}
    r["results_sha256"] = hashlib.sha256(
        json.dumps(
            numeric, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()
    return r


def dme001(cache, folder, cfg, progress=None, cancel=None):
    tick = time.monotonic()
    flights, dataset = acquire_idf(
        cache,
        folder,
        cfg.get("flights", 30),
        cfg.get("offline", False),
        progress,
        cancel,
    )
    if len(flights) != 30:
        raise ValueError(
            "Preregistered benchmark requires all30selected valid flights; changed cohort must be documented"
        )
    normalized = Path(folder) / "normalized"
    normalized.mkdir(exist_ok=True)
    for f in flights:
        pd.DataFrame(
            {
                "time_s": f["time_s"],
                "east_m": f["position_m"][:, 0],
                "north_m": f["position_m"][:, 1],
                "source_row": f["source_rows"],
            }
        ).to_parquet(normalized / (f["flight_id"] + ".parquet"), index=False)
    acquisition = time.monotonic() - tick
    dev, val, test = flights[:12], flights[12:21], flights[21:]
    sets = {
        "development": [f["flight_id"] for f in dev],
        "validation": [f["flight_id"] for f in val],
        "test": [f["flight_id"] for f in test],
    }
    reference = np.mean(np.concatenate([f["position_m"] for f in dev]), axis=0)
    vrows = []
    trows = []
    exclusions = {}
    for name, fs, rows in [("validation", val, vrows), ("test", test, trows)]:
        for f in fs:
            values, excluded = windows(f)
            rows.extend(values)
            exclusions[f["flight_id"]] = excluded
    yval = np.asarray([x["reference"] for x in vrows])
    ytest = np.asarray([x["reference"] for x in trows])
    results = {}
    parameters = {}
    predictions = {}
    valpredictions = {}
    grids = {}
    performance = {}
    start = time.monotonic()
    for kind in MODELS:
        if cancel and cancel():
            raise InterruptedError("Cancelled between model evaluations")
        candidates = []
        for q in [0.01, 1.0, 100.0]:
            for r in [1.0, 10.0]:
                mean, cov = predict_windows(vrows, kind, q, r, reference)
                m = summarize(mean, cov, yval, vrows)
                candidates.append(
                    {
                        "q": q,
                        "r": r,
                        "ADE_m": m["ADE_m"],
                        "gaussian_NLL": m["gaussian_NLL"],
                    }
                )
        best = min(
            candidates,
            key=lambda v: (round(v["ADE_m"], 10), v["gaussian_NLL"], v["q"], v["r"]),
        )
        mean, cov = predict_windows(vrows, kind, best["q"], best["r"], reference)
        scale = calibrate(mean, cov, yval, vrows)
        parameters[kind] = dict(
            best,
            covariance_validation_scale=scale,
            observation_variance_is="empirical discrepancy hyperparameter, not physical GNSS calibration",
        )
        valpredictions[kind] = (mean, cov * scale)
        tick = time.monotonic()
        mt, ct = predict_windows(trows, kind, best["q"], best["r"], reference)
        elapsed = time.monotonic() - tick
        raw = summarize(mt, ct, ytest, trows)
        ct *= scale
        m = summarize(mt, ct, ytest, trows)
        m["uncalibrated_coverage95"] = raw["coverage95"]
        m["ADE_interval95"] = bootstrap([x["ADE_m"] for x in m["per_flight"]])
        m["coverage_interval95"] = bootstrap([x["coverage95"] for x in m["per_flight"]])
        m["covariance_validation_scale"] = scale
        results[kind] = m
        predictions[kind] = (mt, ct)
        performance[kind] = {
            "test_forecast_seconds": elapsed,
            "forecast_points": m["forecast_points"],
        }
        grids[kind] = candidates
        if progress:
            progress(
                "Comparing held-out mathematical models", len(results), len(MODELS)
            )
    weights, weight_method = fit_ensemble(
        [valpredictions[k][0] for k in MODELS], yval, vrows
    )
    mv, cv = mix(
        [valpredictions[k][0] for k in MODELS],
        [valpredictions[k][1] for k in MODELS],
        weights,
    )
    es = calibrate(mv, cv, yval, vrows)
    mt, ct = mix(
        [predictions[k][0] for k in MODELS],
        [predictions[k][1] for k in MODELS],
        weights,
    )
    ct *= es
    em = summarize(mt, ct, ytest, trows)
    em.update(
        ADE_interval95=bootstrap([x["ADE_m"] for x in em["per_flight"]]),
        coverage_interval95=bootstrap([x["coverage95"] for x in em["per_flight"]]),
        covariance_validation_scale=es,
        region="Moment-matched Gaussian ellipse approximation to a model mixture; empirical coverage measured, no guaranteed95percent mixture mass",
    )
    results["ENSEMBLE"] = em
    predictions["ENSEMBLE"] = (mt, ct)
    comparisons = []
    baseline = {f["flight_id"]: f["ADE_m"] for f in results["CV"]["per_flight"]}
    for kind, m in results.items():
        if kind == "CV":
            continue
        diff = np.array(
            [v["ADE_m"] - baseline[v["flight_id"]] for v in m["per_flight"]]
        )
        signs = np.asarray(list(itertools.product([-1, 1], repeat=len(diff))))
        null = np.mean(signs * diff, axis=1)
        p = float(np.mean(np.abs(null) >= abs(diff.mean()) - 1e-12))
        comparisons.append(
            {
                "model": kind,
                "reference": "CV",
                "mean_ADE_difference_m": float(diff.mean()),
                "paired_flight_bootstrap95": bootstrap(diff),
                "two_sided_exact_signflip_p": p,
                "units": len(diff),
                "interpretation": "Negative=lower observed ADE; conditional on independent/exchangeable flight-file groups, not all UAV platforms",
            }
        )
    order = sorted(
        range(len(comparisons)),
        key=lambda i: comparisons[i]["two_sided_exact_signflip_p"],
    )
    maximum = 0
    for rank, i in enumerate(order):
        maximum = max(
            maximum,
            min(
                1.0, (len(order) - rank) * comparisons[i]["two_sided_exact_signflip_p"]
            ),
        )
        comparisons[i]["holm_adjusted_p"] = maximum
    robustness = {}
    rng = np.random.default_rng(cfg.get("seed", 20261106))
    for condition in ["context_noise2m", "context_missing30percent"]:
        rows = []
        condition_exclusions = {}
        for f in test:
            mask = (
                rng.random(len(f["time_s"])) >= 0.3 if "missing" in condition else None
            )
            noise = (
                rng.normal(0, 2, f["position_m"].shape)
                if "noise" in condition
                else None
            )
            values, excluded = windows(f, mask, noise)
            rows.extend(values)
            condition_exclusions[f["flight_id"]] = excluded
        ref = np.asarray([x["reference"] for x in rows])
        values = {}
        ms = []
        cs = []
        for kind in MODELS:
            p = parameters[kind]
            a, b = predict_windows(rows, kind, p["q"], p["r"], reference)
            b *= p["covariance_validation_scale"]
            values[kind] = summarize(a, b, ref, rows)
            ms.append(a)
            cs.append(b)
        a, b = mix(ms, cs, weights)
        values["ENSEMBLE"] = summarize(a, b * es, ref, rows)
        original_index = {r["key"]: i for i, r in enumerate(trows)}
        selected = [original_index[r["key"]] for r in rows]
        matched = {
            kind: summarize(a[selected], b[selected], ref, rows)
            for kind, (a, b) in predictions.items()
        }
        robustness[condition] = {
            "kind": "Synthetic perturbation of real test context; held-out reference untouched",
            "seed": cfg.get("seed", 20261106),
            "metrics": values,
            "origins": len(rows),
            "matched_unperturbed_metrics": matched,
            "exclusions": condition_exclusions,
            "comparison": "Identical surviving origins, untouched reference and fixed validation parameters; no cohort-change confounding",
        }
    hmm = GaussianHMM(3, cfg.get("seed", 20261106)).fit(
        [motion_features(f) for f in dev]
    )
    behavior = []
    for f in test:
        probs = hmm.posterior(motion_features(f))
        valid = np.isfinite(probs).all(axis=1)
        states = np.argmax(probs[valid], axis=1)
        behavior.append(
            {
                "flight_id": f["flight_id"],
                "samples": len(probs),
                "descriptive_state_counts": np.bincount(states, minlength=3).tolist(),
                "mean_posterior_entropy": float(
                    np.mean(
                        -np.sum(
                            probs[valid] * np.log(np.maximum(probs[valid], 1e-300)),
                            axis=1,
                        )
                    )
                ),
                "not_inferred": "Intent, hostility, payload or operational suitability",
                "features": "speed, acceleration norm, absolute turn rate; offline centered derivatives, stride5; not a causal behavior predictor",
            }
        )
    preview = []
    for index, row in enumerate(trows[:10]):
        preview.append(
            {
                "flight_id": row["flight_id"],
                "origin_time_s": row["origin_time_s"],
                "actual_horizons_s": row["actual_horizons_s"],
                "observed_GNSS_reference_m": row["reference"],
                "predicted_state_m": {k: v[0][index] for k, v in predictions.items()},
                "predicted_covariance_m2": {
                    k: v[1][index] for k, v in predictions.items()
                },
            }
        )
    viewflights = [
        {
            "flight_id": f["flight_id"],
            "split": next(s for s, ids in sets.items() if f["flight_id"] in ids),
            "quality": f["quality"],
            "metadata": {
                k: v for k, v in f["metadata"].items() if k != "origin_lat_lon"
            },
            "display": {
                "time_s": f["time_s"][:: max(1, len(f["time_s"]) // 400)],
                "position_m": f["position_m"][:: max(1, len(f["time_s"]) // 400)],
                "kind": "Recorded source GNSS projected to local ENU; display stride only",
            },
        }
        for f in flights
    ]
    r = {
        "experiment": "DME-001",
        "title": "Probabilistic Flight Modeling Benchmark",
        "status": "computed",
        "kind": "REAL EXPERIMENTAL DATA",
        "dataset": dataset,
        "configuration": {k: v for k, v in cfg.items() if k != "offline"},
        "method_version": "dme-flight-1.0",
        "counts": {
            "flights_imported": len(flights),
            "valid_source_observations": sum(
                f["quality"]["valid_rows"] for f in flights
            ),
            "excluded_source_rows": sum(f["quality"]["excluded_rows"] for f in flights),
            "development_flights": len(dev),
            "validation_flights": len(val),
            "test_flights": len(test),
            "validation_origins": len(vrows),
            "test_origins": len(trows),
            "test_forecast_points_per_model": len(trows) * 3,
            "individual_models": 6,
            "ensemble_models": 1,
        },
        "splits": sets,
        "metrics": results,
        "parameters": parameters,
        "validation_grids": grids,
        "ensemble": {
            "weights": dict(zip(MODELS, weights)),
            "method": weight_method,
            "covariance": "sum(w*(within covariance + outer(mean_i-mixture_mean))); not independent-sensor fusion",
        },
        "paired_comparisons": comparisons,
        "robustness": robustness,
        "behavior_model": hmm.serialize(),
        "behavior": behavior,
        "flights": viewflights,
        "forecast_examples": preview,
        "exclusions": exclusions,
        "limits": [
            "Recorded GNSS is a noisy reference, not known true state. Physical sensor calibration is unavailable.",
            "Flights share platform and circuit; recording-day groups are unavailable. File-disjoint splits prevent row leakage but do not prove external generalization or independent days.",
            "Gaussian nominal regions and validation scaling are empirically evaluated, not guaranteed confidence coverage.",
            "ADE averages sampled1/3/5second horizons, actual timestamp offsets recorded; no interpolation.",
            "All parameter and ensemble fitting use development/validation only; test outcomes are not tuning inputs.",
        ],
    }
    return fingerprint(r), {
        "acquisition_seconds": acquisition,
        "analysis_seconds": time.monotonic() - start,
        "models": performance,
    }


def dme002(cache, folder, cfg, progress=None, cancel=None):
    from .miluv import run

    return run(cache, folder, cfg, progress, cancel)


def aerpaw_unavailable(cache, folder, cfg, progress=None, cancel=None):
    dataset = aerpaw_status(cache, cfg.get("offline", False))
    r = {
        "experiment": "DME-002",
        "title": "Observational Uncertainty & Multi-Sensor Consistency",
        "status": "SOURCE_UNAVAILABLE",
        "kind": "NO EXPERIMENTAL MEASUREMENTS ACQUIRED",
        "dataset": dataset,
        "configuration": {},
        "method_version": "dme-source-status-1.0",
        "counts": {"real_flights_analyzed": 0, "observations_analyzed": 0},
        "metrics": None,
        "findings": [],
        "limits": [
            "Official metadata available; protected API downloads returned401 and public file-stream links403 from the verified Mini.",
            "No alternate origin, authentication bypass or synthetic substitute is used.",
            "A real local archive/subset with verified schema is required before numerical DME-002 results can be claimed.",
        ],
    }
    return fingerprint(r), {"analysis_seconds": 0.0}


def dme003(cache, folder, cfg, progress=None, cancel=None):
    seed = cfg.get("seed", 20261106)
    runs = cfg.get("replicates", 20)
    if runs != 20:
        raise ValueError("Published cohort uses20predeclared seeds")
    records = []
    timings = []
    replays = {}
    start = time.monotonic()
    done = 0
    for scenario in SCENARIOS:
        for n in [1, 5, 10, 20, 50]:
            for k in range(runs):
                if cancel and cancel():
                    raise InterruptedError("Cancelled between synthetic runs")
                sim = Simulation(agents=n, scenario=scenario, seed=seed + 100 * n + k)
                tick = time.monotonic()
                r = sim.run()
                elapsed = time.monotonic() - tick
                records.append(
                    {"scenario": scenario, "seed": seed + 100 * n + k, **r["metrics"]}
                )
                timings.append(
                    {
                        "scenario": scenario,
                        "agents": n,
                        "seed": seed + 100 * n + k,
                        "total_seconds": elapsed,
                        "seconds_per_step": elapsed / 200,
                    }
                )
                if k == 0 and n == 50:
                    replays[scenario] = r
                done += 1
            if progress:
                progress("Computing synthetic multi-agent experiment", done, 500)
    grouped = []
    for scenario in SCENARIOS:
        for n in [1, 5, 10, 20, 50]:
            rows = [
                v for v in records if v["scenario"] == scenario and v["agents"] == n
            ]
            summary = {
                key: {
                    "mean": float(np.mean([v[key] for v in rows])),
                    "std": float(np.std([v[key] for v in rows], ddof=1)),
                    "interval95": bootstrap(
                        [v[key] for v in rows], unit="independent simulation seed"
                    ),
                }
                for key in [
                    "velocity_dispersion_mean",
                    "observation_coverage",
                    "terminal_displacement_mean",
                    "centroid_displacement",
                    "observation_rmse",
                ]
            }
            grouped.append(
                {
                    "scenario": scenario,
                    "agents": n,
                    "runs": len(rows),
                    "metrics": summary,
                }
            )
    sensitivity = []
    for name, values in [
        ("dt", [0.05, 0.1, 0.2]),
        ("noise", [0.1, 0.3, 0.8]),
        ("interaction", [0, 0.8, 1.6]),
        ("missing", [0, 0.3, 0.6]),
        ("observe_every", [1, 2, 5]),
    ]:
        for value in values:
            config = {
                "agents": 20,
                "scenario": "D" if name == "missing" else "C",
                "seed": seed,
                "steps": round(20 / value) if name == "dt" else 200,
                name: value,
            }
            r = Simulation(**config).run()
            sensitivity.append(
                {
                    "parameter": name,
                    "value": value,
                    "configuration": config,
                    "metrics": r["metrics"],
                }
            )
    chosen = replays["C"]
    again = Simulation(**chosen["configuration"]).run()
    exact = json.dumps(clean(chosen), sort_keys=True) == json.dumps(
        clean(again), sort_keys=True
    )
    if not exact:
        raise ValueError("Same-seed simulation not reproducible")
    r = {
        "experiment": "DME-003",
        "title": "Multi-Agent Stochastic Dynamics",
        "status": "computed",
        "kind": "SIMULATED DATA",
        "dataset": {
            "source": "Dynamics mathematical/simulation core",
            "license": "Apache-2.0 original generated synthetic data; no measured flights",
            "actual_flight_data": False,
        },
        "configuration": {k: v for k, v in cfg.items() if k != "offline"},
        "method_version": "dme-simulation-1.0",
        "counts": {
            "main_simulations": len(records),
            "robustness_simulations": len(sensitivity),
            "reproducibility_recalculations": 1,
            "maximum_agents": 50,
            "steps_per_main_run": 200,
            "seed_replicates_per_configuration": 20,
        },
        "grouped_results": grouped,
        "run_metrics": records,
        "sensitivity": sensitivity,
        "same_seed_exact": exact,
        "replays": replays,
        "monte_carlo_control": monte_carlo("RW", 2, 100, 0.1, 100, seed, 1),
        "limits": [
            "All values are synthetic abstract-system results, not real flights.",
            "Local velocity consensus and a reflecting box are defined mathematical rules, not validated aerodynamics.",
            "Different timesteps use equal physical duration but different stochastic discretizations; sensitivity is not a common-Brownian-path strong-convergence proof.",
            "Bootstrap intervals here resample independent simulation seeds, unlike temporal observations within real flights.",
        ],
    }
    return fingerprint(r), {
        "total_analysis_seconds": time.monotonic() - start,
        "run_timings": timings,
        "scaling": [
            {
                "agents": n,
                "simulations": sum(v["agents"] == n for v in timings),
                "median_total_seconds": float(
                    np.median([v["total_seconds"] for v in timings if v["agents"] == n])
                ),
                "median_step_seconds": float(
                    np.median(
                        [v["seconds_per_step"] for v in timings if v["agents"] == n]
                    )
                ),
            }
            for n in [1, 5, 10, 20, 50]
        ],
    }

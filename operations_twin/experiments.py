# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Preregistered independent temporal evaluation and hypothetical paired Monte Carlo."""

from collections import Counter
import json, time
import numpy as np
from scipy.stats import wasserstein_distance, ks_2samp
from dynamics.experiments import clean, fingerprint
from dynamics.experiment_core import stream, summary, interval, cluster_bootstrap
from .twin import MODELS, SCENARIOS, calibrate, simulate, arrivals, plan, proxy
from .discovery import sample_cohort, DAY
from .process_models import interval_candidates, arrival_diagnostics

SEED = 20261106
BOUNDS = {
    "mean_relative_error": 0.2,
    "median_relative_error": 0.2,
    "p90_relative_error": 0.25,
    "throughput_relative_error": 0.2,
    "wasserstein_over_observed_mean": 0.2,
    "variant_total_variation": 0.3,
    "proxy_rework_rate_absolute_difference": 0.1,
}
ORIGINS = {"validation": 1530403200000000, "test": 1538352000000000}


def tv(a, b):
    na = sum(a.values())
    nb = sum(b.values())
    if not na or not nb:
        return None
    return 0.5 * sum(abs(a[k] / na - b[k] / nb) for k in set(a) | set(b))


def metrics(observed, simulated, horizon=92.0):
    actual = np.array([x["duration_day"] for x in observed])
    pred = np.array([x["duration_day"] for x in simulated])
    if not len(actual) or not len(pred):
        return {
            "status": "INSUFFICIENT EVIDENCE",
            "observed_cases": len(actual),
            "simulated_cases": len(pred),
        }
    a = summary(actual)
    b = summary(pred)
    out = {
        "status": "COMPUTED RESULT",
        "observed_cases": len(actual),
        "simulated_cases": len(pred),
        "observed_duration_day": a,
        "simulated_duration_day": b,
        "mean_signed_error_day": b["mean"] - a["mean"],
        "median_signed_error_day": b["median"] - a["median"],
        "p90_signed_error_day": b["p90"] - a["p90"],
    }
    for key in ["mean", "median", "p90"]:
        out[key + "_relative_error"] = abs(b[key] - a[key]) / a[key] if a[key] else None
    # Cohort is quarter-contained: observed completion count=len(actual), not a source claim of true business closure.
    complete = sum(x["completion_day"] <= horizon for x in simulated)
    out.update(
        observed_throughput_per_day=len(actual) / horizon,
        simulated_throughput_per_day=complete / horizon,
        throughput_relative_error=abs(complete - len(actual)) / len(actual),
        wasserstein_day=wasserstein_distance(actual, pred),
        wasserstein_over_observed_mean=wasserstein_distance(actual, pred) / a["mean"],
        variant_total_variation=tv(
            Counter(tuple(x["activities"]) for x in observed),
            Counter(tuple(x["activities"]) for x in simulated),
        ),
        activity_total_variation=tv(
            Counter(a for x in observed for a in x["activities"]),
            Counter(a for x in simulated for a in x["activities"]),
        ),
        proxy_rework_rate_absolute_difference=abs(
            np.mean([proxy(x["activities"]) for x in observed])
            - np.mean([proxy(x["activities"]) for x in simulated])
        ),
        observed_change_cancel_rate=float(
            np.mean([proxy(x["activities"]) for x in observed])
        ),
        simulated_change_cancel_rate=float(
            np.mean([proxy(x["activities"]) for x in simulated])
        ),
    )
    out["validation_loss"] = (
        float(np.mean([out[k] for k in BOUNDS]))
        if all(out[k] is not None for k in BOUNDS)
        else None
    )
    return clean(out)


def prediction_intervals(model):
    result = {}
    for cat, g in model["categories"].items():
        result[cat] = {}
        for kind in MODELS:
            if kind == "semi_markov":
                durations = []
                capped = 0
                for i in range(4096):
                    a, gaps, cap = plan(model, cat, stream(SEED, 901, i, 10), kind)
                    capped += cap
                    if not cap:
                        durations.append(sum(gaps))
            else:
                pool = (
                    model["pooled_traces"]
                    if kind == "pooled_bootstrap"
                    else g["traces"]
                )
                durations = [sum(x["gaps_day"]) for x in pool]
                capped = 0
            result[cat][kind] = {
                "interval90_day": np.quantile(durations, [0.05, 0.95]).tolist(),
                "nominal_coverage": 0.9,
                "calibration_generated_samples": len(durations),
                "capped_draws_excluded": capped,
            }
    return result


def evaluate(c, model=None, replicates=20, progress=None, cancel=None):
    if not 2 <= replicates <= 100:
        raise ValueError("Replicate bound")
    tick = time.monotonic()
    cal = sample_cohort(c, "calibration")
    model = model or calibrate(cal)
    pis = prediction_intervals(model)
    evaluations = {}
    replay = None
    selected = None
    for split in ("validation", "test"):
        rows = sample_cohort(c, split)
        evaluation = {
            "cases": len(rows),
            "documents": len({x["document_group"] for x in rows}),
            "by_category": [],
            "models": {},
            "origin_us": ORIGINS[split],
            "horizon_day": 92.0,
        }
        if not rows:
            raise ValueError("No independent temporal cases")
        for cat in sorted({x["category"] for x in rows}):
            obs = [x for x in rows if x["category"] == cat]
            coverage = {}
            for kind in MODELS:
                limits = pis[cat][kind]["interval90_day"]
                actual = [x["duration_day"] for x in obs]
                coverage[kind] = {
                    **pis[cat][kind],
                    "observed_coverage": float(
                        np.mean([(limits[0] <= x <= limits[1]) for x in actual])
                    ),
                    "observed_cases": len(obs),
                }
            evaluation["by_category"].append(
                {
                    "category": cat,
                    "observed_cases": len(obs),
                    "observed_duration_day": summary([x["duration_day"] for x in obs]),
                    "document_cluster_bootstrap": cluster_bootstrap(
                        [x["duration_day"] for x in obs],
                        [x["document_group"] for x in obs],
                        SEED + 7 if split == "test" else SEED + 6,
                    ),
                    "duration_prediction_intervals": coverage,
                }
            )
        for ki, kind in enumerate(MODELS):
            reps = []
            catreps = {cat: [] for cat in model["categories"]}
            for rep in range(replicates):
                if cancel and cancel():
                    raise InterruptedError("Cancelled between simulation replicas")
                sim = simulate(
                    model,
                    arrivals(rows, ORIGINS[split]),
                    kind=kind,
                    replicate=rep + (1000 if split == "test" else 0),
                    seed=SEED,
                    record=split == "test" and kind == selected and rep == 0,
                    cancel=cancel,
                )
                m = metrics(rows, sim["cases"])
                m["unfinished_cases"] = sim["aggregate"]["unfinished_cases"]
                reps.append(m)
                for cat in catreps:
                    catreps[cat].append(
                        metrics(
                            [x for x in rows if x["category"] == cat],
                            [x for x in sim["cases"] if x["category"] == cat],
                        )
                    )
                if split == "test" and kind == selected and rep == 0:
                    replay = sim["replay"]
                if progress:
                    progress(
                        "Independent " + split + " evaluation: " + kind,
                        ki * replicates + rep + 1,
                        len(MODELS) * replicates,
                    )
            scalar = [
                *BOUNDS,
                "validation_loss",
                "mean_signed_error_day",
                "median_signed_error_day",
                "p90_signed_error_day",
                "activity_total_variation",
            ]
            entry = {
                "replicates": replicates,
                "metrics": {k: interval([x[k] for x in reps]) for k in scalar},
                "replicate_results": reps,
                "by_category": [],
            }
            for cat, values in catreps.items():
                good = [x for x in values if x.get("status") == "COMPUTED RESULT"]
                n = sum(x["category"] == cat for x in rows)
                means = {
                    k: float(np.mean([x[k] for x in good]))
                    for k in scalar
                    if good and all(x[k] is not None for x in good)
                }
                failures = [
                    k for k, b in BOUNDS.items() if means.get(k, float("inf")) > b
                ]
                if n < 100:
                    failures.append("minimum100independent_cohort_cases")
                if any(x.get("unfinished_cases", 0) for x in reps):
                    failures.append("unfinished_simulations")
                entry["by_category"].append(
                    {
                        "category": cat,
                        "observed_cases": n,
                        "mean_metrics": means,
                        "failed_acceptance_checks": failures,
                        "status": (
                            "VALIDATED SIMULATION"
                            if split == "test" and not failures
                            else (
                                "NOT VALIDATED"
                                if split == "test"
                                else "VALIDATION SET ONLY"
                            )
                        ),
                    }
                )
            evaluation["models"][kind] = entry
        evaluations[split] = evaluation
        if split == "validation":
            selected = min(
                MODELS,
                key=lambda k: evaluation["models"][k]["metrics"]["validation_loss"][
                    "mean"
                ],
            )
    test = evaluations["test"]
    selectedgroups = test["models"][selected]["by_category"]
    all_pass = all(x["status"] == "VALIDATED SIMULATION" for x in selectedgroups)
    result = {
        "experiment": "OTE-002",
        "title": "Digital Twin Calibration & Validation",
        "kind": "COMPUTED RESULT",
        "model_version": model["version"],
        "arrival_diagnostics": arrival_diagnostics(cal),
        "target_elapsed_interval_fits": interval_candidates(
            [
                g
                for r in cal
                for a, g in zip(r["activities"][1:], r["gaps_day"])
                if a == model["target_activity"]
            ]
        ),
        "calibration_cases": len(cal),
        "calibration_by_category": {
            k: g["cases"] for k, g in model["categories"].items()
        },
        "selected_on_validation_only": selected,
        "selection_criterion": "Unweighted mean of7preregistered distributional/cohort-relative errors; not confidence or a probability",
        "engineering_acceptance_bounds": {**BOUNDS, "minimum_category_test_cases": 100},
        "acceptance_scope": (
            "GLOBAL OBSERVED SUBSET VALIDATION"
            if all_pass
            else "PARTIAL OR NO VALIDATION; see per-category checks"
        ),
        "evaluations": evaluations,
        "nominal_interval_coverage": 0.9,
        "split_method": "Q1+Q2calibration,Q3validation,Q4test; entire core case inside quarter; cross-split purchase documents excluded; max3000SHA-selected heldoutcases",
        "time_model": "Observed elapsed transitions; no claim to identified service or waiting durations",
        "arrival_conditioning": "Heldout sampled-cohort arrival times are conditioned on; fixedquarter completions are simulated. This is retrospective distributional validation, not a prospective demand forecast.",
        "limits": [
            "Observed invoice endpoints and quarter containment create selection bias; results do not validate all251734cases or future periods.",
            "Only2calibration and1test 2-way matching cases: insufficient evidence, regardless of numerical fit.",
            "A semi-Markov model may lose path dependence and perform worse than whole-trace bootstrap; all results are reported.",
            "Simulation CIs condition on fitted model and fixed data; separate purchase-document bootstrap assumes cluster exchangeability.",
            "A90percent marginal duration interval is evaluated for coverage; a successful mean fit does not imply individual case prediction calibration.",
            "Administrative SRM events excluded only from the model projection; complete observed reconstruction remains unchanged.",
        ],
    }
    performance = {
        "evaluation_seconds": time.monotonic() - tick,
        "simulations": replicates * len(MODELS) * 2,
        "prediction_interval_draws_per_semi_markov_category": 4096,
    }
    return fingerprint(clean(result)), model, replay, performance


def what_if(
    c, model, replicates=50, cases=750, progress=None, cancel=None, overrides=None
):
    if not 2 <= replicates <= 100 or not 10 <= cases <= 1500:
        raise ValueError("Bounded what-if cases/replicas")
    tick = time.monotonic()
    rows = sample_cohort(c, "test", limit=cases)
    inputs = arrivals(rows, ORIGINS["test"])
    allreps = {}
    replays = {}
    timings = []
    keys = [
        "mean_cycle_day",
        "median_cycle_day",
        "p90_cycle_day",
        "throughput_per_day",
        "mean_queue_day",
        "max_queue",
        "change_cancel_rate",
        "unfinished_cases",
        "capacity",
    ]
    for si, scenario in enumerate(SCENARIOS):
        reps = []
        for rep in range(replicates):
            if cancel and cancel():
                raise InterruptedError("Cancelled between what-if replicas")
            s = simulate(
                model,
                inputs,
                resource=True,
                replicate=2000 + rep,
                scenario=scenario,
                record=rep == 0,
                cancel=cancel,
                overrides=overrides if scenario == "combined" else None,
            )
            a = s["aggregate"]
            row = {
                "mean_cycle_day": a["duration_day"]["mean"],
                "median_cycle_day": a["duration_day"]["median"],
                "p90_cycle_day": a["duration_day"]["p90"],
                "throughput_per_day": a["throughput_per_day"],
                "mean_queue_day": a["queue_wait_day"]["mean"] or 0.0,
                "max_queue": a["max_queue"],
                "change_cancel_rate": a["change_cancel_case_rate"],
                "unfinished_cases": a["unfinished_cases"],
                "capacity": a["abstract_capacity"],
                "cases_arrived": a["cases_arrived"],
            }
            reps.append(row)
            timings.append(s["seconds"])
            if rep == 0:
                replays[scenario] = s["replay"]
            if progress:
                progress(
                    "Hypothetical Monte Carlo: " + scenario,
                    si * replicates + rep + 1,
                    len(SCENARIOS) * replicates,
                )
        allreps[scenario] = {
            "kind": "HYPOTHETICAL SCENARIO",
            "status": "NOT VALIDATED",
            "parameters": s["parameters"],
            "metrics": {k: interval([x[k] for x in reps]) for k in keys},
            "replicates": reps,
        }
    base = allreps["base"]["replicates"]
    for scenario, r in allreps.items():
        r["paired_difference_from_base"] = {
            k: interval([v[k] - b[k] for v, b in zip(r["replicates"], base)])
            for k in keys
        }
    sensitivity = []
    small = inputs[: min(150, len(inputs))]
    for share in [0.02, 0.05, 0.1]:
        for utilization in [0.5, 0.7, 0.9]:
            values = []
            for rep in range(5):
                s = simulate(
                    model,
                    small,
                    resource=True,
                    replicate=5000 + rep,
                    service_fraction=share,
                    target_utilization=utilization,
                    cancel=cancel,
                )
                values.append(s["aggregate"]["duration_day"]["mean"])
            sensitivity.append(
                {
                    "cases": len(small),
                    "replicates": 5,
                    "assumed_service_fraction": share,
                    "designed_target_utilization": utilization,
                    "cycle_mean_day": interval(values),
                    "abstract_capacity": s["aggregate"]["abstract_capacity"],
                }
            )
    r = {
        "experiment": "OTE-003",
        "title": "Enterprise What-If Simulation",
        "kind": "HYPOTHETICAL SCENARIO",
        "status": "NOT VALIDATED",
        "seed": SEED,
        "cases_base": len(inputs),
        "replicates_per_scenario": replicates,
        "scenarios": allreps,
        "exploratory_combined_overrides": overrides,
        "sensitivity": sensitivity,
        "target_activity": model["target_activity"],
        "target_selection": model["target_selection"],
        "assumptions": {
            "service_fraction_of_observed_elapsed_gap": 0.05,
            "designed_utilization": 0.7,
            "horizon_day": 92.0,
            "queue": "FIFO shared abstract slots for selected activity; not inferred actual personnel",
            "disruption": "Nonpreemptive capacity hold requested day30,released no earlier than45; active work is never interrupted. Late acquisition has shorter/no hold; actual replay records it.",
            "arrivals": "Observed selected test-cohort starts; demand growth draws extra empirical starts. Not a population-wide demand forecast.",
            "common_random_numbers": "Per-case,replicate,component seeds preserve unchanged original agents across scenarios; route modifications can alter later draw correspondence.",
        },
        "limits": [
            "All resource/service parameters are explicitly hypothetical; historical elapsed intervals cannot identify them.",
            "These are model responses, not demonstrated organizational improvements or causal effects.",
            "Change/Cancel intervention changes transition weights20percent then renormalizes; it does not guarantee20percent fewer repeats.",
            "Arrival count grows30percent within the selected cohort; throughput levels cannot be extrapolated to the whole company.",
            "No money, staff productivity or guaranteed savings are calculated.",
            "Sensitivity design changes both assumed share and designed slots, rather than identifying a unique real capacity.",
        ],
    }
    perf = {
        "whatif_seconds": time.monotonic() - tick,
        "main_simulations": replicates * len(SCENARIOS),
        "sensitivity_simulations": 45,
        "simulation_seconds": summary(timings),
        "max_main_agents": max(
            v["cases_arrived"] for x in allreps.values() for v in x["replicates"]
        ),
    }
    return fingerprint(clean(r)), replays, perf

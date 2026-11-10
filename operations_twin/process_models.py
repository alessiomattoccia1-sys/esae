# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Optional explicit interval/arrival assumptions, never imposed on observed gaps."""

import math
import numpy as np
from scipy import stats
from dynamics.experiment_core import stream


def interval_candidates(values):
    x = np.asarray(values, float)
    if x.ndim != 1 or not len(x) or not np.isfinite(x).all() or np.any(x < 0):
        raise ValueError("Finite nonnegative elapsed intervals required")
    positive = x[x > 0]
    n = len(positive)
    if n > 4096:
        positive = np.sort(
            stream(20261106, 0, 0, 33).choice(positive, 4096, replace=False)
        )
    result = {
        "observations": len(x),
        "zero_mass": float(np.mean(x == 0)),
        "positive_fit_sample": len(positive),
        "default": "empirical",
        "status": "DESCRIPTIVE FIT; not a service-time identification or independent KS significance test",
        "candidates": [],
    }
    if len(positive) < 20:
        return result
    for name in ("expon", "gamma", "lognorm", "weibull_min"):
        distribution = getattr(stats, name)
        try:
            params = distribution.fit(positive, floc=0)
            ll = float(np.sum(distribution.logpdf(positive, *params)))
            if not np.isfinite(ll):
                continue
            ks = float(
                stats.kstest(positive, lambda z: distribution.cdf(z, *params)).statistic
            )
            k = len(params) - 1
            result["candidates"].append(
                {
                    "distribution": name,
                    "parameters": list(params),
                    "fixed_location": 0.0,
                    "AIC": 2 * k - 2 * ll,
                    "KS_distance": ks,
                    "zeros": "Separate empirical point mass; positive fit conditional on positive interval",
                }
            )
        except (ValueError, FloatingPointError):
            continue
    result["candidates"].sort(key=lambda x: x["AIC"])
    return result


def arrival_times(
    kind, *, horizon, count=None, rates=None, empirical=None, seed=20261106
):
    """Bounded empirical schedule or homogeneous/piecewise Poisson in days."""
    if not math.isfinite(horizon) or not 0 < horizon <= 366:
        raise ValueError("Bounded horizon required")
    rng = stream(seed, 0, 0, 44)
    if kind == "empirical":
        x = np.asarray(empirical, float)
        if (
            x.ndim != 1
            or not len(x)
            or not np.isfinite(x).all()
            or np.any(x < 0)
            or np.any(x >= horizon)
            or count is None
            or not 1 <= count <= 10000
        ):
            raise ValueError("Bounded observed empirical arrivals required")
        return np.sort(rng.choice(x, count, replace=True)).tolist()
    if kind not in ("poisson", "piecewise_poisson"):
        raise ValueError("Known arrival model required")
    if not rates or len(rates) > 366:
        raise ValueError("Explicit rates per day and boundaries required")
    result = []
    last = 0.0
    for end, rate in rates:
        if not last < float(end) <= horizon or not 0 <= float(rate) <= 1000:
            raise ValueError("Ordered finite rate intervals required")
        n = int(rng.poisson(rate * (end - last)))
        if len(result) + n > 10000:
            raise ValueError("Arrival budget exceeded")
        result.extend(rng.uniform(last, end, n).tolist())
        last = end
    if last != horizon:
        raise ValueError("Rates must cover the explicit entire horizon")
    return sorted(result)


def arrival_diagnostics(rows):
    starts = np.array([r["first_us"] for r in rows], float)
    first = 1514764800000000.0
    horizon = 181
    counts = np.histogram(
        (starts - first) / 86400000000.0, bins=np.arange(horizon + 1)
    )[0]
    mean = float(counts.mean())
    variance = float(np.var(counts, ddof=1))
    return {
        "cohort": "Endpoint-selected Q1+Q2calibration cases only; not total company demand",
        "calendar_days": horizon,
        "daily_count_mean": mean,
        "daily_count_variance": variance,
        "variance_over_mean": variance / mean if mean else None,
        "poisson_assumption": "Not imposed; calendar variation, dependence and selected-cohort censoring may violate homogeneous Poisson assumptions",
        "observed_daily_counts": counts.tolist(),
    }

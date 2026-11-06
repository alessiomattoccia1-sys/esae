# SPDX-License-Identifier: Apache-2.0
"""Domain-independent seeded experiments and uncertainty/distribution utilities."""

import math
import numpy as np
from scipy import stats


def stream(seed, replicate, agent=0, component=0):
    if any(
        not isinstance(x, (int, np.integer)) or x < 0
        for x in [seed, replicate, agent, component]
    ):
        raise ValueError("Nonnegative integer seed coordinates required")
    return np.random.default_rng(
        np.random.SeedSequence([seed, replicate, agent, component])
    )


def interval(values, level=0.95):
    x = np.asarray(values, float)
    if x.ndim != 1 or len(x) < 2 or not np.isfinite(x).all() or not 0 < level < 1:
        raise ValueError("Finite independent replicate values required")
    error = (
        stats.t.ppf((1 + level) / 2, len(x) - 1) * np.std(x, ddof=1) / np.sqrt(len(x))
    )
    return {
        "mean": float(np.mean(x)),
        "median": float(np.median(x)),
        "std": float(np.std(x, ddof=1)),
        "mean_CI95": [float(x.mean() - error), float(x.mean() + error)],
        "outcome_interval95": np.quantile(x, [0.025, 0.975]).tolist(),
        "replicates": len(x),
        "assumption": "Independent seeded simulation replicates conditional on fixed data/model; not total epistemic uncertainty",
    }


def cluster_bootstrap(values, groups, seed=20261106, repeats=499):
    x = np.asarray(values, float)
    g = np.asarray(groups)
    if len(x) != len(g) or not np.isfinite(x).all():
        raise ValueError("Finite grouped observations required")
    ids = np.unique(g)
    if len(ids) < 3:
        return {"status": "INSUFFICIENT EVIDENCE", "clusters": len(ids)}
    indices = [np.flatnonzero(g == v) for v in ids]
    rng = stream(seed, 0, 0, 91)
    means = []
    for _ in range(repeats):
        ix = np.concatenate([indices[i] for i in rng.integers(0, len(ids), len(ids))])
        means.append(np.mean(x[ix]))
    return {
        "mean": float(x.mean()),
        "mean_interval95": np.quantile(means, [0.025, 0.975]).tolist(),
        "clusters": len(ids),
        "replicates": repeats,
        "resampling_unit": "whole supplied cluster; within-cluster observations remain together",
        "limits": "Clusters may share calendar/context; interval conditional on cluster exchangeability",
    }


def summary(values):
    x = np.asarray(values, float)
    x = x[np.isfinite(x)]
    if not len(x):
        return {"n": 0, "mean": None, "median": None, "p90": None, "p95": None}
    return {
        "n": len(x),
        "mean": float(x.mean()),
        "median": float(np.median(x)),
        "p90": float(np.quantile(x, 0.9)),
        "p95": float(np.quantile(x, 0.95)),
        "minimum": float(x.min()),
        "maximum": float(x.max()),
    }


def draw_interval(rng, distribution="empirical", values=None, mean=None, shape=2.0):
    if distribution == "empirical":
        x = np.asarray(values, float)
        if not len(x) or not np.isfinite(x).all() or np.any(x < 0):
            raise ValueError("Valid empirical intervals required")
        return float(x[rng.integers(len(x))])
    if mean is None or not np.isfinite(mean) or mean < 0 or not 0.1 <= shape <= 20:
        raise ValueError("Finite interval mean and bounded shape required")
    if distribution == "exponential":
        return float(rng.exponential(mean))
    if distribution == "gamma":
        return float(rng.gamma(shape, mean / shape))
    if distribution == "lognormal":
        return (
            float(rng.lognormal(np.log(max(mean, 1e-12)) - 0.5 * shape**2, shape))
            if mean
            else 0.0
        )
    if distribution == "weibull":
        return float(rng.weibull(shape) * mean / math.gamma(1 + 1 / shape))
    raise ValueError("Known interval distribution required")

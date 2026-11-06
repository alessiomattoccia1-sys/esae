# SPDX-License-Identifier: Apache-2.0
"""Equal-flight retrospective metrics, covariance diagnostics and paired resampling."""

import numpy as np
from scipy.stats import chi2
from scipy.special import logsumexp
from scipy.optimize import minimize
from .mathematical import GaussianMotion, transition, GaussianHMM

MODELS = ("RW", "CV", "CA", "KF", "CRW", "OU")
HORIZONS = (1.0, 3.0, 5.0)


def forecast(kind, t, z, targets, q=1.0, r=1.0, reference=None):
    t = np.asarray(t, float)
    z = np.asarray(z, float)
    valid = np.isfinite(z).all(axis=1) & np.isfinite(t)
    t = t[valid]
    z = z[valid]
    if len(t) < 8 or np.max(np.diff(t)) > 2:
        raise ValueError(
            "INSUFFICIENT EVIDENCE: finite context with no long gap required"
        )
    model = GaussianMotion(
        kind, 2, q=q, r=r, reference=reference if kind == "OU" else None
    )
    d = 2
    if kind in ("CV", "CA"):
        degree = 2 if kind == "CA" else 1
        design = np.column_stack(
            [np.ones(len(t)), t - t[-1]]
            + ([0.5 * (t - t[-1]) ** 2] if degree == 2 else [])
        )
        coef = np.linalg.lstsq(design, z, rcond=None)[0]
        x = coef.reshape(-1)
        p = np.eye(model.n) * r
        p[2:4, 2:4] = np.eye(2) * 2 * r / max(np.ptp(t) ** 2, 1e-9)
        if kind == "CA":
            p[4:, 4:] = np.eye(2) * 12 * r / max(np.ptp(t) ** 4, 1e-9)
        model.initialize(x, p)
    elif kind == "RW":
        model.initialize(z[-1], np.eye(2) * r)
    else:
        x = np.zeros(model.n)
        x[:2] = z[0]
        if model.n > 2:
            x[2:4] = (z[min(4, len(z) - 1)] - z[0]) / (t[min(4, len(t) - 1)] - t[0])
        model.initialize(x, np.eye(model.n) * r * 10)
        for index in range(len(t)):
            if index:
                model.predict(t[index] - t[index - 1])
            model.update(z[index])
    means = []
    cov = []
    for target in targets:
        dt = float(target - t[-1])
        f, qp = transition(kind, 2, dt, q)
        offset = (
            (np.eye(model.n) - f) @ model.reference
            if kind == "OU"
            else np.zeros(model.n)
        )
        means.append((f @ model.x + offset)[:2])
        cov.append((f @ model.p @ f.T + qp)[:2, :2] + np.eye(2) * r)
    return np.asarray(means), np.asarray(cov)


def windows(flight, mask=None, extra_noise=None):
    t = flight["time_s"]
    x = flight["position_m"]
    rows = []
    excluded = {}
    mask = np.ones(len(t), bool) if mask is None else mask
    inputs = x if extra_noise is None else x + extra_noise
    for origin in range(20, len(t) - 1, 50):
        ix = []
        for h in HORIZONS:
            k = int(np.searchsorted(t, t[origin] + h))
            choices = [j for j in [k - 1, k] if origin < j < len(t)]
            j = min(choices, key=lambda j: abs(t[j] - t[origin] - h)) if choices else -1
            if j < 0 or abs(t[j] - t[origin] - h) > 0.12:
                ix = []
                break
            ix.append(j)
        if len(ix) != 3:
            excluded["horizon_unavailable"] = excluded.get("horizon_unavailable", 0) + 1
            continue
        if np.max(np.diff(t[origin - 19 : ix[-1] + 1])) > 2:
            excluded["source_gap_over_2s"] = excluded.get("source_gap_over_2s", 0) + 1
            continue
        context = slice(origin - 19, origin + 1)
        good = mask[context]
        if good.sum() < 8 or t[origin] - t[context][good][-1] > 1:
            excluded["insufficient_context"] = (
                excluded.get("insufficient_context", 0) + 1
            )
            continue
        rows.append(
            {
                "key": flight["flight_id"] + ":" + str(origin),
                "flight_id": flight["flight_id"],
                "origin_index": origin,
                "origin_time_s": float(t[origin]),
                "context_time": t[context][good],
                "context_position": inputs[context][good],
                "targets_time": t[ix],
                "reference": x[ix],
                "actual_horizons_s": t[ix] - t[origin],
            }
        )
    return rows, excluded


def predict_windows(rows, kind, q, r, reference):
    means = []
    cov = []
    for row in rows:
        m, p = forecast(
            kind,
            row["context_time"],
            row["context_position"],
            row["targets_time"],
            q,
            r,
            reference,
        )
        means.append(m)
        cov.append(p)
    return np.asarray(means), np.asarray(cov)


def distances(mean, cov, reference):
    diff = np.asarray(reference) - mean
    inv = np.linalg.inv(cov)
    d2 = np.einsum("...i,...ij,...j->...", diff, inv, diff)
    logdet = np.linalg.slogdet(cov)[1]
    nll = 0.5 * (2 * np.log(2 * np.pi) + logdet + d2)
    return diff, d2, nll


def summarize(mean, cov, reference, rows):
    diff, d2, nll = distances(mean, cov, reference)
    e = np.linalg.norm(diff, axis=-1)
    flights = []
    for flight in sorted({r["flight_id"] for r in rows}):
        indices = [i for i, r in enumerate(rows) if r["flight_id"] == flight]
        d = diff[indices]
        v = e[indices]
        md = d2[indices]
        flights.append(
            {
                "flight_id": flight,
                "origins": len(indices),
                "forecast_points": v.size,
                "ADE_m": float(v.mean()),
                "FDE_m": float(v[:, -1].mean()),
                "MSE_radial_m2": float(np.mean(v * v)),
                "RMSE_m": float(np.sqrt(np.mean(v * v))),
                "MAE_coordinate_m": float(np.abs(d).mean()),
                "coverage95": float(np.mean(md <= chi2.ppf(0.95, 2))),
                "gaussian_NLL": float(nll[indices].mean()),
            }
        )
    if not flights:
        raise ValueError("INSUFFICIENT EVIDENCE: no compatible forecast windows")
    result = {
        k: float(np.mean([f[k] for f in flights]))
        for k in ["ADE_m", "FDE_m", "MAE_coordinate_m", "coverage95", "gaussian_NLL"]
    }
    result["RMSE_m"] = float(np.sqrt(np.mean([f["MSE_radial_m2"] for f in flights])))
    result.update(
        flights=len(flights),
        origins=len(rows),
        forecast_points=int(e.size),
        per_flight=flights,
        coverage_status="Empirically evaluated nominal Gaussian ellipse; not validated physical measurement uncertainty",
        metric_weighting="Each full flight file has equal weight; ADE averages sampled horizons1/3/5s; FDE is last sampled horizon; RMSE is radial2D; MAE coordinatewise",
    )
    return result


def bootstrap(values, seed=20261106, repeats=999, unit="whole flight file"):
    v = np.asarray(values, float)
    if len(v) < 3:
        return {"status": "INSUFFICIENT EVIDENCE", "units": len(v)}
    rng = np.random.default_rng(seed)
    m = np.mean(v[rng.integers(0, len(v), (repeats, len(v)))], axis=1)
    return {
        "lower": float(np.quantile(m, 0.025)),
        "upper": float(np.quantile(m, 0.975)),
        "resampling_unit": unit + ", equal weight",
        "replicates": repeats,
        "seed": seed,
        "n_units": len(v),
        "assumption": (
            "Independent synthetic seeds, not real measurements"
            if "seed" in unit
            else "Flight-file exchangeability/independence not guaranteed across unreported day groups; conditional interval, limited external generalization"
        ),
    }


def calibrate(mean, cov, reference, rows):
    _, d2, _ = distances(mean, cov, reference)
    per = [
        float(d2[[i for i, r in enumerate(rows) if r["flight_id"] == f]].mean() / 2)
        for f in sorted({r["flight_id"] for r in rows})
    ]
    scale = max(float(np.mean(per)), 1e-6)
    return scale


def fit_ensemble(means, reference, rows):
    stack = np.stack(means, axis=2)
    counts = {
        f: sum(r["flight_id"] == f for r in rows)
        for f in {r["flight_id"] for r in rows}
    }
    weights = np.array([1 / (len(counts) * counts[r["flight_id"]]) for r in rows])
    k = len(means)

    def objective(w):
        d = np.einsum("nhkd,k->nhd", stack, w) - reference
        return float(
            np.sum(weights[:, None] * np.sum(d * d, axis=2)) / reference.shape[1]
        )

    fit = minimize(
        objective,
        np.ones(k) / k,
        method="SLSQP",
        bounds=[(0, 1)] * k,
        constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}],
        options={"ftol": 1e-10, "maxiter": 500},
    )
    if not fit.success:
        raise ValueError("Ensemble optimization not converged")
    w = np.maximum(fit.x, 0)
    w /= w.sum()
    return w, {
        "method": "Simplex constrained equal-flight-weighted validation squared position error; no test tuning",
        "objective_validation_m2": objective(w),
        "converged": True,
        "weights_are": "model-combination coefficients, not intent/danger probabilities",
    }


def mix(means, covariances, weights):
    mu = np.einsum("k,k...d->...d", weights, np.asarray(means))
    total = np.zeros_like(covariances[0])
    for w, m, c in zip(weights, means, covariances):
        delta = m - mu
        total += w * (c + delta[..., None] * delta[..., None, :])
    return mu, total


def motion_features(flight):
    t = flight["time_s"]
    x = flight["position_m"]
    velocity = np.gradient(x, t, axis=0)
    speed = np.linalg.norm(velocity, axis=1)
    acc = np.linalg.norm(np.gradient(velocity, t, axis=0), axis=1)
    angle = np.unwrap(np.arctan2(velocity[:, 1], velocity[:, 0]))
    turn = np.abs(np.gradient(angle, t))
    return np.column_stack([speed, acc, turn])[::5]

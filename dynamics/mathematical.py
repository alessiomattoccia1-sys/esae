# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Generic state-space processes and estimators; no aircraft-specific logic."""

from dataclasses import dataclass, asdict
from copy import deepcopy
import numpy as np
from scipy.special import logsumexp
from scipy.stats import multivariate_normal
from scipy.integrate import solve_ivp
from scipy.cluster.vq import kmeans2

IDS = ("RW", "CRW", "CV", "CA", "OU", "KF", "EKF", "PF", "HMM", "MC")


def registry():
    descriptions = [
        (
            "Random Walk",
            "Gaussian independent increments; baseline, not an aircraft model",
        ),
        (
            "Correlated Random Walk",
            "Persistent velocity with configurable reference-time correlation",
        ),
        (
            "Constant Velocity",
            "Position/velocity state; continuous white acceleration noise",
        ),
        (
            "Constant Acceleration",
            "Position/velocity/acceleration; continuous white jerk noise",
        ),
        (
            "Ornstein–Uhlenbeck",
            "Exact mean-reverting Gaussian state; abstract reference process",
        ),
        (
            "Kalman Filter",
            "Linear Gaussian recursive estimation; Joseph covariance update",
        ),
        (
            "Extended Kalman Filter",
            "User-defined differentiable nonlinear transition/observation with explicit Jacobians",
        ),
        (
            "Particle Filter",
            "Bootstrap importance filter, log weights, ESS and systematic resampling",
        ),
        (
            "Hidden Markov Model",
            "Gaussian emissions and probabilistic descriptive states; no intent labels",
        ),
        ("Monte Carlo", "Repeated generic simulations with independent spawned seeds"),
    ]
    return [
        {
            "id": i,
            "name": n,
            "version": "1.0",
            "category": (
                "estimator"
                if i in ("KF", "EKF", "PF")
                else (
                    "latent_state"
                    if i == "HMM"
                    else "experiment" if i == "MC" else "process"
                )
            ),
            "assumptions": d,
            "units": "Explicit state/observation units supplied by application; not physical sensor calibration",
            "validation": "analytical/synthetic controls; real-flight comparison only for RW,CRW,CV,CA,OU,KF",
            "limits": "Conditional mathematical model; no universal real-world validity",
        }
        for i, (n, d) in zip(IDS, descriptions)
    ]


def covariance(p, n=None):
    p = np.asarray(p, float)
    if (
        p.ndim != 2
        or p.shape[0] != p.shape[1]
        or (n is not None and p.shape != (n, n))
        or not np.isfinite(p).all()
        or not np.allclose(p, p.T, atol=1e-9)
        or np.linalg.eigvalsh(p).min() < -1e-9
    ):
        raise ValueError("Finite symmetric positive-semidefinite covariance required")
    return (p + p.T) / 2


def transition(kind, d, dt, q=1.0, rho=0.8, theta=0.5):
    if kind == "KF":
        kind = "CV"
    if (
        kind not in ("RW", "CRW", "CV", "CA", "OU")
        or d not in (1, 2, 3)
        or not np.isfinite([dt, q, rho, theta]).all()
        or not 0 < dt <= 60
        or q < 0
        or not 0 < rho < 1
        or theta <= 0
    ):
        raise ValueError("Bounded process, dimension and finite parameters required")
    eye = np.eye(d)
    if kind == "RW":
        return eye, eye * q * dt
    if kind == "OU":
        a = np.exp(-theta * dt)
        return a * eye, eye * q * (-np.expm1(-2 * theta * dt)) / (2 * theta)
    if kind == "CA":
        f = np.array([[1, dt, 0.5 * dt * dt], [0, 1, dt], [0, 0, 1.0]])
        qb = (
            np.array(
                [
                    [dt**5 / 20, dt**4 / 8, dt**3 / 6],
                    [dt**4 / 8, dt**3 / 3, dt**2 / 2],
                    [dt**3 / 6, dt**2 / 2, dt],
                ]
            )
            * q
        )
    else:
        phi = rho**dt if kind == "CRW" else 1.0
        f = np.array([[1.0, dt], [0, phi]])
        qb = np.array([[dt**3 / 3, dt * dt / 2], [dt * dt / 2, dt]]) * q
    return np.kron(f, eye), np.kron(qb, eye)


class GaussianMotion:
    def __init__(
        self, kind="CV", dimensions=2, q=1.0, r=1.0, rho=0.8, theta=0.5, reference=None
    ):
        self.kind = kind
        self.d = int(dimensions)
        self.q = float(q)
        self.r = float(r)
        self.rho = float(rho)
        self.theta = float(theta)
        if not np.isfinite(self.r) or self.r <= 0:
            raise ValueError("Positive observation variance required")
        f, _ = transition(kind, self.d, 0.1, self.q, self.rho, self.theta)
        self.n = len(f)
        self.h = np.eye(self.d, self.n)
        self.reference = (
            np.zeros(self.n) if reference is None else np.asarray(reference, float)
        )
        if self.reference.shape != (self.n,) or not np.isfinite(self.reference).all():
            raise ValueError("Matching finite reference required")
        self.initialize(np.zeros(self.n), np.eye(self.n))

    def initialize(self, state, cov=None):
        state = np.asarray(state, float)
        if state.shape != (self.n,) or not np.isfinite(state).all():
            raise ValueError("Matching finite initial state required")
        self.x = state.copy()
        self.p = covariance(np.eye(self.n) if cov is None else cov, self.n)
        self.initial = (self.x.copy(), self.p.copy())
        return self.get_state()

    def predict(self, dt, control=None):
        f, q = transition(self.kind, self.d, float(dt), self.q, self.rho, self.theta)
        offset = (
            (np.eye(self.n) - f) @ self.reference
            if self.kind == "OU"
            else np.zeros(self.n)
        )
        if control is not None:
            u = np.asarray(control, float)
            if u.shape != (self.n,) or not np.isfinite(u).all():
                raise ValueError("State-space input shape required")
            offset += u
        self.x = f @ self.x + offset
        self.p = covariance(f @ self.p @ f.T + q)
        return self.get_state()

    def observe(self):
        return self.h @ self.x

    def update(self, observation, measurement_cov=None):
        z = np.asarray(observation, float)
        if z.shape != (self.d,):
            raise ValueError("Observation shape mismatch")
        good = np.isfinite(z)
        if not good.any():
            return {"status": "INSUFFICIENT EVIDENCE", "updated": False}
        h = self.h[good]
        r = covariance(
            np.eye(self.d) * self.r if measurement_cov is None else measurement_cov,
            self.d,
        )[np.ix_(good, good)]
        innovation = z[good] - h @ self.x
        s = h @ self.p @ h.T + r
        k = np.linalg.solve(s, h @ self.p).T
        self.x += k @ innovation
        a = np.eye(self.n) - k @ h
        self.p = covariance(a @ self.p @ a.T + k @ r @ k.T)
        return {
            "status": "estimated",
            "updated": True,
            "observed_components": int(good.sum()),
        }

    def reset(self):
        self.x, self.p = (v.copy() for v in self.initial)
        return self.get_state()

    def get_state(self):
        return self.x.copy()

    def get_uncertainty(self):
        return self.p.copy()

    def serialize(self):
        return {
            "id": self.kind,
            "version": "1.0",
            "dimensions": self.d,
            "parameters": {
                "q": self.q,
                "r": self.r,
                "rho": self.rho,
                "theta": self.theta,
            },
            "state": self.x.tolist(),
            "covariance": self.p.tolist(),
            "reference": self.reference.tolist(),
            "assumptions": next(
                x["assumptions"] for x in registry() if x["id"] == self.kind
            ),
        }

    def simulate(self, steps=100, dt=0.1, seed=0):
        if not 1 <= steps <= 10000:
            raise ValueError("Simulation length bound")
        rng = np.random.default_rng(seed)
        self.reset()
        self.x += rng.multivariate_normal(np.zeros(self.n), self.p, check_valid="raise")
        states = [self.x.copy()]
        for _ in range(steps):
            self.predict(dt)
            _, q = transition(self.kind, self.d, dt, self.q, self.rho, self.theta)
            self.x += rng.multivariate_normal(np.zeros(self.n), q, check_valid="raise")
            states.append(self.x.copy())
        return np.asarray(states)


class ExtendedKalman:
    def __init__(
        self,
        state,
        p,
        transition_fn,
        transition_jacobian,
        observation_fn,
        observation_jacobian,
        q,
        r,
    ):
        self.x = np.asarray(state, float)
        self.p = covariance(p, len(self.x))
        self.f = transition_fn
        self.fj = transition_jacobian
        self.h = observation_fn
        self.hj = observation_jacobian
        self.q = covariance(q, len(self.x))
        self.r = covariance(r)
        self.initial = (self.x.copy(), self.p.copy())

    def initialize(self, state, p):
        self.x = np.asarray(state, float)
        self.p = covariance(p, len(self.x))
        self.initial = (self.x.copy(), self.p.copy())

    def predict(self, dt):
        f = np.asarray(self.fj(self.x, dt))
        new = np.asarray(self.f(self.x, dt), float)
        if new.shape != self.x.shape or not np.isfinite(new).all():
            raise ValueError("Invalid nonlinear dynamics")
        self.p = covariance(f @ self.p @ f.T + self.q * dt)
        self.x = new
        return self.x.copy()

    def observe(self):
        return np.asarray(self.h(self.x))

    def update(self, z):
        z = np.asarray(z, float)
        if not np.isfinite(z).all():
            return {"status": "INSUFFICIENT EVIDENCE"}
        h = np.asarray(self.hj(self.x))
        s = h @ self.p @ h.T + self.r
        k = np.linalg.solve(s, h @ self.p).T
        self.x += k @ (z - self.observe())
        a = np.eye(len(self.x)) - k @ h
        self.p = covariance(a @ self.p @ a.T + k @ self.r @ k.T)
        return {"status": "estimated"}

    def get_state(self):
        return self.x.copy()

    def get_uncertainty(self):
        return self.p.copy()

    def reset(self):
        self.x, self.p = (v.copy() for v in self.initial)

    def serialize(self):
        return {
            "id": "EKF",
            "state": self.x.tolist(),
            "covariance": self.p.tolist(),
            "nonlinear_functions": "Explicit trusted application callables; not serialized executable data",
        }


class ParticleFilter:
    def __init__(self, particles, transition_fn, observation_fn, q, r, seed=0):
        self.particles = np.asarray(particles, float).copy()
        if (
            self.particles.ndim != 2
            or not 16 <= len(self.particles) <= 10000
            or not np.isfinite(self.particles).all()
        ):
            raise ValueError("Bounded finite particles required")
        self.f = transition_fn
        self.h = observation_fn
        self.q = covariance(q, self.particles.shape[1])
        self.r = covariance(r)
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.weights = np.ones(len(self.particles)) / len(self.particles)
        self.initial = self.particles.copy()
        self.status = "initialized"

    def predict(self, dt):
        self.particles = np.asarray(
            self.f(self.particles, dt)
        ) + self.rng.multivariate_normal(
            np.zeros(self.particles.shape[1]), self.q * dt, len(self.particles)
        )
        return self.get_state()

    def observe(self):
        return np.asarray(self.h(self.particles))

    def update(self, z):
        z = np.asarray(z, float)
        if not np.isfinite(z).all():
            return {"status": "INSUFFICIENT EVIDENCE", "ess": self.ess()}
        residual = z - self.observe()
        logs = np.log(
            np.maximum(self.weights, np.finfo(float).tiny)
        ) + multivariate_normal.logpdf(residual, mean=np.zeros(len(z)), cov=self.r)
        normalizer = logsumexp(logs)
        if not np.isfinite(normalizer):
            self.status = "INSUFFICIENT EVIDENCE: degenerate likelihood"
            return {"status": self.status, "ess": self.ess()}
        self.weights = np.exp(logs - normalizer)
        self.weights /= self.weights.sum()
        ess = self.ess()
        resampled = ess < len(self.weights) / 2
        if resampled:
            self.resample()
        self.status = "estimated"
        return {
            "status": self.status,
            "ess_before_resample": ess,
            "resampled": resampled,
        }

    def ess(self):
        return float(1 / np.dot(self.weights, self.weights))

    def resample(self):
        n = len(self.weights)
        points = (self.rng.random() + np.arange(n)) / n
        ix = np.searchsorted(np.cumsum(self.weights), points, side="right")
        self.particles = self.particles[np.minimum(ix, n - 1)].copy()
        self.weights[:] = 1 / n

    def get_state(self):
        return self.weights @ self.particles

    def get_uncertainty(self):
        d = self.particles - self.get_state()
        return covariance((d.T * self.weights) @ d)

    def reset(self):
        self.particles = self.initial.copy()
        self.weights[:] = 1 / len(self.weights)
        self.rng = np.random.default_rng(self.seed)

    def serialize(self):
        return {
            "id": "PF",
            "particles": self.particles.tolist(),
            "weights": self.weights.tolist(),
            "rng": deepcopy(self.rng.bit_generator.state),
            "status": self.status,
        }


class GaussianHMM:
    def __init__(self, states=3, seed=0):
        if not 2 <= states <= 6:
            raise ValueError("Bounded descriptive states required")
        self.k = states
        self.seed = seed
        self.fitted = False

    def emissions(self, x):
        return np.column_stack(
            [
                -0.5
                * np.sum(
                    np.log(2 * np.pi * self.var[k])
                    + (x - self.mean[k]) ** 2 / self.var[k],
                    axis=1,
                )
                for k in range(self.k)
            ]
        )

    def fit(self, sequences, iterations=15):
        seq = [np.asarray(s, float) for s in sequences if len(s) > 10]
        x = np.concatenate(seq)
        if not np.isfinite(x).all() or len(x) < self.k * 10:
            raise ValueError("Finite development features required")
        self.location = x.mean(axis=0)
        self.scale = np.maximum(x.std(axis=0), 1e-8)
        seq = [(s - self.location) / self.scale for s in seq]
        x = np.concatenate(seq)
        self.mean, _ = kmeans2(x, self.k, minit="points", seed=self.seed)
        self.var = np.tile(np.maximum(x.var(axis=0), 0.1), (self.k, 1))
        self.a = np.full((self.k, self.k), 0.2 / (self.k - 1))
        np.fill_diagonal(self.a, 0.8)
        self.pi = np.ones(self.k) / self.k
        for _ in range(iterations):
            count = np.ones(self.k) * 1e-3
            sums = np.zeros_like(self.mean)
            squares = np.zeros_like(self.mean)
            trans = np.ones_like(self.a) * 1e-3
            initial = np.ones(self.k) * 1e-3
            for s in seq:
                b = self.emissions(s)
                n = len(s)
                alpha = np.empty_like(b)
                alpha[0] = np.log(self.pi) + b[0]
                for t in range(1, n):
                    alpha[t] = b[t] + logsumexp(
                        alpha[t - 1][:, None] + np.log(self.a), axis=0
                    )
                beta = np.zeros_like(b)
                for t in range(n - 2, -1, -1):
                    beta[t] = logsumexp(np.log(self.a) + b[t + 1] + beta[t + 1], axis=1)
                ll = logsumexp(alpha[-1])
                gamma = np.exp(alpha + beta - ll)
                gamma /= gamma.sum(axis=1, keepdims=True)
                initial += gamma[0]
                count += gamma.sum(axis=0)
                sums += gamma.T @ s
                squares += gamma.T @ (s * s)
                for t in range(n - 1):
                    trans += np.exp(
                        alpha[t][:, None] + np.log(self.a) + b[t + 1] + beta[t + 1] - ll
                    )
            self.pi = initial / initial.sum()
            self.a = trans / trans.sum(axis=1, keepdims=True)
            self.mean = sums / count[:, None]
            self.var = np.maximum(
                squares / count[:, None] - self.mean * self.mean, 0.02
            )
        self.fitted = True
        return self

    def posterior(self, x):
        if not self.fitted:
            raise ValueError("HMM needs development-only fit")
        x = np.asarray(x, float)
        good = np.isfinite(x).all(axis=1)
        out = np.full((len(x), self.k), np.nan)
        prior = self.pi.copy()
        for i, row in enumerate(x):
            if not good[i]:
                prior = self.pi.copy()
                continue
            log = (
                np.log(np.maximum(prior @ self.a, 1e-300))
                + self.emissions(((row - self.location) / self.scale)[None])[0]
            )
            prior = np.exp(log - logsumexp(log))
            out[i] = prior
        return out

    def serialize(self):
        return {
            "id": "HMM",
            "states": self.k,
            "transition": self.a.tolist(),
            "initial": self.pi.tolist(),
            "standardized_emission_means": self.mean.tolist(),
            "standardized_emission_variances": self.var.tolist(),
            "normalization_location": self.location.tolist(),
            "normalization_scale": self.scale.tolist(),
            "state_semantics": "Unordered descriptive motion-feature states, no intention labels",
            "seed": self.seed,
        }


def integrate(function, state, times, rtol=1e-8, atol=1e-10):
    times = np.asarray(times, float)
    if (
        not np.isfinite(times).all()
        or np.any(np.diff(times) <= 0)
        or len(times) < 2
        or len(times) > 10001
    ):
        raise ValueError("Finite increasing bounded clock required")
    r = solve_ivp(
        function,
        (times[0], times[-1]),
        np.asarray(state, float),
        t_eval=times,
        rtol=rtol,
        atol=atol,
    )
    if not r.success or not np.isfinite(r.y).all():
        raise ValueError("Integrator did not produce valid states")
    return r.y.T


def monte_carlo(kind="RW", dimensions=2, steps=100, dt=0.1, runs=100, seed=0, q=1):
    if not 2 <= runs <= 1000 or runs * steps * dimensions > 2_000_000:
        raise ValueError("Monte Carlo resource bound")
    seeds = np.random.SeedSequence(seed).spawn(runs)
    out = []
    for s in seeds:
        model = GaussianMotion(kind, dimensions, q=q)
        out.append(model.simulate(steps, dt, int(s.generate_state(1)[0]))[-1])
    values = np.asarray(out)
    return {
        "kind": "SIMULATED DATA",
        "model": kind,
        "seed": seed,
        "runs": runs,
        "mean": values.mean(axis=0).tolist(),
        "covariance": np.atleast_2d(np.cov(values, rowvar=False)).tolist(),
        "p05": np.quantile(values, 0.05, axis=0).tolist(),
        "p95": np.quantile(values, 0.95, axis=0).tolist(),
        "terminal_states": values.tolist(),
    }

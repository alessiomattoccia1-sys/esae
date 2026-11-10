# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Abstract interacting agents, independent from civil-flight parsing or hardware."""

from copy import deepcopy
import numpy as np
from .mathematical import transition

SCENARIOS = {
    "A": "Independent Motion",
    "B": "Stochastic Motion",
    "C": "Local Interaction",
    "D": "Partial Observability",
    "E": "Heterogeneous Agents",
}


class Simulation:
    def __init__(
        self,
        agents=10,
        steps=200,
        dt=0.1,
        scenario="C",
        noise=0.3,
        interaction=0.8,
        missing=0.3,
        observation_sigma=1.0,
        seed=20261106,
        dimensions=2,
        model="CV",
        radius=12.0,
        bound=100.0,
        observe_every=1,
    ):
        if (
            isinstance(agents, bool)
            or not 1 <= agents <= 200
            or not 2 <= steps <= 2000
            or agents * steps * dimensions > 400_000
            or dimensions not in (2, 3)
            or scenario not in SCENARIOS
            or model not in ("CV", "CRW")
            or not 0.01 <= dt <= 1
            or not 0 <= noise <= 5
            or not 0 <= interaction <= 2
            or not 0 <= missing < 0.95
            or not 0.01 <= observation_sigma <= 20
            or not 1 <= radius <= 50
            or not isinstance(observe_every, int)
            or not 1 <= observe_every <= 20
            or not 10 <= bound <= 500
        ):
            raise ValueError("Bounded abstract simulation configuration required")
        self.config = {k: v for k, v in locals().items() if k != "self"}
        self.reset()

    def reset(self):
        seeds = np.random.SeedSequence(self.config["seed"]).spawn(3)
        self.rng = np.random.default_rng(seeds[0])
        self.observation_rng = np.random.default_rng(seeds[1])
        self.visibility_rng = np.random.default_rng(seeds[2])
        n = self.config["agents"]
        d = self.config["dimensions"]
        self.state = np.c_[
            self.rng.uniform(-20, 20, (n, d)), self.rng.normal(0, 2, (n, d))
        ]
        self.tick = 0
        self.paused = False
        self.records = []
        self.events = []
        self.degree_history = []
        self._record()
        return self.get_state()

    def get_state(self):
        return self.state.copy()

    def _record(self):
        c = self.config
        n = c["agents"]
        d = c["dimensions"]
        obs = self.state[:, :d] + self.observation_rng.normal(
            0, c["observation_sigma"], (n, d)
        )
        visible = (
            self.visibility_rng.random(n) > c["missing"]
            if c["scenario"] == "D"
            else np.ones(n, bool)
        )
        if self.tick % c["observe_every"]:
            visible[:] = False
        obs[~visible] = np.nan
        self.records.append(
            {
                "time_s": self.tick * c["dt"],
                "true_state": self.state.copy(),
                "observed_position": obs,
                "visible": visible,
            }
        )

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def step(self):
        c = self.config
        n = c["agents"]
        d = c["dimensions"]
        dt = c["dt"]
        if self.paused or self.tick >= c["steps"]:
            return False
        f, q = transition(
            c["model"], d, dt, 0 if c["scenario"] == "A" else c["noise"] ** 2
        )
        next = self.state @ f.T
        if c["scenario"] == "E":
            for kind, mask in [
                ("CV", np.arange(n) % 2 == 0),
                ("CRW", np.arange(n) % 2 == 1),
            ]:
                ff, qq = transition(kind, d, dt, c["noise"] ** 2)
                next[mask] = self.state[mask] @ ff.T + self.rng.multivariate_normal(
                    np.zeros(2 * d), qq, int(mask.sum())
                )
        elif c["noise"] and c["scenario"] != "A":
            next += self.rng.multivariate_normal(np.zeros(2 * d), q, n)
        if c["scenario"] == "C":
            distance = np.linalg.norm(
                self.state[:, None, :d] - self.state[None, :, :d], axis=2
            )
            adj = (distance < c["radius"]) & (~np.eye(n, dtype=bool))
            degree = adj.sum(axis=1)
            self.degree_history.append(float(degree.mean()))
            mean = np.divide(
                adj @ self.state[:, d:],
                degree[:, None],
                out=self.state[:, d:].copy(),
                where=degree[:, None] > 0,
            )
            next[:, d:] += dt * c["interaction"] * (mean - self.state[:, d:])
        outside = np.abs(next[:, :d]) > c["bound"]
        if outside.any():
            folded = (next[:, :d] + c["bound"]) % (4 * c["bound"])
            sign = np.where(folded <= 2 * c["bound"], 1.0, -1.0)
            next[:, :d] = np.where(
                folded <= 2 * c["bound"], folded - c["bound"], 3 * c["bound"] - folded
            )
            next[:, d:] *= sign
            self.events.append(
                {
                    "tick": self.tick + 1,
                    "kind": "abstract_reflecting_boundary",
                    "agent_ids": np.where(outside.any(axis=1))[0].tolist(),
                }
            )
        if not np.isfinite(next).all():
            raise ValueError("Numerically invalid simulation; no silent repair")
        self.state = next
        self.tick += 1
        self._record()
        return True

    def run(self, cancel=None):
        while self.tick < self.config["steps"] and not self.paused:
            if cancel and cancel():
                raise InterruptedError(
                    "Simulation cancelled between deterministic ticks"
                )
            self.step()
        return self.result()

    def result(self):
        truth = np.stack([r["true_state"] for r in self.records])
        obs = np.stack([r["observed_position"] for r in self.records])
        visible = np.stack([r["visible"] for r in self.records])
        d = self.config["dimensions"]
        vel = truth[:, :, d:]
        vdisp = np.mean(np.var(vel, axis=1))
        pos = truth[:, :, :d]
        distance = np.linalg.norm(pos[-1] - pos[0], axis=1)
        centroid = np.mean(pos, axis=1)
        valid = visible.sum()
        error = np.linalg.norm(obs - pos, axis=2)
        variable = np.std(vel[:, :, 0], axis=0) > 1e-12
        corr = None
        if variable.sum() > 1:
            cc = np.corrcoef(vel[:, variable, 0], rowvar=False)
            corr = float(cc[~np.eye(len(cc), dtype=bool)].mean())
        metrics = {
            "agents": self.config["agents"],
            "steps_completed": self.tick,
            "simulated_seconds": self.tick * self.config["dt"],
            "valid_observations": int(valid),
            "planned_observations": int(visible.size),
            "observation_coverage": float(visible.mean()),
            "velocity_dispersion_mean": float(vdisp),
            "pairwise_velocity_correlation_mean": corr,
            "mean_local_neighbor_degree": (
                float(np.mean(self.degree_history)) if self.degree_history else None
            ),
            "scheduled_observations": self.config["agents"]
            * (self.tick // self.config["observe_every"] + 1),
            "terminal_displacement_mean": float(distance.mean()),
            "centroid_displacement": float(np.linalg.norm(centroid[-1] - centroid[0])),
            "observation_rmse": float(np.sqrt(np.nanmean(error**2))) if valid else None,
            "boundary_events": len(self.events),
            "finite_states": bool(np.isfinite(truth).all()),
            "truth_observed_estimated_distinct": True,
        }
        return {
            "kind": "SIMULATED DATA",
            "configuration": deepcopy(self.config),
            "time_s": [r["time_s"] for r in self.records],
            "agent_ids": list(range(self.config["agents"])),
            "true_state": truth.tolist(),
            "observed_position": np.where(np.isfinite(obs), obs, None).tolist(),
            "visible": visible.tolist(),
            "metrics": metrics,
            "events": deepcopy(self.events),
            "interactions": "dv_i/dt = kappa(mean_{j within radius} v_j-v_i), synchronous old-state neighbors; no pursuit, targets or tactical objective",
            "state_order": ["position_" + str(j) for j in range(d)]
            + ["velocity_" + str(j) for j in range(d)],
            "units": {
                "position": "abstract length unit",
                "velocity": "abstract length unit/s",
                "time": "s",
            },
            "limits": "Abstract reflecting box, observational noise and synthetic interactions; not a flight simulator or operational plan",
        }

    def serialize(self):
        return {
            "configuration": deepcopy(self.config),
            "tick": self.tick,
            "paused": self.paused,
            "state": self.state.tolist(),
            "rng": deepcopy(self.rng.bit_generator.state),
            "observation_rng": deepcopy(self.observation_rng.bit_generator.state),
            "visibility_rng": deepcopy(self.visibility_rng.bit_generator.state),
            "records": [
                {
                    k: (
                        np.where(np.isfinite(v), v, None).tolist()
                        if k == "observed_position"
                        else v.tolist() if isinstance(v, np.ndarray) else v
                    )
                    for k, v in r.items()
                }
                for r in self.records
            ],
            "events": deepcopy(self.events),
            "degree_history": deepcopy(self.degree_history),
        }

    @classmethod
    def restore(cls, data):
        sim = cls(**data["configuration"])
        sim.tick = int(data["tick"])
        sim.paused = bool(data["paused"])
        sim.state = np.asarray(data["state"], float)
        sim.rng.bit_generator.state = data["rng"]
        sim.observation_rng.bit_generator.state = data["observation_rng"]
        sim.visibility_rng.bit_generator.state = data["visibility_rng"]
        sim.records = [
            {
                k: (
                    np.asarray(v, dtype=bool if k == "visible" else float)
                    if k in ("true_state", "observed_position", "visible")
                    else v
                )
                for k, v in r.items()
            }
            for r in data["records"]
        ]
        sim.events = deepcopy(data["events"])
        sim.degree_history = deepcopy(data.get("degree_history", []))
        return sim

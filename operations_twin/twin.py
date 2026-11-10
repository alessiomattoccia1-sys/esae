# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Calibrated elapsed-time models and a separate explicitly hypothetical queue twin."""

from collections import Counter, defaultdict
import math, time
import numpy as np
import simpy
from scipy import stats
from dynamics.events import EventCore, EventAgent
from dynamics.experiment_core import stream, summary

MODELS = ("pooled_bootstrap", "category_bootstrap", "semi_markov")
SCENARIOS = (
    "base",
    "demand_growth",
    "capacity_reduction",
    "automation",
    "rework_reduction",
    "disruption",
    "combined",
)


def proxy(sequence):
    return any(a.startswith(("Change ", "Cancel ")) for a in sequence)


def calibrate(rows):
    if not rows:
        raise ValueError("No eligible calibration cases")
    categories = {}
    alltraces = []
    incoming = defaultdict(list)
    for cat in sorted({x["category"] for x in rows}):
        traces = []
        edges = defaultdict(lambda: defaultdict(list))
        starts = Counter()
        for row in rows:
            if row["category"] != cat:
                continue
            acts = row["activities"]
            gaps = [float(g) for g in row["gaps_day"]]
            if len(gaps) != len(acts) - 1 or any(
                g < 0 or not math.isfinite(g) for g in gaps
            ):
                raise ValueError("Ordered finite elapsed traces required")
            traces.append({"activities": acts, "gaps_day": gaps})
            starts[acts[0]] += 1
            for a, b, g in zip(acts, acts[1:], gaps):
                edges[a][b].append(g)
                incoming[b].append(g)
            edges[acts[-1]]["__END__"].append(0.0)
        alltraces.extend(traces)
        transitions = {}
        for a, values in edges.items():
            names = sorted(values)
            counts = np.array([len(values[b]) for b in names], float)
            transitions[a] = {
                "targets": names,
                "probabilities": (counts / counts.sum()).tolist(),
                "gaps_day": {b: values[b] for b in names},
            }
        categories[cat] = {
            "cases": len(traces),
            "traces": traces,
            "starts": dict(starts),
            "transitions": transitions,
        }
    candidates = [(np.mean(g), a) for a, g in incoming.items() if len(g) >= 100]
    target = (
        max(candidates)[1]
        if candidates
        else max(incoming, key=lambda a: np.mean(incoming[a]))
    )
    return {
        "version": "ote-twin-1.0",
        "calibration_cases": len(rows),
        "categories": categories,
        "pooled_traces": alltraces,
        "target_activity": target,
        "target_selection": "Largest mean incoming elapsed gap among activities with at least100calibration transitions; potential observed delay, not proven bottleneck",
        "elapsed_not_service": True,
    }


def plan(
    model, category, rng, kind="semi_markov", rework_factor=1.0, maximum_steps=512
):
    if kind not in MODELS:
        raise ValueError("Known twin model required")
    if category not in model["categories"]:
        raise ValueError("MODEL NOT VALIDATED FOR THIS CATEGORY")
    group = model["categories"][category]
    if kind != "semi_markov":
        pool = model["pooled_traces"] if kind == "pooled_bootstrap" else group["traces"]
        x = pool[int(rng.integers(len(pool)))]
        return list(x["activities"]), list(x["gaps_day"]), False
    names = list(group["starts"])
    p = np.array(list(group["starts"].values()), float)
    p /= p.sum()
    acts = [str(rng.choice(names, p=p))]
    gaps = []
    for _ in range(maximum_steps):
        options = group["transitions"].get(acts[-1])
        if not options:
            return acts, gaps, True
        names = options["targets"]
        p = np.array(options["probabilities"], float)
        p *= np.array(
            [
                rework_factor if a.startswith(("Change ", "Cancel ")) else 1.0
                for a in names
            ]
        )
        p /= p.sum()
        dest = str(rng.choice(names, p=p))
        if dest == "__END__":
            return acts, gaps, False
        values = options["gaps_day"][dest]
        g = float(values[int(rng.integers(len(values)))])
        acts.append(dest)
        gaps.append(g)
    return acts, gaps, True


def arrivals(rows, origin_us):
    return [
        {
            "id": i,
            "category": r["category"],
            "arrival_day": (r["first_us"] - origin_us) / 86400000000.0,
        }
        for i, r in enumerate(rows)
    ]


def design_capacity(
    model, arrivals_, service_fraction=0.05, target_utilization=0.7, horizon=92.0
):
    demand = 0.0
    target = model["target_activity"]
    for cat, g in model["categories"].items():
        count = sum(x["category"] == cat for x in arrivals_)
        demand += (
            count
            * np.mean(
                [
                    sum(
                        v
                        for a, v in zip(t["activities"][1:], t["gaps_day"])
                        if a == target
                    )
                    for t in g["traces"]
                ]
            )
            * service_fraction
        )
    return max(1, int(math.ceil(demand / max(horizon * target_utilization, 1e-9))))


def simulate(
    model,
    arrivals_,
    *,
    kind="semi_markov",
    seed=20261106,
    replicate=0,
    scenario="base",
    resource=False,
    service_fraction=0.05,
    target_utilization=0.7,
    capacity=None,
    horizon=92.0,
    record=False,
    cancel=None,
    overrides=None,
):
    if (
        scenario not in SCENARIOS
        or not 1 <= len(arrivals_) <= 10000
        or not 0 <= service_fraction <= 1
        or not 0.05 <= target_utilization <= 0.95
        or not 1 <= horizon <= 366
    ):
        raise ValueError("Bounded valid simulation parameters required")
    overrides = overrides or {}
    if set(overrides) - {
        "demand_growth",
        "capacity_factor",
        "service_factor",
        "rework_factor",
    }:
        raise ValueError("Known scenario parameters required")
    growth = 0.3 if scenario in ("demand_growth", "combined") else 0.0
    capfactor = (
        0.75
        if scenario == "capacity_reduction"
        else 1.25 if scenario == "combined" else 1.0
    )
    servicefactor = 0.8 if scenario in ("automation", "combined") else 1.0
    reworkfactor = 0.8 if scenario in ("rework_reduction", "combined") else 1.0
    growth = float(overrides.get("demand_growth", growth))
    capfactor = float(overrides.get("capacity_factor", capfactor))
    servicefactor = float(overrides.get("service_factor", servicefactor))
    reworkfactor = float(overrides.get("rework_factor", reworkfactor))
    if (
        not 0 <= growth <= 1
        or not 0.25 <= capfactor <= 2
        or not 0.1 <= servicefactor <= 2
        or not 0.1 <= reworkfactor <= 1
    ):
        raise ValueError("Scenario modification bound")
    inputs = [dict(x) for x in arrivals_]
    for j in range(int(round(len(inputs) * growth))):
        x = dict(
            arrivals_[int(stream(seed, replicate, j, 77).integers(len(arrivals_)))]
        )
        x["id"] = len(arrivals_) + j
        inputs.append(x)
    if not all(0 <= x["arrival_day"] < horizon for x in inputs):
        raise ValueError("Arrivals must lie inside fixed observation horizon")
    basecapacity = (
        int(capacity)
        if capacity is not None
        else design_capacity(
            model, arrivals_, service_fraction, target_utilization, horizon
        )
    )
    if not 1 <= basecapacity <= 200:
        raise ValueError("Abstract capacity must lie between1and200")
    slots = max(1, int(round(basecapacity * capfactor)))
    core = EventCore(record_limit=20000 if record else 0)
    pool = simpy.Resource(core.env, capacity=slots) if resource else None
    outcomes = []
    waits = []
    service_total = [0.0]
    maxqueue = [0]
    replay_agents = []
    censored_plans = [0]
    tick = time.monotonic()
    target = model["target_activity"]
    maxday = horizon + 365.0

    def emit(kind, ident, activity=None, **attrs):
        capture = (
            record
            and ident is not None
            and (
                ident < 20
                or kind
                in ("Resource Request", "Resource Release", "Queue Entry", "Queue Exit")
            )
        )
        core.emit(
            kind,
            ident,
            record=capture,
            activity=activity,
            queue=len(pool.queue) if pool else 0,
            busy=pool.count if pool else 0,
            capacity=slots if pool else None,
            **attrs,
        )

    def run_case(x):
        ident = x["id"]
        rng = stream(seed, replicate, ident, 1)
        acts, gaps, capped = plan(model, x["category"], rng, kind, reworkfactor)
        if capped:
            censored_plans[0] += 1
        yield core.timeout(x["arrival_day"])
        agent = EventAgent(ident, parameters={"category": x["category"]})
        if record and ident < 20:
            replay_agents.append(agent)
        emit("Case Arrival", ident, acts[0])
        agent.transition("active", core.now)
        emit("Activity Start", ident, acts[0])
        emit("Activity Completion", ident, acts[0])
        for act, gap in zip(acts[1:], gaps):
            if not math.isfinite(gap) or gap < 0:
                raise ValueError("Invalid elapsed gap")
            constrained = resource and act == target
            assumed = gap * service_fraction if constrained else 0.0
            yield core.timeout(gap - assumed)
            if constrained:
                emit("Resource Request", ident, act)
                entered = core.now
                request = pool.request()
                emit("Queue Entry", ident, act)
                maxqueue[0] = max(maxqueue[0], len(pool.queue))
                yield request
                waits.append(core.now - entered)
                emit("Queue Exit", ident, act, wait_day=core.now - entered)
                emit("Activity Start", ident, act)
                d = assumed * servicefactor
                yield core.timeout(d)
                service_total[0] += d
                emit("Activity Completion", ident, act)
                pool.release(request)
                emit("Resource Release", ident, act)
            else:
                # No lifecycle data: these are an instantaneous synthetic transition after an observed elapsed interval, not observed service times.
                emit("Activity Start", ident, act)
                emit("Activity Completion", ident, act)
            if act.startswith(("Change ", "Cancel ")):
                emit(
                    "Rework",
                    ident,
                    act,
                    meaning="Change/Cancel proxy, not confirmed waste",
                )
            if record and ident < 20:
                agent.transition(act, core.now)
        if capped:
            emit("Plan Censored", ident, acts[-1])
            return
        duration = core.now - x["arrival_day"]
        agent.transition("complete", core.now)
        emit("Case Completion", ident, acts[-1])
        outcomes.append(
            {
                "id": ident,
                "category": x["category"],
                "arrival_day": x["arrival_day"],
                "completion_day": core.now,
                "duration_day": duration,
                "activities": acts,
                "change_cancel": proxy(acts),
                "repeated_occurrences": len(acts) - len(set(acts)),
            }
        )

    def disrupt():
        yield core.timeout(30.0)
        requests = [pool.request() for _ in range(max(1, slots // 2))]
        for req in requests:
            yield req
        start = core.now
        if start < 45:
            yield core.timeout(45 - start)
        for req in requests:
            pool.release(req)
        core.emit(
            "Capacity availability hold",
            None,
            record=record,
            requested_start_day=30.0,
            actual_start_day=start,
            end_day=core.now,
            slots=len(requests),
            nonpreemptive=True,
        )

    if resource and scenario == "disruption":
        core.env.process(disrupt())
    for x in inputs:
        core.env.process(run_case(x))
    runtime = core.run(until=maxday, cancel=cancel)
    completewindow = sum(x["completion_day"] <= horizon for x in outcomes)
    variants = Counter(tuple(x["activities"]) for x in outcomes)
    aggregate = {
        "cases_arrived": len(inputs),
        "cases_completed": len(outcomes),
        "unfinished_cases": len(inputs) - len(outcomes),
        "capped_route_cases": censored_plans[0],
        "duration_day": summary([x["duration_day"] for x in outcomes]),
        "completions_within_fixed_window": completewindow,
        "throughput_per_day": completewindow / horizon,
        "change_cancel_case_rate": (
            float(np.mean([x["change_cancel"] for x in outcomes])) if outcomes else None
        ),
        "repeat_activity_case_rate": (
            float(np.mean([x["repeated_occurrences"] > 0 for x in outcomes]))
            if outcomes
            else None
        ),
        "queue_wait_day": summary(waits),
        "max_queue": maxqueue[0],
        "abstract_capacity": slots if resource else None,
        "assumed_service_fraction": service_fraction if resource else None,
        "assumed_service_time_total_day": service_total[0],
        "utilization_entire_simulated_horizon": (
            service_total[0] / max(core.now * slots, 1e-9) if resource else None
        ),
        "runtime": runtime,
    }
    replay = {
        "kind": "HYPOTHETICAL SCENARIO" if resource else "SIMULATED DATA",
        "source": "SimPy-calculated events, not original company events",
        "displayed_agent_limit": 20,
        "total_cases": len(inputs),
        "events": core.records,
        "agents": [a.serialize() for a in replay_agents],
        "target_activity": target,
        "scenario": scenario,
        "truncated": core.record_truncated,
    }
    return {
        "aggregate": aggregate,
        "cases": outcomes,
        "variant_counts": variants,
        "replay": replay,
        "seconds": time.monotonic() - tick,
        "parameters": {
            "model": kind,
            "seed": seed,
            "replicate": replicate,
            "scenario": scenario,
            "resource_layer": resource,
            "horizon_day": horizon,
            "service_fraction": service_fraction if resource else None,
            "designed_basecapacity": basecapacity if resource else None,
            "target_utilization": target_utilization if resource else None,
            "changes": {
                "demand_growth": growth,
                "capacity_factor": capfactor,
                "service_factor": servicefactor,
                "rework_factor": reworkfactor,
            },
        },
    }

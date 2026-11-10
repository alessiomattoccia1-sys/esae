# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Generic discrete-event adapter beside the unchanged fixed-step Dynamics core."""

from dataclasses import dataclass, field
from copy import deepcopy
import math, time
import simpy


@dataclass
class EventAgent:
    id: int
    state: str = "created"
    parameters: dict = field(default_factory=dict)
    history: list = field(default_factory=list)

    def transition(self, state, at, **attributes):
        if not math.isfinite(at) or (self.history and at < self.history[-1]["time"]):
            raise ValueError("Monotonic finite simulation clock required")
        self.state = state
        self.history.append({"time": float(at), "state": state, **attributes})

    def serialize(self):
        return deepcopy(
            {
                "id": self.id,
                "state": self.state,
                "parameters": self.parameters,
                "history": self.history,
            }
        )


class EventCore:
    """SimPy scheduler, bounded recorder and clock; no flight/business assumptions."""

    def __init__(self, record_limit=20000, event_limit=10000000, wall_limit=300):
        if (
            not 0 <= record_limit <= 200000
            or not 1 <= event_limit <= 20000000
            or not 1 <= wall_limit <= 600
        ):
            raise ValueError("Bounded event core required")
        self.record_limit = record_limit
        self.event_limit = event_limit
        self.wall_limit = wall_limit
        self.reset()

    def reset(self):
        self.env = simpy.Environment()
        self.records = []
        self.count = 0
        self.paused = False
        self.started = time.monotonic()
        self.record_truncated = False

    @property
    def now(self):
        return float(self.env.now)

    def emit(self, kind, agent=None, record=True, **attributes):
        self.count += 1
        if self.count > self.event_limit:
            raise ValueError("Simulation event budget exceeded")
        if record:
            if len(self.records) < self.record_limit:
                self.records.append(
                    {
                        "time_day": self.now,
                        "kind": str(kind),
                        "agent": agent,
                        **attributes,
                    }
                )
            else:
                self.record_truncated = True

    def process(self, generator):
        return self.env.process(generator)

    def timeout(self, duration):
        if not math.isfinite(duration) or duration < 0:
            raise ValueError("Nonnegative finite interval required")
        return self.env.timeout(float(duration))

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def step(self):
        if self.paused or self.env.peek() == float("inf"):
            return False
        self.env.step()
        return True

    def run(self, until=None, cancel=None):
        if until is not None and (not math.isfinite(until) or until < self.now):
            raise ValueError("Future finite clock limit required")
        iterations = 0
        while not self.paused and self.env.peek() != float("inf"):
            if until is not None and self.env.peek() > until:
                break
            if iterations % 1024 == 0:
                if cancel and cancel():
                    raise InterruptedError("Cancelled between discrete events")
                if time.monotonic() - self.started > self.wall_limit:
                    raise ValueError("Discrete-event wall-time limit exceeded")
            self.step()
            iterations += 1
            if iterations > self.event_limit * 4:
                raise ValueError("Scheduler operation budget exceeded")
        return {
            "clock_day": self.now,
            "events_emitted": self.count,
            "scheduler_steps": iterations,
            "paused": self.paused,
            "record_truncated": self.record_truncated,
        }

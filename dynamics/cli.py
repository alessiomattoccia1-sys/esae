# SPDX-License-Identifier: Apache-2.0
"""python -m dynamics.cli run|serve|reproduce|models|simulate|monte-carlo"""

import argparse, json, os
from pathlib import Path
from .service import DynamicsEngine
from .mathematical import registry, monte_carlo


def main():
    p = argparse.ArgumentParser(
        description="Dynamics Lab · offline mathematical research"
    )
    p.add_argument(
        "command",
        choices=["run", "reproduce", "serve", "models", "simulate", "monte-carlo"],
    )
    p.add_argument("identifier", nargs="?", default="DME-001")
    p.add_argument("--data", type=Path, default=Path(".local/dynamics-data"))
    p.add_argument("--offline", action="store_true")
    p.add_argument("--port", type=int, default=4206)
    p.add_argument("--agents", type=int, default=50)
    p.add_argument("--scenario", choices=list("ABCDE"), default="C")
    p.add_argument("--seed", type=int, default=20261106)
    p.add_argument("--ollama-url")
    p.add_argument("--ollama-model")
    a = p.parse_args()
    if a.command == "models":
        print(json.dumps(registry(), indent=2))
        return
    if a.command == "monte-carlo":
        print(json.dumps(monte_carlo("RW", 2, 100, 0.1, 100, a.seed, 1), indent=2))
        return
    engine = DynamicsEngine(a.data, a.ollama_url, a.ollama_model)
    if a.command == "serve":
        if not 1024 <= a.port <= 65535:
            raise ValueError("Unprivileged local port required")
        import uvicorn
        from .api import create_app

        uvicorn.run(create_app(engine, a.port), host="127.0.0.1", port=a.port)
        return
    if a.command == "reproduce":
        r = engine.verify(a.identifier)
    elif a.command == "simulate":
        r = engine.run(
            "SIMULATION", {"agents": a.agents, "scenario": a.scenario, "seed": a.seed}
        )
    else:
        r = engine.run(a.identifier, {"offline": a.offline})
    print(json.dumps(r, indent=2))
    if r.get("status") == "failed" or r.get("passed") is False:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

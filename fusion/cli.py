# SPDX-License-Identifier: Apache-2.0
import argparse, json, os
from pathlib import Path
from .service import FusionEngine


def main():
    p = argparse.ArgumentParser(
        description="FPRE0.1: local retrospective experimental diagnostics, no apparatus control"
    )
    p.add_argument("operation", choices=["run", "reproduce", "serve"])
    p.add_argument("--experiment", choices=["FPE-001", "FPE-002"], default="FPE-001")
    p.add_argument("--data", type=Path, default=Path(".local/fusion"))
    p.add_argument("--job")
    p.add_argument("--resume")
    p.add_argument("--shots", type=int, default=5)
    p.add_argument("--start", type=float, default=0.05)
    p.add_argument("--end", type=float, default=0.35)
    p.add_argument("--offline", action="store_true")
    p.add_argument("--port", type=int, default=4205)
    p.add_argument("--ollama-url")
    p.add_argument("--ollama-model")
    a = p.parse_args()
    os.umask(0o077)
    if not 1024 <= a.port <= 65535:
        p.error("Loopback port bound1024..65535")
    e = FusionEngine(a.data, a.ollama_url, a.ollama_model)
    if a.operation == "serve":
        import uvicorn
        from .api import create_app

        uvicorn.run(
            create_app(e, a.port), host="127.0.0.1", port=a.port, access_log=False
        )
    elif a.operation == "reproduce":
        if not a.job:
            p.error("--job required for exact acquisition-vintage replay")
        if not e.store.get(a.job):
            p.error("Unknown fusion job")
        if e.store.get(a.job)["experiment"] != a.experiment:
            p.error("Experiment/job mismatch")
        if not e.lock.acquire(False):
            raise ValueError("An operation is active")
        try:
            r = e.verify(a.job)
            print(json.dumps(r, indent=2))
        finally:
            e.lock.release()
        if not r["passed"]:
            raise SystemExit(1)
    else:
        cfg = (
            {
                "shot_count": a.shots,
                "window_seconds": [a.start, a.end],
                "offline": a.offline,
            }
            if a.experiment == "FPE-001"
            else {"offline": a.offline}
        )
        j = e.run(a.experiment, cfg, resume=a.resume)
        print(json.dumps(j, indent=2))
        if j["status"] != "completed":
            raise SystemExit(1)


if __name__ == "__main__":
    main()

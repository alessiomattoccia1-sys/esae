# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
import argparse, json
from pathlib import Path
from .service import OperationsEngine


def main():
    p = argparse.ArgumentParser(
        description="Dynamics Lab · Operations Twin · local process research"
    )
    p.add_argument(
        "command", choices=["run", "reproduce", "serve", "import", "what-if"]
    )
    p.add_argument("identifier", nargs="?", default="OTE-001")
    p.add_argument("--data", type=Path, default=Path(".local/operations-twin-data"))
    p.add_argument("--offline", action="store_true")
    p.add_argument("--port", type=int, default=4207)
    p.add_argument(
        "--format", choices=["xes", "csv", "json", "jsonl", "parquet"], default="xes"
    )
    p.add_argument("--cases", type=int, default=150)
    p.add_argument("--replicates", type=int, default=5)
    p.add_argument("--ollama-url")
    p.add_argument("--ollama-model")
    a = p.parse_args()
    e = OperationsEngine(a.data, a.ollama_url, a.ollama_model)
    if a.command == "serve":
        if not 1024 <= a.port <= 65535:
            raise ValueError("Unprivileged loopback port required")
        import uvicorn
        from .api import create_app

        uvicorn.run(create_app(e, a.port), host="127.0.0.1", port=a.port)
        return
    if a.command == "reproduce":
        r = e.reproduce(a.identifier)
    elif a.command == "import":
        r = e.import_file(a.identifier, a.format)
    elif a.command == "what-if":
        r = e.run(
            "WHATIF",
            {"offline": a.offline, "cases": a.cases, "replicates": a.replicates},
        )
    else:
        r = e.run(a.identifier, {"offline": a.offline})
    print(json.dumps(r, indent=2))
    if r.get("status") == "failed" or r.get("passed") is False:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

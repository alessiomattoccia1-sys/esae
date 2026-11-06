# SPDX-License-Identifier: Apache-2.0
import argparse, json, os, datetime
from pathlib import Path
from .service import FinancialEngine
from .analysis import StudyConfig


def main():
    p = argparse.ArgumentParser(
        description="FSIE0.1 — local institutional-data research, no trading or forecasts"
    )
    p.add_argument(
        "operation",
        choices=["run", "verify", "serve", "benchmark", "import-file", "ecb"],
    )
    p.add_argument("--data", type=Path, default=Path(".local/financial"))
    p.add_argument("--job")
    p.add_argument("--resume")
    p.add_argument("--start", default="2000-01-01")
    p.add_argument(
        "--end", default=datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    )
    p.add_argument("--refresh", action="store_true")
    p.add_argument("--port", type=int, default=4204)
    p.add_argument("--ollama-url")
    p.add_argument("--ollama-model")
    p.add_argument("--benchmark-rows", type=int, default=20_000_000)
    p.add_argument("--file", type=Path)
    p.add_argument("--source-url")
    p.add_argument(
        "--parser", choices=["treasury_csv", "treasury_xml", "nfci_csv", "sofr_json"]
    )
    a = p.parse_args()
    os.umask(0o077)
    if not 1024 <= a.port <= 65535:
        p.error("Loopback port must be1024..65535")
    if a.operation == "benchmark":
        from .benchmark import run
        from research_core.locking import OperationLock

        lock = OperationLock(a.data / "active.lock")
        a.data.mkdir(parents=True, exist_ok=True)
        if not lock.acquire(False):
            raise ValueError("Another financial operation is active")
        try:
            print(
                json.dumps(
                    run(a.data / "synthetic-benchmark", a.benchmark_rows), indent=2
                )
            )
        finally:
            lock.release()
        return
    engine = FinancialEngine(
        a.data, ollama_url=a.ollama_url, ollama_model=a.ollama_model
    )
    if a.operation == "import-file":
        if not a.file or not a.source_url or not a.parser:
            p.error("--file, --source-url and --parser required")
        from .connectors import import_official_file

        if not engine.lock.acquire(False):
            raise ValueError("Another operation is active")
        try:
            r = import_official_file(a.file, a.source_url, a.parser, engine.cache)
            dest = engine.root / "manual-sources.json"
            records = json.loads(dest.read_text()) if dest.exists() else []
            records = [x for x in records if x["url"] != r["url"]] + [r]
            dest.write_text(json.dumps(records, indent=2) + "\n")
            print(json.dumps(r, indent=2))
        finally:
            engine.lock.release()
    elif a.operation == "ecb":
        from .ecb import ECBConnector

        if not engine.lock.acquire(False):
            raise ValueError("Another operation is active")
        try:
            r = ECBConnector(engine.root / "ecb-cache").acquire(a.start, a.end)
            folder = engine.root / "ecb"
            folder.mkdir(exist_ok=True)
            (folder / "ECB_SDMX_RESULT.json").write_text(json.dumps(r, indent=2) + "\n")
            print(json.dumps({k: v for k, v in r.items() if k != "data"}, indent=2))
        finally:
            engine.lock.release()
    elif a.operation == "serve":
        import uvicorn
        from .api import create_app

        uvicorn.run(
            create_app(engine, a.port), host="127.0.0.1", port=a.port, access_log=False
        )
    elif a.operation == "verify":
        if not a.job:
            p.error("--job is required")
        r = engine.verify(a.job)
        print(json.dumps(r, indent=2))
        if not r["passed"]:
            raise SystemExit(1)
    else:
        job = engine.run(
            StudyConfig(start=a.start, end=a.end), refresh=a.refresh, resume=a.resume
        )
        print(json.dumps(job, indent=2))
        if job["status"] != "completed":
            raise SystemExit(1)


if __name__ == "__main__":
    main()

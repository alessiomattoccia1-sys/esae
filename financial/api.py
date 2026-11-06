# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
from dataclasses import asdict
from typing import Literal
import datetime, hashlib, json, re, uuid
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from research_core.web import local_boundary
from research_core.local_ai import hypothesis
from esae.scanner import read_regular
from .analysis import StudyConfig, clean
from .connectors import SOURCES, FUTURE_CONNECTORS


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start: datetime.date = datetime.date(2000, 1, 1)
    end: datetime.date = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).date()
    )
    refresh: bool = False


def create_app(engine, port=4204):
    app = FastAPI(
        title="Financial Systems Intelligence Engine",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    local_boundary(app, port)
    static = Path(__file__).parent / "static"

    @app.exception_handler(ValueError)
    async def bad(request, exc):
        return Response(
            json.dumps({"detail": str(exc)}),
            status_code=400,
            media_type="application/json",
        )

    @app.get("/")
    def index():
        return FileResponse(static / "index.html")

    @app.get("/shared/style.css")
    def shared():
        return FileResponse(
            Path(__file__).resolve().parents[1] / "esae/static/style.css"
        )

    @app.get("/static/{name}")
    def asset(name: str):
        if name not in ("app.js", "financial.css"):
            raise HTTPException(404)
        return FileResponse(static / name)

    @app.get("/api/status")
    def status():
        return {
            "engine": "Financial Systems Intelligence Engine",
            "version": "0.1.0",
            "busy": engine.lock.locked(),
            "sources": SOURCES,
            "other_connectors": FUTURE_CONNECTORS,
            "ollama": {
                "configured": bool(engine.ollama_url and engine.ollama_model),
                "model": engine.ollama_model,
            },
            "today": datetime.datetime.now(datetime.timezone.utc).date().isoformat(),
            "cloud_ai": False,
            "trading": False,
            "public_data_only": True,
        }

    @app.get("/api/jobs")
    def jobs():
        return [
            {
                k: j.get(k)
                for k in [
                    "id",
                    "created_at",
                    "completed_at",
                    "status",
                    "phase",
                    "progress",
                    "summary",
                    "duration_seconds",
                    "errors",
                ]
            }
            for j in engine.store.list()
        ]

    @app.post("/api/jobs", status_code=202)
    def run(body: RunRequest):
        return engine.run(
            StudyConfig(start=body.start.isoformat(), end=body.end.isoformat()),
            refresh=body.refresh,
            asynchronous=True,
        )

    def get(j):
        value = engine.store.get(str(j))
        if not value:
            raise HTTPException(404, "Unknown financial study")
        return value

    @app.get("/api/jobs/{job_id}")
    def job(job_id: uuid.UUID):
        return get(job_id)

    @app.get("/api/jobs/{job_id}/report")
    def report(job_id: uuid.UUID):
        get(job_id)
        return engine.report(str(job_id))

    @app.get("/api/jobs/{job_id}/series")
    def series(job_id: uuid.UUID):
        get(job_id)
        return engine.store.series(str(job_id))

    @app.get("/api/jobs/{job_id}/observations")
    def explorer(
        job_id: uuid.UUID,
        series: str | None = Query(None, max_length=40),
        start: datetime.date | None = None,
        end: datetime.date | None = None,
        source: Literal["treasury", "chicago", "newyork"] | None = None,
        frequency: Literal["daily", "weekly"] | None = None,
        unit: Literal["percentage_points", "standardized_index"] | None = None,
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
    ):
        get(job_id)
        return engine.store.explorer(
            str(job_id),
            series,
            start.isoformat() if start else None,
            end.isoformat() if end else None,
            source,
            frequency,
            unit,
            limit,
            offset,
        )

    @app.get("/api/jobs/{job_id}/chart")
    def chart(
        job_id: uuid.UUID,
        series: str = Query(..., max_length=40),
        start: datetime.date | None = None,
        end: datetime.date | None = None,
    ):
        get(job_id)
        if series not in {s["series_id"] for s in engine.store.series(str(job_id))}:
            raise ValueError("Unknown financial series")
        sql = (
            "SELECT observation_date,value FROM parquet_observations WHERE series_id=?"
        )
        params = [series]
        if start:
            sql += " AND observation_date>=?"
            params.append(start.isoformat())
        if end:
            sql += " AND observation_date<=?"
            params.append(end.isoformat())
        with engine.store.analytical(str(job_id), True) as db:
            rows = db.execute(
                sql + " ORDER BY observation_date LIMIT 12001", params
            ).fetchall()
        if len(rows) > 12000:
            raise ValueError("Narrow chart period; maximum12000observations")
        return {
            "series": series,
            "points": [{"date": str(d), "value": v} for d, v in rows],
            "interpolated": False,
        }

    @app.get("/api/jobs/{job_id}/curve")
    def curve(job_id: uuid.UUID, date: datetime.date):
        get(job_id)
        with engine.store.analytical(str(job_id), True) as db:
            rows = db.execute(
                "SELECT series_id,value FROM parquet_observations WHERE observation_date=? AND source_id='treasury'",
                [date.isoformat()],
            ).fetchall()
        points = []
        for name, value in rows:
            tenor = name.removeprefix("UST_")
            months = float(tenor[:-1]) * (12 if tenor.endswith("Y") else 1)
            points.append(
                {"series": name, "months": months, "yield_percentage_points": value}
            )
        return {
            "date": date.isoformat(),
            "points": sorted(points, key=lambda p: p["months"]),
            "has_observations": bool(points),
            "missing_date_policy": "No last-session fallback; selected non-working dates return no curve",
        }

    @app.get("/api/jobs/{job_id}/export/{kind}")
    def export(
        job_id: uuid.UUID,
        kind: Literal["json", "html", "csv", "manifest", "method", "reproduction"],
    ):
        get(job_id)
        name = {
            "json": "FSIE-001_RESULTS.json",
            "html": "FSIE-001_REPORT.html",
            "csv": "FSIE-001_FINDINGS.csv",
            "manifest": "FSIE-001_MANIFEST.json",
            "method": "FSIE-001_METHODOLOGY.md",
            "reproduction": "FSIE-001_REPRODUCIBILITY.md",
        }[kind]
        p = engine.store.directory(str(job_id)) / name
        if not p.is_file():
            raise HTTPException(404, "Study not ready")
        return FileResponse(p, filename=name)

    @app.post("/api/jobs/{job_id}/resume", status_code=202)
    def resume(job_id: uuid.UUID):
        get(job_id)
        return engine.run(resume=str(job_id), asynchronous=True)

    @app.post("/api/jobs/{job_id}/verify")
    def verify(job_id: uuid.UUID):
        get(job_id)
        if not engine.lock.acquire(False):
            raise ValueError("A financial operation is active")
        try:
            return engine.verify(str(job_id))
        finally:
            engine.lock.release()

    @app.get("/api/benchmark")
    def benchmark():
        paths = sorted(
            (engine.root / "synthetic-benchmark").glob("*/FSIE-BENCHMARK.json")
        )
        return (
            json.loads(read_regular(paths[-1], 2000000))
            if paths
            else {"status": "not_run", "synthetic_only": True}
        )

    @app.post("/api/jobs/{job_id}/findings/{finding_id}/explain")
    def explain(job_id: uuid.UUID, finding_id: str):
        get(job_id)
        if not engine.ollama_url or not engine.ollama_model:
            raise ValueError(
                "Ollama not configured; quantitative analysis remains available"
            )
        report = engine.report(str(job_id))
        finding = next((f for f in report["findings"] if f["id"] == finding_id), None)
        if not finding:
            raise HTTPException(404, "Unknown finding")
        if not engine.lock.acquire(False):
            raise ValueError("A financial operation is active")
        try:
            observed = {
                "finding": finding,
                "period": report["study_period"],
                "source_ids": finding["source_ids"],
                "vintage_policy": report["analysis_kind"],
            }
            computed = {
                "coverage": report["coverage"],
                "lag_summary": report["lag_test_summary"],
                "interpretive_limit": "Retrospective latest-vintage association; not trading, price forecast, causal claim or real-time crisis prediction",
            }
            r = hypothesis(
                observed,
                computed,
                [finding_id],
                engine.ollama_url,
                engine.ollama_model,
                timeout=120,
            )
            r["not_verified"] = (
                "Interpretation is an unverified financial research hypothesis; no causal proof, real-time crisis prediction, investment advice or trading instruction is established."
            )
            folder = engine.store.directory(str(job_id)) / "ai"
            folder.mkdir(exist_ok=True)
            dest = folder / (finding_id + ".json")
            if dest.exists():
                old = read_regular(dest, 128000)
                history = folder / "history"
                history.mkdir(exist_ok=True)
                saved = history / (hashlib.sha256(old).hexdigest() + ".json")
                if not saved.exists():
                    saved.write_bytes(old)
            dest.write_text(json.dumps(r, indent=2) + "\n")
            return r
        finally:
            engine.lock.release()

    @app.get("/api/jobs/{job_id}/insights")
    def insights(job_id: uuid.UUID):
        get(job_id)
        folder = engine.store.directory(str(job_id)) / "ai"
        return (
            [
                json.loads(read_regular(p, 128000))
                for p in sorted(folder.glob("FSIE-001-F*.json"))[:20]
            ]
            if folder.exists()
            else []
        )

    return app

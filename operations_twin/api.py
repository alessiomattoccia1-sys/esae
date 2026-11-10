# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
from typing import Literal
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from research_core.web import local_boundary
from research_core.local_ai import hypothesis
from esae.scanner import read_regular, no_symlink
from .reporting import CSS


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    experiment: Literal["OTE-001", "OTE-002", "OTE-003"] = "OTE-001"
    offline: bool = False


class Changes(BaseModel):
    model_config = ConfigDict(extra="forbid")
    demand_growth: float = Field(0.3, ge=0, le=1)
    capacity_factor: float = Field(1.0, ge=0.25, le=2)
    service_factor: float = Field(0.8, ge=0.1, le=2)
    rework_factor: float = Field(0.8, ge=0.1, le=1)


class WhatIfRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cases: int = Field(150, ge=10, le=1500)
    replicates: int = Field(5, ge=2, le=100)
    changes: Changes = Field(default_factory=Changes)


class ImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    format: Literal["xes", "csv", "json", "jsonl", "parquet"] = "csv"
    mapping: dict[str, str] | None = None


def create_app(engine, port=4207):
    app = FastAPI(
        title="Dynamics Lab · Operations Twin",
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
            json.dumps({"detail": str(exc)[:1000]}), 400, media_type="application/json"
        )

    def job(id):
        try:
            j = engine.store.get(id)
        except ValueError:
            raise HTTPException(404)
        if not j:
            raise HTTPException(404)
        return j

    @app.get("/")
    def index():
        return FileResponse(static / "index.html")

    @app.get("/static/{name}")
    def asset(name: str):
        if name not in ("app.js", "operations.css"):
            raise HTTPException(404)
        return FileResponse(static / name)

    @app.get("/shared/style.css")
    def shared():
        return FileResponse(Path(__file__).parents[1] / "esae/static/style.css")

    @app.get("/report.css")
    def reportcss():
        return Response(CSS, media_type="text/css")

    @app.get("/api/status")
    def status():
        return {
            "family": "DYNAMICS LAB",
            "engine": "Operations Twin",
            "number": 2,
            "version": "0.1.0",
            "busy": engine.lock.locked(),
            "cloud": False,
            "ai_configured": bool(engine.ollama_url and engine.ollama_model),
            "public_backend": False,
            "import_formats": ["xes", "csv", "parquet", "json", "jsonl"],
        }

    @app.get("/api/jobs")
    def jobs():
        return [
            {k: v for k, v in x.items() if k not in ("result", "sources")}
            for x in engine.store.list()
        ]

    @app.get("/api/jobs/{id}")
    def getjob(id: str):
        return job(id)

    @app.post("/api/run")
    def run(a: RunRequest):
        return engine.run(a.experiment, {"offline": a.offline}, asynchronous=True)

    @app.post("/api/what-if")
    def whatif(a: WhatIfRequest):
        return engine.run(
            "WHATIF",
            {
                "offline": True,
                "cases": a.cases,
                "replicates": a.replicates,
                "overrides": a.changes.model_dump(),
            },
            asynchronous=True,
        )

    @app.post("/api/jobs/{id}/cancel")
    def cancel(id: str):
        return engine.cancel(id)

    @app.post("/api/jobs/{id}/resume")
    def resume(id: str):
        j = job(id)
        return engine.run(j["experiment"], resume=id, asynchronous=True)

    @app.get("/api/jobs/{id}/files/{name}")
    def file(id: str, name: str):
        j = job(id)
        if name not in j.get("result_files", []) or Path(name).name != name:
            raise HTTPException(404)
        return FileResponse(no_symlink(engine.directory(id) / name))

    @app.get("/api/imports")
    def imports():
        return {
            "directory": "imports within configured local data directory",
            "files": [
                p.name
                for p in (engine.root / "imports").iterdir()
                if p.is_file() and not p.is_symlink()
            ],
        }

    @app.post("/api/import")
    def importlog(a: ImportRequest):
        return engine.import_file(a.name, a.format, a.mapping)

    @app.post("/api/jobs/{id}/ai")
    def ai(id: str):
        j = job(id)
        if not engine.ollama_url or not engine.ollama_model:
            return {
                "status": "disabled",
                "kind": "ai_hypothesis",
                "verification_status": "not_verified",
                "detail": "Optional local Ollama is not configured. Deterministic research remains operational.",
            }
        r = j.get("result")
        exp = j.get("experiment")
        if not r or exp == "WHATIF":
            raise ValueError("Completed published experiment required")
        observed = {
            "source": "BPI Challenge2019,4TU,CC BY4.0",
            "elapsed_time_not_service_time": True,
        }
        if exp == "OTE-001":
            computed = {
                k: r["counts"][k] for k in ("events", "cases", "activities", "variants")
            }
        elif exp == "OTE-002":
            computed = {
                "selected_on_validation": r["selected_on_validation_only"],
                "validation_scope": r["acceptance_scope"],
                "test_cases": r["evaluations"]["test"]["cases"],
            }
        else:
            computed = {
                "kind": r["kind"],
                "status": r["status"],
                "scenarios": list(r["scenarios"]),
                "cases": r["cases_base"],
            }
        return hypothesis(
            observed,
            computed,
            [
                r["results_sha256"],
                "https://doi.org/10.4121/uuid:d06aff4b-79f0-45e6-8ec8-e19730c248f1",
            ],
            engine.ollama_url,
            engine.ollama_model,
        )

    return app

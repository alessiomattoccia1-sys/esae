# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
from typing import Literal
import json, uuid
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field, ConfigDict
from research_core.web import local_boundary
from research_core.local_ai import hypothesis
from esae.scanner import read_regular, no_symlink
from .mathematical import registry
from .simulation import SCENARIOS
from .reporting import CSS


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    experiment: Literal["DME-001", "DME-002", "DME-003"] = "DME-001"
    offline: bool = False


class SimRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    agents: int = Field(10, ge=1, le=200)
    steps: int = Field(200, ge=2, le=1000)
    dt: float = Field(0.1, ge=0.01, le=1)
    scenario: Literal["A", "B", "C", "D", "E"] = "C"
    model: Literal["CV", "CRW"] = "CV"
    noise: float = Field(0.3, ge=0, le=5)
    interaction: float = Field(0.8, ge=0, le=2)
    missing: float = Field(0.3, ge=0, lt=0.95)
    observe_every: int = Field(1, ge=1, le=20)
    seed: int = Field(20261106, ge=0, le=4294967295)


def create_app(engine, port=4206):
    app = FastAPI(
        title="Dynamics Lab · Drone Dynamics",
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

    @app.get("/static/{name}")
    def asset(name: str):
        if name not in ("app.js", "dynamics.css"):
            raise HTTPException(404)
        return FileResponse(static / name)

    @app.get("/shared/style.css")
    def shared():
        return FileResponse(Path(__file__).parents[1] / "esae/static/style.css")

    @app.get("/report.css")
    def report_style():
        return Response(CSS, media_type="text/css")

    @app.get("/api/status")
    def status():
        return {
            "family": "DYNAMICS LAB",
            "engine": "Drone Dynamics",
            "version": "0.1.0",
            "busy": engine.lock.locked(),
            "cloud": False,
            "operational_control": False,
            "ollama": bool(engine.ollama_url and engine.ollama_model),
            "scenarios": SCENARIOS,
        }

    @app.get("/api/models")
    def models():
        return registry()

    @app.get("/api/jobs")
    def jobs():
        return engine.store.list()

    @app.post("/api/jobs", status_code=202)
    def run(body: RunRequest):
        return engine.run(body.experiment, {"offline": body.offline}, True)

    @app.post("/api/simulations", status_code=202)
    def simulate(body: SimRequest):
        return engine.run("SIMULATION", body.model_dump(), True)

    def get(id):
        j = engine.store.get(str(id))
        if not j:
            raise HTTPException(404, "Unknown Dynamics job")
        return j

    @app.get("/api/jobs/{id}")
    def job(id: uuid.UUID):
        return get(id)

    @app.get("/api/jobs/{id}/results")
    def result(id: uuid.UUID):
        get(id)
        return engine.report(str(id))

    @app.post("/api/jobs/{id}/cancel", status_code=202)
    def cancel(id: uuid.UUID):
        j = get(id)
        if j["status"] != "running":
            raise ValueError("Only a running job can cancel")
        (engine.store.directory(str(id)) / "cancel-requested").write_text(
            "Explicit local cancellation\n"
        )
        return {"status": "requested"}

    @app.post("/api/jobs/{id}/resume", status_code=202)
    def resume(id: uuid.UUID):
        get(id)
        return engine.run(resume=str(id), asynchronous=True)

    @app.get("/api/jobs/{id}/figure/{name}")
    def figure(id: uuid.UUID, name: str):
        j = get(id)
        m = json.loads(
            read_regular(
                engine.store.directory(str(id)) / (j["experiment"] + "_MANIFEST.json"),
                16_000_000,
            )
        )
        if name not in {Path(x["file"]).name for x in m["figures"]}:
            raise HTTPException(404)
        return FileResponse(
            no_symlink(engine.store.directory(str(id)) / "figures" / name)
        )

    @app.get("/api/jobs/{id}/export/{kind}")
    def export(
        id: uuid.UUID,
        kind: Literal["json", "html", "csv", "manifest", "method", "reproduction"],
    ):
        j = get(id)
        suffix = {
            "json": "RESULTS.json",
            "html": "REPORT.html",
            "csv": "METRICS.csv",
            "manifest": "MANIFEST.json",
            "method": "METHODOLOGY.md",
            "reproduction": "REPRODUCIBILITY.md",
        }[kind]
        p = engine.store.directory(str(id)) / (j["experiment"] + "_" + suffix)
        if not p.is_file():
            raise HTTPException(404, "Artifact unavailable")
        if kind == "html":
            text = read_regular(p, 12_000_000).decode()
            text = text.replace(
                "<style>" + CSS + "</style>",
                '<link rel="stylesheet" href="/report.css">',
            ).replace('src="figures/', 'src="/api/jobs/' + str(id) + "/figure/")
            return Response(text, media_type="text/html")
        return FileResponse(no_symlink(p), filename=p.name)

    @app.post("/api/jobs/{id}/insight")
    def insight(id: uuid.UUID):
        get(id)
        r = engine.report(str(id))
        if not engine.ollama_url or not engine.ollama_model:
            return {
                "status": "disabled",
                "verification_status": "NOT VERIFIED",
                "message": "Optional local Ollama is not configured; all numerical analyses remain available.",
            }
        return hypothesis(
            {
                "kind": r.get("kind"),
                "source": r["dataset"].get("source", r["dataset"].get("doi")),
            },
            {"counts": r["counts"], "limits": r.get("limits", [])[:4]},
            [r["experiment"]],
            engine.ollama_url,
            engine.ollama_model,
        )

    return app

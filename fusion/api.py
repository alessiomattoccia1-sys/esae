# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
from typing import Literal
import json, uuid, hashlib, re
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from research_core.web import local_boundary
from research_core.local_ai import hypothesis
from esae.scanner import read_regular, no_symlink


class RequestRun(BaseModel):
    model_config = ConfigDict(extra="forbid")
    experiment: Literal["FPE-001", "FPE-002"] = "FPE-001"
    shot_count: int = Field(5, ge=5, le=20)
    start_seconds: float = Field(0.05, ge=-1, le=9)
    end_seconds: float = Field(0.35, ge=-0.9, le=10)
    offline: bool = False


def create_app(engine, port=4205):
    app = FastAPI(
        title="Fusion Plasma Research Engine",
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
    def style():
        return FileResponse(Path(__file__).parents[1] / "esae/static/style.css")

    @app.get("/static/{name}")
    def asset(name: str):
        if name not in ("app.js", "fusion.css"):
            raise HTTPException(404)
        return FileResponse(static / name)

    @app.get("/api/status")
    def status():
        return {
            "engine": "FPRE",
            "version": "0.1.0",
            "busy": engine.lock.locked(),
            "apparatus_control": False,
            "cloud": False,
            "ollama": {
                "configured": bool(engine.ollama_url and engine.ollama_model),
                "model": engine.ollama_model,
            },
            "labs": ["FPE-001", "FPE-002"],
            "data_policy": "Real retrospective diagnostics; no target/drive/implosion optimization or inferred yield",
        }

    @app.get("/api/jobs")
    def jobs():
        return [
            {
                k: j.get(k)
                for k in [
                    "id",
                    "experiment",
                    "created_at",
                    "completed_at",
                    "status",
                    "phase",
                    "summary",
                    "progress",
                    "errors",
                    "duration_seconds",
                ]
            }
            for j in engine.store.list()
        ]

    @app.post("/api/jobs", status_code=202)
    def run(body: RequestRun):
        cfg = (
            {
                "shot_count": body.shot_count,
                "window_seconds": [body.start_seconds, body.end_seconds],
                "offline": body.offline,
            }
            if body.experiment == "FPE-001"
            else {"offline": body.offline}
        )
        return engine.run(body.experiment, cfg, asynchronous=True)

    def get(id):
        j = engine.store.get(str(id))
        if not j:
            raise HTTPException(404, "Unknown fusion job")
        return j

    @app.get("/api/jobs/{job_id}")
    def job(job_id: uuid.UUID):
        return get(job_id)

    @app.get("/api/jobs/{job_id}/report")
    def report(job_id: uuid.UUID):
        get(job_id)
        return engine.report(str(job_id))

    @app.post("/api/jobs/{job_id}/resume", status_code=202)
    def resume(job_id: uuid.UUID):
        get(job_id)
        return engine.run(resume=str(job_id), asynchronous=True)

    @app.post("/api/jobs/{job_id}/cancel", status_code=202)
    def cancel(job_id: uuid.UUID):
        j = get(job_id)
        if j["status"] != "running":
            raise ValueError("Only running job can cancel")
        (engine.store.directory(str(job_id)) / "cancel-requested").write_text(
            "Explicit local cancellation\n"
        )
        return {
            "status": "requested",
            "policy": "Stops between bounded acquisition/analysis stages; completed sources/results preserved",
        }

    @app.get("/api/jobs/{job_id}/signals")
    def signals(
        job_id: uuid.UUID,
        shot: int | None = Query(None, ge=1000, le=999999),
        diagnostic: str | None = Query(None, max_length=100),
    ):
        get(job_id)
        r = engine.report(str(job_id))
        rows = r.get("signals", [])
        return [
            x
            for x in rows
            if (shot is None or x["identity"]["shot_id"] == shot)
            and (diagnostic is None or x["identity"]["diagnostic"] == diagnostic)
        ]

    @app.get("/api/jobs/{job_id}/images")
    def images(job_id: uuid.UUID, shot: str | None = Query(None, pattern=r"^\d{6}$")):
        get(job_id)
        return [
            x
            for x in engine.report(str(job_id)).get("images", [])
            if shot is None or x["identity"]["shot_id"] == shot
        ]

    @app.get("/api/jobs/{job_id}/figure/{name}")
    def figure(job_id: uuid.UUID, name: str):
        j = get(job_id)
        folder = engine.store.directory(str(job_id))
        manifest = json.loads(
            read_regular(folder / (j["experiment"] + "_MANIFEST.json"), 8_000_000)
        )
        allowed = {Path(x["file"]).name for x in manifest["figures"]}
        if name not in allowed:
            raise HTTPException(404)
        return FileResponse(no_symlink(folder / "figures" / name))

    @app.get("/api/jobs/{job_id}/export/{kind}")
    def export(
        job_id: uuid.UUID,
        kind: Literal["json", "html", "csv", "manifest", "method", "reproduction"],
    ):
        j = get(job_id)
        suffix = {
            "json": "RESULTS.json",
            "html": "REPORT.html",
            "csv": "FINDINGS.csv",
            "manifest": "MANIFEST.json",
            "method": "METHODOLOGY.md",
            "reproduction": "REPRODUCIBILITY.md",
        }[kind]
        p = engine.store.directory(str(job_id)) / (j["experiment"] + "_" + suffix)
        if not p.is_file():
            raise HTTPException(404, "Export not ready")
        if kind == "html":
            # Rewrite relative original figures for the loopback HTML download route.
            b = (
                read_regular(p, 8_000_000)
                .decode()
                .replace('src="figures/', 'src="/api/jobs/' + str(job_id) + "/figure/")
            )
            b = re.sub(r'<meta http-equiv="Content-Security-Policy"[^>]*>', "", b)
            b = re.sub(
                r"<style>[\s\S]*?</style>",
                '<link rel="stylesheet" href="/api/jobs/'
                + str(job_id)
                + '/report.css">',
                b,
                count=1,
            )
            return Response(b, media_type="text/html")
        return FileResponse(p, filename=p.name)

    @app.get("/api/jobs/{job_id}/report.css")
    def report_style(job_id: uuid.UUID):
        j = get(job_id)
        text = read_regular(
            engine.store.directory(str(job_id)) / (j["experiment"] + "_REPORT.html"),
            8_000_000,
        ).decode()
        m = re.search(r"<style>([\s\S]*?)</style>", text)
        if not m:
            raise HTTPException(404)
        return Response(m.group(1), media_type="text/css")

    @app.post("/api/jobs/{job_id}/verify")
    def verify(job_id: uuid.UUID):
        get(job_id)
        if not engine.lock.acquire(False):
            raise ValueError("Operation already active")
        try:
            return engine.verify(str(job_id))
        finally:
            engine.lock.release()

    @app.post("/api/jobs/{job_id}/findings/{finding_id}/explain")
    def explain(job_id: uuid.UUID, finding_id: str):
        get(job_id)
        if not engine.ollama_url or not engine.ollama_model:
            raise ValueError(
                "Optional local Ollama not configured; analysis remains available"
            )
        r = engine.report(str(job_id))
        f = next((x for x in r["findings"] if x["id"] == finding_id), None)
        if not f:
            raise HTTPException(404)
        if not engine.lock.acquire(False):
            raise ValueError("Operation already active")
        try:
            observed = {
                "experiment": r["experiment"],
                "dataset": r["dataset"],
                "scope": "Only existing selected diagnostics; no operating settings, apparatus control, implosion/yield optimization or new physical measurements",
            }
            computed = {
                "finding": f,
                "summary": r["counts"],
            }
            value = hypothesis(
                observed,
                computed,
                [finding_id],
                engine.ollama_url,
                engine.ollama_model,
                timeout=120,
            )
            value["not_verified"] = (
                "Unverified scientific interpretation of existing diagnostic evidence; no named physical mode, causal result, implosion/yield/ignition performance or apparatus action established."
            )
            folder = engine.store.directory(str(job_id)) / "ai"
            folder.mkdir(exist_ok=True)
            dest = folder / (finding_id + ".json")
            if dest.exists():
                previous = dest.read_bytes()
                history = folder / "history"
                history.mkdir(exist_ok=True)
                saved = history / (hashlib.sha256(previous).hexdigest() + ".json")
                if not saved.exists():
                    saved.write_bytes(previous)
            dest.write_text(json.dumps(value, indent=2) + "\n")
            return value
        finally:
            engine.lock.release()

    @app.get("/api/jobs/{job_id}/insights")
    def insights(job_id: uuid.UUID):
        get(job_id)
        folder = engine.store.directory(str(job_id)) / "ai"
        return (
            [
                json.loads(read_regular(p, 128000))
                for p in sorted(folder.glob("*.json"))[:12]
            ]
            if folder.exists()
            else []
        )

    return app

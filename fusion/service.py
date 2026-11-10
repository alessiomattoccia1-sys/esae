# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Persistent local jobs, two independent experiment paths and full raw replay."""

from pathlib import Path
import json, time, threading, hashlib, datetime, sys, subprocess, importlib.metadata, platform, resource, uuid
from research_core import now, validate_ollama
from research_core.locking import OperationLock
from .storage import FusionStore
from .acquisition import FusionCache
from .experiments import magnetic, inertial
from .report import figures, html_report, methodology, reproduction, findings_csv
from . import PARSER_VERSION


class FusionEngine:
    def __init__(self, root, ollama_url=None, ollama_model=None):
        self.store = FusionStore(root)
        self.root = self.store.root
        self.lock = OperationLock(self.root / "active.lock")
        self.ollama_url = validate_ollama(ollama_url) if ollama_url else None
        self.ollama_model = ollama_model

    def run(
        self, experiment="FPE-001", parameters=None, asynchronous=False, resume=None
    ):
        if experiment not in ("FPE-001", "FPE-002"):
            raise ValueError("Known fusion experiment required")
        cfg = (
            {"shot_count": 5, "window_seconds": [0.05, 0.35]}
            if experiment == "FPE-001"
            else {}
        )
        cfg.update(parameters or {})
        if set(cfg) - (
            {"shot_count", "window_seconds", "offline"}
            if experiment == "FPE-001"
            else {"offline"}
        ):
            raise ValueError("Unknown study configuration")
        if experiment == "FPE-001" and (
            isinstance(cfg["shot_count"], bool)
            or not 5 <= cfg["shot_count"] <= 20
            or len(cfg["window_seconds"]) != 2
            or not -1 <= cfg["window_seconds"][0] < cfg["window_seconds"][1] <= 10
            or cfg["window_seconds"][1] - cfg["window_seconds"][0] > 2
        ):
            raise ValueError("Bounded comparable cohort/time window required")
        if not self.lock.acquire(False):
            raise ValueError("Another fusion analysis is active")
        try:
            if resume:
                job = self.store.get(resume)
                if not job or job["status"] not in (
                    "interrupted",
                    "failed",
                    "cancelled",
                ):
                    raise ValueError("Only incomplete jobs can resume")
                if job.get("parser_version") != PARSER_VERSION:
                    raise ValueError("Resume requires original parser version")
                cfg = job["parameters"]
                experiment = job["experiment"]
                job["status"] = "running"
            else:
                job = self.store.create("fusion", cfg)
                job.update(experiment=experiment, parser_version=PARSER_VERSION)
            folder = self.store.directory(job["id"])
            folder.mkdir(parents=True, exist_ok=True)
            cancel = folder / "cancel-requested"
            if cancel.exists():
                cancel.rename(folder / ("cancel-history-" + str(time.time_ns())))
            self.store.save(job)
            if asynchronous:
                threading.Thread(target=self.execute, args=(job,), daemon=True).start()
                return job
            self.execute(job)
            return self.store.get(job["id"])
        except BaseException:
            self.lock.release()
            raise

    def execute(self, job):
        folder = self.store.directory(job["id"])
        cache = FusionCache(self.root / "cache")
        start = time.monotonic()
        exp = job["experiment"]
        try:
            partial = folder / "sources-progress.json"
            if partial.exists():
                cache.expected = {r["url"]: r for r in json.loads(partial.read_text())}
                cache.allow_missing = True

            def source_progress(records):
                temp = folder / "sources-progress.new.json"
                temp.write_text(json.dumps(records, indent=2) + "\n")
                temp.replace(partial)

            cache.on_record = source_progress

            def progress(phase, n, total):
                job.update(phase=phase, progress={"completed": n, "planned": total})
                self.store.save(job)

            progress(
                "Acquiring selected official experiment data",
                0,
                job["parameters"].get("shot_count", 7),
            )
            fn = magnetic if exp == "FPE-001" else inertial
            r, phases = fn(
                cache,
                folder,
                job["parameters"],
                progress,
                lambda: (folder / "cancel-requested").exists(),
            )
            progress("Generating scientific report and original figures", 1, 2)
            tick = time.monotonic()
            plots = figures(r, folder)
            plot_time = time.monotonic() - tick
            try:
                commit = subprocess.check_output(
                    ["git", "rev-parse", "HEAD"],
                    cwd=Path(__file__).parents[1],
                    stderr=subprocess.DEVNULL,
                    text=True,
                ).strip()
            except subprocess.CalledProcessError:
                commit = "source-distribution-no-git"
            software = {
                k: importlib.metadata.version(k)
                for k in [
                    "numpy",
                    "scipy",
                    "pandas",
                    "xarray",
                    "zarr",
                    "dask",
                    "pint",
                    "pyhdf",
                    "matplotlib",
                    "fastapi",
                ]
            }
            rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            childrss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
            manifest = {
                "experiment_id": exp,
                "engine_version": "0.1.0",
                "git_commit_at_execution": commit,
                "working_source_files_sha256": {
                    p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in Path(__file__).parent.glob("*.py")
                },
                "parser_version": PARSER_VERSION,
                "algorithm_version": r["method_version"],
                "configuration": job["parameters"],
                "sources": list(cache.records.values()),
                "shot_ids": (
                    [x["shot_id"] for x in r.get("selection", [])]
                    if exp == "FPE-001"
                    else [x["identity"]["shot_id"] for x in r["images"]]
                ),
                "diagnostics": sorted(
                    {
                        x["identity"]["diagnostic"]
                        for x in r.get("signals", r.get("images", []))
                    }
                ),
                "random_seed": 20261106,
                "dependencies": software,
                "execution_environment": {
                    "system": platform.system(),
                    "release": platform.release(),
                    "architecture": platform.machine(),
                    "python": sys.version.split()[0],
                },
                "created_at": job["created_at"],
                "completed_at": now(),
                "results_sha256": r["results_sha256"],
                "validation_status": "computational_results_pending_separate_qualification",
                "data_derivative_license": r["data_derivative_license"],
                "source_data_terms_distinct_from_Apache": True,
                "performance": dict(
                    phases,
                    plot_generation_seconds=plot_time,
                    total_seconds=time.monotonic() - start,
                    network_bytes_this_run=cache.transport.network_bytes,
                    source_response_bytes=sum(
                        s["bytes"] for s in cache.records.values()
                    ),
                    unique_source_objects=len(cache.records),
                    process_peak_rss_bytes=int(
                        rss if platform.system() == "Darwin" else rss * 1024
                    ),
                    native_reader_child_peak_rss_bytes=int(
                        childrss if platform.system() == "Darwin" else childrss * 1024
                    ),
                    rss_scope="Whole process lifetime peak and separately reported child peak; not summed concurrent peaks; explicit resource/input/chunk bounds, no unmeasured hard RSS guarantee",
                ),
                "original_bytes_unchanged": True,
                "errors": [],
                "figures": plots,
            }
            artifacts = {
                exp + "_RESULTS.json": json.dumps(r, indent=2, allow_nan=False) + "\n",
                exp
                + "_MANIFEST.json": json.dumps(manifest, indent=2, allow_nan=False)
                + "\n",
                exp + "_FINDINGS.csv": findings_csv(r),
                exp + "_METHODOLOGY.md": methodology(r),
                exp + "_REPRODUCIBILITY.md": reproduction(r),
            }
            for name, text in artifacts.items():
                (folder / name).write_text(text)
            (folder / (exp + "_REPORT.html")).write_text(
                html_report(r, manifest, plots)
            )
            self.store.save_results(job["id"], r)
            job.update(
                status="completed",
                phase=exp + " computed; separate verification available",
                completed_at=manifest["completed_at"],
                summary=r["counts"],
                results_sha256=r["results_sha256"],
                duration_seconds=manifest["performance"]["total_seconds"],
                progress={"completed": 2, "planned": 2},
                errors=[],
            )
        except InterruptedError as e:
            job.update(
                status="cancelled",
                phase="Cancelled safely between bounded stages",
                errors=[str(e)],
            )
        except Exception as e:
            job.update(
                status="failed",
                phase="Experiment not completed",
                errors=[str(e)[:1500]],
            )
        finally:
            self.store.save(job)
            self.lock.release()

    def report(self, job_id):
        job = self.store.get(job_id)
        if not job:
            raise ValueError("Unknown fusion job")
        p = self.store.directory(job_id) / (job["experiment"] + "_RESULTS.json")
        if not p.is_file():
            raise ValueError("Fusion results not ready")
        return json.loads(p.read_text())

    def verify(self, job_id):
        r = self.report(job_id)
        job = self.store.get(job_id)
        manifest = json.loads(
            (
                self.store.directory(job_id) / (r["experiment"] + "_MANIFEST.json")
            ).read_text()
        )
        cache = FusionCache(self.root / "cache")
        cache.expected = {s["url"]: s for s in manifest["sources"]}
        for source in manifest["sources"]:
            cache.frozen(source)
        folder = self.store.directory(job_id) / ("raw-replay-" + uuid.uuid4().hex)
        folder.mkdir()
        tick = time.monotonic()
        fn = magnetic if r["experiment"] == "FPE-001" else inertial
        cfg = dict(r["configuration"], offline=True)
        replayed, timing = fn(cache, folder, cfg)
        passed = replayed["results_sha256"] == r["results_sha256"]
        return {
            "passed": passed,
            "experiment": r["experiment"],
            "sources_rehashed": len(manifest["sources"]),
            "network_used": False,
            "actual_results_sha256": replayed["results_sha256"],
            "expected_results_sha256": r["results_sha256"],
            "duration_seconds": time.monotonic() - tick,
            "verified_at": now(),
            "scope": "All original acquired bytes rehashed; selected chunks/HDF reparsed and all deterministic findings recomputed; no substituted vintage",
        }

# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Isolated persistent local jobs; no migration of the established engines."""

from pathlib import Path
import json, time, threading, uuid, hashlib, subprocess, platform, sys, resource, importlib.metadata, os
from research_core.jobs import JobStore
from research_core.locking import OperationLock
from research_core import now, validate_ollama
from esae.scanner import no_symlink, read_regular
from dynamics.experiments import clean, fingerprint
from . import __version__, PARSER_VERSION
from .ingestion import acquire, normalize, digest
from .discovery import connect, analyze
from .experiments import evaluate, what_if
from .twin import calibrate
from .reporting import exports


class OperationsEngine:
    def __init__(self, root, ollama_url=None, ollama_model=None):
        self.root = no_symlink(Path(root)).resolve()
        self.store = JobStore(self.root)
        self.lock = OperationLock(self.root / "active.lock")
        self.ollama_url = validate_ollama(ollama_url) if ollama_url else None
        self.ollama_model = ollama_model
        (self.root / "imports").mkdir(exist_ok=True, mode=0o700)

    def directory(self, id):
        return no_symlink(self.root / "jobs" / str(uuid.UUID(id)))

    def run(
        self, experiment="OTE-001", parameters=None, asynchronous=False, resume=None
    ):
        if experiment not in ("OTE-001", "OTE-002", "OTE-003", "WHATIF"):
            raise ValueError("Known Operations experiment required")
        cfg = {"offline": False, **(parameters or {})}
        allowed = (
            {"offline"}
            if experiment != "WHATIF"
            else {"offline", "cases", "replicates", "overrides"}
        )
        if set(cfg) - allowed:
            raise ValueError("Unknown study parameter")
        if experiment == "WHATIF":
            if (
                not 10 <= int(cfg.get("cases", 150)) <= 1500
                or not 2 <= int(cfg.get("replicates", 5)) <= 100
            ):
                raise ValueError("Bounded local scenario required")
            changes = cfg.get("overrides", {})
            bounds = {
                "demand_growth": (0, 1),
                "capacity_factor": (0.25, 2),
                "service_factor": (0.1, 2),
                "rework_factor": (0.1, 1),
            }
            if set(changes) - set(bounds) or any(
                not bounds[k][0] <= float(v) <= bounds[k][1] for k, v in changes.items()
            ):
                raise ValueError("Bounded known scenario modifications required")
        if not self.lock.acquire(False):
            raise ValueError("Another Operations job is active")
        try:
            if resume:
                j = self.store.get(resume)
                if (
                    not j
                    or j["status"] not in ("failed", "cancelled", "interrupted")
                    or j.get("parser_version") != PARSER_VERSION
                ):
                    raise ValueError(
                        "Only an incomplete job with the same parser can resume"
                    )
                j["status"] = "running"
                experiment = j["experiment"]
                cfg = j["parameters"]
            else:
                j = self.store.create("operations-twin", cfg)
                j.update(experiment=experiment, parser_version=PARSER_VERSION)
            folder = self.directory(j["id"])
            folder.mkdir(parents=True, exist_ok=True, mode=0o700)
            cancel = folder / "cancel-requested"
            if cancel.exists():
                cancel.rename(folder / ("cancel-history-" + str(time.time_ns())))
            self.store.save(j)
            if asynchronous:
                threading.Thread(target=self.execute, args=(j,), daemon=True).start()
                return j
            self.execute(j)
            return self.store.get(j["id"])
        except BaseException:
            self.lock.release()
            raise

    def execute(self, j):
        start = time.monotonic()
        folder = self.directory(j["id"])
        c = None
        try:

            def progress(phase, n, total):
                j.update(phase=phase, progress={"completed": n, "planned": total})
                self.store.save(j)

            cancel = lambda: (folder / "cancel-requested").exists()
            oldsources = self.root / "pinned-sources.json"
            expected = (
                json.loads(read_regular(oldsources, 100000))
                if oldsources.exists()
                else None
            )
            path, dataset, net = acquire(
                self.root,
                offline=j["parameters"]["offline"],
                expected=expected,
                cancel=cancel,
            )
            if not oldsources.exists():
                oldsources.write_text(json.dumps(dataset["sources"], indent=2))
                oldsources.chmod(0o600)
            normalized = self.root / "normalized-v1"
            m = normalize(
                path,
                normalized,
                expected_sha=dataset["original"]["sha256"],
                expected_events=1595923,
                progress=progress,
                cancel=cancel,
            )
            c = connect(self.root / "analysis", normalized)
            if (
                j["experiment"] == "OTE-001"
                or not (self.root / "observed.json").exists()
            ):
                observed, phases = analyze(c, m, dataset, progress, cancel)
                (self.root / "observed.json").write_text(json.dumps(observed, indent=2))
                (self.root / "observed-performance.json").write_text(json.dumps(phases))
            else:
                observed = json.loads(
                    read_regular(self.root / "observed.json", 8000000)
                )
                phases = {}
            from .discovery import sample_cohort

            replay = {}
            if j["experiment"] == "OTE-001":
                r = observed
            elif j["experiment"] == "OTE-002":
                r, model, rp, phases = evaluate(c, progress=progress, cancel=cancel)
                replay = {"selected": rp}
                (self.root / "calibrated-model.json").write_text(
                    json.dumps(model, separators=(",", ":"))
                )
                (self.root / "calibrated-model.json").chmod(0o600)
            else:
                model = calibrate(sample_cohort(c, "calibration"))
                cfg = j["parameters"]
                r, replay, phases = what_if(
                    c,
                    model,
                    replicates=cfg.get(
                        "replicates", 50 if j["experiment"] == "OTE-003" else 5
                    ),
                    cases=cfg.get(
                        "cases", 750 if j["experiment"] == "OTE-003" else 150
                    ),
                    progress=progress,
                    cancel=cancel,
                    overrides=cfg.get("overrides"),
                )
                if j["experiment"] == "WHATIF":
                    r = fingerprint({**r, "exploratory": True})
            perf = {
                "total_seconds_before_export": time.monotonic() - start,
                "normalization_seconds": m["elapsed_seconds"],
                "normalized_parquet_bytes": sum(v["bytes"] for v in m["parts"]),
                "stages": phases,
                "peak_process_RSS_bytes": resource.getrusage(
                    resource.RUSAGE_SELF
                ).ru_maxrss,
                "RSS_scope": "Process lifetime high-water mark, not incremental allocation of this job",
                "network_bytes_this_run": net,
            }
            try:
                commit = subprocess.check_output(
                    ["git", "rev-parse", "HEAD"],
                    cwd=Path(__file__).parents[1],
                    text=True,
                    stderr=subprocess.DEVNULL,
                ).strip()
            except (OSError, subprocess.CalledProcessError):
                commit = "source-distribution-no-git"
            sources = {
                str(p.relative_to(Path(__file__).parents[1])): digest(p)
                for p in list(Path(__file__).parent.glob("*.py"))
                + [
                    Path(__file__).parents[1] / "dynamics/events.py",
                    Path(__file__).parents[1] / "dynamics/experiment_core.py",
                    Path(__file__).parents[1] / "dynamics/experiments.py",
                ]
            }
            manifest = {
                "experiment_id": r["experiment"],
                "engine": "Operations Twin",
                "engine_version": __version__,
                "parser_version": PARSER_VERSION,
                "git_commit_at_execution": commit,
                "working_source_files_sha256": sources,
                "dataset": dataset,
                "acquired_at": dataset["acquired_at"],
                "executed_at": now(),
                "seed": 20261106,
                "parameters": j["parameters"],
                "scientific_result_sha256": r["results_sha256"],
                "environment": {
                    "python": platform.python_version(),
                    "platform": platform.platform(),
                    "machine": platform.machine(),
                    "hardware": (
                        subprocess.check_output(
                            ["/usr/sbin/sysctl", "-n", "machdep.cpu.brand_string"],
                            text=True,
                        ).strip()
                        if sys.platform == "darwin"
                        else platform.processor()
                    ),
                    "logical_cpus": os.cpu_count(),
                },
                "dependencies": {
                    x.metadata["Name"]: x.version
                    for x in importlib.metadata.distributions()
                },
                "validation_status": r.get(
                    "acceptance_scope", r.get("status", r["kind"])
                ),
                "performance": perf,
                "import": {
                    "events": m["counts"],
                    "parts": len(m["parts"]),
                    "input_sha256": m["input_sha256"],
                },
                "reproduction": "Pinned original/source hashes; offline original+partitions; rerun numerical pipeline; no LLM",
                "output_files": [
                    r["experiment"] + s
                    for s in [
                        "_REPORT.html",
                        "_RESULTS.json",
                        "_METRICS.csv",
                        "_MANIFEST.json",
                        "_METHODOLOGY.md",
                        "_REPRODUCIBILITY.md",
                    ]
                ],
            }
            files = exports(r, manifest, folder, replay)
            result_hashes = {
                f: digest(folder / f) for f in files if not f.endswith("_MANIFEST.json")
            }
            manifest["output_sha256"] = result_hashes
            (folder / (r["experiment"] + "_MANIFEST.json")).write_text(
                json.dumps(clean(manifest), indent=2) + "\n"
            )
            j.update(
                status="completed",
                phase="Computed and exported",
                completed_at=now(),
                result=r,
                result_files=files,
                performance={**perf, "total_seconds": time.monotonic() - start},
                sources=dataset["sources"],
                scientific_hash=r["results_sha256"],
            )
            self.store.save(j)
        except InterruptedError as e:
            j.update(status="cancelled", phase=str(e))
            self.store.save(j)
        except Exception as e:
            j.update(
                status="failed",
                phase="Computation failed",
                errors=j["errors"] + [str(e)[:1000]],
            )
            self.store.save(j)
        finally:
            if c:
                c.close()
            self.lock.release()

    def cancel(self, id):
        j = self.store.get(id)
        if not j or j["status"] != "running":
            raise ValueError("Active job required")
        (self.directory(id) / "cancel-requested").touch(mode=0o600)
        return {"requested": True}

    def reproduce(self, identifier):
        jobs = [
            x
            for x in self.store.list()
            if x.get("experiment") == identifier and x["status"] == "completed"
        ]
        j = (
            jobs[0]
            if jobs
            else self.store.get(identifier) if identifier.count("-") == 4 else None
        )
        if not j or j["status"] != "completed":
            raise ValueError("Completed job or experiment required")
        manifest = json.loads(
            read_regular(
                self.directory(j["id"])
                / (j["result"]["experiment"] + "_MANIFEST.json"),
                2000000,
            )
        )
        for name, sha in manifest["working_source_files_sha256"].items():
            if digest(Path(__file__).parents[1] / name) != sha:
                raise ValueError(
                    "Original implementation changed; use recorded source version for reproduction"
                )
        old = j["result"]["results_sha256"]
        new = self.run(j["experiment"], {**j["parameters"], "offline": True})
        return {
            "status": new["status"],
            "passed": new.get("scientific_hash") == old,
            "original": old,
            "recomputed": new.get("scientific_hash"),
            "job": new["id"],
        }

    def import_file(self, name, format, mapping=None):
        if not self.lock.acquire(False):
            raise ValueError("Another Operations job is active")
        try:
            return self._import_file(name, format, mapping)
        finally:
            self.lock.release()

    def _import_file(self, name, format, mapping=None):
        if Path(name).name != name or len(name) > 120:
            raise ValueError("Import filename only")
        keyfile = self.root / "private-import-key"
        if not keyfile.exists():
            with keyfile.open("xb") as f:
                os.chmod(keyfile, 0o600)
                f.write(os.urandom(32))
        path = no_symlink(self.root / "imports" / name)
        ident = digest(path)[:16]
        return normalize(
            path,
            self.root / "private-imports" / ident,
            format,
            mapping,
            drop_resources=True,
            privacy_key=read_regular(keyfile, 64),
        )

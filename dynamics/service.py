# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Persistent isolated Dynamics jobs and pinned offline source replay."""

from pathlib import Path
import json, time, uuid, threading, hashlib, subprocess, platform, sys, resource, importlib.metadata
from research_core.jobs import JobStore
from research_core.locking import OperationLock
from research_core import now, validate_ollama
from esae.scanner import no_symlink, read_regular
from . import PARSER_VERSION, __version__
from .acquisition import DataCache
from .experiments import clean, fingerprint, dme001, dme002, dme003
from .simulation import Simulation
from .mathematical import registry, GaussianMotion
from .reporting import figures, html_report, methodology, reproduce_text, metrics_csv

FUNCTIONS = {"DME-001": dme001, "DME-002": dme002, "DME-003": dme003}


class DynamicsStore(JobStore):
    def __init__(self, root):
        super().__init__(root)
        with self.connect() as db:
            db.executescript(
                "CREATE TABLE IF NOT EXISTS datasets(job TEXT PRIMARY KEY,data TEXT);CREATE TABLE IF NOT EXISTS results(job TEXT PRIMARY KEY,experiment TEXT,hash TEXT);CREATE TABLE IF NOT EXISTS models(id TEXT PRIMARY KEY,data TEXT);"
            )
            for m in registry():
                db.execute(
                    "INSERT OR REPLACE INTO models VALUES(?,?)",
                    (m["id"], json.dumps(m)),
                )

    def directory(self, id):
        return no_symlink(self.root / "jobs" / str(uuid.UUID(id)))


class DynamicsEngine:
    def __init__(self, root, ollama_url=None, ollama_model=None):
        self.store = DynamicsStore(root)
        self.root = self.store.root
        self.lock = OperationLock(self.root / "active.lock")
        self.ollama_url = validate_ollama(ollama_url) if ollama_url else None
        self.ollama_model = ollama_model

    def run(
        self, experiment="DME-001", parameters=None, asynchronous=False, resume=None
    ):
        if experiment not in (*FUNCTIONS, "SIMULATION"):
            raise ValueError("Known Dynamics experiment required")
        cfg = {"seed": 20261106}
        cfg.update(parameters or {})
        if experiment == "SIMULATION":
            Simulation(**{k: v for k, v in cfg.items() if k != "offline"})
        else:
            if set(cfg) - {"seed", "offline", "flights", "replicates"}:
                raise ValueError("Unknown study parameter")
            if (
                cfg.get("flights", 30) != 30
                or cfg.get("replicates", 20) != 20
                or cfg["seed"] != 20261106
            ):
                raise ValueError(
                    "Published study uses fixed cohort/seed; use Simulation Lab for exploratory parameters"
                )
        if not self.lock.acquire(False):
            raise ValueError("Another Dynamics job is active")
        try:
            if resume:
                j = self.store.get(resume)
                if (
                    not j
                    or j["status"] not in ("failed", "cancelled", "interrupted")
                    or j.get("parser_version") != PARSER_VERSION
                ):
                    raise ValueError(
                        "Only incomplete jobs with the original parser can resume"
                    )
                cfg = j["parameters"]
                experiment = j["experiment"]
                j["status"] = "running"
            else:
                j = self.store.create("dynamics", cfg)
                j.update(experiment=experiment, parser_version=PARSER_VERSION)
            folder = self.store.directory(j["id"])
            folder.mkdir(parents=True, exist_ok=True)
            c = folder / "cancel-requested"
            if c.exists():
                c.rename(folder / ("cancel-history-" + str(time.time_ns())))
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
        folder = self.store.directory(j["id"])
        cache = DataCache(self.root / "cache")
        exp = j["experiment"]
        try:
            partial = folder / "sources-progress.json"
            if partial.is_file():
                # Resumed acquisitions keep source metadata and already-read archive validators.
                cache.expected = {
                    s["key"]: s for s in json.loads(read_regular(partial, 8_000_000))
                }
                cache.allow_missing = True

            def sources(values):
                temp = folder / "sources-progress.new.json"
                temp.write_text(json.dumps(values, indent=2))
                temp.replace(partial)

            cache.on_record = sources

            def progress(phase, n, total):
                j.update(phase=phase, progress={"completed": n, "planned": total})
                self.store.save(j)

            cancel = lambda: (folder / "cancel-requested").exists()
            if exp == "SIMULATION":
                sim = Simulation(**j["parameters"])
                r = sim.run(cancel)
                r = self.add_estimates(r)
                r = fingerprint(
                    dict(
                        r,
                        experiment=exp,
                        status="computed",
                        counts=r["metrics"],
                        dataset={"source": "Synthetic abstract simulation"},
                    )
                )
                phases = {}
            else:
                r, phases = FUNCTIONS[exp](
                    cache, folder, j["parameters"], progress, cancel
                )
            plots = figures(r, folder) if exp != "SIMULATION" else []
            try:
                commit = subprocess.check_output(
                    ["git", "rev-parse", "HEAD"],
                    cwd=Path(__file__).parents[1],
                    text=True,
                    stderr=subprocess.DEVNULL,
                ).strip()
            except (OSError, subprocess.CalledProcessError):
                commit = "source-distribution-no-git"
            manifest = {
                "experiment_id": exp,
                "engine_version": __version__,
                "git_commit_at_execution": commit,
                "working_source_files_sha256": {
                    p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in Path(__file__).parent.glob("*.py")
                },
                "parser_version": PARSER_VERSION,
                "configuration": j["parameters"],
                "sources": list(cache.records.values()),
                "dataset": r["dataset"],
                "created_at": j["created_at"],
                "completed_at": now(),
                "dependencies": {
                    k: importlib.metadata.version(k)
                    for k in [
                        "numpy",
                        "scipy",
                        "pandas",
                        "pyarrow",
                        "PyYAML",
                        "fastapi",
                        "matplotlib",
                        "httpx",
                    ]
                },
                "execution_environment": {
                    "system": platform.system(),
                    "architecture": platform.machine(),
                    "python": sys.version.split()[0],
                },
                "results_sha256": r["results_sha256"],
                "validation_status": "computed; independently qualified by external acceptance evidence",
                "performance": dict(
                    phases,
                    total_seconds=time.monotonic() - start,
                    network_bytes_this_run=cache.downloaded
                    + cache.transport.network_bytes,
                    source_response_bytes=sum(
                        s["bytes"] for s in cache.records.values()
                    ),
                    process_peak_rss_bytes=int(
                        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                        * (1 if platform.system() == "Darwin" else 1024)
                    ),
                    rss_scope="Whole process lifetime peak; no unmeasured hard RSS guarantee",
                ),
                "figures": plots,
                "outputs": {},
            }
            files = {
                exp
                + "_RESULTS.json": json.dumps(clean(r), indent=2, allow_nan=False)
                + "\n"
            }
            if exp != "SIMULATION":
                files.update(
                    {
                        exp + "_METRICS.csv": metrics_csv(r),
                        exp + "_METHODOLOGY.md": methodology(r),
                        exp + "_REPRODUCIBILITY.md": reproduce_text(r),
                        exp + "_REPORT.html": html_report(r, manifest, plots),
                    }
                )
            for name, value in files.items():
                (folder / name).write_text(value)
                manifest["outputs"][name] = hashlib.sha256(
                    (folder / name).read_bytes()
                ).hexdigest()
            (folder / (exp + "_MANIFEST.json")).write_text(
                json.dumps(manifest, indent=2, allow_nan=False) + "\n"
            )
            with self.store.connect() as db:
                db.execute(
                    "INSERT OR REPLACE INTO datasets VALUES(?,?)",
                    (j["id"], json.dumps(r["dataset"])),
                )
                db.execute(
                    "INSERT OR REPLACE INTO results VALUES(?,?,?)",
                    (j["id"], exp, r["results_sha256"]),
                )
            j.update(
                status="completed",
                phase="Computed; reports and source manifest ready",
                completed_at=manifest["completed_at"],
                summary=r["counts"],
                results_sha256=r["results_sha256"],
                duration_seconds=manifest["performance"]["total_seconds"],
                progress={"completed": 1, "planned": 1},
                errors=[],
            )
        except InterruptedError as e:
            j.update(
                status="cancelled",
                phase="Cancelled between bounded stages",
                errors=[str(e)],
            )
        except Exception as e:
            j.update(
                status="failed", phase="Analysis not completed", errors=[str(e)[:1200]]
            )
        finally:
            self.store.save(j)
            self.lock.release()

    @staticmethod
    def add_estimates(r):
        import numpy as np

        c = r["configuration"]
        obs = np.array(r["observed_position"], float)
        n = c["agents"]
        d = c["dimensions"]
        state = []
        cov = []
        models = []
        for i in range(n):
            k = GaussianMotion(
                "KF", d, q=max(0.0001, c["noise"] ** 2), r=c["observation_sigma"] ** 2
            )
            x = np.zeros(2 * d)
            finite = np.isfinite(obs[0, i]).all()
            if finite:
                x[:d] = obs[0, i]
            k.initialize(x, np.eye(2 * d) * 100)
            models.append((k, finite))
        for t in range(len(obs)):
            ms = []
            ps = []
            for i, (k, initialized) in enumerate(models):
                z = obs[t, i]
                valid = np.isfinite(z).all()
                if not initialized and valid:
                    x = np.zeros(2 * d)
                    x[:d] = z
                    k.initialize(x, np.eye(2 * d) * 100)
                    initialized = True
                    models[i] = (k, True)
                if t:
                    k.predict(c["dt"])
                if valid:
                    k.update(z)
                ms.append(k.x[:d].tolist() if initialized else [None] * d)
                ps.append(k.p[:d, :d].tolist() if initialized else None)
            state.append(ms)
            cov.append(ps)
        r["estimated_position"] = state
        r["estimated_covariance"] = cov
        r["estimate_limits"] = (
            "Exploratory CV Kalman estimates from simulated noisy observations only; not tuned or validated for all interacting scenarios. Unobserved initial agents remain unavailable until first observation."
        )
        return r

    def report(self, id):
        j = self.store.get(id)
        if not j:
            raise ValueError("Unknown Dynamics job")
        return json.loads(
            read_regular(
                self.store.directory(id) / (j["experiment"] + "_RESULTS.json"),
                32_000_000,
            )
        )

    def verify(self, id):
        j = self.store.get(id)
        r = self.report(id)
        folder = self.store.directory(id)
        m = json.loads(
            read_regular(folder / (j["experiment"] + "_MANIFEST.json"), 16_000_000)
        )
        cache = DataCache(self.root / "cache")
        cache.expected = {s["key"]: s for s in m["sources"]}
        for s in m["sources"]:
            cache.frozen(s)
        target = folder / ("raw-replay-" + uuid.uuid4().hex)
        target.mkdir()
        tick = time.monotonic()
        if j["experiment"] == "SIMULATION":
            s = Simulation(**j["parameters"])
            v = fingerprint(
                dict(
                    self.add_estimates(s.run()),
                    experiment="SIMULATION",
                    status="computed",
                    counts=s.result()["metrics"],
                    dataset={"source": "Synthetic abstract simulation"},
                )
            )
        else:
            v, _ = FUNCTIONS[j["experiment"]](
                cache, target, dict(j["parameters"], offline=True)
            )
        return {
            "passed": v["results_sha256"] == r["results_sha256"],
            "expected": r["results_sha256"],
            "actual": v["results_sha256"],
            "sources_rehashed": len(m["sources"]),
            "network_used": False,
            "duration_seconds": time.monotonic() - tick,
            "verified_at": now(),
        }

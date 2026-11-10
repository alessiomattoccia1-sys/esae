# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Local immutable-source study orchestration and exact frozen-vintage replay."""

from pathlib import Path
from dataclasses import asdict
from collections import Counter
import json, time, threading, hashlib, importlib.metadata, sys, datetime
from research_core import now, validate_ollama
from research_core.locking import OperationLock
from .connectors import FinancialCache, InstitutionalConnector, SOURCES
from .parsers import parse
from .analysis import StudyConfig, analyze, clean
from .storage import FinancialStore
from .report import html_report, findings_csv, methodology, reproduction, NYFED_NOTICE
from . import PARSER_VERSION


class FinancialEngine:
    def __init__(self, root, *, ollama_url=None, ollama_model=None):
        self.store = FinancialStore(root)
        self.root = self.store.root
        self.lock = OperationLock(self.root / "active.lock")
        self.cache = FinancialCache(self.root / "cache")
        self.ollama_url = validate_ollama(ollama_url) if ollama_url else None
        self.ollama_model = ollama_model

    def phase(self, job, name, done=0, total=0):
        job.update(phase=name, progress={"completed": done, "planned": total})
        self.store.save(job)

    def run(self, config=None, *, refresh=False, asynchronous=False, resume=None):
        config = (config or StudyConfig()).validate()
        if not self.lock.acquire(False):
            raise ValueError("A financial operation is already running")
        try:
            if resume:
                job = self.store.get(resume)
                if not job or job["status"] not in ("failed", "partial", "interrupted"):
                    raise ValueError("Only an incomplete study can resume")
                if job.get("parser_version") != PARSER_VERSION:
                    raise ValueError("Resume requires matching original parser version")
                config = StudyConfig(**job["parameters"]).validate()
                job["status"] = "running"
                refresh = False
            else:
                job = self.store.create("financial", asdict(config))
                job["parser_version"] = PARSER_VERSION
            folder = self.store.directory(job["id"])
            folder.mkdir(parents=True, exist_ok=True)
            self.store.save(job)
            if asynchronous:
                threading.Thread(
                    target=self.execute, args=(job, config, refresh), daemon=True
                ).start()
                return job
            self.execute(job, config, refresh)
            return self.store.get(job["id"])
        except BaseException:
            self.lock.release()
            raise

    def normalize_sources(self, records, config, update_revisions=False):
        counts = Counter()
        selected = {}
        source_counts = []
        for record in records:
            rows, stats = parse(self.cache.frozen(record), record)
            counts.update(stats)
            source_counts.append(
                {
                    "source_sha256": record["sha256"],
                    "counts": stats,
                    "period": {
                        "start": min(r["observation_date"] for r in rows),
                        "end": max(r["observation_date"] for r in rows),
                    },
                    "series": sorted({r["series_id"] for r in rows}),
                }
            )
            for r in rows:
                if not config.start <= r["observation_date"] <= config.end:
                    counts["excluded_outside_configured_period"] += 1
                    continue
                key = (r["series_id"], r["observation_date"])
                if key in selected:
                    if selected[key]["value"] != r["value"]:
                        raise ValueError(
                            "Cross-source conflicting observation identity"
                        )
                    counts["identical_duplicates"] += 1
                else:
                    selected[key] = r
        values = sorted(
            selected.values(), key=lambda r: (r["observation_date"], r["series_id"])
        )
        counts["stored_unique_period_observations"] = len(values)
        revisions = self.store.revisions(values) if update_revisions else None
        return values, dict(counts), source_counts, revisions

    def execute(self, job, config, refresh):
        start = time.monotonic()
        folder = self.store.directory(job["id"])
        try:
            self.phase(job, "Acquiring official institutional sources")
            frozen = (
                json.loads((folder / "sources.json").read_text())
                if (folder / "sources.json").exists()
                else []
            )
            manual = self.root / "manual-sources.json"
            if manual.exists():
                for record in json.loads(manual.read_text()):
                    if record["url"] not in {r["url"] for r in frozen}:
                        frozen.append(record)

            def progress(records, done, total):
                (folder / "sources.json").write_text(
                    json.dumps(records, indent=2) + "\n"
                )
                self.phase(job, "Acquiring official institutional sources", done, total)

            sources = InstitutionalConnector(self.cache).acquire(
                config.end, refresh=refresh, frozen=frozen, progress=progress
            )
            self.phase(job, "Normalizing dates, units, vintages and revisions")
            rows, ingestion, source_counts, revisions = self.normalize_sources(
                sources, config, True
            )
            for source in sources:
                self.store.record_source(source)
            if (
                not rows
                or ingestion.get("invalid_observations", 0)
                or ingestion.get("invalid_rows", 0)
            ):
                raise ValueError(
                    "Official source has invalid records; inspect import audit before scientific publication"
                )
            self.phase(
                job,
                "Building partitioned Parquet and analytical database",
                len(rows),
                len(rows),
            )
            storage = self.store.write_snapshot(job["id"], rows)
            metadata = self.store.series(job["id"])
            frame = self.store.frame(job["id"])
            self.phase(
                job,
                "Computing historical regimes, dependence-aware statistics and anomalies",
            )
            report, weekly = analyze(frame, metadata, ingestion, config)
            for source in sources:
                source["source_period_and_counts"] = next(
                    x for x in source_counts if x["source_sha256"] == source["sha256"]
                )
            report.update(
                sources=sources,
                ingestion=ingestion,
                created_at=job["created_at"],
                completed_at=now(),
                duration_seconds=round(time.monotonic() - start, 3),
                source_data_terms={k: SOURCES[k]["terms"] for k in SOURCES},
                nyfed_notice=NYFED_NOTICE,
            )
            software = {
                name: importlib.metadata.version(name)
                for name in [
                    "duckdb",
                    "pyarrow",
                    "pandas",
                    "numpy",
                    "scipy",
                    "statsmodels",
                    "fastapi",
                ]
            }
            software["python"] = sys.version.split()[0]
            manifest = {
                "experiment": "FSIE-001",
                "engine_version": "0.1.0",
                "parser_version": PARSER_VERSION,
                "method_version": report["method_version"],
                "configuration": asdict(config),
                "sources": sources,
                "ingestion": ingestion,
                "source_counts": source_counts,
                "storage": storage,
                "revisions": revisions,
                "software": software,
                "analysis_sha256": report["analysis_sha256"],
                "source_code_sha256": {
                    p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in Path(__file__).parent.glob("*.py")
                },
                "dates_policy": "Observation date distinct from publication, source update, acquisition and vintage. Historical publication timestamps unavailable -> null; retrospective current-vintage study only.",
                "source_license_policy": "Institutional terms separate from Apache2.0 originalcode; raw responses/fullseries staylocal, no blanket publicredistribution",
                "nyfed_notice": NYFED_NOTICE,
                "duration_seconds": report["duration_seconds"],
                "errors": [],
            }
            self.store.save_results(job["id"], report, weekly)
            artifacts = {
                "FSIE-001_RESULTS.json": json.dumps(report, indent=2, allow_nan=False)
                + "\n",
                "FSIE-001_MANIFEST.json": json.dumps(
                    manifest, indent=2, allow_nan=False
                )
                + "\n",
                "FSIE-001_FINDINGS.csv": findings_csv(report),
                "FSIE-001_METHODOLOGY.md": methodology(report),
                "FSIE-001_REPRODUCIBILITY.md": reproduction(report),
                "FSIE-001_REPORT.html": html_report(report),
            }
            for name, text in artifacts.items():
                (folder / name).write_text(text)
            job.update(
                status="completed",
                phase="FSIE-001 completed",
                completed_at=report["completed_at"],
                duration_seconds=report["duration_seconds"],
                summary=report["coverage"],
                analysis_sha256=report["analysis_sha256"],
                progress={"completed": len(rows), "planned": len(rows)},
                errors=[],
            )
        except Exception as exc:
            job.update(
                status="failed",
                phase="Scientific study not completed",
                completed_at=now(),
                duration_seconds=round(time.monotonic() - start, 3),
                errors=[str(exc)[:1000]],
            )
        finally:
            self.store.save(job)
            self.lock.release()

    def report(self, job_id):
        if not self.store.get(job_id):
            raise ValueError("Unknown study")
        path = self.store.directory(job_id) / "FSIE-001_RESULTS.json"
        if not path.is_file():
            raise ValueError("Study results not ready")
        return json.loads(path.read_text())

    def verify(self, job_id):
        report = self.report(job_id)
        config = StudyConfig(**report["configuration"]).validate()
        rows, counts, source_counts, _ = self.normalize_sources(
            report["sources"], config
        )
        import pandas as pd

        frame = pd.DataFrame(rows)[["series_id", "observation_date", "value"]]
        result, _ = analyze(frame, report["series_metadata"], counts, config)
        passed = (
            result["analysis_sha256"] == report["analysis_sha256"]
            and counts == report["ingestion"]
        )
        return {
            "passed": passed,
            "network_used": False,
            "sources_rehashed": len(report["sources"]),
            "observations_reparsed": counts["observations_seen"],
            "stored_unique_period_observations": len(rows),
            "analysis_sha256": result["analysis_sha256"],
            "expected": report["analysis_sha256"],
            "verified_at": now(),
            "scope": "Full raw immutable response replay of the exact acquired vintage; no historical real-time predictive claim",
        }

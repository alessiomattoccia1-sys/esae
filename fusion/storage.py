# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Separate fusion registry; no migrations of other engines' databases."""

import json, uuid
from pathlib import Path
from research_core.jobs import JobStore
from esae.scanner import no_symlink


class FusionStore(JobStore):
    def __init__(self, root):
        super().__init__(root)
        with self.connect() as db:
            db.executescript(
                """CREATE TABLE IF NOT EXISTS experiments(id TEXT PRIMARY KEY,data TEXT);CREATE TABLE IF NOT EXISTS datasets(id TEXT PRIMARY KEY,data TEXT);CREATE TABLE IF NOT EXISTS shots(id TEXT,experiment TEXT,data TEXT,PRIMARY KEY(id,experiment));CREATE TABLE IF NOT EXISTS diagnostics(id TEXT,experiment TEXT,data TEXT,PRIMARY KEY(id,experiment));CREATE TABLE IF NOT EXISTS measurements(id TEXT PRIMARY KEY,experiment TEXT,shot TEXT,diagnostic TEXT,data TEXT);CREATE TABLE IF NOT EXISTS analyses(id TEXT PRIMARY KEY,experiment TEXT,data TEXT);CREATE TABLE IF NOT EXISTS findings(id TEXT,job TEXT,data TEXT,PRIMARY KEY(id,job));"""
            )

    def directory(self, job):
        p = self.root / "jobs" / str(uuid.UUID(job))
        no_symlink(p)
        return p

    def save_results(self, job, r):
        exp = r["experiment"]
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO experiments VALUES(?,?)",
                (
                    exp,
                    json.dumps(
                        {
                            "experiment_id": exp,
                            "confinement": (
                                "magnetic" if exp == "FPE-001" else "inertial"
                            ),
                            "facility": (
                                "MAST / UKAEA"
                                if exp == "FPE-001"
                                else "OMEGA / STFC eData"
                            ),
                            "dataset": r["dataset"],
                        }
                    ),
                ),
            )
            db.execute(
                "INSERT OR REPLACE INTO datasets VALUES(?,?)",
                (job, json.dumps(r["dataset"])),
            )
            db.execute(
                "INSERT OR REPLACE INTO analyses VALUES(?,?,?)",
                (
                    job,
                    exp,
                    json.dumps(
                        {
                            "method_version": r["method_version"],
                            "configuration": r["configuration"],
                            "results_sha256": r["results_sha256"],
                        }
                    ),
                ),
            )
            for finding in r["findings"]:
                db.execute(
                    "INSERT OR REPLACE INTO findings VALUES(?,?,?)",
                    (finding["id"], job, json.dumps(finding)),
                )
            for item in r.get("signals", r.get("images", [])):
                identity = item["identity"]
                shot = str(identity["shot_id"])
                diag = identity["diagnostic"]
                db.execute(
                    "INSERT OR REPLACE INTO shots VALUES(?,?,?)",
                    (
                        shot,
                        exp,
                        json.dumps(
                            identity.get("shot_catalog_metadata", {"shot_id": shot})
                        ),
                    ),
                )
                db.execute(
                    "INSERT OR REPLACE INTO diagnostics VALUES(?,?,?)",
                    (
                        diag,
                        exp,
                        json.dumps(
                            {
                                "diagnostic_id": diag,
                                "units": identity.get(
                                    "unit", "uncalibrated detector units"
                                ),
                                "calibration": identity.get(
                                    "calibration_status",
                                    "Source calibration uncertainty not provided",
                                ),
                            }
                        ),
                    ),
                )
                mid = job + ":" + shot + ":" + diag
                db.execute(
                    "INSERT OR REPLACE INTO measurements VALUES(?,?,?,?,?)",
                    (mid, exp, shot, diag, json.dumps(identity)),
                )

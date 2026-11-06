# SPDX-License-Identifier: Apache-2.0
"""SQLite provenance/revisions plus bounded DuckDB and partitioned Parquet."""

from pathlib import Path
import json, hashlib, datetime
import duckdb, pyarrow as pa
from research_core.jobs import JobStore
from esae.scanner import no_symlink

SCHEMA = pa.schema(
    [
        ("series_id", pa.string()),
        ("observation_date", pa.date32()),
        ("value", pa.float64()),
        ("unit", pa.string()),
        ("frequency", pa.string()),
        ("source_id", pa.string()),
        ("source_sha256", pa.string()),
        ("publication_at", pa.string()),
        ("source_updated_at", pa.string()),
        ("acquired_at", pa.string()),
        ("vintage_at", pa.string()),
        ("vintage_kind", pa.string()),
        ("revision_flag", pa.string()),
        ("parser_version", pa.string()),
        ("year", pa.int32()),
    ]
)


class FinancialStore(JobStore):
    def __init__(self, root):
        super().__init__(root)
        with self.connect() as db:
            db.executescript(
                """CREATE TABLE IF NOT EXISTS data_sources(sha TEXT PRIMARY KEY,url TEXT,source TEXT,data TEXT);CREATE TABLE IF NOT EXISTS release_metadata(id TEXT PRIMARY KEY,source_sha TEXT,acquired TEXT,data TEXT);CREATE TABLE IF NOT EXISTS series_metadata(job_id TEXT,series TEXT,data TEXT,PRIMARY KEY(job_id,series));CREATE TABLE IF NOT EXISTS observation_versions(series TEXT,date TEXT,source_sha TEXT,value REAL,acquired TEXT,PRIMARY KEY(series,date,source_sha));CREATE TABLE IF NOT EXISTS data_revisions(id TEXT PRIMARY KEY,series TEXT,date TEXT,old_sha TEXT,new_sha TEXT,old_value REAL,new_value REAL,acquired TEXT);CREATE TABLE IF NOT EXISTS research_findings(job_id TEXT,id TEXT,data TEXT,PRIMARY KEY(job_id,id));CREATE TABLE IF NOT EXISTS scientific_experiments(job_id TEXT PRIMARY KEY,data TEXT);CREATE INDEX IF NOT EXISTS observation_history ON observation_versions(series,date,acquired);"""
            )

    def record_source(self, source):
        with self.lock, self.connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO data_sources VALUES(?,?,?,?)",
                (
                    source["sha256"],
                    source["url"],
                    source["source_id"],
                    json.dumps(source),
                ),
            )
            identity = hashlib.sha256(
                (source["sha256"] + source["url"] + source["acquired_at"]).encode()
            ).hexdigest()
            db.execute(
                "INSERT OR IGNORE INTO release_metadata VALUES(?,?,?,?)",
                (identity, source["sha256"], source["acquired_at"], json.dumps(source)),
            )

    def revisions(self, rows):
        inserted = 0
        revised = 0
        with self.lock, self.connect() as db:
            for r in rows:
                args = (r["series_id"], r["observation_date"])
                exists = db.execute(
                    "SELECT 1 FROM observation_versions WHERE series=? AND date=? AND source_sha=?",
                    args + (r["source_sha256"],),
                ).fetchone()
                if exists:
                    continue
                prior = db.execute(
                    "SELECT source_sha,value FROM observation_versions WHERE series=? AND date=? ORDER BY acquired DESC LIMIT 1",
                    args,
                ).fetchone()
                db.execute(
                    "INSERT INTO observation_versions VALUES(?,?,?,?,?)",
                    args + (r["source_sha256"], r["value"], r["acquired_at"]),
                )
                inserted += 1
                if prior and prior[1] != r["value"]:
                    key = hashlib.sha256(
                        json.dumps([*args, prior[0], r["source_sha256"]]).encode()
                    ).hexdigest()
                    db.execute(
                        "INSERT OR IGNORE INTO data_revisions VALUES(?,?,?,?,?,?,?,?)",
                        (
                            key,
                            *args,
                            prior[0],
                            r["source_sha256"],
                            prior[1],
                            r["value"],
                            r["acquired_at"],
                        ),
                    )
                    revised += 1
        return {
            "new_observation_versions": inserted,
            "changed_values_vs_prior_acquisition": revised,
        }

    def directory(self, job_id):
        import uuid

        p = self.root / "jobs" / str(uuid.UUID(job_id))
        no_symlink(p)
        return p

    def analytical(self, job_id, read_only=False):
        p = self.directory(job_id) / "warehouse.duckdb"
        no_symlink(p)
        db = duckdb.connect(str(p), read_only=read_only)
        db.execute("SET memory_limit='512MB'")
        db.execute("SET threads=2")
        return db

    def write_snapshot(self, job_id, rows):
        folder = self.directory(job_id)
        folder.mkdir(parents=True, exist_ok=True)
        parts = folder / "parquet"
        no_symlink(parts)
        # One immutable Parquet snapshot per job, rebuilt only for explicit interrupted resume.
        with self.analytical(job_id) as db:
            db.execute(
                "CREATE OR REPLACE TABLE observations(series_id VARCHAR,observation_date DATE,value DOUBLE,unit VARCHAR,frequency VARCHAR,source_id VARCHAR,source_sha256 VARCHAR,publication_at VARCHAR,source_updated_at VARCHAR,acquired_at VARCHAR,vintage_at VARCHAR,vintage_kind VARCHAR,revision_flag VARCHAR,parser_version VARCHAR,year INTEGER)"
            )
            for i in range(0, len(rows), 5000):
                batch = [
                    dict(
                        r,
                        observation_date=datetime.date.fromisoformat(
                            r["observation_date"]
                        ),
                        year=int(r["observation_date"][:4]),
                    )
                    for r in rows[i : i + 5000]
                ]
                table = pa.Table.from_pylist(batch, schema=SCHEMA)
                db.register("incoming", table)
                db.execute("INSERT INTO observations SELECT * FROM incoming")
                db.unregister("incoming")
            duplicate = db.execute(
                "SELECT series_id,observation_date,count(*) FROM observations GROUP BY 1,2 HAVING count(*)>1 LIMIT 1"
            ).fetchone()
            if duplicate:
                raise ValueError("Conflicting duplicate in analytic snapshot")
            if parts.exists():
                # Preserve older partial snapshot rather than delete unknown evidence.
                import time

                parts.rename(folder / ("partial-parquet-" + str(time.time_ns())))
            db.execute(
                "COPY (SELECT * FROM observations ORDER BY year,series_id,observation_date) TO ? (FORMAT PARQUET,PARTITION_BY(year),COMPRESSION ZSTD,ROW_GROUP_SIZE 122880)",
                [str(parts)],
            )
            db.execute(
                "CREATE OR REPLACE VIEW parquet_observations AS SELECT * FROM read_parquet('"
                + str(parts / "year=*/*.parquet").replace("'", "''")
                + "',hive_partitioning=true)"
            )
            count = db.execute("SELECT count(*) FROM parquet_observations").fetchone()[
                0
            ]
            if count != len(rows):
                raise ValueError("Parquet record count mismatch")
            db.execute(
                "CREATE OR REPLACE TABLE derived_indicators(observation_date DATE,indicator VARCHAR,value DOUBLE,unit VARCHAR)"
            )
        return {
            "rows": count,
            "partitions": len(list(parts.glob("year=*"))),
            "parquet_bytes": sum(p.stat().st_size for p in parts.rglob("*.parquet")),
            "memory_limit_bytes": 512_000_000,
            "threads": 2,
        }

    def series(self, job_id):
        with self.analytical(job_id, True) as db:
            data = db.execute(
                "SELECT series_id,source_id,unit,frequency,count(*),count(value),min(observation_date),max(observation_date) FROM parquet_observations GROUP BY 1,2,3,4 ORDER BY 1"
            ).fetchall()
        return [
            {
                "series_id": a,
                "source_id": b,
                "unit": c,
                "frequency": d,
                "observations": e,
                "present": f,
                "missing": e - f,
                "start": str(g),
                "end": str(h),
            }
            for a, b, c, d, e, f, g, h in data
        ]

    def frame(self, job_id):
        with self.analytical(job_id, True) as db:
            return db.execute(
                "SELECT series_id,observation_date,value FROM parquet_observations ORDER BY observation_date,series_id"
            ).df()

    def explorer(
        self,
        job_id,
        series=None,
        start=None,
        end=None,
        source=None,
        frequency=None,
        unit=None,
        limit=500,
        offset=0,
    ):
        query = " FROM parquet_observations WHERE TRUE"
        params = []
        for column, op, value in [
            ("series_id", "=", series),
            ("observation_date", ">=", start),
            ("observation_date", "<=", end),
            ("source_id", "=", source),
            ("frequency", "=", frequency),
            ("unit", "=", unit),
        ]:
            if value is not None:
                query += " AND " + column + op + "?"
                params.append(value)
        with self.analytical(job_id, True) as db:
            total = db.execute("SELECT count(*)" + query, params).fetchone()[0]
            cursor = db.execute(
                "SELECT * EXCLUDE(year)"
                + query
                + " ORDER BY observation_date DESC,series_id LIMIT ? OFFSET ?",
                params + [min(1000, max(1, limit)), max(0, offset)],
            )
            keys = [v[0] for v in cursor.description]
            rows = [dict(zip(keys, v)) for v in cursor.fetchall()]
        for r in rows:
            r["observation_date"] = str(r["observation_date"])
        return {"total": total, "offset": offset, "items": rows}

    def save_results(self, job_id, report, weekly):
        with self.connect() as db:
            for f in report["findings"]:
                db.execute(
                    "INSERT OR REPLACE INTO research_findings VALUES(?,?,?)",
                    (job_id, f["id"], json.dumps(f)),
                )
            db.execute(
                "INSERT OR REPLACE INTO scientific_experiments VALUES(?,?)",
                (
                    job_id,
                    json.dumps(
                        {
                            "experiment": "FSIE-001",
                            "analysis_sha256": report["analysis_sha256"],
                        }
                    ),
                ),
            )
            for s in report["series_metadata"]:
                db.execute(
                    "INSERT OR REPLACE INTO series_metadata VALUES(?,?,?)",
                    (job_id, s["series_id"], json.dumps(s)),
                )
        with self.analytical(job_id) as db:
            for col in ["spread_10y2y_bp", "spread_10y3m_bp"]:
                rows = [
                    (date.date(), col, float(value), "basis_points")
                    for date, value in weekly[col].dropna().items()
                ]
                db.executemany("INSERT INTO derived_indicators VALUES(?,?,?,?)", rows)

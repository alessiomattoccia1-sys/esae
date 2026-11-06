# SPDX-License-Identifier: Apache-2.0
"""Separate deterministic SYNTHETIC scalability test, never scientific evidence."""

from pathlib import Path
import datetime, hashlib, json, os, platform, resource, shutil, subprocess, time, uuid, statistics
import duckdb


def run(root, rows=20_000_000):
    if isinstance(rows, bool) or not 10_000 <= rows <= 50_000_000:
        raise ValueError("Benchmark row bound10000..50000000")
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(root).free < 5_000_000_000:
        raise ValueError("At least5GB free required before benchmark")
    folder = root / (
        datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S")
        + "-"
        + uuid.uuid4().hex[:8]
    )
    folder.mkdir()
    parts = folder / "parquet"
    start = time.monotonic()
    db = duckdb.connect(
        str(folder / "analytical.duckdb"),
        config={
            "memory_limit": "512MB",
            "threads": "2",
            "temp_directory": str(folder / "spill"),
        },
    )
    begin = time.monotonic()
    db.execute(
        "COPY (SELECT DATE '2000-01-01'+CAST(floor(i/10000) AS INTEGER) AS observation_date,CAST(i%10000 AS INTEGER) AS series_id,sin(i*.001)+cos((i%10000)*.1) AS value,year(DATE '2000-01-01'+CAST(floor(i/10000) AS INTEGER)) AS year FROM range(?) t(i)) TO ? (FORMAT PARQUET,PARTITION_BY(year),COMPRESSION ZSTD,ROW_GROUP_SIZE 122880)",
        [rows, str(parts)],
    )
    generation = time.monotonic() - begin
    literal = str(parts / "year=*/*.parquet").replace("'", "''")
    db.execute(
        "CREATE VIEW source_parquet AS SELECT * FROM read_parquet('"
        + literal
        + "',hive_partitioning=true)"
    )
    begin = time.monotonic()
    db.execute("CREATE TABLE loaded_observations AS SELECT * FROM source_parquet")
    loading = time.monotonic() - begin
    queries = {
        "count_metadata": "SELECT count(*) FROM source_parquet",
        "time_series_filter": "SELECT count(*),avg(value) FROM source_parquet WHERE observation_date BETWEEN DATE '2002-01-01' AND DATE '2002-01-31' AND series_id BETWEEN 100 AND 199",
        "group_aggregation": "SELECT series_id,count(*),avg(value),stddev_samp(value) FROM source_parquet GROUP BY series_id ORDER BY series_id",
        "full_scan_sum": "SELECT sum(value),min(value),max(value) FROM source_parquet",
    }
    results = {}
    for name, query in queries.items():
        times = []
        hashes = []
        sample = []
        n = 0
        for repeat in range(3):
            begin = time.monotonic()
            data = db.execute(query).fetchall()
            times.append(time.monotonic() - begin)
            raw = json.dumps(data, separators=(",", ":")).encode()
            hashes.append(hashlib.sha256(raw).hexdigest())
            sample = data[:3]
            n = len(data)
        # Parallel floating aggregation can differ in low bits: hashes retained, no bitwise-associativity claim.
        results[name] = {
            "sql": query,
            "seconds": times,
            "median_seconds": statistics.median(times),
            "result_rows": n,
            "result_sha256": hashes,
            "first_rows": sample,
            "cache_state": "firstobserved then warm; OS caches not forcibly dropped",
        }
    count = results["count_metadata"]["first_rows"][0][0]
    assert count == rows
    a = (datetime.date(2002, 1, 1) - datetime.date(2000, 1, 1)).days
    b = (datetime.date(2002, 1, 31) - datetime.date(2000, 1, 1)).days
    expected = sum(
        max(0, min(200, rows - day * 10000) - 100)
        for day in range(a, b + 1)
        if rows > day * 10000
    )
    assert results["time_series_filter"]["first_rows"][0][0] == expected
    db.close()
    files = [
        {
            "name": p.relative_to(folder).as_posix(),
            "bytes": p.stat().st_size,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        }
        for p in sorted(parts.rglob("*.parquet"))
    ]
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    rss_bytes = int(rss if platform.system() == "Darwin" else rss * 1024)

    def sysctl(key):
        p = subprocess.run(
            ["/usr/sbin/sysctl", "-n", key], capture_output=True, text=True
        )
        return p.stdout.strip() if p.returncode == 0 else None

    result = {
        "benchmark": "FSIE-BIGDATA-001",
        "classification": "SYNTHETIC_TECHNICAL_ONLY_NOT_FINANCIAL_RESEARCH",
        "rows": rows,
        "generator": "range(i),10000series,date2000-01-01+floor(i/10000),value=sin(i*.001)+cos((i%10000)*.1);deterministic,no market observations",
        "duckdb_version": duckdb.__version__,
        "machine": {
            "system": platform.system(),
            "release": platform.release(),
            "architecture": platform.machine(),
            "chip": sysctl("machdep.cpu.brand_string"),
            "physical_memory_bytes": int(sysctl("hw.memsize") or 0),
        },
        "settings": {
            "memory_limit": "512MB",
            "threads": 2,
            "row_group_size": 122880,
            "compression": "ZSTD",
            "partition": "year",
        },
        "generation_parquet_write_seconds": generation,
        "parquet_load_into_duckdb_seconds": loading,
        "parquet_bytes": sum(f["bytes"] for f in files),
        "parquet_files": len(files),
        "year_partitions": len(list(parts.glob("year=*"))),
        "loaded_database_bytes": (folder / "analytical.duckdb").stat().st_size,
        "process_peak_rss_bytes": rss_bytes,
        "rss_scope": "Whole fresh CLI process peak includes Python/imports; not an assertion of engine-only memory",
        "query_results": results,
        "expected_count": rows,
        "expected_time_filter_rows": expected,
        "files": files,
        "duration_seconds": time.monotonic() - start,
        "finished_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "passed": True,
    }
    (folder / "FSIE-BENCHMARK.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Benchmark folder:", folder, flush=True)
    return result

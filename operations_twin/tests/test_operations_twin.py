# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Independent small controls; scientific acquisition is validated separately."""

import json
from collections import Counter
from pathlib import Path
import numpy as np
import pytest
from operations_twin.ingestion import normalize, timestamp, xes_traces, policy
from operations_twin.discovery import connect, analyze, sample_cohort
from dynamics.events import EventCore, EventAgent
from dynamics.experiment_core import stream, interval, cluster_bootstrap, draw_interval


def log(tmp_path):
    rows = []
    for i, month in enumerate([1, 2, 7, 8, 10, 11]):
        for n, act in enumerate(
            [
                "Create Purchase Order Item",
                "Record Goods Receipt",
                "Record Invoice Receipt",
                "Clear Invoice",
            ]
        ):
            rows.append(
                dict(
                    case_id=str(i),
                    document_id=str(i),
                    category="3-way match, invoice after GR",
                    activity=act,
                    timestamp=f"2018-{month:02d}-{n+1:02d}T00:00:00Z",
                    resource="User-1",
                )
            )
    # Exact duplicate retained; one invalid required timestamp explicitly excluded.
    rows.append(dict(rows[3]))
    rows.append(dict(rows[3], timestamp="bad"))
    path = tmp_path / "input.json"
    path.write_text(json.dumps(rows))
    return path


def test_import_discovery_heldout_and_quality(tmp_path):
    p = log(tmp_path)
    folder = tmp_path / "norm"
    m = normalize(p, folder, "json")
    assert m["counts"]["source_events"] == 26
    assert m["counts"]["imported_events"] == 25
    assert normalize(p, folder, "json") == m
    c = connect(tmp_path / "db", folder)
    r, perf = analyze(c, m, {"name": "known control"})
    assert r["counts"]["cases"] == 6 and r["counts"]["events"] == 25
    assert r["counts"]["activities"] == 4 and r["counts"]["purchase_documents"] == 6
    assert r["data_quality"]["exact_duplicate_candidates_retained"] == 1
    assert r["data_quality"]["excluded_events"] == 1
    assert all(x["elapsed_median_day"] == 3 for x in r["category_performance"])
    assert len(sample_cohort(c, "test")) == 2
    sets = [
        {x["document_group"] for x in sample_cohort(c, s)}
        for s in ["calibration", "validation", "test"]
    ]
    assert not (sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2])
    c.close()
    part = folder / m["parts"][0]["file"]
    part.write_bytes(b"tamper")
    with pytest.raises(ValueError, match="changed"):
        normalize(p, folder, "json")


def test_timezone_and_input_security(tmp_path):
    assert timestamp("2018-01-01T01:00:00+01:00") == timestamp("2018-01-01T00:00:00Z")
    with pytest.raises(ValueError, match="timezone"):
        timestamp("2018-01-01T00:00:00")
    with pytest.raises(ValueError):
        policy("http://data.4tu.nl/evil")
    p = tmp_path / "evil.xes"
    p.write_text(
        '<!DOCTYPE log [<!ENTITY x SYSTEM "file:///etc/passwd">]><log><trace><string key="concept:name" value="&x;"/></trace></log>'
    )
    with pytest.raises(Exception):
        list(xes_traces(p))
    alias = tmp_path / "alias.json"
    alias.symlink_to(log(tmp_path))
    with pytest.raises(ValueError):
        normalize(alias, tmp_path / "bad", "json")


@pytest.mark.parametrize("format", ["csv", "jsonl", "parquet"])
def test_format_equivalence(tmp_path, format):
    import csv, pyarrow as pa, pyarrow.parquet as pq

    rows = json.loads(log(tmp_path).read_text())[:24]
    p = tmp_path / ("input." + format)
    if format == "csv":
        with p.open("w") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    elif format == "jsonl":
        p.write_text("\n".join(json.dumps(x) for x in rows))
    else:
        pq.write_table(pa.Table.from_pylist(rows), p)
    m = normalize(p, tmp_path / "norm", format, drop_resources=True)
    c = connect(tmp_path / "db", tmp_path / "norm")
    r, _ = analyze(c, m, {})
    assert r["counts"]["cases"] == 6 and r["counts"]["events"] == 24
    assert r["counts"]["identifiable_resource_tokens"] == 0
    c.close()


def test_clock_seed_distribution_and_uncertainty():
    core = EventCore()
    agent = EventAgent(1)

    def work():
        agent.transition("start", core.now)
        core.emit("Start", 1)
        yield core.timeout(2)
        agent.transition("end", core.now)
        core.emit("End", 1)

    core.env.process(work())
    core.pause()
    assert not core.step()
    core.resume()
    r = core.run()
    assert r["clock_day"] == 2 and agent.state == "end"
    assert np.array_equal(
        stream(1, 2, 3).normal(size=10), stream(1, 2, 3).normal(size=10)
    )
    x = interval([1, 2, 3])
    assert x["mean"] == 2 and x["mean_CI95"][0] < 2 < x["mean_CI95"][1]
    b = cluster_bootstrap(
        [1, 1, 2, 2, 3, 3], ["a", "a", "b", "b", "c", "c"], repeats=99
    )
    assert b["clusters"] == 3
    for d in ["empirical", "exponential", "gamma", "lognormal", "weibull"]:
        assert draw_interval(stream(1, 2), d, values=[0, 1], mean=1) >= 0


def test_empirical_model_and_fifo_twin_reproducible():
    from operations_twin.twin import calibrate, simulate, plan
    from operations_twin.experiments import metrics, tv

    rows = [
        dict(
            category="control",
            activities=["Create Purchase Order Item", "Review", "Clear Invoice"],
            gaps_day=[2.0, 3.0],
            duration_day=5.0,
        )
        for _ in range(101)
    ]
    model = calibrate(rows)
    arr = [dict(id=i, category="control", arrival_day=0.0) for i in range(5)]
    a = simulate(model, arr, kind="category_bootstrap", record=True)
    b = simulate(model, arr, kind="category_bootstrap", record=True)
    assert a["cases"] == b["cases"] and a["replay"] == b["replay"]
    assert a["aggregate"]["duration_day"]["mean"] == 5
    assert metrics(rows, a["cases"])["mean_relative_error"] == 0
    assert tv(Counter({("x",): 1}), Counter({("x",): 2})) == 0
    # All arrive together; a deterministic3day incoming interval split into50%service generates a real FIFO queue.
    s = simulate(
        model,
        arr,
        kind="category_bootstrap",
        resource=True,
        capacity=1,
        service_fraction=0.5,
        record=True,
    )
    assert s["aggregate"]["max_queue"] >= 3
    assert s["aggregate"]["queue_wait_day"]["mean"] > 0
    completed = [x["id"] for x in s["cases"]]
    assert completed == list(range(5))
    assert {
        "Queue Entry",
        "Queue Exit",
        "Resource Request",
        "Resource Release",
        "Case Completion",
    } <= {x["kind"] for x in s["replay"]["events"]}


def test_interval_fits_poisson_and_calendar_arrivals():
    from operations_twin.process_models import interval_candidates, arrival_times

    x = np.r_[np.zeros(20), stream(1, 2).gamma(2, 3, 1000)]
    fits = interval_candidates(x)
    assert fits["zero_mass"] == 20 / 1020 and len(fits["candidates"]) == 4
    assert fits["candidates"][0]["distribution"] == "gamma"
    for kind in ["poisson", "piecewise_poisson"]:
        a = arrival_times(kind, horizon=20, rates=[(10, 3), (20, 8)])
        b = arrival_times(kind, horizon=20, rates=[(10, 3), (20, 8)])
        assert a == b and all(0 <= x < 20 for x in a) and a == sorted(a)
    assert len(arrival_times("empirical", horizon=2, count=10, empirical=[0, 1])) == 10
    with pytest.raises(ValueError):
        arrival_times("piecewise_poisson", horizon=2, rates=[(3, 1)])


def test_api_boundary_and_no_ai(tmp_path):
    from fastapi.testclient import TestClient
    from operations_twin.service import OperationsEngine
    from operations_twin.api import create_app

    e = OperationsEngine(tmp_path / "state")
    client = TestClient(create_app(e), base_url="http://127.0.0.1:4207")
    assert client.get("/").status_code == 200
    assert client.get("/api/status").json()["number"] == 2
    assert (
        client.get("/api/status", headers={"Host": "attacker.example"}).status_code
        == 400
    )
    assert client.post("/api/run", json={}).status_code == 403
    assert (
        client.post(
            "/api/run",
            headers={"x-research-request": "1", "Origin": "https://attacker.example"},
            json={},
        ).status_code
        == 403
    )
    headers = {"x-research-request": "1"}
    assert (
        client.post("/api/what-if", headers=headers, json={"cases": 100000}).status_code
        == 422
    )
    assert (
        client.post(
            "/api/import",
            headers=headers,
            json={"name": "../../etc/passwd", "format": "csv"},
        ).status_code
        == 400
    )
    assert client.get("/static/not-allowed.js").status_code == 404
    j = e.store.create("operations-twin", {})
    j.update(
        status="completed", result={"experiment": "OTE-001", "results_sha256": "abc"}
    )
    e.store.save(j)
    a = client.post("/api/jobs/" + j["id"] + "/ai", headers=headers, json={}).json()
    assert a["status"] == "disabled"
    assert client.get("/api/jobs/" + j["id"] + "/files/secret").status_code == 404
    assert (
        client.get("/api/jobs/" + j["id"] + "/files/nope")
        .headers["Content-Security-Policy"]
        .find("frame-ancestors 'none'")
        >= 0
    )
    assert (
        client.post("/api/run", headers=headers, content="x" * 17000).status_code == 413
    )


def test_private_import_persistence_and_mapping(tmp_path):
    from operations_twin.service import OperationsEngine

    e = OperationsEngine(tmp_path / "state")
    p = e.root / "imports/input.json"
    p.write_text(
        json.dumps(
            [
                dict(
                    id="private",
                    act="Review",
                    time="2018-01-01T00:00:00Z",
                    resource="Person",
                )
            ]
        )
    )
    m = e.import_file(
        "input.json", "json", {"case_id": "id", "activity": "act", "timestamp": "time"}
    )
    assert m["counts"]["imported_events"] == 1
    import pyarrow.parquet as pq

    part = next((e.root / "private-imports").glob("*/*.parquet"))
    row = pq.read_table(part).to_pylist()[0]
    assert row["resource_key"] is None and row["case_key"] != "private"
    e2 = OperationsEngine(e.root)
    assert (
        e2.import_file(
            "input.json",
            "json",
            {"case_id": "id", "activity": "act", "timestamp": "time"},
        )
        == m
    )


def test_resume_committed_partitions(tmp_path):
    p = tmp_path / "big.jsonl"
    p.write_text(
        "\n".join(
            json.dumps(
                dict(case_id=str(i), activity="a", timestamp="2018-01-01T00:00:00Z")
            )
            for i in range(10020)
        )
    )
    folder = tmp_path / "norm"
    calls = [0]

    def cancel():
        calls[0] += 1
        return calls[0] > 10005

    with pytest.raises(InterruptedError):
        normalize(p, folder, "jsonl", cancel=cancel)
    assert (folder / "import-state.json").exists()
    m = normalize(p, folder, "jsonl")
    assert (
        m["counts"]["source_events"] == 10020
        and sum(x["rows"] for x in m["parts"]) == 10020
    )


def test_report_exports_fingerprint_and_no_dataset_execution(tmp_path):
    from operations_twin.reporting import exports
    from dynamics.experiments import fingerprint

    p = log(tmp_path)
    folder = tmp_path / "normalized"
    m = normalize(p, folder, "json")
    c = connect(tmp_path / "db", folder)
    r, _ = analyze(c, m, {})
    files = exports(r, {"executed_at": "control"}, tmp_path / "report")
    c.close()
    value = json.loads((tmp_path / "report/OTE-001_RESULTS.json").read_text())
    assert fingerprint(value)["results_sha256"] == r["results_sha256"]
    assert (
        len([x for x in files if x.startswith("OTE-001")]) == 7
    )  # Six mandatory files plus figure
    text = (tmp_path / "report/OTE-001_REPORT.html").read_text()
    assert "time:timestamp" not in text and "CC BY4.0" in text


def test_cancellation_and_event_budget():
    core = EventCore(event_limit=1)
    core.emit("first")
    with pytest.raises(ValueError, match="budget"):
        core.emit("second")
    core = EventCore()
    core.env.timeout(1)
    with pytest.raises(InterruptedError):
        core.run(cancel=lambda: True)


def test_distribution_distances_known_control():
    from operations_twin.experiments import metrics, tv

    observed = [dict(duration_day=d, activities=["A", "B"]) for d in [1.0, 2.0, 3.0]]
    simulated = [
        dict(duration_day=d, activities=["A", "B"], completion_day=d)
        for d in [2.0, 3.0, 4.0]
    ]
    r = metrics(observed, simulated)
    assert r["mean_signed_error_day"] == 1 and r["wasserstein_day"] == 1
    assert r["mean_relative_error"] == 0.5 and r["variant_total_variation"] == 0
    assert tv(Counter(a=2), Counter(b=2)) == 1

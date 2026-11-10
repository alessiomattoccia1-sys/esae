# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Synthetic mathematical control cases, separate from financial findings."""

from copy import deepcopy
import json
import numpy as np, pandas as pd, pytest
from financial.analysis import (
    StudyConfig,
    analyze,
    correlate,
    block_interval,
    inversion_episodes,
    trailing_robust_z,
    lag_family,
    change_candidates,
    aligned_frames,
)
from financial.parsers import parse, day, number
from financial.connectors import source_policy, FinancialCache
from financial.storage import FinancialStore


def record(parser="treasury_csv"):
    return {
        "source_id": (
            "treasury"
            if parser.startswith("treasury")
            else "chicago" if parser.startswith("nfci") else "newyork"
        ),
        "parser": parser,
        "sha256": "0" * 64,
        "acquired_at": "2026-11-06T00:00:00+00:00",
    }


@pytest.mark.parametrize(
    "value,expected",
    [
        ("12/31/24", "2024-12-31"),
        ("01/02/90", "1990-01-02"),
        ("01/07/2000", "2000-01-07"),
        ("2026-10-30T00:00:00", "2026-10-30"),
    ],
)
def test_official_date_representations(value, expected):
    assert day(value) == expected


@pytest.mark.parametrize("value", [None, "", "N/A", ".", "NaN", float("inf")])
def test_missing_never_becomes_zero(value):
    assert number(value) is None


def test_zero_negative_valid_and_non_numeric_rejected():
    assert number(0) == 0 and number(-0.25) == -0.25
    for v in [True, "malformed", 1001]:
        with pytest.raises(ValueError):
            number(v)


def test_csv_units_dates_nulls_and_dedup(tmp_path):
    p = tmp_path / "rates.csv"
    p.write_text(
        "Date,3 Mo,2 Yr,5 Yr,10 Yr,30 Yr\n01/03/00,5.33,6.38,6.5,6.58,N/A\n01/03/00,5.33,6.38,6.5,6.58,N/A\n"
    )
    rows, c = parse(p, record())
    assert len(rows) == 5 and c["identical_duplicates"] == 5
    assert next(r for r in rows if r["series_id"] == "UST_30Y")["value"] is None
    assert all(
        r["unit"] == "percentage_points" and r["publication_at"] is None for r in rows
    )
    p.write_text(
        "Date,3 Mo,2 Yr,5 Yr,10 Yr,30 Yr\n01/03/00,5,6,7,8,9\n01/03/00,5,6,7,9,9\n"
    )
    with pytest.raises(ValueError, match="Conflicting duplicate"):
        parse(p, record())


def test_xml_missingness_no_entities(tmp_path):
    p = tmp_path / "x.xml"
    p.write_text(
        '<feed xmlns="http://www.w3.org/2005/Atom" xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices" xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata"><entry><updated>2026-11-05T16:00:00Z</updated><content><m:properties><d:NEW_DATE>2026-01-02T00:00:00</d:NEW_DATE><d:BC_3MONTH>3.5</d:BC_3MONTH><d:BC_2YEAR>3.7</d:BC_2YEAR><d:BC_5YEAR>3.8</d:BC_5YEAR><d:BC_10YEAR>4</d:BC_10YEAR><d:BC_30YEAR m:null="true"/></m:properties></content></entry></feed>'
    )
    rows, c = parse(p, record("treasury_xml"))
    assert len(rows) == 5 and rows[-1]["value"] is None
    assert (
        rows[0]["publication_at"] is None
        and rows[0]["source_updated_at"] == "2026-11-05T16:00:00Z"
    )
    p.write_text('<!DOCTYPE feed [<!ENTITY bad SYSTEM "file:///never-read">]><feed/>')
    with pytest.raises(ValueError, match="entities"):
        parse(p, record("treasury_xml"))


def test_nfci_friday_reference_not_publication(tmp_path):
    p = tmp_path / "nfci.csv"
    p.write_text(
        "Friday_of_Week,NFCI,ANFCI,Risk\n01/07/2000,-.1,-.2,0\n01/10/2000,0,0,0\n"
    )
    rows, c = parse(p, record("nfci_csv"))
    assert len(rows) == 3 and c["invalid_rows"] == 1
    assert all(r["publication_at"] is None and r["frequency"] == "weekly" for r in rows)


def test_sofr_revision_flag(tmp_path):
    p = tmp_path / "sofr.json"
    p.write_text(
        json.dumps(
            {
                "refRates": [
                    {
                        "effectiveDate": "2020-03-31",
                        "type": "SOFR",
                        "percentRate": 0,
                        "revisionIndicator": "*",
                    }
                ]
            }
        )
    )
    rows, c = parse(p, record("sofr_json"))
    assert (
        rows[0]["value"] == 0
        and rows[0]["revision_flag"] == "*"
        and rows[0]["publication_at"] is None
    )


@pytest.fixture
def control_frame():
    rows = []
    for i, d in enumerate(pd.bdate_range("2000-01-03", periods=1100)):
        for series, value in [
            ("UST_2Y", 3 + np.sin(i / 50)),
            ("UST_3M", 3.3 + np.sin(i / 90)),
            ("UST_5Y", 3.4 + np.sin(i / 80)),
            ("UST_10Y", 3.6 + np.cos(i / 60)),
            ("UST_30Y", 3.9 + np.cos(i / 70)),
        ]:
            rows.append({"series_id": series, "observation_date": d, "value": value})
    for i, d in enumerate(pd.date_range("2000-01-07", periods=220, freq="W-FRI")):
        for series, value in [("NFCI", np.sin(i / 10)), ("ANFCI", np.cos(i / 12))]:
            rows.append({"series_id": series, "observation_date": d, "value": value})
    return pd.DataFrame(rows)


def test_basispoints_and_holiday_alignment(control_frame):
    config = StudyConfig(end="2004-03-19", bootstrap_replicates=99)
    _, daily, weekly = aligned_frames(control_frame, config)
    assert daily.iloc[0].spread_10y2y_bp == pytest.approx(160)
    assert weekly.index[0] == pd.Timestamp("2000-01-07")
    assert (
        weekly.iloc[0].treasury_observation_date == pd.Timestamp("2000-01-07")
        and weekly.iloc[0].NFCI == 0
    )
    holiday = control_frame[
        ~(
            (control_frame.observation_date == pd.Timestamp("2000-01-07"))
            & control_frame.series_id.str.startswith("UST_")
        )
    ]
    _, _, w = aligned_frames(holiday, config)
    assert w.iloc[0].treasury_observation_date == pd.Timestamp("2000-01-06")


def test_inversion_calendar_sessions_and_censoring():
    s = pd.Series(
        [-1, -2, np.nan, -3, 0, -4],
        index=pd.to_datetime(
            [
                "2000-01-06",
                "2000-01-07",
                "2000-01-10",
                "2000-01-11",
                "2000-01-12",
                "2000-01-13",
            ]
        ),
    )
    e = inversion_episodes(s)
    assert (
        e[0]["sessions"] == 2
        and e[0]["calendar_days_inclusive"] == 2
        and e[0]["end_reason"] == "missing_required_yield"
    )
    assert e[-1]["right_censored"] and e[-1]["sessions"] == 1


def test_pearson_spearman_reference():
    assert correlate(pd.Series(range(30)), pd.Series(np.arange(30) * 3))["pearson"] == 1
    assert correlate(pd.Series(range(30)), pd.Series(-np.arange(30)))["spearman"] == -1
    assert (
        correlate(pd.Series([1] * 30), pd.Series(range(30)))["status"]
        == "not_determinable"
    )


def test_moving_block_reproducibility():
    x = np.sin(np.arange(130) / 11)
    y = 0.5 * x + np.cos(np.arange(130) / 5) * 0.3
    cfg = StudyConfig(bootstrap_replicates=99)
    a = block_interval(x, y, cfg)
    assert (
        a == block_interval(x, y, cfg)
        and a["block_weeks"] == 13
        and a["lower"] < a["upper"]
    )
    assert block_interval(x[:20], y[:20], cfg)["status"] == "not_determinable"


def test_lag_sign_and_holm_family():
    rng = np.random.default_rng(42)
    x = pd.Series(rng.normal(size=180))
    y = x.shift(4)
    r = lag_family(
        pd.DataFrame(
            {
                "spread_10y2y_bp": x,
                "spread_10y3m_bp": x * 0.8,
                "NFCI": y,
                "ANFCI": y * 0.5,
            }
        )
    )
    assert len(r) == 28
    positive = next(
        a
        for a in r
        if a["spread"] == "spread_10y2y_bp"
        and a["index"] == "NFCI"
        and a["lag_weeks"] == 4
    )
    negative = next(
        a
        for a in r
        if a["spread"] == "spread_10y2y_bp"
        and a["index"] == "NFCI"
        and a["lag_weeks"] == -4
    )
    assert positive["pearson"] == 1 and abs(negative["pearson"]) < 0.3
    assert all(a["holm_p"] >= a["hac_p"] for a in r)


def test_anomaly_threshold_past_only_and_zero_mad_unknown():
    x = pd.Series(np.random.default_rng(7).normal(size=150))
    a = trailing_robust_z(x)
    b = trailing_robust_z(pd.concat([x, pd.Series([1000] * 20, index=range(150, 170))]))
    pd.testing.assert_series_equal(a, b.iloc[:150])
    assert trailing_robust_z(pd.Series([0.0] * 100 + [1000.0])).isna().all()


def test_change_candidate_threshold_known_sequence():
    c = change_candidates(
        pd.Series([2.0] * 6, index=pd.date_range("2000-01-07", periods=6, freq="W-FRI"))
    )
    assert (
        len(c) == 1 and c[0]["date"] == "2000-02-11" and c[0]["direction"] == "positive"
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://home.treasury.gov/source",
        "https://evil.example/rates.csv",
        "https://markets.newyorkfed.org/api/rates/secured/sofr/search.json?startDate=2000-01-01&endDate=2026-01-01",
        "https://api.data.chicagofed.org/../private",
        "https://127.0.0.1/data",
    ],
)
def test_financial_url_policy(url):
    with pytest.raises(ValueError):
        source_policy(url)


def test_immutable_cache_invalid_hash(tmp_path):
    with pytest.raises(ValueError, match="digest"):
        FinancialCache(tmp_path / "cache").frozen(
            {
                "url": "https://api.data.chicagofed.org/NFCI/nfci-data-series-csv.csv",
                "sha256": "../private",
            }
        )


def test_incremental_revisions_parquet_and_queries(tmp_path):
    store = FinancialStore(tmp_path / "archive")
    job = store.create("financial", {})
    rows = []
    for date in ["2000-01-03", "2001-01-03"]:
        rows.append(
            {
                "series_id": "UST_2Y",
                "observation_date": date,
                "value": 5.0,
                "unit": "percentage_points",
                "frequency": "daily",
                "source_id": "treasury",
                "source_sha256": "0" * 64,
                "publication_at": None,
                "source_updated_at": None,
                "acquired_at": "2026-01-01T00:00:00Z",
                "vintage_at": "2026-01-01T00:00:00Z",
                "vintage_kind": "acquisition_snapshot",
                "revision_flag": None,
                "parser_version": "test",
            }
        )
    assert (
        store.revisions(rows)["new_observation_versions"] == 2
        and store.revisions(rows)["new_observation_versions"] == 0
    )
    changed = deepcopy(rows[:1])
    changed[0].update(
        value=6.0, source_sha256="1" * 64, acquired_at="2026-02-01T00:00:00Z"
    )
    assert store.revisions(changed)["changed_values_vs_prior_acquisition"] == 1
    result = store.write_snapshot(job["id"], rows)
    assert (
        result["memory_limit_bytes"] == 512_000_000 and result["rows"] == 2
        and result["partitions"] == 2
        and store.explorer(job["id"], start="2001-01-01")["total"] == 1
        and store.series(job["id"])[0]["present"] == 2
    )


def test_control_analysis_replay_and_all_windows(control_frame):
    cfg = StudyConfig(end="2004-03-19", bootstrap_replicates=99)
    counts = {"observations_seen": len(control_frame)}
    a, _ = analyze(control_frame, [], counts, cfg)
    b, _ = analyze(control_frame.sample(frac=1, random_state=3), [], counts, cfg)
    assert a["analysis_sha256"] == b["analysis_sha256"]
    assert (
        len(a["lag_tests"]) == 28
        and len(a["rolling_correlations"]) == 24
        and len(a["subperiod_correlations"]) == 28
        and a["ai_used_for_numeric_results"] is False
    )


def test_missing_inversion_boundary_cannot_be_an_observed_onset():
    s = pd.Series(
        [0, -1, float("nan"), -2, 0, -3], index=pd.bdate_range("2000-01-03", periods=6)
    )
    e = inversion_episodes(s)
    assert not e[0]["left_censored"] and e[0]["right_censored"]
    assert e[1]["left_censored"] and not e[1]["right_censored"]
    assert not e[2]["left_censored"] and e[2]["right_censored"]


def test_last_session_missing_is_not_silently_taken_from_earlier_day(control_frame):
    f = control_frame.copy()
    f.loc[
        (f.observation_date == pd.Timestamp("2000-01-14")) & (f.series_id == "UST_3M"),
        "value",
    ] = float("nan")
    _, _, w = aligned_frames(f, StudyConfig(end="2004-03-19"))
    assert pd.isna(w.loc["2000-01-14", "spread_10y3m_bp"]) and w.loc[
        "2000-01-14", "treasury_observation_date"
    ] == pd.Timestamp("2000-01-14")


def test_new_tenor_schema_requires_explicit_normalization(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("Date,3 Mo,2 Yr,5 Yr,10 Yr,30 Yr,40 Yr\n01/03/00,5,6,7,8,9,10\n")
    with pytest.raises(ValueError, match="Unknown Treasury maturities"):
        parse(p, record())


@pytest.fixture
def fixture_engine(tmp_path, control_frame, monkeypatch):
    from financial.service import FinancialEngine
    from financial.connectors import import_official_file, TREASURY_ARCHIVE, NFCI_CSV
    import financial.service as service

    engine = FinancialEngine(tmp_path / "archive")
    w = control_frame.pivot(
        index="observation_date", columns="series_id", values="value"
    )
    treas = (
        w[[c for c in w if c.startswith("UST_")]]
        .dropna(how="all")
        .rename(
            columns={
                "UST_2Y": "2 Yr",
                "UST_3M": "3 Mo",
                "UST_5Y": "5 Yr",
                "UST_10Y": "10 Yr",
                "UST_30Y": "30 Yr",
            }
        )
    )
    treas.index = treas.index.strftime("%m/%d/%Y")
    treas.index.name = "Date"
    tp = tmp_path / "treasury.csv"
    treas.to_csv(tp)
    nfci = w[["NFCI", "ANFCI"]].dropna(how="all")
    nfci.index = nfci.index.strftime("%m/%d/%Y")
    nfci.index.name = "Friday_of_Week"
    np = tmp_path / "nfci.csv"
    nfci.to_csv(np)
    records = [
        import_official_file(tp, TREASURY_ARCHIVE, "treasury_csv", engine.cache),
        import_official_file(np, NFCI_CSV, "nfci_csv", engine.cache),
    ]

    class Connector:
        def __init__(self, cache):
            pass

        def acquire(self, *a, progress=None, **kw):
            if progress:
                progress(records, len(records), len(records))
            return records

    monkeypatch.setattr(service, "InstitutionalConnector", Connector)
    job = engine.run(StudyConfig(end="2004-03-19", bootstrap_replicates=99))
    assert job["status"] == "completed", job
    return engine, job


def test_fixture_complete_storage_replay_resume_and_no_duplicate_revision(
    fixture_engine,
):
    engine, j = fixture_engine
    assert engine.verify(j["id"])["passed"]
    assert engine.report(j["id"])["coverage"]["complete_primary_weeks"] == 220
    j["status"] = "interrupted"
    engine.store.save(j)
    r = engine.run(resume=j["id"])
    assert r["status"] == "completed"
    assert engine.verify(j["id"])["passed"]
    manifest = json.loads(
        (engine.store.directory(j["id"]) / "FSIE-001_MANIFEST.json").read_text()
    )
    assert manifest["revisions"]["new_observation_versions"] == 0


def test_financial_api_filters_curve_exports_and_boundary(fixture_engine):
    from fastapi.testclient import TestClient
    from financial.api import create_app

    engine, j = fixture_engine
    with TestClient(create_app(engine), base_url="http://127.0.0.1:4204") as c:
        base = "/api/jobs/" + j["id"]
        assert c.get("/").status_code == 200
        assert c.get("/api/status").json()["trading"] is False
        r = c.get(
            base
            + "/observations?series=UST_10Y&source=treasury&start=2000-01-01&end=2000-01-31"
        ).json()
        assert r["total"] == 21 and all(x["publication_at"] is None for x in r["items"])
        assert len(c.get(base + "/curve?date=2000-01-03").json()["points"]) == 5
        assert (
            c.get(base + "/curve?date=2000-01-08").json()["has_observations"] is False
        )
        assert c.get(base + "/observations?unit=invalid").status_code == 422
        assert c.get(base + "/chart?series=unknown").status_code == 400
        for kind in ["json", "html", "csv", "manifest", "method", "reproduction"]:
            assert c.get(base + "/export/" + kind).status_code == 200
        assert c.post(base + "/verify", headers={"x-research-request": "1"}).json()[
            "passed"
        ]
        assert (
            c.post(
                base + "/findings/FSIE-001-F1/explain",
                headers={"x-research-request": "1"},
            ).status_code
            == 400
        )
        assert c.get(base + "/insights").json() == []
        assert (
            c.post(
                "/api/jobs",
                json={},
                headers={"origin": "https://evil.example", "x-research-request": "1"},
            ).status_code
            == 403
        )
        assert c.post("/api/jobs", json={}).status_code == 403
        assert (
            c.post(
                "/api/jobs",
                json={"private_file": "forbidden"},
                headers={"x-research-request": "1"},
            ).status_code
            == 422
        )
        assert c.get("/api/status", headers={"host": "evil.example"}).status_code == 400
        assert c.get("/static/secret.py").status_code == 404
        assert (
            c.get(base + "/report")
            .headers["content-security-policy"]
            .find("connect-src 'self'")
            >= 0
        )


def test_raw_replay_detects_modified_bytes(fixture_engine):
    engine, j = fixture_engine
    r = engine.report(j["id"])
    blob = engine.cache.frozen(r["sources"][0])
    blob.write_bytes(blob.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="modified"):
        engine.verify(j["id"])


def test_cache_keeps_old_acquisition_after_refresh(tmp_path, monkeypatch):
    import hashlib

    cache = FinancialCache(tmp_path / "cache")
    data = iter([b"first", b"changed"])

    def fetch(url, **kw):
        b = next(data)
        p = cache.root / "transport" / "test.data"
        part = p.with_suffix(".part")
        part.write_bytes(b)
        part.replace(p)
        return p, {
            "sha256": hashlib.sha256(b).hexdigest(),
            "url": url,
            "acquired_at": str(len(b)),
        }

    monkeypatch.setattr(cache.transport, "fetch", fetch)
    p, a = cache.fetch("https://api.data.chicagofed.org/NFCI/nfci-data-series-csv.csv")
    _, b = cache.fetch(a["url"], refresh=True)
    assert (
        cache.frozen(a).read_bytes() == b"first"
        and cache.frozen(b).read_bytes() == b"changed"
    )


def test_ecb_unit_and_identity():
    from financial.ecb import parse as ecb_parse, policy

    raw = b"KEY,TIME_PERIOD,OBS_VALUE,UNIT,UNIT_MULT,CURRENCY,CURRENCY_DENOM,FREQ\nEXR.D.USD.EUR.SP00.A,2026-10-01,1.1298,USD,0,USD,EUR,D\n"
    assert ecb_parse(raw)[0]["unit"] == "USD_per_EUR"
    with pytest.raises(ValueError):
        ecb_parse(raw.replace(b",USD,0,", b",EUR,0,"))
    with pytest.raises(ValueError):
        policy("https://data-api.ecb.europa.eu/service/data/EXR?format=csvdata")


def test_public_export_rejects_unverified_manual_origin(fixture_engine, tmp_path):
    from financial.export import export

    engine, j = fixture_engine
    with pytest.raises(ValueError, match="official HTTP"):
        export(engine, j["id"], tmp_path / "public")


def test_treasury_display_alias_must_agree(tmp_path):
    p = tmp_path / "feed.xml"
    raw = '<feed xmlns="http://www.w3.org/2005/Atom" xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices"><entry><d:NEW_DATE>2026-01-02</d:NEW_DATE><d:BC_3MONTH>3</d:BC_3MONTH><d:BC_2YEAR>3</d:BC_2YEAR><d:BC_5YEAR>4</d:BC_5YEAR><d:BC_10YEAR>4</d:BC_10YEAR><d:BC_30YEAR>5</d:BC_30YEAR><d:BC_30YEARDISPLAY>5</d:BC_30YEARDISPLAY></entry></feed>'
    p.write_text(raw)
    assert len(parse(p, record("treasury_xml"))[0]) == 5
    p.write_text(raw.replace("DISPLAY>5<", "DISPLAY>6<"))
    with pytest.raises(ValueError, match="display alias"):
        parse(p, record("treasury_xml"))

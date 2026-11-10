# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Analytical/synthetic controls; separate from real experimental qualification."""

from pathlib import Path
from copy import deepcopy
import json, zipfile, stat
import numpy as np, pytest
from scipy import signal, fft
from fusion.physics import convert, uncertainty_sum_independent
from fusion.signals import quality, spectra, events, analyze_signal, pair_correlation
from fusion.inertial import inspect_archive, image_metrics, analyze_image, load_hdf
from fusion.acquisition import policy, FusionCache, STFC_ITEM, STFC_ZIP


def test_dimensional_conversions_and_incompatible_units():
    assert convert([1, 2], "kA", "A").tolist() == [1000, 2000]
    assert convert([1000], "ms", "s")[0] == 1
    with pytest.raises(ValueError):
        convert([1], "T", "A")
    with pytest.raises(ValueError):
        convert([1], "", "A")


def test_independent_uncertainty_reference():
    r = uncertainty_sum_independent([10, 20], [3, 4])
    assert r["value"] == 30 and r["standard_uncertainty"] == 5
    with pytest.raises(ValueError):
        uncertainty_sum_independent([1], [-1])


def test_quality_missing_duplicate_irregular_constant():
    t = np.arange(1000) * 0.001
    x = np.sin(t)
    x[100:110] = np.nan
    q = quality(t, x)
    assert q["missing_samples"] == 10 and q["longest_valid_segment"] == [110, 1000]
    t[200] = t[199]
    q = quality(t, x)
    assert q["duplicate_timestamps"] == 1 and not q["regular_sampling"]
    assert quality(np.arange(100), np.ones(100))["constant_or_degenerate"]


def test_fft_welch_peak_and_power_reference():
    fs = 8192
    t = np.arange(32768) / fs
    x = 2 * np.sin(2 * np.pi * 512 * t)
    r = spectra(t, x, nperseg=1024)
    assert r["dominant_non_dc_hz"] == pytest.approx(512)
    assert r["integrated_psd"] == pytest.approx(2, rel=0.001)
    assert r["input_variance"] == pytest.approx(2, rel=0.001)
    index = np.argmin(np.abs(np.asarray(r["fft"]["frequency_hz"]) - 512))
    assert r["fft"]["amplitude"][index] == pytest.approx(2, rel=0.001)
    assert r["nyquist_hz"] == pytest.approx(4096)


def test_spectral_invalids_and_nan_never_zero():
    t = np.arange(1000) * 0.001
    x = np.sin(t)
    x[10] = np.nan
    assert spectra(t, x)["status"] == "inconclusive"
    assert spectra(t, np.ones(1000))["status"] == "inconclusive"


def test_derivative_and_savgol_analytical_polynomial():
    t = np.linspace(0, 1, 1000)
    x = 3 * t * t + 2 * t + 1
    d = np.gradient(x, t, edge_order=2)
    assert np.max(np.abs(d - (6 * t + 2))) < 1e-9
    assert np.max(np.abs(signal.savgol_filter(x, 21, 3) - x)) < 1e-10


def test_stft_known_stationary_frequency():
    fs = 4096
    t = np.arange(16384) / fs
    r = spectra(t, np.cos(2 * np.pi * 256 * t), 1024)
    s = r["stft"]
    f = np.asarray(s["frequency_hz"])
    z = np.asarray(s["magnitude"])
    assert np.median(s["dominant_frequency_hz_full_grid"]) == pytest.approx(256)
    assert len(s["time_s"]) == z.shape[1]


def test_candidate_event_not_named_physics():
    t = np.arange(5000) * 0.0001
    x = np.random.default_rng(1).normal(0, 0.001, len(t))
    x[2500:] += 1
    e, p = events(t, x)
    assert any(abs(v["timestamp_s"] - 0.25) < 0.001 for v in e)
    assert all(v["verification"] == "candidate_unclassified" for v in e)
    assert p["causal_or_predictive"] is False


def test_zero_mad_events_are_inconclusive():
    t = np.arange(1000) * 0.001
    e, p = events(t, np.ones(1000))
    assert e == [] and p["status"] == "inconclusive"


def test_signal_preserves_input_and_all_sensitivity_cases():
    t = np.arange(4096) / 8192
    x = np.sin(2 * np.pi * 512 * t)
    copy = x.copy()
    m = {
        "shot_id": 30421,
        "diagnostic": "magnetics/b_field_pol_probe_omv_voltage",
        "unit": "V",
        "time_unit": "s",
    }
    r = analyze_signal(t, x, m)
    assert np.array_equal(x, copy)
    assert (
        len(r["filter_sensitivity"]) == 3
        and len(r["event_threshold_sensitivity"]) == 3
        and len(r["spectral"]["window_sensitivity"]) == 3
    )
    assert r["mean_block_interval"]["systematic_calibration_uncertainty"] is None


def test_same_shot_correlation_alignment_and_sign():
    t = np.arange(1500) * 0.001
    tf = np.arange(150000) * 0.00001
    x = np.sin(2 * np.pi * 3 * t)
    y = np.sin(2 * np.pi * 3 * tf)
    r = pair_correlation(t, x, tf, y)
    assert r["n"] >= 1499 and r["pearson"] > 0.999
    assert len(r["lags"]) == 7 and "retrospective" in r["positive_lag"]


def test_known_detector_centroid_and_unchanged_array():
    x = np.zeros((80, 100), np.uint16)
    x[20:40, 30:50] = 100
    before = x.copy()
    m = image_metrics(x)
    assert (
        m["centroid_detector_px"]["x_px"] == 39.5
        and m["centroid_detector_px"]["y_px"] == 29.5
    )
    assert m["physical_scale_conversion"] is False
    assert np.array_equal(x, before)


def test_image_nan_uniform_and_method_sensitivity():
    x = np.zeros((80, 100))
    x[20:40, 30:50] = 100
    x[0, 0] = np.nan
    m = image_metrics(x)
    assert m["invalid_pixels"] == 1
    assert image_metrics(np.ones((50, 50)))["centroid_detector_px"] is None
    r = analyze_image(x, {"shot_id": "fixture"})
    assert len(r["sensitivity"]) == 6 and r["evidence_type"] == "DERIVED"


@pytest.mark.parametrize(
    "name",
    [
        "../escape",
        "/absolute",
        "DataRepo/../../escape",
        "C:/escape",
        "DataRepo\\escape",
    ],
)
def test_zip_traversal_rejected(tmp_path, name):
    p = tmp_path / "bad.zip"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr(name, b"data")
    with pytest.raises(ValueError, match="path"):
        inspect_archive(p)


def test_zip_symlink_and_expansion_rejected(tmp_path):
    p = tmp_path / "bad.zip"
    info = zipfile.ZipInfo("DataRepo/link")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(p, "w") as z:
        z.writestr(info, b"/unrelated")
    with pytest.raises(ValueError):
        inspect_archive(p)
    with zipfile.ZipFile(p, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("DataRepo/zeros", b"0" * 2_000_000)
    with pytest.raises(ValueError, match="expansion"):
        inspect_archive(p)


@pytest.mark.parametrize(
    "url",
    [
        "http://s3.echo.stfc.ac.uk/mast/level2/shots/30421.zarr/zarr.json",
        "https://evil.example/data",
        "https://s3.echo.stfc.ac.uk/mast/level2/defuse/MAST.h5",
        "https://s3.echo.stfc.ac.uk/mast/level2/shots/30421.zarr/../../secret",
        "https://edata.stfc.ac.uk/another-download",
    ],
)
def test_source_policy_does_not_expand_access(url):
    with pytest.raises(ValueError):
        policy(url)


def test_offline_missing_and_hash_tamper_detected(tmp_path):
    cache = FusionCache(tmp_path / "cache")
    cache.expected = {}
    with pytest.raises(ValueError, match="absent"):
        cache.fetch(STFC_ITEM, True)
    with pytest.raises(ValueError, match="digest"):
        cache.frozen({"url": STFC_ITEM, "sha256": "../escape"})


def make_hdf(path):
    from pyhdf.SD import SD, SDC

    f = SD(str(path), SDC.WRITE | SDC.CREATE)
    d = f.create("gel_raw", SDC.UINT16, (80, 100))
    x = np.zeros((80, 100), np.uint16)
    x[20:40, 30:50] = 100
    d[:] = x
    d.shotNum = 109090
    d.endaccess()
    f.end()
    return x


def test_native_hdf_reader_preserves_chunks_and_pixels(tmp_path):
    p = tmp_path / "owned.hdf"
    expected = make_hdf(p)
    x, m = load_hdf(p, tmp_path / "output")
    assert np.array_equal(x, expected)
    assert m["selected"] == "gel_raw" and m["processed_PSL_dataset_used"] is False
    assert all(
        (tmp_path / "output" / name).stat().st_size < 8_000_000
        for name in m["array_parts"]
    )


@pytest.fixture
def fixture_engine(tmp_path, monkeypatch):
    import fusion.experiments as ex
    from fusion.service import FusionEngine

    src = tmp_path / "owned.hdf"
    make_hdf(src)
    archive = tmp_path / "fixture.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.write(
            src, "DataRepo/SLOS-TRXI/Raw Data/slos_trxi_s109090_trxi_-1-[phosphor].hdf"
        )
    item = tmp_path / "item.json"
    item.write_text(
        json.dumps(
            {
                "uuid": "fixture",
                "metadata": {
                    "dc.rights.uri": [
                        {"value": "https://creativecommons.org/licenses/by/4.0/"}
                    ]
                },
            }
        )
    )
    original = FusionCache.fetch

    def fake_fetch(self, url, offline=False):
        if url not in [STFC_ITEM, STFC_ZIP]:
            return original(self, url, offline)
        import hashlib

        p = item if url == STFC_ITEM else archive
        r = {
            "url": url,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "source": "SYNTHETIC_FIXTURE_ONLY",
            "bytes": p.stat().st_size,
            "http_status": None,
            "acquired_at": "fixture",
        }
        self.records[url] = r
        return p, r

    monkeypatch.setattr(FusionCache, "fetch", fake_fetch)
    e = FusionEngine(tmp_path / "archive")
    j = e.run("FPE-002", {})
    assert j["status"] == "completed", j
    return e, j


def test_complete_fixture_pipeline_registry_exports(fixture_engine):
    e, j = fixture_engine
    r = e.report(j["id"])
    assert r["counts"]["raw_images_analyzed"] == 1 and len(r["findings"]) == 3
    with e.store.connect() as db:
        assert db.execute("SELECT count(*) FROM measurements").fetchone()[0] == 1
    for name in [
        "REPORT.html",
        "RESULTS.json",
        "FINDINGS.csv",
        "MANIFEST.json",
        "METHODOLOGY.md",
        "REPRODUCIBILITY.md",
    ]:
        assert (e.store.directory(j["id"]) / ("FPE-002_" + name)).is_file()


def test_api_boundary_and_real_fixture_figures(fixture_engine):
    from fastapi.testclient import TestClient
    from fusion.api import create_app

    e, j = fixture_engine
    with TestClient(create_app(e), base_url="http://127.0.0.1:4205") as c:
        b = "/api/jobs/" + j["id"]
        assert c.get("/").status_code == 200
        assert c.get("/api/status").json()["apparatus_control"] is False
        assert len(c.get(b + "/images?shot=109090").json()) == 1
        assert c.get(b + "/images?shot=invalid").status_code == 422
        for kind in ["json", "html", "csv", "manifest", "method", "reproduction"]:
            assert c.get(b + "/export/" + kind).status_code == 200
        html = c.get(b + "/export/html")
        assert "/report.css" in html.text and "<style>" not in html.text
        assert c.get(b + "/report.css").status_code == 200
        assert c.get(b + "/figure/icf-109090-raw.png").status_code == 200
        assert c.get(b + "/figure/unrelated.png").status_code == 404
        assert (
            c.post(
                b + "/findings/ICF-01/explain", headers={"x-research-request": "1"}
            ).status_code
            == 400
        )
        assert c.post("/api/jobs", json={}).status_code == 403
        assert (
            c.get("/api/status", headers={"origin": "https://evil.example"}).status_code
            == 403
        )
        assert c.get("/api/status", headers={"host": "evil.example"}).status_code == 400
        assert (
            c.post(
                "/api/jobs",
                json={"target_settings": {}},
                headers={"x-research-request": "1"},
            ).status_code
            == 422
        )
        assert (
            c.post(
                "/api/jobs",
                json={"start_seconds": 0.5, "end_seconds": 0.1},
                headers={"x-research-request": "1"},
            ).status_code
            == 400
        )


@pytest.mark.parametrize("level", [1, 2])
def test_selected_zarr2_and_zarr3_chunks_with_known_values(tmp_path, level):
    import xarray as xr, zarr
    from fusion.mast import MastConnector
    from fusion.acquisition import LICENSE_MAST, MAST_ROOT

    n = 2048
    t = np.arange(n) * 0.0001
    values = np.sin(2 * np.pi * 100 * t)
    group = "amc" if level == 1 else "magnetics"
    variable = "plasma_current" if level == 1 else "ip"
    root = tmp_path / "owned.zarr"
    ds = xr.Dataset(
        {variable: ("time", values, {"units": "kA" if level == 1 else "A"})},
        coords={"time": ("time", t, {"units": "s"})},
        attrs={"license_url": LICENSE_MAST},
    )
    ds.to_zarr(
        str(root),
        group=group,
        mode="w",
        zarr_format=2 if level == 1 else 3,
        consolidated=False,
        encoding={variable: {"chunks": (512,)}, "time": {"chunks": (512,)}},
    )
    zarr.consolidate_metadata(str(root))
    base = MAST_ROOT + f"level{level}/shots/30421.zarr/"

    class OwnedCache:
        def __init__(self):
            from research_core.http import PublicCache

            self.transport = PublicCache

        def fetch(self, url, offline=False):
            import hashlib

            assert url.startswith(base)
            p = root / url.removeprefix(base)
            return p, {
                "url": url,
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                "source": "SYNTHETIC_FIXTURE_ONLY",
            }

    got_t, got_x, meta = MastConnector(OwnedCache()).signal(
        30421, group + "/" + variable, tmp_path / "derived", (0.05, 0.15), level, True
    )
    keep = (t >= 0.05) & (t <= 0.15)
    assert np.array_equal(got_t, t[keep]) and np.array_equal(got_x, values[keep])
    assert meta["selection"]["partial_chunks_only"]
    assert len(got_t) == 1001


def test_pinned_sources_journal_offline_and_tamper(tmp_path):
    import hashlib

    root = tmp_path / "cache"
    c = FusionCache(root)
    b = b"owned immutable original"
    digest = hashlib.sha256(b).hexdigest()
    (c.blobs / (digest + ".data")).write_bytes(b)
    r = {"url": STFC_ITEM, "sha256": digest}
    c.expected = {STFC_ITEM: r}
    seen = []
    c.on_record = lambda records: seen.append(records)
    path, record = c.fetch(STFC_ITEM, True)
    assert path.read_bytes() == b and seen == [[r]]
    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="modified"):
        c.fetch(STFC_ITEM, True)


def test_missing_gap_not_compressed_for_lag():
    t = np.arange(1500) * 0.001
    tf = np.arange(150000) * 0.00001
    x = np.sin(2 * np.pi * 3 * t)
    y = np.sin(2 * np.pi * 3 * tf)
    x[500:550] = np.nan
    r = pair_correlation(t, x, tf, y)
    lag = next(v for v in r["lags"] if v["lag_samples"] == 10)
    assert lag["n"] <= 1440
    assert pair_correlation(t[::-1], x, tf, y)["status"] == "inconclusive"


def test_resume_keeps_configuration_and_cancel_releases_lock(tmp_path, monkeypatch):
    import fusion.service as s

    e = s.FusionEngine(tmp_path / "jobs")
    seen = []

    def cancel(cache, folder, cfg, progress, cancel):
        seen.append(dict(cfg))
        raise InterruptedError("Owned cancellation test")

    monkeypatch.setattr(s, "magnetic", cancel)
    j = e.run("FPE-001", {"window_seconds": [0.1, 0.2]})
    assert j["status"] == "cancelled" and not e.lock.locked()
    resumed = e.run(resume=j["id"])
    assert resumed["id"] == j["id"] and seen[0] == seen[1]
    assert not e.lock.locked()


def test_safe_fixture_export_numeric_csv_and_processed_display(fixture_engine):
    import csv, io

    e, j = fixture_engine
    folder = e.store.directory(j["id"])
    rows = list(
        csv.DictReader(io.StringIO((folder / "FPE-002_FINDINGS.csv").read_text()))
    )
    assert len(rows) == 3 and all(json.loads(r["numerical_result_json"]) for r in rows)
    assert (folder / "figures/icf-109090-processed.png").is_file()


def test_public_export_refuses_unqualified_results(tmp_path):
    from fusion.export import export

    q = tmp_path / "qualification.json"
    q.write_text(json.dumps({"passed": False}))
    with pytest.raises(ValueError, match="qualification"):
        export(tmp_path / "local", q, tmp_path / "public")

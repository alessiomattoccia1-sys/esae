# SPDX-License-Identifier: Apache-2.0
"""Analytical controls and synthetic fixtures, separate from real-flight studies."""

import json, io, zipfile
import numpy as np, pandas as pd, pytest
from dynamics.mathematical import (
    GaussianMotion,
    ExtendedKalman,
    ParticleFilter,
    GaussianHMM,
    transition,
    covariance,
    integrate,
    monte_carlo,
    registry,
)
from dynamics.simulation import Simulation
from dynamics.validation import mix, summarize, bootstrap, fit_ensemble
from dynamics.flights import enu, parse_idf
from dynamics.acquisition import RemoteZip, DataCache, IDF_ZIP, policy


@pytest.mark.parametrize("kind", ["CV", "CA", "OU"])
def test_exact_gaussian_transition_semigroup(kind):
    a, q = transition(kind, 2, 0.2, 0.7)
    b, r = transition(kind, 2, 0.3, 0.7)
    f, s = transition(kind, 2, 0.5, 0.7)
    np.testing.assert_allclose(b @ a, f, atol=1e-12)
    np.testing.assert_allclose(b @ q @ b.T + r, s, atol=1e-12)


def test_random_walk_and_correlated_walk_distinct():
    f, q = transition("RW", 2, 0.5, 4)
    np.testing.assert_array_equal(f, np.eye(2))
    np.testing.assert_array_equal(q, np.eye(2) * 2)
    f, _ = transition("CRW", 2, 1, rho=0.8)
    assert f[2, 2] == 0.8 and f[0, 2] == 1


def test_ou_exact_mean_variance():
    f, q = transition("OU", 1, 2, 3, theta=0.5)
    assert f[0, 0] == pytest.approx(np.exp(-1))
    assert q[0, 0] == pytest.approx(3 * (1 - np.exp(-2)))


def test_covariance_inputs_fail_closed():
    for p in [[[1, 2], [0, 1]], [[1, 0], [0, -1]], [[np.nan]]]:
        with pytest.raises(ValueError):
            covariance(p)
    with pytest.raises(ValueError):
        transition("CV", 2, 0)


def test_linear_kalman_known_scalar_joseph_update():
    k = GaussianMotion("RW", 1, r=1)
    k.initialize([2], [[1]])
    k.update([4])
    assert k.x[0] == 3 and k.p[0, 0] == 0.5


def test_partial_observation_preserves_unobserved_uncertainty():
    k = GaussianMotion("RW", 2, r=1)
    k.update([2, np.nan])
    assert k.x[0] == 1 and k.p[0, 0] == 0.5 and k.p[1, 1] == 1
    assert k.update([np.nan, np.nan])["status"] == "INSUFFICIENT EVIDENCE"


def test_ekf_reduces_to_linear_filter_and_nonlinear_jacobian():
    e = ExtendedKalman(
        [2],
        [[1]],
        lambda x, dt: x,
        lambda x, dt: np.eye(1),
        lambda x: x * x,
        lambda x: np.diag(2 * x),
        [[0]],
        [[1]],
    )
    e.update([4.2])
    assert e.x[0] == pytest.approx(2 + 4 / 17 * 0.2)
    assert e.p[0, 0] == pytest.approx(1 / 17)
    e = ExtendedKalman(
        [2],
        [[1]],
        lambda x, dt: x,
        lambda x, dt: np.eye(1),
        lambda x: x,
        lambda x: np.eye(1),
        [[0]],
        [[1]],
    )
    e.update([4])
    assert e.x[0] == 3 and e.p[0, 0] == 0.5


def test_particle_filter_normalization_ess_reset_and_degeneracy():
    particles = np.linspace(-2, 2, 100)[:, None]
    p = ParticleFilter(particles, lambda x, dt: x, lambda x: x, [[0.01]], [[0.1]], 4)
    p.predict(0.1)
    r = p.update([1])
    assert (
        p.weights.sum() == pytest.approx(1)
        and 1 <= p.ess() <= 100.00001
        and r["status"] == "estimated"
    )
    assert abs(p.get_state()[0] - 1) < 0.3
    p.reset()
    np.testing.assert_array_equal(p.particles, particles)
    with np.errstate(over="ignore", invalid="ignore"):
        assert "INSUFFICIENT" in p.update([1e300])["status"]


def test_gaussian_hmm_probabilities_and_descriptive_states():
    rng = np.random.default_rng(12)
    x = np.r_[rng.normal(-3, 0.2, (80, 2)), rng.normal(3, 0.2, (80, 2))]
    h = GaussianHMM(2, 4).fit([x], 6)
    p = h.posterior(x)
    np.testing.assert_allclose(p.sum(axis=1), 1, atol=1e-12)
    np.testing.assert_allclose(h.a.sum(axis=1), 1)
    assert p[:80].mean(axis=0).max() > 0.95 and p[80:].mean(axis=0).max() > 0.95
    assert "no intention" in h.serialize()["state_semantics"]


def test_monte_carlo_seed_and_known_diffusion_variance():
    a = monte_carlo("RW", 1, 10, 0.1, 300, 3, 2)
    b = monte_carlo("RW", 1, 10, 0.1, 300, 3, 2)
    assert a == b
    # Independent closed-form sum of Gaussian increments, including initial N(0,1).
    reference = []
    for child in np.random.SeedSequence(3).spawn(300):
        rng = np.random.default_rng(int(child.generate_state(1)[0]))
        reference.append(rng.normal() + np.sqrt(0.2) * rng.normal(size=10).sum())
    np.testing.assert_allclose(
        np.asarray(a["terminal_states"])[:, 0], reference, atol=1e-12
    )
    from scipy.stats import chi2

    variance = np.var(reference, ddof=1)
    assert chi2.ppf(0.0005, 299) <= 299 * variance / 3 <= chi2.ppf(0.9995, 299)


def test_numerical_integrator_analytic_decay():
    t = np.linspace(0, 2, 101)
    x = integrate(lambda t, x: -x, [1], t)
    np.testing.assert_allclose(x[:, 0], np.exp(-t), rtol=1e-7)


def test_simulation_pause_reset_checkpoint_replay():
    s = Simulation(5, 20, scenario="D", seed=7)
    s.step()
    s.pause()
    assert not s.step() and s.tick == 1
    s.resume()
    s.step()
    checkpoint = json.loads(json.dumps(s.serialize(), allow_nan=False))
    restored = Simulation.restore(checkpoint)
    assert s.run() == restored.run()
    a = s.run()
    s.reset()
    assert s.run() == a


def test_missing_measurements_never_change_true_simulated_dynamics():
    a = Simulation(5, 20, scenario="B", seed=4).run()
    b = Simulation(5, 20, scenario="D", seed=4).run()
    np.testing.assert_array_equal(a["true_state"], b["true_state"])
    assert any(not v for row in b["visible"] for v in row)


@pytest.mark.parametrize("n", [1, 5, 10, 20, 50])
def test_all_agent_cohorts_finite_and_reproducible(n):
    a = Simulation(n, 10, seed=8).run()
    assert a["metrics"]["finite_states"] and a["metrics"]["agents"] == n
    assert a == Simulation(n, 10, seed=8).run()


def test_abstract_three_dimensions_and_resource_limits():
    a = Simulation(10, 20, dimensions=3).run()
    assert len(a["true_state"][0][0]) == 6
    with pytest.raises(ValueError):
        Simulation(1000, 10000)


def test_mixture_covariance_includes_between_model_dispersion():
    m, c = mix(
        [np.array([0.0]), np.array([10.0])],
        [np.array([[1.0]]), np.array([[1.0]])],
        [0.5, 0.5],
    )
    assert m[0] == 5 and c[0, 0] == 26


def test_metric_formulas_ade_fde_rmse_mae_coverage():
    m = np.array([[[3.0, 4], [0, 0], [6, 8]]])
    p = np.tile(np.eye(2), (1, 3, 1, 1))
    r = summarize(m, p, np.zeros_like(m), [{"flight_id": "fixture"}])
    assert (
        r["ADE_m"] == 5
        and r["FDE_m"] == 10
        and r["RMSE_m"] == pytest.approx(np.sqrt(125 / 3))
        and r["MAE_coordinate_m"] == 3.5
        and r["coverage95"] == pytest.approx(1 / 3)
    )


def test_bootstrap_units_and_insufficient_evidence():
    assert bootstrap([1, 1, 1])["lower"] == 1
    assert bootstrap([1, 2])["status"] == "INSUFFICIENT EVIDENCE"
    assert (
        "seed"
        in bootstrap([1, 2, 3], unit="independent simulation seed")["resampling_unit"]
    )


def test_ensemble_uses_validation_optimum():
    rows = [{"flight_id": "a"}, {"flight_id": "b"}, {"flight_id": "c"}]
    truth = np.zeros((3, 3, 2))
    w, details = fit_ensemble([truth.copy(), truth + 1], truth, rows)
    assert w[0] > 0.999 and w.sum() == pytest.approx(1) and details["converged"]


def test_wgs84_geographic_to_local_meters():
    xy = enu([0, 0], [0, 0.001])
    np.testing.assert_allclose(xy[0], [0, 0], atol=1e-9)
    assert xy[1, 0] == pytest.approx(111.31949, rel=1e-6) and abs(xy[1, 1]) < 1e-6


def test_actual_idf_schema_fixture_quality_and_time_units():
    f = pd.DataFrame(
        {
            "time (us)": np.arange(200) * 200000,
            "GPS_coord[0]": np.ones(200) * 39,
            "GPS_coord[1]": -0.6 + np.arange(200) * 0.000001,
            "GPS_numSat": 8,
        }
    )
    f.loc[10, "GPS_coord[0]"] = np.nan
    f.loc[20, "time (us)"] = f.loc[19, "time (us)"]
    r = parse_idf(f.to_csv(index=False).encode(), "FIXTURE")
    assert r["quality"]["valid_rows"] == 198 and r["time_s"][-1] == pytest.approx(39.8)
    assert r["metadata"]["source_altitude_unit"].startswith("Not assumed")


def test_remote_zip_reads_only_selected_verified_member(tmp_path):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("fixture/positions.csv", "t,x,y\n0,1,2\n")
    raw = b.getvalue()

    class Cache:
        def range(self, url, start, end, total, offline):
            return raw[start : end + 1], {"etag": "fixed"}

    z = RemoteZip(Cache(), IDF_ZIP, len(raw), True)
    members = z.inventory()
    assert z.member(members[0]) == b"t,x,y\n0,1,2\n"


def test_remote_zip_rejects_traversal():
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("../escape", "bad")
    raw = b.getvalue()

    class Cache:
        def range(self, url, start, end, total, offline):
            return raw[start : end + 1], {}

    with pytest.raises(ValueError, match="Unsafe"):
        RemoteZip(Cache(), IDF_ZIP, len(raw), True).inventory()


def test_source_policy_and_offline_cache_fail_closed(tmp_path):
    for u in [
        "https://evil.example/data",
        "http://zenodo.org/api/records/16992976",
        "https://datadryad.org/private/token",
    ]:
        with pytest.raises(ValueError):
            policy(u)
    with pytest.raises(ValueError, match="Offline"):
        DataCache(tmp_path).range(IDF_ZIP, 0, 9, 10, True)


def test_registry_separates_estimators_and_processes():
    r = registry()
    assert len(r) == 10 and len({v["id"] for v in r}) == 10
    assert next(v for v in r if v["id"] == "HMM")["category"] == "latent_state"


def test_observation_cadence_does_not_change_latent_process():
    a = Simulation(5, 20, scenario="C", observe_every=1).run()
    b = Simulation(5, 20, scenario="C", observe_every=5).run()
    assert a["true_state"] == b["true_state"]
    assert b["metrics"]["valid_observations"] == 25
    assert b["metrics"]["scheduled_observations"] == 25
    assert a["metrics"]["valid_observations"] == 105


def test_interaction_checkpoint_keeps_neighbor_statistics():
    s = Simulation(10, 20, scenario="C")
    s.step()
    s.step()
    r = Simulation.restore(json.loads(json.dumps(s.serialize())))
    assert s.run() == r.run()


def test_miluv_range_error_and_reference_geometry():
    from dynamics.miluv import statistics, align_mocap

    s = statistics(np.array([-1, 0, 1.0]), np.array([1, 1, 1.0]))
    assert (
        s["RMSE_m"] == pytest.approx(np.sqrt(2 / 3))
        and s["MAE_m"] == pytest.approx(2 / 3)
        and s["coverage95"] == 1
    )
    mocap = pd.DataFrame(
        {
            "timestamp": [0.0, 1.0],
            "pose.position.x": [1.0, 2.0],
            "pose.position.y": [0.0, 0.0],
            "pose.position.z": [0.0, 0.0],
            "pose.orientation.x": [0.0, 0.0],
            "pose.orientation.y": [0.0, 0.0],
            "pose.orientation.z": [0.0, 0.0],
            "pose.orientation.w": [1.0, 1.0],
        }
    )
    rf = pd.DataFrame(
        {"timestamp": [0.001, 1.0, 2.0], "from_id": [10, 10, 10], "to_id": [0, 0, 0]}
    )
    x, good, dt = align_mocap(mocap, rf, {"0": [0, 0, 0]}, {"10": [1, 0, 0]})
    np.testing.assert_allclose(x[:2], [2, 3])
    assert good.tolist() == [True, True, False] and np.isnan(x[2])


def test_pinned_source_tamper_and_missing_object_fail(tmp_path):
    import hashlib

    c = DataCache(tmp_path)
    b = b"original"
    sha = hashlib.sha256(b).hexdigest()
    p = c.blobs / (sha + ".data")
    p.write_bytes(b)
    r = {"url": IDF_ZIP, "sha256": sha}
    assert c.frozen(r).read_bytes() == b
    p.write_bytes(b"changed")
    with pytest.raises(ValueError):
        c.frozen(r)
    p.unlink()
    with pytest.raises(ValueError):
        c.frozen(r)


def test_persistent_jobs_reload_and_unsafe_hosts(tmp_path):
    from dynamics.service import DynamicsEngine
    from dynamics.api import create_app
    from fastapi.testclient import TestClient

    engine = DynamicsEngine(tmp_path)
    job = engine.run("SIMULATION", {"agents": 5, "steps": 10})
    assert job["status"] == "completed", job
    other = DynamicsEngine(tmp_path)
    assert other.store.get(job["id"])["results_sha256"] == job["results_sha256"]
    assert other.verify(job["id"])["passed"]
    c = TestClient(create_app(other), base_url="http://127.0.0.1:4206")
    assert c.get("/api/models").status_code == 200
    assert c.get("/api/jobs").json()[0]["id"] == job["id"]
    assert (
        c.get("/api/jobs/" + job["id"] + "/results").json()["kind"] == "SIMULATED DATA"
    )
    assert c.post("/api/simulations", json={}).status_code == 403
    assert (
        c.post(
            "/api/simulations",
            headers={"x-research-request": "1", "origin": "https://evil.example"},
            json={},
        ).status_code
        == 403
    )
    assert c.get("/", headers={"host": "evil.example"}).status_code == 400
    assert c.get("/static/unknown.js").status_code == 404
    assert (
        c.post(
            "/api/jobs/" + job["id"] + "/insight",
            headers={"x-research-request": "1"},
            json={},
        ).json()["status"]
        == "disabled"
    )
    assert (
        c.post(
            "/api/simulations",
            headers={"x-research-request": "1"},
            json={"agents": 10000},
        ).status_code
        == 422
    )
    assert (
        c.post(
            "/api/simulations", headers={"x-research-request": "1"}, json={"evil": 1}
        ).status_code
        == 422
    )


def test_reports_use_generated_numbers_and_separate_sources(tmp_path):
    from dynamics.reporting import rows, metrics_csv, html_report

    r = {
        "experiment": "DME-002",
        "title": "Control",
        "kind": "REAL EXPERIMENTAL DATA",
        "counts": {"observations_analyzed": 2},
        "metrics": {},
        "flights": [
            {
                "flight_id": "control",
                "valid_rows": 2,
                "calibrated": {
                    "MAE_m": 0.5,
                    "RMSE_m": 0.6,
                    "bias_m": 0.1,
                    "coverage95": 0.5,
                },
                "raw": {"RMSE_m": 1},
                "nearest_mocap": {
                    "matched": 2,
                    "unmatched": 0,
                    "reconstructed_vs_published_reference": {"RMSE_m": 0.01},
                },
                "sensitivity": [],
            }
        ],
        "substitution": {"original": "AERPAW", "new": "MILUV"},
        "method_version": "control",
        "dataset": {"license": "CC BY4.0"},
        "limits": ["Fixture test only"],
        "results_sha256": "a" * 64,
    }
    text = html_report(r, {"completed_at": "2026-11-06", "performance": {}}, [])
    assert "0.6" in text and "MILUV" in text and "Fixture test only" in text
    assert metrics_csv(r).startswith("flight_id,") and rows(r)[0]["RMSE_m"] == 0.6


def test_nonfinite_simulation_parameters_fail_closed():
    for kwargs in [{"dt": float("nan")}, {"noise": float("inf")}, {"agents": True}]:
        with pytest.raises(ValueError):
            Simulation(**kwargs)

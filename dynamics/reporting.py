# SPDX-License-Identifier: Apache-2.0
"""Data-derived standalone reports; no generated prose supplies measurements."""

from pathlib import Path
import os, json, html, csv, io, hashlib

os.environ.setdefault(
    "MPLCONFIGDIR",
    str(Path(__file__).resolve().parents[1] / ".local/dynamics-matplotlib"),
)
import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt
import numpy as np

CSS = """body{font:16px/1.65 system-ui,sans-serif;color:#18272c;background:#f7f5ef;margin:auto;max-width:1120px;padding:50px 25px}h1{font-size:42px;line-height:1.1;max-width:900px}h2{margin-top:50px}a{color:#24616c}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border-bottom:1px solid #cbd2ce;padding:12px;text-align:left}th{background:#e8ede8}figure{margin:35px 0}img{max-width:100%;height:auto}pre{white-space:pre-wrap;font-size:13px;overflow-wrap:anywhere}small,.muted{color:#566a70}.label{letter-spacing:3px;font:12px ui-monospace,monospace}article{border-left:3px solid #527c75;padding-left:20px;margin:24px 0}.scroll{overflow:auto}footer{margin-top:65px;border-top:1px solid #bbc6c1;padding-top:20px}@media print{body{padding:0}h2{break-after:avoid}figure,table{break-inside:avoid}}"""


def rows(r):
    if r["experiment"] == "DME-001":
        return [
            {
                "model": k,
                **{
                    x: v[x]
                    for x in [
                        "ADE_m",
                        "FDE_m",
                        "RMSE_m",
                        "MAE_coordinate_m",
                        "coverage95",
                    ]
                },
            }
            for k, v in r["metrics"].items()
        ]
    if r["experiment"] == "DME-002":
        return [
            {
                "flight_id": f["flight_id"],
                "n": f["valid_rows"],
                **{
                    x: f["calibrated"][x]
                    for x in ["MAE_m", "RMSE_m", "bias_m", "coverage95"]
                },
                "raw_RMSE_m": f["raw"]["RMSE_m"],
            }
            for f in r.get("flights", [])
        ]
    return [
        {
            "scenario": g["scenario"],
            "agents": g["agents"],
            "replicates": g["runs"],
            **{k: v["mean"] for k, v in g["metrics"].items()},
        }
        for g in r["grouped_results"]
    ]


def metrics_csv(r):
    values = rows(r)
    s = io.StringIO()
    w = csv.DictWriter(s, fieldnames=list(values[0]) if values else ["status"])
    w.writeheader()
    w.writerows(values)
    return s.getvalue()


def table(values):
    if not values:
        return "<p>INSUFFICIENT EVIDENCE</p>"
    keys = list(values[0])
    e = lambda v: html.escape(str(round(v, 6) if isinstance(v, float) else v))
    return (
        '<div class="scroll"><table><thead><tr>'
        + "".join("<th>" + e(k) + "</th>" for k in keys)
        + "</tr></thead><tbody>"
        + "".join(
            "<tr>" + "".join("<td>" + e(v.get(k, "")) + "</td>" for k in keys) + "</tr>"
            for v in values
        )
        + "</tbody></table></div>"
    )


def methodology(r):
    exp = r["experiment"]
    text = (
        f"# {exp} — method\n\nKind: {r['kind']}. Algorithm: {r['method_version']}.\n\n"
    )
    if exp == "DME-001":
        text += "First30 sorted source GPS files; first12development, next9validation, last9test. File-disjoint, not recording-day-independent. Twenty past samples per origin, stride50; nearest observed targets1/3/5s within120ms; source gaps>2s rejected. WGS84 ECEF→local ENU horizontal, no altitude or Euclidean degrees. Six methods share identical origins and targets. q∈{.01,1,100}, R∈{1,10}, validationADE/NLL tie-break only. Covariance scale=validation equal-flight mean Mahalanobis²/2. Ensemble simplex minimizes validation equal-flight MSE; total covariance includes within-model and between-mean dispersion. ADE/FDE/RMSE/MAE/coverage aggregate equally over nine test files. Nominal95percent Gaussian ellipse (χ²₂), empirical coverage and999 whole-file bootstrap samples. Exact paired sign-flip512patterns, Holm correction over6comparisons. Robustness adds2m context noise or30percent missingness with untouched held-out reference and matched-origin baseline. HMM3 descriptive states fit development only on offline speed/acceleration/turn-rate features; not causal intent inference.\n"
    elif exp == "DME-002":
        text += "AERPAW unavailable(403public/401API), replaced with user-authorized MILUV v1(CC BY4.0). Three predefined single-UAV sequences share anchor constellation0. Every selected UWB row analyzed; finite/positive gates, first timestamp+pair duplicate retained, explicit stable time sort. Residual=calibrated(or raw) range−source gt_range, metres. Source gt_range derived from motion capture, not exact truth. Published std assessed with ±1.95996398454σ nominal normal95percent intervals. A second computation uses nearest motion capture(≤20ms), no extrapolation: tag_world=p_world+Rotation(quaternion xyzw)×tag_body; distance=norm(tag_world−anchor_world), pinned published extrinsics. Tolerance5/10/20ms and offset−20/−10/0/10/20ms sensitivity reported. Source spline-derived reference may differ from nearest-time reconstruction. No synchronization fitted to residuals; no3D position error claimed. Pooled metrics observation-weighted; equal-flight MAE separately reported. Source calibration training/validation independence unknown; total systematic uncertainty unavailable.\n"
    else:
        text += "Five synthetic scenarios Aindependent/Bstochastic/Clocal velocity consensus/Dpartial observations/Eheterogeneous CV+CRW; N1/5/10/20/50×20seeds=500main runs. dt=.1s,200steps, q=noise²=.09, radius12abstract units, coupling.8, observationσ1, Dmissing.3. Synchronous consensus dv_i=κ(mean_neighbor(v)−v_i)dt; reflecting box±100, no targets or geography. Three separate RNG streams for process/measurement/missingness. Bootstrap resamples independent seeds. Sensitivity dt .05/.1/.2 at equal20s, noise .1/.3/.8, coupling0/.8/1.6, missing0/.3/.6. Observation cadence1/2/5 supplemental after first pilot. Same-seed replay byte checks strict scientific JSON. Timing excludes no work silently; run timing includes state recording/result assembly. Abstract results are not validated drone aerodynamics.\n"
    return (
        text
        + "\n## Limits\n"
        + "".join("- " + x + "\n" for x in r["limits"])
        + "\n## Source\n"
        + json.dumps(r["dataset"], indent=2, ensure_ascii=False)
        + "\n"
    )


def reproduce_text(r):
    return f"# Reproduce {r['experiment']}\n\nUse Python3.12 and the pinned lock. From the distribution root:\n\n    python -m dynamics.cli run {r['experiment']} --data /your/local/dynamics-data\n    python -m dynamics.cli reproduce JOB_UUID --data /your/local/dynamics-data\n\nThe second command rehashes every acquired source object, reparses original selected ZIP bytes and recomputes mathematical results offline, with the original manifest parameters. Missing or altered cached bytes fail explicitly; a new download is a new acquisition, not substitution for an old vintage. The results_sha256 excludes measured execution timing but includes all scientific results and source identities. Public source packages do not contain multi-GB third-party archives. Dataset source availability may change. All seeds/parameters/dependency versions and source hashes are in the manifest.\n"


def figures(r, folder):
    d = Path(folder) / "figures"
    d.mkdir(exist_ok=True)
    out = []
    exp = r["experiment"]
    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.facecolor": "#f7f5ef",
            "axes.facecolor": "#fffdf9",
            "axes.prop_cycle": plt.cycler(
                color=["#3c6c76", "#a6714c", "#748f64", "#995f64"]
            ),
        }
    )

    def save(fig, name, caption):
        p = d / name
        fig.savefig(p, dpi=150, bbox_inches="tight")
        plt.close(fig)
        out.append(
            {
                "file": "figures/" + name,
                "caption": caption,
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            }
        )

    if exp == "DME-001":
        ks = list(r["metrics"])
        v = [r["metrics"][k] for k in ks]
        fig, ax = plt.subplots(figsize=(10, 4.5))
        ax.bar(ks, [x["ADE_m"] for x in v])
        ax.set(
            ylabel="Equal-flight mean ADE (m)",
            title="Held-out civil flights · observed GNSS reference",
        )
        save(
            fig,
            "model-accuracy.png",
            "Six individual methods and validation-fitted ensemble, identical held-out origins. GNSS is a noisy reference.",
        )
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.bar(ks, [100 * x["coverage95"] for x in v])
        ax.axhline(95, color="#a6714c", ls="--", label="Nominal95%")
        ax.set(
            ylim=(0, 100),
            ylabel="Empirical coverage (%)",
            title="Uncertainty calibration on test flights",
        )
        ax.legend()
        save(
            fig,
            "uncertainty-coverage.png",
            "Actual coverage of nominal Gaussian95percent regions; validation fitting does not guarantee test coverage.",
        )
        fig, ax = plt.subplots(figsize=(7, 5))
        f = r["flights"][-1]
        x = np.array(f["display"]["position_m"])
        ax.plot(*x.T, label=f["flight_id"])
        ax.set(
            xlabel="Local east (m)",
            ylabel="Local north (m)",
            title="Recorded trajectory · local projection",
        )
        ax.axis("equal")
        ax.legend()
        save(
            fig,
            "recorded-flight.png",
            "Public display uses relative ENU and stride only; observations are not simulation truth.",
        )
    elif exp == "DME-002":
        fs = r["flights"]
        fig, ax = plt.subplots(figsize=(10, 4))
        ix = np.arange(len(fs))
        ax.bar(ix - 0.17, [f["raw"]["RMSE_m"] for f in fs], 0.34, label="Raw")
        ax.bar(
            ix + 0.17,
            [f["calibrated"]["RMSE_m"] for f in fs],
            0.34,
            label="Source calibrated",
        )
        ax.set_xticks(ix, [f["flight_id"].replace("default_1_", "") for f in fs])
        ax.set(
            ylabel="Range RMSE (m)",
            title="MILUV · range residuals against published reference",
        )
        ax.legend()
        save(
            fig,
            "range-errors.png",
            "Observation-weighted per-flight range RMSE; source calibration is not an independent sensor comparison.",
        )
        f = fs[0]
        a = f["display"]
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(
            [x["time_s"] for x in a], [x["calibrated_residual_m"] for x in a], ".", ms=2
        )
        ax.set(
            xlabel="Source-relative time (s)",
            ylabel="Range residual (m)",
            title=f["flight_id"],
        )
        save(
            fig,
            "range-residuals.png",
            "Display stride only; all valid rows enter metrics. No3D position error inferred.",
        )
    else:
        replay = r["replays"]["C"]
        x = np.array(replay["true_state"])
        fig, ax = plt.subplots(figsize=(8, 6))
        for i in range(x.shape[1]):
            ax.plot(x[:, i, 0], x[:, i, 1], lw=0.6, alpha=0.7)
        ax.set(
            xlabel="Abstract position x",
            ylabel="Abstract position y",
            title="SIMULATED DATA · 50 interacting agents",
        )
        ax.axis("equal")
        save(
            fig,
            "multi-agent.png",
            "Computed synthetic states; no real geography or drone control.",
        )
        fig, ax = plt.subplots(figsize=(10, 4))
        for scenario in ["A", "B", "C", "D", "E"]:
            gs = [g for g in r["grouped_results"] if g["scenario"] == scenario]
            ax.plot(
                [g["agents"] for g in gs],
                [g["metrics"]["velocity_dispersion_mean"]["mean"] for g in gs],
                "-o",
                label=scenario,
            )
        ax.set(
            xlabel="Agents",
            ylabel="Mean velocity dispersion (abstract²/s²)",
            title="20 independent seeds per configuration",
        )
        ax.legend()
        save(
            fig,
            "collective-statistics.png",
            "Seed-level variability and interaction rules determine the measured collective statistics.",
        )
    return out


def html_report(r, manifest, plots):
    e = html.escape
    body = (
        '<p class="label">DYNAMICS LAB · ENGINE01</p><h1>'
        + e(r["title"])
        + "</h1><p>"
        + e(r["experiment"] + " · " + r["kind"])
        + '</p><p class="muted">Computed '
        + e(manifest["completed_at"])
        + " · reproducible scientific prototype</p>"
    )
    body += (
        "<h2>Objective & dataset</h2><p>"
        + e(
            {
                "DME-001": "Compare six motion models and a validation-fitted ensemble on held-out civil flight observations.",
                "DME-002": "Assess historical UWB measurement consistency and uncertainty against a motion-capture-derived reference.",
                "DME-003": "Measure scaling, collective statistics and reproducibility of an abstract stochastic multi-agent system.",
            }[r["experiment"]]
        )
        + "</p><pre>"
        + e(json.dumps(r["counts"], indent=2))
        + "</pre>"
    )
    body += "<h2>Measured and computed results</h2>" + table(rows(r))
    for p in plots:
        body += (
            '<figure><img src="'
            + e(p["file"])
            + '" alt="'
            + e(p["caption"])
            + '"><figcaption>'
            + e(p["caption"])
            + "</figcaption></figure>"
        )
    if r["experiment"] == "DME-001":
        body += (
            "<h2>Paired comparison and uncertainty</h2>"
            + table(
                [
                    {
                        k: v
                        for k, v in x.items()
                        if k not in ["interpretation", "paired_flight_bootstrap95"]
                    }
                    for x in r["paired_comparisons"]
                ]
            )
            + "<p>Intervals resample whole flight files; shared platform/circuit and unknown recording days limit independence. More complex methods and the ensemble are not assumed superior.</p><pre>"
            + e(
                json.dumps(
                    {
                        k: {
                            "ADE_interval95": v["ADE_interval95"],
                            "coverage_interval95": v["coverage_interval95"],
                        }
                        for k, v in r["metrics"].items()
                    },
                    indent=2,
                )
            )
            + "</pre><h2>Robustness</h2>"
            + table(
                [
                    {
                        "condition": c,
                        "model": k,
                        "ADE_m": m["ADE_m"],
                        "matched_baseline_ADE_m": a["matched_unperturbed_metrics"][k][
                            "ADE_m"
                        ],
                        "origins": a["origins"],
                    }
                    for c, a in r["robustness"].items()
                    for k, m in a["metrics"].items()
                ]
            )
        )
    if r["experiment"] == "DME-002":
        body += (
            "<h2>Source substitution and numerical cross-check</h2><pre>"
            + e(json.dumps(r["substitution"], indent=2))
            + "</pre>"
            + table(
                [
                    {
                        "flight": f["flight_id"],
                        "matched": f["nearest_mocap"]["matched"],
                        "unmatched": f["nearest_mocap"]["unmatched"],
                        "reconstructed_reference_RMSE_m": f["nearest_mocap"][
                            "reconstructed_vs_published_reference"
                        ]["RMSE_m"],
                    }
                    for f in r["flights"]
                ]
            )
            + "<h2>Synchronisation sensitivity</h2>"
            + table(
                [
                    {
                        "flight": f["flight_id"],
                        "tolerance_s": s["nearest_tolerance_s"],
                        "offset_s": s["applied_time_offset_s"],
                        "matched": s["matched"],
                        "RMSE_m": s["range_residual"].get("RMSE_m"),
                    }
                    for f in r["flights"]
                    for s in f["sensitivity"]
                ]
            )
        )
    body += (
        "<h2>Method & parameters</h2><pre>"
        + e(methodology(r))
        + "</pre><h2>Validation and reproducibility</h2><pre>"
        + e(reproduce_text(r))
        + "</pre><p>Scientific result SHA-256: <code>"
        + e(r["results_sha256"])
        + "</code>. Numerical correctness is evaluated with independent controls and source replay; scientific validity remains bounded by source quality and model assumptions.</p><h2>Limits</h2>"
        + "".join("<article>" + e(v) + "</article>" for v in r["limits"])
        + "<h2>Sources & attribution</h2><pre>"
        + e(json.dumps(r["dataset"], indent=2, ensure_ascii=False))
        + "</pre><h2>Execution evidence</h2><pre>"
        + e(json.dumps(manifest["performance"], indent=2))
        + "</pre><footer>Original software Apache License2.0. Third-party source data retains its own licence. AI hypotheses do not generate these measurements. Offline research, no operational control.</footer>"
    )
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>'
        + e(r["experiment"] + " · Dynamics Lab")
        + "</title><style>"
        + CSS
        + "</style><body>"
        + body
        + "</body></html>"
    )

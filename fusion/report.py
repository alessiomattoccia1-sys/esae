# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Standalone scientific HTML, original plots and separately licensed data derivatives."""

from pathlib import Path
import csv, io, json, html, os

os.environ.setdefault(
    "MPLCONFIGDIR",
    str(Path(__file__).resolve().parents[1] / ".local/fusion-matplotlib"),
)
import numpy as np
import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt
from PIL import Image


def figures(report, folder):
    folder = Path(folder)
    assets = folder / "figures"
    assets.mkdir(exist_ok=True)
    exp = report["experiment"]
    files = []
    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.facecolor": "#f5f3ed",
            "axes.facecolor": "#fffdf8",
            "axes.edgecolor": "#aebbb5",
            "text.color": "#18252c",
            "axes.labelcolor": "#43565d",
        }
    )
    if exp == "FPE-001":
        for i, r in enumerate(report["signals"]):
            if (
                r["status"] != "computed"
                or r.get("spectral", {}).get("status") != "computed"
            ):
                continue
            identity = r["identity"]
            shot = identity["shot_id"]
            unit = identity["unit"]
            title = f"MAST {shot} / {identity['diagnostic']} / {unit}"
            display = r["display"]
            spec = r["spectral"]
            fig, axes = plt.subplots(2, 2, figsize=(12, 7), layout="constrained")
            axes[0, 0].plot(
                display["time_s"],
                display["original"],
                color="#426c7a",
                lw=0.8,
                label="Original selected measurement",
            )
            axes[0, 0].plot(
                display["time_s"],
                display["savgol21"],
                color="#a8763b",
                lw=0.8,
                label="SG21 polynomial3",
            )
            axes[0, 0].set(xlabel="Source relative time / s", ylabel=unit)
            axes[0, 0].legend(fontsize=7)
            axes[0, 1].plot(
                display["time_s"], display["derivative"], color="#426c7a", lw=0.7
            )
            axes[0, 1].set(xlabel="Source relative time / s", ylabel=unit + "/s")
            axes[1, 0].semilogy(
                spec["psd"]["frequency_hz"], spec["psd"]["density"], color="#426c7a"
            )
            axes[1, 0].set(
                xlabel="Frequency / Hz",
                ylabel=f"{unit}²/Hz",
                title="Welch PSD / full-band display",
            )
            stft = spec["stft"]
            z = np.asarray(stft["magnitude"])
            z = np.where(z > 0, z, np.nan)
            axes[1, 1].pcolormesh(
                stft["time_s"],
                stft["frequency_hz"],
                np.log10(z),
                shading="auto",
                cmap="cividis",
            )
            axes[1, 1].set(
                xlabel="Source relative time / s",
                ylabel="Frequency / Hz",
                title="STFT / log10 magnitude; max-pooled display bins",
            )
            fig.suptitle(
                title + "\nUKAEA FAIR-MAST / CC BY-SA4.0 / analysis by Mattoccia Labs",
                fontsize=12,
            )
            name = f"mast-{shot}-{i}.png"
            fig.savefig(
                assets / name, dpi=125, metadata={"Software": "FPRE / Matplotlib"}
            )
            plt.close(fig)
            files.append(
                {
                    "file": "figures/" + name,
                    "caption": title
                    + "; quality/segment/filter parameters in JSON. Signal-processing features are not identified plasma modes.",
                    "license": "CC-BY-SA-4.0",
                }
            )
    else:
        for item in report["images"]:
            shot = item["identity"]["shot_id"]
            array = np.load(
                folder / "detector-inputs" / item["display_file"], allow_pickle=False
            )
            lo, hi = np.nanquantile(array, [0.01, 0.99])
            scaled = np.uint8(np.clip((array - lo) / (hi - lo or 1), 0, 1) * 255)
            rawname = f"icf-{shot}-raw.png"
            Image.fromarray(scaled).save(assets / rawname)
            files.append(
                {
                    "file": "figures/" + rawname,
                    "caption": f"STFC OMEAG_SAI-23A, shot {shot}: original raw detector array displayed with explicit linear P01–P99 scaling and stride; no physical conversion. CC BY4.0; source authors in manifest.",
                    "license": "CC-BY-4.0",
                }
            )
            baseline = item["baseline"]
            processed = np.maximum(array - baseline["background"]["value"], 0)
            upper = float(np.nanquantile(processed, 0.99))
            processed_name = f"icf-{shot}-processed.png"
            Image.fromarray(
                np.uint8(np.clip(processed / (upper or 1), 0, 1) * 255)
            ).save(assets / processed_name)
            files.append(
                {
                    "file": "figures/" + processed_name,
                    "caption": f"Shot {shot}: display-only positive raw-minus-original-border-median, clipped at transformed P99. Detector coordinates and explicit stride; source original unchanged. STFC CC BY4.0.",
                    "license": "CC-BY-4.0",
                }
            )
            profiles = baseline["profiles"]
            fig, axes = plt.subplots(1, 2, figsize=(10, 3.5), layout="constrained")
            axes[0].plot(profiles["column_sum"], color="#426c7a")
            axes[1].plot(profiles["row_sum"], color="#426c7a")
            axes[0].set(
                xlabel="Detector column / pixel",
                ylabel="Positive background-subtracted intensity sum",
            )
            axes[1].set(
                xlabel="Detector row / pixel",
                ylabel="Positive background-subtracted intensity sum",
            )
            fig.suptitle(f"Shot {shot} / fixed full-frame detector profiles / CC BY4.0")
            name = f"icf-{shot}-profiles.png"
            fig.savefig(assets / name, dpi=120)
            plt.close(fig)
            files.append(
                {
                    "file": "figures/" + name,
                    "caption": "Generic detector-pixel profiles after declared border-median subtraction; not plasma dimensions, yield or implosion performance.",
                    "license": "CC-BY-4.0",
                }
            )
    return files


def findings_csv(r):
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(
        [
            "id",
            "experiment",
            "kind",
            "title",
            "method",
            "unit",
            "uncertainty",
            "verification",
            "limits",
            "numerical_result_json",
            "evidence_json",
        ]
    )
    for f in r["findings"]:
        w.writerow(
            [
                f[k]
                for k in [
                    "id",
                    "experiment",
                    "kind",
                    "title",
                    "method",
                    "unit",
                    "uncertainty",
                    "verification",
                    "limits",
                ]
            ]
            + [
                json.dumps(f["numerical_result"], separators=(",", ":")),
                json.dumps(f["evidence"]),
            ]
        )
    return out.getvalue()


def methodology(r):
    exp = r["experiment"]
    s = (
        "# "
        + exp
        + " — scientific methodology\n\nReal experimental retrospective data. Configuration:\n\n```json\n"
        + json.dumps(r["configuration"], indent=2)
        + "\n```\n\n"
    )
    if exp == "FPE-001":
        s += "Catalog categories M9/Conventional/Lower Single Null/700kA are matched before viewing signal values; nearest shot IDs to documented30421 define order. All candidate exclusions are retained. Level2 magnetics source ingested_at and commit_url are retained. Time coordinates must be monotonic and finite; no interpolation or sorting repairs. Pint converts explicitly stated units. Quality checks report finite samples, gaps, duplicates, jitter, constant values and apparent extreme plateaus without asserting saturation.\n\nTemporal statistics use finite selected samples. Spectra use the longest contiguous regular valid segment. Welch uses periodic Hann, constant detrend,50percent overlap, window largest power of2 not exceeding segment/4, capped4096. Half/double windows are reported. FFT amplitudes use Hann coherent-gain normalization; STFT has no padding or boundary extension. Frequency-bin half width is grid resolution, not total uncertainty.\n\nDerivative events use retrospective median/MAD thresholds4/6/8 and5ms peak separation; no physical event names are assigned. Savitzky-Golay degree3 windows11/21/41 are all retained, not selected to maximize an outcome. Moving-block percentile intervals for the mean use499replicates,seed20261106,block approximatelysqrt(N), conditional on representative dependence/stability; unknown calibration error is not included. Same-shot coarse/fast comparisons use declared cell means and descriptive correlation; boxcar attenuation does not prove alias freedom and no IID p-values are used. Cross-shot dispersion is observational, not causal or phase-aligned.\n"
    else:
        s += "The complete ZIP inventory is validated for traversal, absolute/backslash paths, symlinks, duplicate paths, encryption and expansion limits. Only7raw SLOS-TRXI HDF4 files are selected by a fixed filename rule; target/operating/performance files are cataloged without numerical analysis. A bounded sandboxed native reader reads only gel_raw; processed PSL is not substituted for raw measurement.\n\nOriginal uint16 detector arrays remain unchanged. All finite/invalid pixels and raw statistics are counted. Detector backgrounds use outer10percent borders and quantiles25/50/75. Positive raw-minus-background weights define full-frame detector centroids and profiles in pixels. Whole-frame and fixed central80percent ROIs yield6predeclared cases per image. Their ranges measure preprocessing sensitivity, not confidence intervals or total physical uncertainty. No object-plane conversion, magnification, radiometry, yield, temperature, areal density or implosion-performance inference is performed. ICF03 explicitly uses same-measurement robustness instead of cross-implosion comparison.\n"
    return (
        s
        + "\nObserved data, derived quantities, statistical descriptions and unverified hypotheses remain distinct. Source licenses and modifications are documented separately from original-code Apache2.0.\n"
    )


def reproduction(r):
    return (
        "# Reproduce "
        + r["experiment"]
        + "\n\nFrom the original source release, on qualified macOS Apple Silicon/Python3.12:\n\n```sh\npython3.12 scripts/setup_fusion.py\n.venv-fpre/bin/python -m fusion.cli run --experiment "
        + r["experiment"]
        + " --data .local/fusion\n.venv-fpre/bin/python -m fusion.cli reproduce --experiment "
        + r["experiment"]
        + " --job JOB_ID --data .local/fusion\n```\n\nInitial run acquires official data explicitly. Keep source responses and manifest. Reproduce rehashes original bytes and recomputes without network; missing or modified source objects cause a visible failure. Upstream may replace Zarr objects at the same URL, so fresh acquisition is not automatically the original version. A qualified selected-input public replay is separately labeled; it cannot replace full raw-source validation. No model, apparatus access or cloud is required. Other operating systems are not qualified.\n"
    )


def html_report(r, manifest, plots):
    e = lambda v: html.escape(str(v), quote=True)

    def table(head, rows):
        return (
            '<div class="table"><table><thead><tr>'
            + "".join("<th>" + e(x) + "</th>" for x in head)
            + "</tr></thead><tbody>"
            + "".join(
                "<tr>" + "".join("<td>" + e(x) + "</td>" for x in row) + "</tr>"
                for row in rows
            )
            + "</tbody></table></div>"
        )

    findings = "".join(
        '<article><p class="kind">'
        + e(f["id"] + " / " + f["kind"])
        + "</p><h3>"
        + e(f["title"])
        + "</h3><p>"
        + e(f["method"])
        + "</p><pre>"
        + e(json.dumps(f["numerical_result"], indent=2))
        + "</pre><p>Units: "
        + e(f["unit"])
        + "</p><p>Uncertainty: "
        + e(f["uncertainty"])
        + "</p><p>Limits: "
        + e(f["limits"])
        + "</p></article>"
        for f in r["findings"]
    )
    images = "".join(
        '<figure><img src="'
        + e(p["file"])
        + '" alt="'
        + e(p["caption"])
        + '" loading="lazy"><figcaption>'
        + e(p["caption"])
        + "</figcaption></figure>"
        for p in plots
    )
    details = ""
    if r["experiment"] == "FPE-001":
        details = table(
            [
                "Shot",
                "Diagnostic",
                "N / valid",
                "Unit",
                "RMS",
                "Peak / Hz",
                "Resolution / Hz",
                "Events",
            ],
            [
                [
                    x["identity"]["shot_id"],
                    x["identity"]["diagnostic"],
                    str(x["quality"]["samples"])
                    + " / "
                    + str(x["quality"]["valid_samples"]),
                    x["identity"]["unit"],
                    x["statistics"].get("rms"),
                    x.get("spectral", {}).get("dominant_non_dc_hz"),
                    x.get("spectral", {}).get("frequency_bin_hz"),
                    len(x.get("events", [])),
                ]
                for x in r["signals"]
            ],
        )
    else:
        details = table(
            [
                "Shot",
                "Shape",
                "Valid pixels",
                "Mean raw",
                "Detector centroid / px",
                "Sensitivity x/y / px",
            ],
            [
                [
                    x["identity"]["shot_id"],
                    x["baseline"]["shape"],
                    x["baseline"]["valid_pixels"],
                    x["baseline"]["raw_intensity"]["mean"],
                    x["baseline"]["centroid_detector_px"],
                    x["robustness"],
                ]
                for x in r["images"]
            ],
        ) + table(
            ["File", "Format", "Bytes", "Diagnostic", "Selected"],
            [
                [
                    x["file"],
                    x["format"],
                    x["bytes"],
                    x["diagnostic"],
                    x["selected_raw_image"],
                ]
                for x in r["inventory"]["entries"]
                if not x["directory"]
            ],
        )
    refs = (
        "<ul>"
        + "".join(
            '<li><a href="'
            + e(s["url"])
            + '">'
            + e(s["source"])
            + "</a> · SHA256 <code>"
            + e(s["sha256"])
            + "</code></li>"
            for s in manifest["sources"]
        )
        + "</ul>"
    )
    body = (
        '<p class="kind">MATTOCCIA LABS / RESEARCH ENGINES / FUSION</p><h1>'
        + e(r["title"])
        + "</h1><p>Real experimental retrospective analysis. Version0.1.0; computational verification does not establish a new physical discovery.</p><h2>Abstract and objective</h2><p>"
        + (
            "Characterize comparable MAST diagnostic signals, their temporal/spectral properties and method sensitivity. Candidate events remain unclassified."
            if r["experiment"] == "FPE-001"
            else "Inventory the published experimental archive and characterize raw detector arrays and pixel-domain processing robustness. No implosion-performance or operating-parameter analysis."
        )
        + "</p><h2>Dataset, selection and provenance</h2><pre>"
        + e(
            json.dumps(
                {
                    "dataset": r["dataset"],
                    "configuration": r["configuration"],
                    "counts": r["counts"],
                },
                indent=2,
            )
        )
        + "</pre><h2>Computational methods</h2><p>Methods and all parameters are in the accompanying METHODOLOGY and manifest. Originals and transformed displays remain distinct. Units and unknown calibrations are explicit.</p><h2>Verified quantitative findings</h2>"
        + findings
        + "<h2>Measurements and comparisons</h2>"
        + details
        + "<h2>Original scientific visualizations</h2>"
        + images
        + "<h2>Uncertainty, discussion and limitations</h2><ul>"
        + "".join("<li>" + e(v) + "</li>" for v in r["limitations"])
        + "</ul><h2>Validation and conclusions</h2><p>Algorithm controls, independent numerical checks and exact acquired-source replay accompany publication. These are reproducible descriptions of selected real data, not a new plasma law, named instability, ignition result or validated prediction.</p><code>"
        + e(r["results_sha256"])
        + "</code><h2>Sources, data license and attribution</h2><p>Original software: Apache2.0. Data-derived scientific report, plots and selected measurements: "
        + e(r["data_derivative_license"])
        + ". Source attribution and modifications: acquired source arrays, unit normalization, explicit selections, deterministic statistics and labeled display scaling by Mattoccia Labs; no source endorsement.</p>"
        + refs
        + "<h2>Reproduction</h2><pre>"
        + e(reproduction(r))
        + "</pre>"
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src \'self\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'"><title>'
        + e(r["experiment"])
        + " / FPRE</title><style>body{font:16px/1.85 system-ui;background:#f5f3ed;color:#18252c;max-width:1180px;margin:auto;padding:40px 24px}h1{font-size:clamp(35px,5vw,65px);line-height:1.15;font-weight:500;letter-spacing:-.04em}h2{font-size:30px;line-height:1.2;margin-top:55px;font-weight:500}h3{font-size:23px;font-weight:500}pre{font:12px/1.8 monospace;white-space:pre-wrap;overflow-wrap:anywhere;background:#fffdf8;padding:22px;border:1px solid #cbd3cf;border-radius:13px}.kind{font:11px/2 monospace;color:#7c6747;letter-spacing:.08em}article{border-top:1px solid #cbd3cf;padding-top:25px;margin-top:35px}.table{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:12px}th,td{text-align:left;border-bottom:1px solid #cbd3cf;padding:12px;vertical-align:top}figure{margin:35px 0}img{width:100%;height:auto;border:1px solid #cbd3cf;border-radius:12px}figcaption{font-size:12px;color:#53656b;line-height:1.8}a{color:#3e6877}code,li{overflow-wrap:anywhere}li{margin-bottom:12px}</style></head><body>"
        + body
        + "</body></html>"
    )

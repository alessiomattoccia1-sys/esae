# SPDX-License-Identifier: Apache-2.0
"""Standalone scientific exports, generated from the same typed result objects."""

from pathlib import Path
import json, html, csv, io
import numpy as np
from dynamics.experiments import clean

CSS = """html{color-scheme:light dark}body{font:16px/1.6 system-ui,sans-serif;max-width:1100px;margin:3rem auto;padding:0 20px;background:#f6f6f3;color:#1d2528}h1{font-size:clamp(2rem,5vw,3.5rem);line-height:1.1}h2{margin-top:2.5rem}a{color:#215e79}table{border-collapse:collapse;width:100%;font-size:.9rem}th,td{padding:10px;border-bottom:1px solid #c3c9c9;text-align:left;vertical-align:top}.table{overflow:auto}code,pre{overflow-wrap:anywhere;word-break:break-word;white-space:pre-wrap}img{max-width:100%;height:auto}.tag{font:12px monospace;letter-spacing:.1em}.note{border-left:3px solid #658a91;padding:1rem;background:#eaf0f0}summary{cursor:pointer}footer{margin-top:3rem;border-top:1px solid #aaa;padding-top:1rem}@media(prefers-color-scheme:dark){body{background:#101416;color:#e2e9eb}a{color:#94cfdf}.note{background:#1c292d}td,th{border-color:#39464b}}"""
METHODS = {
    "OTE-001": """Full official BPI2019 XES is parsed using defusedxml streaming, with original MD5/size checked against4TU metadata. Required fields are validated; UTC timestamps are integer microseconds. Exact full-attribute duplicate candidates remain in the original analysis because no unique event identifier establishes erroneous duplication. Stable timestamp/source order constructs traces, category-specific DFG and variants. Durations are elapsed first-to-last observations, not processing/waiting time. A strict2018sensitivity excludes entire out-of-window cases separately. Repeated activities and Change/Cancel prefixes are descriptive proxies, not proven waste. No monetary costs or individual productivity are inferred.""",
    "OTE-002": """Preregistered core projection excludes SRM administrative activities only from the twin. Eligible core cases begin Create Purchase Order Item, end Clear Invoice, remain entirely in one2018quarter, and exclude Consignment/unknown categories. This is an observed endpoint proxy, not proof of closure. Q1+Q2calibration, Q3validation,Q4test; documents crossing sets excluded. SHA-selected heldoutsamples are capped3000cases per set. Pooled trace bootstrap, category trace bootstrap and category semi-Markov elapsed-time models use identical observed arrival schedules and fixed92day windows.20seeded replicas per model/set. Seven unweighted validation errors select one model before independent testing. All model test metrics are reported.90percent marginal duration intervals derive only from calibration; actual heldoutcoverage is measured.95percent Student-t intervals quantify independent MC mean uncertainty conditional on the model;499whole-document bootstrap repetitions quantify observed sample uncertainty separately. Experimental acceptance tolerances and minimum100cases are preregistered engineering bounds, not official standards. Quarter/end-point selection and retrospective arrival conditioning preclude prospective prediction claims.""",
    "OTE-003": """Category semi-Markov routes calibrated on historical elapsed gaps are combined with a separate hypothetical SimPy FIFO resource layer. Target activity is selected using calibration mean incoming elapsed delay among activities with100transitions. Default5percent of each target incoming gap is assumed to be service;95percent remains exogenous delay. Abstract capacity is designed from specified sample workload and target utilization0.7, not identified real staffing.750SHA-selected heldoutarrivals,50replicas per scenario,seed20261106. Seven scenarios: base,demand+30percent,capacity-25percent,assumed service-20percent,Change/Cancel transition weight-20percent,nonpreemptive temporary capacity reduction days30–45,and combined. Per-case/replicate/component random streams preserve original-agent draws; route interventions alter later correspondence. Nine service-share/utilization sensitivity cells use150cases and5replicas each. All outcomes are HYPOTHETICAL SCENARIOS / NOT VALIDATED. Paired MC95percent confidence intervals represent conditional model differences, not causal organizational improvements. No economic savings are calculated.""",
}


def csv_rows(r):
    exp = r["experiment"]
    if exp == "OTE-001":
        return r["category_performance"]
    if exp == "OTE-002":
        return [
            {"split": split, "model": k, "metric": metric, **v}
            for split, e in r["evaluations"].items()
            for k, m in e["models"].items()
            for metric, v in m["metrics"].items()
        ]
    return [
        {"scenario": s, "metric": k, **v}
        for s, d in r["scenarios"].items()
        for k, v in d["metrics"].items()
    ]


def table(rows):
    if not rows:
        return "<p>Insufficient evidence for this table.</p>"
    columns = list(rows[0])
    esc = lambda v: html.escape(
        json.dumps(clean(v), ensure_ascii=False)
        if isinstance(v, (dict, list))
        else f"{v:.6g}" if isinstance(v, float) else str(v)
    )
    return (
        '<div class="table"><table><thead><tr>'
        + "".join("<th>" + esc(c) + "</th>" for c in columns)
        + "</tr></thead><tbody>"
        + "".join(
            "<tr>"
            + "".join("<td>" + esc(row.get(c, "")) + "</td>" for c in columns)
            + "</tr>"
            for row in rows
        )
        + "</tbody></table></div>"
    )


def figures(r, folder):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "figure.facecolor": "#f6f6f3",
            "axes.facecolor": "#f6f6f3",
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    exp = r["experiment"]
    fig, ax = plt.subplots(figsize=(10, 5), layout="constrained")
    if exp == "OTE-001":
        rows = r["category_performance"]
        names = [
            x["category"]
            .replace("3-way match, invoice ", "3-way\n")
            .replace(" ", "\u00a0")
            for x in rows
        ]
        x = np.arange(len(rows))
        for i, (k, label) in enumerate(
            [
                ("elapsed_median_day", "Median"),
                ("elapsed_p90_day", "P90"),
                ("elapsed_p95_day", "P95"),
            ]
        ):
            ax.bar(x + (i - 1) * 0.24, [v[k] for v in rows], 0.24, label=label)
        ax.set_xticks(x, names)
        ax.set_ylabel("Observed elapsed days")
        ax.legend()
        ax.set_title(
            "OTE-001 · Elapsed durations by process category · all source cases"
        )
    elif exp == "OTE-002":
        rows = r["evaluations"]["test"]["models"]
        names = list(rows)
        x = np.arange(len(names))
        keys = ["mean_relative_error", "median_relative_error", "p90_relative_error"]
        for i, k in enumerate(keys):
            ax.bar(
                x + (i - 1) * 0.24,
                [rows[n]["metrics"][k]["mean"] for n in names],
                0.24,
                label=k.replace("_relative_error", ""),
            )
        ax.set_xticks(x, [n.replace("_", "\n") for n in names])
        ax.set_ylabel("Relative absolute error · heldout test cohort")
        ax.legend()
        ax.set_title("OTE-002 · All three models · no test tuning")
    else:
        rows = r["scenarios"]
        names = list(rows)
        means = [v["metrics"]["mean_cycle_day"]["mean"] for v in rows.values()]
        errs = [
            v["metrics"]["mean_cycle_day"]["mean_CI95"][1]
            - v["metrics"]["mean_cycle_day"]["mean"]
            for v in rows.values()
        ]
        ax.barh(np.arange(len(names)), means, xerr=errs, color="#487a88")
        ax.set_yticks(np.arange(len(names)), [n.replace("_", " ") for n in names])
        ax.set_xlabel("Simulated mean elapsed days · MC mean95%CI")
        ax.set_title(
            "OTE-003 · Hypothetical capacity/service assumptions · not validated"
        )
    name = exp + "_FIGURE.png"
    fig.savefig(folder / name, dpi=150)
    plt.close(fig)
    return [name]


def exports(r, manifest, folder, replays=None):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    exp = r["experiment"]

    def write(name, value):
        p = folder / name
        p.write_text(value, encoding="utf-8")
        return p

    write(
        exp + "_RESULTS.json",
        json.dumps(clean(r), indent=2, ensure_ascii=True, allow_nan=False) + "\n",
    )
    write(
        exp + "_MANIFEST.json",
        json.dumps(clean(manifest), indent=2, ensure_ascii=True, allow_nan=False)
        + "\n",
    )
    rows = csv_rows(r)
    s = io.StringIO()
    w = csv.DictWriter(s, fieldnames=list(rows[0]) if rows else ["status"])
    w.writeheader()
    w.writerows(
        {
            k: json.dumps(clean(v)) if isinstance(v, (dict, list)) else v
            for k, v in row.items()
        }
        for row in rows
    )
    write(exp + "_METRICS.csv", s.getvalue())
    write(
        exp + "_METHODOLOGY.md",
        "# "
        + exp
        + " Methodology\n\n"
        + METHODS[exp]
        + "\n\n"
        + "\n".join("- " + x for x in r.get("limits", []))
        + "\n",
    )
    write(
        exp + "_REPRODUCIBILITY.md",
        f'# {exp} Reproducibility\n\n`python -m operations_twin.cli reproduce {exp} --data .local/operations-twin-data`\n\nThe first run uses the pinned official source hashes. Offline replay requires the acquired original XES and verified cache/partitions. Never silently replace a vintage. Numerical results are recomputed without an LLM. Commit/source hashes, parameters, seed and dependency versions are in the manifest. Result hash: `{r["results_sha256"]}`. Timing, environment and job identifiers are excluded from the scientific fingerprint.\n',
    )
    write("report.css", CSS)
    images = figures(r, folder)
    for name, value in (replays or {}).items():
        write(
            exp + "_REPLAY_" + name + ".json",
            json.dumps(clean(value), separators=(",", ":"), allow_nan=False) + "\n",
        )
    title = html.escape(exp + " · " + r["title"])
    parts = [
        f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="report.css"><title>{title}</title><main><p class="tag">DYNAMICS LAB · OPERATIONS TWIN · SCIENTIFIC REPORT</p><h1>{title}</h1><p class="note">{html.escape(r["kind"])}. Observed elapsed time, simulated service assumptions and business outcomes are distinct. This report does not assess individual employees or calculate monetary savings.</p><h2>Objective and dataset</h2><p>BPI Challenge2019 · public Purchase-to-Pay log · Boudewijn van Dongen · 4TU.ResearchData · version1 · CC BY4.0. Original input:728,558,522bytes, checked against official MD5.</p><p><a href="https://doi.org/10.4121/uuid:d06aff4b-79f0-45e6-8ec8-e19730c248f1">Official dataset and attribution</a></p><h2>Method and parameters</h2><p>{html.escape(METHODS[exp])}</p>'
    ]
    if exp == "OTE-001":
        parts += [
            "<h2>Structure and data quality</h2>",
            table([r["counts"]]),
            table([r["data_quality"]]),
            "<h2>Category performance · observed</h2>",
            table(rows),
            "<h2>Long elapsed transitions · investigation candidates</h2>",
            table(r["long_elapsed_transitions"]),
            "<h2>Model cohort and exclusions</h2>",
            table(r["model_cohort"]["exclusion_rules"]),
            table(r["model_cohort"]["groups"]),
        ]
    elif exp == "OTE-002":
        parts += [
            "<h2>Independent test and validation</h2>",
            f'<p>Selected only on validation: <strong>{html.escape(r["selected_on_validation_only"])}</strong>. {html.escape(r["acceptance_scope"])}</p>',
        ]
        for split, e in r["evaluations"].items():
            parts += [
                f'<h3>{split} · {e["cases"]}cases · {e["documents"]}documents</h3>',
                table(
                    [
                        {
                            "model": k,
                            **{key: v["mean"] for key, v in m["metrics"].items()},
                        }
                        for k, m in e["models"].items()
                    ]
                ),
            ]
        parts += [
            "<h2>Per-category acceptance · independent test</h2>",
            table(
                [
                    {"model": k, **v}
                    for k, m in r["evaluations"]["test"]["models"].items()
                    for v in m["by_category"]
                ]
            ),
            "<h2>Nominal90%duration coverage · not implied by mean fit</h2>",
            table(
                [
                    {
                        "category": c["category"],
                        "cases": c["observed_cases"],
                        "model": k,
                        **v,
                    }
                    for c in r["evaluations"]["test"]["by_category"]
                    for k, v in c["duration_prediction_intervals"].items()
                ]
            ),
        ]
    else:
        parts += [
            "<h2>Hypothetical scenarios · paired conditional Monte Carlo</h2>",
            table(
                [
                    {"scenario": s, **{k: v["mean"] for k, v in d["metrics"].items()}}
                    for s, d in r["scenarios"].items()
                ]
            ),
            "<h2>Sensitivity to unidentifiable service/capacity assumptions</h2>",
            table(r["sensitivity"]),
        ]
    parts += ["<h2>Calculated figures</h2>"] + [
        f'<figure><img src="{x}" alt="{exp} computed research figure"><figcaption>Generated from the result JSON. No manually inserted scientific values.</figcaption></figure>'
        for x in images
    ]
    parts += [
        "<h2>Uncertainty and limitations</h2><ul>"
        + "".join("<li>" + html.escape(v) + "</li>" for v in r.get("limits", []))
        + "</ul>",
        "<h2>Evidence and reproducibility</h2><p>Acquisition: "
        + html.escape(str(manifest.get("acquired_at", "")))
        + " · Execution: "
        + html.escape(str(manifest.get("executed_at", "")))
        + ".</p><p>Scientific fingerprint <code>"
        + r["results_sha256"]
        + '</code></p><p><a href="'
        + exp
        + '_RESULTS.json">Results JSON</a> · <a href="'
        + exp
        + '_MANIFEST.json">Manifest</a></p><details><summary>Complete computed result</summary><pre>'
        + html.escape(json.dumps(clean(r), indent=2, ensure_ascii=False))
        + "</pre></details><footer>Original software Apache2.0. Source data and attributed derived dataset material CC BY4.0. Hypotheses are not measurements; no LLM is required.</footer></main></html>",
    ]
    write(exp + "_REPORT.html", "".join(parts))
    return [p.name for p in folder.iterdir() if p.is_file()]

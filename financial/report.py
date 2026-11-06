# SPDX-License-Identifier: Apache-2.0
"""Original deterministic research findings, escaped standalone reports."""

import csv, io, json, html, math

NYFED_NOTICE = "SOFR data and derived research results are subject to the Terms of Use at https://www.newyorkfed.org/privacy/termsofuse. The New York Fed is not responsible for publication of these results by Mattoccia Labs, does not endorse this republication, and has no liability for your use. Mattoccia Labs is not affiliated with the New York Fed. The New York Fed does not sanction, endorse, or recommend products or services offered by Mattoccia Labs. SOFR data are calculated using data provided under a license granted to the New York Fed by DTCC Solutions LLC; those parties have no liability for this material."


def findings_csv(r):
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(
        [
            "finding_id",
            "kind",
            "date",
            "indicator",
            "value",
            "unit",
            "method",
            "source_ids",
        ]
    )
    for col, stat in r["yield_curve"].items():
        for ep in stat["episodes"]:
            w.writerow(
                [
                    "FSIE-001-F1",
                    "inversion_episode",
                    ep["start"],
                    col,
                    ep["sessions"],
                    "observed_sessions",
                    "spread<0; end="
                    + ep["end"]
                    + ";right_censored="
                    + str(ep["right_censored"]),
                    "treasury",
                ]
            )
    for c in r["contemporaneous_correlations"]:
        w.writerow(
            [
                "FSIE-001-F2",
                c["transformation"],
                "",
                c["spread"] + " vs " + c["index"],
                c["pearson"],
                "Pearson_coefficient",
                "pairedN=" + str(c["n_pairs"]) + ";movingblock13weeks95CI",
                "treasury;chicago",
            ]
        )
    for a in r["anomalies"]:
        w.writerow(
            [
                "FSIE-001-F3",
                "extreme_change",
                a["date"],
                a["indicator"],
                a["change"],
                a["unit"],
                "past-only robustz=" + str(a["robust_z"]),
                ";".join(a["source_ids"]),
            ]
        )
    return out.getvalue()


def methodology(r):
    return (
        "# FSIE-001 — quantitative methodology\n\nRetrospective latest-acquired-vintage research, not a predictive trading backtest.\n\nConfiguration:\n```json\n"
        + json.dumps(r["configuration"], indent=2)
        + "\n```\n\n"
        + """Observation dates and current snapshot acquisition times do not prove original historical publication availability. Unknown publication timestamps remain null. NFCI/ANFCI can revise their histories. Never forward-fill a Friday index into earlier trading dates. Weekly alignment selects the last Treasury session in the same Monday-Friday week, preserving original dates and missingness. No interpolation.\n\nSpread basis points =100*(10Y yield - short yield), input rates in percentage points. Volatility is ddof1 standard deviation of changes in yield/spread basis points per observed session/week, not bond-price volatility or annualized investment risk.\n\nStrict negative spread defines inversion. Episodes count observed inverted sessions and inclusive calendar span separately. Missing required yields and sample end censor episodes; unknown intervals do not prove termination.\n\nPearson/Spearman are descriptive; no IID correlation p-values. Joint moving-block bootstrap:13 weeks, 999 replicates, seed 20261106, 95% percentile intervals. Calendar alignment and paired missingness retained. These intervals require temporal-dependence/stability assumptions.\n\nLags:-26,-13,-4,0,4,13,26weeks. corr(delta_spread[t],delta_index[t+k]):positive k means spread observation leads index reference week, not publication availability or causality. All 28 predeclared first-difference tests use OLS/HAC(Newey-West, 13 lags) and Holm correction across the full 28-test family, including unestimable tests as conservative p=1. Rolling windows 26/52/104 weeks and all predefined historical subperiods are reported. No favorable-window selection.\n\nAnomalies:past-only 104-week median/MAD, minimum 52 prior observations,scale 1.4826, |z| >= 4. ZeroMAD is not determinable, never an infinite surprise. Volatility exceedances use only preceding104weekly estimates,p95,min52. Two-sided CUSUM/Page-Hinkley-style accumulation of standardized changes has drift 0.5, threshold 8 and resets on an event; these are heuristic candidates, not formal break proofs. NFCI>0 and>1 are declared relative-condition thresholds; persistence4weeks is an overlapping-window count.\n\nNo-follow-through proxy:inversion onset not followed by index threshold0/1/2 within 13/26/52 weeks, excluding incomplete follow-up. These are retrospective threshold sensitivity counts, not true/false crisis forecasts. NFCI already combines financial-market information; sources and indicators are not independent.\n\nOriginal-code Apache 2.0 is separate from source-data terms. Raw institutional archives/full series remain local. Public artifacts contain original computed findings/aggregates and source references. No trading, broker integration, money management, personalized advice or return promise.\n"""
    )


def reproduction(r):
    return (
        """# Reproducing FSIE-001\n\n1. Extract the original Research Engines source release.\n2. On the qualified macOS Apple Silicon / Python 3.12 environment, run `python3.12 scripts/setup_financial.py`.\n3. Run `.venv-fsie/bin/python -m financial.cli run --data .local/financial --start """
        + r["configuration"]["start"]
        + " --end "
        + r["configuration"]["end"]
        + """`. Acquisition is explicit and subject to official source terms.\n4. Preserve the full immutable response cache and manifest. Use `.venv-fsie/bin/python -m financial.cli verify --data .local/financial --job JOB_ID` for network-free replay from those original bytes.\n5. Compare the analysis SHA-256, source SHA-256, parser/method/software versions and configuration. Sources, especially NFCI, revise; a fresh acquisition is a new study and need not reproduce an older vintage. A changed source must not be presented as the old study.\n\nThe distributed source does not indiscriminately redistribute institutional raw time-series archives. A new user may reproduce the algorithm and current official acquisition; an exact historical numeric replay requires the manifest-matching source snapshot. The original complete frozen cache was replayed locally before publication. No artificial source values are supplied to make a hash match.\n\nDashboard: `.venv-fsie/bin/python -m financial.cli serve`, then http://127.0.0.1:4204/. No cloud or persistent service. Windows/Linux unqualified. The complete regression suite additionally needs the separately installed ESAE C++ analyzers; FSIE itself does not.\n"""
    )


def line_svg(points, key, label):
    e = lambda x: html.escape(str(x), quote=True)
    valid = [(i, p[key]) for i, p in enumerate(points) if p.get(key) is not None]
    if not valid:
        return "<p>No comparable observations.</p>"
    ys = [v for i, v in valid]
    lo = min(ys)
    hi = max(ys)
    span = hi - lo or 1
    path = ""
    previous = None
    for i, p in enumerate(points):
        v = p.get(key)
        if v is None:
            previous = None
            continue
        x = 40 + 920 * i / max(1, len(points) - 1)
        y = 270 - 230 * (v - lo) / span
        path += ("M" if previous is None else "L") + f"{x:.2f},{y:.2f}"
        previous = i
    return (
        '<svg class="plot" viewBox="0 0 1000 320" role="img" aria-label="'
        + e(label)
        + '"><path d="M40 20V270H970" class="axis"/><path d="'
        + path
        + '" class="series"/><text x="5" y="20">'
        + e(round(hi, 2))
        + '</text><text x="5" y="285">'
        + e(round(lo, 2))
        + '</text><text x="40" y="310">'
        + e(points[0]["date"])
        + '</text><text x="855" y="310">'
        + e(points[-1]["date"])
        + "</text></svg>"
    )


def html_report(r):
    e = lambda x: html.escape(str(x), quote=True)

    def table(heads, rows):
        return (
            '<div class="table"><table><thead><tr>'
            + "".join("<th>" + e(x) + "</th>" for x in heads)
            + "</tr></thead><tbody>"
            + "".join(
                "<tr>" + "".join("<td>" + e(x) + "</td>" for x in row) + "</tr>"
                for row in rows
            )
            + "</tbody></table></div>"
        )

    coverage = r["coverage"]
    yieldrows = [
        [
            col,
            s["valid_sessions"],
            s["inverted_sessions"],
            len(s["episodes"]),
            s["distribution_bp"]["minimum"],
            s["distribution_bp"]["maximum"],
        ]
        for col, s in r["yield_curve"].items()
    ]
    correlations = [
        [
            c["spread"],
            c["index"],
            c["transformation"],
            c["n_pairs"],
            c["pearson"],
            c["spearman"],
            c["bootstrap_ci95"].get("lower"),
            c["bootstrap_ci95"].get("upper"),
        ]
        for c in r["contemporaneous_correlations"]
    ]
    lags = [
        [
            c["spread"],
            c["index"],
            c["lag_weeks"],
            c["n_pairs"],
            c["pearson"],
            c["hac_p"],
            c["holm_p"],
        ]
        for c in r["lag_tests"]
    ]
    anomalyrows = [
        [a["date"], a["indicator"], a["change"], a["unit"], a["robust_z"]]
        for a in r["anomalies"][:25]
    ]
    sources = "".join(
        "<li>"
        + e(s["organization"])
        + ' · <a href="'
        + e(s["url"])
        + '">official source</a> · SHA256<code>'
        + e(s["sha256"])
        + "</code> · acquired "
        + e(s["acquired_at"])
        + "</li>"
        for s in r.get("sources", [])
    )
    charts = "".join(
        "<h3>"
        + e(col)
        + " / basis points</h3>"
        + line_svg(r["derived_spread_history"], col, col)
        for col in r["yield_curve"]
    )
    subperiod = table(
        ["Spread", "Index", "From", "To", "N", "Pearson", "Spearman"],
        [
            [
                x["spread"],
                x["index"],
                x["start"],
                x["end"],
                x["n_pairs"],
                x["pearson"],
                x["spearman"],
            ]
            for x in r["subperiod_correlations"]
        ],
    )
    main = (
        '<p class="notice">Retrospective latest-vintage research. No predictive backtest, trading signal, investment advice or assured systemic-crisis detection.</p><p>'
        + e(r["study_period"])
        + '</p><div class="stats">'
        + "".join(
            "<div><b>" + e(value) + "</b><span>" + e(label) + "</span></div>"
            for value, label in [
                (
                    coverage["source_observations_acquired"],
                    "Source observations parsed",
                ),
                (coverage["complete_primary_weeks"], "Complete primary weeks"),
                (len(r["anomalies"]), "Past-normalized change flags"),
                (
                    r["lag_test_summary"]["holm_significant_05"],
                    "HAC/Holm associations /28",
                ),
            ]
        )
        + "</div>"
    )
    main += (
        "<h2>Principal measured results</h2><p>"
        + e(coverage["complete_primary_weeks"])
        + " comparable weeks, "
        + e(r["study_period"]["weekly_start"])
        + " to "
        + e(r["study_period"]["weekly_end"])
        + ". The 10Y–2Y curve was inverted in "
        + e(r["yield_curve"]["spread_10y2y_bp"]["inverted_sessions"])
        + " of "
        + e(r["yield_curve"]["spread_10y2y_bp"]["valid_sessions"])
        + " observed sessions. Of the 28 predeclared lag comparisons, "
        + e(r["lag_test_summary"]["holm_significant_05"])
        + " pass the HAC/Holm threshold. A null result is retained as an observed outcome; it is not proof that every possible financial relationship is absent.</p>"
    )
    body = (
        main
        + "<h2>Objective, sources and versions</h2><p>Study associations between the U.S. Treasury yield curve and institutional financial-condition indices, with separately documented SOFR money-market context. Statistical relationships are not causal or predictive proofs.</p><ul>"
        + sources
        + "</ul><pre>"
        + e(
            json.dumps(
                {
                    "period": r["study_period"],
                    "configuration": r["configuration"],
                    "coverage": coverage,
                    "analysis_sha256": r["analysis_sha256"],
                },
                indent=2,
            )
        )
        + "</pre><h2>1 / Yield-curve regimes</h2>"
        + table(
            [
                "Spread",
                "Known sessions",
                "Inverted sessions",
                "Episodes",
                "Minimum /bp",
                "Maximum /bp",
            ],
            yieldrows,
        )
        + charts
        + "<h3>Inversion episodes and censoring</h3>"
        + table(
            [
                "Spread",
                "Start",
                "End",
                "Inverted sessions",
                "Calendar span",
                "Right-censored",
            ],
            [
                [
                    col,
                    x["start"],
                    x["end"],
                    x["sessions"],
                    x["calendar_days_inclusive"],
                    x["right_censored"],
                ]
                for col, v in r["yield_curve"].items()
                for x in v["episodes"]
            ],
        )
        + "<h2>2 / Financial-condition relationships</h2><p>All contemporaneous comparisons and predeclared lag tests are included. Positive lag k compares spread-change[t] with index-change[t+k]. Confidence intervals use joint 13-week moving blocks, not independent observations. HAC regression and Holm correction apply to the full 28 first-difference test family.</p>"
        + table(
            [
                "Spread",
                "Index",
                "Transform",
                "N pairs",
                "Pearson",
                "Spearman",
                "Block95CI low",
                "Block95CI high",
            ],
            correlations,
        )
        + table(
            ["Spread", "Index", "Lag weeks", "N pairs", "Pearson", "HAC p", "Holm p"],
            lags,
        )
        + "<pre>"
        + e(json.dumps(r["lag_test_summary"], indent=2))
        + "</pre><h3>All predefined subperiods</h3>"
        + subperiod
        + "<h3>Rolling-correlation sensitivity</h3>"
        + table(
            [
                "Spread",
                "Index",
                "Transform",
                "Window weeks",
                "Valid estimates",
                "Minimum",
                "Maximum",
            ],
            [
                [
                    x["spread"],
                    x["index"],
                    x["transformation"],
                    x["window_weeks"],
                    x["summary"]["n"],
                    x["summary"]["minimum"],
                    x["summary"]["maximum"],
                ]
                for x in r["rolling_correlations"]
            ],
        )
        + "<h2>3 / Statistical anomalies</h2><p>First 25 flags ranked by absolute past-normalized robustz. All flags and methods are in JSON/CSV. Threshold uses only preceding 104 weeks with minimum 52 prior observations. Outliers are research findings, not assumed acquisition errors or imminent-crisis warnings.</p>"
        + table(["Date", "Indicator", "Change", "Unit", "Past robustz"], anomalyrows)
        + "<h3>Volatility and change candidates</h3><pre>"
        + e(
            json.dumps(
                {
                    "daily_yield_change_volatility": r["daily_yield_change_volatility"],
                    "weekly_spread_change_volatility": r[
                        "weekly_spread_change_volatility"
                    ],
                    "change_point_candidates": r["change_point_candidates"],
                },
                indent=2,
            )
        )
        + "</pre><h3>Systemic-risk descriptors and follow-through sensitivity</h3><pre>"
        + e(
            json.dumps(
                {
                    k: v
                    for k, v in r["systemic_stress"].items()
                    if k != "annual_aggregates"
                },
                indent=2,
            )
        )
        + "</pre><h3>Money-market supplement</h3><pre>"
        + e(json.dumps(r["money_market_supplement"], indent=2))
        + "</pre><h2>Methods, uncertainty and limits</h2><p>Full method and reproducibility instructions accompany this report. Unknown historical publication times remain null; acquisition time is not original release time. NFCI/ANFCI can revise and already include market information. No source independence is assumed.</p><ul>"
        + "".join("<li>" + e(x) + "</li>" for x in r["limitations"])
        + "</ul><h2>Source attribution and license</h2><p>Original FSIE software Apache 2.0. Original calculations by Mattoccia Labs using official institutional data; source data retain upstream terms and are not relicensed as Apache. Full raw response archives remain local. Chicago Fed indices are source-attributed research inputs, not endorsements or copied institutional publications.</p><p>"
        + e(NYFED_NOTICE)
        + "</p><h2>Reproducibility</h2><p>SourceSHA256, parser/method/configuration/software versions are in FSIE-001_MANIFEST.json. Replay the matching frozen sources with financial.cli verify. Fresh current data may differ due to revisions; do not assert identical vintage without matching hashes.</p>"
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'"><title>FSIE-001 · Financial Systems Intelligence</title><style>'
        + """body{font:16px/1.8 system-ui;background:#f5f3ed;color:#172229;max-width:1180px;margin:auto;padding:45px 24px}h1{font-size:clamp(35px,6vw,70px);font-weight:500;line-height:1.1;letter-spacing:-.05em}h2{font-size:30px;font-weight:500;margin-top:48px;line-height:1.2}a{color:#315f6e}code{overflow-wrap:anywhere}.table{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:12px}th,td{padding:12px;text-align:left;border-bottom:1px solid #ccd3d0;vertical-align:top}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#fffdf8;padding:20px;border:1px solid #ccd3d0;border-radius:12px;font-size:11px}.notice{border-left:3px solid #8a734f;padding-left:20px}.stats{display:grid;grid-template-columns:repeat(4,1fr);border:1px solid #cbd3ce;border-radius:15px}.stats div{padding:20px}.stats b{display:block;font-size:30px}.stats span{font-size:12px}.plot{width:100%;height:auto;background:#fffdf8;border:1px solid #d0d8d3;border-radius:12px}.plot .series{fill:none;stroke:#3c6979;stroke-width:1.5}.plot .axis{fill:none;stroke:#aab9b4}.plot text{font:11px monospace;fill:#536460}li{overflow-wrap:anywhere;margin-bottom:10px}@media(max-width:700px){body{padding:25px 18px}.stats{grid-template-columns:1fr 1fr}.stats div{padding:14px}.stats b{font-size:25px}}"""
        + "</style></head><body><p>MATTOCCIA LABS / RESEARCH ENGINES / ENGINE04 — MARKETS</p><h1>Treasury Yield Curve<br>& Financial Stress.</h1>"
        + body
        + "</body></html>"
    )

# SPDX-License-Identifier: Apache-2.0
"""Predeclared retrospective finance statistics; no trading or forecasts."""

from dataclasses import dataclass, asdict, field
import datetime, math, json, hashlib
import numpy as np, pandas as pd
from scipy.stats import pearsonr, spearmanr
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests

METHOD_VERSION = "fsie-001-1.0"


@dataclass(frozen=True)
class StudyConfig:
    start: str = "2000-01-01"
    end: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
        .date()
        .isoformat()
    )
    bootstrap_replicates: int = 999
    block_weeks: int = 13
    seed: int = 20261106
    anomaly_window: int = 104
    anomaly_min_history: int = 52
    anomaly_z: float = 4.0

    def validate(self):
        a = datetime.date.fromisoformat(self.start)
        b = datetime.date.fromisoformat(self.end)
        if (
            not datetime.date(2000, 1, 1)
            <= a
            < b
            <= datetime.datetime.now(datetime.timezone.utc).date()
            or b.year - a.year > 50
        ):
            raise ValueError("Historical study dates required, maximum50years")
        if (
            isinstance(self.bootstrap_replicates, bool)
            or not 99 <= self.bootstrap_replicates <= 1999
            or not 4 <= self.block_weeks <= 52
            or not 52 <= self.anomaly_window <= 260
            or not 26 <= self.anomaly_min_history <= self.anomaly_window
            or not 2 <= self.anomaly_z <= 10
        ):
            raise ValueError("Statistical parameter bounds exceeded")
        return self


def finite(value):
    return None if value is None or not np.isfinite(value) else round(float(value), 12)


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, (pd.Timestamp, datetime.datetime, datetime.date)):
        return str(value)[:10]
    if isinstance(value, (float, np.floating)):
        return finite(value)
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    return value


def describe(series):
    x = pd.Series(series).dropna().astype(float)
    if not len(x):
        return {
            "n": 0,
            "minimum": None,
            "maximum": None,
            "mean": None,
            "median": None,
            "std_sample": None,
        }
    return clean(
        {
            "n": len(x),
            "minimum": x.min(),
            "maximum": x.max(),
            "mean": x.mean(),
            "median": x.median(),
            "std_sample": x.std(ddof=1),
            "p05": x.quantile(0.05),
            "p95": x.quantile(0.95),
        }
    )


def correlate(x, y, min_pairs=20):
    frame = (
        pd.concat([pd.Series(x).rename("x"), pd.Series(y).rename("y")], axis=1)
        .replace([np.inf, -np.inf], np.nan)
        .dropna()
    )
    n = len(frame)
    if n < min_pairs or frame.x.nunique() < 2 or frame.y.nunique() < 2:
        return {
            "n_pairs": n,
            "status": "not_determinable",
            "pearson": None,
            "spearman": None,
        }
    return {
        "n_pairs": n,
        "status": "computed",
        "pearson": finite(pearsonr(frame.x, frame.y).statistic),
        "spearman": finite(spearmanr(frame.x, frame.y).statistic),
        "inference": "Descriptive; no IID p-value or causality claim",
    }


def block_interval(x, y, config):
    values = np.column_stack([np.asarray(x, float), np.asarray(y, float)])
    n = len(values)
    block = config.block_weeks
    if n < max(52, 2 * block):
        return {
            "status": "not_determinable",
            "method": "joint moving-block bootstrap",
            "n_calendar_weeks": n,
        }
    rng = np.random.default_rng(config.seed)
    rhos = []
    for _ in range(config.bootstrap_replicates):
        starts = rng.integers(0, n - block + 1, size=math.ceil(n / block))
        idx = (starts[:, None] + np.arange(block)).ravel()[:n]
        pair = values[idx]
        pair = pair[np.isfinite(pair).all(axis=1)]
        if len(pair) >= 20 and np.std(pair[:, 0]) > 0 and np.std(pair[:, 1]) > 0:
            rhos.append(float(np.corrcoef(pair.T)[0, 1]))
    if len(rhos) < 0.95 * config.bootstrap_replicates:
        return {"status": "not_determinable", "valid_replicates": len(rhos)}
    return clean(
        {
            "status": "computed",
            "method": "Joint overlapping moving blocks; percentile95CI; paired missingness retained; descriptive under temporal dependence",
            "lower": np.quantile(rhos, 0.025),
            "upper": np.quantile(rhos, 0.975),
            "block_weeks": block,
            "replicates": config.bootstrap_replicates,
            "valid_replicates": len(rhos),
            "seed": config.seed,
            "not_realtime_predictive": True,
        }
    )


def inversion_episodes(series):
    records = []
    active = None
    previous = None

    def finish(censored, reason):
        nonlocal active
        if active:
            end = active.pop("last_date")
            active.update(
                end=end,
                calendar_days_inclusive=(
                    pd.Timestamp(end) - pd.Timestamp(active["start"])
                ).days
                + 1,
                right_censored=censored,
                end_reason=reason,
            )
            records.append(active)
            active = None

    for date, value in series.items():
        if pd.isna(value):
            finish(True, "missing_required_yield")
            previous = None
            continue
        if value < 0:
            if active is None:
                active = {
                    "start": date.date().isoformat(),
                    "last_date": date.date().isoformat(),
                    "sessions": 0,
                    "minimum_bp": float(value),
                    "left_censored": previous is None,
                }
            active["last_date"] = date.date().isoformat()
            active["sessions"] += 1
            active["minimum_bp"] = min(active["minimum_bp"], float(value))
        else:
            finish(False, "observed_nonnegative_spread")
        previous = date
    finish(True, "end_of_sample")
    return clean(records)


def aligned_frames(frame, config):
    frame = frame.copy()
    frame["observation_date"] = pd.to_datetime(frame["observation_date"])
    wide = frame.pivot(
        index="observation_date", columns="series_id", values="value"
    ).sort_index()
    required = ["UST_2Y", "UST_3M", "UST_5Y", "UST_10Y", "UST_30Y", "NFCI", "ANFCI"]
    if not set(required) <= set(wide):
        raise ValueError("Mandatory Treasury/NFCI series unavailable")
    treasury = (
        wide[[c for c in wide if c.startswith("UST_")]]
        .loc[config.start : config.end]
        .dropna(how="all")
    )
    treasury["spread_10y2y_bp"] = (treasury.UST_10Y - treasury.UST_2Y) * 100
    treasury["spread_10y3m_bp"] = (treasury.UST_10Y - treasury.UST_3M) * 100
    # No interpolation or calendar-day filling. Resampling selects existing sessions.
    selected = treasury.index.to_series().resample("W-FRI").max()
    wt = treasury.reindex(selected.to_numpy())
    wt.index = selected.index
    wt["treasury_observation_date"] = selected
    valid_date = (wt.index.to_series() - selected).dt.days.between(0, 4)
    wt.loc[~valid_date, wt.columns != "treasury_observation_date"] = np.nan
    indices = (
        wide[
            [
                c
                for c in [
                    "NFCI",
                    "ANFCI",
                    "Risk",
                    "Credit",
                    "Leverage",
                    "Nonfinancial_Leverage",
                ]
                if c in wide
            ]
        ]
        .dropna(how="all")
        .loc[config.start : config.end]
    )
    if any(indices.index.day_of_week != 4):
        raise ValueError("Financial condition dates must be Friday reference weeks")
    joined = wt.join(indices, how="inner")
    good = joined[["NFCI", "spread_10y2y_bp", "spread_10y3m_bp"]].dropna()
    if len(good) < 104:
        raise ValueError("At least104comparable weeks required for FSIE-001")
    last = good.index.max()
    first = good.index.min()
    weeks = pd.date_range(first, last, freq="W-FRI")
    weekly = wt.reindex(weeks).join(indices)
    daily = treasury.loc[config.start : last]
    if "SOFR" in wide:
        weekly["SOFR"] = wide.SOFR.dropna().resample("W-FRI").last().reindex(weeks)
    return wide, daily, weekly


def trailing_robust_z(series, window=104, minimum=52):
    values = series.to_numpy(float)
    out = np.full(len(values), np.nan)
    for i in range(len(values)):
        past = values[max(0, i - window) : i]
        past = past[np.isfinite(past)]
        if len(past) < minimum or not np.isfinite(values[i]):
            continue
        median = np.median(past)
        mad = np.median(np.abs(past - median))
        if mad > 1e-12:
            out[i] = (values[i] - median) / (1.4826 * mad)
    return pd.Series(out, index=series.index)


def change_candidates(z, drift=0.5, threshold=8):
    plus = minus = 0.0
    out = []
    for date, value in z.items():
        if pd.isna(value):
            plus = minus = 0
            continue
        plus = max(0, plus + value - drift)
        minus = min(0, minus + value + drift)
        if plus >= threshold or minus <= -threshold:
            out.append(
                {
                    "date": str(date.date()),
                    "direction": "positive" if plus >= threshold else "negative",
                    "accumulator": finite(plus if plus >= threshold else minus),
                    "threshold": threshold,
                    "method": "two-sided past-normalized CUSUM/Page-Hinkley-style candidate; not a verified structural break",
                }
            )
            plus = minus = 0
    return out


def lag_family(weekly):
    results = []
    lags = [-26, -13, -4, 0, 4, 13, 26]
    for spread in ["spread_10y2y_bp", "spread_10y3m_bp"]:
        for index in ["NFCI", "ANFCI"]:
            x = weekly[spread].diff()
            original_y = weekly[index].diff()
            for lag in lags:
                y = original_y.shift(-lag)
                v = pd.concat([x.rename("x"), y.rename("y")], axis=1).dropna()
                r = correlate(x, y)
                r.update(
                    spread=spread,
                    index=index,
                    lag_weeks=lag,
                    kind="first_difference",
                    positive_lag_means="Spread observation at t leads index reference week t+k; not publication availability or causality",
                    hac_maxlags=13,
                    hac_p=None,
                    hac_slope=None,
                    holm_p=None,
                )
                if len(v) >= 52 and v.x.nunique() > 1:
                    fit = sm.OLS(v.y.to_numpy(), sm.add_constant(v.x.to_numpy())).fit(
                        cov_type="HAC", cov_kwds={"maxlags": 13}
                    )
                    r.update(
                        hac_slope=finite(fit.params[1]),
                        hac_p=finite(fit.pvalues[1]),
                        hac_ci95=[finite(z) for z in fit.conf_int()[1]],
                    )
                results.append(r)
    selected = [i for i, r in enumerate(results) if r["hac_p"] is not None]
    if selected:
        # Holm across all28 preregistered tests; unestimable tests conservatively p=1.
        pvals = [r["hac_p"] if r["hac_p"] is not None else 1.0 for r in results]
        reject, adjusted, *_ = multipletests(pvals, alpha=0.05, method="holm")
        for i in selected:
            results[i]["holm_p"] = finite(adjusted[i])
            results[i]["reject_holm_05"] = bool(reject[i])
    return results


def followthrough(daily, weekly):
    episodes = inversion_episodes(daily.spread_10y2y_bp)
    out = []
    for horizon in [13, 26, 52]:
        for threshold in [0, 1, 2]:
            evaluated = 0
            no_follow = 0
            censored = 0
            cases = []
            for episode in episodes:
                if episode["left_censored"]:
                    continue
                start = pd.Timestamp(episode["start"])
                stop = start + pd.Timedelta(weeks=horizon)
                values = weekly.NFCI.loc[
                    (weekly.index >= start) & (weekly.index <= stop)
                ]
                if (
                    stop > weekly.index.max()
                    or len(values) < horizon - 1
                    or values.isna().any()
                ):
                    censored += 1
                    continue
                evaluated += 1
                absent = not (values > threshold).any()
                no_follow += int(absent)
                cases.append(
                    {
                        "inversion_start": episode["start"],
                        "followup_weeks": horizon,
                        "nfci_threshold": threshold,
                        "no_followthrough": absent,
                    }
                )
            out.append(
                {
                    "weeks": horizon,
                    "nfci_threshold": threshold,
                    "evaluated_onsets": evaluated,
                    "no_followthrough": no_follow,
                    "censored_onsets": censored,
                    "cases": cases,
                    "interpretation": "Illustrative retrospective threshold follow-through proxy, not true/false crisis labels or predictive backtest",
                }
            )
    return out


def analyze(frame, metadata, ingestion, config=None):
    config = (config or StudyConfig()).validate()
    wide, daily, weekly = aligned_frames(frame, config)
    spreads = ["spread_10y2y_bp", "spread_10y3m_bp"]
    regimes = {}
    daily_vol = {}
    for col in spreads:
        s = daily[col]
        change = s.diff()
        change.loc[daily.index.to_series().diff().dt.days > 7] = np.nan
        regimes[col] = {
            "distribution_bp": describe(s),
            "change_distribution_bp": describe(change),
            "inverted_sessions": int((s < 0).sum()),
            "valid_sessions": int(s.notna().sum()),
            "missing_sessions": int(s.isna().sum()),
            "regime_counts": {
                "inverted": int((s < 0).sum()),
                "flat_0_to_50bp": int(s.between(0, 50).sum()),
                "positive_above50bp": int((s > 50).sum()),
            },
            "episodes": inversion_episodes(s),
            "max_absolute_session_changes": [
                {"date": str(d.date()), "change_bp": finite(change[d])}
                for d in change.abs().nlargest(10).index
            ],
        }
    for col in ["UST_2Y", "UST_10Y", "UST_30Y"]:
        change = daily[col].diff() * 100
        change.loc[daily.index.to_series().diff().dt.days > 7] = np.nan
        daily_vol[col] = {
            "change_unit": "basis_points_per_observed_session",
            "not_bond_price_return_volatility": True,
            "windows": {
                str(w): describe(change.rolling(w, min_periods=w).std(ddof=1))
                for w in [20, 60]
            },
        }
    contemporaneous = []
    rolling = []
    subperiods = []
    periods = [
        ("2000-01-01", "2006-12-31"),
        ("2007-01-01", "2009-12-31"),
        ("2010-01-01", "2019-12-31"),
        ("2020-01-01", "2020-12-31"),
        ("2021-01-01", "2021-12-31"),
        ("2022-01-01", "2024-12-31"),
        ("2025-01-01", config.end),
    ]
    for spread in spreads:
        for index in ["NFCI", "ANFCI"]:
            for difference in [False, True]:
                x = weekly[spread].diff() if difference else weekly[spread]
                y = weekly[index].diff() if difference else weekly[index]
                r = correlate(x, y)
                r.update(
                    spread=spread,
                    index=index,
                    transformation="first_difference" if difference else "level",
                    bootstrap_ci95=block_interval(x, y, config),
                )
                contemporaneous.append(r)
                for window in [26, 52, 104]:
                    values = x.rolling(window, min_periods=window).corr(y)
                    rolling.append(
                        {
                            "spread": spread,
                            "index": index,
                            "transformation": r["transformation"],
                            "window_weeks": window,
                            "summary": describe(values),
                            "history": [
                                {"date": str(d.date()), "correlation": finite(v)}
                                for d, v in values.dropna().items()
                            ],
                        }
                    )
            for a, b in periods:
                v = weekly.loc[a:b]
                r = correlate(v[spread], v[index])
                r.update(
                    spread=spread,
                    index=index,
                    start=a,
                    end=min(b, str(weekly.index.max().date())),
                    scope="retrospective level correlation; subperiod sample only",
                )
                subperiods.append(r)
    anomalies = []
    zvalues = {}
    change_points = {}
    volatility = []
    for series in spreads + ["NFCI", "ANFCI"]:
        change = weekly[series].diff()
        z = trailing_robust_z(change, config.anomaly_window, config.anomaly_min_history)
        zvalues[series] = z
        for d in z.index[z.abs() >= config.anomaly_z]:
            anomalies.append(
                {
                    "date": str(d.date()),
                    "indicator": series,
                    "change": finite(change[d]),
                    "unit": "basis_points" if series in spreads else "index_points",
                    "robust_z": finite(z[d]),
                    "threshold_abs_z": config.anomaly_z,
                    "history_window_weeks": config.anomaly_window,
                    "minimum_prior_weeks": config.anomaly_min_history,
                    "kind": "extreme_observed_change_not_acquisition_error",
                    "source_ids": ["treasury"] if series in spreads else ["chicago"],
                }
            )
        if series in spreads:
            change_points[series] = change_candidates(z)
            for window in [13, 26]:
                vol = change.rolling(window, min_periods=window).std(ddof=1)
                cutoff = vol.rolling(104, min_periods=52).quantile(0.95).shift(1)
                dates = vol.index[(vol > cutoff) & cutoff.notna()]
                volatility.append(
                    {
                        "indicator": series,
                        "window_weeks": window,
                        "unit": "bp_change_standard_deviation_per_week",
                        "summary": describe(vol),
                        "exceedance_count": len(dates),
                        "exceedance_denominator": int(cutoff.notna().sum()),
                        "threshold": "95th percentile of preceding104weeks, minimum52prior estimates",
                        "examples": [
                            {
                                "date": str(d.date()),
                                "volatility_bp": finite(vol[d]),
                                "past_p95_bp": finite(cutoff[d]),
                            }
                            for d in dates[:20]
                        ],
                    }
                )
    anomalies.sort(key=lambda x: (-abs(x["robust_z"]), x["date"], x["indicator"]))
    divergences = []
    for d in weekly.index:
        a = zvalues[spreads[0]][d]
        b = zvalues["NFCI"][d]
        if (
            np.isfinite(a)
            and np.isfinite(b)
            and abs(a) >= 2
            and abs(b) >= 2
            and a * b < 0
        ):
            divergences.append(
                {
                    "date": str(d.date()),
                    "spread_change_bp": finite(weekly[spreads[0]].diff()[d]),
                    "nfci_change": finite(weekly.NFCI.diff()[d]),
                    "spread_past_z": finite(a),
                    "nfci_past_z": finite(b),
                    "rule": "opposite sign changes, both past-normalized absz>=2; not a causal contradiction",
                }
            )
    annual = []
    for year, group in weekly.groupby(weekly.index.year):
        annual.append(
            {
                "year": int(year),
                "reference_weeks": len(group),
                "nfci": describe(group.NFCI),
                "anfci": describe(group.ANFCI),
            }
        )
    stress = {
        "nfci": describe(weekly.NFCI),
        "anfci": describe(weekly.ANFCI),
        "nfci_above_zero_weeks": int((weekly.NFCI > 0).sum()),
        "nfci_above_one_weeks": int((weekly.NFCI > 1).sum()),
        "denominator_known_nfci_weeks": int(weekly.NFCI.notna().sum()),
        "persistent_positive_4weeks": int(
            (weekly.NFCI.gt(0).rolling(4).sum() == 4).sum()
        ),
        "annual_aggregates": annual,
        "divergences": divergences,
        "threshold_sensitivity": followthrough(daily, weekly),
        "interpretation": "Relative condition and anomaly descriptors, not probabilities of systemic crisis. Index components overlap market information; sources are not independent.",
    }
    sofr = {}
    if "SOFR" in wide:
        s = wide.SOFR.loc[config.start : weekly.index.max()].dropna()
        change = s.diff() * 100
        sofr = {
            "observations": len(s),
            "start": str(s.index.min().date()) if len(s) else None,
            "end": str(s.index.max().date()) if len(s) else None,
            "change_distribution_bp": describe(change),
            "largest_absolute_changes": [
                {"date": str(d.date()), "change_bp": finite(change[d])}
                for d in change.abs().nlargest(5).index
            ],
            "weekly_nfci_correlation": correlate(weekly.SOFR, weekly.NFCI),
            "comparison_scope": "Money-market supplement; shorter inception coverage; retrospective not independent crisis ground truth",
        }
    lag = lag_family(weekly)
    significant = sum(x.get("reject_holm_05", False) for x in lag)
    matrix = {}
    for a in spreads + ["NFCI", "ANFCI"]:
        matrix[a] = {
            b: correlate(weekly[a], weekly[b]) for b in spreads + ["NFCI", "ANFCI"]
        }
    result = {
        "experiment": "FSIE-001",
        "title": "Treasury Yield Curve & Financial Stress — A Historical Analysis of Market Regimes",
        "engine_version": "0.1.0",
        "method_version": METHOD_VERSION,
        "analysis_kind": "retrospective_latest_acquired_vintage_not_predictive_backtest",
        "configuration": asdict(config),
        "study_period": {
            "daily_start": str(daily.index.min().date()),
            "daily_end": str(daily.index.max().date()),
            "weekly_start": str(weekly.index.min().date()),
            "weekly_end": str(weekly.index.max().date()),
        },
        "coverage": {
            "source_observations_acquired": ingestion["observations_seen"],
            "stored_unique_period_observations": len(frame),
            "daily_treasury_sessions": len(daily),
            "weekly_calendar_slots": len(weekly),
            "complete_primary_weeks": int(
                weekly[[*spreads, "NFCI", "ANFCI"]].notna().all(axis=1).sum()
            ),
            "missing_primary_week_slots": int(
                weekly[[*spreads, "NFCI", "ANFCI"]].isna().any(axis=1).sum()
            ),
            "invalid_observations": ingestion.get("invalid_observations", 0),
            "duplicates": ingestion.get("identical_duplicates", 0),
            "excluded_outside_configured_period": ingestion.get(
                "excluded_outside_configured_period", 0
            ),
        },
        "series_metadata": metadata,
        "yield_curve": regimes,
        "daily_yield_change_volatility": daily_vol,
        "contemporaneous_correlations": contemporaneous,
        "rolling_correlations": rolling,
        "lag_tests": lag,
        "lag_test_summary": {
            "family_size": 28,
            "estimable": sum(x["hac_p"] is not None for x in lag),
            "holm_significant_05": significant,
            "holm_not_significant_or_not_estimable": 28 - significant,
            "multiple_testing": "Holm family28, HAC/Newey-West13lags on first differences; no unadjusted result selection",
        },
        "correlation_matrix": matrix,
        "subperiod_correlations": subperiods,
        "anomalies": anomalies,
        "change_point_candidates": change_points,
        "weekly_spread_change_volatility": volatility,
        "systemic_stress": stress,
        "money_market_supplement": sofr,
        "derived_spread_history": [
            {
                "date": str(d.date()),
                "spread_10y2y_bp": finite(v.spread_10y2y_bp),
                "spread_10y3m_bp": finite(v.spread_10y3m_bp),
            }
            for d, v in weekly.iterrows()
        ],
        "findings": [
            {
                "id": "FSIE-001-F1",
                "title": "Observed yield-curve regimes",
                "method": "100*(10Y-shortyield), strictnegative inversion, original observed sessions; explicit episode censoring",
                "evidence": "yield_curve / study_period / coverage",
                "source_ids": ["treasury"],
                "limits": "An inversion is not a certain crisis; sessions and calendar days differ.",
            },
            {
                "id": "FSIE-001-F2",
                "title": "Retrospective financial-condition relationships",
                "method": "Calendar-week alignment, Pearson/Spearman, joint13week blockbootstrap, all28lagtests with HAC/Holm",
                "evidence": "contemporaneous_correlations / lag_tests / subperiod_correlations",
                "source_ids": ["treasury", "chicago"],
                "limits": "Latest-vintage descriptive study, revisions/publication timestamps unavailable; overlapping inputs and autocorrelation limit inference.",
            },
            {
                "id": "FSIE-001-F3",
                "title": "Extreme changes and regime-change candidates",
                "method": "Past-only104week median/MAD, absz>=4, explicit volatility thresholds and two-sidedCUSUM-style candidates",
                "evidence": "anomalies / weekly_spread_change_volatility / change_point_candidates",
                "source_ids": ["treasury", "chicago"],
                "limits": "Outlier is not an acquisition error or proven structural break; no trades, forecasting or investment advice.",
            },
        ],
        "limitations": [
            "Acquired current-vintage observations are not an ALFRED historical real-time panel; no claim of a look-ahead-free predictive backtest.",
            "Observation dates, source update time, acquisition snapshot and actual publication timestamps are distinct; unknown publication dates remain null.",
            "NFCI/ANFCI and subindices include market inputs and revisions; relationships need not be independent and correlations are not causal.",
            "HAC and block-bootstrap inference rely on temporal-dependence/stability assumptions; exploratory results are not guaranteed valid under arbitrary nonstationarity.",
            "All predefined lags, windows and subperiods are shown, including non-significant or not-determinable results.",
            "Yield-change volatility is measured in basis points per observed session/week, not bond-price return volatility or annualized investment risk.",
            "CUSUM-style changes and robust anomalies are heuristic research flags, not verified structural breaks or imminent-crisis labels.",
            "No-follow-through counts use arbitrary declared stress proxies and censor incomplete follow-up; they are not measured crisis forecasting accuracy.",
            "No trading, broker access, money management, leverage, performance promise or personalized recommendation.",
            "No raw institutional time-series archive is relicensed as Apache2.0 or publicly redistributed with the original-code release.",
        ],
        "ai_used_for_numeric_results": False,
    }
    result = clean(result)
    result["analysis_sha256"] = hashlib.sha256(
        json.dumps(
            result, sort_keys=True, allow_nan=False, separators=(",", ":")
        ).encode()
    ).hexdigest()
    return result, weekly

# SPDX-License-Identifier: Apache-2.0
"""Original deterministic process discovery and columnar SQL; no PM4Py/AGPL."""

from pathlib import Path
import json, time, hashlib
import duckdb
from .ingestion import LOW, HIGH
from dynamics.experiments import clean, fingerprint

DAY = 86400000000


def connect(folder, normalized=None):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    c = duckdb.connect(
        str(folder / "analysis.duckdb"), config={"memory_limit": "512MB", "threads": 2}
    )
    c.execute("SET autoinstall_known_extensions=false")
    c.execute("SET autoload_known_extensions=false")
    if normalized:
        c.from_parquet(str(Path(normalized) / "part-*.parquet")).create_view(
            "events", replace=True
        )
    return c


def dicts(c, sql, params=None):
    q = c.execute(sql, params or [])
    keys = [v[0] for v in q.description]
    return [dict(zip(keys, row)) for row in q.fetchall()]


def build(c, progress=None, cancel=None):
    start = time.monotonic()
    marks = {}
    c.execute(
        f"""CREATE OR REPLACE TABLE cases AS SELECT case_key, min(document_key) document_key, min(trace_ordinal) source_case_ordinal, min(category) category,count(DISTINCT category) category_values,count(*) n_events,count(DISTINCT activity) n_activities,count(DISTINCT resource_key) n_resources,min(timestamp_us) first_us,max(timestamp_us) last_us,(max(timestamp_us)-min(timestamp_us))/{DAY}.0 elapsed_day,arg_min(activity,struct_pack(t:=timestamp_us,r:=source_row)) first_activity,arg_max(activity,struct_pack(t:=timestamp_us,r:=source_row)) last_activity,sum(CASE WHEN outside_expected_2018 THEN 1 ELSE 0 END) outside_events,sum(CASE WHEN lifecycle IS NULL THEN 1 ELSE 0 END) missing_lifecycle_events,CAST(to_json(list(activity ORDER BY timestamp_us,source_row)) AS VARCHAR) sequence_json, count(*)-count(DISTINCT activity) repeated_activity_occurrences, sum(CASE WHEN starts_with(activity,'Change ') OR starts_with(activity,'Cancel ') THEN 1 ELSE 0 END) change_cancel_events FROM events GROUP BY case_key"""
    )
    marks["case_reconstruction_seconds"] = time.monotonic() - start
    if progress:
        progress("Reconstructing complete case traces", 1, 4)
    if cancel and cancel():
        raise InterruptedError("Cancelled after case reconstruction")
    tick = time.monotonic()
    c.execute(
        f"""CREATE OR REPLACE TABLE ordered_edges AS SELECT * FROM (SELECT case_key, category,activity source_activity,lead(activity)OVER w target_activity,(lead(timestamp_us)OVER w-timestamp_us)/{DAY}.0 elapsed_day,timestamp_us,lead(timestamp_us)OVER w next_us,source_row FROM events WINDOW w AS(PARTITION BY case_key ORDER BY timestamp_us,source_row))WHERE target_activity IS NOT NULL"""
    )
    c.execute(
        """CREATE OR REPLACE TABLE dfg AS SELECT category,source_activity,target_activity,count(*) frequency,count(DISTINCT case_key) cases,avg(elapsed_day) elapsed_mean_day,median(elapsed_day) elapsed_median_day,quantile_cont(elapsed_day,.9) elapsed_p90_day,sum(CASE WHEN elapsed_day=0 THEN 1 ELSE 0 END) same_timestamp_pairs FROM ordered_edges GROUP BY category,source_activity,target_activity"""
    )
    c.execute(
        """CREATE OR REPLACE TABLE variants AS SELECT category,sha256(sequence_json) variant_id,sequence_json,count(*) cases,avg(elapsed_day) elapsed_mean_day,median(elapsed_day) elapsed_median_day FROM cases GROUP BY category,sequence_json"""
    )
    marks["graph_and_variant_seconds"] = time.monotonic() - tick
    if progress:
        progress("Building observed transition graph and variants", 2, 4)
    if cancel and cancel():
        raise InterruptedError("Cancelled after graph reconstruction")
    tick = time.monotonic()
    # Separate core projection for the twin, not a deletion from the original log.
    c.execute(
        f"""CREATE OR REPLACE TABLE core_cases AS SELECT case_key,min(document_key) document_key,min(trace_ordinal) source_case_ordinal,min(category) category,count(DISTINCT category) category_values,list(activity ORDER BY timestamp_us,source_row) activities,list(timestamp_us ORDER BY timestamp_us,source_row) times_us,min(timestamp_us) first_us,max(timestamp_us) last_us,arg_min(activity,struct_pack(t:=timestamp_us,r:=source_row)) first_activity,arg_max(activity,struct_pack(t:=timestamp_us,r:=source_row)) last_activity,count(*) n_events,sum(CASE WHEN outside_expected_2018 THEN 1 ELSE 0 END) outside_events FROM events WHERE NOT starts_with(activity,'SRM:')GROUP BY case_key"""
    )
    c.execute(
        """CREATE OR REPLACE TABLE cohort_all AS SELECT *,floor((date_part('month',make_timestamp(first_us))-1)/3)+1 cohort_quarter,CASE WHEN date_part('month',make_timestamp(first_us))<=6 THEN 'calibration' WHEN date_part('month',make_timestamp(first_us))<=9 THEN 'validation' ELSE 'test' END split FROM core_cases"""
    )
    c.execute(
        f"""CREATE OR REPLACE TABLE cohort_eligible AS SELECT * FROM cohort_all WHERE category_values=1 AND category!='Consignment' AND category!='UNKNOWN' AND first_activity='Create Purchase Order Item' AND last_activity='Clear Invoice' AND first_us>={LOW} AND last_us<{HIGH} AND date_trunc('quarter',make_timestamp(first_us))=date_trunc('quarter',make_timestamp(last_us))"""
    )
    c.execute(
        """CREATE OR REPLACE TABLE crossing_documents AS SELECT coalesce(document_key,case_key) document_id,count(DISTINCT split) split_count FROM cohort_eligible GROUP BY document_id HAVING count(DISTINCT split)>1"""
    )
    c.execute(
        """CREATE OR REPLACE TABLE cohort AS SELECT a.* FROM cohort_eligible a ANTI JOIN crossing_documents b ON coalesce(a.document_key,a.case_key)=b.document_id"""
    )
    marks["model_cohort_seconds"] = time.monotonic() - tick
    if progress:
        progress(
            "Applying preregistered temporal and document-disjoint cohort rules", 3, 4
        )
    return marks


def analyze(c, import_manifest, dataset, progress=None, cancel=None):
    tick = time.monotonic()
    marks = build(c, progress, cancel)
    totals = dicts(
        c,
        """SELECT count(*) cases,count(DISTINCT document_key) purchase_documents,sum(n_events) events,count(DISTINCT sequence_json) variants, sum(CASE WHEN repeated_activity_occurrences>0 THEN 1 ELSE 0 END) cases_with_repeated_activities,sum(repeated_activity_occurrences) repeated_activity_occurrences,sum(CASE WHEN change_cancel_events>0 THEN 1 ELSE 0 END) cases_with_change_cancel_proxy,sum(change_cancel_events) change_cancel_events,sum(CASE WHEN outside_events>0 THEN 1 ELSE 0 END) cases_outside_2018,min(make_timestamp(first_us)) first_observation,max(make_timestamp(last_us)) last_observation FROM cases""",
    )[0]
    for k in ["first_observation", "last_observation"]:
        totals[k] = totals[k].isoformat() + "Z" if totals[k] else None
    counts = dicts(
        c,
        """SELECT count(DISTINCT activity) activities,count(DISTINCT resource_key) identifiable_resource_tokens,count(DISTINCT CASE WHEN resource_kind='batch' THEN resource_key ELSE NULL END) reported_batch_tokens,count(DISTINCT CASE WHEN lifecycle IS NOT NULL THEN lifecycle ELSE NULL END) lifecycle_values FROM events""",
    )[0]
    totals.update(counts)
    counts2 = dicts(
        c,
        "SELECT count(*) transition_types FROM(SELECT DISTINCT source_activity,target_activity FROM dfg)",
    )[0]
    totals.update(counts2)
    cats = dicts(
        c,
        """SELECT category,count(*) cases,sum(n_events) events,count(DISTINCT sequence_json) variants,avg(elapsed_day) elapsed_mean_day,median(elapsed_day) elapsed_median_day,quantile_cont(elapsed_day,.9) elapsed_p90_day,quantile_cont(elapsed_day,.95) elapsed_p95_day,min(elapsed_day) elapsed_min_day,max(elapsed_day) elapsed_max_day,avg(CASE WHEN repeated_activity_occurrences>0 THEN 1.0 ELSE 0 END) repeated_activity_case_rate,avg(CASE WHEN change_cancel_events>0 THEN 1.0 ELSE 0 END) change_cancel_case_rate,sum(CASE WHEN outside_events>0 THEN 1 ELSE 0 END) cases_outside_2018 FROM cases GROUP BY category ORDER BY cases DESC""",
    )
    quality = dict(import_manifest["counts"])
    quality["exact_duplicate_candidates_retained"] = dicts(
        c,
        "SELECT coalesce(sum(n-1),0) n FROM(SELECT case_key,event_hash,count(*)n FROM events GROUP BY case_key,event_hash HAVING count(*)>1)",
    )[0]["n"]
    quality["source_order_time_reversals"] = dicts(
        c,
        "SELECT count(*) n FROM(SELECT timestamp_us,lag(timestamp_us)OVER(PARTITION BY case_key ORDER BY source_row)previous FROM events)WHERE timestamp_us<previous",
    )[0]["n"]
    quality["same_timestamp_adjacent_pairs"] = dicts(
        c, "SELECT count(*) n FROM ordered_edges WHERE elapsed_day=0"
    )[0]["n"]
    quality["category_conflict_cases"] = dicts(
        c, "SELECT count(*) n FROM cases WHERE category_values!=1"
    )[0]["n"]
    quality["cases_without_create_item"] = dicts(
        c,
        "SELECT count(*)n FROM cases WHERE NOT contains(sequence_json,'\"Create Purchase Order Item\"')",
    )[0]["n"]
    quality["source_closed_case_status"] = (
        "Not supplied; last observed event is not proof of business closure"
    )
    quality["service_and_waiting_times_identifiable"] = False
    included = int(quality.get("imported_events", 0))
    source = int(quality.get("source_events", 0))
    quality["excluded_events"] = source - included
    quality["excluded_percent"] = 100 * (source - included) / source if source else None
    period = dicts(
        c,
        f"""SELECT category,count(*) cases,avg(elapsed_day)elapsed_mean_day,median(elapsed_day)elapsed_median_day,quantile_cont(elapsed_day,.9)elapsed_p90_day FROM cases WHERE first_us>={LOW} AND last_us<{HIGH}GROUP BY category ORDER BY category""",
    )
    graph = dicts(
        c,
        "SELECT * FROM dfg ORDER BY frequency DESC,category,source_activity,target_activity",
    )
    nodes = dicts(
        c,
        "SELECT activity,count(*) events,count(DISTINCT case_key) cases FROM events GROUP BY activity ORDER BY events DESC,activity",
    )
    topvariants = dicts(
        c,
        "SELECT category,variant_id,sequence_json,cases,elapsed_median_day FROM variants ORDER BY cases DESC,variant_id LIMIT 30",
    )
    for x in topvariants:
        x["activities"] = json.loads(x.pop("sequence_json"))
    longedges = dicts(
        c,
        "SELECT * FROM dfg WHERE cases>=100 ORDER BY elapsed_median_day DESC,frequency DESC LIMIT 15",
    )
    # Observed open-interval WIP proxy; no inference of unobserved work after final event.
    daily = dicts(
        c,
        f"""SELECT CAST(day AS DATE)date,(SELECT count(*)FROM cases WHERE first_us<=epoch_us(day) AND last_us>epoch_us(day))observed_interval_WIP,(SELECT count(*) FROM cases WHERE first_us>=epoch_us(day) AND first_us<epoch_us(day+INTERVAL 1 DAY))first_observations,(SELECT count(*)FROM cases WHERE last_us>=epoch_us(day) AND last_us<epoch_us(day+INTERVAL 1 DAY))last_observations FROM generate_series(TIMESTAMP '2018-01-01',TIMESTAMP '2018-12-31',INTERVAL 1 DAY) t(day)""",
    )
    for x in daily:
        x["date"] = x["date"].isoformat()
    compliance = dicts(
        c,
        """WITH x AS(SELECT case_key,min(category) category,min(CASE WHEN activity='Record Goods Receipt' THEN timestamp_us END) goods_us,min(CASE WHEN activity='Record Invoice Receipt' THEN timestamp_us END) invoice_us FROM events GROUP BY case_key)SELECT category,count(*) cases,sum(CASE WHEN goods_us IS NOT NULL AND invoice_us IS NOT NULL AND invoice_us<goods_us THEN 1 ELSE 0 END) invoice_observed_before_first_goods,sum(CASE WHEN invoice_us IS NOT NULL AND goods_us IS NULL THEN 1 ELSE 0 END) invoice_without_observed_goods FROM x GROUP BY category ORDER BY category""",
    )
    sample_stats = dicts(
        c,
        """SELECT split,category,count(*) cases,count(DISTINCT coalesce(document_key,case_key)) documents FROM cohort GROUP BY split,category ORDER BY split,category""",
    )
    stages = {
        "source_cases": totals["cases"],
        "core_projected_cases": dicts(c, "SELECT count(*)n FROM core_cases")[0]["n"],
        "core_events_retained": dicts(
            c, "SELECT count(*)n FROM events WHERE NOT starts_with(activity,'SRM:')"
        )[0]["n"],
        "invoice_endpoint_quarter_eligible_cases": dicts(
            c, "SELECT count(*)n FROM cohort_eligible"
        )[0]["n"],
        "cross_split_documents_excluded": dicts(
            c, "SELECT count(*)n FROM crossing_documents"
        )[0]["n"],
        "cross_split_document_cases_excluded": dicts(
            c,
            "SELECT (SELECT count(*)FROM cohort_eligible)-(SELECT count(*)FROM cohort)n",
        )[0]["n"],
        "cohort_cases": dicts(c, "SELECT count(*)n FROM cohort")[0]["n"],
        "groups": sample_stats,
    }
    # Explicit nonoverlapping reasons (not subtracting SRM events from full discovery).
    stages["exclusion_rules"] = dicts(
        c,
        f"""SELECT reason,count(*) cases FROM(SELECT CASE WHEN category_values!=1 THEN 'category_conflict' WHEN category IN('Consignment','UNKNOWN') THEN 'no_comparable_invoice_endpoint_category' WHEN first_activity!='Create Purchase Order Item' THEN 'projected_creation_not_observed_first' WHEN last_activity!='Clear Invoice' THEN 'projected_invoice_clearance_not_observed_last' WHEN first_us<{LOW} OR last_us>={HIGH} THEN 'core_timestamp_outside2018' WHEN date_trunc('quarter',make_timestamp(first_us))!=date_trunc('quarter',make_timestamp(last_us))THEN 'case_crosses_quarter_boundary' ELSE 'eligible_before_document_gate' END reason FROM cohort_all)GROUP BY reason ORDER BY reason""",
    )
    r = {
        "experiment": "OTE-001",
        "title": "Enterprise Process Reconstruction",
        "kind": "OBSERVED",
        "method_version": "ote-discovery-1.0",
        "dataset": dataset,
        "counts": totals,
        "data_quality": quality,
        "category_performance": cats,
        "strict_2018_sensitivity": period,
        "graph": {
            "nodes": nodes,
            "edges": graph,
            "meaning": "Directly-follows observations, not causal dependencies; timestamp ties retain original stable source order",
        },
        "top_variants": topvariants,
        "long_elapsed_transitions": longedges,
        "daily_observed_metrics": daily,
        "explicit_rule_observations": {
            "rules": "For after-GR matching only, an earlier invoice is a deviation from the stated model rule. Other categories legitimately permit different sequences. Missing events/censoring/ties prevent confirmed compliance conclusions.",
            "classification": "Observed deviations; no confirmed business/regulatory violations claimed",
            "by_category": compliance,
        },
        "model_cohort": stages,
        "limits": [
            "Elapsed first-to-last observation is not processing time or waiting time. No start/completion lifecycle supplied in inspected source schema; full distribution audited.",
            "Repeated goods receipts/invoices can be legitimate installments; repetition is not automatically waste or rework. Change/Cancel is an explicit descriptive proxy.",
            "Declared2018coverage differs from any out-of-period observed timestamps; flagged observations remain in full discovery and a strict-window sensitivity is separate.",
            "WIP is an observed interval proxy and last-observation counts are not independently verified true business completions.",
            "Long elapsed transitions suggest investigation; employee productivity, causes and monetary savings are not inferred.",
            "All model validation uses an explicitly projected, endpoint-proxy, quarter-contained and document-disjoint subset; not all251734cases.",
        ],
    }
    marks["performance_analysis_seconds"] = (
        time.monotonic() - tick - sum(marks.values())
    )
    marks["total_discovery_seconds"] = time.monotonic() - tick
    if progress:
        progress(
            "Observed process reconstructed with quality and category audits", 4, 4
        )
    return fingerprint(clean(r)), marks


def sample_cohort(c, split, limit=3000, seed=20261106):
    if split not in ("calibration", "validation", "test") or not 1 <= limit <= 100000:
        raise ValueError("Known bounded temporal cohort required")
    suffix = (
        ""
        if split == "calibration"
        else f" ORDER BY sha256(CAST(source_case_ordinal AS VARCHAR)||':{int(seed)}') LIMIT {int(limit)}"
    )
    rows = dicts(c, "SELECT * FROM cohort WHERE split=?" + suffix, [split])
    rows.sort(key=lambda x: (x["first_us"], x["source_case_ordinal"]))
    for row in rows:
        row["duration_day"] = (row["last_us"] - row["first_us"]) / DAY
        row["gaps_day"] = [
            (b - a) / DAY for a, b in zip(row["times_us"], row["times_us"][1:])
        ]
        row["document_group"] = row["document_key"] or row["case_key"]
    return rows

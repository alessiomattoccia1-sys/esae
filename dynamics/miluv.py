# SPDX-License-Identifier: Apache-2.0
"""MILUV historical range consistency, not tracking, control or sensor placement."""

from pathlib import Path
import json, io, hashlib, time
import numpy as np, pandas as pd, yaml
from scipy.spatial.transform import Rotation
from .acquisition import MILUV_META, MILUV_FILES, RemoteZip

COMMIT = "399ad46f4e6e88c3c98b40aae33fe8e2c6719cff"
COHORT = ["default_1_circular2D_0", "default_1_circular3D_0", "default_1_random3_0"]
CONFIG = [
    "config/experiments.csv",
    "config/uwb/anchors.yaml",
    "config/uwb/tags.yaml",
    "preprocess/cleanup_csv.py",
    "preprocess/process_uwb.py",
    "miluv/utils.py",
    "examples/ekfutils/imu_one_robot_models.py",
]


def read_csv(data, required):
    if len(data) > 40_000_000:
        raise ValueError("Bounded scientific CSV required")
    f = pd.read_csv(io.BytesIO(data))
    if len(f) > 200000 or not set(required) <= set(f):
        raise ValueError("Verified MILUV schema required")
    for col in required:
        f[col] = pd.to_numeric(f[col], errors="coerce")
    return f


def statistics(residual, std=None):
    e = np.asarray(residual, float)
    e = e[np.isfinite(e)]
    if not len(e):
        return {"n": 0, "status": "INSUFFICIENT EVIDENCE"}
    r = {
        "n": len(e),
        "bias_m": float(e.mean()),
        "MAE_m": float(np.abs(e).mean()),
        "RMSE_m": float(np.sqrt(np.mean(e**2))),
        "absolute_error_p50_m": float(np.quantile(abs(e), 0.5)),
        "absolute_error_p95_m": float(np.quantile(abs(e), 0.95)),
    }
    if std is not None:
        s = np.asarray(std, float)
        good = np.isfinite(s) & (s > 0) & np.isfinite(residual)
        r.update(
            coverage95=(
                float(
                    np.mean(
                        abs(np.asarray(residual)[good]) <= 1.959963984540054 * s[good]
                    )
                )
                if good.any()
                else None
            ),
            coverage_denominator=int(good.sum()),
            nominal_coverage=0.95,
        )
    return r


def align_mocap(mocap, ranges, anchors, tags, tolerance=0.02, offset=0):
    cols = (
        ["timestamp"]
        + ["pose.position." + c for c in "xyz"]
        + ["pose.orientation." + c for c in ["x", "y", "z", "w"]]
    )
    m = mocap[cols].to_numpy(float)
    valid = (
        np.isfinite(m).all(axis=1)
        & (np.linalg.norm(m[:, 1:4], axis=1) > 1e-6)
        & (np.abs(np.linalg.norm(m[:, 4:], axis=1) - 1) < 0.01)
    )
    m = m[valid]
    if len(m) < 2 or np.any(np.diff(m[:, 0]) <= 0):
        raise ValueError("Increasing valid motion-capture clock required")
    t = ranges.timestamp.to_numpy() + offset
    k = np.searchsorted(m[:, 0], t)
    a = np.maximum(0, k - 1)
    b = np.minimum(len(m) - 1, k)
    ix = np.where(abs(m[a, 0] - t) <= abs(m[b, 0] - t), a, b)
    match = (t >= m[0, 0]) & (t <= m[-1, 0]) & (abs(m[ix, 0] - t) <= tolerance)
    expected = np.full(len(t), np.nan)
    for i, row in enumerate(ranges.itertuples(index=False)):
        if not match[i]:
            continue
        src, dst = str(int(row.from_id)), str(int(row.to_id))
        tag = src if src in tags else dst if dst in tags else None
        anchor = dst if dst in anchors else src if src in anchors else None
        if tag is None or anchor is None:
            match[i] = False
            continue
        pose = m[ix[i]]
        position = pose[1:4] + Rotation.from_quat(pose[4:]).apply(tags[tag])
        expected[i] = np.linalg.norm(position - np.asarray(anchors[anchor]))
    return expected, match, abs(m[ix, 0] - t)


def run(cache, folder, cfg, progress=None, cancel=None):
    from .experiments import fingerprint

    tick = time.monotonic()
    offline = cfg.get("offline", False)
    p, meta = cache.fetch(MILUV_META, offline)
    j = json.loads(p.read_text())
    if j["license"]["name"] != "CC BY 4.0" or j["version"] != 1:
        raise ValueError("MILUV vintage/rights changed: review required")
    documents = {}
    sources = {}
    for path in CONFIG:
        p, rec = cache.fetch(
            "https://raw.githubusercontent.com/decargroup/miluv/" + COMMIT + "/" + path,
            offline,
        )
        documents[path] = p.read_text()
        sources[path] = rec["sha256"]
    experiments = pd.read_csv(io.StringIO(documents["config/experiments.csv"]))
    # safe_load never reconstructs executable Python objects; string vectors use JSON.
    anchor_sets = yaml.safe_load(documents["config/uwb/anchors.yaml"])
    tag_sets = yaml.safe_load(documents["config/uwb/tags.yaml"])
    tags = {str(k): json.loads(v) for k, v in tag_sets["ifo001"].items()}
    anchors = {str(k): json.loads(v) for k, v in anchor_sets["0"].items()}
    members = []
    flights = []
    all_cal = []
    all_raw = []
    all_std = []
    dataset_observations = 0
    excluded_total = 0
    invalid_mocap_total = 0
    normalized = Path(folder) / "normalized"
    normalized.mkdir(parents=True, exist_ok=True)
    for seq in COHORT:
        if cancel and cancel():
            raise InterruptedError("Cancelled between scientific subsets")
        erow = experiments[experiments.experiment == seq]
        if len(erow) != 1 or str(erow.iloc[0].anchor_constellation) != "0":
            raise ValueError("Comparable published constellation required")
        f = next(x for x in j["files"] if x["name"] == seq + ".zip")
        if f["id"] not in MILUV_FILES:
            raise ValueError("Unexpected source file")
        z = RemoteZip(cache, f["download_url"], f["size"], offline)
        rows = z.inventory()
        data = {}
        for name in ["uwb_range.csv", "mocap.csv"]:
            row = next(x for x in rows if x["name"] == seq + "/ifo001/" + name)
            b = z.member(row)
            target = Path(folder) / "inputs" / seq
            target.mkdir(parents=True, exist_ok=True)
            (target / name).write_bytes(b)
            members.append(
                {
                    "name": row["name"],
                    "archive_url": f["download_url"],
                    "archive_size": f["size"],
                    "whole_archive_checksum_verified": False,
                    "bytes": len(b),
                    "crc32": f"{row['crc32']:08x}",
                    "sha256": hashlib.sha256(b).hexdigest(),
                }
            )
            data[name] = b
        columns = [
            "timestamp",
            "from_id",
            "to_id",
            "range",
            "range_raw",
            "gt_range",
            "std",
        ]
        rf = read_csv(data["uwb_range.csv"], columns)
        mf = read_csv(
            data["mocap.csv"],
            ["timestamp"]
            + ["pose.position." + c for c in "xyz"]
            + ["pose.orientation." + c for c in ["x", "y", "z", "w"]],
        )
        dataset_observations += len(rf)
        valid = (
            np.isfinite(rf[columns]).all(axis=1)
            & (rf.range >= 0)
            & (rf.range_raw >= 0)
            & (rf.gt_range > 0)
            & (rf["std"] > 0)
        )
        invalid = int((~valid).sum())
        rf = rf[valid].copy()
        dup = rf.duplicated(["timestamp", "from_id", "to_id"])
        dups = int(dup.sum())
        rf = rf[~dup].copy()
        # Source table may interleave pairs; a stable sort is explicit and recorded.
        rf = rf.sort_values("timestamp", kind="stable")
        excluded_total += invalid + dups
        calibrated = (rf.range - rf.gt_range).to_numpy()
        raw = (rf.range_raw - rf.gt_range).to_numpy()
        std = rf["std"].to_numpy()
        calc, good, dt = align_mocap(mf, rf, anchors, tags)
        if not good.any():
            raise ValueError("No independently reconstructed timestamp-matched ranges")
        invalid_mocap = int((~np.isfinite(mf.to_numpy(float)).all(axis=1)).sum())
        invalid_mocap_total += invalid_mocap
        groups = []
        for pair, rows in rf.groupby(["from_id", "to_id"], sort=True):
            groups.append(
                {
                    "pair": list(map(int, pair)),
                    "calibrated": statistics(
                        (rows.range - rows.gt_range).to_numpy(), rows["std"].to_numpy()
                    ),
                    "raw": statistics((rows.range_raw - rows.gt_range).to_numpy()),
                }
            )
        sensitivity = []
        for tolerance, offset in [(v, 0) for v in [0.005, 0.01, 0.02]] + [
            (0.02, v) for v in [-0.02, -0.01, 0.01, 0.02]
        ]:
            g, ok, _ = align_mocap(mf, rf, anchors, tags, tolerance, offset)
            sensitivity.append(
                {
                    "nearest_tolerance_s": tolerance,
                    "applied_time_offset_s": offset,
                    "matched": int(ok.sum()),
                    "range_residual": statistics((rf.range.to_numpy() - g)[ok]),
                }
            )
        out = pd.DataFrame(
            {
                "time_s": rf.timestamp,
                "from_id": rf.from_id,
                "to_id": rf.to_id,
                "calibrated_residual_m": calibrated,
                "raw_residual_m": raw,
                "source_std_m": std,
                "source_reference_range_m": rf.gt_range,
                "reconstructed_range_m": calc,
                "mocap_time_distance_s": dt,
                "mocap_match": good,
            }
        )
        out.to_parquet(normalized / (seq + ".parquet"), index=False)
        stride = max(1, len(rf) // 600)
        flights.append(
            {
                "flight_id": seq,
                "robot_id": "ifo001",
                "raw_rows": len(valid),
                "valid_rows": len(rf),
                "invalid_rows": invalid,
                "duplicates_removed": dups,
                "mocap_rows": len(mf),
                "invalid_mocap_nonfinite_rows": invalid_mocap,
                "temporal_coverage_s": [
                    float(rf.timestamp.min()),
                    float(rf.timestamp.max()),
                ],
                "calibrated": statistics(calibrated, std),
                "raw": statistics(raw),
                "pair_groups": groups,
                "nearest_mocap": {
                    "matched": int(good.sum()),
                    "unmatched": int((~good).sum()),
                    "tolerance_s": 0.02,
                    "max_time_distance_s": float(dt[good].max()),
                    "reconstructed_vs_published_reference": statistics(
                        calc[good] - rf.gt_range.to_numpy()[good]
                    ),
                    "calibrated_vs_reconstructed": statistics(
                        rf.range.to_numpy()[good] - calc[good]
                    ),
                },
                "sensitivity": sensitivity,
                "display": out.iloc[::stride]
                .where(pd.notna(out.iloc[::stride]), None)
                .to_dict(orient="records"),
            }
        )
        all_cal.extend(calibrated)
        all_raw.extend(raw)
        all_std.extend(std)
        if progress:
            progress(
                "Analysing historical MILUV UWB/reference consistency", len(flights), 3
            )
    r = {
        "experiment": "DME-002",
        "title": "Observational Uncertainty & Multi-Sensor Consistency — MILUV substitution",
        "status": "computed",
        "kind": "REAL EXPERIMENTAL DATA",
        "method_version": "dme-miluv-1.0",
        "configuration": {k: v for k, v in cfg.items() if k != "offline"},
        "dataset": {
            "name": j["title"],
            "doi": j["doi"],
            "version": j["version"],
            "source": MILUV_META,
            "license": "CC BY 4.0",
            "authors": [x.get("full_name") for x in j["authors"]],
            "available_experiments_source_description": 36,
            "selected_flights": COHORT,
            "selected_members": members,
            "devkit_commit": COMMIT,
            "configuration_hashes": sources,
        },
        "substitution": {
            "original": "AERPAW DOI10.5061/dryad.7d7wm3898",
            "reason": "Official public download403 and API401; no matching local archive; user authorized another scientific source",
            "scope_change": "UWB scalar range vs motion-capture-derived distance instead of radar/RF3D position; no claimed position or independent sensor accuracy",
        },
        "counts": {
            "real_flights_analyzed": len(flights),
            "source_uwb_rows": dataset_observations,
            "observations_analyzed": len(all_cal),
            "excluded_uwb_rows": excluded_total,
            "source_mocap_rows": sum(f["mocap_rows"] for f in flights),
            "matched_mocap_ranges": sum(f["nearest_mocap"]["matched"] for f in flights),
        },
        "metrics": {
            "observation_weighted_calibrated": statistics(
                np.asarray(all_cal), np.asarray(all_std)
            ),
            "observation_weighted_raw": statistics(np.asarray(all_raw)),
            "equal_flight_mean_MAE_m": float(
                np.mean([f["calibrated"]["MAE_m"] for f in flights])
            ),
        },
        "flights": flights,
        "units": {
            "range": "m",
            "residual": "m",
            "time": "s",
            "orientation": "quaternion xyzw, body→Vicon world",
        },
        "transformations": [
            "Source calibrated range and source gt_range retained separately from raw range",
            "finite/positive gates; duplicate timestamp+pair first retained; explicit stable time sort",
            "Nearest motion capture without extrapolation; explicit20ms tolerance",
            "tag_world=position+Rotation(xyzw)@published_tag_offset; reference=norm(tag_world-anchor)",
            "Sensitivity recalculates fixed time tolerances and offsets, not fitted synchronisation",
        ],
        "limits": [
            "UWB range residual is not3D position error or UAV intent.",
            "Source gt_range is motion-capture-derived, not exact physical truth; reconstruction uses same reference system.",
            "Published std is a calibrated measurement uncertainty model, not known total uncertainty; nominal normal95percent coverage is measured, not guaranteed.",
            "Source calibrator training/held-out independence not established; before/after comparison is descriptive.",
            "Three selected flights/one UAV/indoor constellation0 do not establish generalization across36experiments or platforms.",
            "Nearest-time differences and source spline processing can explain reconstructed-vs-published reference differences; no unrecorded alignment or recalibration.",
        ],
    }
    return fingerprint(r), {"acquisition_and_analysis_seconds": time.monotonic() - tick}

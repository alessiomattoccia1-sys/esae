# SPDX-License-Identifier: Apache-2.0
"""Historical civil trajectory schema and WGS84 local Cartesian normalization."""

from pathlib import Path
import re, io, json, hashlib
import numpy as np, pandas as pd
from .acquisition import ZENODO_META, IDF_ZIP, RemoteZip, DRYAD_META


def enu(latitude, longitude, origin=None):
    lat = np.asarray(latitude, float)
    lon = np.asarray(longitude, float)
    if (
        lat.shape != lon.shape
        or not np.isfinite(lat).all()
        or not np.isfinite(lon).all()
        or (np.abs(lat) > 90).any()
        or (np.abs(lon) > 180).any()
    ):
        raise ValueError("Finite geographic degrees required")
    origin = tuple(origin) if origin is not None else (float(lat[0]), float(lon[0]))
    a = 6378137.0
    e2 = 6.6943799901413165e-3
    phi = np.deg2rad(lat)
    lam = np.deg2rad(lon)
    n = a / np.sqrt(1 - e2 * np.sin(phi) ** 2)
    xyz = np.column_stack(
        [
            n * np.cos(phi) * np.cos(lam),
            n * np.cos(phi) * np.sin(lam),
            n * (1 - e2) * np.sin(phi),
        ]
    )
    p, l = np.deg2rad(origin)
    n0 = a / np.sqrt(1 - e2 * np.sin(p) ** 2)
    center = np.array(
        [
            n0 * np.cos(p) * np.cos(l),
            n0 * np.cos(p) * np.sin(l),
            n0 * (1 - e2) * np.sin(p),
        ]
    )
    east = np.array([-np.sin(l), np.cos(l), 0])
    north = np.array([-np.sin(p) * np.cos(l), -np.sin(p) * np.sin(l), np.cos(p)])
    delta = xyz - center
    return np.column_stack([delta @ east, delta @ north])


def parse_idf(data, flight_id):
    if len(data) > 20_000_000:
        raise ValueError("CSV bound")
    frame = pd.read_csv(io.BytesIO(data))
    required = ["time (us)", "GPS_coord[0]", "GPS_coord[1]", "GPS_numSat"]
    if not set(required) <= set(frame):
        raise ValueError("Verified IDF GPS schema required")
    if not 100 <= len(frame) <= 200000:
        raise ValueError("Flight sample bound")
    v = frame[required].apply(pd.to_numeric, errors="coerce").to_numpy()
    bad = ~np.isfinite(v).all(axis=1)
    geo = (
        (np.abs(v[:, 1]) > 90)
        | (np.abs(v[:, 2]) > 180)
        | ((v[:, 1] == 0) & (v[:, 2] == 0))
    )
    sat = v[:, 3] < 4
    keep = ~(bad | geo | sat)
    selected = v[keep]
    rows = np.where(keep)[0]
    if len(selected) < 100:
        raise ValueError("Insufficient valid source GPS")
    t = selected[:, 0] * 1e-6
    dup = np.r_[False, np.diff(t) == 0]
    selected = selected[~dup]
    rows = rows[~dup]
    t = selected[:, 0] * 1e-6
    if (np.diff(t) <= 0).any():
        raise ValueError("Nonmonotonic source clock; no silent sorting")
    relative = t - t[0]
    xy = enu(selected[:, 1], selected[:, 2])
    dt = np.diff(relative)
    quality = {
        "input_rows": len(frame),
        "valid_rows": len(t),
        "excluded_rows": len(frame) - len(t),
        "nonfinite_rows": int(bad.sum()),
        "invalid_geo_rows": int((geo & ~bad).sum()),
        "insufficient_satellite_rows": int((sat & ~bad & ~geo).sum()),
        "duplicate_timestamps_removed_keep_first": int(dup.sum()),
        "gaps_over_2s": int((dt > 2).sum()),
        "median_step_seconds": float(np.median(dt)),
        "minimum_step_seconds": float(dt.min()),
        "maximum_step_seconds": float(dt.max()),
        "irregular_sampling": bool(np.ptp(dt) > 1e-5),
        "gps_fix_type_values": (
            sorted(frame.GPS_fixType.dropna().unique().tolist())
            if "GPS_fixType" in frame
            else []
        ),
        "sensor_calibration_uncertainty": None,
        "rules": "finite coordinates, geographic ranges, >=4satellites, first duplicate retained; no interpolation/sorting; motion reference is recorded GNSS, not known true state",
    }
    return {
        "flight_id": flight_id,
        "dataset": "IDF_DS",
        "kind": "REAL EXPERIMENTAL DATA",
        "platform": "Speedybee/INAV fixed-wing source subset",
        "time_s": relative,
        "position_m": xy,
        "source_rows": rows,
        "quality": quality,
        "metadata": {
            "time_source": "time (us), source relative onboard clock; us→s then first retained time subtraction",
            "coordinate_frame": "Horizontal local ENU projection of WGS84 ellipsoid ECEF; source altitude not interpreted",
            "position_units": "m",
            "time_units": "s",
            "source_unit_evidence": "CSV header time(us), decimal-degree GPS coordinate fields and dataset description; only horizontal positions used",
            "source_altitude_unit": "Not assumed, altitude excluded",
            "origin_lat_lon": selected[0, 1:3].tolist(),
            "independent_day_group": "Not provided; full source file split, shared circuit/platform generalization limitation",
            "source_sha256": hashlib.sha256(data).hexdigest(),
            "transformations": [
                "finite/coordinate/satellite gates",
                "explicit duplicate handling",
                "relative time",
                "WGS84 ECEF→ENU horizontal",
            ],
            "reference_status": "Recorded GNSS with unknown total error, not simulation truth",
        },
    }


def acquire_idf(cache, folder, count=30, offline=False, progress=None, cancel=None):
    if count not in (12, 30, 60):
        raise ValueError("Documented cohort sizes12/30/60")
    p, meta = cache.fetch(ZENODO_META, offline)
    j = json.loads(p.read_text())
    if j["metadata"].get("license", {}).get("id") != "cc-by-4.0":
        raise ValueError("IDF source rights require review")
    source = next(f for f in j["files"] if f["key"] == "Speedybee DataSet.zip")
    z = RemoteZip(cache, source["links"]["self"], source["size"], offline)
    inventory = z.inventory()
    gps = sorted(
        [
            x
            for x in inventory
            if re.fullmatch(
                r"Speedybee DataSet/processed/GPS/Lap\d{3}_gps\.csv", x["name"]
            )
        ],
        key=lambda x: x["name"],
    )
    selected = gps[:count]
    folder = Path(folder)
    inputs = folder / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    flights = []
    excluded = []
    members = []
    for index, row in enumerate(selected):
        if cancel and cancel():
            raise InterruptedError("Cancelled between bounded member acquisitions")
        data = z.member(row)
        flight_id = Path(row["name"]).stem
        path = inputs / (flight_id + ".csv")
        path.write_bytes(data)
        members.append(
            {
                "name": row["name"],
                "bytes": len(data),
                "crc32": f"{row['crc32']:08x}",
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
        try:
            flights.append(parse_idf(data, flight_id))
        except ValueError as e:
            excluded.append({"flight_id": flight_id, "reason": str(e)})
        if progress:
            progress("Acquiring verified IDF GPS members", index + 1, len(selected))
    return flights, {
        "source": "Zenodo IDF_DS",
        "doi": j["doi"],
        "version": j["metadata"].get("version"),
        "archive_url": source["links"]["self"],
        "archive_total_bytes": source["size"],
        "archive_declared_md5_not_whole_verified": source["checksum"],
        "whole_archive_downloaded": False,
        "license": "CC-BY-4.0",
        "authors": [c["name"] for c in j["metadata"]["creators"]],
        "concept_dataset_flights_claimed": 240,
        "readme_speedybee_flights_claimed": 120,
        "actual_gps_members": len(gps),
        "selected_by_rule": "First"
        + str(count)
        + "lexicographically sorted GPS files before values; no outcome selection",
        "members": members,
        "excluded": excluded,
        "source_metadata_sha256": meta["sha256"],
        "imported_flights": len(flights),
        "raw_source_bytes": sum(m["bytes"] for m in members),
        "documentation_caveat": "Speedybee README describes120flights; actual archive has111GPS files. Do not conflate archive layouts or claim all240flights analyzed.",
    }


def aerpaw_status(cache, offline=False):
    p, r = cache.fetch(DRYAD_META, offline)
    j = json.loads(p.read_text())
    if j.get("license") != "https://spdx.org/licenses/CC0-1.0.html":
        raise ValueError("Dryad source rights require review")
    return {
        "source": "AERPAW / Dryad",
        "doi": "10.5061/dryad.7d7wm3898",
        "version": j.get("versionNumber"),
        "license": "CC0-1.0",
        "title": j["title"],
        "source_metadata_sha256": r["sha256"],
        "authors": [
            str(x.get("firstName", "")) + " " + str(x.get("lastName", ""))
            for x in j.get("authors", [])
        ],
        "documented_real_competition_flights": 33,
        "documented_localization_extras": 3,
        "digital_twin_data_present": True,
        "scope": "Only historical real-flight observed/reference consistency; no placement/flight optimization or live tracking",
    }

# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Explicit units/dates and missingness; XML/CSV/JSON are data, never commands."""

import csv, datetime, io, json, math, re, xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter
from . import PARSER_VERSION

CSV_MATURITIES = {
    "1 Mo": "1M",
    "1.5 Month": "1.5M",
    "2 Mo": "2M",
    "3 Mo": "3M",
    "4 Mo": "4M",
    "6 Mo": "6M",
    "1 Yr": "1Y",
    "2 Yr": "2Y",
    "3 Yr": "3Y",
    "5 Yr": "5Y",
    "7 Yr": "7Y",
    "10 Yr": "10Y",
    "20 Yr": "20Y",
    "30 Yr": "30Y",
}
XML_MATURITIES = {
    "BC_1MONTH": "1M",
    "BC_1_5MONTH": "1.5M",
    "BC_2MONTH": "2M",
    "BC_3MONTH": "3M",
    "BC_4MONTH": "4M",
    "BC_6MONTH": "6M",
    "BC_1YEAR": "1Y",
    "BC_2YEAR": "2Y",
    "BC_3YEAR": "3Y",
    "BC_5YEAR": "5Y",
    "BC_7YEAR": "7Y",
    "BC_10YEAR": "10Y",
    "BC_20YEAR": "20Y",
    "BC_30YEAR": "30Y",
}
NFCI_FIELDS = ["NFCI", "ANFCI", "Risk", "Credit", "Leverage", "Nonfinancial_Leverage"]


def day(value):
    value = str(value).strip()
    try:
        d = (
            datetime.date.fromisoformat(value[:10])
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}(T.*)?", value)
            else datetime.datetime.strptime(
                value,
                (
                    "%m/%d/%y"
                    if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{2}", value)
                    else "%m/%d/%Y"
                ),
            ).date()
        )
    except ValueError:
        raise ValueError("Invalid observation date")
    if not datetime.date(1970, 1, 1) <= d <= datetime.date(2100, 12, 31):
        raise ValueError("Date outside financial bounds")
    return d.isoformat()


def number(value):
    if value is None or str(value).strip().lower() in (
        "",
        "n/a",
        "na",
        "null",
        ".",
        "nan",
    ):
        return None
    if isinstance(value, bool):
        raise ValueError("Boolean is not a financial quantity")
    try:
        v = float(value)
    except (ValueError, TypeError):
        raise ValueError("Invalid financial quantity")
    if not math.isfinite(v):
        return None
    if abs(v) > 1000:
        raise ValueError("Quantity outside declared parser bound")
    return v


def observation(series, date, value, record, frequency, unit, revision=None):
    d = day(date)
    return {
        "series_id": series,
        "observation_date": d,
        "value": number(value),
        "unit": unit,
        "frequency": frequency,
        "source_id": record["source_id"],
        "source_sha256": record["sha256"],
        "publication_at": None,
        "source_updated_at": record.get("source_updated_at"),
        "acquired_at": record["acquired_at"],
        "vintage_at": record["acquired_at"],
        "vintage_kind": "acquisition_snapshot",
        "revision_flag": revision,
        "parser_version": PARSER_VERSION,
    }


def parse(path, record):
    if Path(path).stat().st_size > 12_000_000:
        raise ValueError("Source file limit exceeded")
    kind = record["parser"]
    data = Path(path).read_bytes()
    rows = []
    counts = Counter()

    def emit(series, date, value, frequency, unit, revision=None):
        counts["observations_seen"] += 1
        try:
            r = observation(series, date, value, record, frequency, unit, revision)
        except (ValueError, TypeError) as exc:
            counts["invalid_observations"] += 1
            counts["reason:" + str(exc)] += 1
            return
        if r["value"] is None:
            counts["missing_values"] += 1
        rows.append(r)

    if kind in ("treasury_csv", "nfci_csv"):
        reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")))
        headers = reader.fieldnames or []
        if kind == "treasury_csv":
            if not {"Date", "3 Mo", "2 Yr", "5 Yr", "10 Yr", "30 Yr"} <= set(headers):
                raise ValueError("Treasury CSV schema changed")
            unknown = set(headers) - {"Date"} - set(CSV_MATURITIES)
            if unknown:
                raise ValueError(
                    "Unknown Treasury maturities: " + ",".join(sorted(unknown))
                )
            fields = {k: v for k, v in CSV_MATURITIES.items() if k in headers}
        else:
            if not {"Friday_of_Week", "NFCI", "ANFCI"} <= set(headers):
                raise ValueError("NFCI CSV schema changed")
            fields = {k: k for k in NFCI_FIELDS if k in headers}
        for row in reader:
            counts["rows_seen"] += 1
            date = row.get("Date" if kind == "treasury_csv" else "Friday_of_Week")
            if kind == "nfci_csv":
                try:
                    if datetime.date.fromisoformat(day(date)).weekday() != 4:
                        raise ValueError("Weekly reference must be Friday")
                except ValueError:
                    counts["invalid_rows"] += 1
                    continue
            for field, label in fields.items():
                emit(
                    ("UST_" + label) if kind == "treasury_csv" else label,
                    date,
                    row.get(field),
                    "daily" if kind == "treasury_csv" else "weekly",
                    (
                        "percentage_points"
                        if kind == "treasury_csv"
                        else "standardized_index"
                    ),
                )
    elif kind == "treasury_xml":
        if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
            raise ValueError("XML entities/doctype prohibited")
        try:
            root = ET.fromstring(data)
        except ET.ParseError:
            raise ValueError("Invalid Treasury XML")
        entries = root.findall("{http://www.w3.org/2005/Atom}entry")
        counts["rows_seen"] = len(entries)
        if not entries:
            raise ValueError("Empty Treasury XML source")
        for entry in entries:
            values = {
                e.tag.split("}")[-1]: (
                    None
                    if e.attrib.get(
                        "{http://schemas.microsoft.com/ado/2007/08/dataservices/metadata}null"
                    )
                    == "true"
                    else e.text
                )
                for e in entry.iter()
            }
            date = values.get("NEW_DATE")
            if not {
                "BC_3MONTH",
                "BC_2YEAR",
                "BC_5YEAR",
                "BC_10YEAR",
                "BC_30YEAR",
            } <= set(values):
                raise ValueError("Treasury XML schema changed")
            unknown = (
                {k for k in values if k.startswith("BC_")}
                - set(XML_MATURITIES)
                - {"BC_30YEARDISPLAY"}
            )
            if unknown:
                raise ValueError(
                    "Unknown Treasury maturities: " + ",".join(sorted(unknown))
                )
            # The official feed repeats the 30-year value for display; it is not a new tenor.
            if "BC_30YEARDISPLAY" in values and number(
                values["BC_30YEARDISPLAY"]
            ) != number(values["BC_30YEAR"]):
                raise ValueError(
                    "Treasury 30-year display alias differs from canonical yield"
                )
            # Atom updated is a source/record update, never assumed original publication.
            local = dict(record, source_updated_at=values.get("updated"))
            for key, label in XML_MATURITIES.items():
                if key in values:
                    counts["observations_seen"] += 1
                    try:
                        r = observation(
                            "UST_" + label,
                            date,
                            values[key],
                            local,
                            "daily",
                            "percentage_points",
                        )
                    except ValueError as exc:
                        counts["invalid_observations"] += 1
                        counts["reason:" + str(exc)] += 1
                        continue
                    if r["value"] is None:
                        counts["missing_values"] += 1
                    rows.append(r)
    elif kind == "sofr_json":
        obj = json.loads(data)
        source = obj.get("refRates")
        if not isinstance(source, list) or len(source) > 400:
            raise ValueError("Unexpected SOFR schema/count; annual requests only")
        for row in source:
            counts["rows_seen"] += 1
            if row.get("type") != "SOFR" or not {"effectiveDate", "percentRate"} <= set(
                row
            ):
                raise ValueError("SOFR schema changed")
            emit(
                "SOFR",
                row["effectiveDate"],
                row["percentRate"],
                "daily",
                "percentage_points",
                row.get("revisionIndicator") or None,
            )
    else:
        raise ValueError("Unsupported source parser")
    if counts["rows_seen"] > 20000 or len(rows) > 250000:
        raise ValueError("Observation/source limit exceeded")
    unique = {}
    for r in rows:
        key = (r["series_id"], r["observation_date"])
        if key in unique:
            if unique[key]["value"] != r["value"]:
                raise ValueError("Conflicting duplicate in one source")
            counts["identical_duplicates"] += 1
        else:
            unique[key] = r
    counts["valid_unique_observations"] = len(unique)
    return list(unique.values()), dict(counts)

# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Bounded streaming event logs; original content is data, never executable code."""

from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import json, csv, hashlib, hmac, io, time, gzip, os
import pyarrow as pa, pyarrow.parquet as pq
from defusedxml.ElementTree import iterparse
from esae.scanner import no_symlink, read_regular
from research_core.http import PublicCache
from research_core import now
from urllib.parse import urlsplit
from . import PARSER_VERSION

META = "https://data.4tu.nl/v2/articles/12715853"
GZIP = "https://icpmconference.org/2019/wp-content/uploads/sites/6/2019/01/log_IEEE.xes_.gz"
FILE = "https://data.4tu.nl/file/35ed7122-966a-484e-a0e1-749b64e3366d/864493d1-3a58-47f6-ad6f-27f95f995828"
LOW = 1514764800000000
HIGH = 1546300800000000
SCHEMA = pa.schema(
    [
        ("case_key", pa.string()),
        ("document_key", pa.string()),
        ("category", pa.string()),
        ("activity", pa.string()),
        ("timestamp_us", pa.int64()),
        ("resource_key", pa.string()),
        ("resource_kind", pa.string()),
        ("lifecycle", pa.string()),
        ("event_hash", pa.string()),
        ("trace_ordinal", pa.int64()),
        ("source_event_ordinal", pa.int32()),
        ("source_row", pa.int64()),
        ("outside_expected_2018", pa.bool_()),
        ("goods_receipt_required", pa.bool_()),
        ("gr_based_invoice", pa.bool_()),
    ]
)


def policy(url):
    p = urlsplit(url)
    if (
        url not in (META, GZIP, FILE)
        or p.scheme != "https"
        or p.username
        or p.password
        or p.fragment
        or p.port not in (None, 443)
    ):
        raise ValueError("Only fixed official BPI HTTPS sources")
    return p


def digest(path):
    return PublicCache.file_hash(no_symlink(Path(path)))


def acquire(root, offline=False, expected=None, cancel=None):
    root = no_symlink(Path(root)).resolve()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    cache = PublicCache(
        root / "cache",
        max_bytes=60_000_000,
        max_response_bytes=25_000_000,
        source_policy=policy,
        organization="4TU.ResearchData / official ICPM2019",
        parser_version=PARSER_VERSION,
        user_agent="MattocciaLabs-OperationsTwin/0.1 public scientific research",
    )
    records = []
    for url in [META, GZIP]:
        p, r = cache.fetch(url, offline=offline, as_path=True)
        if expected:
            previous = next((x for x in expected if x["url"] == url), None)
            if not previous or previous["sha256"] != r["sha256"]:
                raise ValueError("Source vintage differs from pinned manifest")
        records.append(r)
        if url == META:
            meta = json.loads(p.read_text())
        else:
            compressed = p
    if meta["license"]["name"] != "CC BY 4.0" or meta["version"] != 1:
        raise ValueError("Dataset terms/version changed; review required")
    declared = meta["files"][0]
    target = root / "BPI_Challenge_2019.xes"
    no_symlink(target)
    manifest = root / "original.json"
    if target.exists() and not manifest.exists():
        sha = hashlib.sha256()
        md5 = hashlib.md5()
        with target.open("rb") as stream:
            for b in iter(lambda: stream.read(1024 * 1024), b""):
                sha.update(b)
                md5.update(b)
        if (
            target.stat().st_size != declared["size"]
            or md5.hexdigest() != declared["computed_md5"]
        ):
            raise ValueError("Existing source XES differs from official record")
        r = {
            "bytes": target.stat().st_size,
            "sha256": sha.hexdigest(),
            "md5": md5.hexdigest(),
            "official_md5_verified": True,
            "gzip_bytes": compressed.stat().st_size,
        }
        manifest.write_text(json.dumps(r, indent=2) + "\n")
        manifest.chmod(0o600)
    if target.exists() and manifest.exists():
        r = json.loads(read_regular(manifest, 2_000_000))
        if target.stat().st_size != r["bytes"] or digest(target) != r["sha256"]:
            raise ValueError("Original cached XES changed")
    else:
        part = root / "original.part"
        no_symlink(part)
        sha = hashlib.sha256()
        md5 = hashlib.md5()
        n = 0
        with gzip.open(compressed, "rb") as stream, part.open("wb") as out:
            while chunk := stream.read(1024 * 1024):
                if cancel and cancel():
                    raise InterruptedError("Cancelled during bounded decompression")
                n += len(chunk)
                if n > 900_000_000:
                    raise ValueError("Decompressed input limit exceeded")
                out.write(chunk)
                sha.update(chunk)
                md5.update(chunk)
        if n != declared["size"] or md5.hexdigest() != declared["computed_md5"]:
            raise ValueError("Official gzip not byte equivalent to declared4TU XES")
        part.replace(target)
        target.chmod(0o600)
        r = {
            "bytes": n,
            "sha256": sha.hexdigest(),
            "md5": md5.hexdigest(),
            "official_md5_verified": True,
            "gzip_bytes": compressed.stat().st_size,
        }
        manifest.write_text(json.dumps(r, indent=2) + "\n")
        manifest.chmod(0o600)
    return (
        target,
        {
            "dataset": "BPI Challenge2019",
            "doi": meta["doi"],
            "version": meta["version"],
            "author": [x["full_name"] for x in meta["authors"]],
            "publisher": "4TU.ResearchData",
            "license": meta["license"],
            "metadata_url": META,
            "original_file_url": FILE,
            "acquired_at": records[1]["acquired_at"],
            "original": r,
            "sources": records,
            "source_coverage": "2018, declared in official metadata; out-of-period observations audited separately",
            "amounts": "Anonymized monetary values are excluded; no costs/savings inferred",
        },
        cache.network_bytes,
    )


def timestamp(value):
    if not isinstance(value, str) or len(value) > 80:
        raise ValueError("invalid_timestamp")
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        raise ValueError("invalid_timestamp")
    if d.tzinfo is None:
        raise ValueError("timezone_missing")
    d = d.astimezone(timezone.utc)
    if not 1900 <= d.year <= 2100:
        raise ValueError("timestamp_outside_supported_years")
    # Integer arithmetic avoids float epoch rounding; source milliseconds retained.
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    delta = d - epoch
    return delta.days * 86400000000 + delta.seconds * 1000000 + delta.microseconds


def xes_traces(path, max_events=5_000_000):
    count = 0
    trace = 0
    root = None

    class WindowReader:
        def __init__(self, handle):
            self.handle = handle
            self.window = 0

        def read(self, size=-1):
            b = self.handle.read(size)
            self.window += len(b)
            if self.window > 8 * 1024 * 1024:
                raise ValueError("XES trace/metadata byte budget exceeded")
            return b

    with path.open("rb") as handle:
        stream = WindowReader(handle)
        for kind, e in iterparse(
            stream,
            events=("start", "end"),
            forbid_dtd=True,
            forbid_entities=True,
            forbid_external=True,
        ):
            tag = e.tag.rsplit("}", 1)[-1]
            if root is None and kind == "start":
                root = e
            if kind == "end" and tag == "trace":
                trace += 1
                attrs = {}
                events = []
                for child in e:
                    typ = child.tag.rsplit("}", 1)[-1]
                    if typ == "event":
                        if len(child) > 100:
                            raise ValueError("XES attribute count limit exceeded")
                        values = {}
                        for v in child:
                            key = v.attrib.get("key")
                            value = v.attrib.get("value")
                            if (
                                key
                                and len(key) <= 200
                                and isinstance(value, str)
                                and len(value) <= 16384
                            ):
                                values[key] = (v.tag.rsplit("}", 1)[-1], value)
                            elif key:
                                raise ValueError("Oversized/unsupported XES attribute")
                        events.append(values)
                        count += 1
                        if count > max_events or len(events) > 20000:
                            raise ValueError("Event/trace input limit exceeded")
                    elif child.attrib.get("key"):
                        key = child.attrib["key"]
                        value = child.attrib.get("value", "")
                        if len(key) > 200 or len(value) > 16384 or len(attrs) > 100:
                            raise ValueError("XES trace attribute limit exceeded")
                        attrs[key] = value
                yield trace, attrs, events
                e.clear()
                if root is not None:
                    root.remove(e)
                stream.window = 0


def flat_rows(path, format):
    def convert(row):
        if (
            not isinstance(row, dict)
            or len(row) > 100
            or sum(len(str(v)) for v in row.values()) > 1024 * 1024
        ):
            raise ValueError("Bounded structured event object required")
        return {
            str(k): ("string", str(v))
            for k, v in row.items()
            if v is not None and isinstance(v, (str, int, float, bool, datetime))
        }

    if format == "csv":
        csv.field_size_limit(1024 * 1024)
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                yield convert(row)
    elif format == "parquet":
        pf = pq.ParquetFile(path)
        if len(pf.schema) > 100 or pf.metadata.num_rows > 5_000_000:
            raise ValueError("Parquet schema/row bound")
        for batch in pf.iter_batches(batch_size=10000):
            for row in batch.to_pylist():
                yield convert(row)
    elif format == "jsonl":
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if len(line) > 1024 * 1024:
                    raise ValueError("JSON record bound")
                if line.strip():
                    yield convert(json.loads(line))
    elif format == "json":
        value = json.loads(read_regular(path, 5_000_000))
        value = value.get("events") if isinstance(value, dict) else value
        if not isinstance(value, list):
            raise ValueError("JSON array or events array required")
        for row in value:
            yield convert(row)
    else:
        raise ValueError("Supported log formats: xes/csv/jsonl/json/parquet")


def normalize(
    path,
    folder,
    format="xes",
    mapping=None,
    drop_resources=False,
    privacy_key=None,
    progress=None,
    cancel=None,
    expected_sha=None,
    expected_events=0,
):
    start = time.monotonic()
    path = no_symlink(Path(path)).resolve()
    if not path.is_file() or path.stat().st_size > 1_000_000_000:
        raise ValueError("Bounded regular event log required")
    source_sha = digest(path)
    if expected_sha and source_sha != expected_sha:
        raise ValueError("Source input hash differs")
    key = privacy_key if privacy_key is not None else bytes.fromhex(source_sha)
    if not isinstance(key, bytes) or len(key) < 16:
        raise ValueError("Pseudonymization key must be bytes of at least16bytes")

    def pseudonym(namespace, v):
        return (
            hmac.new(
                key, (namespace + ":" + str(v)).encode(), hashlib.sha256
            ).hexdigest()[:32]
            if v not in (None, "")
            else None
        )

    defaults = {
        "case_id": "case_id",
        "activity": "activity",
        "timestamp": "timestamp",
        "resource": "resource",
        "lifecycle": "lifecycle",
        "category": "category",
        "document": "document_id",
    }
    if mapping and (
        set(mapping) - set(defaults)
        or any(not isinstance(v, str) or len(v) > 200 for v in mapping.values())
    ):
        raise ValueError("Known field mappings required")
    mapping = {**defaults, **(mapping or {})}
    profile = {
        "format": format,
        "mapping": mapping,
        "drop_resources": drop_resources,
        "privacy_profile_sha256": hashlib.sha256(key).hexdigest(),
        "parser_version": PARSER_VERSION,
    }
    folder = no_symlink(Path(folder))
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    state = folder / "import-state.json"
    complete = folder / "import-manifest.json"
    if complete.exists():
        old = json.loads(read_regular(complete, 5_000_000))
        if old["input_sha256"] != source_sha or old["profile"] != profile:
            raise ValueError("Normalized cache has a different source/profile")
        for f in old["parts"]:
            if digest(folder / f["file"]) != f["sha256"]:
                raise ValueError("Normalized Parquet changed")
        return old
    saved = json.loads(read_regular(state, 5_000_000)) if state.exists() else None
    if saved and (saved["input_sha256"] != source_sha or saved["profile"] != profile):
        raise ValueError("Cannot resume a different input/profile")
    counters = Counter(saved["counts"]) if saved else Counter()
    parts = saved["parts"] if saved else []
    committed = saved["committed_unit"] if saved else 0
    pending = []
    unit = 0
    for part in parts:
        if digest(folder / part["file"]) != part["sha256"]:
            raise ValueError("Committed normalized partition changed")

    def flush(unit):
        nonlocal pending
        if pending:
            number = len(parts)
            dest = folder / ("part-" + str(number).zfill(5) + ".parquet")
            temp = folder / (dest.name + ".part")
            no_symlink(temp)
            pq.write_table(
                pa.Table.from_pylist(pending, schema=SCHEMA),
                temp,
                compression="zstd",
                use_dictionary=True,
            )
            temp.replace(dest)
            dest.chmod(0o600)
            parts.append(
                {
                    "file": dest.name,
                    "rows": len(pending),
                    "bytes": dest.stat().st_size,
                    "sha256": digest(dest),
                }
            )
            pending = []
        data = {
            "input_sha256": source_sha,
            "profile": profile,
            "counts": dict(counters),
            "parts": parts,
            "committed_unit": unit,
        }
        tmp = folder / "import-state.new.json"
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(state)
        state.chmod(0o600)

    def add(rawcase, attrs, events, trace_id):
        counters["source_cases_or_rows"] += 1
        case = pseudonym("case", rawcase)
        document = pseudonym(
            "document", attrs.get("Purchasing Document", attrs.get(mapping["document"]))
        )
        category = (
            attrs.get("Item Category", attrs.get(mapping["category"])) or "UNKNOWN"
        )
        for n, event in enumerate(events):
            counters["source_events"] += 1
            get = lambda k: event[k][1] if k in event else None
            act = get("concept:name" if format == "xes" else mapping["activity"])
            timevalue = get(
                "time:timestamp" if format == "xes" else mapping["timestamp"]
            )
            if not case:
                counters["excluded_missing_case_id"] += 1
                continue
            if not act or len(act) > 200:
                counters["excluded_missing_or_long_activity"] += 1
                continue
            try:
                ts = timestamp(timevalue)
            except ValueError as e:
                counters["excluded_" + str(e)] += 1
                continue
            resource = get("org:resource" if format == "xes" else mapping["resource"])
            missing = resource is None or resource.strip().lower() in (
                "",
                "none",
                "null",
                "nan",
            )
            lifecycle = get(
                "lifecycle:transition" if format == "xes" else mapping["lifecycle"]
            )
            if missing:
                counters["missing_resource_events"] += 1
            if not lifecycle:
                counters["missing_lifecycle_events"] += 1
            outside = not LOW <= ts < HIGH
            if outside:
                counters["events_outside_declared_2018"] += 1
            attrs_hash = hashlib.sha256(
                json.dumps(event, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            flag = lambda v: (
                True
                if str(v).lower() == "true"
                else False if str(v).lower() == "false" else None
            )
            pending.append(
                {
                    "case_key": case,
                    "document_key": document,
                    "category": category,
                    "activity": act,
                    "timestamp_us": ts,
                    "resource_key": (
                        None
                        if missing or drop_resources
                        else pseudonym("resource", resource)
                    ),
                    "resource_kind": (
                        "missing"
                        if missing
                        else (
                            "batch"
                            if resource.lower().startswith("batch")
                            else "reported"
                        )
                    ),
                    "lifecycle": lifecycle,
                    "event_hash": attrs_hash,
                    "trace_ordinal": trace_id,
                    "source_event_ordinal": n,
                    "source_row": counters["source_events"],
                    "outside_expected_2018": outside,
                    "goods_receipt_required": flag(attrs.get("Goods Receipt")),
                    "gr_based_invoice": flag(attrs.get("GR-Based Inv. Verif.")),
                }
            )
            counters["imported_events"] += 1

    if format == "xes":
        for unit, attrs, events in xes_traces(path):
            if unit <= committed:
                continue
            if cancel and cancel():
                raise InterruptedError(
                    "Cancelled between complete source traces; committed partitions preserved"
                )
            add(attrs.get("concept:name"), attrs, events, unit)
            if len(pending) >= 10000:
                flush(unit)
                if progress:
                    progress(
                        "Streaming XES to verified Parquet",
                        counters["source_events"],
                        expected_events,
                    )
    else:
        for unit, event in enumerate(flat_rows(path, format), 1):
            if unit > 5_000_000:
                raise ValueError("Event row limit exceeded")
            if unit <= committed:
                continue
            if cancel and cancel():
                raise InterruptedError("Cancelled between structured records")
            attrs = {k: v[1] for k, v in event.items()}
            add(attrs.get(mapping["case_id"]), attrs, [event], unit)
            if len(pending) >= 10000:
                flush(unit)
    flush(unit)
    result = {
        "input_sha256": source_sha,
        "parser_version": PARSER_VERSION,
        "profile": profile,
        "counts": dict(counters),
        "parts": parts,
        "original_bytes_unchanged": True,
        "elapsed_seconds": time.monotonic() - start,
        "rules": "Explicit UTC parsing; required-field exclusions counted; out-of2018timestamps retained and flagged; exact duplicate candidates retained; raw attributes/amounts/vendor names not exported",
        "privacy": "HMAC pseudonyms; default public dataset hash is not a secret anonymity guarantee. Private authorized logs can supply a private key or remove resources; no employee ranking.",
    }
    complete.write_text(json.dumps(result, indent=2) + "\n")
    complete.chmod(0o600)
    return result

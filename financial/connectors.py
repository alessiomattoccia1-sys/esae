# SPDX-License-Identifier: Apache-2.0
"""Official bounded downloads with immutable acquisition snapshots, no credentials."""

from pathlib import Path
from urllib.parse import urlsplit, parse_qs
import hashlib, json, os, datetime, shutil, re
from research_core.http import PublicCache
from esae.scanner import no_symlink
from . import PARSER_VERSION

TREASURY_ARCHIVE = (
    "https://home.treasury.gov/system/files/276/yield-curve-rates-1990-2024.csv"
)
NFCI_CSV = "https://api.data.chicagofed.org/NFCI/nfci-data-series-csv.csv"
NYFED_TERMS = "https://www.newyorkfed.org/privacy/termsofuse"
CHICAGO_TERMS = "https://www.chicagofed.org/utilities/legal-notices"
SOURCES = {
    "treasury": {
        "name": "U.S. Department of the Treasury",
        "unit": "percentage_points",
        "frequency": "daily_business_sessions",
        "url": "https://home.treasury.gov/treasury-daily-interest-rate-xml-feed",
        "terms": "https://home.treasury.gov/subfooter/privacy-policy",
    },
    "chicago": {
        "name": "Federal Reserve Bank of Chicago",
        "unit": "standardized_index",
        "frequency": "weekly_Friday_reference",
        "url": "https://www.chicagofed.org/research/data/nfci/current-data",
        "terms": CHICAGO_TERMS,
    },
    "newyork": {
        "name": "Federal Reserve Bank of New York",
        "unit": "percentage_points",
        "frequency": "daily_business_sessions",
        "url": "https://markets.newyorkfed.org/static/docs/markets-api.html",
        "terms": NYFED_TERMS,
    },
}
FUTURE_CONNECTORS = {
    "FRED_ALFRED": {
        "implemented": False,
        "requires_environment_api_key": True,
        "configured": bool(os.environ.get("FRED_API_KEY")),
    },
    "ECB_SDMX": {
        "implemented": True,
        "phase": "second-phase USD/EUR connector; outside FSIE-001",
    },
    "SEC_EDGAR": {
        "implemented": False,
        "requires_identified_client_and_rate_policy": True,
    },
}


def source_policy(url):
    p = urlsplit(url)
    q = parse_qs(p.query, keep_blank_values=True)
    allowed = False
    if (
        p.scheme != "https"
        or p.username
        or p.password
        or p.fragment
        or p.port not in (None, 443)
    ):
        raise ValueError("Official HTTPS sources only")
    if p.hostname == "home.treasury.gov":
        if p.path == "/system/files/276/yield-curve-rates-1990-2024.csv" and not q:
            allowed = True
        if (
            p.path == "/resource-center/data-chart-center/interest-rates/pages/xml"
            and set(q) == {"data", "field_tdr_date_value"}
            and q["data"] == ["daily_treasury_yield_curve"]
        ):
            try:
                allowed = (
                    2000 <= int(q["field_tdr_date_value"][0]) <= 2100
                    and len(q["field_tdr_date_value"]) == 1
                )
            except ValueError:
                pass
    elif (
        p.hostname == "api.data.chicagofed.org"
        and p.path == "/NFCI/nfci-data-series-csv.csv"
        and not q
    ):
        allowed = True
    elif (
        p.hostname == "markets.newyorkfed.org"
        and p.path == "/api/rates/secured/sofr/search.json"
        and set(q) == {"startDate", "endDate"}
    ):
        try:
            a = datetime.date.fromisoformat(q["startDate"][0])
            b = datetime.date.fromisoformat(q["endDate"][0])
            allowed = (
                len(q["startDate"]) == len(q["endDate"]) == 1
                and 0 <= (b - a).days <= 366
                and a >= datetime.date(2018, 1, 1)
            )
        except (ValueError, IndexError):
            pass
    if not allowed:
        raise ValueError("Source URL not in financial allowlist")
    return p


class FinancialCache:
    def __init__(self, root, max_bytes=80_000_000):
        self.root = no_symlink(Path(root)).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.blobs = self.root / "blobs"
        no_symlink(self.blobs)
        self.blobs.mkdir(exist_ok=True)
        self.transport = PublicCache(
            self.root / "transport",
            max_bytes=max_bytes,
            max_response_bytes=12_000_000,
            retries=3,
            source_policy=source_policy,
            organization="Official financial institution; see source_id",
            parser_version=PARSER_VERSION,
            user_agent="MattocciaLabs-ResearchEngines-FSIE/0.1 (public scientific research; https://mattoccia.com/contatti/)",
        )

    def fetch(self, url, *, refresh=False):
        path, metadata = self.transport.fetch(url, refresh=refresh, as_path=True)
        blob = self.blobs / (metadata["sha256"] + ".data")
        no_symlink(blob)
        if not blob.exists():
            os.link(path, blob)
            blob.chmod(0o600)
        if self.transport.file_hash(blob) != metadata["sha256"]:
            raise ValueError("Immutable source hash mismatch")
        record = dict(metadata)
        record["source_id"] = (
            "treasury"
            if urlsplit(url).hostname == "home.treasury.gov"
            else "chicago" if "chicagofed" in url else "newyork"
        )
        record["organization"] = SOURCES[record["source_id"]]["name"]
        record["vintage_kind"] = "acquisition_snapshot_not_historical_realtime_vintage"
        record["publication_at"] = None
        history = self.root / "metadata"
        no_symlink(history)
        history.mkdir(exist_ok=True)
        dest = history / (
            hashlib.sha256((url + record["acquired_at"]).encode()).hexdigest() + ".json"
        )
        if not dest.exists():
            dest.write_text(json.dumps(record, indent=2) + "\n")
        return blob, record

    def frozen(self, record):
        source_policy(record["url"])
        if not re.fullmatch("[a-f0-9]{64}", record["sha256"]):
            raise ValueError("Invalid source digest")
        path = self.blobs / (record["sha256"] + ".data")
        no_symlink(path)
        if not path.is_file() or self.transport.file_hash(path) != record["sha256"]:
            raise ValueError("Frozen source absent or modified")
        return path


class InstitutionalConnector:
    def __init__(self, cache):
        self.cache = cache

    def plan(self, end):
        end = datetime.date.fromisoformat(end)
        if (
            not datetime.date(2000, 1, 1)
            <= end
            <= datetime.datetime.now(datetime.timezone.utc).date()
        ):
            raise ValueError("Study end must be historical or current, not future")
        urls = [("treasury_csv", TREASURY_ARCHIVE)]
        urls += [
            (
                "treasury_xml",
                "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value="
                + str(y),
            )
            for y in range(2025, end.year + 1)
        ]
        urls.append(("nfci_csv", NFCI_CSV))
        for year in range(2018, end.year + 1):
            start = max(datetime.date(year, 1, 1), datetime.date(2018, 4, 2))
            stop = min(datetime.date(year, 12, 31), end)
            if start <= stop:
                urls.append(
                    (
                        "sofr_json",
                        "https://markets.newyorkfed.org/api/rates/secured/sofr/search.json?startDate="
                        + start.isoformat()
                        + "&endDate="
                        + stop.isoformat(),
                    )
                )
        return urls

    def acquire(self, end, *, refresh=False, frozen=None, progress=None):
        records = []
        for i, (kind, url) in enumerate(self.plan(end)):
            previous = next(
                (r for r in frozen or [] if r["url"] == url and r["parser"] == kind),
                None,
            )
            if previous:
                path = self.cache.frozen(previous)
                record = previous
            else:
                path, record = self.cache.fetch(url, refresh=refresh)
                record.update(parser=kind, schema_version=PARSER_VERSION)
            records.append(record)
            if progress:
                progress(records, i + 1, len(self.plan(end)))
        return records


def import_official_file(path, source_url, parser, cache):
    """Explicit local fallback: provenance is user-supplied, not authenticated HTTP."""
    source_policy(source_url)
    path = no_symlink(Path(path)).resolve()
    if (
        parser not in ("treasury_csv", "treasury_xml", "nfci_csv", "sofr_json")
        or not path.is_file()
        or not 0 < path.stat().st_size <= 12_000_000
    ):
        raise ValueError("Bounded official file and known parser required")
    from research_core import now

    digest = PublicCache.file_hash(path)
    dest = cache.blobs / (digest + ".data")
    no_symlink(dest)
    if not dest.exists():
        shutil.copyfile(path, dest)
        dest.chmod(0o600)
    host = urlsplit(source_url).hostname
    source_id = (
        "treasury"
        if host == "home.treasury.gov"
        else "chicago" if host == "api.data.chicagofed.org" else "newyork"
    )
    expected = (
        "treasury_csv"
        if source_url == TREASURY_ARCHIVE
        else (
            "treasury_xml"
            if source_id == "treasury"
            else "nfci_csv" if source_id == "chicago" else "sofr_json"
        )
    )
    if parser != expected:
        raise ValueError("Declared parser does not match official source URL")
    return {
        "source_id": source_id,
        "organization": SOURCES[source_id]["name"],
        "url": source_url,
        "sha256": digest,
        "bytes": path.stat().st_size,
        "parser": parser,
        "acquired_at": now(),
        "acquisition_kind": "manual_official_file_origin_not_independently_authenticated",
        "publication_at": None,
        "vintage_kind": "acquisition_snapshot",
        "parser_version": PARSER_VERSION,
    }

# SPDX-License-Identifier: Apache-2.0
"""Second-phase ECB SDMX supplement, separate from FSIE-001 inference."""

import csv, datetime, io
from urllib.parse import urlsplit, parse_qs, urlencode
from research_core.http import PublicCache
from .parsers import day, number

TERMS = (
    "https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html"
)


def policy(url):
    p = urlsplit(url)
    q = parse_qs(p.query)
    if (
        p.scheme != "https"
        or p.hostname != "data-api.ecb.europa.eu"
        or p.port not in (None, 443)
        or p.username
        or p.password
        or p.fragment
        or p.path != "/service/data/EXR/D.USD.EUR.SP00.A"
        or set(q) != {"startPeriod", "endPeriod", "format"}
        or q["format"] != ["csvdata"]
    ):
        raise ValueError("Bounded official ECB USD/EUR SDMX source only")
    if any(len(v) != 1 for v in q.values()):
        raise ValueError("One value per parameter")
    a = datetime.date.fromisoformat(q["startPeriod"][0])
    b = datetime.date.fromisoformat(q["endPeriod"][0])
    if (
        not datetime.date(1999, 1, 1)
        <= a
        <= b
        <= datetime.datetime.now(datetime.timezone.utc).date()
        or (b - a).days > 366
    ):
        raise ValueError("ECB supplement limited to one historical year")
    return p


def parse(data):
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")))
    if not {
        "KEY",
        "TIME_PERIOD",
        "OBS_VALUE",
        "UNIT",
        "UNIT_MULT",
        "CURRENCY",
        "CURRENCY_DENOM",
        "FREQ",
    } <= set(reader.fieldnames or []):
        raise ValueError("ECB SDMX CSV schema changed")
    rows = {}
    for r in reader:
        if (
            r["KEY"] != "EXR.D.USD.EUR.SP00.A"
            or r["UNIT"] != "USD"
            or r["UNIT_MULT"] != "0"
            or r["CURRENCY"] != "USD"
            or r["CURRENCY_DENOM"] != "EUR"
            or r["FREQ"] != "D"
        ):
            raise ValueError("ECB series identity or unit changed")
        d = day(r["TIME_PERIOD"])
        v = number(r["OBS_VALUE"])
        if d in rows and rows[d]["value"] != v:
            raise ValueError("Conflicting ECB date")
        rows[d] = {
            "series_id": r["KEY"],
            "observation_date": d,
            "value": v,
            "unit": "USD_per_EUR",
            "publication_at": None,
            "status": r.get("OBS_STATUS"),
        }
        if len(rows) > 370:
            raise ValueError("ECB count bound exceeded")
    if not rows:
        raise ValueError("Empty ECB response")
    return [rows[d] for d in sorted(rows)]


class ECBConnector:
    def __init__(self, root):
        self.cache = PublicCache(
            root,
            max_bytes=2000000,
            max_response_bytes=1000000,
            source_policy=policy,
            organization="European Central Bank",
            parser_version="fsie-ecb-sdmx-1.0",
            user_agent="MattocciaLabs-FSIE/0.1 public research",
        )

    def acquire(self, start, end):
        url = (
            "https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?"
            + urlencode({"startPeriod": start, "endPeriod": end, "format": "csvdata"})
        )
        data, source = self.cache.fetch(url)
        rows = parse(data)
        return {
            "source": source,
            "terms": TERMS,
            "series": "EXR.D.USD.EUR.SP00.A",
            "observations": len(rows),
            "period": {
                "start": rows[0]["observation_date"],
                "end": rows[-1]["observation_date"],
            },
            "unit": "USD_per_EUR",
            "scope": "Second-phase connector qualification only; not part of FSIE-001 results or financial-stress inference",
            "data": rows,
        }

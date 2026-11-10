# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Official metadata and bounded anonymous ZIP subsets; no full archive fallback."""

from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
import httpx, json, hashlib, time, struct, zlib, binascii, stat, os
from research_core.http import PublicCache
from research_core import now
from esae.scanner import no_symlink
from . import PARSER_VERSION

ZENODO_META = "https://zenodo.org/api/records/16992976"
IDF_ZIP = (
    "https://zenodo.org/api/records/16992976/files/Speedybee%20DataSet.zip/content"
)
DRYAD_META = "https://datadryad.org/api/v2/datasets/doi%3A10.5061%2Fdryad.7d7wm3898"
DRYAD_PAGE = "https://datadryad.org/dataset/doi%3A10.5061/dryad.7d7wm3898?public=true"
DRYAD_ZIP = "https://datadryad.org/downloads/file_stream/4651889"
MILUV_META = "https://api.figshare.com/v2/articles/28386041"
MILUV_FILES = {52250714, 52250702, 52250735}


def policy(url):
    p = urlsplit(url)
    if (
        p.scheme != "https"
        or p.username
        or p.password
        or p.port not in (None, 443)
        or p.fragment
    ):
        raise ValueError("Uncredentialed official HTTPS only")
    if p.hostname == "zenodo.org" and (
        p.path == "/api/records/16992976"
        or p.path.startswith("/api/records/16992976/files/")
        or p.path.startswith("/records/16992976/files/")
    ):
        return p
    if p.hostname == "datadryad.org" and (
        url in (DRYAD_META, DRYAD_PAGE, DRYAD_ZIP)
        or p.path
        in (
            "/api/v2/versions/430761",
            "/api/v2/versions/430761/files",
            "/downloads/file_stream/4651901",
            "/api/v2/files/4651901",
            "/api/v2/files/4651889",
        )
    ):
        return p
    if url == MILUV_META or (
        p.hostname == "ndownloader.figshare.com"
        and p.path in {f"/files/{i}" for i in MILUV_FILES}
    ):
        return p
    if (
        p.hostname == "raw.githubusercontent.com"
        and p.path.startswith("/decargroup/miluv/")
        and p.path.endswith((".yaml", ".csv", ".md", ".py"))
    ):
        return p
    raise ValueError("Outside Dynamics official source policy")


class DataCache:
    def __init__(self, root, limit=100_000_000):
        self.root = no_symlink(Path(root)).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.blobs = self.root / "blobs"
        self.blobs.mkdir(exist_ok=True)
        self.transport = PublicCache(
            self.root / "metadata",
            max_bytes=limit,
            max_response_bytes=8_000_000,
            source_policy=policy,
            organization="Zenodo IDF_DS / Dryad AERPAW",
            parser_version=PARSER_VERSION,
            user_agent="MattocciaLabs-DynamicsLab/0.1 civil retrospective mathematical research",
        )
        self.records = {}
        self.expected = None
        self.allow_missing = False
        self.limit = limit
        self.downloaded = 0
        self.on_record = None

    def remember(self, r):
        self.records[r["key"]] = r
        if self.on_record:
            self.on_record(list(self.records.values()))

    def frozen(self, r):
        policy(r["url"])
        digest = r["sha256"]
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("Invalid source digest")
        p = no_symlink(self.blobs / (digest + ".data"))
        if not p.is_file() or PublicCache.file_hash(p) != digest:
            raise ValueError("Frozen acquired bytes missing or changed")
        return p

    def fetch(self, url, offline=False):
        key = url
        if self.expected is not None:
            if key not in self.expected and not self.allow_missing:
                raise ValueError("Source absent from pinned manifest")
            if key in self.expected:
                r = self.expected[key]
                p = self.frozen(r)
                self.remember(r)
                return p, r
        p, r = self.transport.fetch(url, offline=offline, as_path=True)
        r = dict(r, key=key)
        dest = self.blobs / (r["sha256"] + ".data")
        if not dest.exists():
            os.link(p, dest)
        self.remember(r)
        return dest, r

    def range(self, url, start, end, total, offline=False):
        policy(url)
        if not 0 <= start <= end < total or end - start + 1 > 16_000_000:
            raise ValueError("Bounded archive range required")
        key = url + "|bytes=" + str(start) + "-" + str(end)
        meta = self.root / (hashlib.sha256(key.encode()).hexdigest() + ".json")
        if self.expected is not None:
            if key not in self.expected and not self.allow_missing:
                raise ValueError("Range absent from pinned manifest")
            if key in self.expected:
                r = self.expected[key]
                p = self.frozen(r)
                self.remember(r)
                return p.read_bytes(), r
        if meta.is_file():
            r = json.loads(meta.read_text())
            p = self.frozen(r)
            self.remember(r)
            return p.read_bytes(), r
        if offline:
            raise ValueError("Offline source range unavailable")
        for attempt in range(3):
            try:
                with httpx.Client(
                    timeout=40, trust_env=False, follow_redirects=False
                ) as c:
                    with c.stream(
                        "GET",
                        url,
                        headers={
                            "Range": f"bytes={start}-{end}",
                            "Accept-Encoding": "identity",
                            "User-Agent": "MattocciaLabs-DynamicsLab/0.1",
                        },
                    ) as response:
                        # Follow the publisher's ordinary signed download redirect only.
                        # The transient query is neither persisted nor published.
                        if (
                            response.status_code in (301, 302, 303, 307, 308)
                            and urlsplit(url).hostname == "ndownloader.figshare.com"
                        ):
                            location = response.headers.get("location", "")
                            target = urlsplit(location)
                            if (
                                target.scheme != "https"
                                or target.hostname != "s3-eu-west-1.amazonaws.com"
                                or not target.path.startswith(
                                    "/pstorage-plus-7003492043/"
                                )
                                or target.username
                                or target.port not in (None, 443)
                            ):
                                raise ValueError(
                                    "Unrecognized publisher download redirect"
                                )
                            with c.stream(
                                "GET",
                                location,
                                headers={
                                    "Range": f"bytes={start}-{end}",
                                    "Accept-Encoding": "identity",
                                },
                            ) as redirected:
                                return self._range_response(
                                    redirected, url, key, start, end, total, meta
                                )
                        return self._range_response(
                            response, url, key, start, end, total, meta
                        )
            except httpx.HTTPError:
                if attempt == 2:
                    raise
                time.sleep(2**attempt)

    def _range_response(self, response, url, key, start, end, total, meta):
        if response.status_code in (401, 403):
            raise ValueError(
                "Official source access unavailable; no protection bypass or full archive fallback"
            )
        if (
            response.status_code != 206
            or response.headers.get("content-range") != f"bytes {start}-{end}/{total}"
        ):
            raise ValueError("Source does not honor exact bounded ranges")
        b = b""
        for chunk in response.iter_bytes():
            b += chunk
            self.downloaded += len(chunk)
            if len(b) > end - start + 1 or self.downloaded > self.limit:
                raise ValueError("Download budget exceeded")
        if len(b) != end - start + 1:
            raise ValueError("Incomplete archive range")
        r = {
            "key": key,
            "url": url,
            "range": [start, end],
            "archive_bytes": total,
            "bytes": len(b),
            "sha256": hashlib.sha256(b).hexdigest(),
            "etag": response.headers.get("etag"),
            "last_modified": response.headers.get("last-modified"),
            "acquired_at": now(),
            "http_status": 206,
            "parser_version": PARSER_VERSION,
            "whole_archive_checksum_verified": False,
        }
        p = self.blobs / (r["sha256"] + ".data")
        no_symlink(p)
        if not p.exists():
            p.write_bytes(b)
        meta.write_text(json.dumps(r, indent=2) + "\n")
        self.remember(r)
        return b, r


class RemoteZip:
    def __init__(self, cache, url, size, offline=False):
        self.cache = cache
        self.url = url
        self.size = size
        self.offline = offline
        self.validators = []

    def read(self, a, b):
        raw, record = self.cache.range(self.url, a, b, self.size, self.offline)
        validator = record.get("etag") or record.get("last_modified")
        if validator and self.validators and validator != self.validators[0]:
            raise ValueError("Archive changed between range reads")
        if validator:
            self.validators.append(validator)
        return raw

    def inventory(self):
        a = max(0, self.size - 131072)
        tail = self.read(a, self.size - 1)
        pos = tail.rfind(b"PK\x05\x06")
        if pos < 0:
            raise ValueError("ZIP end record missing")
        e = struct.unpack_from("<4s4H2IH", tail, pos)
        count = e[4]
        cdsize, offset = e[5:7]
        if offset == 0xFFFFFFFF or cdsize == 0xFFFFFFFF or count == 65535:
            loc = tail.rfind(b"PK\x06\x07", 0, pos)
            if loc < 0:
                raise ValueError("ZIP64 locator missing")
            _, disk, eo64, disks = struct.unpack_from("<4sIQI", tail, loc)
            if disk or disks != 1:
                raise ValueError("Multi-volume ZIP unsupported")
            b = self.read(eo64, eo64 + 55)
            f = struct.unpack("<4sQ2H2I4Q", b)
            count = f[7]
            cdsize = f[8]
            offset = f[9]
        if not 0 < count <= 50000 or not 0 < cdsize <= 8_000_000:
            raise ValueError("Archive directory bound")
        data = self.read(offset, offset + cdsize - 1)
        rows = []
        i = 0
        seen = set()
        while i < len(data):
            f = struct.unpack_from("<4s6H3I5H2I", data, i)
            if f[0] != b"PK\x01\x02":
                raise ValueError("Malformed archive directory")
            fn, ex, co = f[10:13]
            name = data[i + 46 : i + 46 + fn].decode(
                "utf-8" if f[3] & 2048 else "cp437"
            )
            p = PurePosixPath(name)
            if (
                p.is_absolute()
                or ".." in p.parts
                or "\\" in name
                or ":" in name
                or "\x00" in name
                or name in seen
                or stat.S_ISLNK(f[15] >> 16)
            ):
                raise ValueError("Unsafe archive path/type")
            seen.add(name)
            expanded, compressed, entryoffset = f[9], f[8], f[-1]
            extra = data[i + 46 + fn : i + 46 + fn + ex]
            j = 0
            while j + 4 <= len(extra):
                typ, length = struct.unpack_from("<HH", extra, j)
                values = extra[j + 4 : j + 4 + length]
                j += 4 + length
                if typ == 1:
                    k = 0
                    if expanded == 0xFFFFFFFF:
                        expanded = struct.unpack_from("<Q", values, k)[0]
                        k += 8
                    if compressed == 0xFFFFFFFF:
                        compressed = struct.unpack_from("<Q", values, k)[0]
                        k += 8
                    if entryoffset == 0xFFFFFFFF:
                        entryoffset = struct.unpack_from("<Q", values, k)[0]
            rows.append(
                {
                    "name": name,
                    "compressed": compressed,
                    "expanded": expanded,
                    "offset": entryoffset,
                    "method": f[4],
                    "flags": f[3],
                    "crc32": f[7],
                }
            )
            i += 46 + fn + ex + co
        if len(rows) != count:
            raise ValueError("ZIP directory count mismatch")
        return rows

    def member(self, row):
        if (
            row["flags"] & 1
            or row["method"] not in (0, 8)
            or not 0 < row["compressed"] <= 15_000_000
            or row["expanded"] > 80_000_000
            or row["expanded"] / row["compressed"] > 1000
        ):
            raise ValueError("Selected ZIP member resource/encryption bound")
        a = row["offset"]
        h = self.read(a, a + 29)
        fields = struct.unpack("<4s5H3I2H", h)
        if fields[0] != b"PK\x03\x04" or fields[3] != row["method"]:
            raise ValueError("Local/central ZIP header mismatch")
        start = a + 30 + fields[-2] + fields[-1]
        raw = self.read(start, start + row["compressed"] - 1)
        if row["method"] == 8:
            d = zlib.decompressobj(-15)
            out = d.decompress(raw, row["expanded"] + 1)
            if len(out) > row["expanded"] or d.unconsumed_tail or not d.eof:
                raise ValueError("Invalid/excessive compressed member")
        else:
            out = raw
        if (
            len(out) != row["expanded"]
            or binascii.crc32(out) & 0xFFFFFFFF != row["crc32"]
        ):
            raise ValueError("Selected archive member CRC/size mismatch")
        return out

# SPDX-License-Identifier: Apache-2.0
"""Allowlisted anonymous official data; immutable bytes and bounded resource use."""

from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
import re, json, os, hashlib, threading
from research_core.http import PublicCache
from esae.scanner import no_symlink
from . import PARSER_VERSION

MAST_ROOT = "https://s3.echo.stfc.ac.uk/mast/"
STFC_ITEM = "https://edata.stfc.ac.uk/server/api/core/items/e7a22beb-f55a-45a0-a0c7-bca8eb94d849"
STFC_CONTENT = "https://edata.stfc.ac.uk/server/api/core/bitstreams/bf56f40c-f70b-4bad-af69-5e6e65ea2a71/content"
STFC_ZIP = (
    "https://edata.stfc.ac.uk/bitstreams/bf56f40c-f70b-4bad-af69-5e6e65ea2a71/download"
)
LICENSE_MAST = "https://creativecommons.org/licenses/by-sa/4.0/"
LICENSE_STFC = "https://creativecommons.org/licenses/by/4.0/"


def policy(url):
    p = urlsplit(url)
    if (
        p.scheme != "https"
        or p.port not in (None, 443)
        or p.username
        or p.password
        or p.fragment
        or p.query
    ):
        raise ValueError("Official uncredentialed HTTPS objects only")
    if p.hostname == "s3.echo.stfc.ac.uk":
        if re.fullmatch(
            r"/mast/fairmast-meta/(?:l[12]_(?:shots|sources)\.parquet|l[12]_signals/signals_\d{4,6}\.parquet)",
            p.path,
        ):
            return p
        if (
            re.fullmatch(
                r"/mast/level[12]/shots/\d{4,6}\.zarr/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+",
                p.path,
            )
            and ".." not in PurePosixPath(p.path).parts
        ):
            return p
    if url in (STFC_ITEM, STFC_ZIP, STFC_CONTENT):
        return p
    raise ValueError("URL outside selected FAIR-MAST/STFC policy")


class FusionCache:
    def __init__(self, root, max_bytes=512_000_000, max_response=80_000_000):
        self.root = no_symlink(Path(root)).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.blobs = self.root / "blobs"
        no_symlink(self.blobs)
        self.blobs.mkdir(exist_ok=True)
        self.records = {}
        self.expected = None
        self.allow_missing = False
        self.on_record = None
        self.record_lock = threading.RLock()
        self.transport = PublicCache(
            self.root / "transport",
            max_bytes=max_bytes,
            max_response_bytes=max_response,
            source_policy=policy,
            organization="UKAEA FAIR-MAST / STFC eData",
            parser_version=PARSER_VERSION,
            user_agent="MattocciaLabs-FPRE/0.1 public retrospective diagnostic research; https://mattoccia.com/research-engines/",
        )

    def fetch(self, url, offline=False):
        if self.expected is not None and url in self.expected:
            r = self.expected[url]
            path = self.frozen(r)
            self.remember(url, r)
            return path, r
        if self.expected is not None and not self.allow_missing:
            raise ValueError("Object absent from frozen acquisition manifest")
        path, r = self.transport.fetch(url, offline=offline, as_path=True)
        dest = self.blobs / (r["sha256"] + ".data")
        no_symlink(dest)
        if not dest.exists():
            os.link(path, dest)
            dest.chmod(0o600)
        if PublicCache.file_hash(dest) != r["sha256"]:
            raise ValueError("Immutable source modified")
        r = dict(
            r,
            source="UKAEA FAIR-MAST" if "s3.echo" in url else "STFC eData",
            license=LICENSE_MAST if "s3.echo" in url else LICENSE_STFC,
        )
        self.remember(url, r)
        return dest, r

    def remember(self, url, record):
        with self.record_lock:
            self.records[url] = record
            if self.on_record:
                self.on_record(list(self.records.values()))

    def frozen(self, record):
        policy(record["url"])
        if not re.fullmatch("[a-f0-9]{64}", record["sha256"]):
            raise ValueError("Invalid source digest")
        p = self.blobs / (record["sha256"] + ".data")
        no_symlink(p)
        if not p.is_file() or PublicCache.file_hash(p) != record["sha256"]:
            raise ValueError("Frozen original missing or modified")
        return p

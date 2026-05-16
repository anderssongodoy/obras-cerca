"""Utilidades compartidas: sesión HTTP, paths, descargas con stream."""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Iterable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

ROOT = Path(__file__).resolve().parent
DATA_RAW = ROOT / "data" / "raw"


def make_session(extra_headers: dict | None = None) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Accept-Language": "es-PE,es;q=0.9,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    if extra_headers:
        s.headers.update(extra_headers)
    retry = Retry(
        total=4,
        backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "HEAD"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=8)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


def stream_to_file(session: requests.Session, url: str, dest: Path, chunk: int = 1 << 15) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with session.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        total = 0
        with dest.open("wb") as fh:
            for buf in r.iter_content(chunk_size=chunk):
                if buf:
                    fh.write(buf)
                    total += len(buf)
    return total


def log(*args: object) -> None:
    print(time.strftime("[%H:%M:%S]"), *args, file=sys.stderr, flush=True)


def out_dir(subdir: str) -> Path:
    p = DATA_RAW / subdir
    p.mkdir(parents=True, exist_ok=True)
    return p

"""Recorre /api/v1/releases paginando y guarda cada página como JSONL.

Cada página es un OCDS Release Package. Aquí escribimos cada release como
una línea NDJSON para procesamiento posterior con Polars/DuckDB.

Uso:
    python 05_ocds_releases.py --max-pages 5
    python 05_ocds_releases.py --max-pages 0   # todas (cuidado, son muchas)
"""
from __future__ import annotations

import argparse
import json
import time

from common import log, make_session, out_dir

BASE = "https://contratacionesabiertas.oece.gob.pe"
ENDPOINT = f"{BASE}/api/v1/releases"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--page-size", type=int, default=100)
    ap.add_argument("--start-page", type=int, default=1)
    ap.add_argument("--max-pages", type=int, default=2,
                    help="0 = sin tope. Default 2 para probar.")
    ap.add_argument("--sleep", type=float, default=0.4,
                    help="Pausa entre requests (segundos)")
    args = ap.parse_args()

    session = make_session(extra_headers={"Accept": "application/json"})

    out = out_dir("ocds_releases")
    ndjson = out / f"releases_p{args.start_page}_size{args.page_size}.ndjson"
    log(f"Escribiendo en {ndjson}")

    count_pages = 0
    count_releases = 0
    page = args.start_page
    with ndjson.open("w", encoding="utf-8") as fh:
        while True:
            if args.max_pages and count_pages >= args.max_pages:
                log(f"Tope --max-pages={args.max_pages} alcanzado")
                break
            params = {"page": page, "paginateBy": args.page_size}
            log(f"GET {ENDPOINT} {params}")
            r = session.get(ENDPOINT, params=params, timeout=120)
            if r.status_code == 404:
                log("404 — fin de la paginación")
                break
            r.raise_for_status()
            pkg = r.json()
            releases = pkg.get("releases") or []
            if not releases:
                log("Sin releases en esta página — fin")
                break
            for rel in releases:
                fh.write(json.dumps(rel, ensure_ascii=False))
                fh.write("\n")
            count_releases += len(releases)
            count_pages += 1
            log(f"  página {page}: {len(releases)} releases (total {count_releases})")
            page += 1
            time.sleep(args.sleep)

    log(f"Listo: {count_pages} páginas, {count_releases} releases en {ndjson}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

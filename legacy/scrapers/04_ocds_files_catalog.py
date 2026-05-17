"""Descarga el catálogo /api/v1/files y opcionalmente los bulks mensuales.

El catálogo lista, para cada combinación (source, year, month), URLs de los
archivos en formatos csv / csv_es / xlsx / xlsx_es / json / sha.

Source: seace_v1 (2004-2008), seace_v2 (2009-2016), seace_v3 (2017-presente).

Uso:
    # Solo el catálogo
    python 04_ocds_files_catalog.py

    # Catálogo + bajar todos los xlsx_es de seace_v3 del año 2025
    python 04_ocds_files_catalog.py --download --source seace_v3 --year 2025 --format xlsx_es
"""
from __future__ import annotations

import argparse
import json

from common import log, make_session, out_dir, stream_to_file

BASE = "https://contratacionesabiertas.oece.gob.pe"
CATALOG = f"{BASE}/api/v1/files"


def fetch_catalog(session) -> dict:
    log("GET", CATALOG)
    r = session.get(CATALOG, headers={"Accept": "application/json"}, timeout=60)
    r.raise_for_status()
    return r.json()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--download", action="store_true",
                    help="Además de listar, descargar los archivos filtrados")
    ap.add_argument("--source", choices=("seace_v1", "seace_v2", "seace_v3"))
    ap.add_argument("--year", type=int)
    ap.add_argument("--month", type=int)
    ap.add_argument(
        "--format",
        choices=("csv", "csv_es", "xlsx", "xlsx_es", "json", "sha"),
        default="xlsx_es",
    )
    args = ap.parse_args()

    session = make_session(extra_headers={"Accept": "application/json"})
    cat = fetch_catalog(session)
    results = cat.get("results") if isinstance(cat, dict) else cat
    if not isinstance(results, list):
        log("Respuesta inesperada del catálogo")
        return 1

    out = out_dir("ocds_catalog")
    cat_path = out / "files_catalog.json"
    cat_path.write_text(json.dumps(cat, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"Catálogo escrito en {cat_path} ({len(results)} entradas)")

    if args.source:
        results = [e for e in results if e.get("source") == args.source]
    if args.year:
        results = [e for e in results if str(e.get("year")) == str(args.year)]
    if args.month:
        results = [e for e in results if int(str(e.get("month"))) == args.month]
    log(f"Tras filtros: {len(results)} entradas")

    if not args.download:
        for e in results[:20]:
            print(f"{e['source']} {e['year']}-{e['month']}  {e['files'].get(args.format)}")
        if len(results) > 20:
            log(f"... y {len(results) - 20} más (pasa --download para bajarlas)")
        return 0

    for entry in results:
        files = entry.get("files", {})
        url = files.get(args.format)
        if not url:
            log(f"  sin {args.format}: {entry.get('id')}")
            continue
        ext = "json" if args.format == "json" else ("xlsx" if "xlsx" in args.format else "csv")
        dest = out_dir(f"ocds_bulk/{entry['source']}") / f"{entry['id']}.{args.format}.{ext}"
        if dest.exists() and dest.stat().st_size > 0:
            log(f"  ya existe: {dest.name}")
            continue
        try:
            size = stream_to_file(session, url, dest)
            log(f"  bajado: {dest.name} ({size:,} B)")
        except Exception as exc:
            log(f"  ERROR {entry.get('id')}: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

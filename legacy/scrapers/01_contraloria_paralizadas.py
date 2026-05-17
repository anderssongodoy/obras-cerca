"""Descarga el informe Contraloría de Obras Paralizadas (PDF + 3 anexos XLSX).

Por defecto baja el informe a diciembre 2025. Pasa --slug para otro informe
de la colección 18230, o --coleccion para listar todos los disponibles.

Uso:
    python 01_contraloria_paralizadas.py
    python 01_contraloria_paralizadas.py --coleccion
    python 01_contraloria_paralizadas.py --slug 6555301-informe-de-obras-paralizadas-en-el-territorio-nacional-a-diciembre-2024
"""
from __future__ import annotations

import argparse
import re
from urllib.parse import unquote, urlparse

from common import log, make_session, out_dir, stream_to_file

BASE = "https://www.gob.pe"
COLECCION_URL = f"{BASE}/institucion/contraloria/colecciones/18230-obras-paralizadas-documentos"
DEFAULT_SLUG = "7715417-informe-de-obras-paralizadas-en-el-territorio-nacional-a-diciembre-2025"

CDN_RX = re.compile(
    r'https://cdn\.www\.gob\.pe/uploads/document/file/[^"?]+\?v=\d+'
)
SLUG_RX = re.compile(
    r'/institucion/contraloria/informes-publicaciones/(\d+-[a-z0-9-]+)'
)
PREVIEW_RX = re.compile(r"/preview_", re.IGNORECASE)


def listar_coleccion(session) -> list[str]:
    r = session.get(COLECCION_URL, timeout=60)
    r.raise_for_status()
    slugs = sorted(set(SLUG_RX.findall(r.text)))
    return slugs


def descargar_informe(session, slug: str) -> list[tuple[str, int]]:
    url = f"{BASE}/institucion/contraloria/informes-publicaciones/{slug}"
    log("GET", url)
    r = session.get(url, timeout=60)
    r.raise_for_status()
    urls = sorted(set(CDN_RX.findall(r.text)))
    urls = [u for u in urls if not PREVIEW_RX.search(u)]
    log(f"Encontrados {len(urls)} archivos no-preview")

    dest_dir = out_dir(f"contraloria_paralizadas/{slug}")
    resultados: list[tuple[str, int]] = []
    for u in urls:
        name = unquote(urlparse(u).path.rsplit("/", 1)[-1])
        dest = dest_dir / name
        if dest.exists() and dest.stat().st_size > 0:
            log(f"  ya existe: {name} ({dest.stat().st_size:,} B)")
            resultados.append((name, dest.stat().st_size))
            continue
        size = stream_to_file(session, u, dest)
        log(f"  bajado: {name} ({size:,} B)")
        resultados.append((name, size))
    return resultados


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slug", default=DEFAULT_SLUG)
    ap.add_argument("--coleccion", action="store_true",
                    help="Solo listar slugs de la colección 18230 y salir")
    args = ap.parse_args()

    session = make_session()

    if args.coleccion:
        for slug in listar_coleccion(session):
            print(slug)
        return 0

    resultados = descargar_informe(session, args.slug)
    log(f"Total: {len(resultados)} archivos, {sum(s for _, s in resultados):,} B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

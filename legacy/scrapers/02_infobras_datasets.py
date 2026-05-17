"""Descarga los 4 DataSets bulk de Infobras (Contraloría).

Descubre los filenames vigentes haciendo scrape del HTML /InfobrasWeb/DataSets,
luego invoca el endpoint /InfobrasWeb/Archivo/DownloadFile para cada uno.

Datasets esperados (filename data sin extensión, la fecha cambia con cada actualización):
    - DataSet-Obras-Paralizadas <fecha>
    - DataSet-Obras-Publicas <fecha>
    - DataSet-Obras-en-reconstruccion-con-Cambios <fecha>
    - DataSet-Asociaciones-Publico-Privadas <fecha>
"""
from __future__ import annotations

import argparse
import re
from urllib.parse import quote

from common import log, make_session, out_dir, stream_to_file

BASE = "https://infobras.contraloria.gob.pe"
LISTING = f"{BASE}/InfobrasWeb/DataSets"
DOWNLOAD = f"{BASE}/InfobrasWeb/Archivo/DownloadFile"
XLSX_CT = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

DATA_FILENAME_RX = re.compile(
    r'class="download-file[^"]*"[^>]*data-filename="([^"]+)"[^>]*data-extension="(\.[a-z]+)"',
    re.IGNORECASE,
)


def discover(session) -> list[tuple[str, str]]:
    log("GET", LISTING)
    r = session.get(LISTING, timeout=60)
    r.raise_for_status()
    pairs = list({(m.group(1), m.group(2)) for m in DATA_FILENAME_RX.finditer(r.text)})
    log(f"Encontrados {len(pairs)} datasets:")
    for fn, ext in pairs:
        log(f"  - {fn}{ext}")
    return pairs


def descargar_dataset(session, filename: str, extension: str) -> int:
    safe_name = filename.replace(" ", "_") + extension
    dest = out_dir("infobras_datasets") / safe_name
    if dest.exists() and dest.stat().st_size > 0:
        log(f"ya existe: {safe_name} ({dest.stat().st_size:,} B)")
        return dest.stat().st_size

    url = (
        f"{DOWNLOAD}?filename={quote(filename)}"
        f"&name={quote(filename)}"
        f"&contentType={quote(XLSX_CT)}"
        f"&extension={quote(extension)}"
    )
    log("GET", url)
    size = stream_to_file(session, url, dest)
    log(f"  bajado: {safe_name} ({size:,} B)")
    return size


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", help="Sustring para filtrar qué dataset bajar (ej: 'Paralizadas')")
    args = ap.parse_args()

    session = make_session(extra_headers={"Referer": LISTING})
    pairs = discover(session)
    if args.only:
        pairs = [p for p in pairs if args.only.lower() in p[0].lower()]
        log(f"Filtrados {len(pairs)} por '{args.only}'")

    total = 0
    for filename, extension in pairs:
        total += descargar_dataset(session, filename, extension)
    log(f"Total: {total:,} B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

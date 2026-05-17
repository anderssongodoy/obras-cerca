"""Guarda el HTML server-side de una ficha individual Infobras por ObraId.

Útil para enriquecer obras puntuales con campos que no estén en el bulk.
El HTML es Razor/MVC clásico (no SPA), parseable con BeautifulSoup en un
paso posterior.

Uso:
    python 03_infobras_ficha.py 52903 52904 52905
    python 03_infobras_ficha.py --from-file ids.txt
"""
from __future__ import annotations

import argparse
from pathlib import Path

from common import log, make_session, out_dir

BASE = "https://infobras.contraloria.gob.pe"
SUMARIO = f"{BASE}/InfobrasWeb/Mapa/Sumario"


def bajar_ficha(session, obra_id: int) -> Path:
    dest = out_dir("infobras_fichas") / f"obra_{obra_id}.html"
    if dest.exists() and dest.stat().st_size > 0:
        log(f"ya existe: {dest.name} ({dest.stat().st_size:,} B)")
        return dest
    r = session.get(SUMARIO, params={"ObraId": obra_id}, timeout=90)
    r.raise_for_status()
    dest.write_bytes(r.content)
    log(f"bajado: {dest.name} ({dest.stat().st_size:,} B)")
    return dest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ids", type=int, nargs="*", help="ObraId(s) a descargar")
    ap.add_argument("--from-file", type=Path, help="Archivo con un ObraId por línea")
    args = ap.parse_args()

    ids: list[int] = list(args.ids)
    if args.from_file:
        for line in args.from_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                ids.append(int(line))
    if not ids:
        ap.error("Pasa al menos un ObraId o usa --from-file")

    session = make_session(extra_headers={"Referer": f"{BASE}/infobrasweb"})
    for obra_id in ids:
        bajar_ficha(session, obra_id)
    log(f"Total fichas: {len(ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Descarga Órdenes de Compra y Servicios (≤8 UIT) desde OECE CONOSCE.

URLs descubiertas via Playwright al portal Pentaho (ver docs en
analisis_scraping.md §4). Una vez identificadas, son URLs directas
públicas en conosce.osce.gob.pe que se bajan con curl/requests.

Para el MVP: solo los últimos N meses (default 6) — cada archivo
mensual pesa ~50 MB.

Uso:
    python 06_pentaho_ordenes_compra.py --meses 6
    python 06_pentaho_ordenes_compra.py --year 2026 --mes 4   # uno específico
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import log, make_session, out_dir, stream_to_file  # noqa: E402

CONOSCE_BASE = "https://conosce.osce.gob.pe/buscador/assets/67ae6c4a/reportes/ordenes"

MESES = {
    1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL",
    5: "MAYO", 6: "JUNIO", 7: "JULIO", 8: "AGOSTO",
    9: "SETIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE",
}


def url_para(year: int, mes: int) -> str:
    nombre = MESES[mes]
    # Patrón observado: CONOSCE_ORDENESCOMPRA<MES_MAYUS><YEAR>_0.xlsx
    return f"{CONOSCE_BASE}/{year}/CONOSCE_ORDENESCOMPRA{nombre}{year}_0.xlsx"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--meses", type=int, default=6, help="Cuántos meses hacia atrás bajar (desde hoy)")
    ap.add_argument("--year", type=int, help="Año específico")
    ap.add_argument("--mes", type=int, help="Mes específico (1-12)")
    ap.add_argument("--force", action="store_true", help="Reemplazar archivos existentes")
    args = ap.parse_args()

    session = make_session(extra_headers={
        "Referer": "https://bi.seace.gob.pe/pentaho/api/repos/:public:portal:datosabiertos.html/content"
    })

    objetivos: list[tuple[int, int]] = []
    if args.year and args.mes:
        objetivos.append((args.year, args.mes))
    else:
        # Últimos N meses partiendo de mes anterior al actual (los del mes en curso aún no se publican)
        from datetime import date
        d = date.today().replace(day=1)
        for _ in range(args.meses):
            # retroceder un mes
            y = d.year if d.month > 1 else d.year - 1
            m = d.month - 1 if d.month > 1 else 12
            d = d.replace(year=y, month=m)
            objetivos.append((y, m))

    log(f"A descargar: {len(objetivos)} archivos")
    dest = out_dir("pentaho_ordenes")
    total = 0
    for year, mes in objetivos:
        url = url_para(year, mes)
        fname = url.rsplit("/", 1)[-1]
        path = dest / fname
        if path.exists() and not args.force and path.stat().st_size > 0:
            log(f"ya existe: {fname} ({path.stat().st_size:,} B)")
            total += path.stat().st_size
            continue
        try:
            size = stream_to_file(session, url, path)
            log(f"bajado: {fname} ({size:,} B)")
            total += size
        except Exception as e:
            log(f"ERROR {fname}: {e}")

    log(f"Total: {total:,} B en {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

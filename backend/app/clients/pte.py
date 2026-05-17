"""Cliente para el Portal de Transparencia Estándar (PTE).

Catálogo nacional de entidades públicas: ~1,800 munis + ministerios +
organismos autónomos + empresas estatales + universidades.
"""
from __future__ import annotations

import re

from .common import make_session

BASE = "https://www.transparencia.gob.pe"


# Mapeo Tipo_Pod -> tipo de entidad (los 7 universos del PTE)
TIPO_POD_MAP = {
    1: "legislativo",          # Congreso
    2: "judicial",              # Poder Judicial, JNJ, etc
    4: "organismo_autonomo",    # JNJ, JNE, ONPE, Defensoría, ...
    5: "gobierno_local",        # Municipalidades (las 1,279 munis y otros)
    7: "gobierno_regional",     # Gobiernos regionales
}
# Tipo_Pod sin parámetro o tipo_pod=3 -> poder ejecutivo (ministerios)


class PTEClient:
    def __init__(self, session=None):
        self.s = session or make_session()

    def listar_entidades(self, tipo_pod: int | None = 5) -> list[dict]:
        """Lista todas las entidades del tipo dado (default: gobiernos locales).

        Devuelve [{'id_entidad': N, 'nombre': str, 'sigla': str|None}, ...]
        """
        q = f"?Tipo_Pod={tipo_pod}" if tipo_pod else ""
        url = f"{BASE}/buscador/pte_transparencia_listado_entidades_poder.aspx{q}"
        try:
            r = self.s.get(url, timeout=60)
            if r.status_code != 200:
                return []
            html = r.text
        except Exception:
            return []

        # <a href='...?id_entidad=NNN'>NOMBRE (SIGLA)</a>
        rx = re.compile(
            r"<a\s+[^>]*id_entidad=(\d+)[^>]*>([^<]+)</a>",
            re.IGNORECASE,
        )
        seen: dict[int, dict] = {}
        for m in rx.finditer(html):
            id_ent = int(m.group(1))
            if id_ent in seen:
                continue
            raw = re.sub(r"\s+", " ", m.group(2)).strip()
            sigla_m = re.search(r"\(([^)]+)\)\s*$", raw)
            sigla = sigla_m.group(1).strip() if sigla_m else None
            nombre = re.sub(r"\s*\([^)]+\)\s*$", "", raw).strip()
            seen[id_ent] = {"id_entidad": id_ent, "nombre": nombre, "sigla": sigla}
        return list(seen.values())

"""Cliente HTTP para Infobras (Contraloría).

Capas:
    WFS              -> coordenadas oficiales + estado oficial (la verdad)
    Ficha pública    -> estado visible al ciudadano (server-side HTML)
    InformeControl   -> variable JS lInformeControl con PDFs auditoría
"""
from __future__ import annotations

import json
import re
from typing import Any

from .common import make_session

BASE = "https://infobras.contraloria.gob.pe"


class InfobrasClient:
    def __init__(self, session=None):
        self.s = session or make_session()

    # ----- WFS: coordenadas + estado oficial Contraloría -----

    def wfs_obra(self, nobr_id: int) -> dict | None:
        """Devuelve la feature WFS de la obra (coords + estado oficial), o None.

        Estado posible: 'En Ejecución', 'Paralizada', 'Finalizada', etc.
        """
        url = (
            f"{BASE}/InfobrasWeb/Mapa/MapaEstadistico/WmsProxy"
            "?path=ows&service=WFS&request=GetFeature"
            "&typeName=inf_geoobrdef_4326_pt&outputFormat=application/json"
            f"&CQL_FILTER=cdp1_codigo='{nobr_id}'"
        )
        try:
            r = self.s.get(url, timeout=30)
            if r.status_code != 200:
                return None
            data = r.json()
            features = data.get("features", [])
            if not features:
                return None
            f = features[0]
            geom = f.get("geometry") or {}
            coords = geom.get("coordinates") or [None, None]
            props = f.get("properties") or {}
            return {
                "lon": coords[0],
                "lat": coords[1],
                "estado": props.get("cdp1_estadoobra"),
                "departamento": props.get("cdp1_departamento"),
                "provincia": props.get("cdp1_provincia"),
                "distrito": props.get("cdp1_distrito"),
            }
        except Exception:
            return None

    # ----- Ficha pública (HTML) -----

    def ficha_obra(self, nobr_id: int) -> dict | None:
        """Scrape de la ficha pública. Devuelve dict con campos visibles."""
        url = f"{BASE}/InfobrasWeb/Mapa/Sumario?ObraId={nobr_id}"
        try:
            r = self.s.get(url, timeout=30)
            if r.status_code != 200:
                return None
            html = r.text
        except Exception:
            return None

        labels = [
            "NOMBRE DE OBRA", "CÓDIGO ÚNICO DE INVERSIÓN", "CÓDIGO SNIP",
            "ENTIDAD RESPONSABLE DE LA OBRA", "ESTADO DE OBRA",
            "PORCENTAJE DE AVANCE FÍSICO", "FECHA DEL ULTIMO AVANCE",
            "MONTO DE APROBACIÓN", "MONTO DEL CONTRATO", "CONTRATISTA",
            "FECHA DE INICIO", "FECHA DE FIN", "MODALIDAD",
            "CONTRATO", "FECHA DE CONTRATO",
        ]
        out: dict[str, str] = {}
        for label in labels:
            pattern = re.escape(label) + r"\s*\n\s*([^\n<]+)"
            m = re.search(pattern, html, re.IGNORECASE)
            if m:
                v = re.sub(r"\s+", " ", m.group(1)).strip()
                if v and v.lower() not in ("", "—", "-"):
                    out[label] = v
        return out or None

    # ----- Informes de Control -----

    def informes_control(self, nobr_id: int) -> list[dict]:
        """Extrae la variable JS `lInformeControl` con los informes de Contraloría."""
        url = f"{BASE}/InfobrasWeb/Mapa/InformeControl?obraId={nobr_id}"
        try:
            r = self.s.get(url, timeout=30)
            if r.status_code != 200:
                return []
        except Exception:
            return []

        m = re.search(r"lInformeControl\s*=\s*(\[.*?\]);", r.text, re.DOTALL)
        if not m:
            return []
        try:
            return json.loads(m.group(1))
        except Exception:
            return []

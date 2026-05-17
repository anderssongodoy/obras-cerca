"""Cliente HTTP para MEF (Invierte.pe / SIAF / SEACE).

Todos los endpoints provienen del Postman del compañero:
    docs/postman_collection.json

Patrones:
    id_entidad (PTE) -> IdUE (SIAF) -> CUI (Invierte.pe) -> NOBR_ID (Infobras)

Cada función devuelve dict|list crudo o None si vacío/error.
Nunca lanza excepciones: los errores se loguean y devuelven None.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any

from .common import make_session

BASE = "https://ofi5.mef.gob.pe"


def _dotnet_date(v: Any) -> date | None:
    """MEF devuelve fechas como '/Date(1488430800000)/'.

    También acepta strings DD/MM/YY o DD/MM/YYYY.
    """
    if v is None or v == "":
        return None
    if isinstance(v, (date, datetime)):
        return v if isinstance(v, date) else v.date()
    s = str(v).strip()
    m = re.match(r"^/Date\((\d+)\)/$", s)
    if m:
        try:
            return datetime.fromtimestamp(int(m.group(1)) / 1000).date()
        except (ValueError, OSError):
            return None
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})$", s)
    if m:
        try:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if y < 100:
                y += 2000 if y < 50 else 1900
            return date(y, mo, d)
        except ValueError:
            return None
    return None


class MEFClient:
    def __init__(self, session=None):
        self.s = session or make_session(extra_headers={
            "X-Requested-With": "XMLHttpRequest",
        })

    # ----- 1. Mapeo entidad -> IdUE SIAF -----

    def scrape_idue_de_pte(self, id_entidad: int) -> int | None:
        """Visita pte_transparencia_pro_inv.aspx?id_entidad=X&id_tema=26
        y extrae IdUE del HTML.
        """
        url = (
            "https://www.transparencia.gob.pe/reportes_directos/"
            "pte_transparencia_pro_inv.aspx"
            f"?id_entidad={id_entidad}&id_tema=26&ver=1"
        )
        try:
            r = self.s.get(url, timeout=30)
            if r.status_code != 200:
                return None
            m = re.search(r"IdUE=(\d+)", r.text)
            return int(m.group(1)) if m else None
        except Exception:
            return None

    # ----- 2. Por UE -> lista de CUIs -----

    def get_ejecucion(self, idue: int, periodo: int, page: int = 1,
                       page_size: int = 30) -> list[dict]:
        """GetEjecucion: lista paginada de CUIs ejecutados por una UE en un periodo."""
        url = f"{BASE}/proyectos_pte/forms/UnidadEjecutora.aspx/GetEjecucion"
        ref = f"{BASE}/proyectos_pte/forms/UnidadEjecutora.aspx?tipo=2&IdUE={idue}&IdUEBase={idue}&periodoBase={periodo}"
        body = {
            "pPageSize": page_size,
            "pPageNumber": page,
            "pSortColumn": "codDGPP",
            "pSortOrder": "asc",
            "pPeriodo": str(periodo),
            "pCodEjecutora": str(idue),
            "pCodDGPP": "",
            "pCodSNIP": "",
            "pNomProyecto": "",
        }
        try:
            r = self.s.post(
                url,
                data=json.dumps(body),
                headers={"Content-Type": "application/json; charset=UTF-8", "Referer": ref},
                timeout=60,
            )
            if r.status_code != 200:
                return []
            data = r.json()
            d = data.get("d") if isinstance(data, dict) else data
            if isinstance(d, str):
                d = json.loads(d)
            return d.get("rows", []) if isinstance(d, dict) else (d or [])
        except Exception:
            return []

    # ----- 3. Por CUI -> 4 endpoints en serie -----

    def trae_det_inv_ssi(self, cui: int) -> dict | None:
        """Datos generales del proyecto Invierte.pe."""
        url = f"{BASE}/invierteWS/Ssi/traeDetInvSSI"
        ref = f"{BASE}/ssi/Ssi/Index?tipo=2&codigo={cui}"
        try:
            r = self.s.post(
                url, data={"id": cui, "tipo": "SIAF"},
                headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "Referer": ref},
                timeout=60,
            )
            if r.status_code != 200:
                return None
            data = r.json()
            if isinstance(data, list):
                return data[0] if data else None
            return data
        except Exception:
            return None

    def ver_info_obras2(self, cui: int) -> list[dict]:
        """Lista de NOBR_IDs vinculados al CUI (1..N: original + saldos de obra)."""
        url = f"{BASE}/ssi/Ssi/verInfObras2/{cui}"
        ref = f"{BASE}/ssi/Ssi/Index?tipo=2&codigo={cui}"
        try:
            r = self.s.get(
                url,
                headers={"Referer": ref, "Accept": "application/json"},
                timeout=60,
            )
            if r.status_code != 200:
                return []
            text = r.text.strip()
            if not text:
                return []
            data = json.loads(text)
            if isinstance(data, str):
                data = json.loads(data)
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("lstObra") or data.get("rows") or data.get("data") or []
            return []
        except Exception:
            return []

    def trae_contrato_seace_dwh(self, cui: int) -> list[dict]:
        """Contratos SEACE vinculados al CUI."""
        url = f"{BASE}/invierteWS/Ssi/traeContratoSeaceDWH"
        ref = f"{BASE}/ssi/Ssi/Index?tipo=2&codigo={cui}"
        try:
            r = self.s.post(
                url, data={"id": cui, "codsnip": cui, "vers": "v2"},
                headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "Referer": ref},
                timeout=60,
            )
            if r.status_code != 200:
                return []
            data = r.json()
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("rows") or data.get("d") or []
            return []
        except Exception:
            return []

    def trae_lista_paraliza_publico(self, cui: int) -> list[dict]:
        """Paralizaciones declaradas oficialmente para el CUI."""
        url = f"{BASE}/invierte/paraliza/traeListaParalizaPublico"
        ref = f"{BASE}/ssi/Ssi/Index?tipo=2&codigo={cui}"
        try:
            r = self.s.post(
                url, data={"id": cui},
                headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "Referer": ref},
                timeout=60,
            )
            if r.status_code != 200:
                return []
            data = r.json()
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("rows") or data.get("d") or []
            return []
        except Exception:
            return []

    def trae_deveng_ssi(self, cui: int) -> list[dict]:
        """Devengado mensual SIAF."""
        url = f"{BASE}/invierteWS/Dashboard/traeDevengSSI"
        ref = f"{BASE}/ssi/Ssi/Index?tipo=2&codigo={cui}"
        try:
            r = self.s.post(
                url, data={"id": cui, "tipo": "FINAN"},
                headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "Referer": ref},
                timeout=60,
            )
            if r.status_code != 200:
                return []
            data = r.json()
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("rows") or []
            return []
        except Exception:
            return []

"""Smoke test de toda la API — prueba 20+ endpoints y genera un reporte.

Útil para:
1. Verificar que cada endpoint responde correctamente tras un deploy
2. Demostrar cobertura del API al jurado (corre antes de la demo)

Uso:
    python scripts/smoke_test.py
    python scripts/smoke_test.py --base http://localhost:8000
"""
from __future__ import annotations

import argparse
import io
import sys
import time
import urllib.request
import urllib.error
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def hit(url: str, *, expect_json: bool = True) -> tuple[bool, str, float, int]:
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
            dt = time.time() - t0
            if expect_json:
                data = json.loads(body)
                if isinstance(data, list):
                    return True, f"list[{len(data)}]", dt, len(body)
                if isinstance(data, dict):
                    if "items" in data:
                        return True, f"items[{len(data['items'])}] total={data.get('total','?')}", dt, len(body)
                    keys = list(data.keys())[:5]
                    return True, f"obj keys={keys}", dt, len(body)
            return True, f"{r.status}", dt, len(body)
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}", time.time() - t0, 0
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"[:80], time.time() - t0, 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    args = ap.parse_args()
    B = args.base.rstrip("/")

    checks = [
        ("META",     "GET /"),                                          f"{B}/",
        ("META",     "GET /api/health"),                                f"{B}/api/health",
        ("STATS",    "GET /api/stats"),                                 f"{B}/api/stats",
        ("STATS",    "GET /api/stats/series-paralizadas"),              f"{B}/api/stats/series-paralizadas",
        ("DISTRITO", "GET /api/distritos"),                             f"{B}/api/distritos",
        ("DISTRITO", "GET /api/distritos/resumen"),                     f"{B}/api/distritos/resumen",
        ("DISTRITO", "GET /api/distritos/150101"),                      f"{B}/api/distritos/150101",
        ("DISTRITO", "GET /api/distritos/150131"),                      f"{B}/api/distritos/150131",
        ("OBRAS",    "GET /api/obras (default)"),                       f"{B}/api/obras?limit=3",
        ("OBRAS",    "GET /api/obras (cerca de mí San Isidro 1km)"),    f"{B}/api/obras?lat=-12.0959&lon=-77.0364&radio_m=1000&limit=3",
        ("OBRAS",    "GET /api/obras (paralizadas vigentes)"),          f"{B}/api/obras?paralizadas=true&clasificacion=vigente&limit=3",
        ("OBRAS",    "GET /api/obras?q=hospital"),                      f"{B}/api/obras?q=hospital&limit=3",
        ("OBRAS",    "GET /api/obras (Miraflores)"),                    f"{B}/api/obras?ubigeo=150122&limit=3",
        ("MAPA",     "GET /api/mapa/heatmap"),                          f"{B}/api/mapa/heatmap",
        ("MAPA",     "GET /api/mapa/bounds (Lima centro)"),             f"{B}/api/mapa/bounds?nw_lat=-12.0&nw_lon=-77.1&se_lat=-12.2&se_lon=-77.0&limit=10",
        ("CONTRAT",  "GET /api/contratistas?con_paralizadas=true"),     f"{B}/api/contratistas?con_paralizadas=true&limit=5",
        ("CONTRAT",  "GET /api/contratistas/sospechosos"),              f"{B}/api/contratistas/sospechosos?min_pct=20",
        ("CONTRAT",  "GET /api/contratistas/20600182197 (PROTEGE)"),    f"{B}/api/contratistas/20600182197",
        ("CONTRAT",  "GET /api/contratistas/20600182197/explicacion"),  f"{B}/api/contratistas/20600182197/explicacion",
        ("SENALES",  "GET /api/senales (top)"),                         f"{B}/api/senales?limit=5",
        ("SENALES",  "GET /api/senales?tipo=concentracion_menores"),    f"{B}/api/senales?tipo=concentracion_menores",
        ("SENALES",  "GET /api/senales?solo_confirmadas=true"),         f"{B}/api/senales?solo_confirmadas=true&limit=5",
        ("ENTIDAD",  "GET /api/entidades?q=municipal"),                 f"{B}/api/entidades?q=municipal&limit=5",
        ("SECTOR",   "GET /api/sectores"),                              f"{B}/api/sectores",
        ("SEARCH",   "GET /api/search?q=hospital"),                     f"{B}/api/search?q=hospital",
    ]

    # checks viene como (cat, desc), url, (cat, desc), url, ...
    items = []
    for i in range(0, len(checks), 2):
        cat, desc = checks[i]
        url = checks[i+1]
        items.append((cat, desc, url))

    print(f"\n{'-'*120}")
    print(f"Smoke test: {len(items)} endpoints en {B}\n")

    ok = fail = 0
    total_ms = 0
    for cat, desc, url in items:
        success, info, dt, size = hit(url)
        total_ms += dt * 1000
        tag = f"{GREEN}OK   {RESET}" if success else f"{RED}FAIL {RESET}"
        color = GREEN if success else RED
        ms = int(dt * 1000)
        kb = size / 1024 if size else 0
        print(f"{tag} [{cat:<9}] {desc:<55} {color}{ms:>5}ms{RESET}  {kb:>6.1f}KB  {info}")
        if success:
            ok += 1
        else:
            fail += 1
            print(f"        url: {url}")

    print(f"\n{'-'*120}")
    print(f"Resultado: {GREEN}{ok} OK{RESET} · {RED}{fail} FAIL{RESET} · total {int(total_ms)}ms ({int(total_ms/len(items))}ms promedio)")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

"""Descarga el catálogo de Gobiernos Locales del Portal de Transparencia (PTE).

Source: https://www.transparencia.gob.pe/buscador/pte_transparencia_listado_entidades_poder.aspx?Tipo_Pod=5

Output:
    scrapers/data/raw/pte_entidades/gobiernos_locales.csv (id_entidad, nombre, slug_gob_pe)
    scrapers/data/raw/pte_entidades/gobiernos_locales.html (snapshot crudo)

Por qué: el id_entidad PTE es la llave para:
    - Abrir el portal de cada muni: transparencia.gob.pe?id_entidad=NNN
    - Mapear a IdUE SIAF (paso 1 del Postman collection del compañero)
    - Validar Infobras contra cada muni vía MEF/SIAF
"""
from __future__ import annotations

import csv
import io
import re
import sys
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import log, make_session, out_dir  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

URL = "https://www.transparencia.gob.pe/buscador/pte_transparencia_listado_entidades_poder.aspx?Tipo_Pod=5"

# Patrón: <a href='...?id_entidad=NNN...'>NOMBRE (SIGLA)</a>
# Acepta comillas simples o dobles
LINK_RX = re.compile(
    r"""<a\s+[^>]*id_entidad=(\d+)[^>]*>([^<]+)</a>""",
    re.IGNORECASE,
)


def main() -> int:
    dest = out_dir("pte_entidades")
    html_path = dest / "gobiernos_locales.html"
    csv_path = dest / "gobiernos_locales.csv"

    session = make_session()
    log("GET", URL)
    r = session.get(URL, timeout=60)
    r.raise_for_status()
    html_path.write_bytes(r.content)
    log(f"  HTML guardado: {html_path.name} ({html_path.stat().st_size:,} B)")

    text = r.text
    matches = LINK_RX.findall(text)
    # dedup por id_entidad
    seen: dict[str, str] = {}
    for id_ent, nombre in matches:
        nombre_clean = re.sub(r"\s+", " ", nombre).strip()
        if id_ent not in seen and nombre_clean:
            seen[id_ent] = nombre_clean

    log(f"  Entidades únicas extraídas: {len(seen)}")

    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id_entidad", "nombre"])
        for id_ent, nombre in sorted(seen.items(), key=lambda x: int(x[0])):
            w.writerow([id_ent, nombre])

    log(f"  CSV escrito: {csv_path} ({csv_path.stat().st_size:,} B)")

    # Filtrar Lima Metro + Callao
    palabras_mvp = [
        "MUNICIPALIDAD METROPOLITANA DE LIMA",
        "MUNICIPALIDAD DISTRITAL DE ANCON", "MUNICIPALIDAD DISTRITAL DE ATE", "MUNICIPALIDAD DISTRITAL DE BARRANCO",
        "MUNICIPALIDAD DISTRITAL DE BREÑA", "MUNICIPALIDAD DISTRITAL DE CARABAYLLO",
        "MUNICIPALIDAD DISTRITAL DE CHACLACAYO", "MUNICIPALIDAD DISTRITAL DE CHORRILLOS",
        "MUNICIPALIDAD DISTRITAL DE CIENEGUILLA", "MUNICIPALIDAD DISTRITAL DE COMAS",
        "MUNICIPALIDAD DISTRITAL DE EL AGUSTINO", "MUNICIPALIDAD DISTRITAL DE INDEPENDENCIA",
        "MUNICIPALIDAD DISTRITAL DE JESUS MARIA", "MUNICIPALIDAD DISTRITAL DE LA MOLINA",
        "MUNICIPALIDAD DISTRITAL DE LA VICTORIA", "MUNICIPALIDAD DISTRITAL DE LINCE",
        "MUNICIPALIDAD DISTRITAL DE LOS OLIVOS", "MUNICIPALIDAD DISTRITAL DE LURIGANCHO",
        "MUNICIPALIDAD DISTRITAL DE LURIN", "MUNICIPALIDAD DISTRITAL DE MAGDALENA DEL MAR",
        "MUNICIPALIDAD DISTRITAL DE MAGDALENA VIEJA",  # = Pueblo Libre
        "MUNICIPALIDAD DISTRITAL DE PUEBLO LIBRE",
        "MUNICIPALIDAD DISTRITAL DE MIRAFLORES", "MUNICIPALIDAD DISTRITAL DE PACHACAMAC",
        "MUNICIPALIDAD DISTRITAL DE PUCUSANA", "MUNICIPALIDAD DISTRITAL DE PUENTE PIEDRA",
        "MUNICIPALIDAD DISTRITAL DE PUNTA HERMOSA", "MUNICIPALIDAD DISTRITAL DE PUNTA NEGRA",
        "MUNICIPALIDAD DISTRITAL DEL RIMAC", "MUNICIPALIDAD DISTRITAL DE RIMAC",
        "MUNICIPALIDAD DISTRITAL DE SAN BARTOLO", "MUNICIPALIDAD DISTRITAL DE SAN BORJA",
        "MUNICIPALIDAD DISTRITAL DE SAN ISIDRO", "MUNICIPALIDAD DISTRITAL DE SAN JUAN DE LURIGANCHO",
        "MUNICIPALIDAD DISTRITAL DE SAN JUAN DE MIRAFLORES", "MUNICIPALIDAD DISTRITAL DE SAN LUIS",
        "MUNICIPALIDAD DISTRITAL DE SAN MARTIN DE PORRES", "MUNICIPALIDAD DISTRITAL DE SAN MIGUEL",
        "MUNICIPALIDAD DISTRITAL DE SANTA ANITA", "MUNICIPALIDAD DISTRITAL DE SANTA MARIA DEL MAR",
        "MUNICIPALIDAD DISTRITAL DE SANTA ROSA", "MUNICIPALIDAD DISTRITAL DE SANTIAGO DE SURCO",
        "MUNICIPALIDAD DISTRITAL DE SURQUILLO", "MUNICIPALIDAD DISTRITAL DE VILLA EL SALVADOR",
        "MUNICIPALIDAD DISTRITAL DE VILLA MARIA DEL TRIUNFO",
        # Callao
        "MUNICIPALIDAD PROVINCIAL DEL CALLAO", "MUNICIPALIDAD PROVINCIAL DE CALLAO",
        "MUNICIPALIDAD DISTRITAL DE BELLAVISTA", "MUNICIPALIDAD DISTRITAL DE CARMEN DE LA LEGUA",
        "MUNICIPALIDAD DISTRITAL DE LA PERLA", "MUNICIPALIDAD DISTRITAL DE LA PUNTA",
        "MUNICIPALIDAD DISTRITAL DE VENTANILLA", "MUNICIPALIDAD DISTRITAL DE MI PERU",
    ]
    palabras_set = {p.upper() for p in palabras_mvp}

    # Normalizar agresivo: quitar siglas, sufijos geo, tildes, articulos sueltos
    import unicodedata
    def norm(s: str) -> str:
        s = re.sub(r"\s*\([^)]+\)\s*$", "", s)             # quita sigla final
        s = re.sub(r"\s*-\s*(LIMA|CALLAO).*$", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s+(LIMA|CALLAO)\s*$", "", s, flags=re.IGNORECASE)
        s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
        s = s.upper()
        s = re.sub(r"\bDEL\b", "DE", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    # Alias para nombres con sufijo legal/histórico (Chosica, Reynoso, Vieja)
    aliases_busqueda = {
        "MUNICIPALIDAD DISTRITAL DE LURIGANCHO": "MUNICIPALIDAD DISTRITAL DE LURIGANCHO-CHOSICA",
        "MUNICIPALIDAD DISTRITAL DE CARMEN DE LA LEGUA": "MUNICIPALIDAD DISTRITAL DE CARMEN DE LA LEGUA REYNOSO",
        "MUNICIPALIDAD DISTRITAL DE MAGDALENA VIEJA": "MUNICIPALIDAD DISTRITAL DE PUEBLO LIBRE",  # mismo distrito
    }

    indexed = {norm(nom): (id_ent, nom) for id_ent, nom in seen.items()}

    mvp_matches: list[tuple[str, str]] = []
    no_encontrados: list[str] = []
    visto: set[str] = set()
    for buscar in palabras_mvp:
        clave = aliases_busqueda.get(buscar, buscar)
        b = norm(clave)
        if b in indexed:
            id_ent, nom = indexed[b]
            if id_ent in visto:
                continue
            visto.add(id_ent)
            mvp_matches.append((id_ent, nom))
        else:
            no_encontrados.append(buscar)

    log("\n=== Entidades MVP encontradas ===")
    for id_ent, nombre in mvp_matches:
        log(f"  id_entidad={id_ent:>6}  {nombre}")
    log(f"\nTotal MVP: {len(mvp_matches)} / {len(palabras_mvp)}")

    if no_encontrados:
        log("\nNo encontradas (matching laxo necesario):")
        for n in no_encontrados:
            log(f"  - {n}")

    # CSV solo del MVP
    mvp_csv = dest / "mvp_lima_callao.csv"
    with mvp_csv.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id_entidad", "nombre"])
        for id_ent, nombre in mvp_matches:
            w.writerow([id_ent, nombre])
    log(f"\nCSV MVP: {mvp_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Ingesta las obras Infobras filtradas a obrascerca.

Lee scrapers/data/processed/obras_lima_3distritos_clean.csv y carga a:
    - entidad      (UPSERT por nombre_norm)
    - contratista  (UPSERT por RUC)
    - obra         (UPSERT por codigo_infobras)
    - obra_paralizacion  (para las marcadas con Existe Paralización = SI)
    - senal_revision     (tipo 'paralizacion')
    - fuente_dato        (registro de la ingesta)
"""
from __future__ import annotations

import io
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import psycopg
from psycopg.types.json import Json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "scrapers" / "data" / "processed" / "obras_mvp_50distritos.csv"
DSN = "host=localhost user=postgres password=123 dbname=obrascerca"
FUENTE_NOMBRE = "infobras_obras_publicas_2026-05-15"

# Alias: variaciones en Infobras → nombre canónico que está en el seed de distritos
DISTRITO_ALIAS = {
    "MAGDALENA VIEJA": "PUEBLO LIBRE",
    "CERCADO DE LIMA": "LIMA",
    "CERCADO": "LIMA",
}


def to_date(s):
    if pd.isna(s) or str(s).strip() in ("", "nan", "NaT"):
        return None
    try:
        return pd.to_datetime(s, dayfirst=True, errors="coerce").date()
    except Exception:
        return None


def to_num(s):
    if pd.isna(s):
        return None
    if isinstance(s, (int, float)):
        return float(s) if pd.notna(s) else None
    txt = str(s).strip().replace("%", "").strip()
    if not txt or txt.lower() in ("nan", "none"):
        return None
    txt = re.sub(r"^(\d+)\s+(\d+)$", r"\1.\2", txt)
    try:
        return float(txt)
    except ValueError:
        return None


def to_pct(s):
    """Igual que to_num pero satura a 9999.99 (cabe en NUMERIC(6,2)).

    Algunas filas de Infobras tienen valores de avance/financiero
    obviamente erróneos (>10000%). Para no perder la fila, capamos.
    """
    v = to_num(s)
    if v is None:
        return None
    if v > 9999.99:
        return 9999.99
    if v < -9999.99:
        return -9999.99
    return v


def to_int(s):
    n = to_num(s)
    return int(n) if n is not None else None


def to_text(s):
    if pd.isna(s):
        return None
    t = str(s).strip()
    return t if t and t.lower() != "nan" else None


def to_bool_si(s):
    if pd.isna(s):
        return False
    return str(s).strip().upper() == "SI"


def normalizar_distrito(s: str) -> str:
    raw = (s or "").strip().upper()
    return DISTRITO_ALIAS.get(raw, raw)


def main() -> int:
    if not CSV_PATH.exists():
        print(f"ERROR: no encuentro {CSV_PATH}")
        return 1

    print(f"Leyendo {CSV_PATH.name}...")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"  {len(df):,} filas")

    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            # Mapa distrito_nombre -> id (solo distritos MVP)
            cur.execute("SELECT id, distrito, provincia FROM distrito WHERE ambito_mvp")
            distrito_map = {(r[1].upper(), r[2].upper()): r[0] for r in cur.fetchall()}
            print(f"  {len(distrito_map)} distritos MVP en BD")

            # ----- Entidades únicas -----
            entidades = (
                df["Entidad Pública"]
                .dropna().astype(str).str.strip()
                .loc[lambda s: s != ""]
                .unique()
            )
            print(f"\nUpserting {len(entidades)} entidades únicas...")
            for nombre in entidades:
                cur.execute(
                    """
                    INSERT INTO entidad (nombre, nombre_norm, nivel_gobierno, sector)
                    VALUES (%s, %s, NULL, NULL)
                    ON CONFLICT (nombre_norm) DO NOTHING
                    """,
                    (nombre, nombre.upper())
                )

            # Mapa entidad_norm -> id
            cur.execute("SELECT id, nombre_norm FROM entidad")
            entidad_map = {r[1]: r[0] for r in cur.fetchall()}
            print(f"  total entidades en BD: {len(entidad_map)}")

            # ----- Contratistas únicos -----
            # Por filas hay RUC + razón social
            cdf = df[["RUC", "Nombre o razón social de la empresa o consorcio"]].dropna()
            cdf = cdf.assign(
                ruc=cdf["RUC"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True),
                razon=cdf["Nombre o razón social de la empresa o consorcio"].astype(str).str.strip(),
            )
            cdf = cdf[(cdf["ruc"].str.match(r"^\d{8,11}$")) & (cdf["razon"] != "")]
            cdf = cdf.drop_duplicates(subset=["ruc"])
            print(f"\nUpserting {len(cdf)} contratistas únicos...")
            for _, r in cdf.iterrows():
                cur.execute(
                    """
                    INSERT INTO contratista (ruc, razon_social)
                    VALUES (%s, %s)
                    ON CONFLICT (ruc) DO UPDATE SET razon_social = EXCLUDED.razon_social
                    """,
                    (r["ruc"], r["razon"])
                )
            cur.execute("SELECT id, ruc FROM contratista")
            contratista_map = {r[1]: r[0] for r in cur.fetchall()}
            print(f"  total contratistas en BD: {len(contratista_map)}")

            # ----- Obras -----
            print(f"\nUpserting {len(df)} obras...")
            insertadas = paralizadas_n = senales_n = 0
            for _, row in df.iterrows():
                cod_inf = to_int(row.get("Código INFOBRAS"))
                if not cod_inf:
                    continue
                dist_key = (normalizar_distrito(row.get("Distrito")), normalizar_distrito(row.get("Provincia")))
                distrito_id = distrito_map.get(dist_key)

                entidad_id = None
                ent_nombre = to_text(row.get("Entidad Pública"))
                if ent_nombre:
                    entidad_id = entidad_map.get(ent_nombre.upper())

                contratista_id = None
                ruc_raw = to_text(row.get("RUC"))
                if ruc_raw:
                    ruc = re.sub(r"\.0$", "", ruc_raw).strip()
                    if re.match(r"^\d{8,11}$", ruc):
                        contratista_id = contratista_map.get(ruc)

                existe_par = to_bool_si(row.get("Existe Paralización"))

                cur.execute(
                    """
                    INSERT INTO obra (
                        codigo_infobras, nombre, entidad_id, contratista_id, distrito_id,
                        direccion, tipo_ubicacion,
                        naturaleza, sector, estado_ejecucion,
                        fecha_inicio, fecha_fin_programada, fecha_ultimo_avance,
                        monto_contrato, monto_ejecutado,
                        avance_fisico_real, avance_fisico_programado, porcentaje_ejecucion_financiera,
                        existe_paralizacion,
                        fuente
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (codigo_infobras) DO UPDATE SET
                        nombre = EXCLUDED.nombre,
                        entidad_id = EXCLUDED.entidad_id,
                        contratista_id = EXCLUDED.contratista_id,
                        distrito_id = EXCLUDED.distrito_id,
                        direccion = EXCLUDED.direccion,
                        avance_fisico_real = EXCLUDED.avance_fisico_real,
                        avance_fisico_programado = EXCLUDED.avance_fisico_programado,
                        porcentaje_ejecucion_financiera = EXCLUDED.porcentaje_ejecucion_financiera,
                        existe_paralizacion = EXCLUDED.existe_paralizacion,
                        fuente = EXCLUDED.fuente,
                        ingestado_en = NOW()
                    RETURNING id
                    """,
                    (
                        cod_inf,
                        to_text(row.get("Nombre de obra")) or "(sin nombre)",
                        entidad_id, contratista_id, distrito_id,
                        to_text(row.get("Dirección o información de referencia")),
                        to_text(row.get("Tipo de ubicación (exacta/referencial)")),
                        to_text(row.get("Naturaleza de la obra")),
                        to_text(row.get("Sector de la Entidad")),
                        to_text(row.get("Estado de ejecución")),
                        to_date(row.get("Fecha de inicio de obra")),
                        to_date(row.get("Fecha finalización programada de obra")),
                        to_date(row.get("Fecha de registro de avance")),
                        to_num(row.get("Monto del contrato  en soles")),
                        to_num(row.get("Monto de valorización Ejecutado Acumulado")),
                        to_pct(row.get("Avance Físico Real Acumulado (%)_num")),
                        to_pct(row.get("Avance Físico Programado Acumulado (%)_num")),
                        to_pct(row.get("Porcentaje de ejecución financiera_num")),
                        existe_par,
                        FUENTE_NOMBRE,
                    )
                )
                obra_id = cur.fetchone()[0]
                insertadas += 1

                if existe_par:
                    fpar = to_date(row.get("Fecha de paralización"))
                    dias = to_int(row.get("Número de dias paralizado"))
                    causal = to_text(row.get("Causal de paralización"))
                    avf = to_pct(row.get("Avance Físico Real Acumulado (%)_num"))
                    avfin = to_pct(row.get("Porcentaje de ejecución financiera_num"))
                    cur.execute(
                        """
                        INSERT INTO obra_paralizacion
                            (obra_id, fecha_paralizacion, dias_paralizado, causal,
                             avance_fisico_al_par, avance_fin_al_par, fuente)
                        VALUES (%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (obra_id, fecha_paralizacion) DO UPDATE SET
                            dias_paralizado = EXCLUDED.dias_paralizado,
                            causal = EXCLUDED.causal
                        """,
                        (obra_id, fpar, dias, causal, avf, avfin, FUENTE_NOMBRE)
                    )
                    paralizadas_n += 1

                    # señal de revisión por paralización (prolongada si >180 días)
                    es_prolongada = (dias or 0) > 180
                    tipo = "paralizacion_prolongada" if es_prolongada else "paralizacion"
                    titulo = (
                        f"Obra paralizada hace {dias or '?'} días"
                        + (" (>180d)" if es_prolongada else "")
                    )
                    explicacion = (
                        f"Esta obra ({to_text(row.get('Naturaleza de la obra')) or 'tipo no reportado'}) "
                        f"lleva {dias or '?'} días sin avance reportado. "
                        f"Causal oficial: {causal or 'no reportada por la entidad'}. "
                        f"Avance al paralizar: {avf or 0:.0f}% físico, {avfin or 0:.0f}% financiero."
                    )
                    evidencia = {
                        "codigo_infobras": cod_inf,
                        "fecha_paralizacion": fpar.isoformat() if fpar else None,
                        "dias": dias,
                        "causal": causal,
                        "avance_fisico_real": avf,
                        "ejecucion_financiera": avfin,
                        "monto_contrato": to_num(row.get("Monto del contrato  en soles")),
                        "fuente": FUENTE_NOMBRE,
                        "infobras_url": f"https://infobras.contraloria.gob.pe/InfobrasWeb/Mapa/Sumario?ObraId={cod_inf}",
                    }
                    cur.execute(
                        """
                        INSERT INTO senal_revision
                            (tipo, obra_id, contratista_id, entidad_id, titulo, explicacion,
                             score, formula, evidencia)
                        VALUES (%s::tipo_senal, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            tipo, obra_id, contratista_id, entidad_id,
                            titulo, explicacion,
                            float(dias or 0),
                            "días_sin_avance >= 180 (Contraloría) — automático del campo 'Existe Paralización'",
                            Json(evidencia),
                        )
                    )
                    senales_n += 1

            # Registrar fuente
            cur.execute(
                """
                INSERT INTO fuente_dato (nombre, descripcion, url, ultima_ingestion, filas_ingestadas, notas)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT (nombre) DO UPDATE SET
                    ultima_ingestion = EXCLUDED.ultima_ingestion,
                    filas_ingestadas = EXCLUDED.filas_ingestadas
                """,
                (
                    FUENTE_NOMBRE,
                    "DataSet Obras Públicas — Infobras (Contraloría)",
                    "https://infobras.contraloria.gob.pe/InfobrasWeb/DataSets",
                    datetime.now(),
                    insertadas,
                    f"Filtrado MVP: 3 distritos piloto (LIMA, SAN ISIDRO, MIRAFLORES). {paralizadas_n} paralizadas, {senales_n} señales generadas.",
                )
            )

            conn.commit()
            print(f"\nObras ingestadas:    {insertadas}")
            print(f"Paralizaciones:      {paralizadas_n}")
            print(f"Señales generadas:   {senales_n}")

            # Resumen final
            cur.execute("SELECT distrito, total_obras, paralizadas, terminadas, avance_promedio FROM v_resumen_distrito ORDER BY total_obras DESC")
            print("\n=== Resumen por distrito (v_resumen_distrito) ===")
            print(f"{'distrito':<28} {'total':>6} {'paral':>6} {'term':>5} {'avg':>6}")
            for r in cur.fetchall():
                print(f"{(r[0] or ''):<28} {r[1] or 0:>6} {r[2] or 0:>6} {r[3] or 0:>5} {r[4] or 0:>6}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

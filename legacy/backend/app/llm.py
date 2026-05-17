"""Capa IA — explicación ciudadana.

PRINCIPIO (MD maestro §6.5 y §12): la IA **solo redacta**. Nunca decide,
nunca clasifica. Los hechos vienen del SQL; la IA los convierte en una
oración natural para el vecino.

Si la API se cae o no hay credenciales, devuelve un texto determinístico
basado en los mismos hechos. La app NUNCA queda muda por una caída del LLM.

Providers soportados:
    - stub      : texto determinístico (default; ideal para demos sin red)
    - minimax   : MiniMax-M2.7 (compatible Anthropic SDK con base_url custom)
    - anthropic : Claude Haiku 4.5
"""
from __future__ import annotations

from typing import Any

from .config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    LLM_PROVIDER,
    MINIMAX_API_KEY,
    MINIMAX_BASE_URL,
    MINIMAX_MODEL,
)

SYSTEM = (
    "Eres un periodista cívico peruano. Escribes en español, con voz neutral, "
    "para un vecino sin formación técnica. NO acuses, NO afirmes corrupción, "
    "NO inventes datos. Si un dato es nulo, omite la frase. Máximo 90 palabras. "
    "Cierra siempre con: 'Datos oficiales de Infobras al 2026-05-15.'"
)


def _stub_obra(hechos: dict) -> str:
    nombre = hechos.get("nombre") or "esta obra"
    distrito = hechos.get("distrito") or "el distrito"
    dias = hechos.get("dias_paralizada_real")
    causal = hechos.get("causal") or "no reportada por la entidad"
    avance = hechos.get("avance_fisico_real")
    monto = hechos.get("monto_contrato")
    entidad = hechos.get("entidad")
    clas = hechos.get("clasificacion")

    partes = []
    partes.append(f"{nombre} se ubica en {distrito}.")
    if entidad:
        partes.append(f"Es ejecutada por {entidad}.")
    if dias:
        partes.append(f"Está marcada como paralizada hace {dias} días.")
    if causal and causal != "no reportada por la entidad":
        partes.append(f"Causal oficial: {causal}.")
    if avance is not None:
        partes.append(f"Avance físico reportado: {float(avance):.0f}%.")
    if monto:
        try:
            partes.append(f"Monto del contrato: S/ {float(monto):,.0f}.")
        except (TypeError, ValueError):
            pass
    if clas == "zombie":
        partes.append("Atención: el registro lleva años sin actualizarse, podría no reflejar el estado actual.")
    elif clas == "dudosa":
        partes.append("Atención: el flag de paralización contradice avances recientes, vale revisar.")
    partes.append("Datos oficiales de Infobras al 2026-05-15.")
    return " ".join(partes)


def _stub_contratista(hechos: dict) -> str:
    razon = hechos.get("razon_social") or "Este contratista"
    ruc = hechos.get("ruc") or "—"
    obras_n = hechos.get("total_obras") or 0
    paral_n = hechos.get("obras_paralizadas") or 0
    top = hechos.get("top_concentracion") or {}
    pct = top.get("pct_monto")
    entidad = top.get("entidad")

    partes = [f"{razon} (RUC {ruc}) tiene {obras_n} obras registradas en Infobras."]
    if paral_n:
        partes.append(f"De ellas, {paral_n} están marcadas como paralizadas.")
    if pct and entidad:
        partes.append(
            f"En los últimos 12 meses concentra {pct}% del monto de compras menores ≤8 UIT de {entidad}."
        )
    partes.append("Datos oficiales de Infobras al 2026-05-15.")
    return " ".join(partes)


def _prompt_obra(hechos: dict) -> str:
    lines = ["Hechos verificados de la obra:"]
    for k in ("nombre", "distrito", "entidad", "naturaleza", "sector",
              "fecha_inicio", "fecha_fin_programada",
              "avance_fisico_real", "porcentaje_ejecucion_financiera",
              "monto_contrato", "monto_ejecutado",
              "existe_paralizacion", "clasificacion", "dias_paralizada_real",
              "causal", "fecha_paralizacion", "confirmada_contraloria"):
        if hechos.get(k) is not None:
            lines.append(f"- {k}: {hechos[k]}")
    lines.append("\nRedacta una explicación ciudadana de 2-3 frases (≤90 palabras).")
    return "\n".join(lines)


def _prompt_contratista(hechos: dict) -> str:
    lines = ["Hechos verificados del contratista:"]
    for k in ("razon_social", "ruc", "total_obras", "obras_paralizadas"):
        if hechos.get(k) is not None:
            lines.append(f"- {k}: {hechos[k]}")
    top = hechos.get("top_concentracion")
    if top:
        lines.append(f"- Concentración más alta: {top.get('pct_monto')}% del monto en {top.get('entidad')}, {top.get('n_ordenes')} órdenes")
    lines.append("\nRedacta una explicación ciudadana de 2-3 frases (≤90 palabras).")
    return "\n".join(lines)


def _call_anthropic_like(client, model: str, prompt: str) -> tuple[str, int, int]:
    resp = client.messages.create(
        model=model,
        max_tokens=400,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    texto = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    usage = getattr(resp, "usage", None)
    tin = getattr(usage, "input_tokens", None) if usage else None
    tout = getattr(usage, "output_tokens", None) if usage else None
    return texto.strip(), tin or 0, tout or 0


def generar_obra(hechos: dict) -> dict[str, Any]:
    """Devuelve {provider, modelo, texto, tokens_input, tokens_output}.

    Si el LLM falla por cualquier razón, cae al stub determinístico.
    """
    provider = LLM_PROVIDER
    if provider == "minimax" and MINIMAX_API_KEY:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=MINIMAX_API_KEY, base_url=MINIMAX_BASE_URL)
            t, ti, to = _call_anthropic_like(client, MINIMAX_MODEL, _prompt_obra(hechos))
            return {"provider": "minimax", "modelo": MINIMAX_MODEL, "texto": t,
                    "tokens_input": ti, "tokens_output": to}
        except Exception as e:
            return {"provider": "stub", "modelo": f"fallback_after_minimax_err:{type(e).__name__}",
                    "texto": _stub_obra(hechos), "tokens_input": 0, "tokens_output": 0}

    if provider == "anthropic" and ANTHROPIC_API_KEY:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            t, ti, to = _call_anthropic_like(client, ANTHROPIC_MODEL, _prompt_obra(hechos))
            return {"provider": "anthropic", "modelo": ANTHROPIC_MODEL, "texto": t,
                    "tokens_input": ti, "tokens_output": to}
        except Exception as e:
            return {"provider": "stub", "modelo": f"fallback_after_anthropic_err:{type(e).__name__}",
                    "texto": _stub_obra(hechos), "tokens_input": 0, "tokens_output": 0}

    return {"provider": "stub", "modelo": "deterministic_v1",
            "texto": _stub_obra(hechos), "tokens_input": 0, "tokens_output": 0}


def generar_contratista(hechos: dict) -> dict[str, Any]:
    provider = LLM_PROVIDER
    if provider == "minimax" and MINIMAX_API_KEY:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=MINIMAX_API_KEY, base_url=MINIMAX_BASE_URL)
            t, ti, to = _call_anthropic_like(client, MINIMAX_MODEL, _prompt_contratista(hechos))
            return {"provider": "minimax", "modelo": MINIMAX_MODEL, "texto": t,
                    "tokens_input": ti, "tokens_output": to}
        except Exception as e:
            return {"provider": "stub", "modelo": f"fallback:{type(e).__name__}",
                    "texto": _stub_contratista(hechos), "tokens_input": 0, "tokens_output": 0}

    if provider == "anthropic" and ANTHROPIC_API_KEY:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            t, ti, to = _call_anthropic_like(client, ANTHROPIC_MODEL, _prompt_contratista(hechos))
            return {"provider": "anthropic", "modelo": ANTHROPIC_MODEL, "texto": t,
                    "tokens_input": ti, "tokens_output": to}
        except Exception as e:
            return {"provider": "stub", "modelo": f"fallback:{type(e).__name__}",
                    "texto": _stub_contratista(hechos), "tokens_input": 0, "tokens_output": 0}

    return {"provider": "stub", "modelo": "deterministic_v1",
            "texto": _stub_contratista(hechos), "tokens_input": 0, "tokens_output": 0}

"""Capa IA — explicación ciudadana.

Principio (MD §6.5 y §12): la IA SOLO redacta. Los hechos vienen del SQL.
Si el LLM cae, devuelve texto determinístico construido con los mismos
hechos — la app nunca queda muda.

Providers: stub (default), minimax (compatible Anthropic SDK), anthropic.
"""
from __future__ import annotations

from typing import Any

from .config import (
    ANTHROPIC_API_KEY, ANTHROPIC_MODEL,
    LLM_PROVIDER,
    MINIMAX_API_KEY, MINIMAX_BASE_URL, MINIMAX_MODEL,
)

SYSTEM = (
    "Eres un periodista cívico peruano. Escribes en español, voz neutral, "
    "para un vecino sin formación técnica. NO acusas, NO afirmas corrupción, "
    "NO inventas datos. Si un dato es nulo, omites la frase. Máximo 90 palabras. "
    "Siempre cierras con: 'Datos cruzados de MEF/Invierte.pe + Infobras/Contraloría al 16-may-2026.'"
)


def _stub_obra(h: dict) -> str:
    nombre = h.get("nombre") or "Esta obra"
    distrito = h.get("distrito") or "el distrito"
    entidad = h.get("entidad")
    estado_mef = h.get("estado_mef")
    estado_wfs = h.get("estado_wfs")
    sobrecosto = h.get("sobrecosto_pct")
    avance_mef = h.get("avance_mef")
    avance_inf = h.get("avance_infobras")
    saldos = h.get("saldos_hijos") or 0
    informes = h.get("informes_control") or 0

    p = [f"{nombre} se ubica en {distrito}."]
    if entidad:
        p.append(f"Es ejecutada por {entidad}.")
    if estado_mef == "DESACTIVADO_PERMANENTE":
        p.append("El MEF la marca como **desactivada permanente** — el proyecto está oficialmente cerrado.")
    elif estado_wfs == "Paralizada":
        p.append("Contraloría WFS confirma que está **paralizada** hoy.")
    if avance_mef is not None and avance_inf is not None and abs(avance_mef - avance_inf) > 10:
        p.append(f"Hay discrepancia entre fuentes: MEF reporta {avance_mef:.0f}% y Infobras {avance_inf:.0f}%.")
    if sobrecosto is not None and sobrecosto > 30:
        p.append(f"Sobrecosto del {sobrecosto:.0f}% sobre el monto viable.")
    if saldos:
        p.append(f"Tiene {saldos} saldo(s) de obra vinculados — el contrato original quedó inconcluso.")
    if informes:
        p.append(f"Contraloría tiene {informes} informe(s) de control publicado(s) sobre esta obra.")
    p.append("Datos cruzados de MEF/Invierte.pe + Infobras/Contraloría al 16-may-2026.")
    return " ".join(p)


def _prompt_obra(h: dict) -> str:
    lines = ["Hechos verificados de la obra (cruzados desde 3 fuentes oficiales):"]
    for k, v in h.items():
        if v is not None:
            lines.append(f"- {k}: {v}")
    lines.append("\nRedacta 2-3 frases para un vecino peruano (≤90 palabras).")
    return "\n".join(lines)


def _llm_call(client, model: str, prompt: str) -> tuple[str, int, int]:
    resp = client.messages.create(
        model=model, max_tokens=400, system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    texto = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    usage = getattr(resp, "usage", None)
    return (texto.strip(),
            getattr(usage, "input_tokens", 0) or 0 if usage else 0,
            getattr(usage, "output_tokens", 0) or 0 if usage else 0)


def generar_obra(hechos: dict) -> dict[str, Any]:
    provider = LLM_PROVIDER
    if provider == "minimax" and MINIMAX_API_KEY:
        try:
            import anthropic
            c = anthropic.Anthropic(api_key=MINIMAX_API_KEY, base_url=MINIMAX_BASE_URL)
            t, ti, to = _llm_call(c, MINIMAX_MODEL, _prompt_obra(hechos))
            return {"provider": "minimax", "modelo": MINIMAX_MODEL, "texto": t,
                    "tokens_input": ti, "tokens_output": to}
        except Exception as e:
            return {"provider": "stub", "modelo": f"fallback:{type(e).__name__}",
                    "texto": _stub_obra(hechos), "tokens_input": 0, "tokens_output": 0}
    if provider == "anthropic" and ANTHROPIC_API_KEY:
        try:
            import anthropic
            c = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            t, ti, to = _llm_call(c, ANTHROPIC_MODEL, _prompt_obra(hechos))
            return {"provider": "anthropic", "modelo": ANTHROPIC_MODEL, "texto": t,
                    "tokens_input": ti, "tokens_output": to}
        except Exception as e:
            return {"provider": "stub", "modelo": f"fallback:{type(e).__name__}",
                    "texto": _stub_obra(hechos), "tokens_input": 0, "tokens_output": 0}
    return {"provider": "stub", "modelo": "deterministic_v1",
            "texto": _stub_obra(hechos), "tokens_input": 0, "tokens_output": 0}

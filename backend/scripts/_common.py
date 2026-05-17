"""Utilidades compartidas para los scripts de ingesta."""
from __future__ import annotations

import io
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # para 'app.clients...' funcione

# UTF-8 a stdout (Windows tiene cp1252 por defecto)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def norm(s: str | None) -> str:
    """Uppercase sin tildes; espacios colapsados; ideal para dedupe."""
    if not s:
        return ""
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = s.upper()
    s = " ".join(s.split())
    return s

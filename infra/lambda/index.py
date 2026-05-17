"""Lambda obras-cerca-trigger.

Disparada por EventBridge cron diario. Hace POST al endpoint del backend FastAPI
en la EC2, autenticada con un token compartido (env var INGESTA_TOKEN).

El backend responde 202 inmediatamente y arranca el pipeline en background.
La Lambda solo "toca el timbre" — la lógica pesada vive en la EC2.

Timeout configurado en Terraform: 30 segundos (suficiente para un POST + 202).
"""
from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone


BACKEND_URL = os.environ["BACKEND_URL"]          # https://obrascerca.trinitylabs.app
INGESTA_TOKEN = os.environ["INGESTA_TOKEN"]      # secret shared with backend


def lambda_handler(event, context):
    url = f"{BACKEND_URL.rstrip('/')}/api/admin/ingesta-diaria"
    req = urllib.request.Request(
        url,
        method="POST",
        headers={
            "X-Admin-Token": INGESTA_TOKEN,
            "Content-Type": "application/json",
            "User-Agent": "obras-cerca-cron/1.0",
        },
        data=json.dumps({
            "triggered_by": "eventbridge",
            "triggered_at": datetime.now(timezone.utc).isoformat(),
            "event_id": event.get("id", "unknown"),
        }).encode("utf-8"),
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8")
            return {
                "statusCode": resp.status,
                "body": body,
                "triggered_at": datetime.now(timezone.utc).isoformat(),
            }
    except urllib.error.HTTPError as e:
        return {
            "statusCode": e.code,
            "error": e.reason,
            "body": e.read().decode("utf-8", errors="replace"),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "error": str(e),
        }

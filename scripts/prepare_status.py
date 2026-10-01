"""Fetch only the allowlisted public summary for a GitHub Pages deployment."""

from __future__ import annotations

import json
import os
import pathlib
import urllib.request
from datetime import datetime, timezone

SOURCE = os.environ.get("STATUS_SOURCE_URL", "http://177.1.195.34/status.json")
DESTINATION = pathlib.Path(os.environ.get("STATUS_OUTPUT", "_site/status.json"))
ALLOWED_STATES = {"ok", "warning", "down", "unknown"}
SERVICE_IDS = ("freeturn", "mieru", "free_pool")


def main() -> None:
    try:
        with urllib.request.urlopen(SOURCE, timeout=10) as response:
            incoming = json.load(response)
        services = incoming["services"]
        checked_at = incoming["checked_at"]
        datetime.fromisoformat(checked_at.replace("Z", "+00:00"))
        output = {"checked_at": checked_at, "services": {}}
        for service_id in SERVICE_IDS:
            item = services[service_id]
            state = item["state"]
            if state not in ALLOWED_STATES:
                raise ValueError("invalid state")
            output["services"][service_id] = {
                "state": state,
                "summary": str(item.get("summary", ""))[:160],
                "detail": str(item.get("detail", ""))[:160],
            }
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        output = {
            "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "services": {service_id: {
                "state": "unknown", "summary": "Нет свежих данных с сервера.",
                "detail": "Следующая проверка запланирована через несколько минут.",
            } for service_id in SERVICE_IDS},
        }
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    DESTINATION.write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    main()

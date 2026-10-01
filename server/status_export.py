"""Public, credential-free status summary for the GitHub Pages collector."""

from __future__ import annotations

import json
import re
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "0.0.0.0"
PORT = 80
OPS_STATUS = "http://127.0.0.1:8766/status.json"
POOL_STATUS = "http://127.0.0.1:8080/api/probe-pool"


def read_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=2) as response:
        data = json.load(response)
    return data if isinstance(data, dict) else {}


def active(unit: str) -> bool:
    return subprocess.run(
        ["systemctl", "is-active", "--quiet", unit],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2,
    ).returncode == 0


def listening(port: int, udp: bool) -> bool:
    command = ["ss", "-H", "-uln" if udp else "-tln"]
    output = subprocess.run(command, capture_output=True, text=True, timeout=2).stdout
    return re.search(rf":{port}\s", output) is not None


def service_status(unit: str, port: int, udp: bool, name: str) -> dict:
    try:
        running = active(unit)
        socket_ready = listening(port, udp)
    except (OSError, subprocess.TimeoutExpired):
        return {"state": "unknown", "summary": "Проверка сервера недоступна.", "detail": "Повторим проверку через несколько минут."}
    if running and socket_ready:
        return {"state": "ok", "summary": f"Сервер {name} запущен и принимает соединения.",
                "detail": "Проверен серверный процесс и сетевой порт."}
    return {"state": "down", "summary": f"Сервер {name} сейчас недоступен.",
            "detail": "Процесс или сетевой порт не отвечает."}


def free_pool_status() -> dict:
    try:
        ops = read_json(OPS_STATUS)
        pool = read_json(POOL_STATUS)
        if not pool.get("available"):
            raise ValueError("pool metrics unavailable")
        last_cycle = int(ops.get("updated_at") or 0)
        if not last_cycle or time.time() - last_cycle > 20 * 60:
            return {"state": "warning", "summary": "Подборка не обновлялась более 20 минут.",
                    "detail": "Ожидаем свежих результатов проверки."}
        count = max(0, int(pool.get("de_test_pool") or 0))
        if count:
            return {"state": "ok", "summary": f"Подтверждено узлов: {count}.",
                    "detail": "Проверка выполнена на 177 и в Yandex Cloud."}
        return {"state": "warning", "summary": "Сейчас нет подтверждённых узлов.",
                "detail": "Новые кандидаты проходят проверку."}
    except (OSError, ValueError, TypeError, KeyError, TimeoutError):
        return {"state": "unknown", "summary": "Данные о подборке временно недоступны.",
                "detail": "Сервер повторит проверку автоматически."}


def collect() -> dict:
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "services": {
            "freeturn": service_status("free-turn-proxy", 56666, True, "FreeTurn"),
            "mieru": service_status("mita", 443, False, "Mieru"),
            "free_pool": free_pool_status(),
        },
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/status.json":
            self.send_error(404)
            return
        body = json.dumps(collect(), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args: object) -> None:
        pass


if __name__ == "__main__":
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()

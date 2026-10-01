"""Render the same publication locally: no client credentials or remote pages."""
import functools
import http.server
import json
import pathlib
import threading
from playwright.sync_api import sync_playwright

root = pathlib.Path("_site").resolve()
class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass

server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(root)))
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1000, "height": 900}, device_scale_factor=1.5)
        page.goto(f"http://127.0.0.1:{server.server_port}/", wait_until="networkidle")
        page.locator("#systems .service").first.wait_for(timeout=15000)
        page.locator('section[aria-labelledby="systems-title"]').screenshot(path=str(root / "status.png"))
        browser.close()
    data = json.loads((root / "status.json").read_text(encoding="utf-8"))
    (root / "status-image.json").write_text(json.dumps({"checked_at": data["checked_at"]}), encoding="utf-8")
finally:
    server.shutdown()

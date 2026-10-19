#!/usr/bin/env python3
"""Local dashboard for the data in dataExports/.

Usage:
    python3 dashboard/server.py [--port 8000] [--data PATH_TO_dataExports]

Then open http://localhost:8000. Uses only the Python standard library.
Data is re-read on every page load, so new downloads show up after a browser refresh.
"""

import argparse
import json
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
DEFAULT_DATA = HERE.parent / "dataExports"

STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
}

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'",
}


def load_items(data_dir):
    """Read every item folder under data_dir. Returns (items, warnings); bad folders become warnings."""
    items, warnings = [], []
    if not data_dir.is_dir():
        return items, [f"Data folder not found: {data_dir}"]
    for service_dir in sorted(p for p in data_dir.iterdir() if p.is_dir() and not p.name.startswith(("_", "."))):
        for item_dir in sorted(p for p in service_dir.iterdir() if p.is_dir() and not p.name.startswith(("_", "."))):
            label = f"{service_dir.name}/{item_dir.name}"
            try:
                meta = json.loads((item_dir / "metadata.json").read_text(encoding="utf-8"))
                content_path = item_dir / "content.md"
                content = content_path.read_text(encoding="utf-8") if content_path.is_file() else ""
                items.append({
                    "id": label,
                    "service": meta.get("service") or service_dir.name,
                    "type": meta.get("type", ""),
                    "title": meta.get("title", item_dir.name),
                    "author": meta.get("author", ""),
                    "time": meta.get("primaryTime"),
                    "url": meta.get("url"),
                    "exportedAt": meta.get("exportedAt"),
                    "fields": meta.get("fields", {}),
                    "content": content,
                    "folder": f"dataExports/{label}",
                })
            except (OSError, json.JSONDecodeError, AttributeError) as exc:
                warnings.append(f"Skipped {label}: {exc}")
    items.sort(key=lambda item: item["time"] or "", reverse=True)
    return items, warnings


class Handler(BaseHTTPRequestHandler):
    data_dir = DEFAULT_DATA

    def _send(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/items":
            items, warnings = load_items(self.data_dir)
            body = json.dumps({"items": items, "warnings": warnings, "dataDir": str(self.data_dir)}).encode("utf-8")
            self._send(HTTPStatus.OK, body, "application/json; charset=utf-8")
        elif path in STATIC_FILES:
            filename, content_type = STATIC_FILES[path]
            self._send(HTTPStatus.OK, (HERE / "static" / filename).read_bytes(), content_type)
        else:
            self._send(HTTPStatus.NOT_FOUND, b"Not found", "text/plain; charset=utf-8")

    do_HEAD = do_GET

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[dashboard] {self.address_string()} {fmt % args}\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="path to the dataExports folder")
    args = parser.parse_args()

    Handler.data_dir = args.data.resolve()
    # 127.0.0.1 only: the exported data never leaves this computer.
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Dashboard running at http://localhost:{args.port}  (data: {Handler.data_dir})")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()

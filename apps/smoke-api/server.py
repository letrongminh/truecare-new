from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    server_version = "truecare-new-smoke/1.0"

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self._json(200, {"status": "ok", "service": "api"})
            return
        if self.path == "/readyz":
            required = ["PUBLIC_API_BASE_URL"]
            missing = [name for name in required if not os.environ.get(name)]
            status = 503 if missing else 200
            self._json(status, {"status": "ready" if not missing else "not_ready", "missing": missing})
            return
        if self.path == "/metrics":
            body = "truecare_new_smoke_up 1\n"
            self.send_response(200)
            self.send_header("content-type", "text/plain; version=0.0.4")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
            return
        self._json(404, {"error": "not_found", "path": self.path})

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stdout.write("%s - %s\n" % (self.address_string(), fmt % args))
        sys.stdout.flush()

    def _json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_server() -> None:
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    signal.signal(signal.SIGTERM, lambda *_: server.shutdown())
    server.serve_forever()


def run_worker() -> None:
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    while True:
        print(json.dumps({"status": "ok", "service": "worker"}), flush=True)
        time.sleep(30)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    if args.worker:
        run_worker()
    run_server()


if __name__ == "__main__":
    main()

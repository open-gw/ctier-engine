#!/usr/bin/env python3
"""Echo the headers this process received. Harness fixture, not a product."""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import threading

HOST, PORT = "0.0.0.0", 8080
_LOCK = threading.Lock()
_LOG = []


class Echo(BaseHTTPRequestHandler):
    def do_GET(self):
        self._echo()

    def do_POST(self):
        self._echo()

    def do_PUT(self):
        self._echo()

    def do_PATCH(self):
        self._echo()

    def do_DELETE(self):
        self._echo()

    def do_HEAD(self):
        self._echo()

    def _echo(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw_body = self.rfile.read(length) if length else b""
        path = self.path.split("?", 1)[0]
        if path == "/_harness/requests":
            with _LOCK:
                payload = json.dumps(_LOG).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(payload)
            return
        record = {
            "method": self.command,
            "path": self.path,
            "headers": {k.lower(): v for k, v in self.headers.items()},
            "body": raw_body.decode("utf-8", "replace") if raw_body else None,
        }
        with _LOCK:
            _LOG.append(record)
        payload = json.dumps({
            "method": self.command,
            "path": self.path,
            "headers": record["headers"],
        }).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    def log_message(self, *_args):
        return


if __name__ == "__main__":
    HTTPServer((HOST, PORT), Echo).serve_forever()

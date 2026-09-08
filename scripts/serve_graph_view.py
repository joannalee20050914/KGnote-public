#!/usr/bin/env python3
"""Serve the static viewer plus one read-only graph-query endpoint."""

from __future__ import annotations

import argparse
import json
import mimetypes
import posixpath
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kgnote.visualization import load_graph_view  # noqa: E402

MAX_QUERY_BYTES = 32_768
HTTP_ERROR_VERSION = "kgnote.graph-view-http-error.v1"
SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}


def http_problem(code: str) -> dict[str, Any]:
    return {"schema_version": HTTP_ERROR_VERSION, "status": "rejected", "problem": {"code": code}}


def safe_static_path(request_path: str, static_root: Path) -> Path | None:
    try:
        root = static_root.resolve(strict=True)
        decoded = unquote(urlsplit(request_path).path, errors="strict")
    except (OSError, UnicodeError):
        return None
    if "\x00" in decoded or ".." in decoded.split("/"):
        return None
    normalized = posixpath.normpath(decoded)
    relative = normalized.lstrip("/") or "index.html"
    candidate = root.joinpath(*Path(relative).parts)
    current = root
    for part in Path(relative).parts:
        current = current / part
        if current.is_symlink():
            return None
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError):
        return None
    return resolved if resolved.is_file() and not candidate.is_symlink() else None


def execute_query(store_root: Path, body: bytes) -> tuple[int, dict[str, Any]]:
    if len(body) > MAX_QUERY_BYTES:
        return HTTPStatus.REQUEST_ENTITY_TOO_LARGE, http_problem("query_too_large")
    try:
        query = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return HTTPStatus.BAD_REQUEST, http_problem("invalid_json")
    try:
        result = load_graph_view(store_root, query)
    except Exception:
        return HTTPStatus.INTERNAL_SERVER_ERROR, http_problem("internal_error")
    return (HTTPStatus.OK if result.status == "ready" else HTTPStatus.BAD_REQUEST), result.response


def handler_for(store_root: Path, static_root: Path | None = None) -> type[BaseHTTPRequestHandler]:
    allowed_static_root = static_root or ROOT / "web"

    class GraphViewHandler(BaseHTTPRequestHandler):
        def send_response(self, code: int, message: str | None = None) -> None:
            self.log_request(code)
            self.send_response_only(code, message)

        def _send_json(self, status: int, payload: dict[str, Any]) -> None:
            encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(encoded)

        def _reject(self, status: int, code: str) -> None:
            self._send_json(status, http_problem(code))

        def end_headers(self) -> None:
            for name, value in SECURITY_HEADERS.items():
                self.send_header(name, value)
            super().end_headers()

        def do_GET(self) -> None:  # noqa: N802
            path = safe_static_path(self.path, allowed_static_root)
            if path is None:
                self._reject(HTTPStatus.NOT_FOUND, "not_found")
                return
            try:
                content = path.read_bytes()
            except OSError:
                self._reject(HTTPStatus.NOT_FOUND, "not_found")
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def do_HEAD(self) -> None:  # noqa: N802
            path = safe_static_path(self.path, allowed_static_root)
            if path is None:
                self._reject(HTTPStatus.NOT_FOUND, "not_found")
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(path.stat().st_size))
            self.end_headers()

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/api/graph-view":
                self._reject(HTTPStatus.NOT_FOUND, "not_found")
                return
            if self.headers.get_content_type() != "application/json":
                self._reject(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "json_content_type_required")
                return
            try:
                raw_length = self.headers.get("Content-Length")
                length = int(raw_length) if raw_length is not None else -1
            except ValueError:
                length = -1
            if length < 0:
                status, payload = HTTPStatus.BAD_REQUEST, http_problem("invalid_content_length")
            elif length > MAX_QUERY_BYTES:
                status, payload = HTTPStatus.REQUEST_ENTITY_TOO_LARGE, http_problem("query_too_large")
            else:
                status, payload = execute_query(store_root, self.rfile.read(length))
            self._send_json(status, payload)

        def do_PUT(self) -> None: self._reject(HTTPStatus.METHOD_NOT_ALLOWED, "method_not_allowed")  # noqa: N802,E701
        def do_PATCH(self) -> None: self._reject(HTTPStatus.METHOD_NOT_ALLOWED, "method_not_allowed")  # noqa: N802,E701
        def do_DELETE(self) -> None: self._reject(HTTPStatus.METHOD_NOT_ALLOWED, "method_not_allowed")  # noqa: N802,E701
        def do_OPTIONS(self) -> None: self._reject(HTTPStatus.METHOD_NOT_ALLOWED, "method_not_allowed")  # noqa: N802,E701
        def do_TRACE(self) -> None: self._reject(HTTPStatus.METHOD_NOT_ALLOWED, "method_not_allowed")  # noqa: N802,E701
        def do_CONNECT(self) -> None: self._reject(HTTPStatus.METHOD_NOT_ALLOWED, "method_not_allowed")  # noqa: N802,E701

        def log_message(self, format: str, *args: object) -> None:
            return

    return GraphViewHandler


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", required=True)
    parser.add_argument("--port", type=int, default=4173)
    args = parser.parse_args()
    store_root = Path(args.store)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(store_root))
    print(f"Serving KGnote read-only graph at http://127.0.0.1:{args.port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

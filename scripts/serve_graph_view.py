#!/usr/bin/env python3
"""Serve the static viewer plus one read-only graph-query endpoint."""

from __future__ import annotations

import argparse
import json
import os
import sys
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kgnote.visualization import load_graph_view  # noqa: E402

MAX_QUERY_BYTES = 32_768


def execute_query(store_root: Path, body: bytes) -> tuple[int, dict[str, Any]]:
    if len(body) > MAX_QUERY_BYTES:
        return HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"status": "rejected", "problem": {"code": "query_too_large"}}
    try:
        query = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return HTTPStatus.BAD_REQUEST, {"status": "rejected", "problem": {"code": "invalid_json"}}
    result = load_graph_view(store_root, query)
    return (HTTPStatus.OK if result.status == "ready" else HTTPStatus.BAD_REQUEST), result.response


def handler_for(store_root: Path) -> type[SimpleHTTPRequestHandler]:
    class GraphViewHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, directory=str(ROOT / "web"), **kwargs)

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/api/graph-view":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if length < 0 or length > MAX_QUERY_BYTES:
                status, payload = HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"status": "rejected", "problem": {"code": "query_too_large"}}
            else:
                status, payload = execute_query(store_root, self.rfile.read(length))
            encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, format: str, *args: object) -> None:
            return

    return GraphViewHandler


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", required=True)
    parser.add_argument("--port", type=int, default=4173)
    args = parser.parse_args()
    store_root = Path(args.store)
    os.chdir(ROOT)
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

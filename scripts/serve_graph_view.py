#!/usr/bin/env python3
"""Serve the static viewer plus bounded local application endpoints."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import mimetypes
import posixpath
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kgnote.visualization import load_graph_view  # noqa: E402
from kgnote.review import (  # noqa: E402
    act_on_due,
    append_feedback,
    append_guided_review,
    append_review,
    build_practice_set,
    build_review_prompt,
    list_attempts,
    list_exposures,
    list_due,
    read_attempt,
    read_feedback,
    record_exposure,
    reveal_practice_answer,
    save_attempt,
    schedule_after_feedback,
    due_exposure_signal,
    validate_attempt_request,
    validate_attempt_against_practice_set,
)
from kgnote.learning import latest_resume_context, load_learning_unit_catalog, prior_encounters, record_resume_context  # noqa: E402
from kgnote.notes import read_note, save_note, search_notes  # noqa: E402
from kgnote.reader import load_reader  # noqa: E402

MAX_QUERY_BYTES = 32_768
MAX_NOTE_BYTES = 300_000
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


def execute_review(store_root: Path, body: bytes) -> tuple[int, dict[str, Any]]:
    if len(body) > MAX_QUERY_BYTES:
        return HTTPStatus.REQUEST_ENTITY_TOO_LARGE, http_problem("review_too_large")
    try:
        request = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return HTTPStatus.BAD_REQUEST, http_problem("invalid_json")
    try:
        result = append_review(store_root, request)
    except Exception:
        return HTTPStatus.INTERNAL_SERVER_ERROR, http_problem("internal_error")
    payload = {"schema_version": "kgnote.review-http.v1", "status": result.status, **result.payload}
    if result.problem_code:
        payload["problem"] = {"code": result.problem_code}
    return (HTTPStatus.OK if result.status in {"recorded", "unchanged"} else HTTPStatus.BAD_REQUEST), payload


def execute_guided_review(review_root: Path, guided_map_model: dict[str, Any], body: bytes) -> tuple[int, dict[str, Any]]:
    if len(body) > MAX_QUERY_BYTES:
        return HTTPStatus.REQUEST_ENTITY_TOO_LARGE, http_problem("review_too_large")
    try:
        request = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return HTTPStatus.BAD_REQUEST, http_problem("invalid_json")
    try:
        result = append_guided_review(review_root, guided_map_model, request)
    except Exception:
        return HTTPStatus.INTERNAL_SERVER_ERROR, http_problem("internal_error")
    payload = {"schema_version": "kgnote.guided-review-http.v1", "status": result.status, **result.payload}
    if result.problem_code:
        payload["problem"] = {"code": result.problem_code}
    return (HTTPStatus.OK if result.status in {"recorded", "unchanged"} else HTTPStatus.BAD_REQUEST), payload


def _note_http_payload(result) -> dict[str, Any]:
    payload = {"status": result.status, **result.payload}
    if result.problem_code:
        payload["problem"] = {"code": result.problem_code}
    return payload


def execute_note_read(notes_root: Path, note_id: str) -> tuple[int, dict[str, Any], dict[str, str]]:
    result = read_note(notes_root, note_id)
    status = {
        "ready": HTTPStatus.OK, "not_found": HTTPStatus.NOT_FOUND,
        "rejected": HTTPStatus.BAD_REQUEST, "failed": HTTPStatus.INTERNAL_SERVER_ERROR,
    }[result.status]
    headers = {"ETag": result.payload["etag"]} if result.status == "ready" else {}
    return status, _note_http_payload(result), headers


def execute_note_search(notes_root: Path, notebook_id: str, query: str) -> tuple[int, dict[str, Any]]:
    result = search_notes(notes_root, notebook_id, query)
    status = HTTPStatus.OK if result.status == "ready" else (
        HTTPStatus.INTERNAL_SERVER_ERROR if result.status == "failed" else HTTPStatus.BAD_REQUEST
    )
    return status, _note_http_payload(result)


def execute_note_save(
    notes_root: Path, note_id: str, body: bytes, if_match: str | None,
) -> tuple[int, dict[str, Any], dict[str, str]]:
    if len(body) > MAX_NOTE_BYTES:
        return HTTPStatus.REQUEST_ENTITY_TOO_LARGE, http_problem("note_too_large"), {}
    try:
        request = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return HTTPStatus.BAD_REQUEST, http_problem("invalid_json"), {}
    if not isinstance(request, dict) or request.get("note_id") != note_id:
        return HTTPStatus.BAD_REQUEST, http_problem("note_path_mismatch"), {}
    try:
        result = save_note(notes_root, request, if_match=if_match)
    except Exception:
        return HTTPStatus.INTERNAL_SERVER_ERROR, http_problem("internal_error"), {}
    status = {
        "saved": HTTPStatus.CREATED if result.payload.get("created") else HTTPStatus.OK,
        "unchanged": HTTPStatus.OK,
        "conflict": HTTPStatus.PRECONDITION_FAILED,
        "rejected": HTTPStatus.BAD_REQUEST,
        "failed": HTTPStatus.INTERNAL_SERVER_ERROR,
    }[result.status]
    headers = {"ETag": result.payload["etag"]} if result.payload.get("etag") else {}
    return status, _note_http_payload(result), headers


def execute_note_source(store_root: Path, source_id: str, locator: str) -> tuple[int, dict[str, Any]]:
    graph = load_graph_view(store_root)
    if graph.status != "ready":
        return HTTPStatus.BAD_REQUEST, http_problem("source_store_unavailable")
    query = {
        "schema_version": "kgnote.reader-query.v1",
        "snapshot_sha256": graph.response["view"]["snapshot_sha256"],
        "source_id": source_id,
        "locator": {"kind": "line_range", "value": locator},
    }
    result = load_reader(store_root, query)
    return (HTTPStatus.OK if result.status == "ready" else HTTPStatus.BAD_REQUEST), result.response


def _application_payload(version: str, result) -> dict[str, Any]:
    payload = {"schema_version": version, "status": result.status, **result.payload}
    if result.problem_code:
        payload["problem"] = {"code": result.problem_code}
    return payload


def execute_practice_items(
    guided_map_model: dict[str, Any], claim_review_overlay: dict[str, Any], supplement: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    result = build_practice_set(guided_map_model, claim_review_overlay, supplement)
    return (
        HTTPStatus.OK if result.status == "ready" else HTTPStatus.BAD_REQUEST,
        _application_payload("kgnote.practice-http.v1", result),
    )


def execute_attempt_list(attempts_root: Path, learning_unit_id: str) -> tuple[int, dict[str, Any]]:
    result = list_attempts(attempts_root, learning_unit_id)
    if result.status == "ready":
        payload = result.payload
        for attempt in payload["attempts"]:
            feedback = read_feedback(attempts_root, attempt["attempt_id"])
            attempt["feedback"] = feedback.payload if feedback.status == "ready" else {"events": [], "latest": None}
        result = type(result)(result.status, json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")), result.problem_code)
    status = {"ready": HTTPStatus.OK, "rejected": HTTPStatus.BAD_REQUEST, "failed": HTTPStatus.INTERNAL_SERVER_ERROR}[result.status]
    return status, _application_payload("kgnote.attempt-http.v1", result)


def execute_attempt_save(
    attempts_root: Path,
    guided_map_model: dict[str, Any],
    claim_review_overlay: dict[str, Any],
    attempt_id: str,
    body: bytes,
    supplement: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    if len(body) > MAX_QUERY_BYTES:
        return HTTPStatus.REQUEST_ENTITY_TOO_LARGE, http_problem("attempt_too_large")
    try:
        request = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return HTTPStatus.BAD_REQUEST, http_problem("invalid_json")
    if not isinstance(request, dict) or request.get("attempt_id") != attempt_id:
        return HTTPStatus.BAD_REQUEST, http_problem("attempt_path_mismatch")
    request_problem = validate_attempt_request(request)
    if request_problem:
        return HTTPStatus.BAD_REQUEST, http_problem(request_problem)
    stale_problem = validate_attempt_against_practice_set(guided_map_model, claim_review_overlay, request, supplement)
    if stale_problem:
        return HTTPStatus.CONFLICT, http_problem(stale_problem)
    result = save_attempt(attempts_root, request)
    status = {
        "saved": HTTPStatus.CREATED if result.payload.get("created") else HTTPStatus.OK,
        "unchanged": HTTPStatus.OK,
        "conflict": HTTPStatus.CONFLICT,
        "rejected": HTTPStatus.BAD_REQUEST,
        "failed": HTTPStatus.INTERNAL_SERVER_ERROR,
    }[result.status]
    payload = _application_payload("kgnote.attempt-http.v1", result)
    if result.status in {"saved", "unchanged"} and request.get("state") == "submitted":
        reveal = reveal_practice_answer(guided_map_model, claim_review_overlay, request["review_item_id"], supplement)
        if reveal.status != "ready":
            return HTTPStatus.CONFLICT, http_problem("practice_answer_unavailable")
        payload["reveal"] = reveal.payload
    return status, payload


def execute_feedback_save(attempts_root: Path, attempt_id: str, body: bytes) -> tuple[int, dict[str, Any]]:
    if len(body) > MAX_QUERY_BYTES:
        return HTTPStatus.REQUEST_ENTITY_TOO_LARGE, http_problem("feedback_too_large")
    try:
        request = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return HTTPStatus.BAD_REQUEST, http_problem("invalid_json")
    if not isinstance(request, dict) or request.get("attempt_id") != attempt_id:
        return HTTPStatus.BAD_REQUEST, http_problem("feedback_path_mismatch")
    attempt_result = read_attempt(attempts_root, attempt_id)
    if attempt_result.status != "ready":
        return HTTPStatus.NOT_FOUND, http_problem(attempt_result.problem_code or "unknown_attempt")
    result = append_feedback(attempts_root, request, attempt_result.payload["attempt"])
    status = {"recorded": HTTPStatus.CREATED, "unchanged": HTTPStatus.OK, "conflict": HTTPStatus.CONFLICT,
              "rejected": HTTPStatus.BAD_REQUEST, "failed": HTTPStatus.INTERNAL_SERVER_ERROR}[result.status]
    payload = _application_payload("kgnote.attempt-feedback-http.v1", result)
    if result.status in {"recorded", "unchanged"}:
        schedule = schedule_after_feedback(attempts_root, attempt_result.payload["attempt"], result.payload.get("latest") or result.payload["event"])
        payload["schedule"] = _application_payload("kgnote.due-http.v1", schedule)
    return status, payload


def execute_due_list(attempts_root: Path, now: str) -> tuple[int, dict[str, Any]]:
    result = list_due(attempts_root, now=now)
    status = HTTPStatus.OK if result.status == "ready" else HTTPStatus.BAD_REQUEST
    return status, _application_payload("kgnote.due-http.v1", result)


def execute_due_action(attempts_root: Path, body: bytes) -> tuple[int, dict[str, Any]]:
    if len(body) > MAX_QUERY_BYTES:
        return HTTPStatus.REQUEST_ENTITY_TOO_LARGE, http_problem("due_action_too_large")
    try:
        request = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return HTTPStatus.BAD_REQUEST, http_problem("invalid_json")
    result = act_on_due(attempts_root, request)
    status = {"saved": HTTPStatus.OK, "unchanged": HTTPStatus.OK, "conflict": HTTPStatus.CONFLICT,
              "rejected": HTTPStatus.BAD_REQUEST, "failed": HTTPStatus.INTERNAL_SERVER_ERROR}[result.status]
    return status, _application_payload("kgnote.due-http.v1", result)


def execute_exposure_save(attempts_root: Path, body: bytes, learning_units: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    try:
        request = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return HTTPStatus.BAD_REQUEST, http_problem("invalid_json")
    if learning_units is not None and isinstance(request, dict):
        bundle = next((value for value in learning_units.values() if value["catalog"]["unit_id"] == request.get("learning_unit_id")), None)
        item = next((value for value in bundle["soak"]["items"] if value["item_id"] == request.get("item_id")), None) if bundle else None
        if item is None or request.get("concept_id") != item["concept_id"] or request.get("source_refs") != item["source_refs"]:
            return HTTPStatus.CONFLICT, http_problem("stale_or_unknown_exposure_item")
    result = record_exposure(attempts_root, request)
    status = {"recorded": HTTPStatus.CREATED, "unchanged": HTTPStatus.OK, "conflict": HTTPStatus.CONFLICT,
              "rejected": HTTPStatus.BAD_REQUEST, "failed": HTTPStatus.INTERNAL_SERVER_ERROR}[result.status]
    return status, _application_payload("kgnote.exposure-http.v1", result)


def execute_exposure_list(attempts_root: Path, learning_unit_id: str) -> tuple[int, dict[str, Any]]:
    result = list_exposures(attempts_root, learning_unit_id)
    status = HTTPStatus.OK if result.status == "ready" else (HTTPStatus.BAD_REQUEST if result.status == "rejected" else HTTPStatus.INTERNAL_SERVER_ERROR)
    return status, _application_payload("kgnote.exposure-http.v1", result)


def execute_resume_save(attempts_root: Path, body: bytes, learning_units: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    try: request=json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError,json.JSONDecodeError): return HTTPStatus.BAD_REQUEST,http_problem("invalid_json")
    bundle=next((value for slug,value in learning_units.items() if slug==request.get("unit_slug") and value["catalog"]["unit_id"]==request.get("learning_unit_id")),None) if isinstance(request,dict) else None
    if bundle is None:return HTTPStatus.CONFLICT,http_problem("unknown_resume_unit")
    nodes={node["id"]:node for node in bundle["structure"]["nodes"]}; breadcrumb=request.get("structural_breadcrumb",[])
    valid_chain=isinstance(breadcrumb,list) and bool(breadcrumb)
    if valid_chain:
        for index,item in enumerate(breadcrumb):
            node=nodes.get(item.get("node_id")) if isinstance(item,dict) else None
            expected_parent=None if index==0 else breadcrumb[index-1].get("node_id")
            if node is None or node.get("title")!=item.get("title") or node.get("parent_id")!=expected_parent:
                valid_chain=False;break
        leaf=nodes.get(breadcrumb[-1].get("node_id")) if valid_chain else None
        scope=request.get("source_scope",{})
        valid_chain=bool(leaf and scope.get("source_id")==bundle["model"]["source"]["id"] and any(anchor["locator"]["value"]==scope.get("locator") for anchor in leaf["source_anchors"]))
    if not valid_chain:
        return HTTPStatus.CONFLICT,http_problem("stale_resume_structure")
    result=record_resume_context(attempts_root,request)
    status={"recorded":HTTPStatus.CREATED,"unchanged":HTTPStatus.OK,"conflict":HTTPStatus.CONFLICT,"rejected":HTTPStatus.BAD_REQUEST,"failed":HTTPStatus.INTERNAL_SERVER_ERROR}[result.status]
    return status,_application_payload("kgnote.resume-context-http.v1",result)


def execute_resume_read(attempts_root: Path, learning_unit_id: str) -> tuple[int, dict[str, Any]]:
    result=latest_resume_context(attempts_root,learning_unit_id)
    if result.status!="ready":
        return (HTTPStatus.BAD_REQUEST if result.status=="rejected" else HTTPStatus.INTERNAL_SERVER_ERROR),_application_payload("kgnote.resume-context-http.v1",result)
    payload=result.payload; attempts=list_attempts(attempts_root,learning_unit_id); exposures=list_exposures(attempts_root,learning_unit_id)
    payload["latest_attempt"]=(attempts.payload.get("attempts") or [None])[0] if attempts.status=="ready" else None
    payload["latest_exposure"]=(exposures.payload.get("events") or [None])[0] if exposures.status=="ready" else None
    return HTTPStatus.OK,{"schema_version":"kgnote.resume-context-http.v1","status":"ready",**payload}


def handler_for(
    store_root: Path,
    static_root: Path | None = None,
    *,
    guided_map_model: dict[str, Any] | None = None,
    guided_review_root: Path | None = None,
    notes_root: Path | None = None,
    note_writes_enabled: bool = False,
    claim_review_overlay: dict[str, Any] | None = None,
    attempts_root: Path | None = None,
    learning_units: dict[str, Any] | None = None,
) -> type[BaseHTTPRequestHandler]:
    allowed_static_root = static_root or ROOT / "web"

    class GraphViewHandler(BaseHTTPRequestHandler):
        def send_response(self, code: int, message: str | None = None) -> None:
            self.log_request(code)
            self.send_response_only(code, message)

        def _send_json(self, status: int, payload: dict[str, Any], headers: dict[str, str] | None = None) -> None:
            encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            for name, value in (headers or {}).items():
                self.send_header(name, value)
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
            parsed = urlsplit(self.path)
            if learning_units is not None and parsed.path == "/api/learning-units":
                if parsed.query:
                    self._reject(HTTPStatus.BAD_REQUEST, "invalid_learning_unit_query")
                    return
                self._send_json(HTTPStatus.OK, {
                    "schema_version": "kgnote.learning-unit-catalog-http.v1", "status": "ready",
                    "units": [bundle["catalog"] | {
                        "practice_items_count": len(bundle["practice"]["items"]),
                        "soak_items_count": len(bundle["soak"]["items"]),
                        "reviewed_claims_count": sum(review["teaching_answer_status"] == "ready" for review in bundle["claim_reviews"]["reviews"]),
                    } for bundle in learning_units.values()],
                })
                return
            if learning_units is not None and parsed.path.startswith("/api/learning-units/"):
                slug = unquote(parsed.path.removeprefix("/api/learning-units/"))
                if "/" in slug or parsed.query or slug not in learning_units:
                    self._reject(HTTPStatus.NOT_FOUND, "unknown_learning_unit")
                    return
                bundle = learning_units[slug]
                reading_assist = json.loads(json.dumps(bundle["reading_assist"], ensure_ascii=False))
                history_events = []
                if attempts_root is not None:
                    for other_slug, other_bundle in learning_units.items():
                        if other_slug == slug:
                            continue
                        exposure_result = list_exposures(attempts_root, other_bundle["catalog"]["unit_id"])
                        if exposure_result.status == "ready":
                            history_events.extend(exposure_result.payload["events"])
                reading_assist["prior_encounters"] = prior_encounters(reading_assist, history_events, current_unit_id=bundle["catalog"]["unit_id"])
                self._send_json(HTTPStatus.OK, {
                    "schema_version": "kgnote.learning-unit-bundle-http.v1", "status": "ready",
                    "unit": bundle["catalog"], "model": bundle["model"], "source_text": bundle["source_text"],
                    "claim_reviews": bundle["claim_reviews"], "structure": bundle["structure"],
                    "reading_assist": reading_assist, "degradations": bundle.get("degradations", []),
                })
                return
            if parsed.path == "/api/practice-items" and (
                learning_units is not None or (guided_map_model is not None and claim_review_overlay is not None)
            ):
                parameters = parse_qs(parsed.query, keep_blank_values=True)
                if learning_units is not None:
                    if set(parameters) != {"unit"} or len(parameters["unit"]) != 1 or parameters["unit"][0] not in learning_units:
                        self._reject(HTTPStatus.BAD_REQUEST, "invalid_practice_query")
                        return
                    bundle = learning_units[parameters["unit"][0]]
                    status, payload = execute_practice_items(bundle["model"], bundle["claim_reviews"], bundle["practice_supplement"])
                else:
                    if parsed.query:
                        self._reject(HTTPStatus.BAD_REQUEST, "invalid_practice_query")
                        return
                    status, payload = execute_practice_items(guided_map_model, claim_review_overlay)
                self._send_json(status, payload)
                return
            if learning_units is not None and parsed.path == "/api/soak-items":
                parameters = parse_qs(parsed.query, keep_blank_values=True)
                if set(parameters) != {"unit"} or len(parameters["unit"]) != 1 or parameters["unit"][0] not in learning_units:
                    self._reject(HTTPStatus.BAD_REQUEST, "invalid_soak_query")
                    return
                bundle = learning_units[parameters["unit"][0]]
                self._send_json(HTTPStatus.OK, {"schema_version":"kgnote.soak-http.v1", "status":"ready", "learning_unit_id":bundle["catalog"]["unit_id"], "items":bundle["soak"]["items"]})
                return
            if attempts_root is not None and parsed.path == "/api/exposures":
                parameters = parse_qs(parsed.query, keep_blank_values=True)
                if set(parameters) != {"learning_unit_id"} or len(parameters["learning_unit_id"]) != 1:
                    self._reject(HTTPStatus.BAD_REQUEST, "invalid_exposure_query")
                    return
                status, payload = execute_exposure_list(attempts_root, parameters["learning_unit_id"][0])
                self._send_json(status, payload)
                return
            if attempts_root is not None and parsed.path == "/api/resume-contexts":
                parameters=parse_qs(parsed.query,keep_blank_values=True)
                if set(parameters)!={"learning_unit_id"} or len(parameters["learning_unit_id"])!=1:
                    self._reject(HTTPStatus.BAD_REQUEST,"invalid_resume_query");return
                status,payload=execute_resume_read(attempts_root,parameters["learning_unit_id"][0]);self._send_json(status,payload);return
            if attempts_root is not None and parsed.path == "/api/due":
                parameters = parse_qs(parsed.query, keep_blank_values=True)
                if set(parameters) - {"now"} or any(len(values) != 1 for values in parameters.values()):
                    self._reject(HTTPStatus.BAD_REQUEST, "invalid_due_query")
                    return
                now = parameters.get("now", [dt.datetime.now(dt.timezone.utc).isoformat()])[0]
                status, payload = execute_due_list(attempts_root, now)
                if status == HTTPStatus.OK and learning_units is not None:
                    index = {item["item_id"]: (slug, item) for slug, bundle in learning_units.items() for item in bundle["practice"]["items"]}
                    exposure_cache = {}
                    for due in payload["items"]:
                        found = index.get(due["review_item_id"])
                        due["blocked"] = found is None
                        if found:
                            due["unit_slug"], item = found
                            due["label"] = item["label"]
                            due["activity_type"] = item["activity_type"]
                            bundle = learning_units[due["unit_slug"]]
                            related_soak_ids = {soak["item_id"] for soak in bundle["soak"]["items"] if soak["related_practice_item_id"] == due["review_item_id"]}
                            if due["learning_unit_id"] not in exposure_cache:
                                exposure_cache[due["learning_unit_id"]] = list_exposures(attempts_root, due["learning_unit_id"])
                            exposure_result = exposure_cache[due["learning_unit_id"]]
                            if exposure_result.status == "ready":
                                matching = [event for event in exposure_result.payload["events"] if event["item_id"] in related_soak_ids]
                                due["exposure_signal"] = due_exposure_signal(due, matching)
                            else:
                                due["exposure_signal"] = None
                                due["exposure_signal_unavailable"] = True
                self._send_json(status, payload)
                return
            if attempts_root is not None and parsed.path == "/api/attempts":
                parameters = parse_qs(parsed.query, keep_blank_values=True)
                if set(parameters) != {"learning_unit_id"} or len(parameters["learning_unit_id"]) != 1:
                    self._reject(HTTPStatus.BAD_REQUEST, "invalid_attempt_query")
                    return
                status, payload = execute_attempt_list(attempts_root, parameters["learning_unit_id"][0])
                self._send_json(status, payload)
                return
            if notes_root is not None and parsed.path == "/api/notes":
                parameters = parse_qs(parsed.query, keep_blank_values=True)
                if set(parameters) != {"notebook_id", "q"} or any(len(values) != 1 for values in parameters.values()):
                    self._reject(HTTPStatus.BAD_REQUEST, "invalid_note_search")
                    return
                status, payload = execute_note_search(notes_root, parameters["notebook_id"][0], parameters["q"][0])
                self._send_json(status, payload)
                return
            if notes_root is not None and parsed.path.startswith("/api/notes/"):
                note_id = unquote(parsed.path.removeprefix("/api/notes/"))
                if "/" in note_id or parsed.query:
                    self._reject(HTTPStatus.NOT_FOUND, "not_found")
                    return
                status, payload, headers = execute_note_read(notes_root, note_id)
                self._send_json(status, payload, headers)
                return
            if notes_root is not None and parsed.path.startswith("/api/note-sources/"):
                source_id = unquote(parsed.path.removeprefix("/api/note-sources/"))
                parameters = parse_qs(parsed.query, keep_blank_values=True)
                if "/" in source_id or set(parameters) != {"locator"} or len(parameters["locator"]) != 1:
                    self._reject(HTTPStatus.BAD_REQUEST, "invalid_source_anchor")
                    return
                status, payload = execute_note_source(store_root, source_id, parameters["locator"][0])
                self._send_json(status, payload)
                return
            if parsed.path == "/api/review-prompt":
                concept_id = parsed.query.removeprefix("concept_id=") if parsed.query.startswith("concept_id=") else ""
                result = build_review_prompt(store_root, unquote(concept_id))
                payload = {"schema_version": "kgnote.review-http.v1", "status": result.status, **result.payload}
                if result.problem_code:
                    payload["problem"] = {"code": result.problem_code}
                self._send_json(HTTPStatus.OK if result.status == "ready" else HTTPStatus.BAD_REQUEST, payload)
                return
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
            allowed = {"/api/graph-view", "/api/reviews"}
            if guided_map_model is not None and guided_review_root is not None:
                allowed.add("/api/guided-reviews")
            parsed = urlsplit(self.path)
            is_feedback = parsed.path.startswith("/api/attempts/") and parsed.path.endswith("/feedback")
            if attempts_root is not None:
                allowed.add("/api/due-actions")
                allowed.add("/api/exposures")
                if learning_units is not None:
                    allowed.add("/api/resume-contexts")
            if self.path not in allowed and not is_feedback:
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
                body = self.rfile.read(length)
                if is_feedback:
                    attempt_id = unquote(parsed.path.removeprefix("/api/attempts/").removesuffix("/feedback"))
                    if "/" in attempt_id or parsed.query or attempts_root is None:
                        status, payload = HTTPStatus.NOT_FOUND, http_problem("not_found")
                    else:
                        status, payload = execute_feedback_save(attempts_root, attempt_id, body)
                elif self.path == "/api/due-actions":
                    status, payload = execute_due_action(attempts_root, body)
                elif self.path == "/api/exposures":
                    status, payload = execute_exposure_save(attempts_root, body, learning_units)
                elif self.path == "/api/resume-contexts" and learning_units is not None:
                    status, payload = execute_resume_save(attempts_root, body, learning_units)
                elif self.path == "/api/graph-view":
                    status, payload = execute_query(store_root, body)
                elif self.path == "/api/reviews":
                    status, payload = execute_review(store_root, body)
                else:
                    status, payload = execute_guided_review(guided_review_root, guided_map_model, body)
            self._send_json(status, payload)

        def do_PUT(self) -> None:  # noqa: N802
            parsed = urlsplit(self.path)
            if parsed.path.startswith("/api/attempts/"):
                if attempts_root is None or (learning_units is None and (guided_map_model is None or claim_review_overlay is None)):
                    self._reject(HTTPStatus.NOT_FOUND, "not_found")
                    return
                attempt_id = unquote(parsed.path.removeprefix("/api/attempts/"))
                if "/" in attempt_id or parsed.query:
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
                    status, payload = HTTPStatus.REQUEST_ENTITY_TOO_LARGE, http_problem("attempt_too_large")
                else:
                    body = self.rfile.read(length)
                    if learning_units is None:
                        status, payload = execute_attempt_save(attempts_root, guided_map_model, claim_review_overlay, attempt_id, body)
                    else:
                        try:
                            unit_id = json.loads(body.decode("utf-8")).get("learning_unit_id")
                        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
                            unit_id = None
                        bundle = next((item for item in learning_units.values() if item["catalog"]["unit_id"] == unit_id), None)
                        if bundle is None:
                            status, payload = HTTPStatus.BAD_REQUEST, http_problem("unknown_learning_unit")
                        else:
                            status, payload = execute_attempt_save(
                                attempts_root, bundle["model"], bundle["claim_reviews"], attempt_id, body, bundle["practice_supplement"],
                            )
                self._send_json(status, payload)
                return
            if notes_root is None and parsed.path.startswith("/api/notes/"):
                self._reject(HTTPStatus.NOT_FOUND, "not_found")
                return
            if not parsed.path.startswith("/api/notes/"):
                self._reject(HTTPStatus.METHOD_NOT_ALLOWED, "method_not_allowed")
                return
            if not note_writes_enabled:
                self._reject(HTTPStatus.METHOD_NOT_ALLOWED, "note_writes_disabled")
                return
            note_id = unquote(parsed.path.removeprefix("/api/notes/"))
            if "/" in note_id or parsed.query:
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
                status, payload, headers = HTTPStatus.BAD_REQUEST, http_problem("invalid_content_length"), {}
            elif length > MAX_NOTE_BYTES:
                status, payload, headers = HTTPStatus.REQUEST_ENTITY_TOO_LARGE, http_problem("note_too_large"), {}
            else:
                status, payload, headers = execute_note_save(
                    notes_root, note_id, self.rfile.read(length), self.headers.get("If-Match"),
                )
            self._send_json(status, payload, headers)
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
    parser.add_argument("--guided-map-model", help="Explicit server-trusted Guided Map read-model JSON for Edge reviews.")
    parser.add_argument("--guided-review-root", help="Explicit local directory for append-only Guided Map reviews.")
    parser.add_argument("--notes-root", help="Explicit notebook root containing the authoritative notes/ directory.")
    parser.add_argument("--enable-note-writes", action="store_true", help="Enable ETag-guarded LearningNote PUT routes.")
    parser.add_argument("--claim-review-overlay", help="Snapshot-bound ClaimReview overlay used to gate practice items.")
    parser.add_argument("--learning-unit-catalog", help="Bounded catalog for the multi-unit Learn and Practice surfaces.")
    parser.add_argument("--attempts-root", help="Local root for machine-managed Attempt v1 records.")
    parser.add_argument(
        "--host", choices=("127.0.0.1", "0.0.0.0"), default="127.0.0.1",
        help="Use 0.0.0.0 only for trusted local-network access.",
    )
    args = parser.parse_args()
    store_root = Path(args.store)
    if bool(args.guided_map_model) != bool(args.guided_review_root):
        parser.error("--guided-map-model and --guided-review-root must be provided together")
    if args.claim_review_overlay and not args.attempts_root:
        parser.error("--claim-review-overlay requires --attempts-root")
    if args.learning_unit_catalog and not args.attempts_root:
        parser.error("--learning-unit-catalog requires --attempts-root")
    if args.claim_review_overlay and not args.guided_map_model:
        parser.error("practice configuration requires --guided-map-model")
    if args.enable_note_writes and not args.notes_root:
        parser.error("--enable-note-writes requires --notes-root")
    guided_map_model = None
    guided_review_root = None
    if args.guided_map_model:
        try:
            guided_map_model = json.loads(Path(args.guided_map_model).read_text(encoding="utf-8"))
            guided_review_root = Path(args.guided_review_root)
            guided_review_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            parser.error(f"guided review configuration unavailable: {type(error).__name__}")
    notes_root = None
    if args.notes_root:
        try:
            notes_root = Path(args.notes_root)
            notes_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        except OSError as error:
            parser.error(f"notes configuration unavailable: {type(error).__name__}")
    claim_review_overlay = None
    attempts_root = None
    if args.claim_review_overlay:
        try:
            claim_review_overlay = json.loads(Path(args.claim_review_overlay).read_text(encoding="utf-8"))
            attempts_root = Path(args.attempts_root)
            attempts_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            parser.error(f"practice configuration unavailable: {type(error).__name__}")
    elif args.attempts_root:
        try:
            attempts_root = Path(args.attempts_root)
            attempts_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        except OSError as error:
            parser.error(f"attempt configuration unavailable: {type(error).__name__}")
    learning_units = None
    if args.learning_unit_catalog:
        catalog_result = load_learning_unit_catalog(args.learning_unit_catalog)
        if catalog_result.status != "ready":
            parser.error(f"learning unit catalog unavailable: {catalog_result.problem_code}")
        learning_units = catalog_result.payload["bundles"]
    server = ThreadingHTTPServer(
        (args.host, args.port),
        handler_for(
            store_root, guided_map_model=guided_map_model, guided_review_root=guided_review_root,
            notes_root=notes_root, note_writes_enabled=args.enable_note_writes,
            claim_review_overlay=claim_review_overlay, attempts_root=attempts_root,
            learning_units=learning_units,
        ),
    )
    location = "this Mac's local-network IP" if args.host == "0.0.0.0" else "127.0.0.1"
    print(f"KGnote Learn: http://{location}:{args.port}/learn.html", flush=True)
    print(f"KGnote Practice: http://{location}:{args.port}/practice.html", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Extract trusted provider and usage evidence from ``codex exec --json``.

Arbitrary agent messages and command output are intentionally ignored for
failure classification.  Only Codex JSONL ``error``/``turn.failed`` events can
carry provider failure evidence; this prevents documentation mentioning 429,
quota, or rate limits from changing recovery policy.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any


PROVIDER_FAILURE_PREFIX = "KGNOTE_PROVIDER_FAILURE="
RATE_LIMIT_CODES = {"rate_limit_exceeded", "rate_limited", "too_many_requests"}
QUOTA_CODES = {"insufficient_quota", "quota_exhausted"}
USAGE_LIMIT_CODES = {"usage_limit_reached", "usage_limit_exceeded"}


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _nested_error(event: dict[str, Any]) -> dict[str, Any]:
    raw = event.get("error")
    if isinstance(raw, dict):
        return raw
    response = event.get("response")
    if isinstance(response, dict) and isinstance(response.get("error"), dict):
        return response["error"]
    return event


def _text(error: dict[str, Any], event: dict[str, Any]) -> str:
    for source in (error, event):
        for key in ("message", "detail", "error_message"):
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def _integer(error: dict[str, Any], event: dict[str, Any], *keys: str) -> int | None:
    for source in (error, event):
        for key in keys:
            value = source.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                return value
            if isinstance(value, str) and value.isdigit():
                return int(value)
    return None


def _string(error: dict[str, Any], event: dict[str, Any], *keys: str) -> str | None:
    for source in (error, event):
        for key in keys:
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def provider_failure_from_event(event: object) -> dict[str, Any] | None:
    """Return bounded evidence only for a structured Codex failure event."""
    if not isinstance(event, dict) or event.get("type") not in {"error", "turn.failed"}:
        return None
    error = _nested_error(event)
    code = (_string(error, event, "code", "error_code", "type") or "").lower()
    status = _integer(error, event, "http_status", "status_code", "status")
    message = _text(error, event)
    lowered = message.lower()
    if code in USAGE_LIMIT_CODES or "usage limit" in lowered:
        failure_class = "USAGE_LIMIT_REACHED"
    elif code in QUOTA_CODES or "insufficient quota" in lowered or "quota exhausted" in lowered:
        failure_class = "QUOTA_EXHAUSTED"
    elif code in RATE_LIMIT_CODES or status == 429 or re.search(r"\b(?:http\s*)?429\b", lowered) or "rate limit" in lowered:
        failure_class = "RATE_LIMITED"
    else:
        return None
    evidence: dict[str, Any] = {
        "schema_version": "kgnote.provider-failure-evidence.v1",
        "source": "codex_jsonl_structured_event",
        "event_type": event["type"],
        "failure_class": failure_class,
        "code": code or None,
        "http_status": status,
        "message_sha256": hashlib.sha256(message.encode()).hexdigest() if message else None,
        "event_sha256": hashlib.sha256(_canonical(event)).hexdigest(),
        "retry_after_seconds": _integer(error, event, "retry_after_seconds", "retry_after"),
        "retry_at": _string(error, event, "retry_at", "reset_at", "resets_at"),
    }
    return evidence


def parse_codex_jsonl(value: str) -> dict[str, Any]:
    """Summarize JSONL without treating nested transcript text as evidence."""
    event_count = 0
    completed = False
    usage: dict[str, int] | None = None
    provider_failure: dict[str, Any] | None = None
    for line in value.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict) or not isinstance(event.get("type"), str):
            continue
        event_count += 1
        if event["type"] == "turn.completed":
            completed = True
            raw_usage = event.get("usage")
            if isinstance(raw_usage, dict):
                input_tokens = raw_usage.get("input_tokens")
                output_tokens = raw_usage.get("output_tokens")
                if all(
                    isinstance(item, int) and not isinstance(item, bool) and item >= 0
                    for item in (input_tokens, output_tokens)
                ):
                    usage = {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                    }
        candidate = provider_failure_from_event(event)
        if candidate is not None:
            provider_failure = candidate
    return {
        "schema_version": "kgnote.codex-jsonl-summary.v1",
        "event_count": event_count,
        "turn_completed": completed,
        "usage": usage,
        "provider_failure": provider_failure,
    }


def provider_failure_from_output(value: str) -> dict[str, Any] | None:
    """Re-derive evidence from JSONL; wrapper-looking output is not trusted."""
    return parse_codex_jsonl(value)["provider_failure"]

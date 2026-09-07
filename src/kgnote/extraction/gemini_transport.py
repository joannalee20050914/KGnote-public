"""Single-request Gemini transport for the provider-neutral extraction boundary."""

from __future__ import annotations

import json
import socket
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from kgnote.extraction.run_adapter import (
    TransportConfig,
    TransportFailure,
    TransportResponse,
)


GEMINI_PROVIDER = "google-gemini"
GEMINI_MODEL = "gemini-3.7-flash"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

# Provider-facing candidate schema. Adapter-owned provenance fields are deliberately absent.
GEMINI_CANDIDATE_SCHEMA: Mapping[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["concepts", "evidence", "learning_events", "edges"],
    "properties": {
        "concepts": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["local_ref", "name", "aliases", "spaces", "summary", "evidence_refs", "extraction_confidence"],
                "properties": {
                    "local_ref": {"type": "string"}, "name": {"type": "string"},
                    "aliases": {"type": "array", "items": {"type": "string"}},
                    "spaces": {"type": "array", "minItems": 1, "items": {"type": "string"}},
                    "summary": {"type": "string"},
                    "evidence_refs": {"type": "array", "minItems": 1, "items": {"type": "string"}},
                    "extraction_confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                },
            },
        },
        "evidence": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["local_ref", "locator", "proposition", "observed_at", "extraction_confidence"],
                "properties": {
                    "local_ref": {"type": "string"},
                    "locator": {
                        "type": "object", "additionalProperties": False,
                        "required": ["kind", "value"],
                        "properties": {
                            "kind": {"type": "string", "enum": ["line_range", "heading", "message", "page", "timestamp", "whole_source"]},
                            "value": {"type": "string"},
                        },
                    },
                    "proposition": {"type": "string"},
                    "observed_at": {"anyOf": [{"type": "string", "format": "date-time"}, {"type": "null"}]},
                    "extraction_confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                },
            },
        },
        "learning_events": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["local_ref", "locator", "event_type", "occurred_at", "context", "concept_refs", "evidence_refs", "extraction_confidence"],
                "properties": {
                    "local_ref": {"type": "string"},
                    "locator": {"$ref": "#/$defs/locator"},
                    "event_type": {"type": "string", "enum": ["exposure", "question", "confusion", "explanation", "application", "assessment"]},
                    "occurred_at": {"anyOf": [{"type": "string", "format": "date-time"}, {"type": "null"}]},
                    "context": {"type": "string"},
                    "concept_refs": {"type": "array", "minItems": 1, "items": {"type": "string"}},
                    "evidence_refs": {"type": "array", "minItems": 1, "items": {"type": "string"}},
                    "extraction_confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                },
            },
        },
        "edges": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["local_ref", "source_ref", "relation", "target_ref", "edge_class", "evidence_refs", "confidence"],
                "properties": {
                    "local_ref": {"type": "string"}, "source_ref": {"type": "string"},
                    "relation": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "target_ref": {"type": "string"},
                    "edge_class": {"type": "string", "enum": ["canonical", "learning", "soft_association"]},
                    "evidence_refs": {"type": "array", "minItems": 1, "items": {"type": "string"}},
                    "confidence": {"type": "string", "enum": ["high", "medium", "low", "unresolved"]},
                },
            },
        },
    },
    "$defs": {
        "locator": {
            "type": "object", "additionalProperties": False,
            "required": ["kind", "value"],
            "properties": {
                "kind": {"type": "string", "enum": ["line_range", "heading", "message", "page", "timestamp", "whole_source"]},
                "value": {"type": "string"},
            },
        }
    },
}


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _map_http_error(status: int) -> str:
    if status in {401, 403}:
        return "authentication_error"
    if status == 429:
        return "rate_limit"
    return "provider_error"


@dataclass(frozen=True, repr=False)
class GeminiExtractionTransport:
    """Explicit-credential, non-streaming Gemini REST transport with no retries."""

    api_key: str = field(repr=False)
    opener: Callable[..., Any] = field(default=urlopen, repr=False)
    api_base: str = GEMINI_API_BASE

    def __post_init__(self) -> None:
        if not isinstance(self.api_key, str) or not self.api_key.strip():
            raise ValueError("gemini_api_key_required")
        if not callable(self.opener):
            raise ValueError("invalid_opener")
        if self.api_base != GEMINI_API_BASE:
            raise ValueError("unsupported_gemini_api_base")

    def __call__(
        self, envelope: Mapping[str, Any], config: TransportConfig
    ) -> TransportResponse:
        if config.provider != GEMINI_PROVIDER or config.model != GEMINI_MODEL:
            raise TransportFailure("transport_error")
        request_body = {
            "contents": [{"role": "user", "parts": [{"text": _json_bytes(envelope).decode("utf-8")}]}],
            "generationConfig": {
                "candidateCount": 1,
                "maxOutputTokens": 8192,
                "responseMimeType": "application/json",
                "responseJsonSchema": GEMINI_CANDIDATE_SCHEMA,
            },
            "systemInstruction": {
                "parts": [{"text": "Extract only claims supported by the supplied source. Return only the requested JSON. Never infer mastery or understanding from mention, exposure, questions, or explanations."}]
            },
        }
        request = Request(
            f"{self.api_base}/models/{quote(config.model, safe='')}:generateContent",
            data=_json_bytes(request_body), method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key},
        )
        try:
            with self.opener(request, timeout=config.timeout_seconds) as response:
                provider_payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            raise TransportFailure(_map_http_error(error.code)) from None
        except (TimeoutError, socket.timeout):
            raise TimeoutError from None
        except (URLError, OSError):
            raise TransportFailure("transport_error") from None
        except (UnicodeError, json.JSONDecodeError, AttributeError, TypeError):
            raise TransportFailure("provider_error") from None

        try:
            candidates = provider_payload["candidates"]
            if len(candidates) != 1:
                raise ValueError
            parts = candidates[0]["content"]["parts"]
            if len(parts) != 1 or not isinstance(parts[0]["text"], str):
                raise ValueError
            raw_response = parts[0]["text"].encode("utf-8")
            request_id = provider_payload.get("responseId")
            usage_payload = provider_payload.get("usageMetadata")
            usage = None
            if isinstance(usage_payload, dict):
                names = {
                    "promptTokenCount": "input_tokens",
                    "candidatesTokenCount": "output_tokens",
                    "totalTokenCount": "total_tokens",
                }
                if all(name in usage_payload for name in names):
                    usage = {mapped: int(usage_payload[name]) for name, mapped in names.items()}
        except (KeyError, TypeError, ValueError, OverflowError):
            raise TransportFailure("provider_error") from None
        return TransportResponse(
            raw_response=raw_response, provider=GEMINI_PROVIDER, model=GEMINI_MODEL,
            request_id=request_id if isinstance(request_id, str) else None, usage=usage,
        )

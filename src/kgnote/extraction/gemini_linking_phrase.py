"""Single-request Gemini transport for linking-phrase proposals."""

from __future__ import annotations

import json
import socket
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from kgnote.extraction.gemini_transport import GEMINI_API_BASE, GEMINI_MODEL, GEMINI_PROVIDER
from kgnote.extraction.run_adapter import TransportConfig, TransportFailure, TransportResponse


PHRASE_SCHEMA: Mapping[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["proposals"],
    "properties": {
        "proposals": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["edge_id", "linking_phrase"],
                "properties": {
                    "edge_id": {"type": "string"},
                    "linking_phrase": {"type": "string"},
                },
            },
        }
    },
}


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


@dataclass(frozen=True, repr=False)
class GeminiLinkingPhraseTransport:
    """Explicit-credential, non-streaming Gemini REST transport with no retries."""

    api_key: str = field(repr=False)
    opener: Callable[..., Any] = field(default=urlopen, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.api_key, str) or not self.api_key.strip():
            raise ValueError("gemini_api_key_required")
        if not callable(self.opener):
            raise ValueError("invalid_opener")

    def __call__(
        self, envelope: Mapping[str, Any], config: TransportConfig,
    ) -> TransportResponse:
        if config.provider != GEMINI_PROVIDER or config.model != GEMINI_MODEL:
            raise TransportFailure("transport_error")
        body = {
            "contents": [{
                "role": "user",
                "parts": [{"text": _json_bytes(envelope).decode("utf-8")}],
            }],
            "generationConfig": {
                "candidateCount": 1,
                "maxOutputTokens": 2048,
                "responseMimeType": "application/json",
                "responseJsonSchema": PHRASE_SCHEMA,
            },
            "systemInstruction": {"parts": [{
                "text": "For every supplied directed Edge, propose one concise learner-facing linking phrase grounded only in its Evidence. Preserve direction. Return only edge_id and linking_phrase. Do not score understanding."
            }]},
        }
        request = Request(
            f"{GEMINI_API_BASE}/models/{quote(config.model, safe='')}:generateContent",
            data=_json_bytes(body), method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key},
        )
        try:
            with self.opener(request, timeout=config.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            code = "authentication_error" if error.code in {401, 403} else "rate_limit" if error.code == 429 else "provider_error"
            raise TransportFailure(code) from None
        except (TimeoutError, socket.timeout):
            raise TimeoutError from None
        except (URLError, OSError):
            raise TransportFailure("transport_error") from None
        except (UnicodeError, json.JSONDecodeError, AttributeError, TypeError):
            raise TransportFailure("provider_error") from None

        try:
            candidates = payload["candidates"]
            if len(candidates) != 1:
                raise ValueError
            parts = candidates[0]["content"]["parts"]
            if len(parts) != 1 or not isinstance(parts[0]["text"], str):
                raise ValueError
            usage_payload = payload.get("usageMetadata")
            usage = None
            if isinstance(usage_payload, dict):
                names = {
                    "promptTokenCount": "input_tokens",
                    "candidatesTokenCount": "output_tokens",
                    "totalTokenCount": "total_tokens",
                }
                if all(name in usage_payload for name in names):
                    usage = {mapped: int(usage_payload[name]) for name, mapped in names.items()}
            request_id = payload.get("responseId")
            return TransportResponse(
                raw_response=parts[0]["text"].encode(), provider=GEMINI_PROVIDER,
                model=GEMINI_MODEL,
                request_id=request_id if isinstance(request_id, str) else None,
                usage=usage,
            )
        except (KeyError, TypeError, ValueError, OverflowError):
            raise TransportFailure("provider_error") from None


__all__ = ["GeminiLinkingPhraseTransport", "PHRASE_SCHEMA"]

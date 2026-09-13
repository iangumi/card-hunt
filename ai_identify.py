
from __future__ import annotations

import json
import mimetypes
import os
import random
import time
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

DEFAULT_MAX_ATTEMPTS = 4
RETRY_DELAYS_SECONDS = (2.0, 5.0, 10.0)

IDENTIFICATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "card_name": {"type": ["string", "null"]},
        "card_number": {"type": ["string", "null"]},
        "set_or_promo": {"type": ["string", "null"]},
        "year": {"type": ["integer", "null"]},
        "language": {"type": ["string", "null"]},
        "variant": {"type": ["string", "null"]},
        "raw_or_slab": {
            "anyOf": [
                {"type": "string", "enum": ["raw", "slab"]},
                {"type": "null"},
            ]
        },
        "grade": {"type": ["string", "null"]},
        "store_price_jpy": {"type": ["integer", "null"]},
        "req_count": {"type": "integer", "minimum": 0},
        "status_hint": {
            "type": "string",
            "enum": ["available", "requested", "sold", "unknown"]
        },
        "id_confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "price_confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "req_confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "needs_review": {"type": "boolean"},
        "review_reason": {"type": ["string", "null"]},
        "possible_matches": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 5
        },
        "visible_evidence": {"type": "string"},
    },
    "required": [
        "card_name", "card_number", "set_or_promo", "year", "language", "variant",
        "raw_or_slab", "grade", "store_price_jpy", "req_count", "status_hint",
        "id_confidence", "price_confidence", "req_confidence", "needs_review",
        "review_reason", "possible_matches", "visible_evidence"
    ],
}

IDENTIFICATION_INSTRUCTIONS = """
You are the identification stage of a Pokémon card hunt system.

Your job is ONLY to identify the exact visible card/variant and extract store metadata.
Do not estimate market value and do not recommend buying.

Be conservative. Wrong variant identification is more harmful than returning "needs review".

Identification priorities:
1. Read exact printed card number where visible.
2. Distinguish Japanese promo/set/edition/variant, rarity symbols, holo/reverse/glossy,
   old-back/new-back, first edition/unlimited, special stamps, slab label, etc.
3. Use visible artwork, attacks, illustrator, set symbols, printed number and label text as evidence.
4. If the exact card number/variant is not visible and multiple plausible prints exist,
   set needs_review=true and list possible_matches.
5. Never invent a card number, year, set, price, grade, or req count.
6. A shop label such as "1 req", "2 req", "1 request", etc. means requested by other buyers.
   Extract that integer as req_count. If no request marking is visible, use 0 but lower
   req_confidence when the label area is cropped/unclear.
7. Extract store price in Japanese yen when visibly shown. Return null when unreadable.
8. raw_or_slab is "slab" only when a grading holder/label is visibly present.
9. id_confidence refers to confidence in the exact print/variant, not just the Pokémon species.
10. visible_evidence should briefly state the concrete visual clues you relied on.

Use Japanese text when it is useful evidence, but normalize card_name/set names to readable English
when confidently known.
""".strip()


def _image_part(path: str | Path) -> types.Part:
    p = Path(path)
    mime = mimetypes.guess_type(p.name)[0] or "image/jpeg"
    return types.Part.from_bytes(data=p.read_bytes(), mime_type=mime)


def parse_identification(payload: Any) -> dict:
    """Normalize Gemini's schema-constrained response without provider-specific models."""
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        result = json.loads(payload)
        if isinstance(result, dict):
            return result
    raise ValueError("AI provider returned an invalid structured identification response.")


def _usage_metadata(response: Any, model: str) -> dict:
    usage = getattr(response, "usage_metadata", None)
    result = {
        "provider": "gemini",
        "model": getattr(response, "model_version", None) or model,
        "response_id": getattr(response, "response_id", None),
    }
    if usage is not None:
        result.update({
            "input_tokens": getattr(usage, "prompt_token_count", None),
            "output_tokens": getattr(usage, "candidates_token_count", None),
            "total_tokens": getattr(usage, "total_token_count", None),
            "cached_tokens": getattr(usage, "cached_content_token_count", None),
            "thought_tokens": getattr(usage, "thoughts_token_count", None),
        })
    return {key: value for key, value in result.items() if value is not None}


def api_ready() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


def _error_details(error: Exception) -> tuple[int | str | None, str, bool]:
    code = getattr(error, "code", None)
    if code is None:
        code = getattr(error, "status_code", None)
    try:
        normalized_code: int | str | None = int(code) if code is not None else None
    except (TypeError, ValueError):
        normalized_code = str(code) if code is not None else None

    status = getattr(error, "status", None)
    status_name = getattr(status, "name", status)
    status_text = str(status_name or "").upper()
    transient = normalized_code == 503 or status_text == "UNAVAILABLE"

    reason = getattr(error, "message", None) or str(error)
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        reason = str(reason).replace(api_key, "[REDACTED]")
    return normalized_code, str(reason), transient


def _generate_identification(
    client: Any,
    model: str,
    contents: list[Any],
    config: types.GenerateContentConfig,
) -> tuple[dict, dict]:
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=config,
    )
    parsed = getattr(response, "parsed", None)
    result = parse_identification(parsed if parsed is not None else response.text)
    return result, _usage_metadata(response, model)


def identify_card(
    image_path: str | Path,
    model: str | None = None,
    detail: str = "high",
    fallback_model: str | None = None,
    crop_id: int | None = None,
    event_callback: Callable[[dict], None] | None = None,
    status_callback: Callable[[str], None] | None = None,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> tuple[dict, dict]:
    if not api_ready():
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Put it in .env or export it in your shell."
        )

    model = model or os.environ.get("CARD_HUNT_MODEL", "gemini-3.8-flash")
    if fallback_model is None:
        fallback_model = os.environ.get(
            "CARD_HUNT_FALLBACK_MODEL", "gemini-3.5-flash"
        )
    fallback_model = fallback_model.strip() if fallback_model else None
    if fallback_model == model:
        fallback_model = None
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    # Keep the existing argument for caller compatibility; Gemini processes the
    # supplied crop directly and does not use this provider-specific hint.
    _ = detail
    contents = [
        (
            "Identify this single store card candidate. The image may include "
            "the card, sleeve, price sticker, and request marker. Return only "
            "the structured identification."
        ),
        _image_part(image_path),
    ]
    config = types.GenerateContentConfig(
        system_instruction=IDENTIFICATION_INSTRUCTIONS,
        response_mime_type="application/json",
        response_json_schema=IDENTIFICATION_SCHEMA,
    )

    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return _generate_identification(client, model, contents, config)
        except Exception as error:
            error_code, reason, transient = _error_details(error)
            if not transient:
                raise
            last_error = error
            if attempt == max_attempts:
                break

            next_attempt = attempt + 1
            if event_callback:
                event_callback({
                    "event": "ai_retry",
                    "crop_id": crop_id,
                    "provider": "gemini",
                    "model": model,
                    "attempt": next_attempt,
                    "error_code": error_code,
                    "reason": reason,
                })
            if status_callback:
                status_callback(
                    "Gemini temporarily unavailable — "
                    f"retrying ({next_attempt}/{max_attempts})..."
                )
            delay = RETRY_DELAYS_SECONDS[min(attempt - 1, len(RETRY_DELAYS_SECONDS) - 1)]
            time.sleep(delay + random.uniform(0.0, 0.5))

    if fallback_model:
        if event_callback:
            event_callback({
                "event": "ai_fallback",
                "provider": "gemini",
                "from_model": model,
                "to_model": fallback_model,
                "crop_id": crop_id,
            })
        if status_callback:
            status_callback(
                f"Gemini primary model unavailable — trying {fallback_model}..."
            )
        return _generate_identification(client, fallback_model, contents, config)

    if last_error is not None:
        raise last_error
    raise RuntimeError("Gemini identification failed without an error response.")

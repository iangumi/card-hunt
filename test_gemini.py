import json
from types import SimpleNamespace

import pandas as pd
import pytest

import ai_identify
from ai_identify import identify_card, parse_identification


IDENTIFICATION = {
    "card_name": "Pikachu",
    "card_number": None,
    "set_or_promo": None,
    "year": None,
    "language": "Japanese",
    "variant": None,
    "raw_or_slab": "raw",
    "grade": None,
    "store_price_jpy": None,
    "req_count": 0,
    "status_hint": "unknown",
    "id_confidence": 0.4,
    "price_confidence": 0.0,
    "req_confidence": 0.2,
    "needs_review": True,
    "review_reason": "Exact print is not visible",
    "possible_matches": [],
    "visible_evidence": "Artwork is visible but the card number is not",
}


class FakeGeminiError(Exception):
    def __init__(self, code, status, message):
        super().__init__(message)
        self.code = code
        self.status = status
        self.message = message


class FakeModels:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        outcome = next(self.outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        if outcome.model_version is None:
            outcome.model_version = kwargs["model"]
        return outcome


def response(payload=IDENTIFICATION, model=None):
    return SimpleNamespace(
        parsed=payload,
        text=json.dumps(payload),
        usage_metadata=None,
        model_version=model,
        response_id="test-response",
    )


def install_fake_client(monkeypatch, outcomes):
    models = FakeModels(outcomes)
    client = SimpleNamespace(models=models)
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-secret")
    monkeypatch.setattr(ai_identify.genai, "Client", lambda **kwargs: client)
    sleeps = []
    monkeypatch.setattr(ai_identify.time, "sleep", sleeps.append)
    monkeypatch.setattr(ai_identify.random, "uniform", lambda low, high: 0.25)
    return models, sleeps


def test_parse_identification_accepts_structured_json_without_api_call():
    assert parse_identification(json.dumps(IDENTIFICATION)) == IDENTIFICATION
    assert parse_identification(IDENTIFICATION) is IDENTIFICATION


def test_parse_identification_rejects_non_object_json():
    with pytest.raises(ValueError):
        parse_identification("[]")


def test_503_then_success_retries_same_payload(monkeypatch, tmp_path):
    models, sleeps = install_fake_client(monkeypatch, [
        FakeGeminiError(
            503,
            "UNAVAILABLE",
            "High demand for unit-test-secret",
        ),
        response(),
    ])
    image = tmp_path / "crop.jpg"
    image.write_bytes(b"fake image bytes")
    events = []
    statuses = []

    result, usage = identify_card(
        image,
        crop_id=7,
        event_callback=events.append,
        status_callback=statuses.append,
    )

    assert result == IDENTIFICATION
    assert usage["model"] == "gemini-3.8-flash"
    assert [call["model"] for call in models.calls] == [
        "gemini-3.8-flash",
        "gemini-3.8-flash",
    ]
    assert models.calls[0]["contents"] is models.calls[1]["contents"]
    assert models.calls[0]["config"] is models.calls[1]["config"]
    assert sleeps == [2.25]
    assert events[0] == {
        "event": "ai_retry",
        "crop_id": 7,
        "provider": "gemini",
        "model": "gemini-3.8-flash",
        "attempt": 2,
        "error_code": 503,
        "reason": "High demand for [REDACTED]",
    }
    assert statuses == ["Gemini temporarily unavailable — retrying (2/4)..."]


def test_repeated_503_uses_fallback_after_primary_retries(monkeypatch, tmp_path):
    unavailable = [
        FakeGeminiError(503, "UNAVAILABLE", "High demand")
        for _ in range(4)
    ]
    models, sleeps = install_fake_client(
        monkeypatch,
        [*unavailable, response(model="gemini-3.5-flash")],
    )
    image = tmp_path / "crop.jpg"
    image.write_bytes(b"fake image bytes")
    events = []

    result, usage = identify_card(image, crop_id=2, event_callback=events.append)

    assert result == IDENTIFICATION
    assert usage["model"] == "gemini-3.5-flash"
    assert [call["model"] for call in models.calls] == [
        "gemini-3.8-flash",
        "gemini-3.8-flash",
        "gemini-3.8-flash",
        "gemini-3.8-flash",
        "gemini-3.5-flash",
    ]
    assert len({id(call["contents"]) for call in models.calls}) == 1
    assert len({id(call["config"]) for call in models.calls}) == 1
    assert sleeps == [2.25, 5.25, 10.25]
    assert [event["attempt"] for event in events if event["event"] == "ai_retry"] == [
        2,
        3,
        4,
    ]
    assert events[-1] == {
        "event": "ai_fallback",
        "provider": "gemini",
        "from_model": "gemini-3.8-flash",
        "to_model": "gemini-3.5-flash",
        "crop_id": 2,
    }


def test_401_does_not_retry_or_fallback(monkeypatch, tmp_path):
    auth_error = FakeGeminiError(401, "UNAUTHENTICATED", "Bad API key")
    models, sleeps = install_fake_client(monkeypatch, [auth_error])
    image = tmp_path / "crop.jpg"
    image.write_bytes(b"fake image bytes")
    events = []

    with pytest.raises(FakeGeminiError):
        identify_card(image, crop_id=1, event_callback=events.append)

    assert len(models.calls) == 1
    assert sleeps == []
    assert events == []


@pytest.mark.parametrize(
    ("error", "expected_type"),
    [
        (FakeGeminiError(400, "INVALID_ARGUMENT", "Invalid request"), FakeGeminiError),
        (FakeGeminiError(403, "PERMISSION_DENIED", "Forbidden"), FakeGeminiError),
        (ValueError("Schema/programming error"), ValueError),
    ],
)
def test_non_transient_errors_do_not_retry(
    monkeypatch, tmp_path, error, expected_type
):
    models, sleeps = install_fake_client(monkeypatch, [error])
    image = tmp_path / "crop.jpg"
    image.write_bytes(b"fake image bytes")
    events = []

    with pytest.raises(expected_type):
        identify_card(image, crop_id=1, event_callback=events.append)

    assert len(models.calls) == 1
    assert sleeps == []
    assert events == []


def test_failed_call_does_not_mutate_existing_session_state(monkeypatch, tmp_path):
    failures = [
        FakeGeminiError(503, "UNAVAILABLE", "High demand")
        for _ in range(4)
    ]
    install_fake_client(monkeypatch, failures)
    image = tmp_path / "crop.jpg"
    image.write_bytes(b"fake image bytes")
    candidates = pd.DataFrame([{"crop_id": 1, "card_name": "Existing result"}])
    state = {
        "session_id": "existing-session",
        "candidates": candidates.copy(deep=True),
        "crop_paths": [str(image)],
    }
    expected_candidates = state["candidates"].copy(deep=True)

    with pytest.raises(FakeGeminiError):
        identify_card(image, crop_id=1, fallback_model="")

    assert state["session_id"] == "existing-session"
    assert state["crop_paths"] == [str(image)]
    pd.testing.assert_frame_equal(state["candidates"], expected_candidates)

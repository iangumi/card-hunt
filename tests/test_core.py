
import pandas as pd
import pytest

from card_hunt_core import (
    active_filter,
    apply_ai_result,
    candidate_bool,
    candidate_value_or,
    default_candidates,
    hunt_score_row,
    make_upload_fingerprint,
    normalize_candidate_dtypes,
)


def test_upload_fingerprint_is_stable_for_reruns_and_changes_with_file():
    screenshot = b"same uploaded screenshot bytes"

    first_run = make_upload_fingerprint(screenshot)
    rerun = make_upload_fingerprint(screenshot)
    different_upload = make_upload_fingerprint(b"different screenshot bytes")

    assert first_run == rerun
    assert first_run != different_upload
    assert len(first_run) == 40


def test_candidate_missing_values_are_safe_for_ui_truthiness():
    assert candidate_value_or(pd.NA, "?") == "?"
    assert candidate_value_or(None, "fallback") == "fallback"
    assert candidate_value_or("", "fallback") == "fallback"
    assert candidate_value_or("001/021", "?") == "001/021"
    assert candidate_bool(pd.NA) is False
    assert candidate_bool(None) is False
    assert candidate_bool(True) is True


def test_ai_result_and_confidence_gate():
    df = default_candidates(["one.jpg"])
    result = {
        "card_name": "Victini",
        "card_number": "001/021",
        "set_or_promo": "Battle Theme Deck Victini",
        "year": 1997,
        "language": "Japanese",
        "variant": "Holo",
        "raw_or_slab": "raw",
        "grade": None,
        "store_price_jpy": 6000,
        "req_count": 0,
        "status_hint": "available",
        "id_confidence": 0.97,
        "price_confidence": 0.99,
        "req_confidence": 0.90,
        "needs_review": False,
        "review_reason": None,
        "possible_matches": [],
        "visible_evidence": "001/021 visible",
    }
    out = apply_ai_result(df, 1, result)
    assert out.loc[0, "verified"]
    assert out.loc[0, "year"] == 1997
    assert out.loc[0, "price_jpy"] == 6000
    assert out.loc[0, "req_count"] == 0
    assert out.loc[0, "card_number"] == "001/021"
    assert isinstance(out.loc[0, "card_number"], str)
    assert str(out["year"].dtype) == "Int64"
    assert str(out["price_jpy"].dtype) == "Int64"
    assert str(out["req_count"].dtype) == "Int64"

    active = active_filter(out, 10000, 0.80)
    assert len(active) == 1


def test_ai_result_accepts_missing_year():
    df = default_candidates(["one.jpg"])
    out = apply_ai_result(df, 1, {
        "year": None,
        "card_number": "001/021",
        "needs_review": True,
    })

    assert pd.isna(out.loc[0, "year"])
    assert str(out["year"].dtype) == "Int64"
    assert out.loc[0, "card_number"] == "001/021"


def test_candidate_dtype_pipeline_survives_ai_and_data_handling():
    candidates = default_candidates(["one.jpg"])
    identified = apply_ai_result(candidates, 1, {
        "year": 1997,
        "store_price_jpy": 6000,
        "req_count": 0,
        "card_number": "001/021",
        "id_confidence": 0.91,
    })
    handled = normalize_candidate_dtypes(identified.copy())

    assert handled.loc[0, "year"] == 1997
    assert handled.loc[0, "price_jpy"] == 6000
    assert handled.loc[0, "req_count"] == 0
    assert handled.loc[0, "card_number"] == "001/021"
    assert str(handled["id_confidence"].dtype) == "Float64"
    assert str(handled["hunt_score"].dtype) == "Float64"


def test_malformed_ai_numeric_field_does_not_mutate_existing_result():
    candidates = default_candidates(["one.jpg"])
    candidates = apply_ai_result(candidates, 1, {
        "year": 1997,
        "card_number": "001/021",
        "card_name": "Existing identification",
    })
    before = candidates.copy(deep=True)

    with pytest.raises((TypeError, ValueError)):
        apply_ai_result(candidates, 1, {
            "year": "not-a-year",
            "card_name": "Partial replacement",
        })

    pd.testing.assert_frame_equal(candidates, before)


def test_ambiguous_variant_blocked():
    df = default_candidates(["one.jpg"])
    result = {
        "card_name": "Pikachu",
        "card_number": None,
        "set_or_promo": None,
        "year": None,
        "language": "Japanese",
        "variant": None,
        "raw_or_slab": "raw",
        "grade": None,
        "store_price_jpy": 6220,
        "req_count": 0,
        "status_hint": "available",
        "id_confidence": 0.70,
        "price_confidence": 0.99,
        "req_confidence": 0.90,
        "needs_review": True,
        "review_reason": "Multiple old-back Pikachu prints possible",
        "possible_matches": ["Base Set #025", "Vending Pikachu"],
        "visible_evidence": "Pikachu artwork visible; exact rarity/number unclear",
    }
    out = apply_ai_result(df, 1, result)
    active = active_filter(out, 10000, 0.80)
    assert len(active) == 0


def test_hunt_score_range():
    row = {
        "value": 10,
        "demand": 10,
        "liquidity_score": 10,
        "scarcity": 10,
        "history": 10,
        "artwork": 10,
        "condition_score": 10,
    }
    assert hunt_score_row(row) == 100.0

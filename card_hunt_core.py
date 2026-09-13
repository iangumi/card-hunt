
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import hashlib
import json
import io

import cv2
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw


DEFAULT_WEIGHTS = {
    "value": 25,
    "demand": 20,
    "liquidity": 20,
    "scarcity": 15,
    "history": 10,
    "artwork": 5,
    "condition": 5,
}

LEDGER_COLUMNS = [
    "inventory_id",
    "card_name",
    "card_number",
    "set_or_promo",
    "year",
    "language",
    "variant",
    "raw_or_slab",
    "grade",
    "condition",
    "purchase_price_jpy",
    "purchase_date",
    "source",
    "market_low_jpy",
    "market_high_jpy",
    "hunt_score",
    "deal_edge",
    "liquidity",
    "id_confidence",
    "portfolio_role",
    "status",
    "notes",
]

CANDIDATE_COLUMNS = [
    "selected",
    "crop_id",
    "verified",
    "needs_review",
    "card_name",
    "card_number",
    "set_or_promo",
    "year",
    "language",
    "variant",
    "raw_or_slab",
    "grade",
    "price_jpy",
    "req_count",
    "status",
    "id_confidence",
    "price_confidence",
    "req_confidence",
    "possible_matches",
    "visible_evidence",
    "review_reason",
    "value",
    "demand",
    "liquidity_score",
    "scarcity",
    "history",
    "artwork",
    "condition_score",
    "hunt_score",
    "deal_edge",
    "liquidity_grade",
    "notes",
]

CANDIDATE_FLOAT_COLUMNS = [
    "id_confidence",
    "price_confidence",
    "req_confidence",
    "value",
    "demand",
    "liquidity_score",
    "scarcity",
    "history",
    "artwork",
    "condition_score",
    "hunt_score",
]


def ensure_dirs(data_dir: Path):
    (data_dir / "hunts").mkdir(parents=True, exist_ok=True)
    (data_dir / "crops").mkdir(parents=True, exist_ok=True)


def load_ledger(path: Path) -> pd.DataFrame:
    if path.exists():
        df = pd.read_csv(path)
        for c in LEDGER_COLUMNS:
            if c not in df.columns:
                df[c] = None
        return df[LEDGER_COLUMNS]
    return pd.DataFrame(columns=LEDGER_COLUMNS)


def save_ledger(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def next_inventory_id(df: pd.DataFrame, prefix="PKM") -> str:
    nums = []
    if "inventory_id" in df.columns:
        for value in df["inventory_id"].dropna().astype(str):
            try:
                nums.append(int(value.split("-")[-1]))
            except Exception:
                pass
    return f"{prefix}-{max(nums, default=0)+1:06d}"


def hunt_score_row(row) -> float:
    fields = {
        "value": row.get("value", 0),
        "demand": row.get("demand", 0),
        "liquidity": row.get("liquidity_score", 0),
        "scarcity": row.get("scarcity", 0),
        "history": row.get("history", 0),
        "artwork": row.get("artwork", 0),
        "condition": row.get("condition_score", 0),
    }
    total_weight = sum(DEFAULT_WEIGHTS.values())
    weighted = 0.0
    for key, weight in DEFAULT_WEIGHTS.items():
        try:
            val = float(fields.get(key, 0))
        except Exception:
            val = 0
        val = max(0, min(10, val))
        weighted += val * weight
    return round(weighted / (10 * total_weight) * 100, 1)


def make_session_id(file_bytes: bytes) -> str:
    h = hashlib.sha1(file_bytes).hexdigest()[:8]
    return f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{h}"


def make_upload_fingerprint(file_bytes: bytes) -> str:
    """Return a stable identity for uploaded content across Streamlit reruns."""
    return hashlib.sha1(file_bytes).hexdigest()


def pil_to_cv(img: Image.Image):
    arr = np.array(img.convert("RGB"))
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def detect_cards(img: Image.Image):
    """Experimental local rectangle detector for portrait card regions."""
    bgr = pil_to_cv(img)
    h, w = bgr.shape[:2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(gray, 40, 120)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    img_area = w * h
    boxes = []

    for c in contours:
        x, y, bw, bh = cv2.boundingRect(c)
        area = bw * bh
        if area < img_area * 0.012 or area > img_area * 0.35:
            continue
        if bw < 80 or bh < 110:
            continue
        aspect = bw / bh
        if not (0.42 <= aspect <= 1.02):
            continue
        boxes.append((x, y, x + bw, y + bh))

    boxes = sorted(boxes, key=lambda b: (b[1], b[0]))
    filtered = []
    for box in boxes:
        x1, y1, x2, y2 = box
        keep = True
        for idx, f in enumerate(filtered):
            fx1, fy1, fx2, fy2 = f
            ix1, iy1 = max(x1, fx1), max(y1, fy1)
            ix2, iy2 = min(x2, fx2), min(y2, fy2)
            if ix2 > ix1 and iy2 > iy1:
                inter = (ix2 - ix1) * (iy2 - iy1)
                a1 = (x2 - x1) * (y2 - y1)
                a2 = (fx2 - fx1) * (fy2 - fy1)
                iou = inter / (a1 + a2 - inter)
                if iou > 0.55:
                    # Prefer larger region so price label/sleeve context is more likely retained.
                    if a1 <= a2:
                        keep = False
                    else:
                        filtered[idx] = box
                        keep = False
                    break
        if keep:
            filtered.append(box)

    return sorted(filtered, key=lambda b: (b[1] // 80, b[0]))[:50]


def padded_box(box, img_size, pad_x=0.18, pad_top=0.08, pad_bottom=0.30):
    """Add context, particularly below a card where shop price / req labels often sit."""
    x1, y1, x2, y2 = box
    w, h = img_size
    bw, bh = x2 - x1, y2 - y1
    return (
        max(0, int(x1 - bw * pad_x)),
        max(0, int(y1 - bh * pad_top)),
        min(w, int(x2 + bw * pad_x)),
        min(h, int(y2 + bh * pad_bottom)),
    )


def draw_boxes(img: Image.Image, boxes):
    out = img.convert("RGB").copy()
    d = ImageDraw.Draw(out)
    for i, (x1, y1, x2, y2) in enumerate(boxes, start=1):
        d.rectangle((x1, y1, x2, y2), outline="red", width=5)
        d.rectangle((x1, y1, x1 + 48, y1 + 30), fill="red")
        d.text((x1 + 5, y1 + 5), str(i), fill="white")
    return out


def save_crops(img: Image.Image, boxes, session_id: str, crops_dir: Path):
    folder = crops_dir / session_id
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    context_paths = []

    for i, box in enumerate(boxes, start=1):
        crop = img.crop(box)
        context = img.crop(padded_box(box, img.size))

        p = folder / f"crop_{i:02d}.jpg"
        cp = folder / f"context_{i:02d}.jpg"
        crop.convert("RGB").save(p, quality=95)
        context.convert("RGB").save(cp, quality=95)
        paths.append(p)
        context_paths.append(cp)
    return paths, context_paths


def normalize_candidate_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Return a candidate copy with stable nullable numeric dtypes."""
    out = df.copy()
    out["year"] = pd.to_numeric(out["year"], errors="coerce").astype("Int64")
    out["price_jpy"] = pd.to_numeric(
        out["price_jpy"], errors="coerce"
    ).astype("Int64")
    out["req_count"] = (
        pd.to_numeric(out["req_count"], errors="coerce")
        .fillna(0)
        .astype("Int64")
    )
    for col in CANDIDATE_FLOAT_COLUMNS:
        out[col] = pd.to_numeric(out[col], errors="coerce").astype("Float64")
    return out


def candidate_value_or(value, fallback):
    """Return a display/default value without evaluating pd.NA as a boolean."""
    if value is None:
        return fallback
    missing = pd.isna(value)
    if isinstance(missing, (bool, np.bool_)) and bool(missing):
        return fallback
    if isinstance(value, str) and value == "":
        return fallback
    return value


def candidate_bool(value) -> bool:
    """Convert a candidate scalar to bool, treating missing values as false."""
    if value is None:
        return False
    missing = pd.isna(value)
    if isinstance(missing, (bool, np.bool_)) and bool(missing):
        return False
    return bool(value)


def default_candidates(crop_paths):
    rows = []
    for i, _ in enumerate(crop_paths, start=1):
        rows.append({
            "selected": True,
            "crop_id": i,
            "verified": False,
            "needs_review": False,
            "card_name": "",
            "card_number": "",
            "set_or_promo": "",
            "year": pd.NA,
            "language": "",
            "variant": "",
            "raw_or_slab": "raw",
            "grade": "",
            "price_jpy": None,
            "req_count": 0,
            "status": "available",
            "id_confidence": "",
            "price_confidence": "",
            "req_confidence": "",
            "possible_matches": "",
            "visible_evidence": "",
            "review_reason": "",
            "value": 5,
            "demand": 5,
            "liquidity_score": 5,
            "scarcity": 5,
            "history": 5,
            "artwork": 5,
            "condition_score": 5,
            "hunt_score": 50.0,
            "deal_edge": "",
            "liquidity_grade": "",
            "notes": "",
        })
    candidates = pd.DataFrame(rows, columns=CANDIDATE_COLUMNS, dtype=object)
    return normalize_candidate_dtypes(candidates)


def confidence_grade(conf, needs_review=False) -> str:
    try:
        c = float(conf)
    except Exception:
        return "D"
    if needs_review:
        if c >= 0.80:
            return "B"
        if c >= 0.60:
            return "C"
        return "D"
    if c >= 0.92:
        return "A"
    if c >= 0.80:
        return "B"
    if c >= 0.60:
        return "C"
    return "D"


def apply_ai_result(df: pd.DataFrame, crop_id: int, result: dict):
    # Work on a normalized copy so a failed assignment/conversion cannot mutate
    # the caller's existing candidate/session dataframe.
    out = normalize_candidate_dtypes(df)
    mask = pd.to_numeric(out["crop_id"], errors="coerce") == int(crop_id)
    if not mask.any():
        return out

    mapping = {
        "card_name": "card_name",
        "card_number": "card_number",
        "set_or_promo": "set_or_promo",
        "year": "year",
        "language": "language",
        "variant": "variant",
        "raw_or_slab": "raw_or_slab",
        "grade": "grade",
        "store_price_jpy": "price_jpy",
        "req_count": "req_count",
        "status_hint": "status",
        "id_confidence": "id_confidence",
        "price_confidence": "price_confidence",
        "req_confidence": "req_confidence",
        "visible_evidence": "visible_evidence",
        "review_reason": "review_reason",
    }
    for src, dst in mapping.items():
        if src in result and result[src] is not None:
            out.loc[mask, dst] = result[src]

    pm = result.get("possible_matches") or []
    if isinstance(pm, list):
        pm = " | ".join(str(x) for x in pm)
    out.loc[mask, "possible_matches"] = pm
    needs_review = bool(result.get("needs_review", False))
    out.loc[mask, "needs_review"] = needs_review

    # Auto-verify only when exact ID is exceptionally confident and model sees no ambiguity.
    idc = result.get("id_confidence", 0)
    exact_num = str(result.get("card_number") or "").strip()
    try:
        auto_verified = float(idc) >= 0.96 and not needs_review and bool(exact_num)
    except Exception:
        auto_verified = False
    out.loc[mask, "verified"] = auto_verified

    return normalize_candidate_dtypes(out)


def active_filter(df: pd.DataFrame, max_price: float, confidence_threshold=0.80):
    out = df.copy()
    price = pd.to_numeric(out["price_jpy"], errors="coerce")
    req = pd.to_numeric(out["req_count"], errors="coerce").fillna(0)
    idc = pd.to_numeric(out["id_confidence"], errors="coerce").fillna(0)
    verified = out["verified"].fillna(False).astype(bool)
    needs_review = out["needs_review"].fillna(False).astype(bool)
    status = out["status"].fillna("").str.lower()

    eligible_identity = verified | ((idc >= confidence_threshold) & (~needs_review))
    active = (
        (price <= max_price)
        & (req == 0)
        & eligible_identity
        & (~status.isin(["sold", "sold out", "owned", "bought", "passed", "skip"]))
    )
    return out[active].sort_values(["hunt_score", "price_jpy"], ascending=[False, True])


def review_filter(df: pd.DataFrame, confidence_threshold=0.80):
    idc = pd.to_numeric(df["id_confidence"], errors="coerce").fillna(0)
    return df[(df["needs_review"].fillna(False).astype(bool)) | (idc < confidence_threshold)]


def append_audit(path: Path, event: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"ts": datetime.now().isoformat(timespec="seconds"), **event}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")

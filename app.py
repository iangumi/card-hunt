
from __future__ import annotations

from pathlib import Path
from datetime import datetime
import hashlib
import io
import json

import cv2
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
HUNTS_DIR = DATA_DIR / "hunts"
CROPS_DIR = DATA_DIR / "crops"
LEDGER_PATH = DATA_DIR / "ledger.csv"

DATA_DIR.mkdir(exist_ok=True)
HUNTS_DIR.mkdir(parents=True, exist_ok=True)
CROPS_DIR.mkdir(parents=True, exist_ok=True)

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
    "card_name",
    "card_number",
    "set_or_promo",
    "year",
    "variant",
    "price_jpy",
    "req_count",
    "status",
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
    "id_confidence",
    "notes",
]


def load_ledger():
    if LEDGER_PATH.exists():
        df = pd.read_csv(LEDGER_PATH)
        for c in LEDGER_COLUMNS:
            if c not in df.columns:
                df[c] = None
        return df[LEDGER_COLUMNS]
    return pd.DataFrame(columns=LEDGER_COLUMNS)


def save_ledger(df):
    df.to_csv(LEDGER_PATH, index=False)


def next_inventory_id(df: pd.DataFrame, prefix="PKM"):
    nums = []
    if "inventory_id" in df.columns:
        for value in df["inventory_id"].dropna().astype(str):
            try:
                nums.append(int(value.split("-")[-1]))
            except Exception:
                pass
    return f"{prefix}-{max(nums, default=0)+1:06d}"


def hunt_score_row(row):
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
        val = fields.get(key, 0)
        try:
            val = float(val)
        except Exception:
            val = 0
        val = max(0, min(10, val))
        weighted += val * weight
    return round(weighted / (10 * total_weight) * 100, 1)


def make_session_id(file_bytes: bytes):
    h = hashlib.sha1(file_bytes).hexdigest()[:8]
    return f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{h}"


def pil_to_cv(img: Image.Image):
    arr = np.array(img.convert("RGB"))
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def detect_cards(img: Image.Image):
    """
    Experimental rectangle detector.
    It tries to find card-like rectangular regions in screenshots.
    Returns boxes (x1,y1,x2,y2).
    """
    bgr = pil_to_cv(img)
    h, w = bgr.shape[:2]

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(gray, 40, 120)
    edges = cv2.dilate(edges, np.ones((3,3), np.uint8), iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    img_area = w * h
    for c in contours:
        x, y, bw, bh = cv2.boundingRect(c)
        area = bw * bh
        if area < img_area * 0.015 or area > img_area * 0.35:
            continue
        if bw < 90 or bh < 130:
            continue

        aspect = bw / bh
        # Pokemon cards are portrait, but screenshots may include sleeves/labels.
        if not (0.45 <= aspect <= 0.95):
            continue

        boxes.append((x, y, x+bw, y+bh))

    # remove near-duplicates / nested boxes
    boxes = sorted(boxes, key=lambda b: (b[1], b[0]))
    filtered = []
    for box in boxes:
        x1,y1,x2,y2 = box
        keep = True
        for fx1,fy1,fx2,fy2 in filtered:
            inter_x1, inter_y1 = max(x1,fx1), max(y1,fy1)
            inter_x2, inter_y2 = min(x2,fx2), min(y2,fy2)
            if inter_x2 > inter_x1 and inter_y2 > inter_y1:
                inter = (inter_x2-inter_x1)*(inter_y2-inter_y1)
                area1 = (x2-x1)*(y2-y1)
                area2 = (fx2-fx1)*(fy2-fy1)
                iou = inter / (area1 + area2 - inter)
                if iou > 0.55:
                    if area1 <= area2:
                        keep = False
                        break
        if keep:
            filtered.append(box)

    # Sort roughly row-major
    filtered = sorted(filtered, key=lambda b: (b[1]//80, b[0]))
    return filtered[:40]


def draw_boxes(img: Image.Image, boxes):
    out = img.convert("RGB").copy()
    d = ImageDraw.Draw(out)
    for i, (x1,y1,x2,y2) in enumerate(boxes, start=1):
        d.rectangle((x1,y1,x2,y2), outline="red", width=5)
        d.rectangle((x1, y1, x1+46, y1+28), fill="red")
        d.text((x1+5, y1+4), str(i), fill="white")
    return out


def save_crops(img: Image.Image, boxes, session_id):
    folder = CROPS_DIR / session_id
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, box in enumerate(boxes, start=1):
        crop = img.crop(box)
        p = folder / f"crop_{i:02d}.jpg"
        crop.convert("RGB").save(p, quality=94)
        paths.append(p)
    return paths


def default_candidates(crop_paths):
    rows = []
    for i, p in enumerate(crop_paths, start=1):
        rows.append({
            "selected": True,
            "crop_id": i,
            "card_name": "",
            "card_number": "",
            "set_or_promo": "",
            "year": "",
            "variant": "",
            "price_jpy": None,
            "req_count": 0,
            "status": "available",
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
            "id_confidence": "",
            "notes": "",
        })
    return pd.DataFrame(rows, columns=CANDIDATE_COLUMNS)


def market_filter(df, max_price):
    out = df.copy()
    price = pd.to_numeric(out["price_jpy"], errors="coerce")
    req = pd.to_numeric(out["req_count"], errors="coerce").fillna(0)
    status = out["status"].fillna("").str.lower()

    active = (
        (price <= max_price)
        & (req == 0)
        & (~status.isin(["sold", "sold out", "owned", "bought", "passed", "skip"]))
    )
    return out[active].sort_values(["hunt_score", "price_jpy"], ascending=[False, True])


st.set_page_config(page_title="Card Hunt Local", page_icon="🃏", layout="wide")
st.title("Card Hunt Local")
st.caption("Drop a store screenshot → create crops → build a hunt worksheet → rank → move purchases to your ledger.")

with st.sidebar:
    st.header("Hunt rules")
    max_price = st.number_input("Max price per card (¥)", min_value=0, value=10000, step=500)
    st.caption("req > 0 is excluded from Active ranking automatically.")
    st.divider()
    st.header("Score weights")
    st.write(DEFAULT_WEIGHTS)
    st.caption("Each factor is scored 0–10; the weighted result is 0–100.")
    st.divider()
    st.warning("This app does not fetch live sold comps. Add market data manually or use your preferred research source.")

tabs = st.tabs(["1. Screenshot Intake", "2. Hunt Worksheet", "3. Purchase Ledger", "4. Export"])

with tabs[0]:
    uploaded = st.file_uploader("Drop a store screenshot", type=["png","jpg","jpeg","webp"])
    if uploaded:
        file_bytes = uploaded.getvalue()
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        session_id = make_session_id(file_bytes)

        st.session_state["session_id"] = session_id
        st.session_state["image"] = img

        st.image(img, caption=f"Session {session_id}", use_container_width=True)

        col1, col2 = st.columns([1,1])
        with col1:
            if st.button("Auto-detect card crops", type="primary"):
                boxes = detect_cards(img)
                st.session_state["boxes"] = boxes
                st.session_state["crop_paths"] = save_crops(img, boxes, session_id)
                st.session_state["candidates"] = default_candidates(st.session_state["crop_paths"])

        with col2:
            st.write("If auto-detection is messy, use manual/grid crops below.")

        boxes = st.session_state.get("boxes", [])
        if boxes:
            st.subheader("Detected regions")
            st.image(draw_boxes(img, boxes), use_container_width=True)
            st.caption(f"Detected {len(boxes)} candidate card regions.")

            crop_paths = st.session_state.get("crop_paths", [])
            if crop_paths:
                cols = st.columns(5)
                for i, p in enumerate(crop_paths):
                    with cols[i % 5]:
                        st.image(str(p), caption=f"Crop {i+1}", use_container_width=True)

        st.divider()
        st.subheader("Manual crop")
        w, h = img.size
        c1,c2,c3,c4 = st.columns(4)
        x1 = c1.number_input("x1", 0, w, 0)
        y1 = c2.number_input("y1", 0, h, 0)
        x2 = c3.number_input("x2", 0, w, w)
        y2 = c4.number_input("y2", 0, h, h)

        if x2 > x1 and y2 > y1:
            manual_crop = img.crop((x1,y1,x2,y2))
            st.image(manual_crop, width=350)
            if st.button("Add manual crop"):
                folder = CROPS_DIR / session_id
                folder.mkdir(parents=True, exist_ok=True)
                existing = list(folder.glob("crop_*.jpg"))
                p = folder / f"crop_{len(existing)+1:02d}.jpg"
                manual_crop.save(p, quality=94)
                crop_paths = st.session_state.get("crop_paths", [])
                crop_paths.append(p)
                st.session_state["crop_paths"] = crop_paths
                st.session_state["candidates"] = default_candidates(crop_paths)
                st.success(f"Added {p.name}")

with tabs[1]:
    crop_paths = st.session_state.get("crop_paths", [])
    if not crop_paths:
        st.info("Upload a screenshot and create crops first.")
    else:
        st.subheader("Candidate reference")
        cols = st.columns(6)
        for i, p in enumerate(crop_paths):
            with cols[i % 6]:
                st.image(str(p), caption=f"#{i+1}", use_container_width=True)

        if "candidates" not in st.session_state:
            st.session_state["candidates"] = default_candidates(crop_paths)

        candidates = st.session_state["candidates"].copy()

        st.subheader("Hunt worksheet")
        st.caption("Fill exact ID + price first. Add 0–10 scores after you research sold comps.")

        edited = st.data_editor(
            candidates,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "selected": st.column_config.CheckboxColumn(),
                "price_jpy": st.column_config.NumberColumn(format="¥%d"),
                "req_count": st.column_config.NumberColumn(min_value=0, step=1),
                "value": st.column_config.NumberColumn(min_value=0, max_value=10, step=0.5),
                "demand": st.column_config.NumberColumn(min_value=0, max_value=10, step=0.5),
                "liquidity_score": st.column_config.NumberColumn(min_value=0, max_value=10, step=0.5),
                "scarcity": st.column_config.NumberColumn(min_value=0, max_value=10, step=0.5),
                "history": st.column_config.NumberColumn(min_value=0, max_value=10, step=0.5),
                "artwork": st.column_config.NumberColumn(min_value=0, max_value=10, step=0.5),
                "condition_score": st.column_config.NumberColumn(min_value=0, max_value=10, step=0.5),
                "hunt_score": st.column_config.NumberColumn(disabled=True),
            },
            key="candidate_editor",
        )

        edited["hunt_score"] = edited.apply(hunt_score_row, axis=1)
        st.session_state["candidates"] = edited

        st.subheader("Active ranking")
        active = market_filter(edited, max_price)
        show_cols = [
            "crop_id","card_name","card_number","set_or_promo","price_jpy",
            "hunt_score","deal_edge","liquidity_grade","id_confidence","notes"
        ]
        st.dataframe(active[show_cols], use_container_width=True, hide_index=True)

        req_watch = edited[pd.to_numeric(edited["req_count"], errors="coerce").fillna(0) > 0]
        if len(req_watch):
            st.subheader("Watch if released")
            st.dataframe(req_watch[show_cols + ["req_count"]], use_container_width=True, hide_index=True)

        st.divider()
        if st.button("Save hunt session"):
            sid = st.session_state.get("session_id", datetime.now().strftime("%Y%m%d_%H%M%S"))
            path = HUNTS_DIR / f"{sid}.csv"
            edited.to_csv(path, index=False)
            st.success(f"Saved: {path}")

        st.subheader("Mark purchases")
        selected = edited[edited["selected"] == True].copy()
        if len(selected):
            purchase_names = selected.apply(
                lambda r: f"#{r['crop_id']} {r['card_name'] or '(unnamed)'} — ¥{r['price_jpy'] if pd.notna(r['price_jpy']) else '?'}",
                axis=1
            ).tolist()
            picks = st.multiselect("Cards bought", purchase_names)

            if st.button("Add purchases to ledger"):
                ledger = load_ledger()
                for label in picks:
                    idx = purchase_names.index(label)
                    r = selected.iloc[idx]
                    inv_id = next_inventory_id(ledger)
                    row = {
                        "inventory_id": inv_id,
                        "card_name": r.get("card_name"),
                        "card_number": r.get("card_number"),
                        "set_or_promo": r.get("set_or_promo"),
                        "year": r.get("year"),
                        "language": "Japanese",
                        "variant": r.get("variant"),
                        "raw_or_slab": "raw",
                        "grade": "",
                        "condition": "",
                        "purchase_price_jpy": r.get("price_jpy"),
                        "purchase_date": datetime.now().date().isoformat(),
                        "source": "Card Hunt Local",
                        "market_low_jpy": "",
                        "market_high_jpy": "",
                        "hunt_score": r.get("hunt_score"),
                        "deal_edge": r.get("deal_edge"),
                        "liquidity": r.get("liquidity_grade"),
                        "id_confidence": r.get("id_confidence"),
                        "portfolio_role": "",
                        "status": "owned",
                        "notes": r.get("notes"),
                    }
                    ledger = pd.concat([ledger, pd.DataFrame([row])], ignore_index=True)
                save_ledger(ledger)
                st.success(f"Added {len(picks)} purchase(s) to ledger.")

with tabs[2]:
    st.subheader("Purchase ledger")
    ledger = load_ledger()

    if ledger.empty:
        st.info("No purchases recorded yet.")
    else:
        edited_ledger = st.data_editor(
            ledger,
            use_container_width=True,
            num_rows="dynamic",
            key="ledger_editor"
        )
        if st.button("Save ledger changes"):
            save_ledger(edited_ledger)
            st.success("Ledger saved.")

        owned = edited_ledger[edited_ledger["status"].fillna("owned").str.lower().eq("owned")]
        cost = pd.to_numeric(owned["purchase_price_jpy"], errors="coerce").fillna(0).sum()
        c1,c2 = st.columns(2)
        c1.metric("Owned cards", len(owned))
        c2.metric("Cost basis", f"¥{cost:,.0f}")

with tabs[3]:
    st.subheader("Export")
    ledger = load_ledger()
    csv_data = ledger.to_csv(index=False).encode("utf-8")
    xlsx = io.BytesIO()
    with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
        ledger.to_excel(writer, index=False, sheet_name="Inventory")
    xlsx.seek(0)

    st.download_button(
        "Download ledger CSV",
        data=csv_data,
        file_name="pokemon_card_ledger.csv",
        mime="text/csv",
    )
    st.download_button(
        "Download ledger Excel",
        data=xlsx,
        file_name="pokemon_card_ledger.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    if st.session_state.get("candidates") is not None:
        cand = st.session_state["candidates"]
        st.download_button(
            "Download current hunt worksheet",
            data=cand.to_csv(index=False).encode("utf-8"),
            file_name="current_hunt.csv",
            mime="text/csv",
        )

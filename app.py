
from __future__ import annotations

from pathlib import Path
from datetime import datetime
import io
import os
import shutil

import pandas as pd
from PIL import Image
import streamlit as st
from dotenv import load_dotenv

from card_hunt_core import (
    DEFAULT_WEIGHTS,
    LEDGER_COLUMNS,
    active_filter,
    append_audit,
    apply_ai_result,
    candidate_bool,
    candidate_value_or,
    default_candidates,
    detect_cards,
    draw_boxes,
    ensure_dirs,
    hunt_score_row,
    load_ledger,
    make_session_id,
    make_upload_fingerprint,
    next_inventory_id,
    normalize_candidate_dtypes,
    review_filter,
    save_crops,
    save_ledger,
)
from ai_identify import api_ready, identify_card

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
HUNTS_DIR = DATA_DIR / "hunts"
CROPS_DIR = DATA_DIR / "crops"
LEDGER_PATH = DATA_DIR / "ledger.csv"
AUDIT_PATH = DATA_DIR / "audit.jsonl"


def safe_ai_error(error: Exception) -> str:
    message = str(error)
    api_key = os.environ.get("GEMINI_API_KEY")
    return message.replace(api_key, "[REDACTED]") if api_key else message


def identify_crop_with_feedback(
    image_path: Path,
    crop_id: int,
    model: str,
    detail: str,
    status,
) -> tuple[dict, dict]:
    def record_runtime_event(event: dict):
        append_audit(AUDIT_PATH, {
            "session_id": st.session_state.get("session_id"),
            **event,
        })

    fallback_model = os.environ.get(
        "CARD_HUNT_FALLBACK_MODEL", "gemini-3.5-flash"
    )
    return identify_card(
        image_path,
        model=model,
        detail=detail,
        fallback_model=fallback_model,
        crop_id=crop_id,
        event_callback=record_runtime_event,
        status_callback=status.warning,
    )


ensure_dirs(DATA_DIR)
load_dotenv(APP_DIR / ".env")

st.set_page_config(page_title="Card Hunt Local v2", page_icon="🃏", layout="wide")
st.title("Card Hunt Local v2")
st.caption(
    "Screenshot → crops → AI exact-ID / price / req extraction → confidence gate → "
    "hunt worksheet → purchase ledger"
)

with st.sidebar:
    st.header("Hunt rules")
    max_price = st.number_input("Max price/card (¥)", min_value=0, value=10000, step=500)
    confidence_threshold = st.slider(
        "Minimum exact-ID confidence",
        min_value=0.50,
        max_value=1.00,
        value=0.80,
        step=0.01,
    )

    st.divider()
    st.header("AI identification")
    model = st.selectbox(
        "Model",
        ["gemini-3.8-flash"],
        index=0,
        help="Gemini model used for identification and per-crop retries.",
    )
    vision_detail = "high"
    fallback_model = os.environ.get(
        "CARD_HUNT_FALLBACK_MODEL", "gemini-3.5-flash"
    )

    if api_ready():
        st.success("GEMINI_API_KEY detected")
    else:
        st.warning("AI disabled: GEMINI_API_KEY not found")
        st.code("cp .env.example .env\n# then edit .env")

    st.caption(
        "When AI identification is used, the selected crop is sent to the Gemini API. "
        "Manual/local workflow remains available without an API key."
    )
    st.caption(f"Fallback after transient retries: `{fallback_model}`")

    st.divider()
    st.header("Hunt Score")
    st.write(DEFAULT_WEIGHTS)
    st.caption("Market scoring remains manual in v2; AI only handles identification/store metadata.")

tabs = st.tabs([
    "1. Intake",
    "2. AI Review",
    "3. Hunt Worksheet",
    "4. Purchase Ledger",
    "5. Audit / Export",
])

# ---------- Intake ----------
with tabs[0]:
    uploaded = st.file_uploader(
        "Drop a store screenshot",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=False,
        key="hunt_screenshot",
    )

    if uploaded:
        file_bytes = uploaded.getvalue()
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        upload_fingerprint = make_upload_fingerprint(file_bytes)

        # A widget interaction reruns the script with the same uploaded bytes.
        # Start a hunt only when those bytes identify a genuinely different file.
        if (
            st.session_state.get("upload_fingerprint") != upload_fingerprint
            or "session_id" not in st.session_state
        ):
            session_id = make_session_id(file_bytes)
            st.session_state["session_id"] = session_id
            st.session_state["upload_fingerprint"] = upload_fingerprint
            st.session_state["image"] = img
            st.session_state["boxes"] = []
            st.session_state["crop_paths"] = []
            st.session_state["context_paths"] = []
            st.session_state["candidates"] = default_candidates([])
            st.session_state["ai_usages"] = []
            st.session_state["ai_errors"] = {}
        else:
            session_id = st.session_state["session_id"]

        st.image(img, caption=f"Session {session_id}", use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Auto-detect card crops", type="primary"):
                boxes = detect_cards(img)
                crop_paths, context_paths = save_crops(
                    img, boxes, session_id, CROPS_DIR
                )
                st.session_state["boxes"] = boxes
                st.session_state["crop_paths"] = crop_paths
                st.session_state["context_paths"] = context_paths
                st.session_state["candidates"] = default_candidates(crop_paths)
                st.rerun()
        with c2:
            st.info(
                "v2 saves a padded context crop below each card so price and `req` labels "
                "are less likely to be cut off."
            )

        boxes = st.session_state.get("boxes", [])
        if boxes:
            st.subheader("Detected regions")
            st.image(draw_boxes(img, boxes), use_container_width=True)

            crop_paths = st.session_state.get("crop_paths", [])
            context_paths = st.session_state.get("context_paths", [])
            cols = st.columns(5)
            for i, p in enumerate(crop_paths):
                with cols[i % 5]:
                    st.image(str(p), caption=f"Card #{i+1}", use_container_width=True)
                    if i < len(context_paths):
                        with st.expander("Context"):
                            st.image(str(context_paths[i]), use_container_width=True)

        st.divider()
        st.subheader("Manual crop fallback")
        w, h = img.size
        c1, c2, c3, c4 = st.columns(4)
        x1 = c1.number_input("x1", 0, w, 0, key="mx1")
        y1 = c2.number_input("y1", 0, h, 0, key="my1")
        x2 = c3.number_input("x2", 0, w, w, key="mx2")
        y2 = c4.number_input("y2", 0, h, h, key="my2")

        if x2 > x1 and y2 > y1:
            manual = img.crop((x1, y1, x2, y2))
            st.image(manual, width=320)
            if st.button("Add manual crop"):
                folder = CROPS_DIR / session_id
                folder.mkdir(parents=True, exist_ok=True)
                existing = list(folder.glob("crop_*.jpg"))
                idx = len(existing) + 1
                p = folder / f"crop_{idx:02d}.jpg"
                cp = folder / f"context_{idx:02d}.jpg"
                manual.save(p, quality=95)
                # Manual crop is already user-selected context; use it for both.
                manual.save(cp, quality=95)

                crop_paths = st.session_state.get("crop_paths", []) + [p]
                context_paths = st.session_state.get("context_paths", []) + [cp]
                old = st.session_state.get("candidates")
                new = default_candidates(crop_paths)
                if old is not None and not old.empty:
                    old = normalize_candidate_dtypes(old)
                    for col in old.columns:
                        if col in new.columns:
                            new.loc[: len(old)-1, col] = old[col].values
                st.session_state["crop_paths"] = crop_paths
                st.session_state["context_paths"] = context_paths
                st.session_state["candidates"] = new
                st.rerun()

# ---------- AI Review ----------
with tabs[1]:
    crop_paths = st.session_state.get("crop_paths", [])
    context_paths = st.session_state.get("context_paths", [])
    candidates = st.session_state.get("candidates")

    if not crop_paths:
        st.info("Create card crops in Intake first.")
    else:
        if candidates is None or candidates.empty:
            candidates = default_candidates(crop_paths)
            st.session_state["candidates"] = candidates
        st.session_state.setdefault("ai_errors", {})

        st.subheader("AI identification")
        st.caption(
            "AI fills exact identity + shop price + req marker. Ambiguous variants are "
            "routed to Needs Review instead of silently entering the ranking."
        )

        col_a, col_b = st.columns([1, 1])
        with col_a:
            if st.button(
                "AI identify ALL crops",
                type="primary",
                disabled=not api_ready(),
            ):
                progress = st.progress(0)
                status = st.empty()
                df = st.session_state["candidates"].copy()
                usages = st.session_state.get("ai_usages", [])
                ai_errors = dict(st.session_state.get("ai_errors", {}))

                for i, cp in enumerate(context_paths):
                    status.write(f"Identifying card {i+1}/{len(context_paths)}...")
                    try:
                        result, usage = identify_crop_with_feedback(
                            cp, i + 1, model, vision_detail, status
                        )
                        df = apply_ai_result(df, i + 1, result)
                        usages.append({"crop_id": i + 1, **usage})
                        ai_errors.pop(i + 1, None)
                        append_audit(AUDIT_PATH, {
                            "event": "ai_identification",
                            "provider": "gemini",
                            "session_id": st.session_state.get("session_id"),
                            "crop_id": i + 1,
                            "model": usage.get("model", model),
                            "result": result,
                        })
                    except Exception as e:
                        error_message = safe_ai_error(e)
                        ai_errors[i + 1] = error_message
                        append_audit(AUDIT_PATH, {
                            "event": "ai_error",
                            "provider": "gemini",
                            "session_id": st.session_state.get("session_id"),
                            "crop_id": i + 1,
                            "model": model,
                            "error": error_message,
                        })
                        st.error(f"Crop #{i+1}: {error_message}")
                    progress.progress((i + 1) / len(context_paths))

                st.session_state["candidates"] = df
                st.session_state["ai_usages"] = usages
                st.session_state["ai_errors"] = ai_errors
                if ai_errors:
                    status.warning("AI identification complete with crop errors")
                else:
                    status.success("AI identification complete")
                st.rerun()

        with col_b:
            crop_choice = st.selectbox(
                "Re-analyze one difficult crop",
                list(range(1, len(crop_paths) + 1)),
            )
            if st.button(
                "AI identify selected crop",
                disabled=not api_ready(),
            ):
                cp = context_paths[crop_choice - 1]
                retry_status = st.empty()
                try:
                    result, usage = identify_crop_with_feedback(
                        cp, crop_choice, model, vision_detail, retry_status
                    )
                    st.session_state["candidates"] = apply_ai_result(
                        st.session_state["candidates"], crop_choice, result
                    )
                    st.session_state.setdefault("ai_usages", []).append(
                        {"crop_id": crop_choice, **usage}
                    )
                    st.session_state.setdefault("ai_errors", {}).pop(crop_choice, None)
                    append_audit(AUDIT_PATH, {
                        "event": "ai_identification",
                        "provider": "gemini",
                        "session_id": st.session_state.get("session_id"),
                        "crop_id": crop_choice,
                        "model": usage.get("model", model),
                        "result": result,
                    })
                    st.success(f"Crop #{crop_choice} updated")
                    st.rerun()
                except Exception as e:
                    error_message = safe_ai_error(e)
                    st.session_state.setdefault("ai_errors", {})[
                        crop_choice
                    ] = error_message
                    append_audit(AUDIT_PATH, {
                        "event": "ai_error",
                        "provider": "gemini",
                        "session_id": st.session_state.get("session_id"),
                        "crop_id": crop_choice,
                        "model": model,
                        "error": error_message,
                    })
                    st.error(error_message)

        ai_errors = st.session_state.get("ai_errors", {})
        if ai_errors:
            st.subheader("AI errors")
            for failed_crop_id, error_message in sorted(ai_errors.items()):
                st.error(f"Crop #{failed_crop_id}: {error_message}")
                if st.button(
                    f"Retry crop #{failed_crop_id}",
                    key=f"retry_failed_crop_{failed_crop_id}",
                    disabled=not api_ready(),
                ):
                    retry_status = st.empty()
                    cp = context_paths[failed_crop_id - 1]
                    try:
                        result, usage = identify_crop_with_feedback(
                            cp,
                            failed_crop_id,
                            model,
                            vision_detail,
                            retry_status,
                        )
                        st.session_state["candidates"] = apply_ai_result(
                            st.session_state["candidates"],
                            failed_crop_id,
                            result,
                        )
                        st.session_state.setdefault("ai_usages", []).append(
                            {"crop_id": failed_crop_id, **usage}
                        )
                        st.session_state["ai_errors"].pop(failed_crop_id, None)
                        append_audit(AUDIT_PATH, {
                            "event": "ai_identification",
                            "provider": "gemini",
                            "session_id": st.session_state.get("session_id"),
                            "crop_id": failed_crop_id,
                            "model": usage.get("model", model),
                            "result": result,
                        })
                        st.rerun()
                    except Exception as e:
                        error_message = safe_ai_error(e)
                        st.session_state["ai_errors"][
                            failed_crop_id
                        ] = error_message
                        append_audit(AUDIT_PATH, {
                            "event": "ai_error",
                            "provider": "gemini",
                            "session_id": st.session_state.get("session_id"),
                            "crop_id": failed_crop_id,
                            "model": model,
                            "error": error_message,
                        })
                        st.error(error_message)

        st.divider()
        st.subheader("Identification review")

        df = st.session_state["candidates"].copy()
        cols = st.columns(4)
        for i, p in enumerate(context_paths):
            row = df[pd.to_numeric(df["crop_id"], errors="coerce") == (i + 1)]
            r = row.iloc[0] if not row.empty else None
            with cols[i % 4]:
                st.image(str(p), caption=f"#{i+1}", use_container_width=True)
                if r is not None:
                    title = candidate_value_or(r.get("card_name"), "Unidentified")
                    num = candidate_value_or(r.get("card_number"), "?")
                    st.markdown(f"**{title} — {num}**")
                    st.write(
                        f"¥{r.get('price_jpy') if pd.notna(r.get('price_jpy')) else '?'}"
                        f" · req {r.get('req_count')}"
                    )
                    idc = r.get("id_confidence")
                    st.write(
                        "Exact-ID confidence: "
                        f"{candidate_value_or(idc, '?')}"
                    )
                    if candidate_bool(r.get("needs_review")):
                        st.warning(
                            candidate_value_or(
                                r.get("review_reason"), "Needs review"
                            )
                        )
                    elif candidate_bool(r.get("verified")):
                        st.success("Auto-verified")
                    else:
                        st.info("Review / verify before purchase")

        st.subheader("Review queue")
        review = review_filter(df, confidence_threshold)
        if review.empty:
            st.success("No candidates below the confidence gate.")
        else:
            st.dataframe(
                review[
                    [
                        "crop_id", "card_name", "card_number", "set_or_promo",
                        "id_confidence", "possible_matches", "visible_evidence",
                        "review_reason"
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

# ---------- Worksheet ----------
with tabs[2]:
    candidates = st.session_state.get("candidates")
    if candidates is None or candidates.empty:
        st.info("Create crops first.")
    else:
        st.subheader("Hunt worksheet")
        st.caption(
            "Correct AI fields here. Set Verified=True once you personally confirm a difficult "
            "variant. Market/value scoring remains manual in v2."
        )

        try:
            candidates_for_editor = normalize_candidate_dtypes(candidates)
        except Exception as e:
            st.error(f"Candidate numeric fields could not be normalized: {e}")
            candidates_for_editor = candidates.copy()

        edited_input = st.data_editor(
            candidates_for_editor,
            width="stretch",
            num_rows="dynamic",
            column_config={
                "selected": st.column_config.CheckboxColumn(),
                "verified": st.column_config.CheckboxColumn(),
                "needs_review": st.column_config.CheckboxColumn(disabled=True),
                "year": st.column_config.NumberColumn(
                    "Year",
                    min_value=1990,
                    max_value=2100,
                    step=1,
                    format="%d",
                ),
                "price_jpy": st.column_config.NumberColumn(format="¥%d"),
                "req_count": st.column_config.NumberColumn(min_value=0, step=1),
                "id_confidence": st.column_config.NumberColumn(min_value=0, max_value=1, format="%.2f"),
                "price_confidence": st.column_config.NumberColumn(min_value=0, max_value=1, format="%.2f"),
                "req_confidence": st.column_config.NumberColumn(min_value=0, max_value=1, format="%.2f"),
                "value": st.column_config.NumberColumn(min_value=0, max_value=10, step=0.5),
                "demand": st.column_config.NumberColumn(min_value=0, max_value=10, step=0.5),
                "liquidity_score": st.column_config.NumberColumn(min_value=0, max_value=10, step=0.5),
                "scarcity": st.column_config.NumberColumn(min_value=0, max_value=10, step=0.5),
                "history": st.column_config.NumberColumn(min_value=0, max_value=10, step=0.5),
                "artwork": st.column_config.NumberColumn(min_value=0, max_value=10, step=0.5),
                "condition_score": st.column_config.NumberColumn(min_value=0, max_value=10, step=0.5),
                "hunt_score": st.column_config.NumberColumn(disabled=True),
            },
            key="candidate_editor_v2",
        )
        try:
            edited = normalize_candidate_dtypes(edited_input)
            edited["hunt_score"] = edited.apply(hunt_score_row, axis=1)
            edited = normalize_candidate_dtypes(edited)
        except Exception as e:
            st.error(
                "Candidate edits were not saved because numeric conversion failed: "
                f"{e}"
            )
            edited = candidates_for_editor
        else:
            st.session_state["candidates"] = edited

        st.subheader("Active ranking")
        active = active_filter(edited, max_price, confidence_threshold)
        show_cols = [
            "crop_id", "card_name", "card_number", "set_or_promo", "price_jpy",
            "hunt_score", "deal_edge", "liquidity_grade", "id_confidence", "verified"
        ]
        if active.empty:
            st.info("No candidates currently pass budget + request + identity-confidence gates.")
        else:
            st.dataframe(active[show_cols], use_container_width=True, hide_index=True)

        req = edited[pd.to_numeric(edited["req_count"], errors="coerce").fillna(0) > 0]
        if not req.empty:
            st.subheader("Watch if released")
            st.dataframe(
                req[show_cols + ["req_count"]],
                use_container_width=True,
                hide_index=True,
            )

        st.divider()
        if st.button("Save hunt session"):
            sid = st.session_state.get("session_id", datetime.now().strftime("%Y%m%d_%H%M%S"))
            path = HUNTS_DIR / f"{sid}.csv"
            edited.to_csv(path, index=False)
            append_audit(AUDIT_PATH, {
                "event": "hunt_saved",
                "session_id": sid,
                "path": str(path),
                "rows": len(edited),
            })
            st.success(f"Saved {path.name}")

        st.subheader("Mark purchases")
        selected = edited[edited["selected"].fillna(False).astype(bool)].copy()
        labels = selected.apply(
            lambda r: (
                f"#{r['crop_id']} "
                f"{candidate_value_or(r['card_name'], '(unnamed)')} "
                f"{candidate_value_or(r['card_number'], '')} — "
                f"¥{int(r['price_jpy']) if pd.notna(r['price_jpy']) else '?'}"
            ),
            axis=1,
        ).tolist()
        picks = st.multiselect("Cards bought", labels)

        if st.button("Add purchases to ledger"):
            ledger = load_ledger(LEDGER_PATH)
            added = 0
            for label in picks:
                idx = labels.index(label)
                r = selected.iloc[idx]
                if not candidate_bool(r.get("verified")) and (
                    candidate_bool(r.get("needs_review"))
                    or float(pd.to_numeric(pd.Series([r.get("id_confidence")]), errors="coerce").fillna(0).iloc[0])
                    < confidence_threshold
                ):
                    st.error(f"Cannot add {label}: exact identity is not verified.")
                    continue

                inv_id = next_inventory_id(ledger)
                row = {
                    "inventory_id": inv_id,
                    "card_name": r.get("card_name"),
                    "card_number": r.get("card_number"),
                    "set_or_promo": r.get("set_or_promo"),
                    "year": r.get("year"),
                    "language": candidate_value_or(r.get("language"), "Japanese"),
                    "variant": r.get("variant"),
                    "raw_or_slab": candidate_value_or(
                        r.get("raw_or_slab"), "raw"
                    ),
                    "grade": r.get("grade"),
                    "condition": "",
                    "purchase_price_jpy": r.get("price_jpy"),
                    "purchase_date": datetime.now().date().isoformat(),
                    "source": f"Card Hunt {st.session_state.get('session_id', '')}",
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
                append_audit(AUDIT_PATH, {
                    "event": "purchase_added",
                    "session_id": st.session_state.get("session_id"),
                    "inventory_id": inv_id,
                    "card_name": r.get("card_name"),
                    "card_number": r.get("card_number"),
                    "price_jpy": r.get("price_jpy"),
                })
                added += 1
            if added:
                save_ledger(ledger, LEDGER_PATH)
                st.success(f"Added {added} purchase(s).")

# ---------- Ledger ----------
with tabs[3]:
    st.subheader("Purchase ledger")
    ledger = load_ledger(LEDGER_PATH)
    if ledger.empty:
        st.info("No purchases recorded in this v2 data folder yet.")
    else:
        edited_ledger = st.data_editor(ledger, use_container_width=True, num_rows="dynamic")
        if st.button("Save ledger changes"):
            save_ledger(edited_ledger, LEDGER_PATH)
            st.success("Ledger saved.")

        owned = edited_ledger[
            edited_ledger["status"].fillna("owned").str.lower().eq("owned")
        ]
        cost = pd.to_numeric(owned["purchase_price_jpy"], errors="coerce").fillna(0).sum()
        c1, c2 = st.columns(2)
        c1.metric("Owned cards", len(owned))
        c2.metric("Cost basis", f"¥{cost:,.0f}")

# ---------- Audit / Export ----------
with tabs[4]:
    st.subheader("AI usage this session")
    usages = st.session_state.get("ai_usages", [])
    if usages:
        st.dataframe(pd.DataFrame(usages), use_container_width=True, hide_index=True)
    else:
        st.caption("No API calls in this session.")

    st.subheader("Audit trail")
    if AUDIT_PATH.exists():
        lines = AUDIT_PATH.read_text(encoding="utf-8").splitlines()
        st.code("\n".join(lines[-30:]), language="json")
    else:
        st.caption("No audit events yet.")

    st.subheader("Export")
    ledger = load_ledger(LEDGER_PATH)
    st.download_button(
        "Download ledger CSV",
        ledger.to_csv(index=False).encode("utf-8"),
        file_name="pokemon_card_ledger.csv",
        mime="text/csv",
    )
    xlsx = io.BytesIO()
    with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
        ledger.to_excel(writer, index=False, sheet_name="Inventory")
    xlsx.seek(0)
    st.download_button(
        "Download ledger Excel",
        xlsx,
        file_name="pokemon_card_ledger.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    cand = st.session_state.get("candidates")
    if cand is not None and not cand.empty:
        st.download_button(
            "Download current hunt CSV",
            cand.to_csv(index=False).encode("utf-8"),
            file_name="current_hunt.csv",
            mime="text/csv",
        )

from __future__ import annotations

import base64
import json
import re
from typing import Any

from sqlalchemy import select

from app import clock
from app.config import get_settings
from app.db.models import InventoryItem, InventoryLog
from app.db.session import SessionLocal
from app.schemas import (
    InventoryDetectedItem,
    InventoryReconciliationItem,
    InventoryReconciliationResponse,
    InventoryScanResponse,
)
from app.services.monitoring_runtime import monitoring_runtime

MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def validate_image_bytes(file_bytes: bytes, filename: str) -> str:
    """Validate image file size, extension, and magic bytes. Returns detected MIME type."""
    if len(file_bytes) == 0:
        raise ValueError("Uploaded file is empty.")
    if len(file_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise ValueError("Image file size exceeds the 10 MB limit.")

    lower_name = filename.lower()
    if not any(lower_name.endswith(ext) for ext in ALLOWED_IMAGE_EXTENSIONS):
        raise ValueError("Unsupported image file format. Allowed formats: JPG, JPEG, PNG, WEBP.")

    # Magic byte verification
    if file_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if file_bytes.startswith(b"RIFF") and b"WEBP" in file_bytes[:16]:
        return "image/webp"

    raise ValueError("Corrupt or invalid image file content.")


def _match_existing_items(
    detected: list[InventoryDetectedItem],
    household_items: list[InventoryItem],
) -> None:
    """Pre-matches detected items with existing household items by normalized name."""
    existing_map = {
        re.sub(r"[^a-z0-9]", "", item.name.lower()): item
        for item in household_items
    }

    for item in detected:
        normalized_detected = re.sub(r"[^a-z0-9]", "", item.name.lower())
        matched = existing_map.get(normalized_detected)
        if not matched:
            # Substring match check
            for norm_key, existing_item in existing_map.items():
                if norm_key in normalized_detected or normalized_detected in norm_key:
                    matched = existing_item
                    break
        if matched:
            item.matched_item_id = matched.id
            item.existing_quantity = matched.quantity


def scan_inventory_image(
    image_bytes: bytes,
    mime_type: str,
    *,
    household_id: str | None = None,
) -> InventoryScanResponse:
    """Processes an inventory image and returns structured detections."""
    settings = get_settings()

    with SessionLocal() as session:
        query = select(InventoryItem)
        if household_id is not None:
            query = query.where(InventoryItem.household_id == household_id)
        household_items = list(session.scalars(query).all())

    if settings.llm_mode == "mock":
        # Deterministic verification mode
        detected = [
            InventoryDetectedItem(
                name="Whole Milk",
                category="beverage",
                estimated_quantity=3.0,
                unit="carton",
                confidence=0.95,
                brand="FarmFresh",
                notes="3 cartons clearly visible on top shelf",
            ),
            InventoryDetectedItem(
                name="Basmati Rice",
                category="pantry",
                estimated_quantity=2.0,
                unit="packet",
                confidence=0.90,
                brand="Royal",
                notes="2 sealed 1kg packets on pantry rack",
            ),
            InventoryDetectedItem(
                name="Water Bottles",
                category="beverage",
                estimated_quantity=5.0,
                unit="bottle",
                confidence=0.82,
                notes="5 bottles counted; rear bottles partially obscured",
            ),
        ]
        _match_existing_items(detected, household_items)
        return InventoryScanResponse(
            detected_items=detected,
            image_summary="Household pantry and shelf scan identifying food, beverage, and pantry essentials.",
            warnings=["Overlapping items in background were flagged with lower confidence."],
        )

    # Live multimodal vision provider
    if not settings.gemini_api_key:
        raise RuntimeError("Live Gemini vision requires GEMINI_API_KEY.")

    from langchain_core.messages import HumanMessage
    from langchain_google_genai import ChatGoogleGenerativeAI

    model_name = settings.gemini_model or "gemini-2.5-flash"
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=settings.gemini_api_key,
        temperature=0.1,
    )

    base64_img = base64.b64encode(image_bytes).decode("utf-8")
    prompt = (
        "You are a computer vision inventory specialist for HomePilot AI. "
        "Analyze this image of household inventory, shelves, refrigerator, or storage. "
        "Extract every distinct visible household item, estimate the count, unit, category, confidence (0.0 to 1.0), and notes. "
        "Do NOT invent items that are not visible. For occluded items, note the uncertainty and reduce confidence. "
        "Return a JSON object strictly matching this schema:\n"
        "{\n"
        '  "detected_items": [\n'
        '    {"name": "...", "category": "...", "estimated_quantity": 1.0, "unit": "...", "confidence": 0.9, "brand": null, "notes": "..."}\n'
        "  ],\n"
        '  "image_summary": "...",\n'
        '  "warnings": []\n'
        "}\n"
        "Return ONLY the valid JSON object without markdown formatting or code fences."
    )

    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": f"data:{mime_type};base64,{base64_img}"},
        ]
    )

    response = llm.invoke([message])
    content = response.content
    if isinstance(content, list):
        content = "".join(str(part) for part in content)

    # Clean markdown fences if present
    content = re.sub(r"^```(?:json)?\s*", "", content.strip())
    content = re.sub(r"\s*```$", "", content.strip())

    try:
        data = json.loads(content)
        parsed = InventoryScanResponse.model_validate(data)
        _match_existing_items(parsed.detected_items, household_items)
        return parsed
    except Exception as exc:
        raise ValueError(f"Failed to parse structured inventory scan output from model: {exc}") from exc


def reconcile_inventory_items(
    items: list[InventoryReconciliationItem],
    *,
    household_id: str,
) -> InventoryReconciliationResponse:
    """Applies user-confirmed inventory adjustments atomically."""
    updated: list[dict] = []
    created: list[dict] = []
    ignored_count = 0

    with SessionLocal() as session:
        for rec in items:
            if rec.action == "ignore":
                ignored_count += 1
                continue

            if rec.action in {"add", "replace"}:
                if not rec.item_id:
                    raise ValueError(f"Action '{rec.action}' requires a valid item_id.")
                row = session.get(InventoryItem, rec.item_id)
                if row is None or row.household_id != household_id:
                    raise ValueError(f"Inventory item {rec.item_id} not found in this household.")

                if rec.action == "add":
                    row.quantity += rec.quantity
                else:  # replace
                    row.quantity = rec.quantity

                row.unit = rec.unit
                session.add(
                    InventoryLog(
                        item_id=row.id,
                        household_id=household_id,
                        quantity=row.quantity,
                        logged_at=clock.now(),
                        source="vision_scan",
                        is_simulated=row.is_simulated,
                        created_at=clock.now(),
                    )
                )
                updated.append(
                    {
                        "id": row.id,
                        "name": row.name,
                        "quantity": row.quantity,
                        "unit": row.unit,
                        "action": rec.action,
                    }
                )

            elif rec.action == "new":
                new_row = InventoryItem(
                    name=rec.name,
                    quantity=rec.quantity,
                    unit=rec.unit,
                    reorder_threshold=rec.reorder_threshold,
                    household_id=household_id,
                    is_simulated=False,
                    created_at=clock.now(),
                )
                session.add(new_row)
                session.flush()

                session.add(
                    InventoryLog(
                        item_id=new_row.id,
                        household_id=household_id,
                        quantity=new_row.quantity,
                        logged_at=clock.now(),
                        source="vision_scan",
                        is_simulated=False,
                        created_at=clock.now(),
                    )
                )
                created.append(
                    {
                        "id": new_row.id,
                        "name": new_row.name,
                        "quantity": new_row.quantity,
                        "unit": new_row.unit,
                        "action": "new",
                    }
                )

        session.commit()

    monitoring_runtime.trigger_event(["inventory"], household_id)
    return InventoryReconciliationResponse(
        updated_items=updated,
        created_items=created,
        ignored_count=ignored_count,
    )

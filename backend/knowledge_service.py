import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from logging_config import get_logger
from query_rag import add_knowledge_document

logger = get_logger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEARNED_DATA_DIR = os.path.join(BASE_DIR, "data", "LEARNED INCIDENTS")


def _safe_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _build_content(payload: dict[str, Any]) -> str:
    description = (payload.get("description") or "").strip()
    log_line = (payload.get("log_line") or "").strip()
    parsed = payload.get("parsed_output") or {}
    notes = (payload.get("notes") or "").strip()

    lines = [
        "Learned Incident Entry",
        f"Description: {description or 'unknown'}",
        f"Logs: {log_line or 'unknown'}",
        f"Executive Summary: {parsed.get('executive_summary', 'unknown')}",
        f"Root Cause: {parsed.get('root_cause', 'unknown')}",
        f"Severity: {parsed.get('severity', 'unknown')}",
        f"Impacted Services: {', '.join(_safe_list(parsed.get('impacted_services')))}",
        f"Indicators Detected: {', '.join(_safe_list(parsed.get('indicators_detected')))}",
        f"Resolution Steps: {' | '.join(_safe_list(parsed.get('resolution_steps')))}",
        f"Preventive Actions: {' | '.join(_safe_list(parsed.get('preventive_actions')))}",
        f"Confidence Score: {parsed.get('confidence_score', 'unknown')}",
    ]
    if notes:
        lines.append(f"Operator Notes: {notes}")
    return "\n".join(lines)


def save_knowledge_entry(payload: dict[str, Any]) -> dict[str, Any]:
    os.makedirs(LEARNED_DATA_DIR, exist_ok=True)
    doc_id = f"DOC-LEARN-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.now(timezone.utc).isoformat()

    parsed = payload.get("parsed_output") or {}
    content = _build_content(payload)
    metadata = {
        "category": "learned_incident",
        "source": "ui_feedback",
        "created_at": now,
        "severity": parsed.get("severity", "unknown"),
        "service": ", ".join(_safe_list(parsed.get("impacted_services"))) or "unknown",
        "tags": _safe_list(parsed.get("indicators_detected")),
    }
    doc = {
        "id": doc_id,
        "content": content,
        "metadata": metadata,
    }

    file_path = os.path.join(LEARNED_DATA_DIR, f"{doc_id}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)

    add_knowledge_document(content=content, metadata=metadata, source_id=doc_id)
    logger.info("Knowledge entry saved | id=%s path=%s", doc_id, file_path)
    return {"id": doc_id, "file_path": file_path}

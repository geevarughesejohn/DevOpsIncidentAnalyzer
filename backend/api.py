import json
import os
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from knowledge_service import save_knowledge_entry
from logging_config import get_logger
from query_rag import analyze_incident, follow_up_discussion

app = FastAPI(
    title="DevOps Incident Analyzer API",
    version="1.0.0",
)
logger = get_logger(__name__)

_origins_raw = os.getenv(
    "FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
)
_allow_origins = [origin.strip() for origin in _origins_raw.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeIncidentRequest(BaseModel):
    description: str | None = Field(
        default=None, description="Human-readable incident summary/description."
    )
    log_line: str | None = Field(
        default=None, description="Raw log snippet or error line(s)."
    )
    incident_text: str | None = Field(
        default=None, description="Backward-compatible combined incident input."
    )


class AnalyzeIncidentResponse(BaseModel):
    raw_output: str
    parsed_output: dict[str, Any] | None = None


class SaveKnowledgeRequest(BaseModel):
    description: str | None = None
    log_line: str | None = None
    parsed_output: dict[str, Any] | None = None
    notes: str | None = None


class SaveKnowledgeResponse(BaseModel):
    id: str
    file_path: str
    message: str


class FollowUpRequest(BaseModel):
    question: str = Field(..., min_length=1)
    description: str | None = None
    log_line: str | None = None
    incident_text: str | None = None
    parsed_output: dict[str, Any] | None = None
    raw_output: str | None = None
    chat_history: list[dict[str, str]] | None = None


class FollowUpResponse(BaseModel):
    answer: str


def _compose_incident_text(payload: AnalyzeIncidentRequest) -> str:
    if payload.incident_text and payload.incident_text.strip():
        return payload.incident_text.strip()

    description = (payload.description or "").strip()
    log_line = (payload.log_line or "").strip()
    parts: list[str] = []
    if description:
        parts.append(f"Description:\n{description}")
    if log_line:
        parts.append(f"Logs:\n{log_line}")
    return "\n\n".join(parts).strip()


def _compose_incident_text_followup(payload: FollowUpRequest) -> str:
    if payload.incident_text and payload.incident_text.strip():
        return payload.incident_text.strip()

    description = (payload.description or "").strip()
    log_line = (payload.log_line or "").strip()
    parts: list[str] = []
    if description:
        parts.append(f"Description:\n{description}")
    if log_line:
        parts.append(f"Logs:\n{log_line}")
    return "\n\n".join(parts).strip()


@app.get("/health")
def health() -> dict[str, str]:
    logger.info("Health check requested")
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeIncidentResponse)
def analyze(payload: AnalyzeIncidentRequest) -> AnalyzeIncidentResponse:
    trace_id = str(uuid.uuid4())
    incident_text = _compose_incident_text(payload)
    if not incident_text:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one of: incident_text, description, log_line.",
        )

    logger.info(
        "Analyze API request received | trace_id=%s incident_len=%s",
        trace_id,
        len(incident_text),
    )
    try:
        result = analyze_incident(incident_text, trace_id=trace_id)
    except Exception as exc:
        logger.exception("Analyze API failed | trace_id=%s", trace_id)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc

    parsed: dict[str, Any] | None = None
    try:
        parsed_candidate = json.loads(result)
        if isinstance(parsed_candidate, dict):
            parsed = parsed_candidate
    except Exception:
        parsed = None

    logger.info(
        "Analyze API completed | trace_id=%s parsed=%s output_len=%s",
        trace_id,
        parsed is not None,
        len(result),
    )
    return AnalyzeIncidentResponse(raw_output=result, parsed_output=parsed)


@app.post("/knowledge/save", response_model=SaveKnowledgeResponse)
def save_knowledge(payload: SaveKnowledgeRequest) -> SaveKnowledgeResponse:
    if not (payload.description or payload.log_line or payload.parsed_output):
        raise HTTPException(
            status_code=400,
            detail="Provide at least one of: description, log_line, parsed_output.",
        )

    try:
        result = save_knowledge_entry(payload.model_dump())
    except Exception as exc:
        logger.exception("Knowledge save failed")
        raise HTTPException(status_code=500, detail=f"Knowledge save failed: {exc}") from exc

    return SaveKnowledgeResponse(
        id=result["id"],
        file_path=result["file_path"],
        message="Knowledge saved and indexed successfully.",
    )


@app.post("/followup", response_model=FollowUpResponse)
def followup(payload: FollowUpRequest) -> FollowUpResponse:
    trace_id = str(uuid.uuid4())
    incident_text = _compose_incident_text_followup(payload)
    if not incident_text:
        raise HTTPException(
            status_code=400,
            detail="Provide incident context: incident_text or description/log_line.",
        )

    analysis_json = "{}"
    if payload.parsed_output:
        try:
            analysis_json = json.dumps(payload.parsed_output, ensure_ascii=False)
        except Exception:
            analysis_json = "{}"
    elif payload.raw_output:
        analysis_json = payload.raw_output

    logger.info(
        "Follow-up API request received | trace_id=%s question_len=%s",
        trace_id,
        len(payload.question),
    )
    try:
        answer = follow_up_discussion(
            incident_text=incident_text,
            question=payload.question,
            analysis_json=analysis_json,
            chat_history=payload.chat_history or [],
            trace_id=trace_id,
        )
    except Exception as exc:
        logger.exception("Follow-up API failed | trace_id=%s", trace_id)
        raise HTTPException(status_code=500, detail=f"Follow-up failed: {exc}") from exc

    return FollowUpResponse(answer=answer)

import json
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from logging_config import get_logger
from query_rag import analyze_incident

app = FastAPI(
    title="DevOps Incident Analyzer API",
    version="1.0.0",
)
logger = get_logger(__name__)


class AnalyzeIncidentRequest(BaseModel):
    incident_text: str = Field(..., min_length=1, description="Raw incident details.")


class AnalyzeIncidentResponse(BaseModel):
    raw_output: str
    parsed_output: dict[str, Any] | None = None


@app.get("/health")
def health() -> dict[str, str]:
    logger.info("Health check requested")
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeIncidentResponse)
def analyze(payload: AnalyzeIncidentRequest) -> AnalyzeIncidentResponse:
    trace_id = str(uuid.uuid4())
    logger.info(
        "Analyze API request received | trace_id=%s incident_len=%s",
        trace_id,
        len(payload.incident_text),
    )
    try:
        result = analyze_incident(payload.incident_text, trace_id=trace_id)
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

import json
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from query_rag import analyze_incident

app = FastAPI(
    title="DevOps Incident Analyzer API",
    version="1.0.0",
)


class AnalyzeIncidentRequest(BaseModel):
    incident_text: str = Field(..., min_length=1, description="Raw incident details.")


class AnalyzeIncidentResponse(BaseModel):
    raw_output: str
    parsed_output: dict[str, Any] | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeIncidentResponse)
def analyze(payload: AnalyzeIncidentRequest) -> AnalyzeIncidentResponse:
    try:
        result = analyze_incident(payload.incident_text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc

    parsed: dict[str, Any] | None = None
    try:
        parsed_candidate = json.loads(result)
        if isinstance(parsed_candidate, dict):
            parsed = parsed_candidate
    except Exception:
        parsed = None

    return AnalyzeIncidentResponse(raw_output=result, parsed_output=parsed)

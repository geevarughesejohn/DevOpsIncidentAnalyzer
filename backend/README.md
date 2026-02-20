# DevOps Incident Analyzer

RAG-based incident analysis project using:
- Azure OpenAI (embeddings + chat)
- FAISS vector index
- Optional Stack Overflow enrichment via Stack Exchange API
- FastAPI for API exposure

## Project Structure

- `ingest_faiss.py`: Loads JSON docs from `data/`, creates FAISS index.
- `query_rag.py`: Retrieves relevant context and generates incident analysis.
- `model_config.py`: Centralized Azure model + TLS/client config.
- `prompts.py`: Prompt templates.
- `stackexchange_tool.py`: Stack Overflow enrichment helper.
- `api.py`: FastAPI app (`/health`, `/analyze`).
- `faiss_index/`: Generated vector index (after ingest).

## Prerequisites

- Python 3.10+
- Valid Azure/OpenAI-compatible endpoint and key
- `tiktoken_cache` folder containing required cache file used by `model_config.py`

## Setup

From repo root, run commands inside `backend/`:

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r backend/requirements.txt
```

## Environment Variables

Create `.env` in `backend/`:

```env
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=https://your-endpoint
AZURE_OPENAI_API_VERSION=2024-02-01

AZURE_OPENAI_CHAT_DEPLOYMENT=
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=
AZURE_OPENAI_CHAT_MODEL=azure/genailab-maas-gpt-4o
AZURE_OPENAI_EMBEDDING_MODEL=azure/genailab-maas-text-embedding-3-large

AZURE_OPENAI_SSL_VERIFY=false
AZURE_OPENAI_CA_BUNDLE=

# Optional external enrichment
STACKEXCHANGE_API_KEY=
ENABLE_WEB_ENRICHMENT=true
WEB_RESULTS_K=3
STACKEXCHANGE_SSL_VERIFY=true
STACKEXCHANGE_CA_BUNDLE=

# Logging
LOG_LEVEL=INFO
LOG_TO_FILE=true
LOG_FILE_PATH=logs/app.log

# Frontend CORS
FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Notes:
- Prefer deployment names (`AZURE_OPENAI_CHAT_DEPLOYMENT`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`) if your gateway requires them.
- If TLS verification is required in your environment, set:
  - `AZURE_OPENAI_SSL_VERIFY=true`
  - `AZURE_OPENAI_CA_BUNDLE=<path-to-ca-bundle.pem>`
- You can also keep your existing key name `stackapps_key`; code supports both:
  - `STACKEXCHANGE_API_KEY`
  - `stackapps_key`
- For Stack Exchange TLS in corporate networks:
  - preferred: set `STACKEXCHANGE_CA_BUNDLE=<path-to-ca.pem>`
  - temporary workaround: set `STACKEXCHANGE_SSL_VERIFY=false`

## Data Format

Place JSON files under `data/` (subfolders supported). Each file should have:

```json
{
  "id": "DOC-XXX-001",
  "content": "Text content...",
  "metadata": {
    "category": "incident",
    "service": "payment-api",
    "severity": "High",
    "tags": ["timeout", "503"]
  }
}
```

## Build Vector Index

```powershell
python backend/ingest_faiss.py
```

Expected success:
- `Loaded <N> documents`
- `FAISS index created successfully!`

## Run Query Script

```powershell
python backend/query_rag.py
```

## Run API

```powershell
uvicorn --app-dir backend api:app --host 0.0.0.0 --port 8000 --reload
```

Logs are written to console and (by default) `backend/logs/app.log`.
Each API analysis call gets a `trace_id` so you can follow end-to-end flow.

### Endpoints

- `GET /health`
- `POST /analyze`
- `POST /followup`
- `POST /knowledge/save`

Request body:

```json
{
  "description": "Users experiencing HTTP 503 errors on payment API.",
  "log_line": "DB timeout; connection pool usage at 97%; pods restarting."
}
```

Backward-compatible request format is still supported:

```json
{
  "incident_text": "Users experiencing HTTP 503 errors..."
}
```

Save learned solution into RAG:

```json
{
  "description": "Order service pods restart after deployment v1.4.2",
  "log_line": "OOMKilled; exit code 137; CrashLoopBackOff",
  "parsed_output": {
    "executive_summary": "Order service pods restarted repeatedly due to memory pressure.",
    "root_cause": "Memory leak in release v1.4.2",
    "impacted_services": ["order-service"],
    "indicators_detected": ["OOMKilled", "exit code 137"],
    "severity": "High",
    "resolution_steps": ["Rollback to v1.4.1", "Increase memory from 512Mi to 1Gi"],
    "preventive_actions": ["Add load tests before release"],
    "confidence_score": 0.9
  },
  "notes": "Validated by on-call engineer."
}
```

Follow-up discussion request:

```json
{
  "description": "Order service pods restart after deployment v1.4.2",
  "log_line": "OOMKilled; exit code 137; CrashLoopBackOff",
  "question": "What should be our first alert to prevent recurrence?",
  "parsed_output": {
    "executive_summary": "...",
    "root_cause": "...",
    "resolution_steps": ["..."]
  },
  "chat_history": [
    {"role": "user", "content": "Can we rollback first?"},
    {"role": "assistant", "content": "Yes, rollback is immediate containment."}
  ]
}
```

Response:

```json
{
  "raw_output": "...",
  "parsed_output": {
    "executive_summary": "...",
    "root_cause": "...",
    "impacted_services": [],
    "indicators_detected": [],
    "severity": "High",
    "resolution_steps": [],
    "preventive_actions": [],
    "confidence_score": 0.85
  }
}
```

## Quick API Test

```powershell
curl -X POST "http://127.0.0.1:8000/analyze" `
  -H "Content-Type: application/json" `
  -d "{\"incident_text\":\"Users experiencing HTTP 503 errors and DB timeouts\"}"
```

# DevOps Incident Analyzer

RAG-based incident analysis project using:
- Azure OpenAI (embeddings + chat)
- FAISS vector index
- FastAPI for API exposure

## Project Structure

- `ingest_faiss.py`: Loads JSON docs from `data/`, creates FAISS index.
- `query_rag.py`: Retrieves relevant context and generates incident analysis.
- `model_config.py`: Centralized Azure model + TLS/client config.
- `prompts.py`: Prompt templates.
- `api.py`: FastAPI app (`/health`, `/analyze`).
- `faiss_index/`: Generated vector index (after ingest).

## Prerequisites

- Python 3.10+
- Valid Azure/OpenAI-compatible endpoint and key
- `tiktoken_cache` folder containing required cache file used by `model_config.py`

## Setup

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

## Environment Variables

Create `.env` in project root:

```env
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=https://your-endpoint
AZURE_OPENAI_API_VERSION=2024-02-01

AZURE_OPENAI_CHAT_DEPLOYMENT=
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=
AZURE_OPENAI_CHAT_MODEL=azure/genailab-maas-gpt-4o-mini
AZURE_OPENAI_EMBEDDING_MODEL=azure/genailab-maas-text-embedding-3-large

AZURE_OPENAI_SSL_VERIFY=false
AZURE_OPENAI_CA_BUNDLE=
```

Notes:
- Prefer deployment names (`AZURE_OPENAI_CHAT_DEPLOYMENT`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`) if your gateway requires them.
- If TLS verification is required in your environment, set:
  - `AZURE_OPENAI_SSL_VERIFY=true`
  - `AZURE_OPENAI_CA_BUNDLE=<path-to-ca-bundle.pem>`

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
python ingest_faiss.py
```

Expected success:
- `Loaded <N> documents`
- `FAISS index created successfully!`

## Run Query Script

```powershell
python query_rag.py
```

## Run API

```powershell
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### Endpoints

- `GET /health`
- `POST /analyze`

Request body:

```json
{
  "incident_text": "Users experiencing HTTP 503 errors..."
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

# Frontend (React)

Simple React UI for `backend/api.py`.

## Run

From repo root:

```powershell
cd frontend
npm install
npm run dev
```

App runs on `http://localhost:5173`.

## API URL

Set API base URL in `frontend/.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Default is already `http://127.0.0.1:8000` if unset.

## Required Backend

Run backend API from repo root:

```powershell
uvicorn --app-dir backend api:app --host 0.0.0.0 --port 8000 --reload
```

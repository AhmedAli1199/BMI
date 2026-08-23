# BMI Sales & Data Brain

Custom build: FastAPI backend, Next.js (App Router + shadcn/ui) frontend, Postgres database. Deployed on Dokploy.

## Structure

- `backend/` — FastAPI service (SQLAlchemy + Alembic migrations)
- `frontend/` — Next.js app (TypeScript, Tailwind, shadcn/ui)
- `docs/build-spec.txt` — original n8n/Act! build spec (kept for reference; this build does not use n8n)

## Local development

```bash
docker compose up --build
```

- Backend: http://localhost:8000 (docs at `/docs`)
- Frontend: http://localhost:3000
- Postgres: localhost:5432 (`postgres` / `postgres` / db `bmi`)

Or run each service natively:

```bash
# backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload

# frontend
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

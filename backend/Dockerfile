FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# The ADMIN_EMAIL/ADMIN_PASSWORD seed step is opt-in and safe to leave
# configured indefinitely: seed_admin.py upserts by email, so it just
# re-applies the same password on every boot rather than creating
# duplicates - handy for resetting a lost login by setting env vars and
# redeploying instead of needing DB access.
CMD ["sh", "-c", "alembic upgrade head && if [ -n \"$ADMIN_EMAIL\" ] && [ -n \"$ADMIN_PASSWORD\" ]; then python -m scripts.seed_admin; fi && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

# ── Stage 1: build the React frontend ─────────────────────────────────────────
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python backend + built SPA ───────────────────────────────────────
FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Chromium for Playwright-based scrapers (Indeed, Naukri) and form filling.
# --with-deps pulls the OS libraries Chromium needs on slim images.
RUN playwright install --with-deps chromium

COPY agents/ agents/
COPY backend/ backend/
COPY config/ config/
COPY orchestrator/ orchestrator/
COPY skills/ skills/
COPY state/ state/
COPY tools/ tools/
COPY main.py ./

# Built SPA — backend/main.py serves frontend/dist at /
COPY --from=frontend-build /app/frontend/dist frontend/dist

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

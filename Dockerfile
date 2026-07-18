# syntax=docker/dockerfile:1

FROM node:22.12.0-bookworm-slim AS frontend-builder

WORKDIR /app/frontend
ENV NPM_CONFIG_CACHE=/tmp/npm-cache

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM python:3.11-slim AS runtime

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    REPOMIND_CACHE_DIR=/tmp/repomind/repos \
    PORT=7860

COPY requirements.txt ./
RUN apt-get update \
    && apt-get install --no-install-recommends -y git \
    && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10001 repomind \
    && mkdir -p /tmp/repomind/repos \
    && chown -R repomind:repomind /tmp/repomind

COPY --chown=repomind:repomind main.py master.py repository.py schemas.py settings.py worker.py artifacts.py ./
COPY --chown=repomind:repomind workers/ ./workers/
COPY --from=frontend-builder --chown=repomind:repomind /app/frontend/dist ./frontend/dist

USER repomind
EXPOSE 7860
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port \"${PORT:-7860}\""]

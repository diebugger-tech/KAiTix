# =============================================================================
# KAiTix — Multi-Stage Containerfile (ubuntu:24.04 Base)
# =============================================================================
# Build-Stage: baut das statische Frontend mit Node.js 22
# Runtime-Stage: enthält nur Python + FastAPI (inkl. statischer Frontend-Dateien)
# =============================================================================

# -----------------------------------------------------------------------------
# 1. Build-Stage (Node)
# -----------------------------------------------------------------------------
FROM ubuntu:24.04 AS build-stage
ENV DEBIAN_FRONTEND=noninteractive
ENV NODE_MAJOR=22

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_${NODE_MAJOR}.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY frontend/ /app/frontend/
RUN cd /app/frontend \
    && npm ci \
    && npm run build

# -----------------------------------------------------------------------------
# 2. Runtime-Stage (Python)
# -----------------------------------------------------------------------------
FROM ubuntu:24.04 AS runtime-stage
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    pkg-config \
    default-libmysqlclient-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN python3 -m venv /app/.venv
ENV PATH="/app/.venv/bin:${PATH}"
ENV VIRTUAL_ENV="/app/.venv"

# Requirements installieren (gepinnt)
COPY requirements.txt /app/
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Code kopieren
COPY app/ /app/app/
COPY alembic.ini /app/
# (Die Alembic-Migrations-Ordner müssen auch mit!)
COPY alembic/ /app/alembic/

# Gebautes Frontend aus Build-Stage kopieren
COPY --from=build-stage /app/frontend/build /app/frontend/build

ENV APP_PORT=8003
EXPOSE 8003

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]

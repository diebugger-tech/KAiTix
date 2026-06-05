# =============================================================================
# KAiTix — All-in-One Containerfile (ubuntu:24.04 Base)
# =============================================================================
# Zweck: Einzelnes Image für Backend + Frontend auf Basis der
#        manuellen Installationsanleitung aus der README.
#
# Build:  podman build -f Containerfile -t kaitix:latest .
# Run:    podman run -p 8080:80 -e DATABASE_URL=... kaitix:latest
#
# HINWEIS: MySQL ist KEIN Teil dieses Images. Es wird als externer
#          Service vorausgesetzt (siehe docker-compose.yml).
#
# BEKANNTE LÜCKEN:
#   1. requirements.txt enthält keine gepinnten Versionen (alle >=).
#      Reproduzierbarkeit ist daher nicht vollständig garantiert.
#   2. Die Test-Suite läuft gegen SQLite (aiosqlite), nicht gegen MySQL.
#      Obwohl aiomysql in requirements.txt steht, wird die echte
#      DB-Schicht in den 38 Tests nicht validiert.
# =============================================================================

FROM ubuntu:24.04 AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV NODE_MAJOR=22

# =============================================================================
# 1. System-Abhängigkeiten
# =============================================================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    make \
    gcc \
    pkg-config \
    default-libmysqlclient-dev \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# 2. Node.js 22+ installieren (Frontend-Build)
# =============================================================================
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_MAJOR}.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# 3. Arbeitsverzeichnis & Code
# =============================================================================
WORKDIR /app
COPY . /app/

# =============================================================================
# 4. Python-Abhängigkeiten (venv — PEP 668 kompatibel)
# =============================================================================
# HINWEIS: requirements.txt enthält ausschließlich >=-Pins.
#          Für vollständige Reproduzierbarkeit müssten Versionen
#          exakt festgeschrieben werden (z. B. via pip freeze).
RUN python3 -m venv /app/.venv \
    && /app/.venv/bin/pip install --upgrade pip \
    && /app/.venv/bin/pip install --no-cache-dir -r requirements.txt

# =============================================================================
# 5. Frontend bauen
# =============================================================================
# @sveltejs/adapter-auto erkennt im Container keine Produktionsumgebung.
# Daher wird adapter-node verwendet, der einen produktionsreifen
# Node-Server in frontend/build/ erzeugt.
RUN cd /app/frontend \
    && npm ci \
    && npm install @sveltejs/adapter-node \
    && sed -i "s|import adapter from '@sveltejs/adapter-auto';|import adapter from '@sveltejs/adapter-node';|" svelte.config.js \
    && npm run build

# =============================================================================
# 6. nginx-Konfiguration (Single-Port)
# =============================================================================
# Alle Anfragen laufen über Port 80. /api/ geht an das Backend,
# alles andere an das SvelteKit-Frontend.
RUN echo 'server {' > /etc/nginx/sites-available/default && \
    echo '    listen 80;' >> /etc/nginx/sites-available/default && \
    echo '    server_name localhost;' >> /etc/nginx/sites-available/default && \
    echo '' >> /etc/nginx/sites-available/default && \
    echo '    location /api/ {' >> /etc/nginx/sites-available/default && \
    echo '        proxy_pass http://127.0.0.1:8003;' >> /etc/nginx/sites-available/default && \
    echo '        proxy_set_header Host $host;' >> /etc/nginx/sites-available/default && \
    echo '        proxy_set_header X-Real-IP $remote_addr;' >> /etc/nginx/sites-available/default && \
    echo '    }' >> /etc/nginx/sites-available/default && \
    echo '' >> /etc/nginx/sites-available/default && \
    echo '    location / {' >> /etc/nginx/sites-available/default && \
    echo '        proxy_pass http://127.0.0.1:3000;' >> /etc/nginx/sites-available/default && \
    echo '        proxy_set_header Host $host;' >> /etc/nginx/sites-available/default && \
    echo '        proxy_http_version 1.1;' >> /etc/nginx/sites-available/default && \
    echo '        proxy_set_header Upgrade $http_upgrade;' >> /etc/nginx/sites-available/default && \
    echo '        proxy_set_header Connection "upgrade";' >> /etc/nginx/sites-available/default && \
    echo '    }' >> /etc/nginx/sites-available/default && \
    echo '}' >> /etc/nginx/sites-available/default

# =============================================================================
# 7. Laufzeit-Konfiguration
# =============================================================================
ENV PATH="/app/.venv/bin:${PATH}"
ENV VIRTUAL_ENV="/app/.venv"
ENV APP_PORT=8003
ENV ORIGIN=http://localhost:3000

EXPOSE 80

# =============================================================================
# 8. Start-Skript (Backend + Frontend + nginx)
# =============================================================================
RUN echo '#!/bin/bash' > /app/start.sh && \
    echo 'set -e' >> /app/start.sh && \
    echo '' >> /app/start.sh && \
    echo 'echo ">>> Starte KAiTix Frontend (Port 3000)..."' >> /app/start.sh && \
    echo 'cd /app/frontend && node build/index.js &' >> /app/start.sh && \
    echo 'FRONTEND_PID=$!' >> /app/start.sh && \
    echo '' >> /app/start.sh && \
    echo 'echo ">>> Starte KAiTix Backend (Port 8003)..."' >> /app/start.sh && \
    echo 'cd /app && uvicorn app.main:app --host 0.0.0.0 --port 8003 &' >> /app/start.sh && \
    echo 'BACKEND_PID=$!' >> /app/start.sh && \
    echo '' >> /app/start.sh && \
    echo 'echo ">>> Starte nginx (Port 80)..."' >> /app/start.sh && \
    echo 'nginx -g "daemon off;" &' >> /app/start.sh && \
    echo 'NGINX_PID=$!' >> /app/start.sh && \
    echo '' >> /app/start.sh && \
    echo 'sleep 2' >> /app/start.sh && \
    echo 'echo ""' >> /app/start.sh && \
    echo 'echo "=================================================================="' >> /app/start.sh && \
    echo 'echo "  KAiTix laeuft!  Im Browser oeffnen:   http://localhost:8080"' >> /app/start.sh && \
    echo 'echo "  NICHT 0.0.0.0 und NICHT :3000 / :8003 (das sind interne Ports)."' >> /app/start.sh && \
    echo 'echo "=================================================================="' >> /app/start.sh && \
    echo 'echo ""' >> /app/start.sh && \
    echo 'cleanup() {' >> /app/start.sh && \
    echo '    echo ">>> Stoppe Services..."' >> /app/start.sh && \
    echo '    kill $FRONTEND_PID $BACKEND_PID $NGINX_PID 2>/dev/null || true' >> /app/start.sh && \
    echo '    wait' >> /app/start.sh && \
    echo '    exit 0' >> /app/start.sh && \
    echo '}' >> /app/start.sh && \
    echo 'trap cleanup SIGTERM SIGINT' >> /app/start.sh && \
    echo '' >> /app/start.sh && \
    echo 'wait' >> /app/start.sh && \
    chmod +x /app/start.sh

CMD ["/app/start.sh"]

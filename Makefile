# =============================================================================
# KAiTix — Development Makefile
# =============================================================================

.PHONY: install dev dev-frontend dev-all status help test lint format migrate-create migrate-apply db-shell restart-all clean clean-bak check-branch

# === UTILS & CHECKS ==========================================================
check-branch:
	@BRANCH=$$(git branch --show-current); \
	if ! echo "$$BRANCH" | grep -qE "^(feature/agent-.*|main|dev)$$"; then \
		echo "FEHLER: Unerwarteter Branch '$$BRANCH'. Erwartet: feature/agent-*, main oder dev."; \
		exit 1; \
	fi

# === SETUP ===================================================================
install:
	@if [ -z "$$IN_NIX_SHELL" ] && [ -z "$$NIX_BUILD_SHELL" ]; then \
		echo "FEHLER: make install darf nur innerhalb von nix-shell ausgeführt werden!"; \
		exit 1; \
	fi
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "FEHLER: Kein virtuelles Environment (.venv) aktiv! Bitte führe zuerst 'source .venv/bin/activate' aus."; \
		exit 1; \
	fi
	@echo ">>> Installiere Abhängigkeiten..."
	python3 -m pip install -r requirements.txt
	@echo ">>> Installation abgeschlossen."

# === DEVELOPMENT =============================================================
dev:
	@if [ ! -d ".venv" ]; then echo "FEHLER: .venv fehlt. nix-shell starten und 'make install' ausführen."; exit 1; fi
	@echo ">>> Starte Backend (Port 8003)..."
	. .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8003

dev-frontend:
	@echo ">>> Starte Frontend (Port 5175)..."
	cd frontend && npm run dev

dev-all:
	@if [ ! -d ".venv" ]; then echo "FEHLER: .venv fehlt. nix-shell starten und 'make install' ausführen."; exit 1; fi
	@echo ">>> Starte Backend + Frontend parallel (Ctrl+C stoppt beide)..."
	@trap 'kill %1 %2 2>/dev/null; exit' INT TERM; \
	. .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8003 & \
	cd frontend && npm run dev & \
	wait

status:
	@echo "=== KAiTix Service Status ==="
	@ss -tlnp 2>/dev/null | grep -E "8003|5175" && echo "" || echo "Keine Services aktiv"
	@[ -d ".venv" ] && echo "venv:        OK (.venv vorhanden)" || echo "venv:        FEHLT"
	@[ -n "$$IN_NIX_SHELL" ] && echo "nix-shell:   AKTIV" || echo "nix-shell:   nicht aktiv"
	@[ -n "$$VIRTUAL_ENV" ] && echo "venv aktiv:  $$VIRTUAL_ENV" || echo "venv aktiv:  nein"

help:
	@echo ""
	@echo "KAiTix — Makefile Targets"
	@echo "─────────────────────────────────────────"
	@echo "  make dev              Backend starten (Port 8003)"
	@echo "  make dev-frontend     Frontend starten (Port 5175)"
	@echo "  make dev-all          Backend + Frontend parallel"
	@echo "  make status           Service-Status anzeigen"
	@echo "  make install          Abhängigkeiten installieren (nix-shell!)"
	@echo "  make test             pytest"
	@echo "  make lint             ruff + mypy"
	@echo "  make format           ruff fix + format"
	@echo "  make migrate-create message='...'  Alembic Revision"
	@echo "  make migrate-apply    Alembic upgrade head"
	@echo "  make db-shell         MySQL Shell"
	@echo "  make clean            pycache + .bak bereinigen"
	@echo ""

# === TESTING =================================================================
test:
	@echo ">>> Führe Tests aus..."
	pytest -v --asyncio-mode=auto

# === CODE QUALITY ============================================================
lint:
	@echo ">>> Linting mit ruff..."
	ruff check .
	@echo ">>> Typ-Check mit mypy..."
	mypy .

format:
	@echo ">>> Formatiere Code mit ruff..."
	ruff check --fix .
	ruff format .

# === DATABASE ================================================================
migrate-create:
	@if [ -z "$(message)" ]; then \
		echo "FEHLER: message ist nicht definiert! Verwendung: make migrate-create message='migration description'"; \
		exit 1; \
	fi
	@echo ">>> Neue Migration erstellen..."
	python3 -m alembic revision --autogenerate -m "$(message)"

migrate-apply:
	@echo ">>> Migration auf Datenbank anwenden..."
	python3 -m alembic upgrade head

db-shell:
	@echo ">>> Starte MySQL-Shell..."
	mysql -u $$(echo $(DATABASE_URL) | sed -n 's/.*:\/\/\([^:]*\).*/\1/p') -p

# === UTILITIES ===============================================================
restart-all: clean
	@echo ">>> Starte alles frisch..."
	make dev

clean-bak:
	@echo ">>> Bereinige *.bak Backup-Dateien..."
	find . -type f -name "*.bak" -delete
	@echo ">>> Backup-Dateien gelöscht."

clean: clean-bak
	@echo ">>> Bereinige generierte Dateien..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov dist build
	@echo ">>> Bereinigung abgeschlossen."


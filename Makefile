# =============================================================================
# KAiTix — Development Makefile
# =============================================================================

BACKEND_PORT  ?= 8003
# Branch für make update: standardmäßig der aktuell ausgecheckte (make update BRANCH=main für main)
BRANCH        ?= $(shell git branch --show-current)
FRONTEND_PORT ?= 5175

# Verzeichnisse, die find bei clean/clean-bak überspringt.
# Hinweis: -prune nicht mit -delete kombinieren (-delete impliziert -depth und hebelt -prune aus).
FIND_PRUNE := \( -path ./.venv -o -path ./frontend/node_modules -o -path ./node_modules -o -path ./.git -o -path ./.direnv \) -prune -o

.PHONY: install update check-db dev dev-frontend dev-all stop stop-backend stop-frontend status help test lint format migrate-create migrate-apply db-shell restart-all clean clean-bak check-branch

# Beendet alle Prozesse auf einem TCP-Port: erst SIGTERM, nach max. 5 s SIGKILL.
# Schlägt nicht fehl, wenn nichts läuft. $(1) = Port, $(2) = Name
define stop_port
	@if fuser $(1)/tcp >/dev/null 2>&1; then \
		echo ">>> Stoppe $(2) (Port $(1))..."; \
		fuser -k -TERM $(1)/tcp >/dev/null 2>&1 || true; \
		i=0; while fuser $(1)/tcp >/dev/null 2>&1 && [ $$i -lt 10 ]; do sleep 0.5; i=$$((i+1)); done; \
		if fuser $(1)/tcp >/dev/null 2>&1; then \
			echo ">>> $(2) reagiert nicht auf SIGTERM, sende SIGKILL..."; \
			fuser -k -KILL $(1)/tcp >/dev/null 2>&1 || true; \
		fi; \
		echo ">>> $(2) gestoppt."; \
	else \
		echo ">>> $(2) läuft nicht (Port $(1) frei)."; \
	fi
endef

# === UTILS & CHECKS ==========================================================
check-branch:
	@BRANCH=$$(git branch --show-current); \
	if ! echo "$$BRANCH" | grep -qE "^(feature/agent-.*|main|develop)$$"; then \
		echo "FEHLER: Unerwarteter Branch '$$BRANCH'. Erwartet: feature/agent-*, main oder develop."; \
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
	@echo ">>> Installiere Frontend-Abhängigkeiten (npm ci)..."
	cd frontend && npm ci
	@echo ">>> Installation abgeschlossen."

update:
	@if [ -z "$(BRANCH)" ]; then echo "FEHLER: Kein Branch ausgecheckt (detached HEAD). Nutze 'make update BRANCH=main'."; exit 1; fi
	@echo ">>> Hole neuesten Code von GitHub (Branch $(BRANCH))..."
	@if [ "$$(git branch --show-current)" != "$(BRANCH)" ]; then git checkout $(BRANCH); fi
	git pull --ff-only origin $(BRANCH)
	@if [ -n "$$IN_NIX_SHELL" ] && [ -n "$$VIRTUAL_ENV" ]; then \
		echo ">>> Installiere neue Abhängigkeiten..."; \
		make install; \
		echo ">>> Wende Datenbank-Migrationen an..."; \
		make migrate-apply; \
		echo ">>> Update erfolgreich! Starte den Server neu mit 'make restart-all'."; \
	else \
		echo ">>> Code aktualisiert! WICHTIG: Um das Update abzuschließen, aktiviere die nix-shell + venv und führe aus:"; \
		echo "    make install && make migrate-apply"; \
	fi

# Bricht ab, wenn die Datenbank nicht auf dem Migrationsstand des Codes ist.
# Überspringen (z. B. frische DB): SKIP_DB_CHECK=1
check-db:
	@if [ -n "$(SKIP_DB_CHECK)" ]; then exit 0; fi; \
	if [ ! -d ".venv" ]; then echo "FEHLER: .venv fehlt. nix-shell starten und 'make install' ausführen."; exit 1; fi; \
	CURRENT=$$(. .venv/bin/activate && python3 -m alembic current 2>/dev/null | tail -n1); \
	HEAD=$$(. .venv/bin/activate && python3 -m alembic heads 2>/dev/null | tail -n1); \
	if ! echo "$$CURRENT" | grep -q "(head)"; then \
		echo "FEHLER: Datenbank ist nicht auf dem aktuellen Migrationsstand."; \
		echo "        DB-Stand:   $${CURRENT:-leer/unbekannt}"; \
		echo "        Code-Stand: $$HEAD"; \
		echo "        Migrationen prüfen, Backup von data/kaitix.db anlegen, dann 'make migrate-apply' (nix-shell + venv)."; \
		echo "        Prüfung überspringen: SKIP_DB_CHECK=1 make ..."; \
		exit 1; \
	fi

# === DEVELOPMENT =============================================================
dev: check-db
	@if [ ! -d ".venv" ]; then echo "FEHLER: .venv fehlt. nix-shell starten und 'make install' ausführen."; exit 1; fi
	@echo ">>> Starte Backend (Port $(BACKEND_PORT))..."
	@echo ">>> Im Browser: http://localhost:$(BACKEND_PORT)/docs  (uvicorn zeigt 0.0.0.0 = Bind-Adresse, nicht im Browser öffnen)"
	. .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT)

dev-frontend:
	@echo ">>> Starte Frontend (Port $(FRONTEND_PORT))..."
	@echo ">>> Im Browser: http://localhost:$(FRONTEND_PORT)"
	cd frontend && KAITIX_FRONTEND_PORT=$(FRONTEND_PORT) KAITIX_BACKEND_PORT=$(BACKEND_PORT) npm run dev

dev-all: check-db
	@if [ ! -d ".venv" ]; then echo "FEHLER: .venv fehlt. nix-shell starten und 'make install' ausführen."; exit 1; fi
	@echo ">>> Starte Backend + Frontend parallel (Ctrl+C stoppt beide, sonst 'make stop')..."
	@echo ">>> UI im Browser:  http://localhost:$(FRONTEND_PORT)"
	@echo ">>> API-Doku:       http://localhost:$(BACKEND_PORT)/docs"
	@trap 'kill %1 %2 2>/dev/null; exit' INT TERM; \
	. .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT) & \
	cd frontend && KAITIX_FRONTEND_PORT=$(FRONTEND_PORT) KAITIX_BACKEND_PORT=$(BACKEND_PORT) npm run dev & \
	wait

stop: stop-backend stop-frontend
	@ss -tln 2>/dev/null | grep -qE ":($(BACKEND_PORT)|$(FRONTEND_PORT))\b" \
		&& echo ">>> WARNUNG: Ports noch belegt — 'make status' prüfen." \
		|| echo ">>> Alle KAiTix-Services gestoppt."

stop-backend:
	$(call stop_port,$(BACKEND_PORT),Backend)

stop-frontend:
	$(call stop_port,$(FRONTEND_PORT),Frontend)

status:
	@echo "=== KAiTix Service Status ==="
	@ss -tlnp 2>/dev/null | grep -E ":($(BACKEND_PORT)|$(FRONTEND_PORT))\b" && echo "" || echo "Keine Services aktiv"
	@[ -d ".venv" ] && echo "venv:        OK (.venv vorhanden)" || echo "venv:        FEHLT"
	@[ -n "$$IN_NIX_SHELL" ] && echo "nix-shell:   AKTIV" || echo "nix-shell:   nicht aktiv"
	@[ -n "$$VIRTUAL_ENV" ] && echo "venv aktiv:  $$VIRTUAL_ENV" || echo "venv aktiv:  nein"

help:
	@echo ""
	@echo "KAiTix — Makefile Targets"
	@echo "─────────────────────────────────────────"
	@echo "  make dev              Backend starten (Port $(BACKEND_PORT))"
	@echo "  make dev-frontend     Frontend starten (Port $(FRONTEND_PORT))"
	@echo "  make dev-all          Backend + Frontend parallel"
	@echo "  make stop             Backend + Frontend beenden"
	@echo "  make stop-backend     Nur Backend beenden"
	@echo "  make stop-frontend    Nur Frontend beenden"
	@echo "  make restart-all      stop + clean + dev-all"
	@echo "  make status           Service-Status anzeigen"
	@echo "  make install          Python- + Frontend-Abhängigkeiten (nix-shell!)"
	@echo "  make update           aktuellen Branch pullen, install + migrate-apply (BRANCH=main möglich)"
	@echo "  make check-db         Prüft Migrationsstand der DB (läuft vor dev/dev-all)"
	@echo "  make test             pytest"
	@echo "  make lint             ruff + mypy"
	@echo "  make format           ruff fix + format"
	@echo "  make migrate-create message='...'  Alembic Revision"
	@echo "  make migrate-apply    Alembic upgrade head"
	@echo "  make db-shell         MySQL Shell"
	@echo "  make clean            pycache, Caches + .bak bereinigen"
	@echo "  make clean-bak        nur *.bak bereinigen"
	@echo "  make check-branch     prüft erlaubten Branch"
	@echo ""
	@echo "  make -n <target>      Dry-Run: zeigt Befehle, ohne sie auszuführen"
	@echo ""
	@echo "  Browser:  UI   http://localhost:$(FRONTEND_PORT)"
	@echo "            API  http://localhost:$(BACKEND_PORT)/docs"
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

# alembic/versions bleibt unangetastet: generierte Migrationen sind immutable.
RUFF_FORMAT_EXCLUDE := --config 'extend-exclude = ["alembic/versions"]'

format:
	@echo ">>> Formatiere Code mit ruff (ohne alembic/versions)..."
	ruff check --fix $(RUFF_FORMAT_EXCLUDE) .
	ruff format $(RUFF_FORMAT_EXCLUDE) .

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
restart-all: stop clean
	@echo ">>> Starte alles frisch..."
	$(MAKE) dev-all

clean-bak:
	@echo ">>> Bereinige *.bak Backup-Dateien..."
	find . $(FIND_PRUNE) -type f -name "*.bak" -exec rm -f {} +
	@echo ">>> Backup-Dateien gelöscht."

clean: clean-bak
	@echo ">>> Bereinige generierte Dateien..."
	find . $(FIND_PRUNE) -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . $(FIND_PRUNE) -type f -name "*.pyc" -exec rm -f {} +
	find . $(FIND_PRUNE) -type f -name ".coverage" -exec rm -f {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov dist build
	@echo ">>> Bereinigung abgeschlossen."

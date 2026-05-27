# ARCHITECTURE.md — KAiTix

## Overview

KAiTix ist ein B2B-Infrastruktur-Dokumentationssystem für die Elektro- und Kabeldomäne. Es implementiert eine saubere Layered Architecture:
- **API Layer**: FastAPI Router, Pydantic-Validierung.
- **Service Layer**: Geschäftslogik, darunter die USV-Berechnungs-Engine, EPLAN-CSV-Import und Exporter.
- **Data Layer**: SQLAlchemy 2.x async ORM, Alembic-Migrationen.
- **Infrastructure**: MySQL (CabellistPro), zentralisiertes Konfigurations- und Dateimanagement.

## Tech Stack Decisions

| Komponente | Wahl | Begründung |
|---|---|---|
| Framework | FastAPI | Native async, automatische OpenAPI-Dokumentation, Pydantic-Integration |
| ORM | SQLAlchemy 2.x | Industriestandard, vollständige async-Unterstützung, Alembic-Migrationen |
| Datenbank | MySQL 8.4 | Etabliert im B2B-Umfeld, gute Performance bei relationalen Daten |
| Validierung | Pydantic V2 | Typsicherheit, automatische Serialisierung, hohe Performance |
| Exporter | `openpyxl` & `odfpy` | Native Unterstützung für die Generierung von Excel (XLSX) und OpenDocument (ODS) ohne Office-Installationen |
| Tests | pytest + httpx | Async-first, integrierte HTTP-Test-Clients |

## Key ADRs

### ADR-001: Async-First Architektur

**Status:** Accepted  
**Context:**  
Moderne APIs müssen hohe Concurrency verarbeiten. Blocking I/O würde den Durchsatz bei industriellen Workloads limitieren.

**Decision:**  
Alle Datenbankzugriffe und externen API-Calls werden asynchron implementiert. FastAPI mit `async def`, SQLAlchemy mit `AsyncSession`, aiomysql als Treiber.

**Consequences:**  
- ✅ Höherer Durchsatz bei I/O-bound Workloads
- ✅ Konsistentes Programmiermodell
- ❌ Steilere Lernkurve für neue Entwickler
- ❌ Debugging komplexer als synchroner Code

### ADR-002: Alembic für Datenbank-Migrationen

**Status:** Accepted  
**Context:**  
Schema-Änderungen müssen versioniert und reproduzierbar sein, insbesondere in Multi-Environment-Setups (dev, staging, prod).

**Decision:**  
Alembic als offizielles SQLAlchemy-Migrationstool. Jede Schema-Änderung erfordert eine eigenständige Migrationsdatei.

**Consequences:**  
- ✅ Versioniertes Schema über alle Umgebungen
- ✅ Downgrade-Pfad für Rollbacks
- ❌ Zusätzlicher Overhead bei jeder Schema-Änderung
- ❌ Erfordert Disziplin: niemals alte Migrationsdateien ändern

### ADR-003: Verbindungsübergreifende Transaktionsisolation für Tests

**Status:** Accepted  
**Context:**  
Tests, die Endpunkte wie den EPLAN-Import aufrufen, führen echte `db.commit()`-Befehle aus. Bei der Nutzung einer In-Memory SQLite-Datenbank persistieren diese Commits und führen bei aufeinanderfolgenden Tests zu UNIQUE-Constraint-Fehlern (z.B. bei Rack-Namen).

**Decision:**  
Wir binden die Test-Sessions an eine explizit geöffnete Verbindung des Engines, starten eine äußere Transaktion auf Verbindungsebene und rollen diese am Ende jedes Tests zurück.

**Consequences:**  
- ✅ 100%ige Isolation aller DB-Tests, selbst bei Aufruf von `db.commit()`.
- ✅ Keine manuelle Datenbankbereinigung oder Tabellen-Drops zwischen Testläufen erforderlich.
- ❌ Komplexere Session-Erzeugung im `db`-Fixture von Pytest.

### ADR-004: Frontend Modal-Pattern für Entity-Details

**Status:** Accepted  
**Context:**  
Die Navigation zu separaten Detail-Seiten (z.B. für Racks oder Geräte) unterbrach den Workflow. Benutzer mussten die Kontext-Übersicht (Topologie oder Rack-Layout) verlassen, um Details oder das VDE-Protokoll einzusehen, was den "Plan. Simulate. Document." Flow störte.

**Decision:**  
Geräte- und Rack-Details werden als zentrierte Overlays (Modals) mit Tab-Navigation (z.B. Geräte-Details, Ports & Kabel, VDE Protokoll) umgesetzt. 

**Consequences:**  
- ✅ Der Benutzer behält den visuellen Kontext (Dashboard/Rack-Ansicht) im Hintergrund.
- ✅ Schnellerer Wechsel zwischen verschiedenen Geräten ohne Page-Reloads.
- ❌ Erfordert sauberes State-Management (Svelte 5 `$state`), um das Modal an verschiedenen Stellen aufrufen zu können.
- ❌ URL-Routing für tiefe Links (Deep-Linking zu einem spezifischen Modal-Tab) ist aufwändiger.

## Open Questions

1. **Caching-Strategie**: Redis für Session-Storage vs. API-Response-Caching — noch nicht entschieden
2. **Message Queue**: Benötigen wir Celery/RQ für Background-Jobs oder reicht async?
3. **Multi-Tenancy**: Row-level Security vs. separate Schemas pro Tenant

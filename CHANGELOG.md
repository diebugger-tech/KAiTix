# Changelog

Alle wesentlichen Änderungen am Projekt werden in dieser Datei dokumentiert.

## [Unreleased]

## [1.0.0] — 2026-05-22

### Hinzugefügt
- Rittal VX IT / TS IT Racks im Hardware-Katalog (8 Varianten, 42/47 HE, 600/800mm)
- Kentix SmartPDU Modelle (Zero-U vertikal, min_rack_hoehe Validierung)
- RackModal als wiederverwendbare Svelte-Komponente (Dashboard + Racks)
- Rack-Modell Auswahl mit automatischer Höhen- und Breitenvorgabe
- PDU-Seiten-Zuordnung (0UL / 0UR, max. 1 PDU pro Seite)
- Topologie-Filter (Geräte, Kabel, Ansicht, Rack-Filter)
- Bearbeiter-Freitext im Frontend (localStorage, X-Username Header)
- CORS auf localhost beschränkt
- Hardware-Katalog kategorie-spezifische Kartenansicht

### Geändert
- hoehe_u Eingabe: Dropdown statt Freitext (dynamisch aus Katalog)
- breite_mm: aus Rack-Modell übernommen, nicht mehr manuell
- USV-Berechnung: Fallback-Kette (Kentix-Messung → psu_nennwatt → tdp_watt)

### Behoben
- Schema-Drift breite_mm (fehlte im ORM/Pydantic)
- alarm_ok Logik invertiert in kentix.py
- min_rack_hoehe: 40HE-PDUs korrigiert auf 42 (nicht 40)

## [0.1.0] — 2025

### Hinzugefügt
- Initiales FastAPI Backend + Svelte 5 Frontend
- Rack-, Geräte-, Kabel- und USV-Verwaltung
- Kentix SmartPDU Integration (REST-API)
- Export: Excel, ODS, CSV, PDF
- Hardware-Katalog mit JSON-Datei
- Topologie-Visualisierung

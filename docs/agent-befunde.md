## 2026-11-17 · Umbau A0 Review · Kimi
- CSV- und EPLAN-Import schreiben Kabel an CablingService vorbei, ohne Belegungsprüfung — app/domains/import_export/routers/import_csv.py:443-478, app/domains/import_export/routers/import_eplan.py:307-331 — Beim Review der zentralen Belegungsprüfung in Phase A0 aufgefallen.

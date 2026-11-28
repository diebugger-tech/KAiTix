## 2026-11-17 · Umbau A0 Review · Kimi
- CSV- und EPLAN-Import schreiben Kabel an CablingService vorbei, ohne Belegungsprüfung — app/domains/import_export/routers/import_csv.py:443-478, app/domains/import_export/routers/import_eplan.py:307-331 — Beim Review der zentralen Belegungsprüfung in Phase A0 aufgefallen.

## 2026-11-17 · Umbau A2 · Claude Fable 5.2
- CSV- und EPLAN-Import legen Kabel ohne kabeltyp_id an; importierte Kabel haben dadurch keinen Katalogtyp — app/domains/import_export/routers/import_csv.py:469-471, app/domains/import_export/routers/import_eplan.py:308 — Aufgefallen, weil der CablingService die Zuordnung typ → kabeltyp_id jetzt setzt und beide Importe ihn umgehen.
- "Strom-C13-Lock" und "Strom-C19-Lock" stehen in festen Frontend-Listen, sind aber weder im Enum cables.typ noch im Katalog; über die Formulare sind sie seit der Katalog-Auswahl nicht mehr wählbar — frontend/src/routes/(app)/cables/+page.svelte:64,86,99, frontend/src/routes/(app)/racks/+page.svelte:1143,1158 — Beim Ersetzen der festen Formularlisten durch GET /kabeltypen aufgefallen.
- Weitere feste Typlisten bleiben neben dem Katalog bestehen: Filter, Kategorien und Badges der Kabelliste sowie der Zielgeräte-Filter im Rack-Formular, der auf typ-Strings prüft — frontend/src/routes/(app)/cables/+page.svelte:60,86,90, frontend/src/routes/(app)/racks/+page.svelte:1093-1096,1121-1124 — Neue Katalogtypen (z. B. Breakouts mit alt_typ "sonstige") laufen dort in den Standardzweig.
- request() setzt bei jeder fehlgeschlagenen Antwort den Backend-Status auf offline, auch bei fachlichen 409/422 — frontend/src/lib/api.ts:531-533 — Aufgefallen, weil die neuen 409-Antworten (Kabeltyp verwendet, Name vergeben) diesen Weg nehmen.
- request() übernimmt parsed.detail ungeprüft als Fehlermeldung; bei Pydantic-Validierungsfehlern ist detail eine Liste und ergibt "[object Object]" — frontend/src/lib/api.ts:520 — Beim Prüfen der 422-Anzeige für die Kabeltyp-Pflegeseite aufgefallen.

## 2026-11-17 · Umbau A3 · Claude Fable 5.2
- Breakout-Kabel haben kein Ziel am Kabel und fallen deshalb aus der Topologie: build_edges nimmt nur Kabel mit von_device_id und nach_device_id — app/domains/cabling/services.py:280 — Aufgefallen, weil die neue Regel nach_device_id/nach_port bei enden_b > 1 leer lässt.
- trace_cable folgt nur den Enden am Kabel; die Strang-Enden eines Breakouts werden nicht verfolgt — app/domains/cabling/services.py:704 — Beim Erweitern der Belegungsprüfung um Strang-Enden gesehen.
- Die Doppelbelegungsprüfung der Simulation (7c) kennt keine Strang-Enden; die Belegungsprüfung im CablingService kennt sie seit A3 — app/domains/simulation/services.py:666-680 — Beide Prüfungen sollten laut A0 dieselbe Semantik haben und laufen jetzt auseinander.
- Der Kabel-Export gibt von_port/nach_port des Kabels aus; bei Breakouts bleibt die Zielspalte leer, die Stränge fehlen — app/domains/import_export/routers/export.py:99-101 — Folge der Breakout-Regel, Exporte waren nicht Teil von A3.
- Die Geräte-Detailansicht in /racks listet Kabel nur über von_device_id/nach_device_id; ein Breakout-Kabel erscheint dort nur am A-Gerät, nicht an den Geräten der B-Enden — frontend/src/routes/(app)/racks/+page.svelte:1873-1874 — Beim Einbau der B-Enden-Zeilen in den Kabel-Dialog aufgefallen.

## 2026-11-17 · Umbau B2 · Claude Fable 5.2
- Die Test-Session hängt an einer äußeren Transaktion; ein rollback() im Service rollt dort die gesamte Testvorbereitung zurück — tests/conftest.py:36-42 — Aufgefallen beim rowcount-0-Pfad, der deshalb ohne rollback auskommt; die vorhandene SAWarning "transaction already deassociated" in den Import- und Power-Tests stammt aus demselben Verhalten.
- Kabel, die der CSV- oder EPLAN-Import ohne kabeltyp_id anlegt, sperren im Umbau das Einfrieren mit "Kabeltyp fehlt" — app/domains/import_export/routers/import_csv.py:469-471, app/domains/import_export/routers/import_eplan.py:308 — Folge des A2-Befunds, beim Bau der Einfrier-Sperre sichtbar geworden.
- Die Abdeckung lässt sich in der vorhandenen venv nicht messen: pytest-cov ist nicht installiert, `pytest --cov` bricht mit "unrecognized arguments" ab — requirements.txt — Aufgefallen beim Prüfen, ob die Tests den rowcount-0-Zweig wirklich ausführen (ersatzweise mit dem Standardmodul trace geprüft).

## 2026-11-17 · Umbau B3 · Claude Fable 5.2
- Die Kabelliste kennt keinen Direktlink auf ein einzelnes Kabel (die Auswahl ist nur Seitenzustand); die Erfassung kann zum Ändern oder Löschen deshalb nur auf /cables verweisen — frontend/src/routes/(app)/cables/+page.svelte:28 — Aufgefallen beim Bau der Kabel-Enden je Gerät in der Erfassungsansicht.
- request() schreibt jede fehlgeschlagene Antwort als console.error, auch erwartbare fachliche 409 wie die Doppelbelegung eines Ports — frontend/src/lib/api.ts:532 — Im Browser-Test der Erfassung in der Konsole gesehen.

## 2026-11-17 · Umbau B4 · Claude Fable 5.2
- Das Frontend hat keinen Testlauf: in den Skripten stehen nur dev, build, preview und check, kein Test-Skript — frontend/package.json:6-13 — Aufgefallen, weil die Abläufe der Umbau-Oberfläche (Erfassung, Sammelbuchung, Korrigieren) nur mit einem Browser-Skript außerhalb des Repos geprüft werden konnten.

## 2026-11-27 · Umbau Korrekturen (Analyse 3, 4, 1, 7, 9) · Claude Opus 5.5
- Die globale Druckregel blendet jedes `header`-Element aus; der Kopf des Runbook-Laufzettels ist selbst ein `<header class="print-header">` und fällt damit laut CSS im Druck weg (nicht im Browser geprüft) — frontend/src/routes/layout.css:326, frontend/src/lib/components/RunbookPrint.svelte:70 — Aufgefallen beim Ausblenden von Seitenleiste und Kopfzeile für die Umbau-Druckliste.
- Der Wechsel Rückbau → Umbau zählt die gesteckten Enden und schreibt den Status in zwei getrennten Schritten; ein Nachtrag, der genau dazwischen gespeichert wird, bliebe als gestecktes Ende im Status „Umbau“ stehen — app/domains/umbau/services.py:520 — Beim Bau des Nachtrags gesehen; im Einzelplatzbetrieb praktisch nicht erreichbar.
- Backend und Oberfläche vergleichen Ports unterschiedlich: Python casefold() macht aus „ß“ „ss“, JavaScript toLocaleLowerCase() nicht — app/domains/umbau/regeln.py:330, frontend/src/lib/umbauApi.ts:158 — Beim Angleichen des Port-Vergleichs aufgefallen.

# Serverraum-Umbau

KAiTix begleitet einen Umbau im Serverraum: Kabel erfassen, Soll-Stand einfrieren, an
beiden Enden abklemmen, nach dem Umbau nach Soll wieder anklemmen. Jede Buchung wird
protokolliert.

Die Kabelliste ist die vorhandene Tabelle `cables`. Der Umbau führt keine zweite
Kabelliste. Er dokumentiert und rechnet auf dokumentierten Daten; er liest keine Geräte
aus und schaltet nichts.

## Ablauf

| Phase | Status | Was passiert | Wer schreibt wohin |
|---|---|---|---|
| 1 | `erfassung` | Je Gerät in den gewählten Racks die Kabel erfassen und das Gerät als vollständig erfasst bestätigen | Kabel über `/cables` in `cables` und `cable_strands`; Bestätigungen in `umbau_geraetepruefungen` |
| 2 | `rueckbau` | Einfrieren legt je Stecker-Ende eine Zeile an. Jedes Ende wird abgeklemmt | nur `umbau_enden`, `umbau_ereignisse` |
| 3 | `umbau` | Der eigentliche Umbau. Es wird nichts gebucht | nur der Status |
| 4 | `wiederaufbau` | Jedes Ende wird an seinem Soll-Port angeklemmt, ein anderer Port nur mit Grund | nur `umbau_enden`, `umbau_ereignisse` |
| 5 | `abgeschlossen` | Nachweis steht, keine Buchung mehr | — |

Ein Umbau lässt sich aus jedem Status außer `abgeschlossen` verwerfen (`verworfen`).

In der Oberfläche: Menü „Betrieb → Umbau“ (`/umbau`, `/umbau/[id]`). Kabeltypen pflegt man
unter „Infrastruktur → Kabeltypen“ (`/kabeltypen`).

## Grundregeln des Datenmodells

- **Port-Wahrheit:** `cables.von_device_id` + `von_port` und `cables.nach_device_id` +
  `nach_port`, jeweils als Text. Interfaces bleiben optional; es gibt keinen Abgleich
  zwischen Interfaces und Kabeln.
- **Der Kabeltyp bestimmt die Enden:** `kabeltypen.enden_a` und `enden_b`. `cables.typ`
  bleibt bestehen und wird beim Speichern aus `kabeltypen.alt_typ` gesetzt, weil Exporte,
  Farbregeln und Simulation ihn weiter lesen.
- **Breakouts:** Bei `enden_b = 1` steht das B-Ende am Kabel. Bei `enden_b > 1` bleiben
  `nach_device_id`/`nach_port` am Kabel leer; die B-Enden sind genau `enden_b` Zeilen in
  `cable_strands` (`strand_number` 1..n, je `nach_device_id` + `nach_port`).
- **Stromkabel** (Kategorie `strom`) gehören nicht zum Umbau.
- **Patchpanels** sind normale Geräte: Server → Panel und Panel → Switch sind zwei Kabel.

## Einspielen

Der Umbau bringt drei Migrationen mit, in dieser Reihenfolge:

| Revision | Inhalt |
|---|---|
| `52e1b97080a3` | Tabelle `kabeltypen` mit 17 Katalogzeilen, `cables.kabeltyp_id` |
| `27f768e65156` | `cable_strands.nach_device_id` und `nach_port` (B-Enden der Breakouts) |
| `a6f7bab2f1b2` | Tabellen des Umbaus |

Container: Die Migrationen laufen beim Start automatisch. Manuelle Installation: Datenbank
sichern, dann `alembic upgrade head`. Die Schritte stehen in der README unter
„Update einer bestehenden Installation".

Vorhandene Kabel bekommen den Katalogtyp, dessen Name gleich ihrem bisherigen `typ` ist.
Kabel ohne passenden Katalogeintrag bleiben ohne Kabeltyp. Sie lassen sich weiter
bearbeiten, sperren aber das Einfrieren eines Umbaus, bis der Typ gesetzt ist.

## Tabellen des Umbaus

Modelle in `app/domains/umbau/models.py`, Migration `a6f7bab2f1b2`.

| Tabelle | Inhalt |
|---|---|
| `umbauten` | Name, Beschreibung, Status, wer wann angelegt, eingefroren und abgeschlossen hat |
| `umbau_racks` | Umfang: die gewählten Racks |
| `umbau_geraetepruefungen` | „Gerät vollständig erfasst“ je Gerät, mit Gerätename als Textkopie; eindeutig je Umbau und Gerät |
| `umbau_enden` | Eine Zeile je physischem Stecker-Ende. Entsteht nur beim Einfrieren |
| `umbau_ereignisse` | Protokoll. Wird nur angehängt |

`umbau_enden` hält das Soll als **Textkopie** fest: `soll_device_name`, `soll_rack_name`,
`soll_port`, `kabel_nr`, `kabeltyp_name`, `kategorie`, `farbe`. Die Verweise `cable_id` und
`soll_device_id` stehen auf `ON DELETE SET NULL`. Wird nach dem Einfrieren ein Kabel
geändert oder ein Gerät gelöscht, bleibt das Soll unverändert lesbar.

Ein Ende ist eindeutig über `(umbau_id, cable_id, seite, ende_nr)`. Seite A hat immer
`ende_nr = 1`. Seite B hat `ende_nr = 1` oder bei Breakouts die Strangnummer.

## Regeln

Alle fachlichen Regeln stehen als reine Funktionen ohne Datenbankzugriff in
`app/domains/umbau/regeln.py`. Service und Oberfläche fragen dieselben Funktionen.

### Umfang und Einfrieren

- **Umfang:** alle Nicht-Strom-Kabel mit mindestens einem Ende an einem Gerät in den
  gewählten Racks. Liegt das andere Ende außerhalb, gehört das Kabel trotzdem dazu und
  beide Enden werden abgeklemmt.
- **Enden je Kabel:** Seite A ein Ende an `von_*`. Seite B ein Ende an `nach_*` oder je
  Strang ein Ende. Ein Breakout QSFP+→4×SFP+ hat fünf Enden.
- **Einfrieren ist gesperrt**, solange
  - ein Kabel im Umfang unvollständig ist (Kabeltyp, A-Ende, Gegenstelle oder B-Enden
    fehlen) oder
  - ein Gerät in den gewählten Racks nicht bestätigt ist.

  Die Sperre nennt jedes betroffene Kabel und Gerät. Die Liste steht in
  `GET /umbau/{id}` unter `einfrier_sperren`.

### Übergänge eines Endes

| Aktion | Nur im Status | Von | Nach |
|---|---|---|---|
| Abklemmen | `rueckbau` | `gesteckt` | `abgeklemmt` |
| Abklemmen zurücknehmen | `rueckbau` | `abgeklemmt` | `gesteckt` |
| Anklemmen nach Soll | `wiederaufbau` | `abgeklemmt` | `angeklemmt` |
| Anklemmen an anderem Port (mit Grund) | `wiederaufbau` | `abgeklemmt` | `angeklemmt_abweichend` |
| Anklemmen zurücknehmen | `wiederaufbau` | `angeklemmt`, `angeklemmt_abweichend` | `abgeklemmt` |

Eine Rücknahme geht genau eine Stufe zurück. Ein anderer Port als im Soll braucht einen
nicht-leeren Grund; das Soll selbst ändert sich dadurch nicht, der Ist-Port steht in
`ist_device_name`, `ist_port` und `abweichung_grund`.

### Übergänge des Umbaus

| Von | Nach | Bedingung |
|---|---|---|
| `erfassung` | `rueckbau` | Einfrieren ist nicht gesperrt |
| `rueckbau` | `umbau` | alle Enden sind abgeklemmt |
| `umbau` | `wiederaufbau` | jederzeit |
| `wiederaufbau` | `abgeschlossen` | kein Ende ist mehr gesteckt oder abgeklemmt |
| jeder außer `abgeschlossen` | `verworfen` | jederzeit |

### Sperrgrund

`sperrgrund(ende_status, umbau_status)` liefert einen Satz oder nichts. Es ist die eine
Regel, nach der die Oberfläche einen Knopf zeigt und der Server eine Buchung annimmt.
`GET /umbau/{id}` liefert den Sperrgrund je Ende und je möglichem Statuswechsel
(`naechste_status`).

## API

Unter `/api/v1/umbau`, Benutzername aus dem Header `X-Username`.

| Aufruf | Zweck |
|---|---|
| `POST /umbau` | Umbau mit Namen und Racks anlegen |
| `GET /umbau` | Liste mit Status und Fortschritt |
| `GET /umbau/{id}` | Erfassungsfortschritt je Gerät, Sperrliste, Enden, Fortschritt je Rack und Gerät, Protokoll |
| `POST /umbau/{id}/geraete/{device_id}/bestaetigen?bestaetigt=true\|false` | „Gerät vollständig erfasst“, nur in der Erfassung |
| `POST /umbau/{id}/einfrieren` | Soll-Stand einfrieren |
| `POST /umbau/{id}/status` mit `{ziel}` | Statuswechsel |
| `PUT /umbau/{id}/enden/{ende_id}/abklemmen?abgeklemmt=true\|false` | Abklemmen oder zurücknehmen |
| `PUT /umbau/{id}/enden/{ende_id}/anklemmen` mit `{angeklemmt, ist_device_id?, ist_port?, grund?}` | Anklemmen oder zurücknehmen |

Kabel werden in der Erfassung über die vorhandenen `/cables`-Endpunkte angelegt und
geändert. Es gibt keinen eigenen Schreibweg und keinen Sammel-Endpunkt; die
Sammelbuchung der Oberfläche ruft den Einzelendpunkt nacheinander auf.

### Gleichzeitigkeit

Die Datenbank ist SQLite, Zeilensperren gibt es nicht. Jede Buchung ist ein bedingtes
`UPDATE … WHERE id = :id AND status = :erwartet`:

- Trifft es eine Zeile, entsteht in derselben Transaktion ein Eintrag in
  `umbau_ereignisse`.
- Trifft es keine Zeile, wird neu gelesen. Ist das Ziel schon erreicht, lautet die Antwort
  200 ohne Änderung und ohne Ereignis. Sonst 409 mit Sperrgrund.

Das gilt für Enden und für den Status des Umbaus. Wiederholte Aufrufe sind dadurch
gefahrlos.

## Bewusste Grenzen der Version 1

- **Kein Strom.** Stromkabel werden nicht zu Enden und sperren das Einfrieren nicht.
- **Kein Rückschreiben des Ist-Stands.** Ab dem Einfrieren schreibt der Umbau nicht in
  `cables`, `cable_strands` oder `interfaces`. Ein abweichend angeklemmtes Ende steht nur
  im Umbau; die Kabelliste muss von Hand nachgezogen werden.
- **Kein Offline-Betrieb.** Die Oberfläche braucht die Verbindung zum Backend.
- **Keine Etiketten, kein QR-Code.**
- **Breakouts nicht in Topologie und Trace.** Topologie, Kabelverfolgung, Simulation und
  Exporte kennen die Strang-Enden nicht.
- **Kein Abgleich mit Interfaces.** Port-Vorschläge kommen aus den Interfaces, belegt
  wird aber allein über die Port-Texte am Kabel.
- **Importe kennen nur die Standardtypen.** CSV- und EPLAN-Import ordnen den Kabeltyp
  über den Namen zu (Katalogzeile mit dem Namen des `typ`, Regel in
  `kabeltyp_service.kabeltyp_id_nach_typ`). Breakouts und eigene Katalogtypen lassen sich
  nicht importieren; ohne passende Katalogzeile bleibt das Kabel ohne Kabeltyp und sperrt
  das Einfrieren, bis der Typ in der Kabelliste gesetzt ist. Beim erneuten Import bleibt
  ein gesetzter Kabeltyp, solange sich `typ` nicht ändert.
- **Bestätigung gilt für alle Geräte der gewählten Racks**, auch für solche ohne
  Datenkabel.

Weitere Beobachtungen aus dem Bau stehen in `docs/agent-befunde.md`.

## Tests

- `tests/test_umbau.py`: Regeln ohne Datenbank und die API einschließlich der
  rowcount-0-Pfade und der Schreibsperre nach dem Einfrieren.
- `tests/test_breakout.py`: Breakout-Stränge im Kabel-Schreibweg.
- `tests/test_kabeltypen.py`: Kabeltyp-Katalog.
- `tests/test_cabling_write.py`: Ports im Schreibweg, Belegungsprüfung, Kabelnummern.

Aufruf im Worktree:

```bash
/home/andreas/Projekte/aktiv/KAiTix/.venv/bin/python -m pytest -v
```

Für die Oberfläche gibt es keinen automatischen Test im Repository.

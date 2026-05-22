# Security Policy

## Responsible Disclosure

Wir nehmen Sicherheit ernst. Wenn du eine Schwachstelle entdeckst, melde sie uns verantwortungsvoll, damit wir sie beheben können, bevor sie öffentlich wird.

## Kontakt

- **E-Mail:** security@diebugger.tech
- **PGP Key:** (optional) Fingerprint hier einfügen
- **Antwortzeit:** Innerhalb von 48 Stunden (Werktage)

## Scope (In-Scope)

Folgende Bereiche und Schwachstellenklassen sind explizit in-scope:

- API-Endpunkte (`/api/*`)
- Authentifizierungs- und Autorisierungsmechanismen
- SQL-Injection, XSS, CSRF in der Anwendung
- Fehlende Rate-Limiting oder Input-Validierung
- Exposition von sensitiven Daten (PII, Credentials)
- Konfigurationsfehler (z.B. offene .env-Dateien, CORS-Misconfiguration)

## Out-of-Scope

Folgende Bereiche sind **nicht** in-scope:

- Social Engineering oder Phishing gegen Mitarbeiter
- Denial-of-Service (DoS) ohne vorherige Absprache
- Schwachstellen in Drittanbieter-Dependencies (melde diese direkt beim Hersteller)
- Schwachstellen in Infrastruktur, die nicht unter unserer direkten Kontrolle steht

## Response-Zeitversprechen

| Phase | Zeitraum |
|---|---|
| Bestätigung der Meldung | 48 Stunden |
| Erste Bewertung | 5 Werktage |
| Fix oder Workaround | 90 Tage (kritisch: 14 Tage) |
| Öffentliche Offenlegung | Nach Absprache mit Reporter |

## Anerkennung

Wir danken allen Sicherheitsforschern, die verantwortungsvoll melden. Nach Absprache und nach Veröffentlichung eines Fixes können Reporter in unserer Hall of Fame erwähnt werden.

---

**Hinweis:** Dies ist ein Open-Source-Projekt unter der AGPL-3.0 Lizenz. Wir begrüßen verantwortungsvolle Sicherheitsmeldungen und bitten darum, Schwachstellen vor der Veröffentlichung vertraulich an uns zu melden.

/**
 * Fehlerantworten der API in eine lesbare Meldung übersetzen.
 *
 * Reine Funktionen ohne Seiteneffekte; request() in api.ts nutzt sie.
 */

/** Ab diesem Status gilt das Backend als gestört (auch Proxy-Fehler, wenn es nicht läuft). */
const STOERUNG_AB_STATUS = 500;

/**
 * Hat das Backend geantwortet, aber fachlich abgelehnt (4xx), ist es erreichbar.
 * Nur 5xx zählt als Störung; Netzwerkfehler erkennt request() selbst.
 */
export function istBackendStoerung(status: number): boolean {
  return status >= STOERUNG_AB_STATUS;
}

type Konflikte = {
  db_duplicates?: string[];
  csv_duplicates?: string[];
  rack_collisions?: string[];
};

type Validierungsfehler = { loc?: unknown[]; msg?: string };

function konfliktText(message: string, c: Konflikte): string {
  const teile: string[] = [];
  if (c.db_duplicates?.length) teile.push(`DB-Duplikate: ${c.db_duplicates.join('; ')}`);
  if (c.csv_duplicates?.length) teile.push(`CSV-Duplikate: ${c.csv_duplicates.join('; ')}`);
  if (c.rack_collisions?.length) teile.push(`Rack-Kollisionen: ${c.rack_collisions.join('; ')}`);
  return teile.length ? `${message} - ${teile.join(' | ')}` : message;
}

/** Pydantic-422: Liste von {loc, msg}. "body" am Anfang von loc ist für Nutzer ohne Wert. */
function validierungsText(fehler: Validierungsfehler[]): string {
  return fehler
    .map(f => {
      const feld = (f.loc ?? []).filter(teil => teil !== 'body').join('.');
      const msg = f.msg ?? 'ungültig';
      return feld ? `${feld}: ${msg}` : msg;
    })
    .join('\n');
}

/** detail aus der FastAPI-Antwort als Text; fallback, wenn nichts Brauchbares drinsteht. */
export function fehlerMeldung(detail: unknown, fallback: string): string {
  if (typeof detail === 'string') return detail || fallback;
  if (Array.isArray(detail)) {
    return detail.length ? validierungsText(detail as Validierungsfehler[]) : fallback;
  }
  if (detail && typeof detail === 'object') {
    const d = detail as { message?: unknown; conflicts?: Konflikte };
    if (typeof d.message === 'string') {
      return d.conflicts ? konfliktText(d.message, d.conflicts) : d.message;
    }
    return JSON.stringify(detail);
  }
  return fallback;
}

/** Fehlerantwort (Rohtext) in eine Meldung übersetzen; kein JSON → Rohtext oder Statustext. */
export function meldungAusAntwort(text: string, statusText: string): string {
  const fallback = text || statusText;
  try {
    const parsed = JSON.parse(text);
    return parsed && typeof parsed === 'object' && 'detail' in parsed
      ? fehlerMeldung(parsed.detail, fallback)
      : fallback;
  } catch {
    return fallback;
  }
}

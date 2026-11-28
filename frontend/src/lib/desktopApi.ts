// Desktop-App (/api/v1/desktop): Version und „Nach Updates suchen“.
// Außerhalb der Desktop-App antwortet das Backend 404; dann zeigt die Oberfläche nichts.
import { request } from '$lib/api';

export interface DesktopInfo {
  desktop: boolean;
  branch: string | null;
  commit: string | null;
  datum: string | null;
}

export interface UpdateStand {
  branch: string | null;
  upstream: string | null;
  lokal: string;
  remote: string | null;
  hinter: number;
  vor: number;
  lokale_aenderungen: boolean;
  /** Neue Commits als "kurzhash Betreff", neueste zuerst. */
  neu: string[];
  /** Warum „Aktualisieren“ nicht geht; null = möglich. */
  sperrgrund: string | null;
}

export interface UpdateErgebnis {
  log: string[];
  neustart: boolean;
}

// Pflicht-Header der Update-Aktionen (Schutz vor fremden Webseiten).
const UPDATE = { 'X-KAiTix-Update': '1' };

export const desktopApi = {
  info: (): Promise<DesktopInfo> => request('desktop/info'),
  pruefen: (): Promise<UpdateStand> => request('desktop/update/pruefen', { method: 'POST', headers: UPDATE }),
  ausfuehren: (): Promise<UpdateErgebnis> => request('desktop/update/ausfuehren', { method: 'POST', headers: UPDATE })
};

/** Desktop-Info ohne Fehlermeldung: null außerhalb der Desktop-App. */
export async function desktopInfo(): Promise<DesktopInfo | null> {
  try {
    const antwort = await fetch('/api/v1/desktop/info');
    return antwort.ok ? ((await antwort.json()) as DesktopInfo) : null;
  } catch {
    return null;
  }
}

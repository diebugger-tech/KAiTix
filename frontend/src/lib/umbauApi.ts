// API des Serverraum-Umbaus (/api/v1/umbau). Typen entsprechen app/domains/umbau/schemas.py.
import { request } from '$lib/api';

export type UmbauStatus = 'erfassung' | 'rueckbau' | 'umbau' | 'wiederaufbau' | 'abgeschlossen' | 'verworfen';
export type EndeStatus = 'gesteckt' | 'abgeklemmt' | 'angeklemmt' | 'angeklemmt_abweichend';

/** Zählung der Enden. angeklemmt enthält auch die abweichend angeklemmten. */
export interface UmbauFortschritt {
  enden_gesamt: number;
  gesteckt: number;
  abgeklemmt: number;
  angeklemmt: number;
  abweichend: number;
}

export interface UmbauRack {
  id: number;
  name: string;
}

export interface UmbauListe {
  id: number;
  name: string;
  beschreibung?: string | null;
  status: UmbauStatus;
  erstellt_am: string;
  erstellt_von?: string | null;
  eingefroren_am?: string | null;
  abgeschlossen_am?: string | null;
  racks: UmbauRack[];
  geraete_gesamt: number;
  geraete_bestaetigt: number;
  fortschritt: UmbauFortschritt;
}

/** Erfassungsfortschritt eines Geräts im Umfang. */
export interface UmbauGeraet {
  device_id: number;
  hostname: string;
  typ: string;
  rack_id?: number | null;
  rack_name?: string | null;
  kabel_gesamt: number;
  kabel_unvollstaendig: number;
  bestaetigt: boolean;
  bestaetigt_am?: string | null;
  bestaetigt_von?: string | null;
}

/** Ein physisches Stecker-Ende mit eingefrorenem Soll. */
export interface UmbauEnde {
  id: number;
  cable_id?: number | null;
  strand_number?: number | null;
  seite: 'A' | 'B';
  ende_nr: number;
  soll_device_id?: number | null;
  soll_device_name: string;
  soll_rack_name?: string | null;
  soll_port: string;
  kabel_nr?: string | null;
  kabeltyp_name: string;
  kategorie: string;
  farbe?: string | null;
  status: EndeStatus;
  abgeklemmt_am?: string | null;
  abgeklemmt_von?: string | null;
  angeklemmt_am?: string | null;
  angeklemmt_von?: string | null;
  ist_device_id?: number | null;
  ist_device_name?: string | null;
  ist_port?: string | null;
  abweichung_grund?: string | null;
  /** Gegenseite(n) als "Gerät:Port". Nur in GET /umbau/{id} gefüllt. */
  gegenseite: string[];
  /** Warum an diesem Ende gerade nichts gebucht werden kann; null = buchbar. */
  sperrgrund?: string | null;
}

export interface UmbauGeraetFortschritt {
  device_name: string;
  fortschritt: UmbauFortschritt;
}

export interface UmbauRackFortschritt {
  rack_name: string;
  fortschritt: UmbauFortschritt;
  geraete: UmbauGeraetFortschritt[];
}

export interface UmbauStatusZiel {
  ziel: UmbauStatus;
  /** null = Wechsel jetzt möglich. */
  sperrgrund?: string | null;
}

export interface UmbauEreignis {
  id: number;
  ende_id?: number | null;
  von_status?: string | null;
  nach_status: string;
  grund?: string | null;
  benutzer?: string | null;
  zeitpunkt: string;
}

export interface UmbauDetail {
  id: number;
  name: string;
  beschreibung?: string | null;
  status: UmbauStatus;
  erstellt_am: string;
  erstellt_von?: string | null;
  eingefroren_am?: string | null;
  eingefroren_von?: string | null;
  abgeschlossen_am?: string | null;
  abgeschlossen_von?: string | null;
  racks: UmbauRack[];
  geraete: UmbauGeraet[];
  einfrier_sperren: string[];
  enden: UmbauEnde[];
  fortschritt: UmbauFortschritt;
  fortschritt_racks: UmbauRackFortschritt[];
  naechste_status: UmbauStatusZiel[];
  ereignisse: UmbauEreignis[];
}

export interface AnklemmenEingabe {
  angeklemmt: boolean;
  ist_device_id?: number | null;
  ist_port?: string | null;
  grund?: string | null;
}

export const STATUS_LABEL: Record<UmbauStatus, string> = {
  erfassung: 'Erfassung',
  rueckbau: 'Rückbau',
  umbau: 'Umbau',
  wiederaufbau: 'Wiederaufbau',
  abgeschlossen: 'Abgeschlossen',
  verworfen: 'Verworfen'
};

export const ENDE_STATUS_LABEL: Record<EndeStatus, string> = {
  gesteckt: 'gesteckt',
  abgeklemmt: 'abgeklemmt',
  angeklemmt: 'angeklemmt',
  angeklemmt_abweichend: 'abweichend angeklemmt'
};

/** Zeitstempel der API sind naive UTC. */
export function zeit(wert?: string | null): string {
  if (!wert) return '—';
  const datum = new Date(/[zZ]|[+-]\d\d:\d\d$/.test(wert) ? wert : `${wert}Z`);
  return datum.toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' });
}

export const umbauApi = {
  list: (): Promise<UmbauListe[]> => request('umbau/'),
  get: (id: number): Promise<UmbauDetail> => request(`umbau/${id}`),
  create: (umbau: { name: string; beschreibung?: string; rack_ids: number[] }): Promise<UmbauDetail> =>
    request('umbau/', { method: 'POST', body: JSON.stringify(umbau) }),
  bestaetigeGeraet: (umbauId: number, deviceId: number, bestaetigt: boolean): Promise<UmbauGeraet> =>
    request(`umbau/${umbauId}/geraete/${deviceId}/bestaetigen?bestaetigt=${bestaetigt}`, { method: 'POST' }),
  einfrieren: (id: number): Promise<UmbauDetail> => request(`umbau/${id}/einfrieren`, { method: 'POST' }),
  status: (id: number, ziel: UmbauStatus): Promise<UmbauDetail> =>
    request(`umbau/${id}/status`, { method: 'POST', body: JSON.stringify({ ziel }) }),
  abklemmen: (umbauId: number, endeId: number, abgeklemmt: boolean): Promise<UmbauEnde> =>
    request(`umbau/${umbauId}/enden/${endeId}/abklemmen?abgeklemmt=${abgeklemmt}`, { method: 'PUT' }),
  anklemmen: (umbauId: number, endeId: number, eingabe: AnklemmenEingabe): Promise<UmbauEnde> =>
    request(`umbau/${umbauId}/enden/${endeId}/anklemmen`, { method: 'PUT', body: JSON.stringify(eingabe) })
};

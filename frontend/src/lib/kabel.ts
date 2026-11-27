import type { Cable, StrangEingabe } from '$lib/api';

/** Ein B-Ende eines Breakout-Kabels im Formular. */
export interface BEnde {
  nach_device_id: number | null;
  nach_port: string;
}

/**
 * Formularzeilen für die B-Enden eines Kabeltyps mit enden_b > 1.
 * Übernimmt vorhandene Stränge des Kabels bzw. schon ausgefüllte Zeilen (nach Position).
 */
export function bEndenFuerTyp(endenB: number, cable?: Cable | null, bisher: BEnde[] = []): BEnde[] {
  if (endenB <= 1) return [];
  const straenge = new Map((cable?.cable_strands ?? []).map(s => [s.strand_number, s]));
  return Array.from({ length: endenB }, (_, index) => {
    const strang = straenge.get(index + 1);
    if (strang) {
      return { nach_device_id: strang.nach_device_id ?? null, nach_port: strang.nach_port ?? '' };
    }
    return bisher[index] ? { ...bisher[index] } : { nach_device_id: null, nach_port: '' };
  });
}

/** Formularzeilen → Feld straenge für POST/PUT /cables. */
export function straengeAusEnden(enden: BEnde[]): StrangEingabe[] {
  return enden.map((ende, index) => ({
    strand_number: index + 1,
    nach_device_id: ende.nach_device_id,
    nach_port: ende.nach_port.trim() || null
  }));
}

/** Stromkabel gehören nicht zum Umbau: Kategorie des Kabeltyps, sonst der bisherige typ. */
export function istStromKabel(cable: Cable): boolean {
  if (cable.kabeltyp) return cable.kabeltyp.kategorie === 'strom';
  return cable.typ.startsWith('Strom');
}

export interface Gegenstelle {
  device_id: number | null;
  port: string | null;
}

/** Ein Kabel-Ende aus Sicht eines Geräts: der eigene Port und wohin das Kabel führt. */
export interface KabelEnde {
  cable: Cable;
  /** Eindeutig je Ende, auch wenn ein Kabel mit zwei Enden am selben Gerät steckt. */
  schluessel: string;
  eigenerPort: string | null;
  gegenstellen: Gegenstelle[];
  /** Hinweis für die Anzeige. Verbindlich ist die Sperrliste der API. */
  unvollstaendig: boolean;
}

function fehlt(g: Gegenstelle): boolean {
  return !g.device_id || !g.port;
}

/** Alle Enden von Nicht-Strom-Kabeln, die an diesem Gerät stecken. */
export function endenAmGeraet(cables: Cable[], deviceId: number): KabelEnde[] {
  const enden: KabelEnde[] = [];
  for (const cable of cables) {
    if (istStromKabel(cable)) continue;
    const straenge = cable.cable_strands ?? [];
    const a: Gegenstelle = { device_id: cable.von_device_id ?? null, port: cable.von_port ?? null };
    const b: Gegenstelle[] = straenge.length
      ? straenge.map(s => ({ device_id: s.nach_device_id ?? null, port: s.nach_port ?? null }))
      : [{ device_id: cable.nach_device_id ?? null, port: cable.nach_port ?? null }];
    // Wie regeln.unvollstaendig im Backend: Nummer, Kabeltyp und alle Enden.
    const offen = !cable.kabel_nr?.trim() || !cable.kabeltyp || fehlt(a) || b.some(fehlt);
    if (a.device_id === deviceId) {
      enden.push({ cable, schluessel: `${cable.id}-A`, eigenerPort: a.port, gegenstellen: b, unvollstaendig: offen });
    }
    b.forEach((ende, index) => {
      if (ende.device_id === deviceId) {
        enden.push({
          cable,
          schluessel: `${cable.id}-B${index + 1}`,
          eigenerPort: ende.port,
          gegenstellen: [a],
          unvollstaendig: offen
        });
      }
    });
  }
  return enden.sort((x, y) => (x.eigenerPort ?? '').localeCompare(y.eigenerPort ?? '', 'de', { numeric: true }));
}

/** Port-Strings, die an einem Gerät schon von irgendeinem Kabel genutzt werden. */
export function genutztePorts(cables: Cable[], deviceId: number): Set<string> {
  const ports = new Set<string>();
  for (const cable of cables) {
    if (cable.von_device_id === deviceId && cable.von_port) ports.add(cable.von_port);
    if (cable.nach_device_id === deviceId && cable.nach_port) ports.add(cable.nach_port);
    for (const strang of cable.cable_strands ?? []) {
      if (strang.nach_device_id === deviceId && strang.nach_port) ports.add(strang.nach_port);
    }
  }
  return ports;
}

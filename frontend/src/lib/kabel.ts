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

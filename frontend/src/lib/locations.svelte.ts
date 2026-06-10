import { browser } from '$app/environment';
import type { Rack } from '$lib/api';

export type LocationType = 'rechenzentrum' | 'dienstaußenstelle';

export interface Location {
  name: string;
  typ: LocationType;
  reihen: string[];
}

const STORAGE_KEY = 'kaitix_locations';

function migrate(): Location[] {
  const r1 = browser ? localStorage.getItem('kaitix_room1_name') : null;
  const r2 = browser ? localStorage.getItem('kaitix_room2_name') : null;
  return [
    { name: r1 ?? 'Serverraum 1', typ: 'rechenzentrum', reihen: [] },
    { name: r2 ?? 'Serverraum 2', typ: 'rechenzentrum', reihen: [] },
  ];
}

class LocationStore {
  locations = $state<Location[]>([]);

  constructor() {
    if (!browser) { this.locations = migrate(); return; }
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      try {
        const parsed = JSON.parse(raw);
        this.locations = parsed.map((l: any) => ({ ...l, reihen: l.reihen || [] }));
        return;
      } catch { /* fall through */ }
    }
    this.locations = migrate();
    this._save();
  }

  private _save() {
    if (browser) localStorage.setItem(STORAGE_KEY, JSON.stringify(this.locations));
  }

  add(name: string, typ: LocationType) {
    const trimmed = name.trim();
    if (!trimmed || trimmed.toLowerCase() === 'alle' || trimmed === '__ALL__' || this.locations.some(l => l.name === trimmed)) return;
    this.locations = [...this.locations, { name: trimmed, typ, reihen: [] }];
    this._save();
  }

  remove(name: string) {
    this.locations = this.locations.filter(l => l.name !== name);
    this._save();
  }

  update(name: string, newName: string, typ: LocationType) {
    const trimmed = newName.trim();
    if (!trimmed || trimmed.toLowerCase() === 'alle' || trimmed === '__ALL__') return;
    this.locations = this.locations.map(l =>
      l.name === name ? { ...l, name: trimmed, typ } : l
    );
    this._save();
  }

  addReihe(standort: string, reihe: string) {
    const trimmed = reihe.trim();
    if (!trimmed || trimmed.toLowerCase() === 'alle' || trimmed === '__ALL__') return;
    this.locations = this.locations.map(l => {
      if (l.name === standort) {
        const existing = l.reihen || [];
        if (!existing.includes(trimmed)) {
          return { ...l, reihen: [...existing, trimmed].sort() };
        }
      }
      return l;
    });
    this._save();
  }

  removeReihe(standort: string, reihe: string) {
    this.locations = this.locations.map(l => {
      if (l.name === standort) {
        return { ...l, reihen: (l.reihen || []).filter(r => r !== reihe) };
      }
      return l;
    });
    this._save();
  }

  renameReihe(standort: string, alteReihe: string, neueReihe: string) {
    const trimmed = neueReihe.trim();
    if (!trimmed || trimmed.toLowerCase() === 'alle' || trimmed === '__ALL__') return;
    this.locations = this.locations.map(l => {
      if (l.name === standort) {
        let arr = (l.reihen || []).filter(r => r !== alteReihe);
        if (!arr.includes(trimmed)) arr.push(trimmed);
        return { ...l, reihen: arr.sort() };
      }
      return l;
    });
    this._save();
  }

  syncFromRacks(racks: Rack[]) {
    let changed = false;
    const discovered = new Map<string, Set<string>>();

    for (const r of racks) {
      if (!r.standort || r.standort.toLowerCase() === 'alle') continue;
      if (!discovered.has(r.standort)) {
        discovered.set(r.standort, new Set());
      }
      if (r.rackreihe && r.rackreihe.toLowerCase() !== 'alle') {
        discovered.get(r.standort)!.add(r.rackreihe);
      }
    }

    this.locations = this.locations.map(l => {
      const disc = discovered.get(l.name);
      if (!disc) return l;
      
      const current = new Set(l.reihen || []);
      let locChanged = false;
      for (const reihe of disc) {
        if (!current.has(reihe)) {
          current.add(reihe);
          locChanged = true;
          changed = true;
        }
      }
      
      if (locChanged) {
        return { ...l, reihen: Array.from(current).sort() };
      }
      return l;
    });

    if (changed) this._save();
  }

  getTyp(name: string): LocationType {
    return this.locations.find(l => l.name === name)?.typ ?? 'rechenzentrum';
  }
}

export const locationStore = new LocationStore();

import { browser } from '$app/environment';

export type LocationType = 'rechenzentrum' | 'dienstaußenstelle';

export interface Location {
  name: string;
  typ: LocationType;
}

const STORAGE_KEY = 'kaitix_locations';

function migrate(): Location[] {
  const r1 = browser ? localStorage.getItem('kaitix_room1_name') : null;
  const r2 = browser ? localStorage.getItem('kaitix_room2_name') : null;
  return [
    { name: r1 ?? 'Serverraum 1', typ: 'rechenzentrum' },
    { name: r2 ?? 'Serverraum 2', typ: 'rechenzentrum' },
  ];
}

class LocationStore {
  locations = $state<Location[]>([]);

  constructor() {
    if (!browser) { this.locations = migrate(); return; }
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      try { this.locations = JSON.parse(raw); return; } catch { /* fall through */ }
    }
    this.locations = migrate();
    this._save();
  }

  private _save() {
    if (browser) localStorage.setItem(STORAGE_KEY, JSON.stringify(this.locations));
  }

  add(name: string, typ: LocationType) {
    const trimmed = name.trim();
    if (!trimmed || this.locations.some(l => l.name === trimmed)) return;
    this.locations = [...this.locations, { name: trimmed, typ }];
    this._save();
  }

  remove(name: string) {
    this.locations = this.locations.filter(l => l.name !== name);
    this._save();
  }

  update(name: string, newName: string, typ: LocationType) {
    this.locations = this.locations.map(l =>
      l.name === name ? { name: newName.trim() || name, typ } : l
    );
    this._save();
  }

  getTyp(name: string): LocationType {
    return this.locations.find(l => l.name === name)?.typ ?? 'rechenzentrum';
  }
}

export const locationStore = new LocationStore();

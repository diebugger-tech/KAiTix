import { browser } from '$app/environment';

class AppState {
  bearbeiter = $state('Andreas');
  backendOnline = $state(true);
  isSyncing = $state(false);

  constructor() {
    if (browser) {
      const stored = localStorage.getItem('kaitix_bearbeiter');
      if (stored) {
        this.bearbeiter = stored;
      }
    }
  }

  setBearbeiter(name: string) {
    this.bearbeiter = name;
    if (browser) {
      localStorage.setItem('kaitix_bearbeiter', name);
    }
  }

  setBackendStatus(online: boolean) {
    this.backendOnline = online;
  }

  setSyncing(syncing: boolean) {
    this.isSyncing = syncing;
  }
}

export const appState = new AppState();

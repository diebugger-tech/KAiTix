import { browser } from '$app/environment';

class AppState {
  bearbeiter = $state('Andreas');
  backendOnline = $state(true);
  isSyncing = $state(false);
  theme = $state('dark');

  constructor() {
    if (browser) {
      const stored = localStorage.getItem('kaitix_bearbeiter');
      if (stored) {
        this.bearbeiter = stored;
      }
      const storedTheme = localStorage.getItem('kaitix_theme');
      if (storedTheme) {
        this.theme = storedTheme;
        if (storedTheme === 'light') {
          document.documentElement.classList.remove('dark');
          document.documentElement.classList.add('light');
        }
      }
    }
  }

  setBearbeiter(name: string) {
    this.bearbeiter = name;
    if (browser) {
      localStorage.setItem('kaitix_bearbeiter', name);
    }
  }

  toggleTheme() {
    this.theme = this.theme === 'dark' ? 'light' : 'dark';
    if (browser) {
      localStorage.setItem('kaitix_theme', this.theme);
      if (this.theme === 'light') {
        document.documentElement.classList.remove('dark');
        document.documentElement.classList.add('light');
      } else {
        document.documentElement.classList.remove('light');
        document.documentElement.classList.add('dark');
      }
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

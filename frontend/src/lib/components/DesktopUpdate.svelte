<!--
  Desktop-App: Version und „Nach Updates suchen“ (Muster: GoTV). Nur sichtbar, wenn das
  Backend als Desktop-App läuft (GET /desktop/info). Geprüft wird nur auf Knopfdruck.
  Aktualisieren = git pull + Neubau im Backend; danach startet der Server neu und die
  Seite lädt neu, sobald er wieder antwortet.
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { desktopApi, desktopInfo, type DesktopInfo, type UpdateStand } from '$lib/desktopApi';
  import { Download, LoaderCircle, RefreshCw, X } from '@lucide/svelte';

  // Nach dem Update: so lange auf den neu startenden Server warten.
  const WARTEN_MS = 2000;
  const WARTEN_VERSUCHE = 60;

  let info = $state<DesktopInfo | null>(null);
  let offen = $state(false);
  let phase = $state<'pruefe' | 'stand' | 'aktualisiere' | 'neustart' | 'fehler'>('pruefe');
  let stand = $state<UpdateStand | null>(null);
  let fehler = $state('');

  onMount(async () => {
    info = await desktopInfo();
  });

  function meldung(err: unknown, standard: string): string {
    return err instanceof Error ? err.message : standard;
  }

  async function pruefen() {
    offen = true;
    phase = 'pruefe';
    fehler = '';
    try {
      stand = await desktopApi.pruefen();
      phase = 'stand';
    } catch (err) {
      fehler = meldung(err, 'Prüfen fehlgeschlagen.');
      phase = 'fehler';
    }
  }

  async function aktualisieren() {
    phase = 'aktualisiere';
    fehler = '';
    try {
      const ergebnis = await desktopApi.ausfuehren();
      if (!ergebnis.neustart) {
        fehler = 'Update eingespielt, aber kein Neustart möglich. KAiTix bitte von Hand neu starten.';
        phase = 'fehler';
        return;
      }
      phase = 'neustart';
      await aufNeustartWarten();
    } catch (err) {
      fehler = meldung(err, 'Aktualisieren fehlgeschlagen.');
      phase = 'fehler';
    }
  }

  /** Erst warten, bis der alte Server weg ist, dann bis der neue antwortet. Begrenzt. */
  async function aufNeustartWarten() {
    const alterCommit = info?.commit;
    for (let versuch = 0; versuch < WARTEN_VERSUCHE; versuch++) {
      await new Promise(fertig => setTimeout(fertig, WARTEN_MS));
      const neu = await desktopInfo();
      if (neu && neu.commit !== alterCommit) {
        location.reload();
        return;
      }
    }
    fehler = 'KAiTix antwortet nach dem Update nicht. Log: ~/.local/share/kaitix/server.log';
    phase = 'fehler';
  }

  const knopf =
    'flex items-center justify-center gap-2 px-4 min-h-11 rounded-lg text-sm font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed';
</script>

{#if info}
  <div class="bg-[var(--color-bg3)] border border-[var(--color-border)] rounded-lg p-3 text-xs space-y-2">
    <div class="flex items-center justify-between gap-2">
      <span class="text-[10px] text-[var(--color-text3)] uppercase tracking-wider font-mono">Desktop</span>
      <span class="font-mono text-[var(--color-text2)] truncate" title="Branch {info.branch} · {info.datum}">
        {info.commit ?? '—'}{info.datum ? ` · ${info.datum}` : ''}
      </span>
    </div>
    <button type="button" onclick={pruefen} class="w-full flex items-center justify-center gap-1.5 min-h-9 rounded-md text-[11px] font-semibold text-[#5DCAA5] border border-[#1D9E75]/40 hover:bg-[#1D9E75]/10 transition">
      <RefreshCw class="w-3.5 h-3.5" />
      Nach Updates suchen
    </button>
  </div>
{/if}

{#if offen}
  <div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
    <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl max-w-lg w-full shadow-2xl overflow-hidden">
      <div class="flex items-center gap-3 px-5 pt-5 pb-3">
        <h3 class="flex-1 text-lg font-bold font-outfit text-[var(--color-text)]">Updates</h3>
        {#if phase !== 'aktualisiere' && phase !== 'neustart'}
          <button type="button" onclick={() => (offen = false)} aria-label="Schließen" class="min-w-11 min-h-11 flex items-center justify-center rounded-lg text-[var(--color-text3)] hover:bg-[var(--color-border)]">
            <X class="w-5 h-5" />
          </button>
        {/if}
      </div>

      <div class="px-5 pb-5 space-y-4 text-sm text-[var(--color-text2)]">
        {#if phase === 'pruefe'}
          <p class="flex items-center gap-2"><LoaderCircle class="w-4 h-4 animate-spin" /> Frage das Repository nach neuen Änderungen…</p>
        {:else if phase === 'stand' && stand}
          <p>
            Installiert: <span class="font-mono text-[var(--color-text)]">{stand.lokal}</span> auf
            <span class="font-mono">{stand.branch ?? '—'}</span>{stand.upstream ? ` (Quelle ${stand.upstream})` : ''}.
          </p>
          {#if stand.hinter > 0}
            <div>
              <p class="font-semibold text-[var(--color-text)]">
                {stand.hinter} {stand.hinter === 1 ? 'neue Änderung' : 'neue Änderungen'}:
              </p>
              <ul class="mt-1 max-h-48 overflow-y-auto space-y-0.5 font-mono text-xs">
                {#each stand.neu as zeile (zeile)}<li>{zeile}</li>{/each}
              </ul>
            </div>
          {/if}
          {#if stand.sperrgrund}
            <p role="status" class={stand.hinter > 0 ? 'text-amber-400' : 'text-emerald-400'}>{stand.sperrgrund}</p>
          {/if}
          <div class="flex justify-end gap-2">
            <button type="button" onclick={() => (offen = false)} class="{knopf} text-[var(--color-text2)] hover:bg-[var(--color-border)]">Schließen</button>
            {#if stand.hinter > 0}
              <button type="button" onclick={aktualisieren} disabled={!!stand.sperrgrund} class="{knopf} bg-[#1D9E75] hover:bg-[#0F6E56] text-white">
                <Download class="w-4 h-4" /> Jetzt aktualisieren
              </button>
            {/if}
          </div>
        {:else if phase === 'aktualisiere'}
          <p class="flex items-center gap-2"><LoaderCircle class="w-4 h-4 animate-spin" /> Hole Änderungen und baue KAiTix neu. Das dauert 1–3 Minuten.</p>
          <p class="text-xs text-[var(--color-text3)]">Fenster offen lassen. Danach startet KAiTix neu; ausstehende Migrationen laufen mit vorheriger Sicherung der Datenbank.</p>
        {:else if phase === 'neustart'}
          <p class="flex items-center gap-2"><LoaderCircle class="w-4 h-4 animate-spin" /> Update installiert. KAiTix startet neu…</p>
        {:else if phase === 'fehler'}
          <p role="alert" class="text-red-400 whitespace-pre-line bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">{fehler}</p>
          <div class="flex justify-end gap-2">
            <button type="button" onclick={() => (offen = false)} class="{knopf} text-[var(--color-text2)] hover:bg-[var(--color-border)]">Schließen</button>
            <button type="button" onclick={pruefen} class="{knopf} border border-[var(--color-border2)] text-[var(--color-text)] hover:bg-[var(--color-border)]">Erneut prüfen</button>
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}

<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import { umbauApi, STATUS_LABEL, zeit, type UmbauDetail, type UmbauStatus } from '$lib/umbauApi';
  import ErfassungAnsicht from '$lib/components/umbau/ErfassungAnsicht.svelte';
  import EndenAnsicht from '$lib/components/umbau/EndenAnsicht.svelte';
  import Ereignisprotokoll from '$lib/components/umbau/Ereignisprotokoll.svelte';
  import UmbauDruck from '$lib/components/umbau/UmbauDruck.svelte';
  import { ArrowLeft, ArrowRight, Construction, Printer, X } from '@lucide/svelte';

  const umbauId = Number(page.params.id ?? '0');

  let umbau = $state<UmbauDetail | null>(null);
  let loading = $state(true);
  let errorMsg = $state('');

  async function load() {
    errorMsg = '';
    try {
      umbau = await umbauApi.get(umbauId);
    } catch (err) {
      errorMsg = err instanceof Error ? err.message : 'Umbau konnte nicht geladen werden.';
    } finally {
      loading = false;
    }
  }

  onMount(load);

  const PHASEN: UmbauStatus[] = ['erfassung', 'rueckbau', 'umbau', 'wiederaufbau', 'abgeschlossen'];
  const phasenIndex = $derived(umbau ? PHASEN.indexOf(umbau.status) : -1);

  // Phasenwechsel: Ziele und Sperrgründe kommen aus der API (naechste_status).
  // Der Wechsel Erfassung → Rückbau ist das Einfrieren und steht in der Erfassungsansicht.
  const WECHSEL_LABEL: Partial<Record<UmbauStatus, string>> = {
    umbau: 'Rückbau abschließen, Umbau beginnen',
    wiederaufbau: 'Wiederaufbau beginnen',
    abgeschlossen: 'Umbau abschließen'
  };
  const weiter = $derived(
    umbau?.naechste_status.find(z => z.ziel !== 'verworfen' && z.ziel !== 'rueckbau') ?? null
  );
  const verwerfbar = $derived(umbau?.naechste_status.some(z => z.ziel === 'verworfen') ?? false);
  let wechselLaeuft = $state(false);

  async function wechsle(ziel: UmbauStatus) {
    if (!umbau) return;
    if (ziel === 'verworfen' && !confirm(`Umbau „${umbau.name}" verwerfen? Das lässt sich nicht rückgängig machen.`)) return;
    if (ziel === 'abgeschlossen' && !confirm('Umbau abschließen? Danach sind keine Buchungen mehr möglich.')) return;
    wechselLaeuft = true;
    errorMsg = '';
    try {
      umbau = await umbauApi.status(umbau.id, ziel);
    } catch (err) {
      errorMsg = err instanceof Error ? err.message : 'Statuswechsel fehlgeschlagen.';
      await load();
    } finally {
      wechselLaeuft = false;
    }
  }
</script>

<svelte:head>
  <title>KAiTix - Umbau{umbau ? ` · ${umbau.name}` : ''}</title>
</svelte:head>

<div class="space-y-6 screen-only">
  <div class="flex flex-wrap items-start justify-between gap-4 border-b border-[var(--color-border)] pb-4">
    <div class="flex items-start gap-3 min-w-0">
      <a
        href="/umbau"
        aria-label="Zurück zur Umbau-Liste"
        class="shrink-0 min-w-11 min-h-11 flex items-center justify-center rounded-lg text-[var(--color-text2)] hover:bg-[var(--color-border)] hover:text-[var(--color-text)] transition"
      >
        <ArrowLeft class="w-5 h-5" />
      </a>
      <div class="min-w-0">
        <h2 class="text-xl font-bold text-[var(--color-text)] font-outfit flex items-center gap-2">
          <Construction class="w-5 h-5 shrink-0 text-emerald-400" />
          <span class="truncate">{umbau?.name ?? 'Umbau'}</span>
        </h2>
        {#if umbau}
          <p class="text-xs text-[var(--color-text3)] mt-1">
            {umbau.racks.map(r => r.name).join(', ')} · angelegt {zeit(umbau.erstellt_am)}{umbau.erstellt_von ? ` von ${umbau.erstellt_von}` : ''}
            {#if umbau.eingefroren_am} · eingefroren {zeit(umbau.eingefroren_am)}{umbau.eingefroren_von ? ` von ${umbau.eingefroren_von}` : ''}{/if}
          </p>
          {#if umbau.beschreibung}
            <p class="text-sm text-[var(--color-text2)] mt-1">{umbau.beschreibung}</p>
          {/if}
        {/if}
      </div>
    </div>
    {#if umbau && (weiter || verwerfbar || umbau.enden.length > 0)}
      <!-- Phasenwechsel: gesperrt mit Grund aus der API -->
      <div class="flex flex-col items-end gap-1.5 max-w-full">
        <div class="flex flex-wrap items-center justify-end gap-2">
          {#if umbau.enden.length > 0}
            <!-- Druckliste: Enden nach Rack/Gerät mit Abhakfeldern, Stand jetzt -->
            <button
              type="button"
              onclick={() => window.print()}
              class="flex items-center gap-2 px-3 min-h-11 rounded-lg text-sm text-[var(--color-text)] border border-[var(--color-border2)] hover:bg-[var(--color-border)] transition"
            >
              <Printer class="w-4 h-4" />
              Druckliste
            </button>
          {/if}
          {#if verwerfbar}
            <button
              type="button"
              onclick={() => wechsle('verworfen')}
              disabled={wechselLaeuft}
              class="px-3 min-h-11 rounded-lg text-sm text-red-400 border border-red-500/40 hover:bg-red-500/10 transition disabled:opacity-50"
            >
              Verwerfen
            </button>
          {/if}
          {#if weiter}
            <button
              type="button"
              onclick={() => wechsle(weiter.ziel)}
              disabled={!!weiter.sperrgrund || wechselLaeuft}
              class="flex items-center gap-2 px-4 min-h-11 rounded-lg text-sm font-semibold bg-[#1D9E75] hover:bg-[#0F6E56] text-white transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {WECHSEL_LABEL[weiter.ziel] ?? STATUS_LABEL[weiter.ziel]}
              <ArrowRight class="w-4 h-4" />
            </button>
          {/if}
        </div>
        {#if weiter?.sperrgrund}
          <p class="text-xs text-amber-400 text-right max-w-md whitespace-pre-line" role="status">{weiter.sperrgrund}</p>
        {/if}
      </div>
    {/if}
  </div>

  {#if umbau}
    <!-- Phasen des Umbaus: wo stehen wir -->
    <ol class="flex flex-wrap gap-2 list-none m-0 p-0" aria-label="Phasen des Umbaus">
      {#if umbau.status === 'verworfen'}
        <li class="px-3 py-1.5 rounded-lg text-xs font-semibold border bg-[var(--color-border)] text-[var(--color-text3)] border-[var(--color-border2)]">
          Verworfen
        </li>
      {:else}
        {#each PHASEN as phase, index (phase)}
          <li
            aria-current={index === phasenIndex ? 'step' : undefined}
            class="px-3 py-1.5 rounded-lg text-xs font-semibold border {index === phasenIndex
              ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/40'
              : index < phasenIndex
                ? 'text-[var(--color-text2)] border-[var(--color-border2)]'
                : 'text-[var(--color-text3)] border-[var(--color-border)]'}"
          >
            {index + 1}. {STATUS_LABEL[phase]}
          </li>
        {/each}
      {/if}
    </ol>
  {/if}

  {#if errorMsg}
    <div role="alert" class="flex items-start justify-between gap-3 bg-red-500/10 border border-red-500/30 text-red-400 rounded-lg px-4 py-3 text-sm whitespace-pre-line">
      <span>{errorMsg}</span>
      <button onclick={() => (errorMsg = '')} aria-label="Meldung schließen" class="shrink-0 hover:text-red-300"><X class="w-4 h-4" /></button>
    </div>
  {/if}

  {#if loading}
    <p class="text-sm text-[var(--color-text3)]">Lade Umbau…</p>
  {:else if umbau}
    {#if umbau.status === 'erfassung'}
      <ErfassungAnsicht {umbau} onchange={load} />
    {:else}
      <EndenAnsicht {umbau} onchange={load} />
    {/if}
    <Ereignisprotokoll {umbau} />
  {/if}
</div>

{#if umbau && umbau.enden.length > 0}
  <div class="print-only">
    <UmbauDruck {umbau} />
  </div>
{/if}

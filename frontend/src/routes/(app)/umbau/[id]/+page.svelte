<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import { umbauApi, STATUS_LABEL, zeit, type UmbauDetail, type UmbauStatus } from '$lib/umbauApi';
  import ErfassungAnsicht from '$lib/components/umbau/ErfassungAnsicht.svelte';
  import { ArrowLeft, Construction, X } from '@lucide/svelte';

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
</script>

<svelte:head>
  <title>KAiTix - Umbau{umbau ? ` · ${umbau.name}` : ''}</title>
</svelte:head>

<div class="space-y-6">
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
      <p class="text-sm text-[var(--color-text2)]">
        Der Soll-Stand ist eingefroren: {umbau.fortschritt.enden_gesamt} Enden.
      </p>
    {/if}
  {/if}
</div>

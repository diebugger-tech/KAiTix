<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { api, type Rack } from '$lib/api';
  import { umbauApi, STATUS_LABEL, zeit, type UmbauListe, type UmbauStatus } from '$lib/umbauApi';
  import FensterKopf from '$lib/components/umbau/FensterKopf.svelte';
  import FensterFuss from '$lib/components/umbau/FensterFuss.svelte';
  import { Construction, Plus, ChevronRight, X } from '@lucide/svelte';

  let umbauten = $state<UmbauListe[]>([]);
  let racks = $state<Rack[]>([]);
  let loading = $state(true);
  let errorMsg = $state('');

  // Anlegen
  let showNeu = $state(false);
  let name = $state('');
  let beschreibung = $state('');
  let gewaehlteRacks = $state<number[]>([]);
  let saving = $state(false);
  let formError = $state('');

  async function loadData() {
    loading = true;
    errorMsg = '';
    try {
      [umbauten, racks] = await Promise.all([umbauApi.list(), api.getRacks()]);
    } catch (err) {
      errorMsg = err instanceof Error ? err.message : 'Fehler beim Laden der Umbauten.';
    } finally {
      loading = false;
    }
  }

  onMount(loadData);

  function openNeu() {
    name = '';
    beschreibung = '';
    gewaehlteRacks = [];
    formError = '';
    showNeu = true;
  }

  function toggleRack(id: number) {
    gewaehlteRacks = gewaehlteRacks.includes(id) ? gewaehlteRacks.filter(r => r !== id) : [...gewaehlteRacks, id];
  }

  const anlegenSperre = $derived(
    !name.trim() ? 'Name fehlt.' : gewaehlteRacks.length === 0 ? 'Mindestens ein Rack wählen.' : null
  );

  async function anlegen() {
    if (anlegenSperre) return;
    saving = true;
    formError = '';
    try {
      const neu = await umbauApi.create({
        name: name.trim(),
        beschreibung: beschreibung.trim() || undefined,
        rack_ids: gewaehlteRacks
      });
      showNeu = false;
      await goto(`/umbau/${neu.id}`);
    } catch (err) {
      formError = err instanceof Error ? err.message : 'Anlegen fehlgeschlagen.';
    } finally {
      saving = false;
    }
  }

  const statusFarbe: Record<UmbauStatus, string> = {
    erfassung: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
    rueckbau: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    umbau: 'bg-fuchsia-500/10 text-fuchsia-400 border-fuchsia-500/30',
    wiederaufbau: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
    abgeschlossen: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    verworfen: 'bg-[var(--color-border)] text-[var(--color-text3)] border-[var(--color-border2)]'
  };

  // Ein Satz Fortschritt je Umbau, passend zur Phase.
  function fortschrittText(u: UmbauListe): string {
    const f = u.fortschritt;
    if (u.status === 'erfassung') return `${u.geraete_bestaetigt} von ${u.geraete_gesamt} Geräten erfasst`;
    if (u.status === 'rueckbau') return `${f.abgeklemmt} von ${f.enden_gesamt} Enden abgeklemmt`;
    if (u.status === 'umbau') return `${f.enden_gesamt} Enden abgeklemmt, Umbau läuft`;
    return `${f.angeklemmt} von ${f.enden_gesamt} Enden angeklemmt${f.abweichend ? ` (${f.abweichend} abweichend)` : ''}`;
  }

  function fortschrittProzent(u: UmbauListe): number {
    const f = u.fortschritt;
    if (u.status === 'erfassung') return u.geraete_gesamt ? (u.geraete_bestaetigt / u.geraete_gesamt) * 100 : 0;
    if (!f.enden_gesamt) return 0;
    if (u.status === 'rueckbau') return (f.abgeklemmt / f.enden_gesamt) * 100;
    if (u.status === 'umbau') return 100;
    return (f.angeklemmt / f.enden_gesamt) * 100;
  }
</script>

<svelte:head>
  <title>KAiTix - Umbau</title>
</svelte:head>

<div class="space-y-6">
  <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-4">
    <div>
      <h2 class="text-xl font-bold text-[var(--color-text)] font-outfit flex items-center gap-2">
        <Construction class="w-5 h-5 text-emerald-400" />
        Serverraum-Umbau
      </h2>
      <p class="text-xs text-[var(--color-text3)] mt-1">
        Kabel erfassen, Soll-Stand einfrieren, abklemmen, nach dem Umbau nach Soll wieder anklemmen.
      </p>
    </div>
    <button
      onclick={openNeu}
      class="flex items-center gap-2 px-4 min-h-11 bg-[#1D9E75] hover:bg-[#0F6E56] text-white rounded-lg text-sm font-semibold transition"
    >
      <Plus class="w-4 h-4" />
      <span>Umbau anlegen</span>
    </button>
  </div>

  {#if errorMsg}
    <div role="alert" class="flex items-start justify-between gap-3 bg-red-500/10 border border-red-500/30 text-red-400 rounded-lg px-4 py-3 text-sm">
      <span>{errorMsg}</span>
      <button onclick={() => (errorMsg = '')} aria-label="Meldung schließen" class="shrink-0 hover:text-red-300"><X class="w-4 h-4" /></button>
    </div>
  {/if}

  {#if loading}
    <p class="text-sm text-[var(--color-text3)]">Lade Umbauten…</p>
  {:else if umbauten.length === 0}
    <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-8 text-center">
      <p class="text-sm text-[var(--color-text2)]">Noch kein Umbau angelegt.</p>
      <p class="text-xs text-[var(--color-text3)] mt-1">Ein Umbau beginnt mit der Auswahl der Racks, die umgebaut werden.</p>
    </div>
  {:else}
    <ul class="grid grid-cols-1 lg:grid-cols-2 gap-4 list-none m-0 p-0">
      {#each umbauten as u (u.id)}
        <li>
          <a
            href="/umbau/{u.id}"
            class="block min-h-11 bg-[var(--color-bg2)] border border-[var(--color-border)] hover:border-[#1D9E75] rounded-xl p-4 transition"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <div class="text-base font-bold text-[var(--color-text)] truncate">{u.name}</div>
                <div class="text-xs text-[var(--color-text3)] mt-0.5 truncate">
                  {u.racks.map(r => r.name).join(', ') || 'Keine Racks'}
                </div>
              </div>
              <span class="shrink-0 text-[11px] font-semibold px-2 py-0.5 rounded border {statusFarbe[u.status]}">
                {STATUS_LABEL[u.status]}
              </span>
            </div>
            <div class="mt-3 h-1.5 rounded-full bg-[var(--color-bg3)] overflow-hidden" aria-hidden="true">
              <div class="h-full bg-[#1D9E75]" style="width: {fortschrittProzent(u)}%"></div>
            </div>
            <div class="mt-2 flex items-center justify-between gap-3 text-xs text-[var(--color-text2)]">
              <span>{fortschrittText(u)}</span>
              <span class="flex items-center gap-1 text-[var(--color-text3)]">
                angelegt {zeit(u.erstellt_am)}{u.erstellt_von ? ` · ${u.erstellt_von}` : ''}
                <ChevronRight class="w-4 h-4" />
              </span>
            </div>
          </a>
        </li>
      {/each}
    </ul>
  {/if}
</div>

{#if showNeu}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl max-w-lg w-full shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
    <FensterKopf titel="Umbau anlegen" onclose={() => (showNeu = false)} />
    <div class="px-5 pb-4 space-y-4 overflow-y-auto">
      <div>
        <label for="umbau-name" class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Name *</label>
        <input
          id="umbau-name"
          type="text"
          bind:value={name}
          maxlength="200"
          placeholder="z. B. Elektro-Umbau Serverraum 1"
          class="w-full min-h-11 bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]"
        />
      </div>
      <div>
        <label for="umbau-beschreibung" class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Beschreibung</label>
        <textarea
          id="umbau-beschreibung"
          bind:value={beschreibung}
          rows="2"
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75] resize-none"
        ></textarea>
      </div>
      <fieldset>
        <legend class="block text-xs font-semibold text-[var(--color-text2)] mb-1">
          Racks im Umfang * — {gewaehlteRacks.length} gewählt
        </legend>
        {#if racks.length === 0}
          <p class="text-sm text-[var(--color-text3)]">Es sind noch keine Racks angelegt.</p>
        {:else}
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {#each racks as rack (rack.id)}
              <label class="flex items-center gap-3 min-h-11 px-3 rounded-lg border cursor-pointer transition {gewaehlteRacks.includes(rack.id) ? 'border-emerald-500 bg-emerald-500/10' : 'border-[var(--color-border2)] hover:bg-[var(--color-hover)]'}">
                <input type="checkbox" checked={gewaehlteRacks.includes(rack.id)} onchange={() => toggleRack(rack.id)} class="w-5 h-5" />
                <span class="min-w-0">
                  <span class="block text-sm font-semibold text-[var(--color-text)] truncate">{rack.name}</span>
                  <span class="block text-[11px] text-[var(--color-text3)] truncate">{rack.standort}</span>
                </span>
              </label>
            {/each}
          </div>
        {/if}
      </fieldset>
      {#if formError}
        <p role="alert" class="text-sm text-red-400">{formError}</p>
      {/if}
    </div>
    <FensterFuss
      hauptLabel="Umbau anlegen"
      onhaupt={anlegen}
      onabbrechen={() => (showNeu = false)}
      gesperrt={!!anlegenSperre}
      grund={anlegenSperre}
      busy={saving}
    />
  </div>
</div>
{/if}

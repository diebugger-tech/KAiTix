<!--
  Erfassung eines Umbaus: Rack → Gerät → vorhandene Kabel-Enden, „Kabel hinzufügen“ und
  „Gerät vollständig erfasst“. Kabel werden über /cables gespeichert; der Umbau liest sie nur.
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { api, type Cable, type Device, type Kabeltyp } from '$lib/api';
  import { endenAmGeraet, type KabelEnde } from '$lib/kabel';
  import { umbauApi, type UmbauDetail, type UmbauGeraet } from '$lib/umbauApi';
  import KabelErfassen from './KabelErfassen.svelte';
  import { Plus, Check, ChevronDown, ChevronRight, TriangleAlert, Snowflake } from '@lucide/svelte';

  let {
    umbau,
    onchange
  }: {
    umbau: UmbauDetail;
    /** Umbau neu laden (Fortschritt je Gerät, Sperrliste). */
    onchange: () => Promise<void> | void;
  } = $props();

  let cables = $state<Cable[]>([]);
  let devices = $state<Device[]>([]);
  let kabeltypen = $state<Kabeltyp[]>([]);
  let loading = $state(true);
  let fehler = $state('');

  let offen = $state<Record<number, boolean>>({});
  let erfassenFuer = $state<UmbauGeraet | null>(null);
  let bestaetigtLaeuft = $state<number | null>(null);
  let einfrierenLaeuft = $state(false);

  async function ladeStammdaten() {
    try {
      const [c, d, k] = await Promise.all([api.getCables(), api.getDevices(), api.getKabeltypen(true)]);
      cables = c;
      devices = d;
      // Strom gehört in dieser Version nicht zum Umbau.
      kabeltypen = k.filter(typ => typ.kategorie !== 'strom');
    } catch (err) {
      fehler = err instanceof Error ? err.message : 'Fehler beim Laden der Kabel.';
    } finally {
      loading = false;
    }
  }

  onMount(ladeStammdaten);

  const geraeteName = $derived(new Map(devices.map(d => [d.id, d.hostname])));
  const racks = $derived.by(() => {
    const gruppen = new Map<string, UmbauGeraet[]>();
    for (const g of umbau.geraete) {
      const rack = g.rack_name ?? 'Ohne Rack';
      gruppen.set(rack, [...(gruppen.get(rack) ?? []), g]);
    }
    return [...gruppen.entries()].sort(([a], [b]) => a.localeCompare(b, 'de', { numeric: true }));
  });
  const bestaetigt = $derived(umbau.geraete.filter(g => g.bestaetigt).length);

  function enden(deviceId: number): KabelEnde[] {
    return endenAmGeraet(cables, deviceId);
  }

  function gegenstelle(ende: KabelEnde): string {
    return ende.gegenstellen
      .map(g => `${g.device_id ? (geraeteName.get(g.device_id) ?? `#${g.device_id}`) : '—'}:${g.port || '—'}`)
      .join(', ');
  }

  async function nachSpeichern() {
    await ladeStammdaten();
    await onchange();
  }

  async function setzeBestaetigt(g: UmbauGeraet, wert: boolean) {
    bestaetigtLaeuft = g.device_id;
    fehler = '';
    try {
      await umbauApi.bestaetigeGeraet(umbau.id, g.device_id, wert);
      await onchange();
    } catch (err) {
      fehler = err instanceof Error ? err.message : 'Bestätigen fehlgeschlagen.';
    } finally {
      bestaetigtLaeuft = null;
    }
  }

  async function einfrieren() {
    if (!confirm('Soll-Stand jetzt einfrieren? Danach beginnt der Rückbau; die erfassten Kabel sind dann das Soll für den Wiederaufbau.')) return;
    einfrierenLaeuft = true;
    fehler = '';
    try {
      await umbauApi.einfrieren(umbau.id);
      await onchange();
    } catch (err) {
      fehler = err instanceof Error ? err.message : 'Einfrieren fehlgeschlagen.';
      await onchange();
    } finally {
      einfrierenLaeuft = false;
    }
  }
</script>

<div class="space-y-5">
  <!-- Einfrieren: gesperrt mit der Liste aus der API -->
  <section class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-4 space-y-3">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <div class="text-sm font-bold text-[var(--color-text)]">{bestaetigt} von {umbau.geraete.length} Geräten vollständig erfasst</div>
        <p class="text-xs text-[var(--color-text3)] mt-0.5">
          Einfrieren hält alle Kabel im Umfang als Soll fest. Stromkabel gehören nicht dazu.
        </p>
      </div>
      <button
        type="button"
        onclick={einfrieren}
        disabled={umbau.einfrier_sperren.length > 0 || einfrierenLaeuft}
        class="flex items-center gap-2 px-4 min-h-11 rounded-lg text-sm font-semibold bg-[#1D9E75] hover:bg-[#0F6E56] text-white transition disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <Snowflake class="w-4 h-4" />
        {einfrierenLaeuft ? 'Friert ein…' : 'Soll-Stand einfrieren'}
      </button>
    </div>
    {#if umbau.einfrier_sperren.length > 0}
      <div class="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2">
        <div class="flex items-center gap-2 text-sm font-semibold text-amber-400">
          <TriangleAlert class="w-4 h-4" />
          Einfrieren gesperrt — {umbau.einfrier_sperren.length} {umbau.einfrier_sperren.length === 1 ? 'Punkt' : 'Punkte'} offen
        </div>
        <ul class="mt-1.5 space-y-0.5 text-xs text-[var(--color-text2)] list-disc pl-5 max-h-48 overflow-y-auto">
          {#each umbau.einfrier_sperren as sperre (sperre)}<li>{sperre}</li>{/each}
        </ul>
      </div>
    {/if}
  </section>

  {#if fehler}
    <p role="alert" class="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2 whitespace-pre-line">{fehler}</p>
  {/if}

  {#if loading}
    <p class="text-sm text-[var(--color-text3)]">Lade Kabel…</p>
  {:else if umbau.geraete.length === 0}
    <p class="text-sm text-[var(--color-text3)]">In den gewählten Racks stehen keine Geräte.</p>
  {:else}
    {#each racks as [rackName, geraete] (rackName)}
      <section class="space-y-2">
        <h3 class="text-xs uppercase font-bold tracking-wider text-[var(--color-text3)] font-mono">
          {rackName} · {geraete.filter(g => g.bestaetigt).length} von {geraete.length} erfasst
        </h3>
        {#each geraete as g (g.device_id)}
          {@const liste = enden(g.device_id)}
          {@const auf = offen[g.device_id] ?? !g.bestaetigt}
          <article class="bg-[var(--color-bg2)] border rounded-xl overflow-hidden {g.bestaetigt ? 'border-emerald-500/40' : 'border-[var(--color-border)]'}">
            <div class="flex flex-wrap items-stretch">
              <button
                type="button"
                onclick={() => (offen = { ...offen, [g.device_id]: !auf })}
                aria-expanded={auf}
                class="flex-1 min-w-0 min-h-12 flex items-center gap-3 px-4 py-2 text-left hover:bg-[var(--color-hover)] transition"
              >
                {#if auf}<ChevronDown class="w-4 h-4 shrink-0 text-[var(--color-text3)]" />{:else}<ChevronRight class="w-4 h-4 shrink-0 text-[var(--color-text3)]" />{/if}
                <span class="min-w-0">
                  <span class="block text-sm font-bold text-[var(--color-text)] truncate">{g.hostname}</span>
                  <span class="block text-xs text-[var(--color-text3)]">
                    {g.typ} · {liste.length} {liste.length === 1 ? 'Kabel-Ende' : 'Kabel-Enden'}{g.kabel_unvollstaendig ? ` · ${g.kabel_unvollstaendig} unvollständig` : ''}
                  </span>
                </span>
              </button>
              <div class="flex items-center gap-2 px-3 py-2">
                <button
                  type="button"
                  onclick={() => (erfassenFuer = g)}
                  class="flex items-center gap-1.5 px-3 min-h-11 rounded-lg border border-[var(--color-border2)] text-sm text-[var(--color-text)] hover:bg-[var(--color-border)] transition"
                >
                  <Plus class="w-4 h-4" /> Kabel hinzufügen
                </button>
                <button
                  type="button"
                  onclick={() => setzeBestaetigt(g, !g.bestaetigt)}
                  disabled={bestaetigtLaeuft === g.device_id}
                  aria-pressed={g.bestaetigt}
                  title={g.bestaetigt ? `Bestätigt von ${g.bestaetigt_von ?? '—'}. Antippen nimmt die Bestätigung zurück.` : 'Alle Kabel dieses Geräts sind erfasst'}
                  class="flex items-center gap-1.5 px-3 min-h-11 rounded-lg text-sm font-semibold transition disabled:opacity-50 {g.bestaetigt
                    ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/40'
                    : 'bg-[#1D9E75] hover:bg-[#0F6E56] text-white'}"
                >
                  <Check class="w-4 h-4" />
                  {g.bestaetigt ? 'Vollständig erfasst' : 'Gerät vollständig erfasst'}
                </button>
              </div>
            </div>
            {#if auf}
              <div class="border-t border-[var(--color-border)] px-4 py-2">
                {#if liste.length === 0}
                  <p class="text-xs text-[var(--color-text3)] py-1">Noch kein Kabel an diesem Gerät erfasst.</p>
                {:else}
                  <ul class="divide-y divide-[var(--color-border)] list-none m-0 p-0">
                    {#each liste as ende (ende.schluessel)}
                      <li class="flex flex-wrap items-center gap-x-3 gap-y-0.5 py-2 text-sm">
                        <span class="font-mono font-bold text-[var(--color-text)] min-w-[5rem]">{ende.eigenerPort || '—'}</span>
                        <span class="text-[var(--color-text3)]">→</span>
                        <span class="font-mono text-[var(--color-text2)]">{gegenstelle(ende)}</span>
                        <span class="ml-auto flex items-center gap-2 text-xs text-[var(--color-text3)]">
                          {#if ende.unvollstaendig}
                            <span class="px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 font-semibold">unvollständig</span>
                          {/if}
                          <span>{ende.cable.kabeltyp?.name ?? ende.cable.typ}</span>
                          <span class="font-mono">{ende.cable.kabel_nr ?? `#${ende.cable.id}`}</span>
                        </span>
                      </li>
                    {/each}
                  </ul>
                {/if}
              </div>
            {/if}
          </article>
        {/each}
      </section>
    {/each}
    <p class="text-xs text-[var(--color-text3)]">
      Kabel ändern oder löschen: in der <a href="/cables" class="underline underline-offset-2 hover:text-[var(--color-text)]">Kabelliste</a>.
    </p>
  {/if}
</div>

{#if erfassenFuer}
  <KabelErfassen
    geraet={erfassenFuer}
    {devices}
    {kabeltypen}
    {cables}
    onsaved={nachSpeichern}
    onclose={() => (erfassenFuer = null)}
  />
{/if}

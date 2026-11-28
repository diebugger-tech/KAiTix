<!--
  Rückbau und Wiederaufbau: die Enden des eingefrorenen Solls, gruppiert Rack → Gerät.
  Rückbau = abzuklemmende Enden, Wiederaufbau = anzuklemmende Enden. Gebucht wird je Ende
  über den Einzelendpunkt; die Sammelbuchung ruft ihn nacheinander auf.
  Ob ein Ende buchbar ist, sagt allein `sperrgrund` aus der API.
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { api, type Device } from '$lib/api';
  import { umbauApi, ENDE_STATUS_LABEL, zeit, type UmbauDetail, type UmbauEnde } from '$lib/umbauApi';
  import CableSelectGrid from './CableSelectGrid.svelte';
  import AndererPort from './AndererPort.svelte';
  import KabelNachtragen from './KabelNachtragen.svelte';
  import { ChevronDown, ChevronRight, ListChecks, Undo2, Unplug, Plug, TriangleAlert, Plus, Trash2 } from '@lucide/svelte';

  let {
    umbau,
    onchange
  }: {
    umbau: UmbauDetail;
    /** Umbau neu laden (Status der Enden, Fortschritt, Protokoll). */
    onchange: () => Promise<void> | void;
  } = $props();

  const rueckbau = $derived(umbau.status === 'rueckbau');
  const wiederaufbau = $derived(umbau.status === 'wiederaufbau');
  const buchbar = $derived(rueckbau || wiederaufbau);

  let devices = $state<Device[]>([]);
  onMount(async () => {
    devices = await api.getDevices().catch(() => []);
  });

  let laeuft = $state<number | null>(null);
  let fehler = $state<string[]>([]);
  let zu = $state<Record<string, boolean>>({});
  let sammel = $state<'buchen' | 'korrigieren' | null>(null);
  let sammelBusy = $state(false);
  let andererPort = $state<UmbauEnde | null>(null);
  let nachtragOffen = $state(false);

  /** Nachträge, die sich noch entfernen lassen: im Rückbau, alle Enden gesteckt. */
  const entfernbar = $derived.by(() => {
    const status = new Map<number, boolean>();
    for (const e of umbau.enden) {
      if (e.nachtrag_nr == null) continue;
      status.set(e.nachtrag_nr, (status.get(e.nachtrag_nr) ?? true) && e.status === 'gesteckt');
    }
    return new Set([...status].filter(([, alleGesteckt]) => rueckbau && alleGesteckt).map(([nr]) => nr));
  });

  async function nachtragEntfernen(e: UmbauEnde) {
    if (e.nachtrag_nr == null) return;
    if (!confirm(`Nachgetragenes Kabel ${e.kabel_nr ?? ''} mit allen Enden entfernen?`)) return;
    await einzeln(e, () => umbauApi.nachtragEntfernen(umbau.id, e.nachtrag_nr as number));
  }

  /** Position und Länge aus der Soll-Kopie, soweit vorhanden. */
  function ortUndLaenge(e: UmbauEnde): string {
    return [e.soll_position, e.laenge_m != null ? `${e.laenge_m.toLocaleString('de-DE')} m` : null]
      .filter(Boolean)
      .join(' · ');
  }

  // --- Was ist in dieser Phase erledigt, offen, zurücknehmbar? -----------------
  function erledigt(e: UmbauEnde): boolean {
    if (rueckbau) return e.status !== 'gesteckt';
    return e.status === 'angeklemmt' || e.status === 'angeklemmt_abweichend';
  }
  /** Enden, die die Hauptaktion der Phase noch braucht. */
  const offene = $derived(
    umbau.enden.filter(e => !e.sperrgrund && (rueckbau ? e.status === 'gesteckt' : e.status === 'abgeklemmt'))
  );
  /** Enden, deren letzte Buchung in dieser Phase zurückgenommen werden kann. */
  const zuruecknehmbar = $derived(
    umbau.enden.filter(
      e => !e.sperrgrund && (rueckbau ? e.status === 'abgeklemmt' : e.status === 'angeklemmt' || e.status === 'angeklemmt_abweichend')
    )
  );
  const verb = $derived(rueckbau ? 'abgeklemmt' : 'angeklemmt');

  // --- Gruppen Rack → Gerät -----------------------------------------------------
  interface Gruppe {
    schluessel: string;
    rack: string;
    geraet: string;
    enden: UmbauEnde[];
    fertig: number;
  }
  const gruppen = $derived.by(() => {
    const nach = new Map<string, Gruppe>();
    for (const e of umbau.enden) {
      const rack = e.soll_rack_name ?? 'Ohne Rack';
      const schluessel = `${rack}\u0000${e.soll_device_name}`;
      const g = nach.get(schluessel) ?? { schluessel, rack, geraet: e.soll_device_name, enden: [], fertig: 0 };
      g.enden.push(e);
      if (erledigt(e)) g.fertig++;
      nach.set(schluessel, g);
    }
    const liste = [...nach.values()].sort(
      (a, b) => a.rack.localeCompare(b.rack, 'de', { numeric: true }) || a.geraet.localeCompare(b.geraet, 'de', { numeric: true })
    );
    for (const g of liste) g.enden.sort((a, b) => a.soll_port.localeCompare(b.soll_port, 'de', { numeric: true }));
    return liste;
  });
  const racks = $derived([...new Set(gruppen.map(g => g.rack))]);

  function gruppeZu(g: Gruppe): boolean {
    // Erledigte Gruppen klappen von selbst zu, damit die offene Arbeit oben steht.
    return zu[g.schluessel] ?? (buchbar && g.fertig === g.enden.length);
  }

  function rackStand(rack: string): string {
    const eigene = gruppen.filter(g => g.rack === rack);
    const gesamt = eigene.reduce((n, g) => n + g.enden.length, 0);
    const fertig = eigene.reduce((n, g) => n + g.fertig, 0);
    return `${fertig} von ${gesamt} ${verb}`;
  }

  // --- Buchungen ------------------------------------------------------------------
  function endeName(e: UmbauEnde): string {
    return `${e.kabel_nr ?? 'Kabel'} · ${e.soll_device_name}:${e.soll_port}`;
  }

  async function einzeln(e: UmbauEnde, aktion: () => Promise<unknown>) {
    laeuft = e.id;
    fehler = [];
    try {
      await aktion();
    } catch (err) {
      fehler = [`${endeName(e)}: ${err instanceof Error ? err.message : 'Buchung fehlgeschlagen'}`];
    } finally {
      laeuft = null;
      await onchange();
    }
  }

  const abklemmen = (e: UmbauEnde) => einzeln(e, () => umbauApi.abklemmen(umbau.id, e.id, true));
  const anklemmenSoll = (e: UmbauEnde) => einzeln(e, () => umbauApi.anklemmen(umbau.id, e.id, { angeklemmt: true }));

  /** Eine Stufe zurück: im Rückbau abgeklemmt → gesteckt, im Wiederaufbau angeklemmt → abgeklemmt. */
  function zuruecknehmen(e: UmbauEnde): Promise<unknown> {
    return rueckbau ? umbauApi.abklemmen(umbau.id, e.id, false) : umbauApi.anklemmen(umbau.id, e.id, { angeklemmt: false });
  }

  // Sammelbuchung: derselbe Einzelendpunkt, nacheinander. Fehlschläge stehen namentlich da.
  async function sammelBuchen(ids: number[], aktion: (e: UmbauEnde) => Promise<unknown>) {
    sammelBusy = true;
    const fehlgeschlagen: string[] = [];
    const nachId = new Map(umbau.enden.map(e => [e.id, e]));
    for (const id of ids) {
      const e = nachId.get(id);
      if (!e) continue;
      try {
        await aktion(e);
      } catch (err) {
        fehlgeschlagen.push(`${endeName(e)}: ${err instanceof Error ? err.message : 'Buchung fehlgeschlagen'}`);
      }
    }
    fehler = fehlgeschlagen;
    sammelBusy = false;
    sammel = null;
    await onchange();
  }

  const statusFarbe: Record<UmbauEnde['status'], string> = {
    gesteckt: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
    abgeklemmt: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    angeklemmt: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    angeklemmt_abweichend: 'bg-fuchsia-500/10 text-fuchsia-400 border-fuchsia-500/30'
  };

  const gridName = (e: UmbauEnde) => `${e.soll_device_name}:${e.soll_port}`;
  const gridMeta = (e: UmbauEnde) =>
    [e.kabel_nr, e.kabeltyp_name, e.gegenseite.length ? `↔ ${e.gegenseite.join(', ')}` : null].filter(Boolean).join(' · ');
  const gridGruppe = (e: UmbauEnde) => `${e.soll_rack_name ?? 'Ohne Rack'} · ${e.soll_device_name}`;
</script>

<div class="space-y-5">
  <!-- Stand der Phase und Sammelaktionen -->
  <section class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-4 flex flex-wrap items-center justify-between gap-3">
    <div>
      {#if rueckbau}
        <div class="text-sm font-bold text-[var(--color-text)]">{umbau.fortschritt.abgeklemmt} von {umbau.fortschritt.enden_gesamt} Enden abgeklemmt</div>
        <p class="text-xs text-[var(--color-text3)] mt-0.5">Jedes Kabel wird an beiden Enden abgeklemmt. Erst dann kann der Umbau beginnen.</p>
      {:else if wiederaufbau}
        <div class="text-sm font-bold text-[var(--color-text)]">
          {umbau.fortschritt.angeklemmt} von {umbau.fortschritt.enden_gesamt} Enden angeklemmt{umbau.fortschritt.abweichend ? ` · ${umbau.fortschritt.abweichend} abweichend vom Soll` : ''}
        </div>
        <p class="text-xs text-[var(--color-text3)] mt-0.5">Jedes Ende kommt an seinen Soll-Port. Ein anderer Port braucht einen Grund.</p>
      {:else}
        <div class="text-sm font-bold text-[var(--color-text)]">{umbau.fortschritt.enden_gesamt} Enden im Soll</div>
        <p class="text-xs text-[var(--color-text3)] mt-0.5">{umbau.enden[0]?.sperrgrund ?? 'In diesem Status wird nichts gebucht.'}</p>
      {/if}
    </div>
    {#if buchbar}
      <div class="flex flex-wrap items-center gap-2">
        {#if rueckbau}
          <button
            type="button"
            onclick={() => (nachtragOffen = true)}
            class="flex items-center gap-2 px-4 min-h-11 rounded-lg text-sm font-semibold border border-[var(--color-border2)] text-[var(--color-text)] hover:bg-[var(--color-border)] transition"
          >
            <Plus class="w-4 h-4" />
            Kabel nachtragen
          </button>
        {/if}
        <button
          type="button"
          onclick={() => (sammel = 'buchen')}
          disabled={offene.length === 0}
          class="flex items-center gap-2 px-4 min-h-11 rounded-lg text-sm font-semibold bg-[#1D9E75] hover:bg-[#0F6E56] text-white transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ListChecks class="w-4 h-4" />
          {rueckbau ? 'Mehrere abklemmen' : 'Mehrere nach Soll anklemmen'}
        </button>
        <button
          type="button"
          onclick={() => (sammel = 'korrigieren')}
          disabled={zuruecknehmbar.length === 0}
          class="flex items-center gap-2 px-4 min-h-11 rounded-lg text-sm font-semibold border border-red-500/40 text-red-400 hover:bg-red-500/10 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Undo2 class="w-4 h-4" />
          Korrigieren
        </button>
      </div>
    {/if}
  </section>

  {#if fehler.length > 0}
    <div role="alert" class="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2">
      <div class="flex items-center gap-2 text-sm font-semibold text-red-400">
        <TriangleAlert class="w-4 h-4" />
        {fehler.length === 1 ? 'Eine Buchung ist fehlgeschlagen' : `${fehler.length} Buchungen sind fehlgeschlagen`}
      </div>
      <ul class="mt-1 space-y-0.5 text-xs text-[var(--color-text2)] list-disc pl-5">
        {#each fehler as zeile (zeile)}<li>{zeile}</li>{/each}
      </ul>
    </div>
  {/if}

  {#if umbau.enden.length === 0}
    <p class="text-sm text-[var(--color-text3)]">Im Umfang dieses Umbaus lag beim Einfrieren kein Kabel.</p>
  {/if}

  {#each racks as rack (rack)}
    <section class="space-y-2">
      <h3 class="text-xs uppercase font-bold tracking-wider text-[var(--color-text3)] font-mono">
        {rack}{buchbar ? ` · ${rackStand(rack)}` : ''}
      </h3>
      {#each gruppen.filter(g => g.rack === rack) as g (g.schluessel)}
        {@const geschlossen = gruppeZu(g)}
        <article class="bg-[var(--color-bg2)] border rounded-xl overflow-hidden {buchbar && g.fertig === g.enden.length ? 'border-emerald-500/40' : 'border-[var(--color-border)]'}">
          <button
            type="button"
            onclick={() => (zu = { ...zu, [g.schluessel]: !geschlossen })}
            aria-expanded={!geschlossen}
            class="w-full min-h-12 flex items-center gap-3 px-4 py-2 text-left hover:bg-[var(--color-hover)] transition"
          >
            {#if geschlossen}<ChevronRight class="w-4 h-4 shrink-0 text-[var(--color-text3)]" />{:else}<ChevronDown class="w-4 h-4 shrink-0 text-[var(--color-text3)]" />{/if}
            <span class="flex-1 min-w-0 text-sm font-bold text-[var(--color-text)] truncate">{g.geraet}</span>
            <span class="shrink-0 text-xs font-semibold text-[var(--color-text2)]">
              {buchbar ? `${g.fertig} von ${g.enden.length} ${verb}` : `${g.enden.length} ${g.enden.length === 1 ? 'Ende' : 'Enden'}`}
            </span>
          </button>
          {#if !geschlossen}
            <ul class="border-t border-[var(--color-border)] divide-y divide-[var(--color-border)] list-none m-0 p-0">
              {#each g.enden as e (e.id)}
                <li class="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
                  <div class="flex-1 min-w-[16rem]">
                    <div class="flex flex-wrap items-center gap-2">
                      <span class="font-mono text-base font-bold text-[var(--color-text)]">{e.soll_device_name}:{e.soll_port}</span>
                      <span class="text-[11px] font-semibold px-2 py-0.5 rounded border {statusFarbe[e.status]}">{ENDE_STATUS_LABEL[e.status]}</span>
                      {#if e.nachtrag_nr != null}
                        <span
                          class="text-[11px] font-semibold px-2 py-0.5 rounded border border-orange-500/40 bg-orange-500/10 text-orange-400"
                          title="Im Rückbau nachgetragen, steht nicht in der Kabelliste"
                        >
                          nachgetragen
                        </span>
                      {/if}
                    </div>
                    <div class="mt-0.5 text-xs text-[var(--color-text2)]">
                      <span class="font-mono">{e.kabel_nr ?? '—'}</span> · {e.kabeltyp_name}{e.farbe ? ` · ${e.farbe}` : ''}
                      · Gegenseite <span class="font-mono">{e.gegenseite.join(', ') || '—'}</span>
                      {#if ortUndLaenge(e)}<span class="text-[var(--color-text3)]"> · {ortUndLaenge(e)}</span>{/if}
                    </div>
                    {#if e.status === 'angeklemmt_abweichend'}
                      <div class="mt-0.5 text-xs text-fuchsia-400">
                        Ist: <span class="font-mono">{e.ist_device_name}:{e.ist_port}</span> · {e.abweichung_grund}
                      </div>
                    {/if}
                    {#if erledigt(e) && buchbar}
                      <div class="mt-0.5 text-[11px] text-[var(--color-text3)]">
                        {rueckbau ? `${zeit(e.abgeklemmt_am)} · ${e.abgeklemmt_von ?? '—'}` : `${zeit(e.angeklemmt_am)} · ${e.angeklemmt_von ?? '—'}`}
                      </div>
                    {/if}
                  </div>
                  {#if !e.sperrgrund && rueckbau && e.status === 'gesteckt'}
                    <div class="flex flex-wrap items-center gap-2">
                      {#if e.seite === 'A' && e.nachtrag_nr != null && entfernbar.has(e.nachtrag_nr)}
                        <button
                          type="button"
                          onclick={() => nachtragEntfernen(e)}
                          disabled={laeuft === e.id}
                          aria-label="Nachtrag {e.kabel_nr ?? ''} entfernen"
                          title="Nachtrag entfernen (z. B. bei Tippfehler)"
                          class="min-w-11 min-h-11 flex items-center justify-center rounded-lg border border-red-500/40 text-red-400 hover:bg-red-500/10 transition disabled:opacity-50"
                        >
                          <Trash2 class="w-4 h-4" />
                        </button>
                      {/if}
                      <button
                        type="button"
                        onclick={() => abklemmen(e)}
                        disabled={laeuft === e.id}
                        class="flex items-center gap-2 px-4 min-h-11 rounded-lg text-sm font-semibold bg-[#1D9E75] hover:bg-[#0F6E56] text-white transition disabled:opacity-50"
                      >
                        <Unplug class="w-4 h-4" /> Abklemmen
                      </button>
                    </div>
                  {:else if !e.sperrgrund && wiederaufbau && e.status === 'abgeklemmt'}
                    <div class="flex flex-wrap items-center gap-2">
                      <button
                        type="button"
                        onclick={() => anklemmenSoll(e)}
                        disabled={laeuft === e.id}
                        class="flex items-center gap-2 px-4 min-h-11 rounded-lg text-sm font-semibold bg-[#1D9E75] hover:bg-[#0F6E56] text-white transition disabled:opacity-50"
                      >
                        <Plug class="w-4 h-4" /> Soll-Port {e.soll_port}
                      </button>
                      <button
                        type="button"
                        onclick={() => (andererPort = e)}
                        disabled={laeuft === e.id}
                        class="px-3 min-h-11 rounded-lg text-sm border border-[var(--color-border2)] text-[var(--color-text)] hover:bg-[var(--color-border)] transition disabled:opacity-50"
                      >
                        Anderer Port…
                      </button>
                    </div>
                  {/if}
                </li>
              {/each}
            </ul>
          {/if}
        </article>
      {/each}
    </section>
  {/each}
</div>

{#if sammel}
  <div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
    <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl max-w-3xl w-full shadow-2xl overflow-hidden">
      {#if sammel === 'buchen'}
        <CableSelectGrid
          cables={offene}
          title={rueckbau ? 'Enden abklemmen' : 'Enden nach Soll anklemmen'}
          actionLabel={rueckbau ? 'Abklemmen buchen' : 'Anklemmen buchen'}
          busy={sammelBusy}
          getId={(e) => e.id}
          getName={gridName}
          getMeta={gridMeta}
          getGroup={gridGruppe}
          confirmNote={rueckbau ? null : 'gebucht wird der Soll-Port'}
          onconfirm={(ids) => sammelBuchen(ids, (e) => (rueckbau ? umbauApi.abklemmen(umbau.id, e.id, true) : umbauApi.anklemmen(umbau.id, e.id, { angeklemmt: true })))}
          oncancel={() => (sammel = null)}
        />
      {:else}
        <!-- Korrigieren: nimmt je Ende genau eine Stufe zurück. Startet ohne Auswahl, rote Optik. -->
        <CableSelectGrid
          cables={zuruecknehmbar}
          title={rueckbau ? 'Korrigieren: Abklemmen zurücknehmen' : 'Korrigieren: Anklemmen zurücknehmen'}
          actionLabel="Zurücknehmen"
          busy={sammelBusy}
          initialSelected="none"
          confirmVariant="danger"
          getId={(e) => e.id}
          getName={gridName}
          getMeta={gridMeta}
          getBadge={(e) => ENDE_STATUS_LABEL[e.status]}
          getGroup={gridGruppe}
          confirmNote={rueckbau ? 'danach wieder „gesteckt“' : 'danach wieder „abgeklemmt“'}
          onconfirm={(ids) => sammelBuchen(ids, zuruecknehmen)}
          oncancel={() => (sammel = null)}
        />
      {/if}
    </div>
  </div>
{/if}

{#if nachtragOffen}
  <KabelNachtragen
    {devices}
    onconfirm={async (eingabe) => {
      await umbauApi.nachtragen(umbau.id, eingabe);
      await onchange();
    }}
    onclose={() => (nachtragOffen = false)}
  />
{/if}

{#if andererPort}
  {@const ziel = andererPort}
  <AndererPort
    ende={ziel}
    {devices}
    onconfirm={async (eingabe) => {
      await umbauApi.anklemmen(umbau.id, ziel.id, { angeklemmt: true, ...eingabe });
      await onchange();
    }}
    onclose={() => (andererPort = null)}
  />
{/if}

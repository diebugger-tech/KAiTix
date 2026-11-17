<script lang="ts" generics="T">
  import { CheckSquare, ChevronDown, ChevronRight, Search, Square } from '@lucide/svelte';
  import { untrack, type Snippet } from 'svelte';
  import FensterKopf from './FensterKopf.svelte';
  import FensterFuss from './FensterFuss.svelte';

  /**
   * Auswahlraster für Sammelbuchungen im Umbau (Abklemmen, Anklemmen, Korrigieren).
   *
   * Übernommen aus CabellistPro (frontend/src/lib/components/CableSelectGrid.svelte) und
   * angepasst: @lucide/svelte statt lucide-svelte, keine CabellistPro-Stores, KAiTix-Farben,
   * ohne Prüfstufen-Filter, Plan-Knöpfe und Werkstatt-Variante.
   *
   * Der Baustein kennt nur Auswahl und Gruppierung. Wonach gruppiert wird und was mit der
   * Auswahl passiert, gibt der Aufrufer hinein. Bewusst KEINE Fachlogik: er liefert die
   * gewählten IDs zurück, mehr nicht.
   *
   * Viele Einträge: das Fenster wächst nicht mit der Anzahl. Große Gruppen sind einzeln
   * einklappbar (ihr Kopf zeigt immer „12 von 40 gewählt“), eine Suche blendet nur aus und
   * ändert keine Auswahl, und die Hauptaktion nennt immer die echte Gesamtzahl.
   */
  let {
    cables = [],
    title = 'Auswahl',
    actionLabel = 'Auswahl übernehmen',
    einheit = 'Enden',
    busy = false,
    getId,
    getName,
    getMeta,
    getBadge,
    getGroup,
    onconfirm,
    oncancel,
    extra,
    confirmDisabled = false,
    sperrGrund = null,
    initialSelected = 'all',
    confirmVariant = 'default',
    isActionable,
    getGroupNote,
    confirmNote = null,
    selectedIds = $bindable(new Set<number>())
  }: {
    cables: T[];
    /** Überschrift des Fensters (ohne Zahlen, die stehen in der Zusammenfassung). */
    title?: string;
    /** Beschriftung der Hauptaktion, z. B. "Abklemmen buchen". */
    actionLabel?: string;
    /** Wie die Einträge heißen, z. B. "Enden". */
    einheit?: string;
    /** Aktion läuft gerade, Knopf gesperrt. */
    busy?: boolean;
    getId: (c: T) => number;
    getName: (c: T) => string;
    /** Optionale Zusatzangabe im Eintrag, z. B. Kabel-Nr und Typ. */
    getMeta?: (c: T) => string | null;
    /** Optionales Kurzzeichen je Eintrag, z. B. die Seite. */
    getBadge?: (c: T) => string | null;
    /** Gruppierung, z. B. Rack · Gerät. */
    getGroup: (c: T) => string;
    /** Liefert die gewählten IDs an den Aufrufer. */
    onconfirm: (ids: number[]) => void;
    oncancel: () => void;
    /** Optionaler Zusatzbereich zwischen Liste und Fußzeile im selben Fenster. */
    extra?: Snippet;
    /** Zusätzliche Sperre der Hauptaktion durch den Aufrufer. */
    confirmDisabled?: boolean;
    /** Grund zur Sperre `confirmDisabled`, steht als Satz neben der Hauptaktion. */
    sperrGrund?: string | null;
    /** 'none' für zurücknehmende Aktionen: sie starten nie mit Vollauswahl. */
    initialSelected?: 'all' | 'none';
    /** 'danger' nutzt rote Warnfarben statt des Akzents. */
    confirmVariant?: 'default' | 'danger';
    /** Nimmt dieser Eintrag an der Hauptaktion teil? `{ ok: false, grund }` bleibt wählbar,
     *  zeigt den Grund am Eintrag und wird bei der Hauptaktion weder gezählt noch übergeben. */
    isActionable?: (c: T) => boolean | { ok: boolean; grund?: string };
    /** Optionale Zusatzangabe im Gruppenkopf. */
    getGroupNote?: (groupCables: T[]) => string | null;
    /** Optionaler Zusatz in der Zusammenfassung. */
    confirmNote?: string | null;
    /** Gewählte IDs, optional gebunden (bind:selectedIds). */
    selectedIds?: Set<number>;
  } = $props();

  function bereit(c: T): { ok: boolean; grund?: string } {
    if (!isActionable) return { ok: true };
    const r = isActionable(c);
    return typeof r === 'boolean' ? { ok: r } : r;
  }

  let initialized = $state(false);

  // Suche: blendet nur aus. Die Auswahl hängt an IDs und bleibt, wie sie ist.
  const SUCHE_AB = 9; // darunter sieht man alle Einträge ohnehin auf einen Blick
  let suche = $state('');
  const sucheZeigen = $derived(cables.length >= SUCHE_AB);
  const suchWorte = $derived(sucheZeigen ? suche.toLowerCase().split(/\s+/).filter(Boolean) : []);
  const sucheAktiv = $derived(suchWorte.length > 0);
  function suchText(c: T): string {
    return [getName(c), getMeta?.(c), getBadge?.(c), getGroup(c)].filter(Boolean).join(' ').toLowerCase();
  }
  const sichtbar = $derived(
    sucheAktiv
      ? cables.filter((c) => {
          const t = suchText(c);
          return suchWorte.every((w) => t.includes(w));
        })
      : cables
  );
  // Gewählt, aber von der Suche ausgeblendet.
  const ausgeblendet = $derived.by(() => {
    if (!sucheAktiv) return 0;
    const gezeigt = new Set(sichtbar.map(getId));
    let n = 0;
    for (const c of cables) {
      const id = getId(c);
      if (selectedIds.has(id) && !gezeigt.has(id)) n++;
    }
    return n;
  });
  const suchStand = $derived(
    [
      `${sichtbar.length} von ${cables.length} angezeigt`,
      ausgeblendet > 0 ? `${ausgeblendet} gewählte ausgeblendet, sie bleiben gewählt` : null
    ]
      .filter(Boolean)
      .join(' · ')
  );
  // Die Schalter „Alle …“ wirken nur auf das Angezeigte, dann heißen sie auch so.
  const eingeengt = $derived(sichtbar.length < cables.length);

  // Beim ersten Aufbau alles auswählen (initialSelected === 'all'): der Regelfall ist
  // "alle nehmen". Zurücknehmende Aktionen ('none') starten leer.
  $effect(() => {
    if (cables.length === 0) {
      untrack(() => {
        initialized = false;
      });
    } else if (!initialized) {
      untrack(() => {
        if (selectedIds.size === 0) {
          selectedIds =
            initialSelected === 'all' ? new Set(cables.filter((c) => bereit(c).ok).map(getId)) : new Set();
        }
        initialized = true;
      });
    }
  });

  // Gruppen sortiert (numerisch: "Rack 2" vor "Rack 10"), "Ohne Zuordnung" zuletzt.
  const OHNE = 'Ohne Zuordnung';
  const grouped = $derived.by(() => {
    const groups: Record<string, T[]> = {};
    for (const c of sichtbar) {
      const key = getGroup(c) || OHNE;
      (groups[key] ??= []).push(c);
    }
    const sortiert = Object.keys(groups).sort(
      (a, b) => Number(a === OHNE) - Number(b === OHNE) || a.localeCompare(b, 'de', { numeric: true })
    );
    // Array statt Objekt: ein Objekt zieht ganzzahlige Schlüssel nach vorn.
    return sortiert.map((k) => [k, groups[k]] as [string, T[]]);
  });

  // Große Gruppen einzeln einklappen: es entscheidet die Größe der Gruppe, nicht die Gesamtzahl.
  const GRUPPE_GROSS = 12;
  let klappWahl = $state<Record<string, boolean>>({}); // von Hand gesetzt: true = zu
  const klappbar = $derived(!sucheAktiv && grouped.length > 1);
  function gruppeZu(name: string, anzahl: number): boolean {
    if (!klappbar) return false;
    return klappWahl[name] ?? anzahl > GRUPPE_GROSS;
  }
  function gruppeKlappen(name: string, anzahl: number) {
    klappWahl = { ...klappWahl, [name]: !gruppeZu(name, anzahl) };
  }
  const zuAnzahl = $derived(grouped.filter(([name, eintraege]) => gruppeZu(name, eintraege.length)).length);
  function alleKlappen(zu: boolean) {
    klappWahl = Object.fromEntries(grouped.map(([name]) => [name, zu]));
  }

  function toggleCable(id: number) {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    selectedIds = next;
  }

  const alleGewaehlt = $derived(sichtbar.length > 0 && sichtbar.every((c) => selectedIds.has(getId(c))));

  function toggleAlle() {
    const next = new Set(selectedIds);
    for (const c of sichtbar) {
      if (alleGewaehlt) next.delete(getId(c));
      else next.add(getId(c));
    }
    selectedIds = next;
  }

  // Was die Hauptaktion tatsächlich bekommt: gewählte IDs ohne Einträge, die nicht teilnehmen.
  const bestaetigbar = $derived.by(() => {
    if (!isActionable) return Array.from(selectedIds);
    const nachId = new Map(cables.map((c) => [getId(c), c]));
    return Array.from(selectedIds).filter((id) => {
      const c = nachId.get(id);
      return !c || bereit(c).ok;
    });
  });

  function toggleGroup(groupName: string) {
    const ids = (grouped.find(([name]) => name === groupName)?.[1] ?? []).map(getId);
    const allSelected = ids.every((id) => selectedIds.has(id));
    const next = new Set(selectedIds);
    for (const id of ids) {
      if (allSelected) next.delete(id);
      else next.add(id);
    }
    selectedIds = next;
  }

  const gefahr = $derived(confirmVariant === 'danger');
  const zeileGross = $derived(`${selectedIds.size} ${einheit} gewählt`);
  const zeileKlein = $derived([`von ${cables.length}`, confirmNote].filter(Boolean).join(' · '));
  const gruppenText = (gewaehlt: number, anzahl: number, note: string | null, nichtBereit: number) =>
    [`${gewaehlt} von ${anzahl} gewählt`, note, nichtBereit > 0 ? `${nichtBereit} nicht bereit` : null]
      .filter(Boolean)
      .join(' · ');
  // Grund der Sperre in einem Satz neben der Hauptaktion.
  const sperre = $derived.by(() => {
    if (bestaetigbar.length === 0) return selectedIds.size === 0 ? 'Nichts gewählt.' : 'Kein gewählter Eintrag ist bereit.';
    if (confirmDisabled) return sperrGrund;
    return null;
  });

  const farbeGewaehlt = $derived(gefahr ? 'text-red-400' : 'text-emerald-400');
</script>

<div class="w-full flex flex-col text-left">
  <FensterKopf titel={title} warnung={gefahr} onclose={oncancel}>
    {#snippet rechts()}
      <button
        type="button"
        onclick={toggleAlle}
        disabled={sichtbar.length === 0}
        class="flex items-center gap-2 px-3 min-h-11 rounded-lg border border-[var(--color-border2)] text-sm text-[var(--color-text)] hover:bg-[var(--color-border)] transition disabled:opacity-50"
      >
        {#if alleGewaehlt}
          <Square class="w-4 h-4" /> {eingeengt ? 'Angezeigte abwählen' : 'Alle abwählen'}
        {:else}
          <CheckSquare class="w-4 h-4" /> {eingeengt ? 'Angezeigte auswählen' : 'Alle auswählen'}
        {/if}
      </button>
    {/snippet}
  </FensterKopf>

  <!-- Zusammenfassung: jede Zahl einmal im Fenster. -->
  <div class="flex flex-wrap items-baseline gap-x-3 gap-y-1 px-5 pb-3">
    <p class="m-0 text-2xl font-extrabold tracking-tight text-[var(--color-text)]">{zeileGross}</p>
    <span class="text-sm text-[var(--color-text3)]">{zeileKlein}</span>
  </div>

  <!-- EIN Scrollbereich zwischen Kopf und Fußleiste; die Suchzeile bleibt oben stehen. -->
  <div class="max-h-[55vh] overflow-y-auto bg-[var(--color-bg)] border-t border-[var(--color-border)]" data-testid="auswahl-scroll">
    {#if sucheZeigen}
      <div class="sticky top-0 z-10 flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-[var(--color-border)] bg-[var(--color-bg2)] px-5 py-3">
        <label class="relative flex min-w-[14rem] flex-1 items-center sm:max-w-sm">
          <Search class="pointer-events-none absolute left-3 w-4 h-4 text-[var(--color-text3)]" />
          <input
            type="search"
            bind:value={suche}
            placeholder="Suchen …"
            aria-label="In der Auswahl suchen"
            data-testid="auswahl-suche"
            class="w-full min-h-11 bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg pl-9 pr-3 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]"
          />
        </label>
        {#if sucheAktiv}
          <span class="text-sm text-[var(--color-text2)]" role="status" data-testid="auswahl-suche-stand">{suchStand}</span>
        {:else if grouped.length > 1}
          <button
            type="button"
            onclick={() => alleKlappen(zuAnzahl === 0)}
            class="ml-auto min-h-11 rounded-lg px-3 text-sm font-semibold text-[var(--color-text2)] underline underline-offset-4 hover:bg-[var(--color-border)]"
            data-testid="gruppen-klappen"
          >
            {zuAnzahl === 0 ? 'Alle Gruppen einklappen' : 'Alle Gruppen aufklappen'}
          </button>
        {/if}
      </div>
    {/if}

    <div class="px-5 py-4 space-y-3">
      {#if sucheAktiv && sichtbar.length === 0}
        <div class="flex flex-wrap items-center gap-3 py-4 text-sm text-[var(--color-text2)]" role="status">
          <span>Nichts passt zur Suche „{suche.trim()}“.</span>
          <button
            type="button"
            onclick={() => (suche = '')}
            class="min-h-11 rounded-lg px-3 font-semibold underline underline-offset-4 hover:bg-[var(--color-border)]"
          >
            Suche leeren
          </button>
        </div>
      {/if}
      {#each grouped as [groupName, groupCables] (groupName)}
        {@const groupIds = groupCables.map(getId)}
        {@const gewaehltHier = groupIds.filter((id) => selectedIds.has(id)).length}
        {@const allSelected = gewaehltHier === groupIds.length}
        {@const someSelected = gewaehltHier > 0}
        {@const groupNote = getGroupNote?.(groupCables) ?? null}
        {@const zu = gruppeZu(groupName, groupCables.length)}
        {@const nichtBereit = zu && isActionable ? groupCables.filter((c) => !bereit(c).ok).length : 0}

        <section
          class="bg-[var(--color-bg2)] rounded-xl border border-[var(--color-border)] overflow-hidden"
          data-testid="auswahl-gruppe"
          data-zu={zu ? 'ja' : 'nein'}
          data-auswahl={allSelected ? 'alle' : someSelected ? 'teil' : 'keine'}
        >
          <div class="flex items-stretch {zu ? '' : 'border-b border-[var(--color-border)]'}">
            <button
              type="button"
              onclick={() => toggleGroup(groupName)}
              class="flex-1 min-w-0 min-h-12 flex flex-wrap items-center justify-between gap-x-3 gap-y-1 px-4 py-2 hover:bg-[var(--color-hover)] transition-colors"
              aria-label="{allSelected ? 'Gruppe abwählen' : 'Gruppe wählen'}: {groupName}"
            >
              <span class="flex min-w-0 items-center gap-3">
                <span class={someSelected ? farbeGewaehlt : 'text-[var(--color-text3)]'}>
                  {#if allSelected}
                    <CheckSquare class="w-5 h-5" />
                  {:else if someSelected}
                    <span class="w-5 h-5 rounded-sm flex items-center justify-center {gefahr ? 'bg-red-500/20' : 'bg-emerald-500/20'}">
                      <span class="w-3 h-0.5 bg-current"></span>
                    </span>
                  {:else}
                    <Square class="w-5 h-5" />
                  {/if}
                </span>
                <span class="truncate text-sm font-bold text-[var(--color-text)]">{groupName}</span>
              </span>
              <span class="shrink-0 text-xs font-semibold text-[var(--color-text2)]" data-testid="gruppe-stand">
                {gruppenText(gewaehltHier, groupCables.length, groupNote, nichtBereit)}
              </span>
            </button>
            {#if klappbar}
              <!-- Eigener Knopf: ein Tipp auf den Gruppenkopf wählt die Gruppe an/ab, das
                   Einklappen braucht einen getrennten Tipp (kein Knopf im Knopf). -->
              <button
                type="button"
                onclick={() => gruppeKlappen(groupName, groupCables.length)}
                aria-expanded={!zu}
                aria-label="{zu ? 'Einträge zeigen' : 'Einträge einklappen'}: {groupName}"
                data-testid="gruppe-klappen"
                class="shrink-0 min-w-12 min-h-12 flex items-center justify-center border-l border-[var(--color-border)] text-[var(--color-text2)] hover:bg-[var(--color-hover)] transition-colors"
              >
                {#if zu}<ChevronRight class="w-5 h-5" />{:else}<ChevronDown class="w-5 h-5" />{/if}
              </button>
            {/if}
          </div>

          {#if !zu}
            <ul class="m-0 list-none grid grid-cols-1 sm:grid-cols-2 gap-2 p-3">
              {#each groupCables as cable (getId(cable))}
                {@const cid = getId(cable)}
                {@const isSel = selectedIds.has(cid)}
                {@const w = bereit(cable)}
                {@const meta = getMeta?.(cable) ?? null}
                {@const badge = getBadge?.(cable) ?? null}
                <li data-testid="auswahl-kachel" data-gewaehlt={isSel ? 'ja' : 'nein'}>
                  <button
                    type="button"
                    onclick={() => toggleCable(cid)}
                    aria-pressed={isSel}
                    class="w-full min-h-14 flex items-center gap-3 px-3 py-2 rounded-xl border-2 text-left transition-colors {isSel
                      ? gefahr
                        ? 'border-red-500 bg-red-500/10'
                        : 'border-emerald-500 bg-emerald-500/10'
                      : 'border-[var(--color-border2)] bg-[var(--color-bg2)] hover:bg-[var(--color-hover)]'}"
                  >
                    <span class="shrink-0 {isSel ? farbeGewaehlt : 'text-[var(--color-text3)]'}">
                      {#if isSel}<CheckSquare class="w-6 h-6" />{:else}<Square class="w-6 h-6" />{/if}
                    </span>
                    <span class="flex min-w-0 flex-1 flex-col gap-0.5">
                      <span class="flex min-w-0 items-center gap-2">
                        <span class="font-mono text-sm font-bold truncate min-w-0 text-[var(--color-text)]" title={getName(cable)}>
                          {getName(cable)}
                        </span>
                        {#if badge}
                          <span class="shrink-0 px-2 py-0.5 rounded-full text-[11px] font-semibold border border-[var(--color-border2)] text-[var(--color-text2)]">
                            {badge}
                          </span>
                        {/if}
                      </span>
                      {#if !w.ok && w.grund}
                        <span class="self-start px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/15 text-amber-400">
                          {w.grund}
                        </span>
                      {:else if meta}
                        <span class="min-w-0 truncate text-xs text-[var(--color-text2)]" title={meta}>{meta}</span>
                      {/if}
                    </span>
                  </button>
                </li>
              {/each}
            </ul>
          {/if}
        </section>
      {/each}
    </div>
  </div>

  {#if extra}
    <div class="px-5 py-4 border-t border-[var(--color-border)]">{@render extra()}</div>
  {/if}

  <FensterFuss
    hauptLabel="{actionLabel} · {bestaetigbar.length} {einheit}"
    onhaupt={() => onconfirm([...bestaetigbar])}
    onabbrechen={oncancel}
    gesperrt={!!sperre}
    grund={sperre}
    {busy}
    variante={gefahr ? 'gefahr' : 'standard'}
  />
</div>

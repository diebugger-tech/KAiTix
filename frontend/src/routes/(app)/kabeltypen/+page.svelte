<script lang="ts">
  import { onMount } from 'svelte';
  import { api, KABELTYP_KATEGORIEN, type Kabeltyp, type KabeltypKategorie } from '$lib/api';
  import { Tags, Plus, Pencil, Trash2, X } from '@lucide/svelte';

  type Formular = Omit<Kabeltyp, 'id' | 'standard_farbe'> & { standard_farbe: string };

  const LEERES_FORMULAR: Formular = {
    name: '',
    kategorie: 'kupfer',
    stecker_a: '',
    stecker_b: '',
    enden_a: 1,
    enden_b: 1,
    standard_farbe: '',
    alt_typ: 'sonstige',
    aktiv: true
  };

  let kabeltypen = $state<Kabeltyp[]>([]);
  let loading = $state(true);
  let errorMsg = $state('');

  // Formular: bearbeitetId === null bedeutet "neu anlegen"
  let showForm = $state(false);
  let bearbeitetId = $state<number | null>(null);
  let form = $state<Formular>({ ...LEERES_FORMULAR });
  let formError = $state('');
  let saving = $state(false);

  // alt_typ ist der Wert, der nach cables.typ geschrieben wird. Die erlaubten Werte
  // stehen bereits im Katalog (je bisherigem Typ eine Zeile), daher keine feste Liste hier.
  const altTypOptionen = $derived(
    [...new Set(['sonstige', form.alt_typ, ...kabeltypen.map(k => k.alt_typ)])].sort()
  );

  async function loadData() {
    loading = true;
    errorMsg = '';
    try {
      kabeltypen = await api.getKabeltypen();
    } catch (err) {
      errorMsg = err instanceof Error ? err.message : 'Fehler beim Laden der Kabeltypen.';
    } finally {
      loading = false;
    }
  }

  onMount(loadData);

  function openNeu() {
    bearbeitetId = null;
    form = { ...LEERES_FORMULAR };
    formError = '';
    showForm = true;
  }

  function openBearbeiten(k: Kabeltyp) {
    bearbeitetId = k.id;
    form = {
      name: k.name,
      kategorie: k.kategorie,
      stecker_a: k.stecker_a,
      stecker_b: k.stecker_b,
      enden_a: k.enden_a,
      enden_b: k.enden_b,
      standard_farbe: k.standard_farbe ?? '',
      alt_typ: k.alt_typ,
      aktiv: k.aktiv
    };
    formError = '';
    showForm = true;
  }

  async function handleSubmit(e: SubmitEvent) {
    e.preventDefault();
    saving = true;
    formError = '';
    const payload = {
      ...form,
      name: form.name.trim(),
      stecker_a: form.stecker_a.trim(),
      stecker_b: form.stecker_b.trim(),
      standard_farbe: form.standard_farbe.trim() || null
    };
    try {
      if (bearbeitetId === null) {
        await api.createKabeltyp(payload);
      } else {
        await api.updateKabeltyp(bearbeitetId, payload);
      }
      showForm = false;
      await loadData();
    } catch (err) {
      formError = err instanceof Error ? err.message : 'Speichern fehlgeschlagen.';
    } finally {
      saving = false;
    }
  }

  async function setAktiv(k: Kabeltyp, aktiv: boolean) {
    errorMsg = '';
    try {
      await api.updateKabeltyp(k.id, { aktiv });
      await loadData();
    } catch (err) {
      errorMsg = err instanceof Error ? err.message : 'Ändern fehlgeschlagen.';
    }
  }

  async function handleDelete(k: Kabeltyp) {
    if (!confirm(`Kabeltyp „${k.name}" endgültig löschen?`)) return;
    errorMsg = '';
    try {
      await api.deleteKabeltyp(k.id);
      await loadData();
    } catch (err) {
      // 409: Typ wird noch von Kabeln verwendet. Die API nennt die Anzahl.
      errorMsg = err instanceof Error ? err.message : 'Löschen fehlgeschlagen.';
    }
  }

  const kategorieLabel: Record<KabeltypKategorie, string> = {
    kupfer: 'Kupfer',
    lwl: 'LWL',
    dac: 'DAC',
    aoc: 'AOC',
    breakout: 'Breakout',
    strom: 'Strom',
    sonstige: 'Sonstige'
  };

  const inputClass =
    'w-full min-h-11 bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]';
  const labelClass = 'block text-xs font-semibold text-[var(--color-text2)] mb-1';
</script>

<svelte:head>
  <title>KAiTix - Kabeltypen</title>
</svelte:head>

<div class="space-y-6">
  <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-4">
    <div>
      <h2 class="text-xl font-bold text-[var(--color-text)] font-outfit flex items-center gap-2">
        <Tags class="w-5 h-5 text-emerald-400" />
        Kabeltypen
      </h2>
      <p class="text-xs text-[var(--color-text3)] mt-1">
        {kabeltypen.length} Typen im Katalog · {kabeltypen.filter(k => k.aktiv).length} aktiv.
        Nur aktive Typen stehen in den Kabel-Formularen zur Auswahl.
      </p>
    </div>
    <button
      onclick={openNeu}
      class="flex items-center gap-2 px-4 min-h-11 bg-[#1D9E75] hover:bg-[#0F6E56] text-[var(--color-text)] rounded-lg text-xs font-semibold transition"
    >
      <Plus class="w-4 h-4" />
      <span>Kabeltyp anlegen</span>
    </button>
  </div>

  {#if errorMsg}
    <div role="alert" class="flex items-start justify-between gap-3 bg-red-500/10 border border-red-500/30 text-red-400 rounded-lg px-4 py-3 text-sm">
      <span>{errorMsg}</span>
      <button onclick={() => (errorMsg = '')} aria-label="Meldung schließen" class="shrink-0 hover:text-red-300"><X class="w-4 h-4" /></button>
    </div>
  {/if}

  {#if loading}
    <p class="text-sm text-[var(--color-text3)]">Lade Kabeltypen…</p>
  {:else if kabeltypen.length === 0}
    <p class="text-sm text-[var(--color-text3)]">Noch keine Kabeltypen im Katalog.</p>
  {:else}
    <div class="overflow-x-auto bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl">
      <table class="w-full text-sm">
        <thead>
          <tr class="text-left text-[10px] uppercase tracking-wider text-[var(--color-text3)] font-mono border-b border-[var(--color-border)]">
            <th class="px-4 py-3">Name</th>
            <th class="px-4 py-3">Kategorie</th>
            <th class="px-4 py-3">Stecker A → B</th>
            <th class="px-4 py-3">Enden A / B</th>
            <th class="px-4 py-3">Standardfarbe</th>
            <th class="px-4 py-3">Typ in Exporten</th>
            <th class="px-4 py-3">Status</th>
            <th class="px-4 py-3 text-right">Aktionen</th>
          </tr>
        </thead>
        <tbody>
          {#each kabeltypen as k (k.id)}
            <tr class="border-b border-[var(--color-border)] last:border-0 {k.aktiv ? '' : 'opacity-60'}">
              <td class="px-4 py-2 font-medium text-[var(--color-text)]">{k.name}</td>
              <td class="px-4 py-2 text-[var(--color-text2)]">{kategorieLabel[k.kategorie] ?? k.kategorie}</td>
              <td class="px-4 py-2 text-[var(--color-text2)] font-mono text-xs">{k.stecker_a} → {k.stecker_b}</td>
              <td class="px-4 py-2 text-[var(--color-text2)] font-mono text-xs">{k.enden_a} / {k.enden_b}</td>
              <td class="px-4 py-2 text-[var(--color-text2)]">{k.standard_farbe || '—'}</td>
              <td class="px-4 py-2 text-[var(--color-text2)] font-mono text-xs">{k.alt_typ}</td>
              <td class="px-4 py-2">
                <span class="text-[10px] px-2 py-0.5 rounded border {k.aktiv ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' : 'bg-[var(--color-border)] text-[var(--color-text3)] border-[var(--color-border2)]'}">
                  {k.aktiv ? 'aktiv' : 'deaktiviert'}
                </span>
              </td>
              <td class="px-4 py-2">
                <div class="flex items-center justify-end gap-1">
                  <button
                    onclick={() => setAktiv(k, !k.aktiv)}
                    class="px-3 min-h-11 rounded-lg text-xs text-[var(--color-text2)] hover:bg-[var(--color-border)] transition"
                  >
                    {k.aktiv ? 'Deaktivieren' : 'Aktivieren'}
                  </button>
                  <button
                    onclick={() => openBearbeiten(k)}
                    aria-label="{k.name} bearbeiten"
                    title="Bearbeiten"
                    class="min-w-11 min-h-11 flex items-center justify-center rounded-lg text-[var(--color-text2)] hover:bg-[var(--color-border)] transition"
                  >
                    <Pencil class="w-4 h-4" />
                  </button>
                  <button
                    onclick={() => handleDelete(k)}
                    aria-label="{k.name} löschen"
                    title="Löschen"
                    class="min-w-11 min-h-11 flex items-center justify-center rounded-lg text-red-400 hover:bg-red-500/10 transition"
                  >
                    <Trash2 class="w-4 h-4" />
                  </button>
                </div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>

{#if showForm}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-6 max-w-lg w-full shadow-2xl overflow-y-auto max-h-[90vh]">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-bold text-[var(--color-text)] font-outfit">
        {bearbeitetId === null ? 'Kabeltyp anlegen' : 'Kabeltyp bearbeiten'}
      </h3>
      <button onclick={() => (showForm = false)} aria-label="Schließen" class="text-[var(--color-text2)] hover:text-[var(--color-text)] transition"><X class="w-5 h-5" /></button>
    </div>
    <form onsubmit={handleSubmit} class="space-y-4">
      <div>
        <label for="kt-name" class={labelClass}>Name *</label>
        <input id="kt-name" type="text" bind:value={form.name} required maxlength="100" placeholder="z. B. Breakout QSFP28→4×SFP28" class={inputClass} />
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label for="kt-kategorie" class={labelClass}>Kategorie *</label>
          <select id="kt-kategorie" bind:value={form.kategorie} class={inputClass}>
            {#each KABELTYP_KATEGORIEN as kat}<option value={kat}>{kategorieLabel[kat]}</option>{/each}
          </select>
        </div>
        <div>
          <label for="kt-farbe" class={labelClass}>Standardfarbe</label>
          <input id="kt-farbe" type="text" bind:value={form.standard_farbe} maxlength="30" placeholder="z. B. Blau" class={inputClass} />
        </div>
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label for="kt-stecker-a" class={labelClass}>Stecker A *</label>
          <input id="kt-stecker-a" type="text" bind:value={form.stecker_a} required maxlength="50" placeholder="z. B. QSFP28" class={inputClass} />
        </div>
        <div>
          <label for="kt-stecker-b" class={labelClass}>Stecker B *</label>
          <input id="kt-stecker-b" type="text" bind:value={form.stecker_b} required maxlength="50" placeholder="z. B. SFP28" class={inputClass} />
        </div>
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label for="kt-enden-a" class={labelClass}>Enden Seite A *</label>
          <input id="kt-enden-a" type="number" min="1" max="64" step="1" bind:value={form.enden_a} required class={inputClass} />
        </div>
        <div>
          <label for="kt-enden-b" class={labelClass}>Enden Seite B *</label>
          <input id="kt-enden-b" type="number" min="1" max="64" step="1" bind:value={form.enden_b} required class={inputClass} />
        </div>
      </div>
      <div>
        <label for="kt-alt-typ" class={labelClass}>Typ in Exporten, Farbregeln und Simulation *</label>
        <select id="kt-alt-typ" bind:value={form.alt_typ} class={inputClass}>
          {#each altTypOptionen as t}<option value={t}>{t}</option>{/each}
        </select>
        <p class="text-[11px] text-[var(--color-text3)] mt-1">
          Dieser Wert wird an jedem Kabel dieses Typs gespeichert. Er lässt sich nicht mehr ändern, sobald Kabel den Typ verwenden.
        </p>
      </div>
      <label class="flex items-center gap-3 min-h-11 text-sm text-[var(--color-text)]">
        <input type="checkbox" bind:checked={form.aktiv} class="w-5 h-5" />
        Aktiv (in den Kabel-Formularen wählbar)
      </label>

      {#if formError}
        <p role="alert" class="text-sm text-red-400">{formError}</p>
      {/if}

      <div class="flex justify-end gap-3 pt-2">
        <button type="button" onclick={() => (showForm = false)} class="px-4 min-h-11 rounded-lg text-sm text-[var(--color-text2)] hover:bg-[var(--color-border)] transition">Abbrechen</button>
        <button type="submit" disabled={saving} class="px-4 min-h-11 bg-[#1D9E75] hover:bg-[#0F6E56] disabled:opacity-50 text-[var(--color-text)] rounded-lg text-sm font-semibold transition">
          {saving ? 'Speichert…' : 'Speichern'}
        </button>
      </div>
    </form>
  </div>
</div>
{/if}

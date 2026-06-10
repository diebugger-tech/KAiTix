<script lang="ts">
  import { untrack } from 'svelte';
  import { X } from '@lucide/svelte';
  import { locationStore } from '$lib/locations.svelte';

  import type { Rack, HardwareType } from '$lib/api';

  interface Props {
    show?: boolean;
    onSave: (data: Partial<Rack>) => Promise<void> | void;
    onClose?: () => void;
    initialData?: Rack | null;
    hardwareTypes?: HardwareType[];
    existingReihen?: string[];
    showRemark?: boolean;
    defaultStandort?: string;
    defaultRackreihe?: string;
  }

  let {
    show = $bindable(false),
    onSave,
    onClose = undefined,
    initialData = null,
    hardwareTypes = [],
    showRemark = false,
    defaultStandort = '',
    defaultRackreihe = '',
  }: Props = $props();

  // Internal form state
  let selectedRackHWId = $state<number | null>(null);
  let name = $state('');
  let standort = $state(defaultStandort || '');
  let rackreihe = $state(defaultRackreihe || '');
  let hoehe_u = $state(42); // will be overridden by defaultHeight in $effect
  let breite_mm = $state(600);
  let bemerkung = $state('');
  let cooling_capacity_w = $state<number | null>(null);
  let namePlaceholder = $state('z.B. RACK-01');

  let availableReihen = $derived(
    locationStore.locations.find(l => l.name === standort)?.reihen || []
  );

  // React to initialData (when modal opens or when initialData changes)
  $effect(() => {
    if (show) {
      untrack(() => {
        if (initialData) {
          name = initialData.name || '';
          standort = initialData.standort || '';
          rackreihe = initialData.rackreihe || '';
          hoehe_u = initialData.hoehe_u || defaultHeight;
          breite_mm = initialData.breite_mm || 600;
          bemerkung = initialData.bemerkung || '';
          cooling_capacity_w = initialData.cooling_capacity_w || null;
          selectedRackHWId = initialData.hardware_type_id || null;
        } else {
          // Reset for addition
          name = '';
          standort = defaultStandort || locationStore.locations[0]?.name || 'Serverraum 1';
          rackreihe = defaultRackreihe || '';
          hoehe_u = defaultHeight;
          breite_mm = 600;
          bemerkung = '';
          cooling_capacity_w = null;
          selectedRackHWId = null;
        }
      });
    }
  });

  // Reactive hardware selection
  let selectedRackHW = $derived(
    selectedRackHWId ? hardwareTypes.find(h => h.id === selectedRackHWId) : null
  );

  // Distinct sorted rack heights from catalog
  let rackHeights = $derived(
    [...new Set(hardwareTypes.map(h => h.u_hoehe))].sort((a, b) => a - b)
  );
  let defaultHeight = $derived(
    rackHeights.includes(42) ? 42 : (rackHeights[0] || 42)
  );

  $effect(() => {
    if (selectedRackHW) {
      hoehe_u = selectedRackHW.u_hoehe;
      if (selectedRackHW.breite_mm) breite_mm = selectedRackHW.breite_mm;
      const base = selectedRackHW.name.replace(/\s+/g, '-');
      namePlaceholder = base + '-';
    } else {
      namePlaceholder = 'z.B. RACK-01';
    }
  });

  let isStandortValid = $derived(standort.trim().length > 0 && standort.trim().toLowerCase() !== 'alle');
  let isRackreiheValid = $derived(rackreihe.trim().toLowerCase() !== 'alle' && rackreihe.trim().toLowerCase() !== '__all__');
  let isFormValid = $derived(name.trim().length > 0 && isStandortValid && isRackreiheValid);

  async function handleSubmit(e: Event) {
    e.preventDefault();
    if (!isFormValid) return;

    const data: Partial<Rack> = {
      name: name.trim(),
      standort: standort.trim(),
      rackreihe: rackreihe.trim() || undefined,
      hoehe_u: Number(hoehe_u),
      breite_mm: Number(breite_mm),
      bemerkung: bemerkung.trim() || undefined,
      hardware_type_id: selectedRackHWId || undefined,
      cooling_capacity_w: cooling_capacity_w ? Number(cooling_capacity_w) : undefined
    };

    try {
      await onSave(data);
      show = false;
    } catch (err) {
      alert('Fehler beim Speichern: ' + (err instanceof Error ? err.message : String(err)));
    }
  }

  function handleClose() {
    show = false;
    if (onClose) onClose();
  }
</script>

{#if show}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-6 max-w-sm w-full shadow-2xl">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-bold text-[var(--color-text)] font-outfit">
        {initialData ? 'Rack bearbeiten' : 'Rack hinzufügen'}
      </h3>
      <button onclick={handleClose} type="button">
        <X class="w-5 h-5 text-[var(--color-text3)]" />
      </button>
    </div>
    <form onsubmit={handleSubmit} class="space-y-4">
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Rack-Modell (Vorlage)</label>
        <select bind:value={selectedRackHWId}
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]">
          <option value={null}>Manuelle Eingabe</option>
          {#each hardwareTypes as hwItem}
            <option value={hwItem.id}>{hwItem.hersteller} {hwItem.modell} ({hwItem.u_hoehe}HE)</option>
          {/each}
        </select>
      </div>
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Bezeichnung *</label>
        <input type="text" bind:value={name} required placeholder={namePlaceholder}
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
      </div>
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Standort *</label>
        <select bind:value={standort} required
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]">
          <option value="" disabled selected>Standort wählen...</option>
          {#if standort && standort !== '__ALL__' && !locationStore.locations.some(l => l.name === standort)}
            <option value={standort}>{standort}</option>
          {/if}
          {#each locationStore.locations as loc}
            {#if loc.name !== '__ALL__'}
              <option value={loc.name}>{loc.name}</option>
            {/if}
          {/each}
        </select>
        {#if standort.trim().toLowerCase() === 'alle'}
          <p class="text-red-400 text-xs mt-1">"Alle" ist ein reservierter Filter-Wert.</p>
        {/if}
      </div>
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Rackreihe</label>
        <div class="flex gap-1.5">
          <select bind:value={rackreihe}
            class="flex-1 bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]">
            <option value="">-- Keine / Bitte wählen --</option>
            {#each availableReihen as r}
              <option value={r}>{r}</option>
            {/each}
          </select>
          <button type="button" onclick={() => {
            const nr = prompt('Neue Rackreihe für diesen Standort (z.B. Kaltgang 1):');
            if (nr && nr.trim()) {
              if (nr.trim().toLowerCase() === 'alle' || nr.trim() === '__ALL__') {
                alert('"Alle" ist ein reservierter Begriff und kann nicht verwendet werden.');
                return;
              }
              locationStore.addReihe(standort, nr);
              rackreihe = nr.trim();
            }
          }} class="px-3 bg-[var(--color-bg3)] border border-[var(--color-border2)] hover:border-[#1D9E75] hover:text-[#1D9E75] text-[var(--color-text3)] rounded-lg transition flex items-center justify-center" title="Neue Reihe anlegen">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>
          </button>
        </div>
      </div>
      
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Max. Kühlleistung (Watt)</label>
        <input type="number" bind:value={cooling_capacity_w} min="0" placeholder="z.B. 10000"
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
        <p class="text-[10px] text-[var(--color-text3)] mt-1">Gibt die maximale Abwärme (TDP) an, die dieses Rack abführen kann.</p>
      </div>

      {#if selectedRackHWId !== null}
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Höheneinheiten</label>
        <div class="w-full bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-lg px-4 py-2 text-sm text-[var(--color-text3)]">{hoehe_u} HE</div>
      </div>
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Breite (mm)</label>
        <div class="w-full bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-lg px-4 py-2 text-sm text-[var(--color-text3)]">{breite_mm} mm</div>
      </div>
      {:else}
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Höheneinheiten</label>
        <select bind:value={hoehe_u}
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]">
          {#each rackHeights as h}
            <option value={h}>{h} HE</option>
          {/each}
        </select>
      </div>
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Breite (mm)</label>
        <select bind:value={breite_mm}
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]">
          <option value={600}>600 mm (Standard)</option>
          <option value={800}>800 mm (Breit)</option>
        </select>
      </div>
      {/if}
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Bemerkung</label>
        <textarea bind:value={bemerkung} rows="2"
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75] resize-none"></textarea>
      </div>
      <div class="flex justify-end space-x-3 pt-2">
        <button type="button" onclick={handleClose} class="px-4 py-2 text-sm text-[var(--color-text2)] hover:bg-[var(--color-border)] rounded-lg transition">Abbrechen</button>
        <button type="submit" disabled={!isFormValid} class="px-4 py-2 bg-[#1D9E75] hover:bg-[#0F6E56] text-[var(--color-text)] rounded-lg text-sm font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed">Speichern</button>
      </div>
    </form>
  </div>
</div>
{/if}

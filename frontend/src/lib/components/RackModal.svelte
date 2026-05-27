<script>
  import { X } from '@lucide/svelte';
  import { locationStore } from '$lib/locations.svelte';

  let {
    show = $bindable(false),
    onSave,
    onClose = undefined,
    initialData = null,
    hardwareTypes = [],
    showRemark = false,
    defaultStandort = '',
    defaultRackreihe = '',
  } = $props();

  // Internal form state
  let selectedRackHWId = $state(null);
  let name = $state('');
  let standort = $state(defaultStandort || locationStore.locations[0]?.name || 'Serverraum 1');
  let rackreihe = $state(defaultRackreihe || '');
  let hoehe_u = $state(42); // will be overridden by defaultHeight in $effect
  let breite_mm = $state(600);
  let bemerkung = $state('');
  let namePlaceholder = $state('z.B. RACK-01');

  // React to initialData (when modal opens or when initialData changes)
  $effect(() => {
    if (show) {
      if (initialData) {
        name = initialData.name || '';
        standort = initialData.standort || locationStore.locations[0]?.name || 'Serverraum 1';
        rackreihe = initialData.rackreihe || '';
        hoehe_u = initialData.hoehe_u || defaultHeight;
        breite_mm = initialData.breite_mm || 600;
        bemerkung = initialData.bemerkung || '';
        selectedRackHWId = initialData.hardware_type_id || null;
      } else {
        // Reset for addition
        name = '';
        standort = defaultStandort || locationStore.locations[0]?.name || 'Serverraum 1';
        rackreihe = defaultRackreihe || '';
        hoehe_u = defaultHeight;
        breite_mm = 600;
        bemerkung = '';
        selectedRackHWId = null;
      }
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

  async function handleSubmit(e) {
    e.preventDefault();
    if (!name.trim()) return;

    const data = {
      name: name.trim(),
      standort: standort.trim(),
      rackreihe: rackreihe.trim() || null,
      hoehe_u: Number(hoehe_u),
      breite_mm: Number(breite_mm),
      bemerkung: bemerkung.trim() || null,
      hardware_type_id: selectedRackHWId || null,
      hersteller: selectedRackHW ? selectedRackHW.hersteller : null,
      modell: selectedRackHW ? selectedRackHW.modell : null
    };

    try {
      await onSave(data);
      show = false;
    } catch (err) {
      alert('Fehler beim Speichern: ' + err.message);
    }
  }

  function handleClose() {
    show = false;
    if (onClose) onClose();
  }
</script>

{#if show}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[#131615] border border-slate-800 rounded-xl p-6 max-w-sm w-full shadow-2xl">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-bold text-white font-outfit">
        {initialData ? 'Rack bearbeiten' : 'Rack hinzufügen'}
      </h3>
      <button onclick={handleClose} type="button">
        <X class="w-5 h-5 text-slate-500" />
      </button>
    </div>
    <form onsubmit={handleSubmit} class="space-y-4">
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Rack-Modell (Vorlage)</label>
        <select bind:value={selectedRackHWId}
          class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]">
          <option value={null}>Manuelle Eingabe</option>
          {#each hardwareTypes as hwItem}
            <option value={hwItem.id}>{hwItem.hersteller} {hwItem.modell} ({hwItem.u_hoehe}HE)</option>
          {/each}
        </select>
      </div>
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Bezeichnung *</label>
        <input type="text" bind:value={name} required placeholder={namePlaceholder}
          class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]" />
      </div>
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Standort</label>
        <select bind:value={standort}
          class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]">
          {#if standort && !locationStore.locations.some(l => l.name === standort)}
            <option value={standort}>{standort}</option>
          {/if}
          {#each locationStore.locations as loc}
            <option value={loc.name}>{loc.name}</option>
          {/each}
        </select>
      </div>
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Rackreihe (Optional)</label>
        <input type="text" bind:value={rackreihe} placeholder="z.B. Kaltgang 1"
          class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]" />
      </div>
      {#if selectedRackHWId !== null}
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Höheneinheiten</label>
        <div class="w-full bg-[#141b27] border border-slate-800 rounded-lg px-4 py-2 text-sm text-slate-500">{hoehe_u} HE</div>
      </div>
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Breite (mm)</label>
        <div class="w-full bg-[#141b27] border border-slate-800 rounded-lg px-4 py-2 text-sm text-slate-500">{breite_mm} mm</div>
      </div>
      {:else}
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Höheneinheiten</label>
        <select bind:value={hoehe_u}
          class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]">
          {#each rackHeights as h}
            <option value={h}>{h} HE</option>
          {/each}
        </select>
      </div>
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Breite (mm)</label>
        <select bind:value={breite_mm}
          class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]">
          <option value={600}>600 mm (Standard)</option>
          <option value={800}>800 mm (Breit)</option>
        </select>
      </div>
      {/if}
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Bemerkung</label>
        <textarea bind:value={bemerkung} rows="2"
          class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75] resize-none"></textarea>
      </div>
      <div class="flex justify-end space-x-3 pt-2">
        <button type="button" onclick={handleClose} class="px-4 py-2 text-sm text-slate-400 hover:bg-slate-800 rounded-lg transition">Abbrechen</button>
        <button type="submit" class="px-4 py-2 bg-[#1D9E75] hover:bg-[#0F6E56] text-white rounded-lg text-sm font-semibold transition">Speichern</button>
      </div>
    </form>
  </div>
</div>
{/if}

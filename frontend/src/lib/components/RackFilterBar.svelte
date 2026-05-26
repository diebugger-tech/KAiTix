<script lang="ts">
  import type { Rack } from '$lib/api';

  interface Props {
    racks: Rack[];
    selectedStandort?: string;
    selectedRackreihe?: string;
    selectedRack?: string | number | null;
    layout?: 'horizontal' | 'vertical';
  }

  let {
    racks = [],
    selectedStandort = $bindable('Alle'),
    selectedRackreihe = $bindable('Alle'),
    selectedRack = $bindable('Alle'),
    layout = 'horizontal'
  }: Props = $props();

  // Extract unique sorted standort names
  let standorte = $derived(
    [...new Set(racks.map(r => r.standort).filter(Boolean))].sort()
  );

  // Extract unique sorted rackreihe names for the selected standort
  let rackreihen = $derived(
    selectedStandort !== 'Alle'
      ? [...new Set(racks.filter(r => r.standort === selectedStandort && r.rackreihe).map(r => r.rackreihe))].sort()
      : []
  );

  // Filtered list of racks based on chosen location and row
  let filteredRacks = $derived.by(() => {
    let list = [...racks];
    if (selectedStandort !== 'Alle') {
      list = list.filter(r => r.standort === selectedStandort);
    }
    if (selectedRackreihe !== 'Alle') {
      list = list.filter(r => r.rackreihe === selectedRackreihe);
    }
    return list.sort((a, b) => a.name.localeCompare(b.name));
  });

  // Cascade reset logic via $effects to handle changes dynamically
  $effect(() => {
    if (selectedStandort === 'Alle') {
      if (selectedRackreihe !== 'Alle') {
        selectedRackreihe = 'Alle';
      }
    } else {
      if (selectedRackreihe !== 'Alle' && !rackreihen.includes(selectedRackreihe)) {
        selectedRackreihe = 'Alle';
      }
    }
  });

  $effect(() => {
    if (selectedRack !== 'Alle' && selectedRack !== null && selectedRack !== undefined) {
      const isValid = filteredRacks.some(r => r.id === selectedRack || String(r.id) === String(selectedRack));
      if (!isValid) {
        selectedRack = 'Alle';
      }
    }
  });

  function handleStandortChange() {
    selectedRackreihe = 'Alle';
    selectedRack = 'Alle';
  }

  function handleReiheChange() {
    selectedRack = 'Alle';
  }
</script>

{#if layout === 'vertical'}
  <div class="space-y-3">
    <!-- Standort -->
    <div>
      <label class="block text-[9px] uppercase font-bold tracking-wider text-slate-500 mb-1">Standort</label>
      <select
        bind:value={selectedStandort}
        onchange={handleStandortChange}
        class="w-full bg-[#182030] border border-slate-700 hover:border-slate-600 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500 transition"
      >
        <option value="Alle">Alle Standorte</option>
        {#each standorte as s}
          <option value={s}>{s}</option>
        {/each}
      </select>
    </div>

    <!-- Rackreihe (only if Standort is selected and rows exist) -->
    {#if selectedStandort !== 'Alle' && rackreihen.length > 0}
      <div>
        <label class="block text-[9px] uppercase font-bold tracking-wider text-slate-500 mb-1">Reihe</label>
        <select
          bind:value={selectedRackreihe}
          onchange={handleReiheChange}
          class="w-full bg-[#182030] border border-slate-700 hover:border-slate-600 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500 transition"
        >
          <option value="Alle">Alle Reihen</option>
          {#each rackreihen as r}
            <option value={r}>{r}</option>
          {/each}
        </select>
      </div>
    {/if}

    <!-- Rack -->
    <div>
      <label class="block text-[9px] uppercase font-bold tracking-wider text-slate-500 mb-1">Rack</label>
      <select
        bind:value={selectedRack}
        class="w-full bg-[#182030] border border-slate-700 hover:border-slate-600 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500 transition"
      >
        <option value="Alle">Alle Racks</option>
        {#each filteredRacks as rack}
          <option value={rack.id}>{rack.name}</option>
        {/each}
      </select>
    </div>
  </div>
{:else}
  <!-- Horizontal layout (for Topology / Netzplan toolbars) -->
  <div class="flex items-center gap-3 flex-wrap">
    <!-- Standort -->
    <div class="flex items-center gap-2">
      <span class="text-[10px] uppercase font-bold tracking-wider text-slate-500 shrink-0">Standort</span>
      <select
        bind:value={selectedStandort}
        onchange={handleStandortChange}
        class="bg-[#182030] border border-slate-700 hover:border-slate-600 rounded-lg px-2.5 py-1 text-xs text-white focus:outline-none focus:border-blue-500 transition"
      >
        <option value="Alle">Alle</option>
        {#each standorte as s}
          <option value={s}>{s}</option>
        {/each}
      </select>
    </div>

    <!-- Rackreihe (only if Standort is selected and rows exist) -->
    {#if selectedStandort !== 'Alle' && rackreihen.length > 0}
      <div class="flex items-center gap-2 border-l border-slate-800 pl-3">
        <span class="text-[10px] uppercase font-bold tracking-wider text-slate-500 shrink-0">Reihe</span>
        <select
          bind:value={selectedRackreihe}
          onchange={handleReiheChange}
          class="bg-[#182030] border border-slate-700 hover:border-slate-600 rounded-lg px-2.5 py-1 text-xs text-white focus:outline-none focus:border-blue-500 transition"
        >
          <option value="Alle">Alle</option>
          {#each rackreihen as r}
            <option value={r}>{r}</option>
          {/each}
        </select>
      </div>
    {/if}

    <!-- Rack -->
    <div class="flex items-center gap-2 border-l border-slate-800 pl-3">
      <span class="text-[10px] uppercase font-bold tracking-wider text-slate-500 shrink-0">Rack</span>
      <select
        bind:value={selectedRack}
        class="bg-[#182030] border border-slate-700 hover:border-slate-600 rounded-lg px-2.5 py-1 text-xs text-white focus:outline-none focus:border-blue-500 transition"
      >
        <option value="Alle">Alle</option>
        {#each filteredRacks as rack}
          <option value={rack.id}>{rack.name}</option>
        {/each}
      </select>
    </div>
  </div>
{/if}

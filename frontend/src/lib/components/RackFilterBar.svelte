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

  // Extract unique sorted rackreihe names for all standort/reihe combinations
  let allCombinations = $derived.by(() => {
    const list: Array<{ standort: string; rackreihe: string; label: string; value: string }> = [];
    const seen = new Set<string>();
    for (const r of racks) {
      if (r.standort && r.rackreihe) {
        const key = `${r.standort} || ${r.rackreihe}`;
        if (!seen.has(key)) {
          seen.add(key);
          list.push({
            standort: r.standort,
            rackreihe: r.rackreihe,
            label: `${r.standort} / ${r.rackreihe}`,
            value: key
          });
        }
      }
    }
    return list.sort((a, b) => a.label.localeCompare(b.label));
  });

  // Extract unique sorted rackreihe names for the selected standort
  let singleStandortRows = $derived(
    selectedStandort !== 'Alle'
      ? [...new Set(racks.filter(r => r.standort === selectedStandort && r.rackreihe).map(r => r.rackreihe))].sort()
      : []
  );

  // Determine row list based on standort selection
  let reiheList = $derived.by(() => {
    if (selectedStandort === 'Alle') {
      return allCombinations;
    } else {
      return singleStandortRows.map(r => ({
        standort: selectedStandort,
        rackreihe: r,
        label: r,
        value: r
      }));
    }
  });

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
      if (selectedRackreihe !== 'Alle' && !selectedRackreihe.includes(' || ')) {
        selectedRackreihe = 'Alle';
      }
    } else {
      const validRows = singleStandortRows;
      if (selectedRackreihe !== 'Alle' && !validRows.includes(selectedRackreihe)) {
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

  function handleReiheChange(e: Event) {
    const val = (e.target as HTMLSelectElement).value;
    if (val === 'Alle') {
      selectedRackreihe = 'Alle';
    } else if (val.includes(' || ')) {
      const [standort, reihe] = val.split(' || ');
      selectedStandort = standort;
      selectedRackreihe = reihe;
    } else {
      selectedRackreihe = val;
    }
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
        class="w-full bg-[#181C1A] border border-slate-700 hover:border-slate-600 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-[#1D9E75] disabled:opacity-50 transition"
      >
        <option value="Alle">Alle Standorte</option>
        {#each standorte as s}
          <option value={s}>{s}</option>
        {/each}
      </select>
    </div>

    <!-- Reihe -->
    <div>
      <label class="block text-[9px] uppercase font-bold tracking-wider text-slate-500 mb-1">Reihe</label>
      <select
        value={selectedRackreihe}
        onchange={handleReiheChange}
        disabled={reiheList.length === 0}
        class="w-full bg-[#181C1A] border border-slate-700 hover:border-slate-600 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-[#1D9E75] disabled:opacity-50 transition"
      >
        <option value="Alle">Alle Reihen</option>
        {#each reiheList as r}
          <option value={r.value}>{r.label}</option>
        {/each}
      </select>
    </div>

    <!-- Rack -->
    <div>
      <label class="block text-[9px] uppercase font-bold tracking-wider text-slate-500 mb-1">Rack</label>
      <select
        bind:value={selectedRack}
        disabled={filteredRacks.length === 0}
        class="w-full bg-[#181C1A] border border-slate-700 hover:border-slate-600 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-[#1D9E75] disabled:opacity-50 transition"
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
        class="bg-[#181C1A] border border-slate-700 hover:border-slate-600 rounded-lg px-2.5 py-1 text-xs text-white focus:outline-none focus:border-[#1D9E75] disabled:opacity-50 transition"
      >
        <option value="Alle">Alle</option>
        {#each standorte as s}
          <option value={s}>{s}</option>
        {/each}
      </select>
    </div>

    <!-- Reihe -->
    <div class="flex items-center gap-2 border-l border-slate-800 pl-3">
      <span class="text-[10px] uppercase font-bold tracking-wider text-slate-500 shrink-0">Reihe</span>
      <select
        value={selectedRackreihe}
        onchange={handleReiheChange}
        disabled={reiheList.length === 0}
        class="bg-[#181C1A] border border-slate-700 hover:border-slate-600 rounded-lg px-2.5 py-1 text-xs text-white focus:outline-none focus:border-[#1D9E75] disabled:opacity-50 transition"
      >
        <option value="Alle">Alle</option>
        {#each reiheList as r}
          <option value={r.value}>{r.label}</option>
        {/each}
      </select>
    </div>

    <!-- Rack -->
    <div class="flex items-center gap-2 border-l border-slate-800 pl-3">
      <span class="text-[10px] uppercase font-bold tracking-wider text-slate-500 shrink-0">Rack</span>
      <select
        bind:value={selectedRack}
        disabled={filteredRacks.length === 0}
        class="bg-[#181C1A] border border-slate-700 hover:border-slate-600 rounded-lg px-2.5 py-1 text-xs text-white focus:outline-none focus:border-[#1D9E75] disabled:opacity-50 transition"
      >
        <option value="Alle">Alle</option>
        {#each filteredRacks as rack}
          <option value={rack.id}>{rack.name}</option>
        {/each}
      </select>
    </div>
  </div>
{/if}

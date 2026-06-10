<script lang="ts">
  import type { Rack } from '$lib/api';
  import { locationStore } from '$lib/locations.svelte';
  import { untrack } from 'svelte';

  interface Props {
    racks: Rack[];
    selectedStandort?: string;
    selectedRackreihe?: string;
    selectedRack?: string | number | null;
    searchQuery?: string;
    layout?: 'horizontal' | 'vertical';
  }

  let {
    racks = [],
    selectedStandort = $bindable('__ALL__'),
    selectedRackreihe = $bindable('__ALL__'),
    selectedRack = $bindable('__ALL__'),
    searchQuery = $bindable(''),
    layout = 'horizontal'
  }: Props = $props();

  // Extract unique sorted standort names
  let standorte = $derived(
    [...new Set([
      ...locationStore.locations.map(l => l.name),
      ...racks.map(r => r.standort).filter(s => Boolean(s) && s !== '__ALL__')
    ])].sort()
  );

  // Extract unique sorted rackreihe names for all standort/reihe combinations
  let allCombinations = $derived.by(() => {
    const list: Array<{ standort: string; rackreihe: string; label: string; value: string }> = [];
    const seen = new Set<string>();
    for (const r of racks) {
      if (r.standort && r.standort !== '__ALL__' && r.rackreihe && r.rackreihe !== '__ALL__') {
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
    selectedStandort !== '__ALL__'
      ? [...new Set(racks.filter(r => r.standort === selectedStandort && r.rackreihe && r.rackreihe !== '__ALL__').map(r => r.rackreihe))].sort()
      : []
  );

  // Determine row list based on standort selection
  let reiheList = $derived.by(() => {
    if (selectedStandort === '__ALL__') {
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
    if (selectedStandort !== '__ALL__') {
      list = list.filter(r => r.standort === selectedStandort);
    }
    if (selectedRackreihe !== '__ALL__') {
      list = list.filter(r => r.rackreihe === selectedRackreihe);
    }
    if (searchQuery) {
      list = list.filter(r => r.name.toLowerCase().includes(searchQuery.toLowerCase()));
    }
    return list.sort((a, b) => a.name.localeCompare(b.name));
  });

  $effect(() => {
    if (racks && racks.length > 0) {
      untrack(() => {
        for (const r of racks) {
          if (r.standort && !locationStore.locations.some(l => l.name === r.standort)) {
            locationStore.add(r.standort, 'rechenzentrum');
          }
        }
      });
    }
  });

  function handleStandortChange(e: Event) {
    selectedStandort = (e.target as HTMLSelectElement).value;
    selectedRackreihe = '__ALL__';
    selectedRack = '__ALL__';
  }

  function handleReiheChange(e: Event) {
    const val = (e.target as HTMLSelectElement).value;
    if (val === '__ALL__') {
      selectedRackreihe = '__ALL__';
    } else if (val.includes(' || ')) {
      const [standort, reihe] = val.split(' || ');
      selectedStandort = standort;
      selectedRackreihe = reihe;
    } else {
      selectedRackreihe = val;
    }
    selectedRack = '__ALL__';
  }

  function handleRackChange(e: Event) {
    selectedRack = (e.target as HTMLSelectElement).value;
  }
</script>

{#if layout === 'vertical'}
  <div class="space-y-3">
    <!-- Standort -->
    <div>
      <label class="block text-[9px] uppercase font-bold tracking-wider text-[var(--color-text3)] mb-1">Standort</label>
      <select
        value={selectedStandort}
        onchange={handleStandortChange}
        class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] hover:border-[var(--color-border2)] rounded-lg px-2.5 py-1.5 text-xs text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75] disabled:opacity-50 transition"
      >
        <option value="__ALL__">Alle</option>
        {#each standorte as s}
          <option value={s}>{s}</option>
        {/each}
      </select>
    </div>

    <!-- Reihe -->
    <div>
      <label class="block text-[9px] uppercase font-bold tracking-wider text-[var(--color-text3)] mb-1">Reihe</label>
      <select
        value={selectedRackreihe}
        onchange={handleReiheChange}
        disabled={reiheList.length === 0}
        class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] hover:border-[var(--color-border2)] rounded-lg px-2.5 py-1.5 text-xs text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75] disabled:opacity-50 transition"
      >
        <option value="__ALL__">Alle</option>
        {#each reiheList as r}
          <option value={r.value}>{r.label}</option>
        {/each}
      </select>
    </div>

    <!-- Rack -->
    <div>
      <label class="block text-[9px] uppercase font-bold tracking-wider text-[var(--color-text3)] mb-1">Rack</label>
      <select
        value={selectedRack?.toString() || '__ALL__'}
        onchange={handleRackChange}
        disabled={filteredRacks.length === 0}
        class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] hover:border-[var(--color-border2)] rounded-lg px-2.5 py-1.5 text-xs text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75] disabled:opacity-50 transition"
      >
        <option value="__ALL__">Alle</option>
        {#each filteredRacks as rack}
          <option value={rack.id?.toString()}>{rack.name}</option>
        {/each}
      </select>
    </div>
  </div>
{:else}
  <!-- Horizontal layout (for Topology / Netzplan toolbars) -->
  <div class="flex items-center gap-3 flex-wrap">
    <!-- Standort -->
    <div class="flex items-center gap-2">
      <span class="text-[10px] uppercase font-bold tracking-wider text-[var(--color-text3)] shrink-0">Standort</span>
      <select
        value={selectedStandort}
        onchange={handleStandortChange}
        class="bg-[var(--color-bg3)] border border-[var(--color-border2)] hover:border-[var(--color-border2)] rounded-lg px-2.5 py-1 text-xs text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75] disabled:opacity-50 transition"
      >
        <option value="__ALL__">Alle</option>
        {#each standorte as s}
          <option value={s}>{s}</option>
        {/each}
      </select>
    </div>

    <!-- Reihe -->
    <div class="flex items-center gap-2 border-l border-[var(--color-border)] pl-3">
      <span class="text-[10px] uppercase font-bold tracking-wider text-[var(--color-text3)] shrink-0">Reihe</span>
      <select
        value={selectedRackreihe}
        onchange={handleReiheChange}
        disabled={reiheList.length === 0}
        class="bg-[var(--color-bg3)] border border-[var(--color-border2)] hover:border-[var(--color-border2)] rounded-lg px-2.5 py-1 text-xs text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75] disabled:opacity-50 transition"
      >
        <option value="__ALL__">Alle</option>
        {#each reiheList as r}
          <option value={r.value}>{r.label}</option>
        {/each}
      </select>
    </div>

    <!-- Rack -->
    <div class="flex items-center gap-2 border-l border-[var(--color-border)] pl-3">
      <span class="text-[10px] uppercase font-bold tracking-wider text-[var(--color-text3)] shrink-0">Rack</span>
      <select
        value={selectedRack?.toString() || '__ALL__'}
        onchange={handleRackChange}
        disabled={filteredRacks.length === 0}
        class="bg-[var(--color-bg3)] border border-[var(--color-border2)] hover:border-[var(--color-border2)] rounded-lg px-2.5 py-1 text-xs text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75] disabled:opacity-50 transition"
      >
        <option value="__ALL__">Alle</option>
        {#each filteredRacks as rack}
          <option value={rack.id?.toString()}>{rack.name}</option>
        {/each}
      </select>
    </div>
  </div>
{/if}

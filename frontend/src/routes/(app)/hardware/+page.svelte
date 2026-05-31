<script lang="ts">
  import { onMount } from 'svelte';
  import { api, type HardwareType } from '$lib/api';
  import { Cpu, Plus, Search, X, Trash2, Edit2, Server, Shield, Database, Zap, Monitor, Plug, Box, Layers, Battery, BatteryCharging } from '@lucide/svelte';

  let items = $state<HardwareType[]>([]);
  let loading = $state(true);
  let errorMsg = $state('');
  let searchQuery = $state('');
  let filterCategory = $state<string>('all');

  // Modal state
  let showModal = $state(false);
  let editMode = $state(false);
  let editId = $state<number | null>(null);

  // Form fields
  let name = $state('');
  let kategorie = $state<HardwareType['kategorie']>('server');
  let hersteller = $state('');
  let modell = $state('');
  let u_hoehe = $state(1);
  let tdp_watt = $state<number | null>(null);
  let psu_count = $state<number | null>(null);
  let psu_nennwatt = $state<number | null>(null);
  let breite_mm = $state<number | null>(null);
  let tiefe_mm = $state<number | null>(null);
  let port_count_rj45 = $state(0);
  let port_count_lwl = $state(0);
  let port_count_sfp = $state(0);
  let leistung_kw = $state<number | null>(null);
  let n1_faehig = $state(false);
  let bemerkung = $state('');

  const categories = [
    { value: 'rack', label: 'Rack', icon: Layers, color: 'text-stone-400 bg-stone-500/10 border-stone-500/30' },
    { value: 'server', label: 'Server', icon: Server, color: 'text-blue-400 bg-blue-500/10 border-[#1D9E75]/30' },
    { value: 'switch', label: 'Netzwerk', icon: Zap, color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30' },
    { value: 'firewall', label: 'Firewall', icon: Shield, color: 'text-red-400 bg-red-500/10 border-red-500/30' },
    { value: 'storage', label: 'Storage', icon: Database, color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30' },
    { value: 'kvm', label: 'KVM', icon: Monitor, color: 'text-fuchsia-400 bg-fuchsia-500/10 border-fuchsia-500/30' },
    { value: 'pdu', label: 'PDU', icon: Plug, color: 'text-orange-400 bg-orange-500/10 border-orange-500/30' },
    { value: 'usv', label: 'USV', icon: Battery, color: 'text-purple-400 bg-purple-500/10 border-purple-500/30' },
    { value: 'usv_modul', label: 'Batterie', icon: BatteryCharging, color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30' },
    { value: 'sonstige', label: 'Sonstige', icon: Box, color: 'text-[var(--color-text2)] bg-[var(--color-border2)] border-[var(--color-border)]' },
  ];

  function getCategoryInfo(cat: string) {
    return categories.find(c => c.value === cat) || categories[categories.length - 1];
  }

  async function loadData() {
    loading = true;
    errorMsg = '';
    try {
      const params = filterCategory !== 'all' ? filterCategory : undefined;
      items = await api.getHardware(params);
    } catch (err: any) {
      errorMsg = err.message || 'Fehler beim Laden.';
    } finally {
      loading = false;
    }
  }

  onMount(() => { loadData(); });

  const filteredItems = $derived(items.filter(i => {
    const q = searchQuery.toLowerCase();
    return i.name.toLowerCase().includes(q) ||
           i.hersteller.toLowerCase().includes(q) ||
           i.modell.toLowerCase().includes(q) ||
           i.bemerkung.toLowerCase().includes(q);
  }));

  function resetForm() {
    name = ''; kategorie = 'server'; hersteller = ''; modell = '';
    u_hoehe = 1; tdp_watt = null; psu_count = null; psu_nennwatt = null;
    breite_mm = null; tiefe_mm = null;
    port_count_rj45 = 0; port_count_lwl = 0; port_count_sfp = 0; bemerkung = '';
    leistung_kw = null; n1_faehig = false;
    editMode = false; editId = null;
  }

  function openAdd() {
    resetForm();
    showModal = true;
  }

  function openEdit(item: HardwareType) {
    resetForm();
    editMode = true;
    editId = item.id;
    name = item.name;
    kategorie = item.kategorie;
    hersteller = item.hersteller;
    modell = item.modell;
    u_hoehe = item.u_hoehe;
    tdp_watt = item.tdp_watt ?? null;
    psu_count = item.psu_count ?? null;
    psu_nennwatt = item.psu_nennwatt ?? null;
    breite_mm = item.breite_mm ?? null;
    tiefe_mm = item.tiefe_mm ?? null;
    port_count_rj45 = item.port_count_rj45;
    port_count_lwl = item.port_count_lwl;
    port_count_sfp = item.port_count_sfp;
    leistung_kw = item.leistung_kw ?? null;
    n1_faehig = item.n1_faehig ?? false;
    bemerkung = item.bemerkung;
    showModal = true;
  }

  async function handleSave(e: SubmitEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    const payload = {
      name: name.trim(),
      kategorie,
      hersteller: hersteller.trim(),
      modell: modell.trim(),
      u_hoehe,
      tdp_watt: tdp_watt ?? undefined,
      psu_count: psu_count ?? undefined,
      psu_nennwatt: psu_nennwatt ?? undefined,
      breite_mm: breite_mm ?? undefined,
      tiefe_mm: tiefe_mm ?? undefined,
      port_count_rj45,
      port_count_lwl,
      port_count_sfp,
      leistung_kw: leistung_kw ?? undefined,
      n1_faehig: kategorie === 'usv_modul' ? n1_faehig : undefined,
      bemerkung: bemerkung.trim()
    };
    try {
      if (editMode && editId) {
        await api.updateHardware(editId, payload);
      } else {
        await api.createHardware(payload);
      }
      showModal = false;
      resetForm();
      await loadData();
    } catch (err: any) {
      alert('Fehler: ' + err.message);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm('Hardware-Typ wirklich löschen?')) return;
    try {
      await api.deleteHardware(id);
      await loadData();
    } catch (err: any) {
      alert('Fehler: ' + err.message);
    }
  }
</script>

<svelte:head><title>KAiTix - Hardware-Katalog</title></svelte:head>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between border-b border-[var(--color-border)] pb-4">
    <div>
      <h2 class="text-xl font-bold text-[var(--color-text)] font-outfit">Hardware-Katalog</h2>
      <p class="text-xs text-[var(--color-text2)]">Verfügbare Komponenten für Rack-Einbau</p>
    </div>
    <button onclick={openAdd}
      class="flex items-center space-x-2 px-4 py-2 bg-purple-600 hover:bg-purple-500 text-[var(--color-text)] rounded-lg text-xs font-semibold transition">
      <Plus class="w-4 h-4" /><span>Hardware hinzufügen</span>
    </button>
  </div>

  <!-- Category Filters -->
  <div class="flex flex-wrap gap-2">
    <button onclick={() => { filterCategory = 'all'; loadData(); }}
      class="px-3 py-1.5 rounded-lg text-xs font-medium transition {filterCategory === 'all' ? 'bg-[var(--color-border2)] text-[var(--color-text)]' : 'bg-[var(--color-bg3)] text-[var(--color-text2)] hover:bg-[var(--color-border)]'}">
      Alle
    </button>
    {#each categories as cat}
      <button onclick={() => { filterCategory = cat.value; loadData(); }}
        class="px-3 py-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1.5 {filterCategory === cat.value ? 'bg-[var(--color-border2)] text-[var(--color-text)]' : 'bg-[var(--color-bg3)] text-[var(--color-text2)] hover:bg-[var(--color-border)]'}">
        <cat.icon class="w-3 h-3" />
        {cat.label}
      </button>
    {/each}
  </div>

  <!-- Search -->
  <div class="relative max-w-md">
    <Search class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text2)]" />
    <input type="text" bind:value={searchQuery} placeholder="Hardware suchen..."
      class="w-full bg-[var(--color-bg3)] border border-[var(--color-border)] rounded-lg pl-9 pr-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-purple-500" />
  </div>

  {#if loading}
    <div class="flex items-center justify-center p-12">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
    </div>
  {:else if errorMsg}
    <div class="p-4 bg-red-950/40 border border-red-800 rounded-xl text-red-400 text-sm">{errorMsg}</div>
  {:else}
    <!-- Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {#each filteredItems as item}
        {@const cat = getCategoryInfo(item.kategorie)}
        <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-5 hover:border-[var(--color-border2)] transition group">
          <div class="flex items-start justify-between mb-3">
            <div class="flex items-center gap-2">
              <div class="p-2 rounded-lg {cat.color}">
                <cat.icon class="w-4 h-4" />
              </div>
              <span class="text-[10px] px-1.5 py-0.5 rounded border {cat.color}">{cat.label}</span>
            </div>
            <div class="flex gap-1 opacity-0 group-hover:opacity-100 transition">
              <button onclick={() => openEdit(item)} class="p-1.5 bg-[var(--color-border)] hover:bg-[var(--color-border2)] rounded text-[var(--color-text2)] transition"><Edit2 class="w-3 h-3" /></button>
              <button onclick={() => handleDelete(item.id)} class="p-1.5 bg-red-950/40 hover:bg-red-900/40 rounded text-red-400 transition"><Trash2 class="w-3 h-3" /></button>
            </div>
          </div>

          <h3 class="font-bold text-[var(--color-text)] text-sm mb-1">{item.name}</h3>
          {#if item.hersteller}
            <p class="text-[11px] text-[var(--color-text2)] mb-3">{item.hersteller}{item.modell ? ' ' + item.modell : ''}</p>
          {/if}

          {#if item.kategorie === 'rack'}
            <div class="grid grid-cols-3 gap-2 text-center">
              <div class="bg-[var(--color-bg3)] rounded-lg p-2">
                <div class="text-[10px] text-[var(--color-text2)]">Höhe</div>
                <div class="text-sm font-bold text-[var(--color-text)]">{item.u_hoehe} HE</div>
              </div>
              <div class="bg-[var(--color-bg3)] rounded-lg p-2">
                <div class="text-[10px] text-[var(--color-text2)]">Breite</div>
                <div class="text-sm font-bold text-[var(--color-text)]">{item.breite_mm ?? '—'} mm</div>
              </div>
              <div class="bg-[var(--color-bg3)] rounded-lg p-2">
                <div class="text-[10px] text-[var(--color-text2)]">Tiefe</div>
                <div class="text-sm font-bold text-[var(--color-text)]">{item.tiefe_mm ?? '—'} mm</div>
              </div>
            </div>
          {:else if item.kategorie === 'pdu'}
            <div class="grid grid-cols-2 gap-2 text-center">
              <div class="bg-[var(--color-bg3)] rounded-lg p-2">
                <div class="text-[10px] text-[var(--color-text2)]">Höhe</div>
                <div class="text-sm font-bold text-[var(--color-text)]">{item.u_hoehe === 0 ? 'Zero-U' : item.u_hoehe + ' HE'}</div>
              </div>
              <div class="bg-[var(--color-bg3)] rounded-lg p-2">
                <div class="text-[10px] text-[var(--color-text2)]">Mind. Rack</div>
                <div class="text-sm font-bold text-[var(--color-text)]">{item.min_rack_hoehe ?? '—'} HE</div>
              </div>
            </div>
          {:else if item.kategorie === 'usv'}
            <div class="grid grid-cols-3 gap-2 text-center">
              <div class="bg-[var(--color-bg3)] rounded-lg p-2">
                <div class="text-[10px] text-[var(--color-text2)]">Leistung</div>
                <div class="text-sm font-bold text-[var(--color-text)]">{item.leistung_kw ?? (item.tdp_watt ? item.tdp_watt / 1000 : '—')} kW</div>
              </div>
              <div class="bg-[var(--color-bg3)] rounded-lg p-2">
                <div class="text-[10px] text-[var(--color-text2)]">Module</div>
                <div class="text-sm font-bold text-[var(--color-text)]">{item.psu_count ?? '—'}× {item.psu_nennwatt ?? '—'} kW</div>
              </div>
              <div class="bg-[var(--color-bg3)] rounded-lg p-2">
                <div class="text-[10px] text-[var(--color-text2)]">Höhe</div>
                <div class="text-sm font-bold text-[var(--color-text)]">{item.u_hoehe === 0 ? 'Schrank' : item.u_hoehe + ' HE'}</div>
              </div>
            </div>
          {:else if item.kategorie === 'usv_modul'}
            <div class="grid grid-cols-3 gap-2 text-center">
              <div class="bg-[var(--color-bg3)] rounded-lg p-2">
                <div class="text-[10px] text-[var(--color-text2)]">Leistung</div>
                <div class="text-sm font-bold text-[var(--color-text)]">{item.leistung_kw ?? '—'} kW</div>
              </div>
              <div class="bg-[var(--color-bg3)] rounded-lg p-2">
                <div class="text-[10px] text-[var(--color-text2)]">Höhe</div>
                <div class="text-sm font-bold text-[var(--color-text)]">{item.u_hoehe} HE</div>
              </div>
              <div class="bg-[var(--color-bg3)] rounded-lg p-2">
                <div class="text-[10px] text-[var(--color-text2)]">Hot-Swap</div>
                <div class="text-sm font-bold {item.n1_faehig ? 'text-emerald-400' : 'text-[var(--color-text2)]'}">{item.n1_faehig ? '✓' : '—'}</div>
              </div>
            </div>
          {:else if item.kategorie === 'switch' || item.kategorie === 'kvm'}
            <div class="grid grid-cols-2 gap-2 text-center">
              <div class="bg-[var(--color-bg3)] rounded-lg p-2">
                <div class="text-[10px] text-[var(--color-text2)]">Höhe</div>
                <div class="text-sm font-bold text-[var(--color-text)]">{item.u_hoehe} HE</div>
              </div>
              <div class="bg-[var(--color-bg3)] rounded-lg p-2">
                <div class="text-[10px] text-[var(--color-text2)]">TDP</div>
                <div class="text-sm font-bold text-[var(--color-text)]">{item.tdp_watt ?? '—'} W</div>
              </div>
            </div>
          {:else}
            <div class="grid grid-cols-3 gap-2 text-center">
              <div class="bg-[var(--color-bg3)] rounded-lg p-2">
                <div class="text-[10px] text-[var(--color-text2)]">Höhe</div>
                <div class="text-sm font-bold text-[var(--color-text)]">{item.u_hoehe} HE</div>
              </div>
              <div class="bg-[var(--color-bg3)] rounded-lg p-2">
                <div class="text-[10px] text-[var(--color-text2)]">TDP</div>
                <div class="text-sm font-bold text-[var(--color-text)]">{item.tdp_watt ?? '—'} W</div>
              </div>
              <div class="bg-[var(--color-bg3)] rounded-lg p-2">
                <div class="text-[10px] text-[var(--color-text2)]">PSU</div>
                <div class="text-sm font-bold text-[var(--color-text)]">{item.psu_count ?? '—'}× {item.psu_nennwatt ?? '—'} W</div>
              </div>
            </div>
          {/if}

          {#if item.bemerkung}
            <p class="text-[10px] text-[var(--color-text3)] mt-3 line-clamp-2">{item.bemerkung}</p>
          {/if}

          <!-- Port breakdown -->
          <div class="flex flex-wrap gap-2 mt-3 text-[10px] text-[var(--color-text2)]">
            {#if item.kategorie === 'usv' && item.psu_count && item.psu_nennwatt}
              {@const n1_kw = (item.psu_count - 1) * item.psu_nennwatt}
              <span class="px-1.5 py-0.5 rounded {item.psu_count > 1 ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30' : 'bg-amber-500/15 text-amber-400 border border-amber-500/30'} font-semibold">
                {item.psu_count > 1 ? '✓ N+1 (' + n1_kw + ' kW)' : '⚠ Kein N+1'}
              </span>
            {/if}
            {#if item.kategorie === 'usv_modul' && item.n1_faehig}
              <span class="px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 font-semibold">Hot-Swap</span>
            {/if}
            {#if item.port_count_rj45 > 0}<span class="px-1.5 py-0.5 rounded bg-[var(--color-bg3)]">RJ45: {item.port_count_rj45}</span>{/if}
            {#if item.port_count_lwl > 0}<span class="px-1.5 py-0.5 rounded bg-[var(--color-bg3)]">LWL: {item.port_count_lwl}</span>{/if}
            {#if item.port_count_sfp > 0}<span class="px-1.5 py-0.5 rounded bg-[var(--color-bg3)]">SFP: {item.port_count_sfp}</span>{/if}
            {#if item.kategorie === 'pdu' && (item.min_rack_hoehe ?? 0) > 0}
              <span class="px-1.5 py-0.5 rounded bg-amber-500/15 border border-amber-500/30 text-amber-400 font-semibold">
                Mind. {item.min_rack_hoehe}HE-Rack
              </span>
            {/if}
          </div>
        </div>
      {:else}
        <div class="col-span-full text-center py-12 text-[var(--color-text2)] text-sm">
          <Cpu class="w-8 h-8 mx-auto mb-2 text-[var(--color-text2)]" />
          Keine Hardware-Typen gefunden.
        </div>
      {/each}
    </div>
  {/if}
</div>

<!-- Modal -->
{#if showModal}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-6 max-w-lg w-full shadow-2xl max-h-[90vh] overflow-y-auto">
    <h3 class="text-lg font-bold text-[var(--color-text)] mb-4 font-outfit">{editMode ? 'Hardware bearbeiten' : 'Hardware hinzufügen'}</h3>
    <form onsubmit={handleSave} class="space-y-4">
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Bezeichnung *</label>
        <input type="text" bind:value={name} required
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-purple-500"
          placeholder="z.B. Dell PowerEdge R740" />
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Kategorie</label>
          <select bind:value={kategorie}
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-purple-500">
            {#each categories as cat}<option value={cat.value}>{cat.label}</option>{/each}
          </select>
        </div>
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Höhe (HE) <span class="text-[var(--color-text3)] font-normal">{u_hoehe === 0 ? '· 0U/seitlich' : ''}</span></label>
          <input type="number" bind:value={u_hoehe} min="0" max="20"
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-purple-500" />
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Hersteller</label>
          <input type="text" bind:value={hersteller}
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-purple-500" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Modell</label>
          <input type="text" bind:value={modell}
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-purple-500" />
        </div>
      </div>

      {#if kategorie === 'rack'}
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Breite (mm)</label>
          <input type="number" bind:value={breite_mm} min="0"
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-purple-500" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Tiefe (mm)</label>
          <input type="number" bind:value={tiefe_mm} min="0"
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-purple-500" />
        </div>
      </div>
      {:else}
      {#if kategorie !== 'pdu'}
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">TDP (W)</label>
        <input type="number" bind:value={tdp_watt}
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-purple-500" />
      </div>
      {/if}

      {#if ['server', 'firewall', 'storage'].includes(kategorie)}
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">PSU Anzahl</label>
          <input type="number" bind:value={psu_count} min="0"
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-purple-500" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">PSU Nennleistung (W)</label>
          <input type="number" bind:value={psu_nennwatt} min="0"
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-purple-500" />
        </div>
      </div>
      {/if}
      {/if}

      {#if kategorie === 'usv' || kategorie === 'usv_modul'}
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">{kategorie === 'usv' ? 'Gesamtleistung' : 'Leistung'} (kW)</label>
        <input type="number" bind:value={leistung_kw} min="0" step="0.1"
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-purple-500" />
      </div>
      {#if kategorie === 'usv_modul'}
      <div class="flex items-center space-x-2">
        <input type="checkbox" id="n1_faehig" bind:checked={n1_faehig}
          class="rounded bg-[var(--color-bg3)] border-[var(--color-border2)] text-purple-600 focus:ring-0 focus:ring-offset-0" />
        <label for="n1_faehig" class="text-xs font-semibold text-[var(--color-text)] select-none cursor-pointer">N+1 fähig (Hot-Swap)</label>
      </div>
      {/if}
      {/if}

      {#if kategorie !== 'rack'}
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Ports</label>
        <div class="grid grid-cols-3 gap-4">
          <div>
            <label class="block text-[10px] text-[var(--color-text2)] mb-1">RJ45</label>
            <input type="number" bind:value={port_count_rj45} min="0"
              class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-purple-500" />
          </div>
          <div>
            <label class="block text-[10px] text-[var(--color-text2)] mb-1">LWL</label>
            <input type="number" bind:value={port_count_lwl} min="0"
              class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-purple-500" />
          </div>
          <div>
            <label class="block text-[10px] text-[var(--color-text2)] mb-1">SFP+</label>
            <input type="number" bind:value={port_count_sfp} min="0"
              class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-purple-500" />
          </div>
        </div>
      </div>
      {/if}

      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Bemerkung</label>
        <textarea bind:value={bemerkung} rows="2"
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-purple-500 resize-none"
          placeholder="Optionale Beschreibung..."></textarea>
      </div>

      <div class="flex justify-end space-x-3 pt-2">
        <button type="button" onclick={() => { showModal = false; resetForm(); }}
          class="px-4 py-2 rounded-lg text-sm text-[var(--color-text2)] hover:bg-[var(--color-border)] transition">Abbrechen</button>
        <button type="submit"
          class="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-[var(--color-text)] rounded-lg text-sm font-semibold transition">Speichern</button>
      </div>
    </form>
  </div>
</div>
{/if}

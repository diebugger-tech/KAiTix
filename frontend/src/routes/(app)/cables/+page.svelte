<script lang="ts">
  import { onMount } from 'svelte';
  import { api, type Cable, type Device } from '$lib/api';
  import {
    Cable as CableIcon,
    Plus,
    Trash2,
    Edit2,
    X,
    Plug,
    Zap,
    Search,
    Download,
    FileSpreadsheet,
    FileText,
    ArrowRightLeft,
    ChevronUp,
    ChevronDown,
    Settings
  } from '@lucide/svelte';

  let cables = $state<Cable[]>([]);
  let devices = $state<Device[]>([]);
  let selectedCable = $state<Cable | null>(null);
  let loading = $state(true);
  let errorMsg = $state('');

  // Trace
  let traceResult = $state<Awaited<ReturnType<typeof api.traceCable>> | null>(null);
  let traceLoading = $state(false);
  let traceError = $state('');

  async function loadTrace(id: number) {
    traceLoading = true;
    traceError = '';
    traceResult = null;
    try {
      traceResult = await api.traceCable(id);
    } catch (e: any) {
      traceError = e.message ?? 'Fehler';
    } finally {
      traceLoading = false;
    }
  }

  // Color Rules Admin
  let colorRules = $state<any[]>([]);
  let showAdmin = $state(false);

  // Filters
  let searchQuery = $state('');
  let filterTyp = $state<string>('all');
  let filterFarbe = $state<string>('all');
  let filterCategory = $state<string>('all');

  const categoryMap: Record<string, string[]> = {
    all: [],
    lwl: ['LC-LC', 'SC-SC', 'SFP+'],
    copper: ['Cat6', 'Cat6A', 'Cat7'],
    power: ['Strom-C13', 'Strom-C13-Lock', 'Strom-C19', 'Strom-C19-Lock', 'Strom-Schuko', 'Strom-CEE-16A-3P', 'Strom-CEE-32A-3P', 'Strom-CEE-63A-3P'],
    dac: ['DAC'],
    sonstige: ['sonstige'],
  };

  // Modals
  let showAddCable = $state(false);
  let showEditCable = $state(false);

  // Form fields
  let kabel_nr = $state('');
  let typ = $state('Cat6A');
  let laenge_m = $state(1.0);
  let farbe = $state('');
  let von_device_id = $state<number | null>(null);
  let von_port = $state('');
  let nach_device_id = $state<number | null>(null);
  let nach_port = $state('');
  let bemerkung = $state('');

  const cableTypes = ['Cat6', 'Cat6A', 'Cat7', 'DAC', 'LC-LC', 'SC-SC', 'SFP+', 'Strom-C13', 'Strom-C13-Lock', 'Strom-C19', 'Strom-C19-Lock', 'Strom-Schuko', 'Strom-CEE-16A-3P', 'Strom-CEE-32A-3P', 'Strom-CEE-63A-3P', 'sonstige'];
  const farben = ['Blau', 'Rot', 'Orange', 'Gelb', 'Erika-Violett', 'Schwarz', 'Grau', 'Grün-Gelb'];

  // Type badge colors
  const typeBadges: Record<string, { bg: string; text: string; border: string }> = {
    'Cat6':        { bg: 'bg-blue-500/10',     text: 'text-blue-400',     border: 'border-[#1D9E75]/30' },
    'Cat6A':       { bg: 'bg-blue-500/10',     text: 'text-blue-400',     border: 'border-[#1D9E75]/30' },
    'Cat7':        { bg: 'bg-blue-500/10',     text: 'text-blue-400',     border: 'border-[#1D9E75]/30' },
    'DAC':         { bg: 'bg-slate-500/10',    text: 'text-slate-400',    border: 'border-slate-500/30' },
    'LC-LC':       { bg: 'bg-fuchsia-500/10',  text: 'text-fuchsia-400',  border: 'border-fuchsia-500/30' },
    'SC-SC':       { bg: 'bg-fuchsia-500/10',  text: 'text-fuchsia-400',  border: 'border-fuchsia-500/30' },
    'SFP+':        { bg: 'bg-cyan-500/10',     text: 'text-cyan-400',     border: 'border-cyan-500/30' },
    'Strom-C13':      { bg: 'bg-red-500/10',    text: 'text-red-400',    border: 'border-red-500/30' },
    'Strom-C13-Lock': { bg: 'bg-orange-500/10', text: 'text-orange-400', border: 'border-orange-500/30' },
    'Strom-C19':      { bg: 'bg-red-500/10',    text: 'text-red-400',    border: 'border-red-500/30' },
    'Strom-C19-Lock': { bg: 'bg-orange-500/10', text: 'text-orange-400', border: 'border-orange-500/30' },
    'Strom-Schuko':   { bg: 'bg-red-500/10',    text: 'text-red-400',    border: 'border-red-500/30' },
    'Strom-CEE-16A-3P':{ bg: 'bg-red-600/10', text: 'text-red-500',   border: 'border-red-600/30' },
    'Strom-CEE-32A-3P':{ bg: 'bg-red-600/10', text: 'text-red-500',   border: 'border-red-600/30' },
    'Strom-CEE-63A-3P':{ bg: 'bg-red-600/10', text: 'text-red-500',   border: 'border-red-600/30' },
    'sonstige':    { bg: 'bg-amber-500/10',    text: 'text-amber-400',    border: 'border-amber-500/30' },
  };

  function getTypeBadge(t: string) {
    return typeBadges[t] ?? typeBadges['sonstige'];
  }

  function getFarbeDotClass(farbe?: string): string {
    if (!farbe) return 'bg-slate-600';
    const f = farbe.toLowerCase();
    if (f.includes('grün-gelb')) return 'bg-lime-500';
    if (f.includes('grün')) return 'bg-green-500';
    if (f.includes('gelb')) return 'bg-yellow-400';
    if (f.includes('rot')) return 'bg-red-500';
    if (f.includes('blau')) return 'bg-blue-500';
    if (f.includes('schwarz')) return 'bg-neutral-900 border border-slate-600';
    if (f.includes('violett') || f.includes('erika')) return 'bg-fuchsia-500';
    if (f.includes('grau')) return 'bg-gray-400';
    if (f.includes('orange')) return 'bg-orange-500';
    return 'bg-slate-500';
  }

  function getDeviceName(id?: number | null): string {
    if (!id) return '—';
    const d = devices.find(d => d.id === id);
    return d?.hostname || `#${id}`;
  }

  // Derived filter values
  const usedFarben = $derived(
    [...new Set(cables.map(c => c.farbe).filter(Boolean))] as string[]
  );

  const filteredCables = $derived(
    cables.filter(c => {
      const q = searchQuery.toLowerCase();
      const matchesSearch = !q ||
        c.kabel_nr.toLowerCase().includes(q) ||
        c.typ.toLowerCase().includes(q) ||
        (c.farbe?.toLowerCase() ?? '').includes(q) ||
        (c.von_port?.toLowerCase() ?? '').includes(q) ||
        (c.nach_port?.toLowerCase() ?? '').includes(q) ||
        getDeviceName(c.von_device_id).toLowerCase().includes(q) ||
        getDeviceName(c.nach_device_id).toLowerCase().includes(q);
      const matchesTyp = filterTyp === 'all' || c.typ === filterTyp;
      const matchesFarbe = filterFarbe === 'all' || c.farbe === filterFarbe;
      const matchesCategory = filterCategory === 'all' || categoryMap[filterCategory]?.includes(c.typ);
      return matchesSearch && matchesTyp && matchesFarbe && matchesCategory;
    })
  );

  const pduDevices = $derived(devices.filter(d => d.typ === 'pdu'));

  async function loadData() {
    loading = true;
    errorMsg = '';
    try {
      const [cablesData, devicesData, rulesData] = await Promise.all([
        api.getCables(),
        api.getDevices(),
        api.getColorRules().catch(() => ({ rules: [] }))
      ]);
      cables = cablesData;
      devices = devicesData;
      colorRules = rulesData.rules || [];

      if (cablesData.length > 0 && !selectedCable) {
        selectedCable = cablesData[0];
      } else if (selectedCable) {
        const refreshed = cablesData.find(c => c.id === selectedCable!.id);
        selectedCable = refreshed || cablesData[0] || null;
      }
    } catch (err: any) {
      errorMsg = err.message || 'Fehler beim Laden der Kabelliste.';
    } finally {
      loading = false;
    }
  }

  onMount(loadData);

  async function suggestColorForTyp(newTyp: string) {
    try {
      const res = await api.suggestCableColor(newTyp);
      if (res.suggested_color) {
        farbe = res.suggested_color;
      }
    } catch {
      // ignore
    }
  }

  function resetForm() {
    kabel_nr = '';
    typ = 'Cat6A';
    laenge_m = 1.0;
    farbe = '';
    von_device_id = null;
    von_port = '';
    nach_device_id = null;
    nach_port = '';
    bemerkung = '';
  }

  function openEditModal() {
    if (!selectedCable) return;
    kabel_nr = selectedCable.kabel_nr;
    typ = selectedCable.typ;
    laenge_m = selectedCable.laenge_m;
    farbe = selectedCable.farbe || '';
    von_device_id = selectedCable.von_device_id || null;
    von_port = selectedCable.von_port || '';
    nach_device_id = selectedCable.nach_device_id || null;
    nach_port = selectedCable.nach_port || '';
    bemerkung = selectedCable.bemerkung || '';
    showEditCable = true;
  }

  async function handleAddCable(e: SubmitEvent) {
    e.preventDefault();
    if (!kabel_nr.trim()) return;
    try {
      await api.createCable({
        kabel_nr: kabel_nr.trim(),
        typ,
        laenge_m,
        farbe: farbe || undefined,
        von_device_id: von_device_id || undefined,
        von_port: von_port || undefined,
        nach_device_id: nach_device_id || undefined,
        nach_port: nach_port || undefined,
        bemerkung: bemerkung || undefined
      });
      showAddCable = false;
      resetForm();
      await loadData();
    } catch (err: any) {
      alert('Fehler beim Hinzufügen: ' + err.message);
    }
  }

  async function handleEditCable(e: SubmitEvent) {
    e.preventDefault();
    if (!selectedCable || !kabel_nr.trim()) return;
    try {
      await api.updateCable(selectedCable.id, {
        kabel_nr: kabel_nr.trim(),
        typ,
        laenge_m,
        farbe: farbe || undefined,
        von_device_id: von_device_id || undefined,
        von_port: von_port || undefined,
        nach_device_id: nach_device_id || undefined,
        nach_port: nach_port || undefined,
        bemerkung: bemerkung || undefined
      });
      showEditCable = false;
      resetForm();
      await loadData();
    } catch (err: any) {
      alert('Fehler beim Aktualisieren: ' + err.message);
    }
  }

  async function handleDeleteCable(id: number) {
    if (!confirm('Kabel wirklich löschen?')) return;
    try {
      await api.deleteCable(id);
      if (selectedCable?.id === id) selectedCable = null;
      await loadData();
    } catch (err: any) {
      alert('Fehler beim Löschen: ' + err.message);
    }
  }

  function exportUrl(fmt: string) {
    return `/api/v1/export/cables?format=${fmt}`;
  }
</script>

<svelte:head>
  <title>KAiTix - Kabelliste</title>
</svelte:head>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
    <div>
      <h2 class="text-xl font-bold text-white font-outfit flex items-center gap-2">
        <CableIcon class="w-5 h-5 text-emerald-400" />
        Kabelliste
      </h2>
      <p class="text-xs text-slate-500 mt-1">
        {cables.length} Kabel im System
        {#if filteredCables.length !== cables.length}· {filteredCables.length} angezeigt{/if}
      </p>
    </div>
    <div class="flex items-center gap-2">
      <a href={exportUrl('xlsx')} class="flex items-center gap-2 px-3 py-2 bg-emerald-600/20 text-emerald-400 border border-emerald-600/30 rounded-lg text-xs font-medium hover:bg-emerald-600/30 transition">
        <FileSpreadsheet class="w-4 h-4" />
        <span class="hidden sm:inline">Excel</span>
      </a>
      <a href={exportUrl('csv')} class="flex items-center gap-2 px-3 py-2 bg-slate-800 text-slate-300 border border-slate-700 rounded-lg text-xs font-medium hover:bg-slate-700 transition">
        <FileText class="w-4 h-4" />
        <span class="hidden sm:inline">CSV</span>
      </a>
      <button
        onclick={() => { resetForm(); showAddCable = true; }}
        class="flex items-center gap-2 px-4 py-2 bg-[#1D9E75] hover:bg-[#0F6E56] text-white rounded-lg text-xs font-semibold transition"
      >
        <Plus class="w-4 h-4" />
        <span>Kabel hinzufügen</span>
      </button>
    </div>
  </div>

  {#if loading}
    <div class="flex items-center justify-center p-12 bg-[#131615] border border-slate-800 rounded-xl">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-[#1D9E75]"></div>
    </div>
  {:else if errorMsg}
    <div class="p-4 bg-red-950/40 border border-red-800 rounded-xl text-red-400 text-sm">{errorMsg}</div>
  {:else}
    <!-- Filters -->
    <div class="bg-[#131615] border border-slate-800 rounded-xl p-4 grid grid-cols-1 sm:grid-cols-3 gap-4 items-center">
      <div class="relative">
        <Search class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
        <input
          type="text"
          bind:value={searchQuery}
          placeholder="Kabel-Nr, Port, Gerät suchen..."
          class="w-full bg-[#181C1A] border border-slate-800 rounded-lg pl-9 pr-4 py-2 text-xs text-white focus:outline-none focus:border-[#1D9E75]"
        />
      </div>
      <div class="flex items-center gap-2">
        <label for="filter-typ" class="text-[10px] uppercase font-bold tracking-wider text-slate-500 font-mono">Typ</label>
        <select id="filter-typ" bind:value={filterTyp}
          class="flex-1 bg-[#181C1A] border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-[#1D9E75]">
          <option value="all">Alle</option>
          {#each cableTypes as t}<option value={t}>{t}</option>{/each}
        </select>
      </div>
      <div class="flex items-center gap-2">
        <label for="filter-farbe" class="text-[10px] uppercase font-bold tracking-wider text-slate-500 font-mono">Farbe</label>
        <select id="filter-farbe" bind:value={filterFarbe}
          class="flex-1 bg-[#181C1A] border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-[#1D9E75]">
          <option value="all">Alle</option>
          {#each farben as f}<option value={f}>{f}</option>{/each}
        </select>
      </div>
    </div>

    <!-- Category Quick Filters -->
    <div class="flex flex-wrap gap-2 mt-3">
      {#each [{k:'all',l:'Alle'},{k:'lwl',l:'LWL'},{k:'copper',l:'Kupfer'},{k:'power',l:'Strom'},{k:'dac',l:'DAC'},{k:'sonstige',l:'Sonstige'}] as item}
        <button
          onclick={() => { filterCategory = item.k; filterTyp = 'all'; }}
          class="px-3 py-1.5 rounded-lg text-xs font-medium border transition {filterCategory === item.k ? 'bg-emerald-600/20 text-emerald-400 border-emerald-600/40' : 'bg-[#131615] text-slate-400 border-slate-700 hover:bg-slate-800 hover:text-slate-200'}"
        >
          {item.l}
        </button>
      {/each}
    </div>

    <!-- Split-View -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- Cable List -->
      <div class="space-y-3">
        <h3 class="text-xs font-bold text-slate-500 uppercase tracking-wider">Kabel ({filteredCables.length})</h3>
        <div class="space-y-2 max-h-[calc(100vh-380px)] overflow-y-auto pr-1">
          {#each filteredCables as cable}
            {@const active = selectedCable?.id === cable.id}
            <button
              onclick={() => { selectedCable = cable; traceResult = null; traceError = ''; }}
              class="w-full text-left p-3 rounded-xl border transition flex items-center gap-3 {
                active
                  ? 'bg-[#1D9E75]/10 border-[#1D9E75]/50 text-white'
                  : 'bg-[#131615] border-slate-800/80 text-slate-400 hover:border-slate-700'
              }"
            >
              <div class="p-2 rounded-lg {
                active ? 'bg-blue-500/20 text-blue-400'
                  : cable.typ.startsWith('Strom') ? 'bg-red-500/10 text-red-400'
                  : cable.typ === 'DAC' ? 'bg-slate-500/10 text-slate-400'
                  : cable.typ.startsWith('Cat') ? 'bg-blue-500/10 text-blue-400'
                  : cable.typ === 'LC-LC' || cable.typ === 'SC-SC' ? 'bg-fuchsia-500/10 text-fuchsia-400'
                  : 'bg-amber-500/10 text-amber-400'
              }">
                {#if cable.typ.startsWith('Strom')}
                  <Zap class="w-4 h-4" />
                {:else if cable.typ === 'DAC'}
                  <Plug class="w-4 h-4" />
                {:else}
                  <CableIcon class="w-4 h-4" />
                {/if}
              </div>
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-2">
                  <span class="font-mono text-xs font-bold {active ? 'text-white' : 'text-slate-200'}">{cable.kabel_nr}</span>
                  {#if cable.farbe}
                    <div class="w-2.5 h-2.5 rounded-full {getFarbeDotClass(cable.farbe)}" title={cable.farbe}></div>
                  {/if}
                </div>
                <div class="flex items-center gap-2 mt-0.5">
                  <span class="text-[10px] px-1.5 py-0.5 rounded border {getTypeBadge(cable.typ).bg} {getTypeBadge(cable.typ).text} {getTypeBadge(cable.typ).border}">{cable.typ}</span>
                  <span class="text-[10px] text-slate-500">{cable.laenge_m}m</span>
                </div>
              </div>
            </button>
          {/each}
        </div>
      </div>

      <!-- Detail View -->
      <div class="lg:col-span-2">
        {#if !selectedCable}
          <div class="p-12 text-center bg-[#131615] border border-slate-800 rounded-xl text-slate-500">
            Bitte wählen Sie ein Kabel aus der Liste aus.
          </div>
        {:else}
          <div class="bg-[#131615] border border-slate-800 rounded-xl p-6 space-y-6">
            <!-- Header -->
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
              <div>
                <div class="flex items-center gap-3">
                  <h3 class="text-lg font-bold text-white font-outfit font-mono">{selectedCable.kabel_nr}</h3>
                  <span class="text-xs px-2 py-0.5 rounded border {getTypeBadge(selectedCable.typ).bg} {getTypeBadge(selectedCable.typ).text} {getTypeBadge(selectedCable.typ).border}">
                    {selectedCable.typ}
                  </span>
                  {#if selectedCable.farbe}
                    <div class="flex items-center gap-1.5">
                      <div class="w-3 h-3 rounded-full {getFarbeDotClass(selectedCable.farbe)}"></div>
                      <span class="text-xs text-slate-400">{selectedCable.farbe}</span>
                    </div>
                  {/if}
                </div>
                <p class="text-xs text-slate-500 mt-1">{selectedCable.laenge_m} Meter</p>
              </div>
              <div class="flex items-center gap-2">
                <button
                  onclick={() => loadTrace(selectedCable!.id)}
                  disabled={traceLoading}
                  class="px-3 py-1.5 bg-violet-600/20 hover:bg-violet-600/30 border border-violet-600/30 text-violet-400 rounded-lg text-xs font-medium transition disabled:opacity-40"
                  title="Kabelpfad verfolgen"
                >
                  {traceLoading ? '…' : 'Trace'}
                </button>
                <button onclick={openEditModal} class="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition" title="Kabel bearbeiten">
                  <Edit2 class="w-4 h-4" />
                </button>
                <button onclick={() => handleDeleteCable(selectedCable!.id)} class="p-2 bg-red-950/40 hover:bg-red-900/40 border border-red-900/60 text-red-400 rounded-lg transition" title="Kabel löschen">
                  <Trash2 class="w-4 h-4" />
                </button>
              </div>
            </div>

            <!-- Connection Details -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <!-- Von -->
              <div class="bg-slate-900/50 border border-slate-800 rounded-xl p-4 space-y-3">
                <div class="text-[10px] text-slate-500 uppercase font-bold tracking-wider font-mono">Von</div>
                <div class="space-y-1">
                  <div class="text-sm font-bold text-white">{getDeviceName(selectedCable.von_device_id)}</div>
                  {#if selectedCable.von_port}
                    <div class="flex items-center gap-1.5 text-xs text-slate-400">
                      <Plug class="w-3 h-3" />
                      <span class="font-mono">{selectedCable.von_port}</span>
                    </div>
                  {/if}
                </div>
              </div>

              <!-- Nach -->
              <div class="bg-slate-900/50 border border-slate-800 rounded-xl p-4 space-y-3">
                <div class="text-[10px] text-slate-500 uppercase font-bold tracking-wider font-mono">Nach</div>
                <div class="space-y-1">
                  <div class="text-sm font-bold text-white">{getDeviceName(selectedCable.nach_device_id)}</div>
                  {#if selectedCable.nach_port}
                    <div class="flex items-center gap-1.5 text-xs text-slate-400">
                      <Plug class="w-3 h-3" />
                      <span class="font-mono">{selectedCable.nach_port}</span>
                    </div>
                  {/if}
                </div>
              </div>
            </div>

            <!-- Connection Arrow -->
            <div class="flex items-center justify-center">
              <div class="flex items-center gap-3 text-slate-600">
                <span class="text-xs font-mono">{getDeviceName(selectedCable.von_device_id)}:{selectedCable.von_port || '—'}</span>
                <ArrowRightLeft class="w-4 h-4" />
                <span class="text-xs font-mono">{getDeviceName(selectedCable.nach_device_id)}:{selectedCable.nach_port || '—'}</span>
              </div>
            </div>

            <!-- Metadata -->
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div class="bg-slate-900/50 border border-slate-800 rounded-xl p-4">
                <div class="text-[10px] text-slate-500 uppercase font-bold tracking-wider font-mono">Verlegt am</div>
                <div class="text-sm font-bold text-white mt-0.5">{selectedCable.verlegt_am || '—'}</div>
              </div>
              <div class="bg-slate-900/50 border border-slate-800 rounded-xl p-4">
                <div class="text-[10px] text-slate-500 uppercase font-bold tracking-wider font-mono">Verlegt von</div>
                <div class="text-sm font-bold text-white mt-0.5">{selectedCable.verlegt_von || '—'}</div>
              </div>
              <div class="bg-slate-900/50 border border-slate-800 rounded-xl p-4">
                <div class="text-[10px] text-slate-500 uppercase font-bold tracking-wider font-mono">Bemerkung</div>
                <div class="text-sm text-slate-300 mt-0.5">{selectedCable.bemerkung || '—'}</div>
              </div>
            </div>

            <!-- Trace Panel -->
            {#if traceError}
              <p class="text-xs text-red-400">{traceError}</p>
            {/if}
            {#if traceResult}
              <div class="border border-violet-800/40 rounded-xl overflow-hidden">
                <div class="px-4 py-2.5 border-b border-slate-800 flex items-center justify-between bg-violet-900/10">
                  <span class="text-[10px] uppercase font-bold tracking-wider text-violet-400">Kabelpfad — {traceResult.hops} Kabel</span>
                  <button onclick={() => traceResult = null} class="text-slate-600 hover:text-slate-400 text-xs">✕</button>
                </div>
                <div class="p-3 space-y-1 max-h-64 overflow-y-auto">
                  {#each traceResult.trace as hop, i}
                    {@const isSelected = hop.id === selectedCable?.id}
                    <div class="flex items-center gap-2 text-xs {isSelected ? 'bg-violet-900/20 rounded px-2 py-1 border border-violet-700/30' : 'px-2 py-0.5'}">
                      <span class="text-slate-600 shrink-0 w-4 text-right">{i + 1}</span>
                      <span class="font-mono text-slate-300 shrink-0">{hop.von_device_hostname ?? '?'}</span>
                      {#if hop.von_port}<span class="text-slate-600 font-mono text-[10px]">:{hop.von_port}</span>{/if}
                      <span class="text-slate-700 shrink-0">→</span>
                      <span class="font-mono text-slate-300 shrink-0">{hop.nach_device_hostname ?? '?'}</span>
                      {#if hop.nach_port}<span class="text-slate-600 font-mono text-[10px]">:{hop.nach_port}</span>{/if}
                      <span class="ml-auto text-[10px] text-slate-500 shrink-0">{hop.kabel_nr ?? '—'} · {hop.typ}</span>
                      {#if hop.id !== selectedCable?.id}
                        <button onclick={() => { selectedCable = cables.find(c => c.id === hop.id) ?? selectedCable; traceResult = null; }} class="text-[10px] text-violet-400 hover:text-violet-300 shrink-0">↗</button>
                      {/if}
                    </div>
                    {#if i < traceResult.trace.length - 1}
                      <div class="pl-6 text-slate-800 text-[10px]">│</div>
                    {/if}
                  {/each}
                </div>
              </div>
            {/if}
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>

<!-- Modal: Kabel hinzufügen -->
{#if showAddCable}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[#131615] border border-slate-800 rounded-xl p-6 max-w-lg w-full shadow-2xl overflow-y-auto max-h-[90vh]">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-bold text-white font-outfit">Kabel hinzufügen</h3>
      <button onclick={() => showAddCable = false} class="text-slate-400 hover:text-white transition"><X class="w-5 h-5" /></button>
    </div>
    <form onsubmit={handleAddCable} class="space-y-4">
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Kabel-Nr *</label>
        <input type="text" bind:value={kabel_nr} required placeholder="z.B. KAB-0031"
          class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]" />
      </div>
      <div class="grid grid-cols-3 gap-4">
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Typ *</label>
          <select bind:value={typ} onchange={() => suggestColorForTyp(typ)} class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]">
            {#each cableTypes as t}<option value={t}>{t}</option>{/each}
          </select>
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Länge (m) *</label>
          <input type="number" step="0.01" min="0.1" bind:value={laenge_m} required
            class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Farbe</label>
          <select bind:value={farbe} class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]">
            <option value="">—</option>
            {#each farben as f}<option value={f}>{f}</option>{/each}
          </select>
        </div>
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Von Gerät</label>
          <select bind:value={von_device_id} class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]">
            <option value={null}>—</option>
            {#each devices as d}<option value={d.id}>{d.hostname}</option>{/each}
          </select>
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Von Port</label>
          <input type="text" bind:value={von_port} placeholder="z.B. Eth0"
            class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]" />
        </div>
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Nach Gerät</label>
          <select bind:value={nach_device_id} class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]">
            <option value={null}>—</option>
            {#each devices as d}<option value={d.id}>{d.hostname}</option>{/each}
          </select>
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Nach Port</label>
          <input type="text" bind:value={nach_port} placeholder="z.B. Port 1"
            class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]" />
        </div>
      </div>
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Bemerkung</label>
        <input type="text" bind:value={bemerkung} placeholder="Optional"
          class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]" />
      </div>
      <div class="flex justify-end gap-3 pt-2">
        <button type="button" onclick={() => showAddCable = false} class="px-4 py-2 rounded-lg text-sm text-slate-400 hover:bg-slate-800 transition">Abbrechen</button>
        <button type="submit" class="px-4 py-2 bg-[#1D9E75] hover:bg-[#0F6E56] text-white rounded-lg text-sm font-semibold transition">Speichern</button>
      </div>
    </form>
  </div>
</div>
{/if}

<!-- Modal: Kabel bearbeiten -->
{#if showEditCable}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[#131615] border border-slate-800 rounded-xl p-6 max-w-lg w-full shadow-2xl overflow-y-auto max-h-[90vh]">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-bold text-white font-outfit">Kabel bearbeiten</h3>
      <button onclick={() => showEditCable = false} class="text-slate-400 hover:text-white transition"><X class="w-5 h-5" /></button>
    </div>
    <form onsubmit={handleEditCable} class="space-y-4">
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Kabel-Nr *</label>
        <input type="text" bind:value={kabel_nr} required
          class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]" />
      </div>
      <div class="grid grid-cols-3 gap-4">
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Typ *</label>
          <select bind:value={typ} onchange={() => suggestColorForTyp(typ)} class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]">
            {#each cableTypes as t}<option value={t}>{t}</option>{/each}
          </select>
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Länge (m) *</label>
          <input type="number" step="0.01" min="0.1" bind:value={laenge_m} required
            class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Farbe</label>
          <select bind:value={farbe} class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]">
            <option value="">—</option>
            {#each farben as f}<option value={f}>{f}</option>{/each}
          </select>
        </div>
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Von Gerät</label>
          <select bind:value={von_device_id} class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]">
            <option value={null}>—</option>
            {#each devices as d}<option value={d.id}>{d.hostname}</option>{/each}
          </select>
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Von Port</label>
          <input type="text" bind:value={von_port}
            class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]" />
        </div>
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Nach Gerät</label>
          <select bind:value={nach_device_id} class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]">
            <option value={null}>—</option>
            {#each devices as d}<option value={d.id}>{d.hostname}</option>{/each}
          </select>
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Nach Port</label>
          <input type="text" bind:value={nach_port}
            class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]" />
        </div>
      </div>
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Bemerkung</label>
        <input type="text" bind:value={bemerkung}
          class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]" />
      </div>
      <div class="flex justify-end gap-3 pt-2">
        <button type="button" onclick={() => showEditCable = false} class="px-4 py-2 rounded-lg text-sm text-slate-400 hover:bg-slate-800 transition">Abbrechen</button>
        <button type="submit" class="px-4 py-2 bg-[#1D9E75] hover:bg-[#0F6E56] text-white rounded-lg text-sm font-semibold transition">Speichern</button>
      </div>
    </form>
  </div>
</div>
{/if}

<!-- Admin: Color Rules -->
{#if colorRules.length > 0}
<div class="mt-8 pt-6 border-t border-slate-800">
  <button
    onclick={() => showAdmin = !showAdmin}
    class="flex items-center gap-2 text-xs font-semibold text-slate-500 hover:text-slate-300 transition uppercase tracking-wider"
  >
    <Settings class="w-4 h-4" />
    Farbregeln ({colorRules.length})
    {#if showAdmin}
      <ChevronUp class="w-3 h-3" />
    {:else}
      <ChevronDown class="w-3 h-3" />
    {/if}
  </button>
  {#if showAdmin}
    <div class="mt-3 bg-[#131615] border border-slate-800 rounded-xl overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-xs">
          <thead>
            <tr class="border-b border-slate-800 bg-[#0d111a]">
              <th class="text-left px-4 py-2 text-slate-400 font-semibold">Typ</th>
              <th class="text-left px-4 py-2 text-slate-400 font-semibold">Standard-Farbe</th>
              <th class="text-left px-4 py-2 text-slate-400 font-semibold">Kategorie</th>
              <th class="text-left px-4 py-2 text-slate-400 font-semibold">Verwendung</th>
              <th class="text-left px-4 py-2 text-slate-400 font-semibold">Standard</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800/60">
            {#each colorRules as rule}
              <tr class="hover:bg-slate-800/20">
                <td class="px-4 py-2 text-white font-mono">{rule.typ}</td>
                <td class="px-4 py-2">
                  <div class="flex items-center gap-2">
                    {#if rule.hex}
                      <div class="w-3 h-3 rounded-full" style="background-color: {rule.hex};"></div>
                    {/if}
                    <span class="text-slate-300">{rule.standard_farbe || '—'}</span>
                  </div>
                </td>
                <td class="px-4 py-2 text-slate-400">{rule.kategorie}</td>
                <td class="px-4 py-2 text-slate-400">{rule.verwendungszweck}</td>
                <td class="px-4 py-2 text-slate-500">{rule.standard}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {/if}
</div>
{/if}

<script lang="ts">
  import { onMount } from 'svelte';
  import { api, type Device, type Rack, type PduOutlet, type PduPhaseOverview } from '$lib/api';
  import {
    Zap,
    Plus,
    Trash2,
    Edit2,
    X,
    Plug,
    Search,
    Settings
  } from '@lucide/svelte';

  let pdus = $state<Device[]>([]);
  let racks = $state<Rack[]>([]);
  let selectedPdu = $state<Device | null>(null);
  let outlets = $state<PduOutlet[]>([]);
  let phaseOverview = $state<PduPhaseOverview | null>(null);
  let loading = $state(true);
  let errorMsg = $state('');

  // Filters
  let searchQuery = $state('');
  let filterRack = $state<string>('all');

  // Modals
  let showAddPdu = $state(false);
  let showEditPdu = $state(false);
  let showAddOutlet = $state(false);
  let showEditOutlet = $state(false);
  let editingOutlet = $state<PduOutlet | null>(null);

  // PDU Form fields
  let hostname = $state('');
  let hersteller = $state('');
  let modell = $state('');
  let seriennummer = $state('');
  let rack_id = $state<number | null>(null);
  let u_position = $state(1);
  let u_hoehe = $state(2);
  let strom_typ = $state('3-phasig');
  let spannung_v = $state(400);
  let anschlussleistung_a = $state(32.0);
  let anschluss_stecker = $state('CEE-32A-3P');
  let bemerkung = $state('');

  // Outlet Form fields
  let outlet_name = $state('');
  let outlet_phase = $state<'L1' | 'L2' | 'L3'>('L1');
  let steckdosentyp = $state<'C13' | 'C19' | 'C14' | 'C20' | 'Schuko' | 'CEE-16A'>('C13');
  let max_watt = $state<number | null>(2300);
  let schaltbar = $state(true);
  let connected_device_id = $state<number | null>(null);
  let connected_port = $state('');

  const steckdosentypen = ['C13', 'C19', 'C14', 'C20', 'Schuko', 'CEE-16A'];
  const anschlussTypen = ['1-phasig', '3-phasig'];
  const steckerTypen = ['CEE-16A-3P', 'CEE-32A-3P', 'CEE-63A-3P', 'C20', 'Schuko'];

  // Phase colors
  const phaseColors: Record<string, { bg: string; border: string; text: string; dot: string }> = {
    'L1': { bg: 'bg-blue-500/10', border: 'border-[#1D9E75]/30', text: 'text-blue-400', dot: 'bg-blue-500' },
    'L2': { bg: 'bg-cyan-500/10', border: 'border-cyan-500/30', text: 'text-cyan-400', dot: 'bg-cyan-500' },
    'L3': { bg: 'bg-orange-500/10', border: 'border-orange-500/30', text: 'text-orange-400', dot: 'bg-orange-500' },
  };

  function getPhaseColor(phase?: string) {
    return phaseColors[phase || 'L1'] || phaseColors['L1'];
  }

  function getOutletTypeColor(typ?: string): string {
    if (!typ) return 'bg-[var(--color-border2)] text-[var(--color-text)]';
    if (typ === 'C19' || typ === 'C20') return 'bg-amber-500/20 text-amber-400 border border-amber-500/30';
    if (typ === 'CEE-16A') return 'bg-red-500/20 text-red-400 border border-red-500/30';
    return 'bg-[var(--color-border2)] text-[var(--color-text)] border border-[var(--color-border2)]';
  }

  const filteredPdus = $derived(
    pdus.filter(p => {
      const q = searchQuery.toLowerCase();
      const matchesSearch = !q || p.hostname.toLowerCase().includes(q) || (p.hersteller?.toLowerCase() ?? '').includes(q) || (p.modell?.toLowerCase() ?? '').includes(q);
      const matchesRack = filterRack === 'all' || p.rack_id?.toString() === filterRack;
      return matchesSearch && matchesRack;
    })
  );

  function getRackName(id?: number | null): string {
    if (!id) return '—';
    const rack = racks.find(r => r.id === id);
    if (!rack) return `#${id}`;
    return `${rack.name}${rack.rackreihe ? ` (${rack.rackreihe})` : ''}`;
  }

  async function loadPdus() {
    loading = true;
    errorMsg = '';
    try {
      const [pdusData, racksData] = await Promise.all([
        api.getPdus(),
        api.getRacks()
      ]);
      pdus = pdusData;
      racks = racksData;

      if (pdusData.length > 0 && !selectedPdu) {
        await selectPdu(pdusData[0]);
      } else if (selectedPdu) {
        const refreshed = pdusData.find(p => p.id === selectedPdu!.id);
        if (refreshed) await selectPdu(refreshed);
        else if (pdusData.length > 0) await selectPdu(pdusData[0]);
        else { selectedPdu = null; outlets = []; phaseOverview = null; }
      }
    } catch (err: any) {
      errorMsg = err.message || 'Fehler beim Laden der PDU-Daten.';
    } finally {
      loading = false;
    }
  }

  async function selectPdu(pdu: Device) {
    selectedPdu = pdu;
    try {
      const [outletsData, overview] = await Promise.all([
        api.getPduOutlets(pdu.id),
        api.getPduPhaseOverview(pdu.id)
      ]);
      outlets = outletsData;
      phaseOverview = overview;
    } catch {
      outlets = [];
      phaseOverview = null;
    }
  }

  onMount(loadPdus);

  function resetPduForm() {
    hostname = '';
    hersteller = '';
    modell = '';
    seriennummer = '';
    rack_id = racks.length > 0 ? racks[0].id : null;
    u_position = 1;
    u_hoehe = 2;
    strom_typ = '3-phasig';
    spannung_v = 400;
    anschlussleistung_a = 32.0;
    anschluss_stecker = 'CEE-32A-3P';
    bemerkung = '';
  }

  function resetOutletForm() {
    outlet_name = '';
    outlet_phase = 'L1';
    steckdosentyp = 'C13';
    max_watt = 2300;
    schaltbar = true;
    connected_device_id = null;
    connected_port = '';
  }

  function openEditPdu() {
    if (!selectedPdu) return;
    hostname = selectedPdu.hostname;
    hersteller = selectedPdu.hersteller || '';
    modell = selectedPdu.modell || '';
    seriennummer = selectedPdu.seriennummer || '';
    rack_id = selectedPdu.rack_id || null;
    u_position = selectedPdu.u_position || 1;
    u_hoehe = selectedPdu.u_hoehe || 2;
    strom_typ = (selectedPdu as any).strom_typ || '3-phasig';
    spannung_v = (selectedPdu as any).spannung_v || 400;
    anschlussleistung_a = (selectedPdu as any).anschlussleistung_a || 32.0;
    anschluss_stecker = (selectedPdu as any).anschluss_stecker || 'CEE-32A-3P';
    bemerkung = selectedPdu.bemerkung || '';
    showEditPdu = true;
  }

  function openEditOutlet(outlet: PduOutlet) {
    editingOutlet = outlet;
    outlet_name = outlet.outlet_name;
    outlet_phase = (outlet.phase || 'L1') as any;
    steckdosentyp = outlet.steckdosentyp || 'C13';
    max_watt = outlet.max_watt || 2300;
    schaltbar = outlet.schaltbar;
    connected_device_id = outlet.connected_device_id || null;
    connected_port = outlet.connected_port || '';
    showEditOutlet = true;
  }

  async function handleAddPdu(e: SubmitEvent) {
    e.preventDefault();
    if (!hostname.trim()) return;
    try {
      await api.createPdu({
        hostname: hostname.trim(),
        hersteller, modell, seriennummer, rack_id,
        u_position, u_hoehe, strom_typ, spannung_v,
        anschlussleistung_a, anschluss_stecker, bemerkung
      } as any);
      showAddPdu = false;
      resetPduForm();
      await loadPdus();
    } catch (err: any) {
      alert('Fehler: ' + err.message);
    }
  }

  async function handleEditPdu(e: SubmitEvent) {
    e.preventDefault();
    if (!selectedPdu || !hostname.trim()) return;
    try {
      await api.updatePdu(selectedPdu.id, {
        hostname: hostname.trim(),
        hersteller, modell, seriennummer, rack_id,
        u_position, u_hoehe, strom_typ, spannung_v,
        anschlussleistung_a, anschluss_stecker, bemerkung
      } as any);
      showEditPdu = false;
      resetPduForm();
      await loadPdus();
    } catch (err: any) {
      alert('Fehler: ' + err.message);
    }
  }

  async function handleDeletePdu(id: number) {
    if (!confirm('PDU wirklich löschen? Alle zugehörigen Steckdosen werden ebenfalls gelöscht.')) return;
    try {
      await api.deletePdu(id);
      selectedPdu = null;
      outlets = [];
      phaseOverview = null;
      await loadPdus();
    } catch (err: any) {
      alert('Fehler: ' + err.message);
    }
  }

  async function handleAddOutlet(e: SubmitEvent) {
    e.preventDefault();
    if (!selectedPdu || !outlet_name.trim()) return;
    try {
      await api.createPduOutlet(selectedPdu.id, {
        pdu_id: selectedPdu.id,
        outlet_name: outlet_name.trim(),
        phase: outlet_phase,
        steckdosentyp,
        max_watt: max_watt ?? undefined,
        schaltbar,
        connected_device_id: connected_device_id ?? undefined,
        connected_port
      });
      showAddOutlet = false;
      resetOutletForm();
      await selectPdu(selectedPdu);
    } catch (err: any) {
      alert('Fehler: ' + err.message);
    }
  }

  async function handleEditOutlet(e: SubmitEvent) {
    e.preventDefault();
    if (!selectedPdu || !editingOutlet) return;
    try {
      await api.updatePduOutlet(selectedPdu.id, editingOutlet.id, {
        outlet_name: outlet_name.trim(),
        phase: outlet_phase,
        steckdosentyp,
        max_watt: max_watt ?? undefined,
        schaltbar,
        connected_device_id: connected_device_id ?? undefined,
        connected_port
      });
      showEditOutlet = false;
      editingOutlet = null;
      resetOutletForm();
      await selectPdu(selectedPdu);
    } catch (err: any) {
      alert('Fehler: ' + err.message);
    }
  }

  async function handleDeleteOutlet(outletId: number) {
    if (!selectedPdu || !confirm('Steckdose wirklich löschen?')) return;
    try {
      await api.deletePduOutlet(selectedPdu.id, outletId);
      await selectPdu(selectedPdu);
    } catch (err: any) {
      alert('Fehler: ' + err.message);
    }
  }
</script>

<svelte:head>
  <title>KAiTix - PDU-Verwaltung</title>
</svelte:head>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between border-b border-[var(--color-border)] pb-4">
    <div>
      <h2 class="text-xl font-bold text-[var(--color-text)] font-outfit flex items-center gap-2">
        <Zap class="w-5 h-5 text-amber-400" />
        PDU-Verwaltung
      </h2>
      <p class="text-xs text-[var(--color-text3)] mt-1">Power Distribution Units mit Phasenverteilung dokumentieren</p>
    </div>
    <button onclick={() => { resetPduForm(); showAddPdu = true; }}
      class="flex items-center gap-2 px-4 py-2 bg-[#1D9E75] hover:bg-[#0F6E56] text-[var(--color-text)] rounded-lg text-xs font-semibold transition">
      <Plus class="w-4 h-4" />
      <span>PDU hinzufügen</span>
    </button>
  </div>

  {#if loading}
    <div class="flex items-center justify-center p-12 bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-[#1D9E75]"></div>
    </div>
  {:else if errorMsg}
    <div class="p-4 bg-red-950/40 border border-red-800 rounded-xl text-red-400 text-sm">{errorMsg}</div>
  {:else}
    <!-- Filters -->
    <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-4 grid grid-cols-1 sm:grid-cols-2 gap-4 items-center">
      <div class="relative">
        <Search class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text3)]" />
        <input type="text" bind:value={searchQuery} placeholder="PDU suchen..."
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border)] rounded-lg pl-9 pr-4 py-2 text-xs text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
      </div>
      <div class="flex items-center gap-2">
        <label for="filter-rack" class="text-[10px] uppercase font-bold tracking-wider text-[var(--color-text3)] font-mono">Rack</label>
        <select id="filter-rack" bind:value={filterRack}
          class="flex-1 bg-[var(--color-bg3)] border border-[var(--color-border)] rounded-lg px-3 py-2 text-xs text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]">
          <option value="all">Alle</option>
          {#each racks as rack}<option value={rack.id.toString()}>{rack.name}{rack.rackreihe ? ` (${rack.rackreihe})` : ''}</option>{/each}
        </select>
      </div>
    </div>

    <!-- Split-View -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- PDU List -->
      <div class="space-y-3">
        <h3 class="text-xs font-bold text-[var(--color-text3)] uppercase tracking-wider">PDUs ({filteredPdus.length})</h3>
        <div class="space-y-2 max-h-[calc(100vh-380px)] overflow-y-auto pr-1">
          {#each filteredPdus as pdu}
            {@const active = selectedPdu?.id === pdu.id}
            <button onclick={() => selectPdu(pdu)}
              class="w-full text-left p-3 rounded-xl border transition flex items-center gap-3 {
                active ? 'bg-amber-600/10 border-amber-500/50 text-[var(--color-text)]'
                       : 'bg-[var(--color-bg2)] border-[var(--color-border)]/80 text-[var(--color-text2)] hover:border-[var(--color-border2)]'
              }">
              <div class="p-2 rounded-lg {active ? 'bg-amber-500/20 text-amber-400' : 'bg-amber-500/10 text-amber-400'}">
                <Zap class="w-4 h-4" />
              </div>
              <div class="min-w-0 flex-1">
                <div class="font-bold text-sm truncate {active ? 'text-[var(--color-text)]' : 'text-[var(--color-text)]'}">{pdu.hostname}</div>
                <div class="text-[10px] text-[var(--color-text3)] truncate">
                  {pdu.hersteller || '—'} {pdu.modell || ''} · {getRackName(pdu.rack_id)}
                </div>
              </div>
            </button>
          {/each}
          {#if filteredPdus.length === 0}
            <div class="p-6 text-center text-xs text-[var(--color-text3)] bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl">
              Keine PDUs gefunden.
            </div>
          {/if}
        </div>
      </div>

      <!-- Detail View -->
      <div class="lg:col-span-2">
        {#if !selectedPdu}
          <div class="p-12 text-center bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl text-[var(--color-text3)]">
            Bitte wählen Sie eine PDU aus der Liste.
          </div>
        {:else}
          <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-6 space-y-6">
            <!-- PDU Header -->
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-[var(--color-border)]">
              <div>
                <div class="flex items-center gap-3">
                  <h3 class="text-lg font-bold text-[var(--color-text)] font-outfit">{selectedPdu.hostname}</h3>
                  <span class="text-xs px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">PDU</span>
                </div>
                <div class="flex flex-wrap gap-4 text-xs text-[var(--color-text3)] mt-1">
                  <span>{selectedPdu.hersteller || '—'} {selectedPdu.modell || ''}</span>
                  <span>|</span>
                  <span>Rack: {getRackName(selectedPdu.rack_id)} · HE {selectedPdu.u_position || '—'}-{(selectedPdu.u_position || 1) + (selectedPdu.u_hoehe || 1) - 1}</span>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <button onclick={openEditPdu} class="p-2 bg-[var(--color-border)] hover:bg-[var(--color-border2)] text-[var(--color-text)] rounded-lg transition" title="PDU bearbeiten">
                  <Edit2 class="w-4 h-4" />
                </button>
                <button onclick={() => handleDeletePdu(selectedPdu!.id)} class="p-2 bg-red-950/40 hover:bg-red-900/40 border border-red-900/60 text-red-400 rounded-lg transition" title="PDU löschen">
                  <Trash2 class="w-4 h-4" />
                </button>
              </div>
            </div>

            <!-- PDU Power Info -->
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-4">
                <div class="text-[10px] text-[var(--color-text3)] uppercase font-bold tracking-wider font-mono">Stromtyp</div>
                <div class="text-sm font-bold text-[var(--color-text)] mt-0.5">{(selectedPdu as any).strom_typ || '—'}</div>
              </div>
              <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-4">
                <div class="text-[10px] text-[var(--color-text3)] uppercase font-bold tracking-wider font-mono">Spannung</div>
                <div class="text-sm font-bold text-[var(--color-text)] mt-0.5">{(selectedPdu as any).spannung_v || '—'} V</div>
              </div>
              <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-4">
                <div class="text-[10px] text-[var(--color-text3)] uppercase font-bold tracking-wider font-mono">Absicherung</div>
                <div class="text-sm font-bold text-[var(--color-text)] mt-0.5">{(selectedPdu as any).anschlussleistung_a || '—'} A</div>
              </div>
              <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-4">
                <div class="text-[10px] text-[var(--color-text3)] uppercase font-bold tracking-wider font-mono">Stecker</div>
                <div class="text-sm font-bold text-[var(--color-text)] mt-0.5">{(selectedPdu as any).anschluss_stecker || '—'}</div>
              </div>
            </div>

            <!-- Phase Overview Grid -->
            <div class="space-y-4">
              <div class="flex items-center justify-between">
                <h4 class="text-xs font-bold text-[var(--color-text3)] uppercase tracking-wider font-mono">Phasen-Steckdosen</h4>
                <button onclick={() => { resetOutletForm(); showAddOutlet = true; }}
                  class="flex items-center gap-1.5 px-3 py-1.5 bg-[#1D9E75] hover:bg-[#0F6E56] text-[var(--color-text)] rounded-lg text-[10px] font-semibold transition">
                  <Plus class="w-3 h-3" />
                  Steckdose hinzufügen
                </button>
              </div>

              <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                {#each ['L1', 'L2', 'L3'] as phase}
                  {@const pc = phaseColors[phase]}
                  {@const phaseOutlets = phaseOverview ? phaseOverview[phase as keyof PduPhaseOverview] as PduOutlet[] : []}
                  {@const phaseWatt = phaseOutlets.reduce((sum, o) => sum + (o.max_watt || 0), 0)}
                  <div class="rounded-xl border {pc.border} {pc.bg} p-4 space-y-3">
                    <!-- Phase Header -->
                    <div class="flex items-center justify-between">
                      <div class="flex items-center gap-2">
                        <div class="w-3 h-3 rounded-full {pc.dot}"></div>
                        <span class="text-sm font-bold {pc.text}">{phase}</span>
                      </div>
                      <span class="text-[10px] {pc.text} font-mono">{phaseOutlets.length} Outlets · {phaseWatt}W</span>
                    </div>

                    <!-- Outlets -->
                    <div class="space-y-2">
                      {#if phaseOutlets.length === 0}
                        <div class="p-3 text-center text-[10px] text-[var(--color-text3)] border border-dashed border-[var(--color-border2)] rounded-lg">
                          Keine Steckdosen
                        </div>
                      {:else}
                        {#each phaseOutlets as outlet}
                          <div class="bg-[var(--color-bg2)]/80 border border-[var(--color-border)]/60 rounded-lg p-3 space-y-2">
                            <div class="flex items-center justify-between">
                              <div class="flex items-center gap-2">
                                <Plug class="w-3.5 h-3.5 text-[var(--color-text3)]" />
                                <span class="text-xs font-bold text-[var(--color-text)] font-mono">{outlet.outlet_name}</span>
                              </div>
                              <div class="flex items-center gap-1.5">
                                <span class="text-[9px] px-1.5 py-0.5 rounded {getOutletTypeColor(outlet.steckdosentyp)}">{outlet.steckdosentyp || '—'}</span>
                                {#if outlet.schaltbar}
                                  <span class="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">schaltbar</span>
                                {/if}
                              </div>
                            </div>
                            <div class="text-[10px] text-[var(--color-text3)]">
                              {#if outlet.connected_device}
                                <span class="text-blue-400 font-medium">{outlet.connected_device.hostname}</span>
                                {#if outlet.connected_port}<span class="ml-1">:{outlet.connected_port}</span>{/if}
                              {:else}
                                <span class="italic">frei</span>
                              {/if}
                              {#if outlet.max_watt}
                                <span class="ml-2 text-[var(--color-text3)]">{outlet.max_watt}W</span>
                              {/if}
                            </div>
                            <div class="flex items-center gap-1">
                              <button onclick={() => openEditOutlet(outlet)} class="p-1 hover:bg-[var(--color-border)] rounded transition" title="Bearbeiten">
                                <Edit2 class="w-3 h-3 text-[var(--color-text3)]" />
                              </button>
                              <button onclick={() => handleDeleteOutlet(outlet.id)} class="p-1 hover:bg-red-900/30 rounded transition" title="Löschen">
                                <Trash2 class="w-3 h-3 text-red-500/60" />
                              </button>
                            </div>
                          </div>
                        {/each}
                      {/if}
                    </div>
                  </div>
                {/each}
              </div>

              <!-- Total Summary -->
              {#if phaseOverview}
                <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-4 flex items-center justify-between">
                  <div class="text-xs text-[var(--color-text3)]">
                    <span class="font-bold text-[var(--color-text)]">{phaseOverview.total_outlets}</span> Steckdosen gesamt
                  </div>
                  <div class="text-xs text-[var(--color-text3)]">
                    Max. Leistung: <span class="font-bold text-[var(--color-text)]">{phaseOverview.total_max_watt}W</span>
                    {#if (selectedPdu as any).spannung_v && (selectedPdu as any).anschlussleistung_a}
                      <span class="ml-2 text-[var(--color-text3)]">
                        ({Math.round(phaseOverview.total_max_watt / ((selectedPdu as any).spannung_v * Math.sqrt(3)) * 100) / 100}% Auslastung)
                      </span>
                    {/if}
                  </div>
                </div>
              {/if}
            </div>
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>

<!-- Modal: PDU hinzufügen -->
{#if showAddPdu}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-6 max-w-lg w-full shadow-2xl overflow-y-auto max-h-[90vh]">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-bold text-[var(--color-text)] font-outfit">PDU hinzufügen</h3>
      <button onclick={() => showAddPdu = false} class="text-[var(--color-text2)] hover:text-[var(--color-text)] transition"><X class="w-5 h-5" /></button>
    </div>
    <form onsubmit={handleAddPdu} class="space-y-4">
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Hostname *</label>
        <input type="text" bind:value={hostname} required placeholder="z.B. PDU-A-R01"
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Hersteller</label>
          <input type="text" bind:value={hersteller} placeholder="z.B. Kentix"
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Modell</label>
          <input type="text" bind:value={modell} placeholder="z.B. SmartPDU 42HE"
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
        </div>
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Seriennummer</label>
          <input type="text" bind:value={seriennummer}
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Rack *</label>
          <select bind:value={rack_id} required
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]">
            {#each racks as rack}<option value={rack.id}>{rack.name}{rack.rackreihe ? ` (${rack.rackreihe})` : ''}</option>{/each}
          </select>
        </div>
      </div>
      <div class="grid grid-cols-3 gap-4">
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Start-HE</label>
          <input type="number" bind:value={u_position} min="1" max="47"
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Höhe (HE)</label>
          <input type="number" bind:value={u_hoehe} min="1" max="47"
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Stromtyp</label>
          <select bind:value={strom_typ}
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]">
            {#each anschlussTypen as t}<option value={t}>{t}</option>{/each}
          </select>
        </div>
      </div>
      <div class="grid grid-cols-3 gap-4">
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Spannung (V)</label>
          <input type="number" bind:value={spannung_v}
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Absicherung (A)</label>
          <input type="number" step="0.1" bind:value={anschlussleistung_a}
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Stecker</label>
          <select bind:value={anschluss_stecker}
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]">
            {#each steckerTypen as s}<option value={s}>{s}</option>{/each}
          </select>
        </div>
      </div>
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Bemerkung</label>
        <input type="text" bind:value={bemerkung}
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
      </div>
      <div class="flex justify-end gap-3 pt-2">
        <button type="button" onclick={() => showAddPdu = false} class="px-4 py-2 rounded-lg text-sm text-[var(--color-text2)] hover:bg-[var(--color-border)] transition">Abbrechen</button>
        <button type="submit" class="px-4 py-2 bg-[#1D9E75] hover:bg-[#0F6E56] text-[var(--color-text)] rounded-lg text-sm font-semibold transition">Speichern</button>
      </div>
    </form>
  </div>
</div>
{/if}

<!-- Modal: PDU bearbeiten -->
{#if showEditPdu}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-6 max-w-lg w-full shadow-2xl overflow-y-auto max-h-[90vh]">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-bold text-[var(--color-text)] font-outfit">PDU bearbeiten</h3>
      <button onclick={() => showEditPdu = false} class="text-[var(--color-text2)] hover:text-[var(--color-text)] transition"><X class="w-5 h-5" /></button>
    </div>
    <form onsubmit={handleEditPdu} class="space-y-4">
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Hostname *</label>
        <input type="text" bind:value={hostname} required
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Hersteller</label>
          <input type="text" bind:value={hersteller}
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Modell</label>
          <input type="text" bind:value={modell}
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
        </div>
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Seriennummer</label>
          <input type="text" bind:value={seriennummer}
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Rack *</label>
          <select bind:value={rack_id} required
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]">
            {#each racks as rack}<option value={rack.id}>{rack.name}{rack.rackreihe ? ` (${rack.rackreihe})` : ''}</option>{/each}
          </select>
        </div>
      </div>
      <div class="grid grid-cols-3 gap-4">
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Start-HE</label>
          <input type="number" bind:value={u_position} min="1" max="47"
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Höhe (HE)</label>
          <input type="number" bind:value={u_hoehe} min="1" max="47"
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Stromtyp</label>
          <select bind:value={strom_typ}
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]">
            {#each anschlussTypen as t}<option value={t}>{t}</option>{/each}
          </select>
        </div>
      </div>
      <div class="grid grid-cols-3 gap-4">
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Spannung (V)</label>
          <input type="number" bind:value={spannung_v}
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Absicherung (A)</label>
          <input type="number" step="0.1" bind:value={anschlussleistung_a}
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Stecker</label>
          <select bind:value={anschluss_stecker}
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]">
            {#each steckerTypen as s}<option value={s}>{s}</option>{/each}
          </select>
        </div>
      </div>
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Bemerkung</label>
        <input type="text" bind:value={bemerkung}
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
      </div>
      <div class="flex justify-end gap-3 pt-2">
        <button type="button" onclick={() => showEditPdu = false} class="px-4 py-2 rounded-lg text-sm text-[var(--color-text2)] hover:bg-[var(--color-border)] transition">Abbrechen</button>
        <button type="submit" class="px-4 py-2 bg-[#1D9E75] hover:bg-[#0F6E56] text-[var(--color-text)] rounded-lg text-sm font-semibold transition">Speichern</button>
      </div>
    </form>
  </div>
</div>
{/if}

<!-- Modal: Steckdose hinzufügen -->
{#if showAddOutlet}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-6 max-w-md w-full shadow-2xl">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-bold text-[var(--color-text)] font-outfit">Steckdose hinzufügen</h3>
      <button onclick={() => showAddOutlet = false} class="text-[var(--color-text2)] hover:text-[var(--color-text)] transition"><X class="w-5 h-5" /></button>
    </div>
    <form onsubmit={handleAddOutlet} class="space-y-4">
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Bezeichnung *</label>
        <input type="text" bind:value={outlet_name} required placeholder="z.B. Outlet-1"
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
      </div>
      <div class="grid grid-cols-3 gap-4">
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Phase *</label>
          <select bind:value={outlet_phase}
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]">
            <option value="L1">L1</option>
            <option value="L2">L2</option>
            <option value="L3">L3</option>
          </select>
        </div>
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Typ</label>
          <select bind:value={steckdosentyp}
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]">
            {#each steckdosentypen as t}<option value={t}>{t}</option>{/each}
          </select>
        </div>
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Max. Watt</label>
          <input type="number" bind:value={max_watt}
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
        </div>
      </div>
      <div class="flex items-center gap-3">
        <input type="checkbox" bind:checked={schaltbar} id="schaltbar-add" class="rounded" />
        <label for="schaltbar-add" class="text-xs text-[var(--color-text2)]">inzeln schaltbar</label>
      </div>
      <div class="flex justify-end gap-3 pt-2">
        <button type="button" onclick={() => showAddOutlet = false} class="px-4 py-2 rounded-lg text-sm text-[var(--color-text2)] hover:bg-[var(--color-border)] transition">Abbrechen</button>
        <button type="submit" class="px-4 py-2 bg-[#1D9E75] hover:bg-[#0F6E56] text-[var(--color-text)] rounded-lg text-sm font-semibold transition">Speichern</button>
      </div>
    </form>
  </div>
</div>
{/if}

<!-- Modal: Steckdose bearbeiten -->
{#if showEditOutlet}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-6 max-w-md w-full shadow-2xl">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-bold text-[var(--color-text)] font-outfit">Steckdose bearbeiten</h3>
      <button onclick={() => showEditOutlet = false} class="text-[var(--color-text2)] hover:text-[var(--color-text)] transition"><X class="w-5 h-5" /></button>
    </div>
    <form onsubmit={handleEditOutlet} class="space-y-4">
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Bezeichnung *</label>
        <input type="text" bind:value={outlet_name} required
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
      </div>
      <div class="grid grid-cols-3 gap-4">
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Phase *</label>
          <select bind:value={outlet_phase}
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]">
            <option value="L1">L1</option>
            <option value="L2">L2</option>
            <option value="L3">L3</option>
          </select>
        </div>
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Typ</label>
          <select bind:value={steckdosentyp}
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]">
            {#each steckdosentypen as t}<option value={t}>{t}</option>{/each}
          </select>
        </div>
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Max. Watt</label>
          <input type="number" bind:value={max_watt}
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
        </div>
      </div>
      <div class="flex items-center gap-3">
        <input type="checkbox" bind:checked={schaltbar} id="schaltbar-edit" class="rounded" />
        <label for="schaltbar-edit" class="text-xs text-[var(--color-text2)]">inzeln schaltbar</label>
      </div>
      <div class="flex justify-end gap-3 pt-2">
        <button type="button" onclick={() => showEditOutlet = false} class="px-4 py-2 rounded-lg text-sm text-[var(--color-text2)] hover:bg-[var(--color-border)] transition">Abbrechen</button>
        <button type="submit" class="px-4 py-2 bg-[#1D9E75] hover:bg-[#0F6E56] text-[var(--color-text)] rounded-lg text-sm font-semibold transition">Speichern</button>
      </div>
    </form>
  </div>
</div>
{/if}

<script lang="ts">
  import { onMount } from 'svelte';
  import { api, type Rack, type Device, type Cable, type HardwareType } from '$lib/api';
  import { 
    Server, 
    Layers, 
    Plus, 
    HardDrive, 
    Zap,
    MapPin,
    Building,
    AlertTriangle,
    Info,
    Cable as CableIcon
  } from '@lucide/svelte';
  import RackModal from '$lib/components/RackModal.svelte';

  let racks = $state<Rack[]>([]);
  let devices = $state<Device[]>([]);
  let cables = $state<Cable[]>([]);
  let loading = $state(true);
  let errorMsg = $state('');

  // Add Rack form state
  let showAddRack = $state(false);
  let hardwareTypes = $state<HardwareType[]>([]);

  async function loadData() {
    loading = true;
    errorMsg = '';
    try {
      const [racksData, devicesData, cablesData, hwData] = await Promise.all([
        api.getRacks(),
        api.getDevices(),
        api.getCables().catch(() => [] as Cable[]),
        api.getHardware('rack').catch(() => [] as HardwareType[])
      ]);
      racks = racksData;
      devices = devicesData;
      cables = cablesData;
      hardwareTypes = hwData;
    } catch (err: any) {
      errorMsg = err.message || 'Fehler beim Laden der Daten.';
    } finally {
      loading = false;
    }
  }

  async function handleAddRack(rackData) {
    try {
      await api.createRack(rackData);
      await loadData();
    } catch (err: any) {
      alert('Fehler beim Erstellen des Racks: ' + err.message);
    }
  }

  onMount(() => {
    loadData();
  });

  // Reactive Derived Values
  const totalRacks = $derived(racks.length);
  const totalDevices = $derived(devices.length);
  const totalPowerWatt = $derived(devices.reduce((sum, d) => sum + (Number(d.anschlussleistung_watt ?? d.tdp_watt) || 0), 0));
  const totalCables = $derived(cables.length);
  const cableTypes = $derived(
    [...new Set(cables.map(c => c.typ))].sort()
  );

  const totalL1Kw = $derived(devices.filter(d => d.phase === 'L1').reduce((s, d) => s + (Number(d.anschlussleistung_watt ?? d.tdp_watt) || 0), 0) / 1000);
  const totalL2Kw = $derived(devices.filter(d => d.phase === 'L2').reduce((s, d) => s + (Number(d.anschlussleistung_watt ?? d.tdp_watt) || 0), 0) / 1000);
  const totalL3Kw = $derived(devices.filter(d => d.phase === 'L3').reduce((s, d) => s + (Number(d.anschlussleistung_watt ?? d.tdp_watt) || 0), 0) / 1000);
  const pduDevices = $derived(devices.filter(d => d.phase));

  // Room grouping
  const rooms = $derived(
    [...new Set(racks.map(r => r.standort).filter(Boolean))].sort() as string[]
  );
  const racksWithoutRoom = $derived(racks.filter(r => !r.standort));

  function computeRoomPhaseLoads(roomRacks: Rack[]) {
    const rackIds = new Set(roomRacks.map(r => r.id));
    const roomDevices = devices.filter(d => rackIds.has(d.rack_id));
    return {
      l1: roomDevices.filter(d => d.phase === 'L1').reduce((s, d) => s + (Number(d.anschlussleistung_watt ?? d.tdp_watt) || 0), 0) / 1000,
      l2: roomDevices.filter(d => d.phase === 'L2').reduce((s, d) => s + (Number(d.anschlussleistung_watt ?? d.tdp_watt) || 0), 0) / 1000,
      l3: roomDevices.filter(d => d.phase === 'L3').reduce((s, d) => s + (Number(d.anschlussleistung_watt ?? d.tdp_watt) || 0), 0) / 1000,
    };
  }
</script>

<svelte:head>
  <title>KAiTix - ServerFlow Dashboard</title>
  <meta name="description" content="Übersicht über die Server- und Strominfrastruktur im Rechenzentrum" />
</svelte:head>

<div class="space-y-8">
  <!-- Stats Header Grid -->
  <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
    <div class="bg-[#101622] border border-slate-800 rounded-xl p-5 flex items-center space-x-4">
      <div class="p-3 bg-blue-500/10 text-blue-400 rounded-lg">
        <Layers class="w-6 h-6" />
      </div>
      <div>
        <div class="text-xs text-slate-500 font-medium">Serverracks</div>
        <div class="text-2xl font-bold text-white mt-0.5">{totalRacks}</div>
      </div>
    </div>

    <div class="bg-[#101622] border border-slate-800 rounded-xl p-5 flex items-center space-x-4">
      <div class="p-3 bg-cyan-500/10 text-cyan-400 rounded-lg">
        <Server class="w-6 h-6" />
      </div>
      <div>
        <div class="text-xs text-slate-500 font-medium">Aktive Geräte</div>
        <div class="text-2xl font-bold text-white mt-0.5">{totalDevices}</div>
      </div>
    </div>

    <div class="bg-[#101622] border border-slate-800 rounded-xl p-5 flex items-center space-x-4">
      <div class="p-3 bg-orange-500/10 text-orange-400 rounded-lg">
        <Zap class="w-6 h-6" />
      </div>
      <div>
        <div class="text-xs text-slate-500 font-medium">Gesamtleistung (Nenn)</div>
        <div class="text-2xl font-bold text-white mt-0.5">{(totalPowerWatt / 1000).toFixed(2)} kW</div>
      </div>
    </div>

    <a href="/cables" class="bg-[#101622] border border-slate-800 rounded-xl p-5 flex items-center space-x-4 hover:border-emerald-500/30 transition">
      <div class="p-3 bg-emerald-500/10 text-emerald-400 rounded-lg">
        <CableIcon class="w-6 h-6" />
      </div>
      <div>
        <div class="text-xs text-slate-500 font-medium">Kabel dokumentiert</div>
        <div class="text-2xl font-bold text-white mt-0.5">{totalCables}</div>
      </div>
    </a>
  </div>

  <!-- Phase Power Cards -->
  {#if pduDevices.length > 0}
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div class="bg-[#101622] border border-blue-500/20 rounded-xl p-5 flex items-center space-x-4">
        <div class="p-3 bg-blue-500/10 text-blue-400 rounded-lg">
          <Zap class="w-6 h-6" />
        </div>
        <div>
          <div class="text-xs text-slate-500 font-medium">Phase L1</div>
          <div class="text-2xl font-bold text-white mt-0.5">{totalL1Kw.toFixed(2)} kW</div>
        </div>
      </div>
      <div class="bg-[#101622] border border-cyan-500/20 rounded-xl p-5 flex items-center space-x-4">
        <div class="p-3 bg-cyan-500/10 text-cyan-400 rounded-lg">
          <Zap class="w-6 h-6" />
        </div>
        <div>
          <div class="text-xs text-slate-500 font-medium">Phase L2</div>
          <div class="text-2xl font-bold text-white mt-0.5">{totalL2Kw.toFixed(2)} kW</div>
        </div>
      </div>
      <div class="bg-[#101622] border border-orange-500/20 rounded-xl p-5 flex items-center space-x-4">
        <div class="p-3 bg-orange-500/10 text-orange-400 rounded-lg">
          <Zap class="w-6 h-6" />
        </div>
        <div>
          <div class="text-xs text-slate-500 font-medium">Phase L3</div>
          <div class="text-2xl font-bold text-white mt-0.5">{totalL3Kw.toFixed(2)} kW</div>
        </div>
      </div>
    </div>
  {/if}

  <!-- Loading / Error Alert -->
  {#if loading}
    <div class="flex items-center justify-center p-12 bg-[#101622] border border-slate-800 rounded-xl">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
    </div>
  {:else if errorMsg}
    <div class="p-4 bg-red-950/40 border border-red-800 rounded-xl text-red-400 text-sm flex items-center space-x-3">
      <AlertTriangle class="w-5 h-5 shrink-0" />
      <span>{errorMsg}</span>
    </div>
  {:else}
    <div class="grid grid-cols-1 gap-8">
      <!-- Racks Visualization Area -->
      <div class="space-y-6">
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-bold text-white font-outfit">Rechenzentrum Racks</h3>
          <button 
            onclick={() => showAddRack = true}
            class="flex items-center space-x-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold transition"
          >
            <Plus class="w-3.5 h-3.5" />
            <span>Rack hinzufügen</span>
          </button>
        </div>

        {#if racks.length === 0}
          <div class="p-12 text-center bg-[#101622] border border-slate-800 border-dashed rounded-xl text-slate-500">
            <Info class="w-8 h-8 mx-auto mb-2 text-slate-600" />
            Keine Racks vorhanden. Erstellen Sie ein neues Rack, um zu starten.
          </div>
        {:else}
          <!-- Room-grouped sections -->
          {#each rooms as room}
            {@const roomRacks = racks.filter(r => r.standort === room)}
            {@const ph = computeRoomPhaseLoads(roomRacks)}
            {@const roomTotalKw = ph.l1 + ph.l2 + ph.l3}
            <div class="space-y-4">
              <!-- Room Header -->
              <div class="flex items-center gap-3">
                <div class="p-2 bg-slate-800 rounded-lg">
                  <Building class="w-4 h-4 text-slate-400" />
                </div>
                <div>
                  <h4 class="font-bold text-white font-outfit text-sm">{room}</h4>
                  <span class="text-[10px] text-slate-500">{roomRacks.length} Rack{roomRacks.length !== 1 ? 's' : ''} · {roomTotalKw.toFixed(2)} kW gesamt</span>
                </div>
              </div>

              <!-- Room Phase Bars -->
              <div class="grid grid-cols-3 gap-3">
                <div class="bg-[#101622] border border-blue-500/15 rounded-lg px-3 py-2">
                  <div class="flex items-center justify-between mb-1">
                    <span class="text-[10px] text-slate-500 font-medium">L1</span>
                    <span class="text-xs font-bold text-blue-400">{ph.l1.toFixed(2)} kW</span>
                  </div>
                  <div class="w-full h-1.5 bg-slate-950 rounded-full overflow-hidden">
                    <div class="h-full bg-blue-500 rounded-full transition-all" style="width: {roomTotalKw > 0 ? Math.round(ph.l1 / roomTotalKw * 100) : 0}%"></div>
                  </div>
                </div>
                <div class="bg-[#101622] border border-cyan-500/15 rounded-lg px-3 py-2">
                  <div class="flex items-center justify-between mb-1">
                    <span class="text-[10px] text-slate-500 font-medium">L2</span>
                    <span class="text-xs font-bold text-cyan-400">{ph.l2.toFixed(2)} kW</span>
                  </div>
                  <div class="w-full h-1.5 bg-slate-950 rounded-full overflow-hidden">
                    <div class="h-full bg-cyan-500 rounded-full transition-all" style="width: {roomTotalKw > 0 ? Math.round(ph.l2 / roomTotalKw * 100) : 0}%"></div>
                  </div>
                </div>
                <div class="bg-[#101622] border border-orange-500/15 rounded-lg px-3 py-2">
                  <div class="flex items-center justify-between mb-1">
                    <span class="text-[10px] text-slate-500 font-medium">L3</span>
                    <span class="text-xs font-bold text-orange-400">{ph.l3.toFixed(2)} kW</span>
                  </div>
                  <div class="w-full h-1.5 bg-slate-950 rounded-full overflow-hidden">
                    <div class="h-full bg-orange-500 rounded-full transition-all" style="width: {roomTotalKw > 0 ? Math.round(ph.l3 / roomTotalKw * 100) : 0}%"></div>
                  </div>
                </div>
              </div>

              <!-- Room Rack Cards -->
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                {#each roomRacks as rack}
                  {@const rackDevices = devices.filter(d => d.rack_id === rack.id)}
                  {@const occupiedU = rackDevices.reduce((sum, d) => sum + d.u_hoehe, 0)}
                  {@const percent = Math.round((occupiedU / rack.hoehe_u) * 100)}
                  {@const rackKw = rackDevices.reduce((s, d) => s + (Number(d.anschlussleistung_watt ?? d.tdp_watt) || 0), 0) / 1000}

                  <a href="/racks?rack={rack.id}" class="block bg-[#101622] border border-slate-800 hover:border-blue-500/40 rounded-xl p-5 space-y-4 transition-colors">
                    <div class="flex items-start justify-between">
                      <div>
                        <h4 class="font-bold text-white font-outfit">{rack.name}</h4>
                        <p class="text-[10px] text-slate-500 mt-0.5">{rackKw.toFixed(2)} kW · {rackDevices.length} Geräte</p>
                      </div>
                      <span class="text-xs font-semibold px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300">
                        {occupiedU} / {rack.hoehe_u} HE
                      </span>
                    </div>

                    <!-- Progress bar -->
                    <div class="space-y-1">
                      <div class="flex justify-between text-[10px] text-slate-400 font-mono">
                        <span>Auslastung</span>
                        <span>{percent}%</span>
                      </div>
                      <div class="w-full h-2 bg-slate-950 rounded-full overflow-hidden">
                        <div 
                          class="h-full bg-gradient-to-r from-blue-500 to-cyan-400 rounded-full" 
                          style="width: {percent}%"
                        ></div>
                      </div>
                    </div>

                    <!-- Vertical Rack View representation -->
                    <div class="border border-slate-950 bg-slate-950/60 rounded p-1 font-mono text-[9px] select-none">
                      <div class="text-center text-[8px] text-slate-600 border-b border-slate-900 pb-1 mb-1">FRONTANSICHT</div>
                      <div class="space-y-0.5">
                        {#each Array.from({ length: Math.min(10, rack.hoehe_u) }).map((_, i) => rack.hoehe_u - i) as u}
                          {@const dev = rackDevices.find(d => u >= (d.u_position ?? 0) && u < (d.u_position ?? 0) + d.u_hoehe)}
                          {#if dev}
                            {#if u === (dev.u_position ?? 0) + dev.u_hoehe - 1}
                              <div 
                                class="px-2 py-1 rounded flex justify-between items-center text-white border border-blue-900/60"
                                style="background-color: {dev.typ === 'server' ? 'rgba(59, 130, 246, 0.2)' : dev.typ === 'switch' ? 'rgba(6, 182, 212, 0.2)' : 'rgba(249, 115, 22, 0.2)'}; grid-row: span {dev.u_hoehe}"
                              >
                                <span class="truncate font-semibold">{dev.hostname}</span>
                                <span class="text-[8px] opacity-65">{dev.typ.toUpperCase()} ({dev.u_hoehe}U)</span>
                              </div>
                            {/if}
                          {:else}
                            <div class="px-2 py-0.5 text-slate-700 border border-dashed border-slate-800/40 flex justify-between items-center">
                              <span>HE {u}</span>
                              <span class="text-[7px] text-slate-800">LEER</span>
                            </div>
                          {/if}
                        {/each}
                        {#if rack.hoehe_u > 10}
                          <div class="text-center text-[8px] py-1 text-slate-600 border-t border-slate-900">
                            + {rack.hoehe_u - 10} weitere Höheneinheiten...
                          </div>
                        {/if}
                      </div>
                    </div>
                  </a>
                {/each}
              </div>
            </div>
          {/each}

          <!-- Racks without standort -->
          {#if racksWithoutRoom.length > 0}
            <div class="space-y-4">
              <div class="flex items-center gap-3">
                <div class="p-2 bg-slate-800 rounded-lg">
                  <AlertTriangle class="w-4 h-4 text-amber-400" />
                </div>
                <div>
                  <h4 class="font-bold text-white font-outfit text-sm">Ohne Standort</h4>
                  <span class="text-[10px] text-slate-500">{racksWithoutRoom.length} Rack{racksWithoutRoom.length !== 1 ? 's' : ''} ohne Raum-Zuordnung</span>
                </div>
              </div>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                {#each racksWithoutRoom as rack}
                  {@const rackDevices = devices.filter(d => d.rack_id === rack.id)}
                  {@const occupiedU = rackDevices.reduce((sum, d) => sum + d.u_hoehe, 0)}
                  {@const percent = Math.round((occupiedU / rack.hoehe_u) * 100)}
                  {@const rackKw = rackDevices.reduce((s, d) => s + (Number(d.anschlussleistung_watt ?? d.tdp_watt) || 0), 0) / 1000}

                  <a href="/racks?rack={rack.id}" class="block bg-[#101622] border border-amber-500/20 hover:border-amber-500/40 rounded-xl p-5 space-y-4 transition-colors">
                    <div class="flex items-start justify-between">
                      <div>
                        <h4 class="font-bold text-white font-outfit">{rack.name}</h4>
                        <p class="text-[10px] text-amber-400/60 mt-0.5">{rackKw.toFixed(2)} kW · {rackDevices.length} Geräte</p>
                      </div>
                      <span class="text-xs font-semibold px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300">
                        {occupiedU} / {rack.hoehe_u} HE
                      </span>
                    </div>
                    <div class="space-y-1">
                      <div class="flex justify-between text-[10px] text-slate-400 font-mono">
                        <span>Auslastung</span>
                        <span>{percent}%</span>
                      </div>
                      <div class="w-full h-2 bg-slate-950 rounded-full overflow-hidden">
                        <div class="h-full bg-gradient-to-r from-amber-500 to-orange-400 rounded-full" style="width: {percent}%"></div>
                      </div>
                    </div>
                  </a>
                {/each}
              </div>
            </div>
          {/if}
        {/if}
      </div>

      <!-- Cable Overview Right Area -->
      <div class="space-y-6">
        <h3 class="text-lg font-bold text-white font-outfit">Kabelübersicht</h3>

        <div class="bg-[#101622] border border-slate-800 rounded-xl p-5 space-y-4">
          {#if cables.length === 0}
            <div class="text-center py-8 text-slate-500 text-sm">
              <Info class="w-8 h-8 text-slate-600 mx-auto mb-2" />
              Keine Kabel dokumentiert.
            </div>
          {:else}
            <div class="space-y-2">
              {#each cableTypes as ct}
                {@const count = cables.filter(c => c.typ === ct).length}
                {@const totalLen = cables.filter(c => c.typ === ct).reduce((s, c) => s + (Number(c.laenge_m) || 0), 0)}
                <div class="flex items-center justify-between py-2 border-b border-slate-800/60 last:border-0">
                  <div class="flex items-center gap-2">
                    <span class="text-[10px] px-1.5 py-0.5 rounded border {
                      ct.startsWith('Strom') ? 'bg-red-500/10 text-red-400 border-red-500/30' :
                      ct === 'DAC' ? 'bg-slate-500/10 text-slate-400 border-slate-500/30' :
                      ct.startsWith('Cat') ? 'bg-blue-500/10 text-blue-400 border-blue-500/30' :
                      ct === 'LC-LC' || ct === 'SC-SC' ? 'bg-fuchsia-500/10 text-fuchsia-400 border-fuchsia-500/30' :
                      'bg-amber-500/10 text-amber-400 border-amber-500/30'
                    }">{ct}</span>
                  </div>
                  <div class="text-right">
                    <div class="text-sm font-bold text-white">{count}</div>
                    <div class="text-[10px] text-slate-500">{totalLen.toFixed(1)} m</div>
                  </div>
                </div>
              {/each}
            </div>
            <a href="/cables" class="block w-full text-center py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium transition">
              Zur Kabelliste →
            </a>
          {/if}
        </div>
      </div>
    </div>
  {/if}
</div>

<!-- Modal Rack hinzufügen -->
<RackModal
  bind:show={showAddRack}
  onSave={handleAddRack}
  hardwareTypes={hardwareTypes}
/>

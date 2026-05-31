<script lang="ts">
  import { onMount } from 'svelte';
  import { api, type Rack, type Device, type DevicePort, type Cable } from '$lib/api';
  import { Server, Layers, Plus, Trash2, Edit2, X, Cpu, Plug, Zap, Search } from '@lucide/svelte';

  let devices = $state<Device[]>([]);
  let racks = $state<Rack[]>([]);
  let selectedDevice = $state<Device | null>(null);
  let ports = $state<DevicePort[]>([]);
  let cables = $state<Cable[]>([]);
  let loading = $state(true);
  let errorMsg = $state('');

  let searchQuery = $state('');
  let filterRack = $state<string>('all');
  let filterType = $state<string>('all');
  let filterPhase = $state<string>('all');

  let showAddDevice = $state(false);
  let showEditDevice = $state(false);

  let hostname = $state('');
  let typ = $state<Device['typ']>('server');
  let u_position = $state(1);
  let u_hoehe = $state(1);
  let phase = $state<'L1' | 'L2' | 'L3'>('L1');
  let tdp_watt = $state(200);
  let rack_id = $state<number | null>(null);

  async function loadData() {
    loading = true;
    errorMsg = '';
    try {
      const [devicesData, racksData, cablesData] = await Promise.all([
        api.getDevices(),
        api.getRacks(),
        api.getCables()
      ]);
      devices = devicesData;
      racks = racksData;
      cables = cablesData;
      if (racksData.length > 0 && !rack_id) rack_id = racksData[0].id;
    } catch (err: any) {
      errorMsg = err.message || 'Fehler beim Laden der Daten.';
    } finally {
      loading = false;
    }
  }

  async function loadDeviceDetails(deviceId: number) {
    try { ports = await api.getDevicePorts(deviceId); } catch { ports = []; }
  }

  async function selectDevice(device: Device) {
    selectedDevice = device;
    await loadDeviceDetails(device.id);
  }

  onMount(() => { loadData(); });

  async function handleAddDevice(e: SubmitEvent) {
    e.preventDefault();
    if (!hostname.trim() || !rack_id) return;
    try {
      const newDev = await api.createDevice({
        hostname: hostname.trim(), typ, u_position, u_hoehe, phase, tdp_watt, rack_id
      });
      showAddDevice = false;
      resetForm();
      await loadData();
      await selectDevice(newDev);
    } catch (err: any) {
      alert('Fehler: ' + err.message);
    }
  }

  async function handleEditDevice(e: SubmitEvent) {
    e.preventDefault();
    if (!selectedDevice || !hostname.trim() || !rack_id) return;
    try {
      await api.updateDevice(selectedDevice.id, {
        hostname: hostname.trim(), typ, u_position, u_hoehe, phase, tdp_watt, rack_id
      });
      showEditDevice = false;
      resetForm();
      await loadData();
    } catch (err: any) {
      alert('Fehler: ' + err.message);
    }
  }

  async function handleDeleteDevice(id: number) {
    if (!confirm('Gerät wirklich löschen?')) return;
    try {
      await api.deleteDevice(id);
      selectedDevice = null;
      await loadData();
    } catch (err: any) {
      alert('Fehler: ' + err.message);
    }
  }

  function openEditModal() {
    if (!selectedDevice) return;
    hostname = selectedDevice.hostname;
    typ = selectedDevice.typ;
    u_position = selectedDevice.u_position ?? 1;
    u_hoehe = selectedDevice.u_hoehe;
    phase = selectedDevice.phase ?? 'L1';
    tdp_watt = selectedDevice.tdp_watt ?? 0;
    rack_id = selectedDevice.rack_id ?? null;
    showEditDevice = true;
  }

  function resetForm() {
    hostname = ''; typ = 'server'; u_position = 1; u_hoehe = 1; phase = 'L1'; tdp_watt = 200;
    if (racks.length > 0) rack_id = racks[0].id;
  }

  const filteredDevices = $derived(devices.filter(d => {
    const matchesSearch = d.hostname.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesRack = filterRack === 'all'
      || (filterRack === 'kein_rack' ? !d.rack_id : d.rack_id?.toString() === filterRack);
    const matchesType = filterType === 'all' || d.typ === filterType;
    const matchesPhase = filterPhase === 'all' || d.phase === filterPhase;
    return matchesSearch && matchesRack && matchesType && matchesPhase;
  }));

  const selectedDeviceRack = $derived(
    selectedDevice ? racks.find(r => r.id === selectedDevice!.rack_id) : null
  );

  function getPortConnection(portId: number) {
    const cable = cables.find(c =>
      (c.von_port === portId.toString() && c.von_device_id === selectedDevice?.id) ||
      (c.nach_port === portId.toString() && c.nach_device_id === selectedDevice?.id)
    );
    if (!cable) return null;
    const otherDevId = cable.von_device_id === selectedDevice?.id ? cable.nach_device_id : cable.von_device_id;
    return { cable, otherDevice: devices.find(d => d.id === otherDevId) || null };
  }
</script>

<svelte:head><title>KAiTix - Geräte</title></svelte:head>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between border-b border-[var(--color-border)] pb-4">
    <div>
      <h2 class="text-xl font-bold text-[var(--color-text)] font-outfit">Rechenzentrum Geräte</h2>
      <p class="text-xs text-[var(--color-text3)]">Server, Switches, PDUs und weitere Hardware verwalten</p>
    </div>
    <button onclick={() => { resetForm(); showAddDevice = true; }}
      class="flex items-center space-x-2 px-4 py-2 bg-[#1D9E75] hover:bg-[#0F6E56] text-[var(--color-text)] rounded-lg text-xs font-semibold transition">
      <Plus class="w-4 h-4" /><span>Gerät hinzufügen</span>
    </button>
  </div>

  {#if loading}
    <div class="flex items-center justify-center p-12">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-[#1D9E75]"></div>
    </div>
  {:else if errorMsg}
    <div class="p-4 bg-red-950/40 border border-red-800 rounded-xl text-red-400 text-sm">{errorMsg}</div>
  {:else}
    <!-- Filters -->
    <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-4 grid grid-cols-1 sm:grid-cols-4 gap-4 items-center">
      <div class="relative">
        <Search class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text3)]" />
        <input type="text" bind:value={searchQuery} placeholder="Gerätename suchen..."
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border)] rounded-lg pl-9 pr-4 py-2 text-xs text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
      </div>
      <select bind:value={filterRack} class="bg-[var(--color-bg3)] border border-[var(--color-border)] rounded-lg px-3 py-2 text-xs text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]">
        <option value="all">Alle Racks</option>
        <option value="kein_rack">Kein Rack</option>
        {#each racks as rack}<option value={rack.id.toString()}>{rack.name}{rack.rackreihe ? ` (${rack.rackreihe})` : ''}</option>{/each}
      </select>
      <select bind:value={filterType} class="bg-[var(--color-bg3)] border border-[var(--color-border)] rounded-lg px-3 py-2 text-xs text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]">
        <option value="all">Alle Typen</option>
        <option value="server">Server</option>
        <option value="switch">Switch</option>
        <option value="pdu">PDU</option>
        <option value="sonstige">Sonstige</option>
      </select>
      <select bind:value={filterPhase} class="bg-[var(--color-bg3)] border border-[var(--color-border)] rounded-lg px-3 py-2 text-xs text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]">
        <option value="all">Alle Phasen</option>
        <option value="L1">L1</option>
        <option value="L2">L2</option>
        <option value="L3">L3</option>
      </select>
    </div>

    <!-- Main Content -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Device List -->
      <div class="lg:col-span-1 space-y-2">
        {#each filteredDevices as device}
          {@const rackObj = racks.find(r => r.id === device.rack_id)}
          {@const rackName = rackObj ? `${rackObj.name}${rackObj.rackreihe ? ` (${rackObj.rackreihe})` : ''}` : ''}
          {@const noRack = !device.rack_id}
          <button onclick={() => selectDevice(device)}
            class="w-full text-left bg-[var(--color-bg2)] border rounded-xl p-4 hover:border-[#1D9E75]/40 transition
              {selectedDevice?.id === device.id ? 'border-[#1D9E75]/60 bg-[#1D9E75]/5' : noRack ? 'border-amber-800/50' : 'border-[var(--color-border)]'}">
            <div class="flex items-center space-x-3">
              <div class="p-2 rounded-lg {device.typ === 'server' ? 'bg-blue-500/10 text-blue-400' : device.typ === 'switch' ? 'bg-cyan-500/10 text-cyan-400' : 'bg-orange-500/10 text-orange-400'}">
                <Server class="w-4 h-4" />
              </div>
              <div class="min-w-0 flex-1">
                <h4 class="font-bold text-sm text-[var(--color-text)] truncate">{device.hostname}</h4>
                <p class="text-[10px] text-[var(--color-text3)] truncate">
                  <span class="font-mono uppercase bg-[var(--color-border)] px-1 py-0.5 rounded text-[8px]">{device.typ}</span>
                  {#if noRack}
                    <span class="ml-1 text-amber-500/80 font-medium">Kein Rack</span>
                  {:else}
                    <span>{rackName} (HE {device.u_position ?? '?'})</span>
                  {/if}
                </p>
              </div>
            </div>
          </button>
        {:else}
          <div class="text-center py-8 text-[var(--color-text3)] text-sm">Keine Geräte gefunden.</div>
        {/each}
      </div>

      <!-- Detail Panel -->
      <div class="lg:col-span-2">
        {#if selectedDevice}
          <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-6 space-y-6">
            <div class="flex items-start justify-between">
              <div>
                <h3 class="text-lg font-bold text-[var(--color-text)] font-outfit">{selectedDevice.hostname}</h3>
                <div class="flex flex-wrap gap-4 text-xs text-[var(--color-text3)] mt-1">
                  <span class="flex items-center capitalize"><Cpu class="w-3.5 h-3.5 mr-1" /> {selectedDevice.typ}</span>
                  <span>{selectedDeviceRack ? `${selectedDeviceRack.name}${selectedDeviceRack.rackreihe ? ` (${selectedDeviceRack.rackreihe})` : ''}` : 'Kein Rack'} (HE {selectedDevice.u_position ?? '?'})</span>
                </div>
              </div>
              <div class="flex space-x-2">
                <button onclick={openEditModal} class="p-2 bg-[var(--color-border)] hover:bg-[var(--color-border2)] rounded-lg text-[var(--color-text2)] transition"><Edit2 class="w-4 h-4" /></button>
                <button onclick={() => handleDeleteDevice(selectedDevice!.id)} class="p-2 bg-red-950/40 hover:bg-red-900/40 rounded-lg text-red-400 transition"><Trash2 class="w-4 h-4" /></button>
              </div>
            </div>

            <!-- Stats -->
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-4">
                <div class="text-[10px] text-[var(--color-text3)] uppercase font-bold font-mono">Phase</div>
                <div class="text-lg font-bold text-[var(--color-text)] mt-0.5">{selectedDevice.phase ?? '—'}</div>
              </div>
              <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-4">
                <div class="text-[10px] text-[var(--color-text3)] uppercase font-bold font-mono">Anschluss W</div>
                <div class="text-lg font-bold text-[var(--color-text)] mt-0.5">{selectedDevice.tdp_watt ?? '—'} W</div>
              </div>
              <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-4">
                <div class="text-[10px] text-[var(--color-text3)] uppercase font-bold font-mono">Höhe</div>
                <div class="text-lg font-bold text-[var(--color-text)] mt-0.5">{selectedDevice.u_hoehe} HE</div>
              </div>
            </div>

            <!-- Ports -->
            {#if ports.length > 0}
              <div>
                <h4 class="text-xs font-bold text-[var(--color-text3)] uppercase tracking-wider font-mono mb-3">Ports & Verbindungen</h4>
                <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {#each ports as port}
                    {@const conn = getPortConnection(port.id)}
                    <div class="bg-[var(--color-bg3)] border border-[var(--color-border)]/80 rounded-lg p-3 text-xs">
                      <div class="flex items-center justify-between">
                        <span class="font-mono font-bold text-[var(--color-text)]">{port.port_name}</span>
                        <span class="text-[10px] px-1.5 py-0.5 rounded bg-[var(--color-border)] text-[var(--color-text2)]">{port.typ}</span>
                      </div>
                      {#if conn}
                        <div class="mt-1 text-[10px] text-emerald-400 truncate">→ {conn.otherDevice?.hostname || '?'}</div>
                      {:else}
                        <div class="mt-1 text-[10px] text-[var(--color-text3)]">Frei</div>
                      {/if}
                    </div>
                  {/each}
                </div>
              </div>
            {/if}
          </div>
        {:else}
          <div class="flex items-center justify-center h-full text-[var(--color-text3)] text-sm">Gerät auswählen um Details anzuzeigen</div>
        {/if}
      </div>
    </div>
  {/if}
</div>

<!-- Add Modal -->
{#if showAddDevice}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-6 max-w-sm w-full shadow-2xl">
    <h3 class="text-lg font-bold text-[var(--color-text)] mb-4 font-outfit">Gerät hinzufügen</h3>
    <form onsubmit={handleAddDevice} class="space-y-4">
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Hostname *</label>
        <input type="text" bind:value={hostname} required
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
      </div>
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Rack *</label>
        <select bind:value={rack_id} required
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]">
          {#each racks as rack}<option value={rack.id}>{rack.name}{rack.rackreihe ? ` (${rack.rackreihe})` : ''}</option>{/each}
        </select>
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Typ</label>
          <select bind:value={typ}
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]">
            <option value="server">Server</option>
            <option value="switch">Switch</option>
            <option value="pdu">PDU</option>
            <option value="sonstige">Sonstige</option>
          </select>
        </div>
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Phase</label>
          <select bind:value={phase}
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]">
            <option value="L1">L1</option>
            <option value="L2">L2</option>
            <option value="L3">L3</option>
          </select>
        </div>
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Position (HE) *</label>
          <input type="number" bind:value={u_position} min="1" max="60" required
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Höhe (HE) *</label>
          <input type="number" bind:value={u_hoehe} min="1" max="10" required
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
        </div>
      </div>
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Anschluss W</label>
        <input type="number" bind:value={tdp_watt}
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
      </div>
      <div class="flex justify-end space-x-3 pt-2">
        <button type="button" onclick={() => showAddDevice = false}
          class="px-4 py-2 rounded-lg text-sm text-[var(--color-text2)] hover:bg-[var(--color-border)] transition">Abbrechen</button>
        <button type="submit"
          class="px-4 py-2 bg-[#1D9E75] hover:bg-[#0F6E56] text-[var(--color-text)] rounded-lg text-sm font-semibold transition">Speichern</button>
      </div>
    </form>
  </div>
</div>
{/if}

<!-- Edit Modal -->
{#if showEditDevice}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-6 max-w-sm w-full shadow-2xl">
    <h3 class="text-lg font-bold text-[var(--color-text)] mb-4 font-outfit">Gerät bearbeiten</h3>
    <form onsubmit={handleEditDevice} class="space-y-4">
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Hostname *</label>
        <input type="text" bind:value={hostname} required
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
      </div>
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Rack *</label>
        <select bind:value={rack_id} required
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]">
          {#each racks as rack}<option value={rack.id}>{rack.name}{rack.rackreihe ? ` (${rack.rackreihe})` : ''}</option>{/each}
        </select>
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Typ</label>
          <select bind:value={typ}
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]">
            <option value="server">Server</option>
            <option value="switch">Switch</option>
            <option value="pdu">PDU</option>
            <option value="sonstige">Sonstige</option>
          </select>
        </div>
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Phase</label>
          <select bind:value={phase}
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]">
            <option value="L1">L1</option>
            <option value="L2">L2</option>
            <option value="L3">L3</option>
          </select>
        </div>
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Position (HE) *</label>
          <input type="number" bind:value={u_position} min="1" max="60" required
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Höhe (HE) *</label>
          <input type="number" bind:value={u_hoehe} min="1" max="10" required
            class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
        </div>
      </div>
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Anschluss W</label>
        <input type="number" bind:value={tdp_watt}
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
      </div>
      <div class="flex justify-end space-x-3 pt-2">
        <button type="button" onclick={() => showEditDevice = false}
          class="px-4 py-2 rounded-lg text-sm text-[var(--color-text2)] hover:bg-[var(--color-border)] transition">Abbrechen</button>
        <button type="submit"
          class="px-4 py-2 bg-[#1D9E75] hover:bg-[#0F6E56] text-[var(--color-text)] rounded-lg text-sm font-semibold transition">Speichern</button>
      </div>
    </form>
  </div>
</div>
{/if}

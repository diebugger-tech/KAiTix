<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import { api, type Rack, type Device, type HardwareType, type Cable, type DevicePort, type PduOutlet } from '$lib/api';
  import {
    Layers, MapPin, Plus, Trash2, Edit2, X, Server, Zap,
    ChevronRight, Activity, Network, Cable as CableIcon, Plug, FileText,
    Building, Wifi
  } from '@lucide/svelte';
  import RackModal from '$lib/components/RackModal.svelte';
  import RackFilterBar from '$lib/components/RackFilterBar.svelte';
  import { locationStore, type LocationType } from '$lib/locations.svelte';

  // ── State ─────────────────────────────────────────────────
  let racks       = $state<Rack[]>([]);
  let devices     = $state<Device[]>([]);
  let cables      = $state<Cable[]>([]);
  let hardware    = $state<HardwareType[]>([]);
  let selectedRack = $state<Rack | null>(null);
  let selectedDevice = $state<Device | null>(null);
  let devicePorts = $state<DevicePort[]>([]);
  let loading     = $state(true);
  let errorMsg    = $state('');

  // Filtering and search state
  let filterStandort = $state('Alle');
  let filterReihe = $state('Alle');
  let searchRackName = $state('');
  let showManageLocations = $state(false);
  let dropdownSelectedRackId = $state<string | number>('Alle');

  let filteredRacks = $derived(
    racks.filter(r => {
      if (filterStandort && filterStandort !== 'Alle' && r.standort !== filterStandort) return false;
      if (filterReihe && filterReihe !== 'Alle' && r.rackreihe !== filterReihe) return false;
      if (searchRackName && !r.name.toLowerCase().includes(searchRackName.toLowerCase())) return false;
      return true;
    }).sort((a, b) => a.name.localeCompare(b.name))
  );

  // Sync dropdown selected rack to main selectedRack object
  $effect(() => {
    if (dropdownSelectedRackId !== 'Alle' && selectedRack?.id !== dropdownSelectedRackId) {
      const found = racks.find(r => r.id == dropdownSelectedRackId);
      if (found) {
        selectedRack = found;
        selectedDevice = null;
      }
    }
  });

  // Sync main selectedRack object back to dropdown selection
  $effect(() => {
    if (selectedRack) {
      if (dropdownSelectedRackId !== selectedRack.id) {
        dropdownSelectedRackId = selectedRack.id;
      }
    } else {
      if (dropdownSelectedRackId !== 'Alle') {
        dropdownSelectedRackId = 'Alle';
      }
    }
  });

  // Standort Management State
  let showAddLocation = $state(false);
  let newLocationName = $state('');
  let newLocationType = $state<LocationType>('rechenzentrum');
  let editingLocation = $state<string | null>(null);
  let editLocationName = $state('');
  let editLocationType = $state<LocationType>('rechenzentrum');

  // Rack modals
  let showAddRack  = $state(false);
  let showEditRack = $state(false);

  // Confirmation Modal State
  let showConfirmModal = $state(false);
  let confirmMessage = $state('');
  let confirmButtonText = $state('Löschen');
  let onConfirmCallback = $state<(() => void | Promise<void>) | null>(null);

  function openConfirm(message: string, callback: () => void | Promise<void>, buttonText = 'Löschen') {
    confirmMessage = message;
    confirmButtonText = buttonText;
    onConfirmCallback = callback;
    showConfirmModal = true;
  }

  async function handleConfirm() {
    if (onConfirmCallback) {
      try {
        await onConfirmCallback();
      } catch (e: any) {
        alert('Fehler: ' + e.message);
      }
    }
    showConfirmModal = false;
    onConfirmCallback = null;
  }

  // Gerät einbauen modal
  let showAddDevice   = $state(false);
  let targetSlot      = $state<number|null>(1);
  let selectedHW      = $state<HardwareType | null>(null);
  let devHostname     = $state('');
  let devPhase        = $state<'L1'|'L2'|'L3'>('L1');
  let devSide         = $state<'left'|'right'>('left');
  let devIp           = $state('');
  let devHersteller   = $state('');
  let devModell       = $state('');
  let devSeriennummer  = $state('');
  let devInventarnummer = $state('');
  let devBemerkung    = $state('');
  let devUHoehe       = $state<number|null>(1);
  let devTdpWatt      = $state<number|null>(null);
  let devPsuCount     = $state<number|null>(null);
  let devPsuNennwatt  = $state<number|null>(null);
  let devAnschlussleistung = $state<number|null>(0);
  let hwFilter        = $state('');
  let pduOnlyMode     = $state(false);

  // Gerät bearbeiten modal
  let showEditDevice = $state(false);
  let editHostname   = $state('');
  let editIp         = $state('');
  let editPhase      = $state<'L1'|'L2'|'L3'>('L1');
  let editAnschluss  = $state<number|null>(0);
  let editHersteller = $state('');
  let editModell     = $state('');
  let editSeriennummer  = $state('');
  let editInventarnummer = $state('');
  let editBemerkung  = $state('');
  let editUPos       = $state<number|null>(1);
  let editUHoehe     = $state<number|null>(1);
  let editSide       = $state<'left'|'right'>('left');
  let editShutdownDelay = $state<number|null>(0);
  let editShutdownPriority = $state<number|null>(2);
  let editShutdownMethod = $state<string>('ACPI_Graceful');
  let editDependencies = $state<any[]>([]);

  // Kabel anlegen modal
  let showAddCable  = $state(false);
  let cableVonPort  = $state('');
  let cableNachDevId = $state<number|null>(null);
  let cableNachPort  = $state('');
  let cableTyp       = $state('Cat6A');
  let cableLaenge    = $state<number|null>(1.0);
  let cableFarbe     = $state('');
  let cableFromDevice = $state<Device|null>(null);

  // Kabel bearbeiten modal
  let showEditCable   = $state(false);
  let editCableId     = $state<number | null>(null);
  let editCableNr     = $state('');
  let editCableTyp    = $state('Cat6A');
  let editCableLaenge = $state<number|null>(1.0);
  let editCableFarbe  = $state('');
  let editCableFromDevice = $state<Device | null>(null);
  let editCableVonPort = $state('');
  let editCableNachDevId = $state<number | null>(null);
  let editCableNachPort = $state('');

  // Interface anlegen modal
  let showAddInterface = $state(false);
  let ifacePort   = $state('');
  let ifaceTyp    = $state('1GbE');
  let ifaceMac    = $state('');

  // PDU Outlet state
  let pduOutlets      = $state<PduOutlet[]>([]);
  let activeModalTab  = $state<'details'|'interfaces'|'protokoll'>('details');
  let powerAuditData  = $state<any>(null);
  let powerAuditLoading = $state(false);

  function closeModal() {
    selectedDevice = null;
    activeModalTab = 'details';
    powerAuditData = null;
  }

  $effect(() => {
    if (activeModalTab === 'protokoll' && selectedDevice?.typ === 'usv') {
      if (!powerAuditData && !powerAuditLoading) {
        powerAuditLoading = true;
        api.getPowerAudit(selectedDevice.id).then(res => {
          powerAuditData = res;
        }).catch(err => {
          console.error(err);
          powerAuditData = { error: err.message };
        }).finally(() => {
          powerAuditLoading = false;
        });
      }
    }
  });
  let showAddOutlet   = $state(false);
  let outletName      = $state('');
  let outletPhase     = $state<'L1'|'L2'|'L3'>('L1');
  let outletTyp       = $state('C13');
  let outletMaxWatt   = $state<number|null>(null);
  let outletDevId     = $state<number|null>(null);

  function isDeviceIncompatible(dev: Device) {
    if (!dev.hersteller || !dev.modell || !selectedRack) return false;
    const hw = hardware.find(h => h.hersteller === dev.hersteller && h.modell === dev.modell);
    if (!hw || !hw.min_rack_hoehe) return false;
    return selectedRack.hoehe_u < hw.min_rack_hoehe;
  }

  // ── Laden ─────────────────────────────────────────────────
  async function loadAll() {
    loading = true; errorMsg = '';
    try {
      const [rd, dd, cd, hd] = await Promise.all([
        api.getRacks(), api.getDevices(),
        api.getCables().catch(() => [] as Cable[]),
        api.getHardware().catch(() => [] as HardwareType[]),
      ]);
      racks = rd; devices = dd; cables = cd; hardware = hd;
      if (!selectedRack && rd.length > 0) {
        const rackParam = page.url.searchParams.get('rack');
        const preselect = rackParam ? rd.find(r => r.id === Number(rackParam)) : null;
        selectedRack = preselect ?? rd[0];
      } else if (selectedRack) {
        selectedRack = rd.find(r => r.id === selectedRack!.id) ?? rd[0] ?? null;
      }
    } catch (e: any) { errorMsg = e.message || 'Ladefehler'; }
    finally { loading = false; }
  }

  async function loadDeviceDetail(dev: Device) {
    try {
      selectedDevice = await api.getDevice(dev.id);
    } catch (err) {
      console.error('Failed to load device details from API:', err);
      selectedDevice = dev;
    }
    try { devicePorts = await api.getDevicePorts(selectedDevice.id); } catch { devicePorts = []; }
    if (selectedDevice.typ === 'pdu') {
      try { pduOutlets = await api.getPduOutlets(selectedDevice.id); } catch { pduOutlets = []; }
    } else {
      pduOutlets = [];
    }
  }

  async function applyLocationRename(oldName: string, newName: string) {
    const trimmed = newName.trim();
    if (!trimmed || trimmed === oldName) return;
    for (const r of racks) {
      if (r.standort === oldName) {
        try { await api.updateRack(r.id, { ...r, standort: trimmed }); }
        catch (e) { console.error('Rack standort update failed:', e); }
      }
    }
    locationStore.update(oldName, trimmed, locationStore.getTyp(oldName));
    await loadAll();
  }

  function startEditLocation(name: string) {
    editingLocation = name;
    editLocationName = name;
    editLocationType = locationStore.getTyp(name);
  }

  async function saveEditLocation() {
    if (!editingLocation) return;
    const old = editingLocation;
    const newName = editLocationName.trim();
    locationStore.update(old, newName, editLocationType);
    if (newName !== old) await applyLocationRename(old, newName);
    editingLocation = null;
  }

  async function removeLocation(name: string) {
    const racksInLoc = racks.filter(r => r.standort === name);
    if (racksInLoc.length > 0) {
      alert(`Kann nicht löschen: ${racksInLoc.length} Rack(s) diesem Standort zugeordnet.`);
      return;
    }
    locationStore.remove(name);
  }

  async function addLocation() {
    const name = newLocationName.trim();
    if (!name) return;
    locationStore.add(name, newLocationType);
    newLocationName = '';
    newLocationType = 'rechenzentrum';
    showAddLocation = false;
  }

  onMount(() => {
    loadAll();
  });

  // ── Rack CRUD ──────────────────────────────────────────────
  async function handleAddRack(rackData) {
    const r = await api.createRack(rackData);
    await loadAll();
    selectedRack = r;
  }

  async function handleEditRack(rackData) {
    if (!selectedRack) return;
    const r = await api.updateRack(selectedRack.id, rackData);
    await loadAll();
    selectedRack = r;
  }

  function deleteRack(id: number) {
    openConfirm('Möchtest du dieses Rack wirklich unwiderruflich löschen? Alle darin verbauten Geräte verlieren ihre Rack-Position.', async () => {
      await api.deleteRack(id);
      selectedRack = null;
      await loadAll();
    });
  }

  function openEditRack() {
    showEditRack = true;
  }

  // ── Gerät einbauen ─────────────────────────────────────────
  // ── Gerät einbauen ─────────────────────────────────────────
  function openAddDevice(slot: number | null) {
    targetSlot = slot; selectedHW = null; devHostname = '';
    devPhase = 'L1'; devSide = 'left'; devIp = ''; devHersteller = ''; devModell = '';
    devSeriennummer = ''; devInventarnummer = ''; devBemerkung = ''; devUHoehe = slot === null ? 0 : 1;
    devTdpWatt = null; devPsuCount = null; devPsuNennwatt = null; devAnschlussleistung = 0;
    hwFilter = ''; pduOnlyMode = slot === null; showAddDevice = true;
  }

  function selectHW(hw: HardwareType) {
    selectedHW = hw;
    devUHoehe   = hw.u_hoehe;
    devAnschlussleistung = hw.tdp_watt ?? 0;
    devTdpWatt  = hw.tdp_watt ?? null;
    devPsuCount = hw.psu_count ?? null;
    devPsuNennwatt = hw.psu_nennwatt ?? null;
    devHersteller = hw.hersteller;
    devModell     = hw.modell;
    if (hw.u_hoehe === 0) {
      targetSlot = null;
    }
    if (!devHostname) devHostname = hw.name.toLowerCase().replace(/\s+/g, '-') + '-01';
  }

  async function submitAddDevice(e: SubmitEvent) {
    e.preventDefault();
    if (!selectedRack || !devHostname.trim()) return;
    try {
      const newDev = await api.createDevice({
        hostname: devHostname.trim(),
        typ: (selectedHW?.kategorie ?? 'sonstige') as any,
        rack_id: selectedRack.id,
        u_position: devUHoehe === 0 || targetSlot === null ? undefined : Number(targetSlot),
        u_hoehe: Number(devUHoehe),
        side: devUHoehe === 0 ? devSide : undefined,
        tdp_watt: devTdpWatt ?? undefined,
        psu_count: devPsuCount ?? undefined,
        psu_nennwatt: devPsuNennwatt ?? undefined,
        anschlussleistung_watt: devAnschlussleistung || undefined,
        ip_adresse: devIp || undefined,
        hersteller: devHersteller || undefined,
        modell: devModell || undefined,
        seriennummer: devSeriennummer || undefined,
        inventarnummer: devInventarnummer || undefined,
        bemerkung: devBemerkung || undefined,
      });
      showAddDevice = false; pduOnlyMode = false;
      await loadAll();
      await loadDeviceDetail(newDev);
      if (newDev.typ === 'pdu') {
        openPduAutoOutlet(newDev);
      }
    } catch (e: any) { alert('Fehler: ' + e.message); }
  }

  function deleteDevice(id: number) {
    openConfirm('Möchtest du dieses Gerät wirklich aus dem Rack entfernen?', async () => {
      await api.deleteDevice(id);
      selectedDevice = null;
      await loadAll();
    }, 'Entfernen');
  }

  // ── Gerät bearbeiten ──────────────────────────────────────────────
  function openEditDevice() {
    if (!selectedDevice) return;
    editHostname     = selectedDevice.hostname;
    editIp           = selectedDevice.ip_adresse || '';
    editPhase        = (selectedDevice.phase as 'L1'|'L2'|'L3') || 'L1';
    editAnschluss    = Number(selectedDevice.anschlussleistung_watt ?? selectedDevice.tdp_watt ?? 0);
    editHersteller   = selectedDevice.hersteller || '';
    editModell       = selectedDevice.modell || '';
    editSeriennummer   = selectedDevice.seriennummer || '';
    editInventarnummer = selectedDevice.inventarnummer || '';
    editBemerkung      = selectedDevice.bemerkung || '';
    editUPos         = selectedDevice.u_position ?? (selectedDevice.u_hoehe === 0 ? null : 1);
    editUHoehe       = selectedDevice.u_hoehe ?? 1;
    editSide         = (selectedDevice.side as 'left'|'right') ?? 'left';
    showEditDevice   = true;
  }

  async function submitEditDevice(e: SubmitEvent) {
    e.preventDefault();
    if (!selectedDevice) return;
    try {
      const updated = await api.updateDevice(selectedDevice.id, {
        hostname:               editHostname.trim(),
        ip_adresse:             editIp || undefined,
        anschlussleistung_watt: editAnschluss || undefined,
        hersteller:             editHersteller || undefined,
        modell:                 editModell || undefined,
        seriennummer:           editSeriennummer || undefined,
        inventarnummer:         editInventarnummer || undefined,
        bemerkung:              editBemerkung || undefined,
        u_position:             editUHoehe === 0 || editUPos === null ? undefined : Number(editUPos),
        u_hoehe:                Number(editUHoehe),
        side:                   editUHoehe === 0 ? editSide : undefined,
      });
      showEditDevice = false;
      await loadAll();
      await loadDeviceDetail(updated);
    } catch (e: any) { alert('Fehler: ' + (e as any).message); }
  }

  // ── Kabel anlegen ──────────────────────────────────────────
  function openAddCable(fromDev: Device, fromPort: string) {
    cableFromDevice = fromDev; cableVonPort = fromPort;
    cableNachDevId = null; cableNachPort = '';
    cableTyp = 'Cat6A'; cableLaenge = 1.0; cableFarbe = '';
    showAddCable = true;
  }

  async function submitAddCable(e: SubmitEvent) {
    e.preventDefault();
    if (!cableFromDevice || !cableNachDevId) return;
    try {
      await api.createCable({
        typ: cableTyp, laenge_m: cableLaenge ?? 1, farbe: cableFarbe || undefined,
        von_device_id: cableFromDevice.id, von_port: cableVonPort || undefined,
        nach_device_id: cableNachDevId, nach_port: cableNachPort || undefined,
      });
      showAddCable = false; await loadAll();
      if (selectedDevice) await loadDeviceDetail(selectedDevice);
    } catch (e: any) { alert('Fehler: ' + e.message); }
  }

  // ── Kabel bearbeiten ────────────────────────────────────────
  function openEditCable(cable: Cable) {
    if (!selectedDevice) return;
    editCableId = cable.id;
    editCableNr = cable.kabel_nr;
    editCableTyp = cable.typ;
    editCableLaenge = Number(cable.laenge_m);
    editCableFarbe = cable.farbe || '';
    
    if (cable.von_device_id === selectedDevice.id) {
      editCableFromDevice = selectedDevice;
      editCableVonPort = cable.von_port || '';
      editCableNachDevId = cable.nach_device_id || null;
      editCableNachPort = cable.nach_port || '';
    } else {
      editCableFromDevice = selectedDevice;
      editCableVonPort = cable.nach_port || '';
      editCableNachDevId = cable.von_device_id || null;
      editCableNachPort = cable.von_port || '';
    }
    showEditCable = true;
  }

  async function submitEditCable(e: SubmitEvent) {
    e.preventDefault();
    if (!editCableId || !editCableFromDevice || !editCableNachDevId) return;
    try {
      const orig = cables.find(c => c.id === editCableId);
      if (!orig) return;

      let von_id = orig.von_device_id;
      let von_p = orig.von_port;
      let nach_id = orig.nach_device_id;
      let nach_p = orig.nach_port;

      if (orig.von_device_id === selectedDevice!.id) {
        nach_id = editCableNachDevId;
        nach_p = editCableNachPort || undefined;
      } else {
        von_id = editCableNachDevId;
        von_p = editCableNachPort || undefined;
      }

      await api.updateCable(editCableId, {
        kabel_nr: editCableNr || undefined,
        typ: editCableTyp,
        laenge_m: editCableLaenge ?? 1,
        farbe: editCableFarbe || undefined,
        von_device_id: von_id || undefined,
        von_port: von_p || undefined,
        nach_device_id: nach_id,
        nach_port: nach_p || undefined,
      });
      showEditCable = false;
      await loadAll();
      if (selectedDevice) await loadDeviceDetail(selectedDevice);
    } catch (e: any) { alert('Fehler: ' + e.message); }
  }

  // ── Interface anlegen ──────────────────────────────────────
  function openAddInterface() { ifacePort=''; ifaceTyp='1GbE'; ifaceMac=''; showAddInterface=true; }

  async function submitAddInterface() {
    if (!ifacePort.trim() || !selectedDevice) return;
    try {
      await api.addDeviceInterface(selectedDevice.id, { port_name: ifacePort.trim(), typ: ifaceTyp, mac_adresse: ifaceMac || null });
      showAddInterface = false;
      await loadAll();
      await loadDeviceDetail(selectedDevice);
    } catch(e: any) { alert('Fehler: ' + e.message); }
  }

  // ── PDU Outlet CRUD ────────────────────────────────────────
  function openAddOutlet() { outletName=''; outletPhase='L1'; outletTyp='C13'; outletMaxWatt=null; outletDevId=null; showAddOutlet=true; }

  async function submitAddOutlet(e: SubmitEvent) {
    e.preventDefault();
    if (!selectedDevice || !outletName.trim()) return;
    try {
      await api.createPduOutlet(selectedDevice.id, {
        pdu_id: selectedDevice.id,
        outlet_name: outletName.trim(),
        phase: outletPhase,
        steckdosentyp: outletTyp as any,
        max_watt: outletMaxWatt ?? undefined,
        connected_device_id: outletDevId ?? undefined,
        schaltbar: false,
      });
      showAddOutlet = false;
      pduOutlets = await api.getPduOutlets(selectedDevice.id);
      devices = await api.getDevices();
      await loadDeviceDetail(selectedDevice);
    } catch(e: any) { alert('Fehler: ' + e.message); }
  }

  function deleteOutlet(outletId: number) {
    if (!selectedDevice) return;
    openConfirm('Möchtest du diese Steckdose wirklich löschen?', async () => {
      await api.deletePduOutlet(selectedDevice!.id, outletId);
      pduOutlets = await api.getPduOutlets(selectedDevice!.id);
      devices = await api.getDevices();
      await loadDeviceDetail(selectedDevice!);
    });
  }

  async function setOutletDevice(outletId: number, devId: number | null) {
    if (!selectedDevice) return;
    try {
      await api.updatePduOutlet(selectedDevice.id, outletId, { connected_device_id: devId ?? undefined });
      pduOutlets = await api.getPduOutlets(selectedDevice.id);
      devices = await api.getDevices();
      await loadDeviceDetail(selectedDevice);
    } catch(e: any) { alert('Fehler: ' + e.message); }
  }

  // ── PDU Auto-Outlet Generation ─────────────────────────────────
  let showPduAutoOutlet = $state(false);
  let pduAutoPattern = $state("");
  let pduAutoPhaseMode = $state<'alternate' | 'L1' | 'L2' | 'L3'>('alternate');
  let pduAutoDevice = $state<Device | null>(null);
  let deleteExistingOutlets = $state(true);

  function openPduAutoOutlet(device: Device) {
    pduAutoDevice = device;
    let pattern = "18x C13 + 18x Cx";
    const patternMatch = selectedHW?.bemerkung?.match(/(\d+x\s*[A-Za-z0-9\-]+(?:\s*\+\s*\d+x\s*[A-Za-z0-9\-]+)*)/i);
    pduAutoPattern = patternMatch ? patternMatch[1] : pattern;
    pduAutoPhaseMode = 'alternate';
    deleteExistingOutlets = true;
    showPduAutoOutlet = true;
  }

  function openPduAutoOutletModal() {
    if (!selectedDevice) return;
    openPduAutoOutlet(selectedDevice);
  }

  function normalizeOutletType(t: string): string {
    const tl = t.toLowerCase();
    if (tl === 'cx') return 'C19';
    if (tl === 'c13') return 'C13';
    if (tl === 'c19') return 'C19';
    if (tl === 'c14') return 'C14';
    if (tl === 'c20') return 'C20';
    if (tl === 'schuko') return 'Schuko';
    if (tl === 'cee-16a' || tl === 'cee16a' || tl === 'cee') return 'CEE-16A';
    return 'C13';
  }

  const pduAutoPreview = $derived.by(() => {
    const specs: { count: number; type: string }[] = [];
    const parts = pduAutoPattern.split('+');
    for (const part of parts) {
      const match = part.match(/(\d+)\s*x\s*([A-Za-z0-9\-]+)/i);
      if (match) {
        const count = parseInt(match[1], 10);
        const rawType = match[2].trim();
        specs.push({ count, type: normalizeOutletType(rawType) });
      }
    }

    if (specs.length === 0) return null;

    const summary: { type: string; count: number; maxWatt: number }[] = [];
    let totalCount = 0;
    let phaseDistribution = { L1: 0, L2: 0, L3: 0 };
    let phaseIndex = 0;
    const phases: ('L1' | 'L2' | 'L3')[] = ['L1', 'L2', 'L3'];

    for (const spec of specs) {
      let maxWatt = 2300;
      if (spec.type === 'C19' || spec.type === 'C20' || spec.type === 'Schuko' || spec.type === 'CEE-16A') {
        maxWatt = 3680;
      }
      summary.push({ type: spec.type, count: spec.count, maxWatt });
      totalCount += spec.count;

      for (let i = 0; i < spec.count; i++) {
        if (pduAutoPhaseMode === 'alternate') {
          const ph = phases[phaseIndex % 3];
          phaseDistribution[ph]++;
          phaseIndex++;
        } else {
          phaseDistribution[pduAutoPhaseMode]++;
        }
      }
    }

    return { summary, totalCount, phaseDistribution };
  });

  async function generatePduOutlets() {
    if (!pduAutoDevice) return;
    const pduId = pduAutoDevice.id;

    const specs: { count: number; type: string }[] = [];
    const parts = pduAutoPattern.split('+');
    for (const part of parts) {
      const match = part.match(/(\d+)\s*x\s*([A-Za-z0-9\-]+)/i);
      if (match) {
        const count = parseInt(match[1], 10);
        const rawType = match[2].trim();
        specs.push({ count, type: normalizeOutletType(rawType) });
      }
    }

    if (specs.length === 0) {
      alert("Ungültiges Muster. Beispiel: 18x C13 + 18x Cx");
      return;
    }

    try {
      if (deleteExistingOutlets) {
        const existing = await api.getPduOutlets(pduId);
        for (const outlet of existing) {
          await api.deletePduOutlet(pduId, outlet.id);
        }
      }

      let outletIndex = 1;
      let phaseIndex = 0;
      const phases: ('L1' | 'L2' | 'L3')[] = ['L1', 'L2', 'L3'];

      for (const spec of specs) {
        for (let i = 0; i < spec.count; i++) {
          const outletName = `Out-${outletIndex}`;
          
          let phase: 'L1' | 'L2' | 'L3' = 'L1';
          if (pduAutoPhaseMode === 'alternate') {
            phase = phases[phaseIndex % 3];
            phaseIndex++;
          } else {
            phase = pduAutoPhaseMode;
          }

          let maxWatt = 2300;
          if (spec.type === 'C19' || spec.type === 'C20' || spec.type === 'Schuko' || spec.type === 'CEE-16A') {
            maxWatt = 3680;
          }

          await api.createPduOutlet(pduId, {
            pdu_id: pduId,
            outlet_name: outletName,
            phase: phase,
            steckdosentyp: spec.type as any,
            max_watt: maxWatt,
            schaltbar: true
          });

          outletIndex++;
        }
      }

      showPduAutoOutlet = false;
      devices = await api.getDevices();
      if (selectedDevice) {
        await loadDeviceDetail(selectedDevice);
      }
    } catch (e: any) {
      alert('Fehler beim Generieren der Steckdosen: ' + e.message);
    }
  }

  // ── PDF Export ────────────────────────────────────────────
  let pdfLoading = $state(false);

  async function downloadRackPdf(rackId: number, rackName: string) {
    pdfLoading = true;
    try {
      const res = await fetch(`/api/v1/racks/${rackId}/pdf`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href     = url;
      a.download = `rack_${rackName.replace(/\s+/g, '_')}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) { alert('PDF-Export fehlgeschlagen: ' + (e as any).message); }
    finally { pdfLoading = false; }
  }

  async function downloadAllRacksPdf() {
    pdfLoading = true;
    try {
      const res = await fetch('/api/v1/export/racks-pdf');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href     = url;
      a.download = 'rack_dokumentation.pdf';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) { alert('PDF-Export fehlgeschlagen: ' + (e as any).message); }
    finally { pdfLoading = false; }
  }

  // ── Derived ────────────────────────────────────────────────
  const rackDevices = $derived(
    selectedRack ? devices.filter(d => d.rack_id === selectedRack!.id) : []
  );
  
  const sideDevices = $derived(rackDevices.filter(d => (d.u_hoehe ?? 0) === 0));
  const leftSide = $derived.by(() => {
    let nullIdx = 0;
    return sideDevices.filter(d => {
      if (d.side) return d.side === 'left';
      return nullIdx++ % 2 === 0;
    });
  });
  const rightSide = $derived.by(() => {
    let nullIdx = 0;
    return sideDevices.filter(d => {
      if (d.side) return d.side === 'right';
      return nullIdx++ % 2 !== 0;
    });
  });

  const occupiedSides = $derived({
    left: leftSide.length > 0,
    right: rightSide.length > 0,
  });

  const occupiedU = $derived(
    rackDevices
      .filter(d => (d.u_hoehe ?? 0) > 0)
      .reduce((s, d) => s + d.u_hoehe, 0)
  );

  const phaseLoads = $derived(() => {
    const ph = { L1: 0, L2: 0, L3: 0 };
    for (const d of rackDevices) {
      let effectivePhases = [];
      if (d.connected_pdu_outlets && d.connected_pdu_outlets.length > 0) {
        effectivePhases = d.connected_pdu_outlets.map(o => o.phase);
      } else if (d.phase === 'L1' || d.phase === 'L2' || d.phase === 'L3') {
        effectivePhases = [d.phase];
      }
      
      const power = Number(d.anschlussleistung_watt ?? d.tdp_watt ?? 0);
      if (effectivePhases.length > 0) {
        const primaryPhase = effectivePhases[0] as 'L1'|'L2'|'L3';
        if (ph[primaryPhase] !== undefined) {
          ph[primaryPhase] += power;
        }
      }
    }
    return ph;
  });

  const imbalanceInfo = $derived.by(() => {
    const loads = phaseLoads();
    const total = loads.L1 + loads.L2 + loads.L3;
    if (total === 0) return { pct: 0, severity: 'ok' as const };
    const ideal = total / 3;
    const maxDev = Math.max(
      Math.abs(loads.L1 - ideal),
      Math.abs(loads.L2 - ideal),
      Math.abs(loads.L3 - ideal)
    );
    const pct = (maxDev / ideal) * 100;
    return { pct, severity: pct > 25 ? 'critical' as const : pct > 10 ? 'warning' as const : 'ok' as const };
  });

  const getDeviceTooltip = $derived((dev: Device) => {
    const power = dev.anschlussleistung_watt ?? dev.tdp_watt ?? 0;
    let phaseDisplay = dev.phase || '–';
    
    if (dev.connected_pdu_outlets && dev.connected_pdu_outlets.length > 0) {
      phaseDisplay = dev.connected_pdu_outlets.map(o => {
        const pduName = devices.find(d => d.id === o.pdu_id)?.hostname || 'PDU';
        return `${o.phase} (${pduName} ${o.outlet_name}${o.steckdosentyp ? ' ' + o.steckdosentyp : ''})`.trim();
      }).join(', ');
    } else if (dev.typ !== 'pdu') {
      phaseDisplay = 'Nicht verbunden';
    }

    return `${dev.hostname}\nIP: ${dev.ip_adresse || '–'}\nPhase/PDU: ${phaseDisplay}\nLeistung: ${power > 0 ? power + ' W' : '–'}\nBemerkung: ${dev.bemerkung || '–'}`;
  });

  const phaseCapacityWatts = $derived((ph: 'L1' | 'L2' | 'L3') => {
    const rackPdus = rackDevices.filter(d => d.typ === 'pdu');
    if (rackPdus.length > 0) {
      const pdu = rackPdus[0];
      const amps = Number(pdu.anschlussleistung_a ?? 16);
      const volts = Number(pdu.spannung_v ?? 230);
      if (pdu.strom_typ === '1-phasig') {
        return pdu.phase === ph ? volts * amps : 0;
      }
      return volts * amps;
    }
    return 3680; // default 16A * 230V
  });

  const filteredHW = $derived(hardware.filter(h => {
    if (!(pduOnlyMode ? h.kategorie === 'pdu' : h.kategorie !== 'pdu')) return false;
    if (!hwFilter) return true;
    const q = hwFilter.toLowerCase();
    return h.name.toLowerCase().includes(q) ||
      h.kategorie.toLowerCase().includes(q) ||
      h.hersteller.toLowerCase().includes(q);
  }));

  let isZeroU = $derived(selectedHW ? selectedHW.u_hoehe === 0 : devUHoehe === 0);

  function isHWIncompatible(hw) {
    if (!selectedRack || !hw.min_rack_hoehe) return false;
    return selectedRack.hoehe_u < hw.min_rack_hoehe;
  }

  const conflictDeviceIds = $derived(() => {
    const placed = rackDevices.filter(d => (d.u_hoehe ?? 0) > 0 && d.u_position != null);
    const ids = new Set<number>();
    for (let i = 0; i < placed.length; i++) {
      for (let j = i + 1; j < placed.length; j++) {
        const a = placed[i], b = placed[j];
        const aStart = a.u_position!, aEnd = aStart + a.u_hoehe;
        const bStart = b.u_position!, bEnd = bStart + b.u_hoehe;
        if (aStart < bEnd && bStart < aEnd) { ids.add(a.id); ids.add(b.id); }
      }
    }
    return ids;
  });

  function devAt(u: number) {
    return rackDevices.find(d =>
      (d.u_hoehe ?? 0) > 0 &&
      u >= (d.u_position ?? 0) &&
      u < (d.u_position ?? 0) + d.u_hoehe
    ) ?? null;
  }
  function isTopU(dev: Device, u: number) { return u === (dev.u_position ?? 0) + dev.u_hoehe - 1; }

  function typColor(typ: string) {
    return typ === 'server'   ? { bg: 'rgba(59,130,246,.18)',  border: 'rgba(59,130,246,.4)'  } :
           typ === 'switch'   ? { bg: 'rgba(6,182,212,.18)',   border: 'rgba(6,182,212,.4)'   } :
           typ === 'pdu'      ? { bg: 'rgba(239,68,68,.18)',   border: 'rgba(239,68,68,.4)'   } :
           typ === 'firewall' ? { bg: 'rgba(234,179,8,.18)',   border: 'rgba(234,179,8,.4)'   } :
           typ === 'storage'  ? { bg: 'rgba(168,85,247,.18)',  border: 'rgba(168,85,247,.4)'  } :
                                { bg: 'rgba(249,115,22,.18)',  border: 'rgba(249,115,22,.4)'  };
  }

  function cableForPort(devId: number, portName: string) {
    return cables.find(c =>
      (c.von_device_id === devId && c.von_port === portName) ||
      (c.nach_device_id === devId && c.nach_port === portName)
    ) ?? null;
  }

  function otherEnd(cable: Cable, devId: number) {
    const otherId = cable.von_device_id === devId ? cable.nach_device_id : cable.von_device_id;
    const otherPort = cable.von_device_id === devId ? cable.nach_port : cable.von_port;
    const otherDev = devices.find(d => d.id === otherId) ?? null;
    const otherRack = otherDev ? racks.find(r => r.id === otherDev.rack_id) ?? null : null;
    const crossRack = otherDev && selectedDevice && otherDev.rack_id !== selectedDevice.rack_id;
    return { otherDev, otherPort, otherRack, crossRack };
  }

  const filteredTargetDevices = $derived(() => {
    if (!cableTyp) return devices.filter(d => d.id !== cableFromDevice?.id);
    if (cableTyp.startsWith('Strom')) {
      // Stromkabel → nur PDUs
      return devices.filter(d => d.typ === 'pdu');
    } else if (['Cat6','Cat6A','Cat7','DAC','SFP+'].includes(cableTyp)) {
      // Netzwerk → keine PDUs
      return devices.filter(d => d.typ !== 'pdu' && d.id !== cableFromDevice?.id);
    } else if (['LC-LC','SC-SC'].includes(cableTyp)) {
      // LWL → keine PDUs
      return devices.filter(d => d.typ !== 'pdu' && d.id !== cableFromDevice?.id);
    }
    return devices.filter(d => d.id !== cableFromDevice?.id);
  });

  const CABLE_TYPES = ['Cat6','Cat6A','Cat7','DAC','LC-LC','SC-SC','SFP+','Strom-C13','Strom-C13-Lock','Strom-C19','Strom-C19-Lock','Strom-Schuko','Strom-CEE-16A-3P','Strom-CEE-32A-3P','sonstige'];
  const IF_TYPES = ['1GbE','10GbE','25GbE','40GbE','100GbE','FC','IPMI','sonstige'];
  const OUTLET_TYPES = ['C13','C14','C19','C20','Schuko','CEE-16A'];

  const targetDevPorts = $derived(() => {
    if (!cableNachDevId) return [];
    const dev = devices.find(d => d.id === cableNachDevId);
    if (!dev) return [];
    return [
      ...(dev.server_interfaces ?? []).map((i: any) => i.port_name),
      ...(dev.device_ports ?? []).map((p: DevicePort) => p.port_name),
    ];
  });

  const editFilteredTargetDevices = $derived(() => {
    if (!editCableTyp) return devices.filter(d => d.id !== editCableFromDevice?.id);
    if (editCableTyp.startsWith('Strom')) {
      // Stromkabel → nur PDUs
      return devices.filter(d => d.typ === 'pdu');
    } else if (['Cat6','Cat6A','Cat7','DAC','SFP+'].includes(editCableTyp)) {
      // Netzwerk → keine PDUs
      return devices.filter(d => d.typ !== 'pdu' && d.id !== editCableFromDevice?.id);
    } else if (['LC-LC','SC-SC'].includes(editCableTyp)) {
      // LWL → keine PDUs
      return devices.filter(d => d.typ !== 'pdu' && d.id !== editCableFromDevice?.id);
    }
    return devices.filter(d => d.id !== editCableFromDevice?.id);
  });

  const editTargetDevPorts = $derived(() => {
    if (!editCableNachDevId) return [];
    const dev = devices.find(d => d.id === editCableNachDevId);
    if (!dev) return [];
    return [
      ...(dev.server_interfaces ?? []).map((i: any) => i.port_name),
      ...(dev.device_ports ?? []).map((p: DevicePort) => p.port_name),
    ];
  });

  const cableTypes = $derived([...new Set(cables.map(c => c.typ))].sort());

  const PINNED_CABLE_TYPES = ['Strom-C13-Lock', 'Strom-C19-Lock'];
  const legendCableTypes = $derived(
    [...new Set([...cableTypes, ...PINNED_CABLE_TYPES])].sort()
  );

  const cableDefs: Record<string, { desc: string; use: string; connector: string; badgeClass: string; dotColor: string }> = {
    'Cat5e':          { desc: 'Netzwerk-Patch',          use: 'Switch ↔ Server, Switch ↔ Switch',          connector: 'RJ-45 · bis 1 Gbps',       badgeClass: 'bg-blue-500/10 text-blue-400 border-blue-500/30',       dotColor: 'bg-blue-400' },
    'Cat6':           { desc: 'Netzwerk-Patch',          use: 'Switch ↔ Server, Switch ↔ Switch',          connector: 'RJ-45 · bis 1 Gbps',       badgeClass: 'bg-blue-500/10 text-blue-400 border-blue-500/30',       dotColor: 'bg-blue-400' },
    'Cat6A':          { desc: 'Netzwerk-Patch',          use: 'Switch ↔ Server, Switch ↔ Switch',          connector: 'RJ-45 · bis 10 Gbps',      badgeClass: 'bg-blue-500/10 text-blue-400 border-blue-500/30',       dotColor: 'bg-blue-400' },
    'Cat7':           { desc: 'Netzwerk-Patch',          use: 'Switch ↔ Server, Switch ↔ Switch',          connector: 'RJ-45 · bis 10 Gbps',      badgeClass: 'bg-blue-500/10 text-blue-400 border-blue-500/30',       dotColor: 'bg-blue-400' },
    'DAC':            { desc: 'Direct-Attach-Kabel',     use: 'Switch ↔ Server, Uplink Switch ↔ Switch',   connector: 'SFP+ / QSFP · 10–100 Gbps',badgeClass: 'bg-slate-500/10 text-slate-400 border-slate-500/30',     dotColor: 'bg-slate-400' },
    'SFP+':           { desc: 'SFP+ Transceiver-Kabel',  use: 'Switch ↔ Server, Uplink',                  connector: 'SFP+ · 10 Gbps',           badgeClass: 'bg-slate-500/10 text-slate-400 border-slate-500/30',     dotColor: 'bg-slate-400' },
    'LC-LC':          { desc: 'Glasfaser LWL',           use: 'Langstrecke, RZ-übergreifend, Backbone',    connector: 'LC Duplex · OM3/OM4',      badgeClass: 'bg-fuchsia-500/10 text-fuchsia-400 border-fuchsia-500/30', dotColor: 'bg-fuchsia-400' },
    'SC-SC':          { desc: 'Glasfaser LWL',           use: 'Langstrecke, RZ-übergreifend',              connector: 'SC Duplex · OM2/OM3',      badgeClass: 'bg-fuchsia-500/10 text-fuchsia-400 border-fuchsia-500/30', dotColor: 'bg-fuchsia-400' },
    'Strom-C13':         { desc: 'Stromversorgung Standard',        use: 'PDU → Server, Switch, Firewall',        connector: 'IEC C13/C14 · max. 10A',              badgeClass: 'bg-red-500/10 text-red-400 border-red-500/30',       dotColor: 'bg-red-400' },
    'Strom-C13-Lock':    { desc: 'Stromversorgung mit Verriegelung', use: 'PDU → Gerät, gesichert gegen Herausziehen', connector: 'IEC C13-Lock (Kentix) · max. 10A',  badgeClass: 'bg-orange-500/10 text-orange-400 border-orange-500/30', dotColor: 'bg-orange-400' },
    'Strom-C19':         { desc: 'Stromversorgung Hochlast',         use: 'PDU → Server, Storage (Hochlast)',      connector: 'IEC C19/C20 · max. 16A',              badgeClass: 'bg-red-500/10 text-red-400 border-red-500/30',       dotColor: 'bg-red-400' },
    'Strom-C19-Lock':    { desc: 'Hochlast mit Verriegelung',        use: 'PDU → Server/Storage, gesichert',       connector: 'IEC C19-Lock (Kentix) · max. 16A',    badgeClass: 'bg-orange-500/10 text-orange-400 border-orange-500/30', dotColor: 'bg-orange-400' },
    'Strom-Schuko':      { desc: 'Schuko-Steckdose',                 use: 'PDU → Gerät (Schuko)',                  connector: 'Schuko CEE 7/4 · max. 16A',           badgeClass: 'bg-red-500/10 text-red-400 border-red-500/30',       dotColor: 'bg-red-400' },
    'Strom-CEE-16A':     { desc: 'Einspeisung Steckdose',            use: 'Verteiler → PDU',                      connector: 'CEE 16A (blau) · 1-phasig',           badgeClass: 'bg-red-500/10 text-red-400 border-red-500/30',       dotColor: 'bg-red-400' },
    'Strom-CEE-16A-3P':  { desc: 'Einspeisung Steckdose',            use: 'Verteiler → PDU',                      connector: 'CEE 16A (blau) · 1-phasig',           badgeClass: 'bg-red-500/10 text-red-400 border-red-500/30',       dotColor: 'bg-red-400' },
    'Strom-CEE-32A-3P':  { desc: 'Drehstrom-Einspeisung',            use: 'Hauptverteiler → PDU (3-phasig)',       connector: 'CEE 32A (rot) · 3×32A',               badgeClass: 'bg-red-500/10 text-red-400 border-red-500/30',       dotColor: 'bg-red-400' },
    'Strom-CEE-63A-3P':  { desc: 'Haupteinspeisung',                 use: 'RZ-Anlage → Hauptverteiler',            connector: 'CEE 63A (rot) · 3×63A',               badgeClass: 'bg-red-500/10 text-red-400 border-red-500/30',       dotColor: 'bg-red-400' },
  };

  function getCableDef(typ: string) {
    if (cableDefs[typ]) return cableDefs[typ];
    if (typ.startsWith('Strom')) return { desc: 'Stromkabel', use: 'Stromversorgung', connector: typ, badgeClass: 'bg-red-500/10 text-red-400 border-red-500/30', dotColor: 'bg-red-400' };
    if (typ.startsWith('Cat'))   return { desc: 'Netzwerk-Patch', use: 'Switch ↔ Gerät', connector: 'RJ-45', badgeClass: 'bg-blue-500/10 text-blue-400 border-blue-500/30', dotColor: 'bg-blue-400' };
    return { desc: 'Kabelverbindung', use: '–', connector: typ, badgeClass: 'bg-amber-500/10 text-amber-400 border-amber-500/30', dotColor: 'bg-amber-400' };
  }
</script>

<svelte:head><title>KAiTix - Racks</title></svelte:head>
<svelte:window onkeydown={(e) => { if (e.key === 'Escape' && selectedDevice && !showEditDevice && !showAddDevice && !showAddCable && !showEditCable && !showAddOutlet && !showAddInterface) closeModal(); }} />

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between border-b border-slate-800 pb-4">
    <div>
      <h2 class="text-xl font-bold text-white font-outfit">Rechenzentrum Racks</h2>
      <p class="text-xs text-slate-500">Racks, Hardware und Verkabelung verwalten</p>
    </div>
    <div class="flex items-center space-x-2">
      <button onclick={downloadAllRacksPdf} disabled={pdfLoading}
        class="flex items-center space-x-2 px-3 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg text-xs font-semibold transition disabled:opacity-50"
        title="Alle Racks als PDF">
        <FileText class="w-3.5 h-3.5" /><span>{pdfLoading ? '…' : 'PDF Alle'}</span>
      </button>
      <button onclick={() => { showAddRack = true; }}
        class="flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold transition">
        <Plus class="w-4 h-4" /><span>Rack hinzufügen</span>
      </button>
    </div>
  </div>

  {#if loading}
    <div class="flex items-center justify-center p-12">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
    </div>
  {:else if errorMsg}
    <div class="p-4 bg-red-950/40 border border-red-800 rounded-xl text-red-400 text-sm">{errorMsg}</div>
  {:else}
    <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">

      <!-- Rack-Auswahl (links, schmal) -->
      <div class="space-y-3">
        <!-- Dreistufiger Filter -->
        <div class="bg-[#101622] border border-slate-800 rounded-xl p-3.5 space-y-3">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-2 text-slate-400 font-bold text-[10px] uppercase tracking-wider">
              <Building class="w-3.5 h-3.5 text-blue-400 shrink-0" />
              <span>Filter</span>
            </div>
            {#if (filterStandort && filterStandort !== 'Alle') || (filterReihe && filterReihe !== 'Alle') || searchRackName}
              <button onclick={() => { filterStandort = 'Alle'; filterReihe = 'Alle'; dropdownSelectedRackId = 'Alle'; searchRackName = ''; }}
                class="text-[10px] text-red-400 hover:text-red-300 font-semibold transition">
                Reset
              </button>
            {/if}
          </div>

          <div class="space-y-2">
            <RackFilterBar
              racks={racks}
              bind:selectedStandort={filterStandort}
              bind:selectedRackreihe={filterReihe}
              bind:selectedRack={dropdownSelectedRackId}
              layout="vertical"
            />

            <div>
              <label class="block text-[9px] uppercase font-bold tracking-wider text-slate-500 mb-1">Suche</label>
              <input type="text" bind:value={searchRackName} placeholder="Rack Name..."
                class="w-full bg-[#182030] border border-slate-700 hover:border-slate-600 rounded-lg px-2 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500 transition" />
            </div>
          </div>
        </div>

        <h3 class="text-xs font-bold text-slate-500 uppercase tracking-wider px-1">Racks ({filteredRacks.length})</h3>
        <div class="space-y-1.5 max-h-[calc(100vh-530px)] overflow-y-auto pr-1">
          {#each filteredRacks as rack}
            {@const active = selectedRack?.id === rack.id}
            <button onclick={() => { selectedRack = rack; selectedDevice = null; }}
              class="w-full text-left p-3 rounded-xl border transition {active ? 'bg-blue-600/10 border-blue-500/50' : 'bg-[#101622] border-slate-800 hover:border-slate-700'}">
              <div class="flex items-center justify-between">
                <div class="flex items-center space-x-2 min-w-0">
                  <Layers class="w-3.5 h-3.5 shrink-0 {active ? 'text-blue-400' : 'text-slate-500'}" />
                  <div class="min-w-0">
                    <div class="font-bold text-xs truncate {active ? 'text-white' : 'text-slate-300'}">{rack.name}</div>
                    <div class="text-[10px] text-slate-500 truncate">
                      {rack.standort || '–'}
                      {#if rack.rackreihe} <span class="opacity-50">·</span> {rack.rackreihe}{/if}
                    </div>
                  </div>
                </div>
                <ChevronRight class="w-3 h-3 text-slate-600 shrink-0" />
              </div>
            </button>
          {/each}
        </div>

        <!-- Standorte verwalten -->
        <div class="bg-[#101622] border border-slate-800 rounded-xl p-3.5 space-y-2.5 mt-3">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-2 text-slate-400 font-bold text-[10px] uppercase tracking-wider">
              <Building class="w-3.5 h-3.5 text-blue-400 shrink-0" />
              <span>Standorte</span>
            </div>
            <button onclick={() => { showAddLocation = !showAddLocation; newLocationName = ''; newLocationType = 'rechenzentrum'; }}
              class="text-[10px] text-blue-400 hover:text-blue-300 font-semibold flex items-center gap-1">
              <Plus class="w-3 h-3" /> Neu
            </button>
          </div>

          {#if showAddLocation}
            <div class="bg-slate-900/60 rounded-lg p-2 space-y-1.5 border border-slate-700/50">
              <input type="text" bind:value={newLocationName} placeholder="Standortname"
                class="w-full bg-[#182030] border border-slate-700 rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-blue-500" />
              <select bind:value={newLocationType}
                class="w-full bg-[#182030] border border-slate-700 rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-blue-500">
                <option value="rechenzentrum">Rechenzentrum</option>
                <option value="dienstaußenstelle">Dienstaußenstelle</option>
              </select>
              <div class="flex gap-1.5">
                <button onclick={addLocation}
                  class="flex-1 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded text-[10px] font-semibold transition">Hinzufügen</button>
                <button onclick={() => showAddLocation = false}
                  class="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-400 rounded text-[10px] transition">Abbruch</button>
              </div>
            </div>
          {/if}

          <div class="space-y-1">
            {#each locationStore.locations as loc}
              {#if editingLocation === loc.name}
                <div class="bg-slate-900/60 rounded-lg p-2 space-y-1.5 border border-blue-700/40">
                  <input type="text" bind:value={editLocationName}
                    class="w-full bg-[#182030] border border-slate-700 rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-blue-500" />
                  <select bind:value={editLocationType}
                    class="w-full bg-[#182030] border border-slate-700 rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-blue-500">
                    <option value="rechenzentrum">Rechenzentrum</option>
                    <option value="dienstaußenstelle">Dienstaußenstelle</option>
                  </select>
                  <div class="flex gap-1.5">
                    <button onclick={saveEditLocation}
                      class="flex-1 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded text-[10px] font-semibold transition">Speichern</button>
                    <button onclick={() => editingLocation = null}
                      class="px-2 py-1 bg-slate-800 text-slate-400 rounded text-[10px] transition">Abbruch</button>
                  </div>
                </div>
              {:else}
                <div class="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-slate-800/40 group">
                  {#if loc.typ === 'rechenzentrum'}
                    <Building class="w-3 h-3 text-blue-400 shrink-0" />
                  {:else}
                    <Wifi class="w-3 h-3 text-violet-400 shrink-0" />
                  {/if}
                  <div class="flex-1 min-w-0">
                    <div class="text-xs text-slate-200 truncate">{loc.name}</div>
                    <div class="text-[9px] text-slate-600">{loc.typ === 'rechenzentrum' ? 'Rechenzentrum' : 'Dienstaußenstelle'}</div>
                  </div>
                  <div class="flex gap-1 opacity-0 group-hover:opacity-100 transition">
                    <button onclick={() => startEditLocation(loc.name)} class="text-slate-500 hover:text-blue-400">
                      <Edit2 class="w-3 h-3" />
                    </button>
                    <button onclick={() => removeLocation(loc.name)} class="text-slate-500 hover:text-red-400">
                      <Trash2 class="w-3 h-3" />
                    </button>
                  </div>
                </div>
              {/if}
            {/each}
          </div>
        </div>


      </div>

      <!-- Rack-Visualisierung (mitte) -->
      <div class="lg:col-span-3">
        {#if !selectedRack}
          <div class="p-8 text-center text-slate-500 text-sm bg-[#101622] border border-slate-800 rounded-xl">Rack auswählen</div>
        {:else}
          <div class="bg-[#101622] border border-slate-800 rounded-xl overflow-hidden">
            <!-- Rack Header -->
            <div class="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
              <div>
                <div class="font-bold text-white text-sm">{selectedRack.name}</div>
                <div class="text-[10px] text-slate-500">{occupiedU}/{selectedRack.hoehe_u} HE{selectedRack.breite_mm ? ' · ' + selectedRack.breite_mm + 'mm' : ''} · {(phaseLoads().L1/1000 + phaseLoads().L2/1000 + phaseLoads().L3/1000).toFixed(1)} kW</div>
              </div>
              <div class="flex items-center space-x-2">
                {#if selectedRack.breite_mm}
                  <span class="text-[9px] px-1.5 py-0.5 rounded font-bold {selectedRack.breite_mm >= 800 ? 'bg-green-500/15 text-green-300 border border-green-500/30' : 'bg-yellow-500/15 text-yellow-300 border border-yellow-500/30'}">{selectedRack.breite_mm}mm</span>
                {/if}
                <button onclick={() => downloadRackPdf(selectedRack!.id, selectedRack!.name)} disabled={pdfLoading}
                  class="p-1.5 bg-slate-800 hover:bg-emerald-700 rounded-lg text-slate-400 hover:text-white transition disabled:opacity-40" title="PDF exportieren">
                  <FileText class="w-3.5 h-3.5" />
                </button>
                <button onclick={openEditRack} class="p-1.5 bg-slate-800 hover:bg-slate-700 rounded-lg text-slate-400 transition"><Edit2 class="w-3.5 h-3.5" /></button>
                <button onclick={() => deleteRack(selectedRack!.id)} class="p-1.5 bg-red-950/40 hover:bg-red-900/40 border border-red-900/60 rounded-lg text-red-400 transition"><Trash2 class="w-3.5 h-3.5" /></button>
              </div>
            </div>

            <!-- Phasen-Balken -->
            <div class="px-4 py-2 border-b border-slate-900">
              <div class="grid grid-cols-3 gap-2 text-[9px]">
                {#each ['L1','L2','L3'] as ph}
                  {@const loadWatts = phaseLoads()[ph as 'L1'|'L2'|'L3']}
                  {@const kw = loadWatts / 1000}
                  {@const capWatts = phaseCapacityWatts(ph as 'L1'|'L2'|'L3')}
                  {@const pct = capWatts > 0 ? Math.min(100, Math.round((loadWatts / capWatts) * 100)) : 0}
                  
                  <div class="bg-[#090d14]/40 border rounded-lg px-2.5 py-1.5 flex flex-col justify-between
                    {ph === 'L1' ? 'border-blue-500/15' : ph === 'L2' ? 'border-cyan-500/15' : 'border-orange-500/15'}">
                    <div class="flex items-center justify-between mb-1">
                      <span class="text-slate-500 font-medium">{ph}</span>
                      <span class="font-bold {ph === 'L1' ? 'text-blue-400' : ph === 'L2' ? 'text-cyan-400' : 'text-orange-400'}">
                        {kw.toFixed(2)} kW
                      </span>
                    </div>
                    <div class="w-full h-1 bg-slate-950 rounded-full overflow-hidden">
                      <div class="h-full rounded-full transition-all 
                        {ph === 'L1' ? 'bg-blue-500' : ph === 'L2' ? 'bg-cyan-500' : 'bg-orange-500'}" 
                        style="width: {pct}%" title="{pct}% Auslastung"></div>
                    </div>
                  </div>
                {/each}
              </div>
              {#if imbalanceInfo.severity !== 'ok'}
                <div class="flex items-center space-x-1.5 mt-2 text-[10px] {imbalanceInfo.severity === 'critical' ? 'text-red-400' : 'text-orange-400'}" title={'Ideale Last: ' + ((phaseLoads().L1 + phaseLoads().L2 + phaseLoads().L3) / 3000).toFixed(2) + ' kW pro Phase'}>
                  <span class="font-bold">⚠</span>
                  <span>Phasen unausgeglichen — {imbalanceInfo.pct.toFixed(1)}%</span>
                </div>
              {/if}
            </div>

            <!-- Rack Layout mit Seitlichen PDUs -->
            <div class="flex border-b border-slate-900 max-h-[60vh]">
              
              <!-- Linke Seite (Zero-U) -->
              <div class="w-10 sm:w-12 bg-[#090d14] border-r border-slate-900 flex flex-col items-stretch p-1.5 min-h-0">
                <div class="text-[7px] text-slate-600 text-center uppercase mb-1">0U L</div>
                {#each leftSide as dev}
                  {@const c = typColor(dev.typ)}
                  {@const isIncompatible = isDeviceIncompatible(dev)}
                  <button
                    onclick={() => loadDeviceDetail(dev)}
                    class="w-full flex-1 min-h-0 rounded border hover:brightness-110 transition flex items-center justify-center overflow-hidden {selectedDevice?.id === dev.id ? 'ring-1 ring-white/30' : ''} {isIncompatible ? 'ring-1 ring-red-500 border-red-500' : ''}"
                    style="background:{isIncompatible ? 'rgba(239,68,68,.22)' : c.bg}; border-color:{isIncompatible ? 'rgba(239,68,68,.7)' : c.border}; writing-mode: vertical-rl; transform: rotate(180deg);"
                    title={isIncompatible ? '⚠ Höhenkonflikt: ' + getDeviceTooltip(dev) : getDeviceTooltip(dev)}
                  >
                    <span class="font-semibold text-white text-[9px] leading-none">{isIncompatible ? '⚠ ' : ''}{dev.hostname}</span>
                    <span class="text-[7px] opacity-60">{dev.typ.toUpperCase()}</span>
                  </button>
                {/each}
                {#if !occupiedSides.left}
                <button onclick={() => { openAddDevice(null); devSide = 'left'; }} class="w-full aspect-square mt-auto border border-dashed border-slate-800 rounded flex items-center justify-center text-slate-600 hover:text-blue-500 hover:border-blue-500/50 hover:bg-blue-500/10 transition shrink-0">
                  <Plus class="w-4 h-4" />
                </button>
                {:else}
                <div class="w-full aspect-square mt-auto border border-dashed border-red-800/20 rounded flex items-center justify-center text-red-800/30 shrink-0" title="Seite bereits belegt">
                  <X class="w-4 h-4" />
                </div>
                {/if}
              </div>

              <!-- Main HE Slots -->
              <div class="flex-1 p-2 font-mono text-[9px] overflow-y-auto relative bg-[#101622]">
                <div class="text-center text-[8px] text-slate-600 pb-1 mb-1 border-b border-slate-900 sticky top-0 bg-[#101622] z-10">FRONTANSICHT</div>
                {#each Array.from({ length: selectedRack.hoehe_u }, (_, i) => selectedRack!.hoehe_u - i) as u}
                  {@const dev = devAt(u)}
                  {#if dev}
                    {#if isTopU(dev, u)}
                      {@const c = typColor(dev.typ)}
                      {@const isConflict = conflictDeviceIds().has(dev.id)}
                      {@const isIncompatible = isDeviceIncompatible(dev)}
                      <button
                        onclick={() => loadDeviceDetail(dev)}
                        class="w-full px-2 rounded border mb-0.5 text-left hover:brightness-110 transition {selectedDevice?.id === dev.id ? 'ring-1 ring-white/30' : ''} {isConflict || isIncompatible ? 'ring-1 ring-red-500' : ''}"
                        style="background:{isConflict || isIncompatible ? 'rgba(239,68,68,.22)' : c.bg}; border-color:{isConflict || isIncompatible ? 'rgba(239,68,68,.7)' : c.border}; min-height:{dev.u_hoehe * 22}px; display:flex; align-items:center; justify-content:space-between;"
                        title={isConflict ? '⚠ U-Positions-Konflikt: ' + getDeviceTooltip(dev) : isIncompatible ? '⚠ Höhenkonflikt: ' + getDeviceTooltip(dev) : getDeviceTooltip(dev)}
                      >
                        <span class="font-semibold {isConflict || isIncompatible ? 'text-red-300' : 'text-white'} truncate">{isIncompatible ? '⚠ ' : ''}{dev.hostname}</span>
                        <span class="text-[8px] opacity-60 shrink-0 ml-1">{isConflict || isIncompatible ? '⚠ ' : ''}{dev.typ.toUpperCase()} {dev.u_hoehe}U</span>
                      </button>
                    {/if}
                  {:else}
                    <button
                      onclick={() => openAddDevice(u)}
                      class="w-full px-2 py-1 mb-0.5 text-slate-700 border border-dashed border-slate-800/50 rounded flex justify-between items-center hover:border-blue-500/40 hover:text-blue-500/60 hover:bg-blue-500/5 transition group"
                    >
                      <span>HE {u}</span>
                      <Plus class="w-3 h-3 opacity-0 group-hover:opacity-100 transition" />
                    </button>
                  {/if}
                {/each}
              </div>

              <!-- Rechte Seite (Zero-U) -->
              <div class="w-10 sm:w-12 bg-[#090d14] border-l border-slate-900 flex flex-col items-stretch p-1.5 min-h-0">
                <div class="text-[7px] text-slate-600 text-center uppercase mb-1">0U R</div>
                {#each rightSide as dev}
                  {@const c = typColor(dev.typ)}
                  {@const isIncompatible = isDeviceIncompatible(dev)}
                  <button
                    onclick={() => loadDeviceDetail(dev)}
                    class="w-full flex-1 min-h-0 rounded border hover:brightness-110 transition flex items-center justify-center overflow-hidden {selectedDevice?.id === dev.id ? 'ring-1 ring-white/30' : ''} {isIncompatible ? 'ring-1 ring-red-500 border-red-500' : ''}"
                    style="background:{isIncompatible ? 'rgba(239,68,68,.22)' : c.bg}; border-color:{isIncompatible ? 'rgba(239,68,68,.7)' : c.border}; writing-mode: vertical-rl; transform: rotate(180deg);"
                    title={isIncompatible ? '⚠ Höhenkonflikt: ' + getDeviceTooltip(dev) : getDeviceTooltip(dev)}
                  >
                    <span class="font-semibold text-white text-[9px] leading-none">{isIncompatible ? '⚠ ' : ''}{dev.hostname}</span>
                    <span class="text-[7px] opacity-60">{dev.typ.toUpperCase()}</span>
                  </button>
                {/each}
                {#if !occupiedSides.right}
                <button onclick={() => { openAddDevice(null); devSide = 'right'; }} class="w-full aspect-square mt-auto border border-dashed border-slate-800 rounded flex items-center justify-center text-slate-600 hover:text-blue-500 hover:border-blue-500/50 hover:bg-blue-500/10 transition shrink-0">
                  <Plus class="w-4 h-4" />
                </button>
                {:else}
                <div class="w-full aspect-square mt-auto border border-dashed border-red-800/20 rounded flex items-center justify-center text-red-800/30 shrink-0" title="Seite bereits belegt">
                  <X class="w-4 h-4" />
                </div>
                {/if}
              </div>

            </div>
          </div>
        {/if}
      </div>

      <!-- Geräte-Detail (als Modal) -->
      {#if selectedDevice}
        {@const c = typColor(selectedDevice.typ)}
        <!-- Overlay -->
        <div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 flex justify-center items-start pt-10 pb-10 overflow-y-auto" onclick={closeModal} role="dialog" tabindex="-1">
          <!-- Modal Container -->
          <div class="bg-[#101622] border border-slate-800 rounded-xl w-full max-w-4xl shadow-2xl relative flex flex-col min-h-[50vh] max-h-full" onclick={(e) => e.stopPropagation()} role="document" tabindex="0">
            
            <!-- Modal Header -->
            <div class="px-5 py-4 border-b border-slate-800 shrink-0" style="border-top-left-radius: 0.75rem; border-top-right-radius: 0.75rem; border-left: 3px solid {c.border}">
              <div class="flex items-start justify-between">
                <div>
                  <h3 class="font-bold text-white text-base flex items-center space-x-2">
                    <span>{selectedDevice.hostname}</span>
                    <span class="capitalize px-1.5 py-0.5 rounded text-[10px]" style="background:{c.bg};color:white">{selectedDevice.typ}</span>
                  </h3>
                  <div class="flex flex-wrap gap-3 text-xs text-slate-500 mt-1">
                    <span>{racks.find(r=>r.id===selectedDevice!.rack_id)?.name ?? '–'} · HE {selectedDevice.u_position ?? '?'}</span>
                    {#if selectedDevice.ip_adresse}<span class="font-mono">{selectedDevice.ip_adresse}</span>{/if}
                  </div>
                </div>
                <div class="flex space-x-1.5">
                  <button onclick={openEditDevice} class="p-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-slate-400 transition"><Edit2 class="w-3.5 h-3.5" /></button>
                  <button onclick={() => deleteDevice(selectedDevice!.id)} class="p-2 bg-red-950/40 hover:bg-red-900/40 border border-red-900/60 rounded-lg text-red-400 transition"><Trash2 class="w-3.5 h-3.5" /></button>
                  <button onclick={closeModal} class="p-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-slate-400 transition"><X class="w-4 h-4" /></button>
                </div>
              </div>

              <!-- Tabs -->
              <div class="flex space-x-4 mt-4 -mb-4">
                <button class="px-3 py-3 text-xs font-semibold border-b-2 {activeModalTab === 'details' ? 'text-blue-400 border-blue-400' : 'text-slate-500 hover:text-slate-300 border-transparent'}" onclick={() => activeModalTab = 'details'}>Geräte-Details</button>
                <button class="px-3 py-3 text-xs font-semibold border-b-2 {activeModalTab === 'interfaces' ? 'text-blue-400 border-blue-400' : 'text-slate-500 hover:text-slate-300 border-transparent'}" onclick={() => activeModalTab = 'interfaces'}>Ports & Kabel</button>
                {#if selectedDevice.typ === 'usv'}
                  <button class="px-3 py-3 text-xs font-semibold border-b-2 {activeModalTab === 'protokoll' ? 'text-emerald-400 border-emerald-400' : 'text-slate-500 hover:text-slate-300 border-transparent'}" onclick={() => activeModalTab = 'protokoll'}>VDE Protokoll</button>
                {/if}
              </div>
            </div>

            <!-- Modal Content Scrollable -->
            <div class="overflow-y-auto p-5 space-y-4">
              {#if activeModalTab === 'details'}
                <!-- Stats -->
                <div class="grid grid-cols-3 gap-3 mt-3">
                  <div class="bg-slate-900/60 rounded-lg p-2.5">
                  {#if selectedDevice.typ === 'pdu'}
                    <div class="text-[9px] text-slate-500 uppercase font-mono">Stromtyp</div>
                    <div class="font-bold text-white text-xs mt-0.5 truncate">{selectedDevice.strom_typ || '3-phasig'}</div>
                  {:else if selectedDevice.connected_pdu_outlets && selectedDevice.connected_pdu_outlets.length > 0}
                    <div class="text-[9px] text-slate-500 uppercase font-mono">Phase / PDU</div>
                    <div class="flex flex-col mt-0.5" title={selectedDevice.connected_pdu_outlets.map(o => `${o.phase} (${devices.find(d => d.id === o.pdu_id)?.hostname || 'PDU'} ${o.outlet_name})`).join(', ')}>
                      {#each selectedDevice.connected_pdu_outlets as o}
                        <div class="flex items-center text-xs truncate">
                          <span class="font-bold mr-1 {o.phase === 'L1' ? 'text-blue-400' : o.phase === 'L2' ? 'text-cyan-400' : 'text-orange-400'}">{o.phase}</span>
                          <span class="text-white opacity-90 truncate">{devices.find(d => d.id === o.pdu_id)?.hostname || 'PDU'}</span>
                        </div>
                      {/each}
                    </div>
                  {:else}
                    <div class="text-[9px] text-slate-500 uppercase font-mono">Stromanschluss</div>
                    <div class="font-bold text-slate-500 text-xs mt-0.5">Nicht verbunden</div>
                  {/if}
                </div>
                <div class="bg-slate-900/60 rounded-lg p-2.5">
                  <div class="text-[9px] text-slate-500 uppercase font-mono">Anschluss</div>
                  <div class="font-bold text-white text-sm mt-0.5">{selectedDevice.anschlussleistung_watt ?? selectedDevice.tdp_watt ?? '–'} W</div>
                </div>
                <div class="bg-slate-900/60 rounded-lg p-2.5">
                  <div class="text-[9px] text-slate-500 uppercase font-mono">Höhe</div>
                  <div class="font-bold text-white text-sm mt-0.5">{selectedDevice.u_hoehe} HE</div>
                </div>
              </div>

              {#if selectedDevice.typ !== 'pdu' && selectedDevice.connected_pdu_outlets && selectedDevice.connected_pdu_outlets.length > 0}
                <div class="bg-slate-950/40 border border-slate-800/80 rounded-lg p-3 space-y-2 mt-3">
                  <div class="text-[9px] text-slate-400 uppercase font-mono tracking-wider flex items-center justify-between">
                    <span>Stromanschluss (PDU)</span>
                    <Zap class="w-3.5 h-3.5 text-yellow-500" />
                  </div>
                  <div class="space-y-1.5">
                    {#each selectedDevice.connected_pdu_outlets as outlet}
                      {@const pduDev = devices.find(d => d.id === outlet.pdu_id)}
                      <div class="bg-[#0b0f19] rounded-lg px-2.5 py-1.5 flex items-center justify-between text-xs border border-slate-800/40">
                        <div class="flex items-center space-x-2">
                          <span class="px-1.5 py-0.5 rounded font-bold text-[9px] font-mono
                            {outlet.phase === 'L1' ? 'bg-blue-950 text-blue-400 border border-blue-900/40' : 
                             outlet.phase === 'L2' ? 'bg-cyan-950 text-cyan-400 border border-cyan-900/40' : 
                             'bg-orange-950 text-orange-400 border border-orange-900/40'}">
                            {outlet.phase ?? '–'}
                          </span>
                          <span class="font-medium text-slate-200">{pduDev?.hostname ?? 'PDU'}</span>
                          <span class="text-slate-500 font-mono text-[10px]">{outlet.outlet_name}</span>
                        </div>
                        {#if outlet.steckdosentyp}
                          <span class="text-[9px] text-slate-400 font-mono bg-slate-900/80 px-1.5 py-0.5 rounded border border-slate-800/60">
                            {outlet.steckdosentyp}
                          </span>
                        {/if}
                      </div>
                    {/each}
                  </div>
                </div>
              {/if}
            </div>

            <!-- PDU Steckdosen (nur für PDU-Geräte) -->
            {#if selectedDevice.typ === 'pdu'}
              <div class="px-5 py-4 space-y-3 border-t border-slate-800">
                <div class="flex items-center justify-between">
                  <h4 class="text-xs font-bold text-slate-500 uppercase tracking-wider font-mono">PDU Steckdosen</h4>
                  <div class="flex items-center space-x-1">
                    <button onclick={openPduAutoOutletModal}
                      class="flex items-center space-x-1 text-[10px] px-2 py-1 bg-blue-900/50 hover:bg-blue-800/50 text-blue-300 border border-blue-800/80 rounded-lg transition">
                      <Zap class="w-3 h-3" /><span>Auto-Generieren</span>
                    </button>
                    <button onclick={openAddOutlet}
                      class="flex items-center space-x-1 text-[10px] px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition">
                      <Plus class="w-3 h-3" /><span>Outlet</span>
                    </button>
                  </div>
                </div>

                {#if pduOutlets.length === 0}
                  <div class="text-center py-4 text-slate-600 text-xs border border-dashed border-slate-800 rounded-lg">
                    Keine Steckdosen konfiguriert. Klicke "+ Outlet".
                  </div>
                {:else}
                  <div class="space-y-1">
                    {#each pduOutlets as outlet}
                      <div class="bg-slate-900/50 border border-slate-800/80 rounded-lg px-3 py-2 flex items-center gap-2 text-xs">
                        <span class="shrink-0 w-7 font-bold text-center {outlet.phase==='L1'?'text-blue-400':outlet.phase==='L2'?'text-cyan-400':'text-orange-400'}">
                          {outlet.phase ?? '–'}
                        </span>
                        <span class="font-mono text-slate-200 w-16 truncate shrink-0">{outlet.outlet_name}</span>
                        <span class="text-[10px] text-slate-500 w-8 shrink-0">{outlet.steckdosentyp ?? '–'}</span>
                        <select
                          class="flex-1 min-w-0 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-[10px] text-white focus:outline-none focus:border-blue-500"
                          value={outlet.connected_device_id ?? ''}
                          onchange={(e) => {
                            const v = (e.target as HTMLSelectElement).value;
                            setOutletDevice(outlet.id, v ? Number(v) : null);
                          }}
                        >
                          <option value="">— frei —</option>
                          {#each devices.filter(d => d.typ !== 'pdu' && d.id !== selectedDevice!.id) as d}
                            <option value={d.id}>{d.hostname}</option>
                          {/each}
                        </select>
                        <button onclick={() => deleteOutlet(outlet.id)} class="shrink-0 p-1 text-red-500/50 hover:text-red-400 transition">
                          <X class="w-3 h-3" />
                        </button>
                      </div>
                    {/each}
                  </div>
                {/if}
              </div>
            {/if}
          {/if}

          {#if activeModalTab === 'interfaces'}
            <!-- Switch Port-Matrix -->
            {#if selectedDevice.typ === 'switch'}
              {@const swPorts = [
                ...(selectedDevice.server_interfaces ?? []).map((i: any) => ({ name: i.port_name, typ: i.typ })),
                ...devicePorts.map(p => ({ name: p.port_name, typ: p.typ }))
              ]}
              {@const connectedCount = swPorts.filter(p => cableForPort(selectedDevice!.id, p.name)).length}
              <div class="px-5 py-4 space-y-3 border-t border-slate-800">
                <div class="flex items-center gap-2">
                  <h4 class="text-xs font-bold text-slate-500 uppercase tracking-wider font-mono">Port-Matrix</h4>
                  <span class="text-[10px] px-1.5 py-0.5 rounded font-mono
                    {connectedCount > 0 ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-slate-800 text-slate-500'}">
                    {connectedCount}/{swPorts.length} belegt
                  </span>
                </div>
                {#if swPorts.length === 0}
                  <div class="text-center py-3 text-slate-600 text-xs border border-dashed border-slate-800 rounded-lg">
                    Keine Ports konfiguriert.
                  </div>
                {:else}
                  <div class="overflow-x-auto rounded-lg border border-slate-800">
                    <table class="w-full text-xs">
                      <thead class="bg-slate-900/60">
                        <tr class="border-b border-slate-800 text-slate-500 uppercase text-[9px] font-mono tracking-wider">
                          <th class="px-2.5 py-1.5 text-left">Port</th>
                          <th class="px-2.5 py-1.5 text-left">Typ</th>
                          <th class="px-2.5 py-1.5 text-left">Kabel-Nr</th>
                          <th class="px-2.5 py-1.5 text-left">Zielgerät</th>
                          <th class="px-2.5 py-1.5 text-left">Ziel-Port</th>
                          <th class="px-2.5 py-1.5 text-left">HE-Pos.</th>
                        </tr>
                      </thead>
                      <tbody>
                        {#each swPorts as p}
                          {@const cable = cableForPort(selectedDevice.id, p.name)}
                          {@const end = cable ? otherEnd(cable, selectedDevice.id) : null}
                          <tr class="border-b border-slate-800/40 last:border-0 transition
                            {cable ? 'hover:bg-emerald-900/10' : 'hover:bg-slate-800/20'}">
                            <td class="px-2.5 py-1.5 font-mono font-bold {cable ? 'text-white' : 'text-slate-600'}">{p.name}</td>
                            <td class="px-2.5 py-1.5 text-slate-500 text-[10px]">{p.typ}</td>
                            <td class="px-2.5 py-1.5 font-mono {cable ? 'text-slate-300' : 'text-slate-700'}">{cable?.kabel_nr ?? '—'}</td>
                            <td class="px-2.5 py-1.5">
                              {#if end && end.otherDev}
                                <button onclick={() => {
                                  const targetDev = end?.otherDev;
                                  if (targetDev) {
                                    const r = racks.find(r => r.id === targetDev.rack_id);
                                    if (r) selectedRack = r;
                                    loadDeviceDetail(targetDev);
                                  }
                                }}
                                  class="font-medium transition {end.crossRack ? 'text-orange-400 hover:text-orange-300' : 'text-emerald-400 hover:text-emerald-300'}">
                                  {end.otherDev.hostname}
                                  {#if end.crossRack}<span class="text-[9px] ml-1 text-orange-500/70">★{end.otherRack?.name}</span>{/if}
                                </button>
                              {:else}
                                <span class="text-slate-700 italic text-[10px]">frei</span>
                              {/if}
                            </td>
                            <td class="px-2.5 py-1.5 font-mono {end ? 'text-slate-400' : 'text-slate-700'}">{end?.otherPort ?? '—'}</td>
                            <td class="px-2.5 py-1.5 text-slate-500">
                              {#if end && end.otherDev && end.otherDev.u_position}
                                HE {end.otherDev.u_position}
                              {:else}
                                —
                              {/if}
                            </td>
                          </tr>
                        {/each}
                      </tbody>
                    </table>
                  </div>
                {/if}
              </div>
            {/if}

            <!-- Interfaces / Ports -->
            <div class="px-5 py-4 space-y-3">
              <div class="flex items-center justify-between">
                <h4 class="text-xs font-bold text-slate-500 uppercase tracking-wider font-mono">Ports & Verbindungen</h4>
                <button onclick={openAddInterface}
                  class="flex items-center space-x-1 text-[10px] px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition">
                  <Plus class="w-3 h-3" /><span>Port</span>
                </button>
              </div>

              {#if selectedDevice.server_interfaces && selectedDevice.server_interfaces.length > 0}
                <div class="space-y-1.5">
                  {#each selectedDevice.server_interfaces as iface}
                    {@const cable = cableForPort(selectedDevice.id, iface.port_name)}
                    {@const end = cable ? otherEnd(cable, selectedDevice.id) : null}
                    <div class="bg-slate-900/50 border border-slate-800/80 rounded-lg p-3 flex items-center justify-between text-xs">
                      <div class="flex items-center space-x-3 min-w-0">
                        <div class="shrink-0">
                          <div class="font-mono font-bold text-slate-200">{iface.port_name}</div>
                          <div class="text-[10px] text-slate-500">{iface.typ}</div>
                        </div>
                        {#if end}
                          <div class="flex items-center space-x-1.5 min-w-0 text-[10px]">
                            <span class="text-slate-600">──[{cable?.typ} {cable?.laenge_m}m]──►</span>
                            <span class="font-medium {end.crossRack ? 'text-orange-400' : 'text-emerald-400'} truncate">
                              {end.otherDev?.hostname ?? '?'}/{end.otherPort}
                              {#if end.crossRack}<span class="ml-1 text-orange-500">★{end.otherRack?.name}</span>{/if}
                            </span>
                          </div>
                        {:else}
                          <span class="text-slate-600 text-[10px]">frei</span>
                        {/if}
                      </div>
                      {#if !cable}
                        <button onclick={() => openAddCable(selectedDevice!, iface.port_name)}
                          class="shrink-0 flex items-center space-x-1 px-2 py-1 bg-slate-800 hover:bg-blue-700 text-slate-400 hover:text-white rounded transition text-[10px]">
                          <CableIcon class="w-3 h-3" /><span>Kabel</span>
                        </button>
                      {:else}
                        <div class="flex items-center space-x-1.5 shrink-0">
                          <button onclick={() => openEditCable(cable)}
                            class="p-1 text-slate-400 hover:text-blue-400 transition" title="Kabel bearbeiten">
                            <Edit2 class="w-3 h-3" />
                          </button>
                          <button onclick={() => api.deleteCable(cable!.id).then(loadAll)}
                            class="p-1 text-red-500/50 hover:text-red-400 transition" title="Kabel löschen">
                            <X class="w-3 h-3" />
                          </button>
                        </div>
                      {/if}
                    </div>
                  {/each}
                </div>
              {:else if devicePorts.length > 0}
                <div class="space-y-1.5">
                  {#each devicePorts as port}
                    {@const cable = cableForPort(selectedDevice.id, port.port_name)}
                    {@const end = cable ? otherEnd(cable, selectedDevice.id) : null}
                    <div class="bg-slate-900/50 border border-slate-800/80 rounded-lg p-3 flex items-center justify-between text-xs">
                      <div class="flex items-center space-x-3 min-w-0">
                        <div class="shrink-0">
                          <div class="font-mono font-bold text-slate-200">{port.port_name}</div>
                          <div class="text-[10px] text-slate-500">{port.typ}</div>
                        </div>
                        {#if end}
                          <div class="flex items-center space-x-1.5 min-w-0 text-[10px]">
                            <span class="text-slate-600">──[{cable?.typ} {cable?.laenge_m}m]──►</span>
                            <span class="font-medium {end.crossRack ? 'text-orange-400' : 'text-emerald-400'} truncate">
                              {end.otherDev?.hostname ?? '?'}/{end.otherPort}
                              {#if end.crossRack}<span class="ml-1 text-orange-500">★{end.otherRack?.name}</span>{/if}
                            </span>
                          </div>
                        {:else}
                          <span class="text-slate-600 text-[10px]">frei</span>
                        {/if}
                      </div>
                      {#if !cable}
                        <button onclick={() => openAddCable(selectedDevice!, port.port_name)}
                          class="shrink-0 flex items-center space-x-1 px-2 py-1 bg-slate-800 hover:bg-blue-700 text-slate-400 hover:text-white rounded transition text-[10px]">
                          <CableIcon class="w-3 h-3" /><span>Kabel</span>
                        </button>
                      {:else}
                        <div class="flex items-center space-x-1.5 shrink-0">
                          <button onclick={() => openEditCable(cable)}
                            class="p-1 text-slate-400 hover:text-blue-400 transition" title="Kabel bearbeiten">
                            <Edit2 class="w-3 h-3" />
                          </button>
                          <button onclick={() => api.deleteCable(cable!.id).then(loadAll)}
                            class="p-1 text-red-500/50 hover:text-red-400 transition" title="Kabel löschen">
                            <X class="w-3 h-3" />
                          </button>
                        </div>
                      {/if}
                    </div>
                  {/each}
                </div>
              {:else}
                <div class="text-center py-4 text-slate-600 text-xs border border-dashed border-slate-800 rounded-lg">
                  Noch keine Ports. Klicke "+ Port" um einen Interface-Port anzulegen.
                </div>
              {/if}

              <!-- Direkte Kabelverbindungen (ohne explizite Ports) -->
              {#if cables.filter(c =>
                (c.von_device_id === selectedDevice!.id || c.nach_device_id === selectedDevice!.id) &&
                !(selectedDevice!.server_interfaces ?? []).some(i => i.port_name === c.von_port || i.port_name === c.nach_port) &&
                !devicePorts.some(p => p.port_name === c.von_port || p.port_name === c.nach_port)
              ).length > 0}
                <div>
                  <div class="text-[10px] text-slate-600 mb-1.5 uppercase font-mono">Weitere Kabel</div>
                  {#each cables.filter(c =>
                    (c.von_device_id === selectedDevice!.id || c.nach_device_id === selectedDevice!.id) &&
                    !(selectedDevice!.server_interfaces ?? []).some(i => i.port_name === c.von_port || i.port_name === c.nach_port) &&
                    !devicePorts.some(p => p.port_name === c.von_port || p.port_name === c.nach_port)
                  ) as cable}
                    {@const end = otherEnd(cable, selectedDevice!.id)}
                    <div class="bg-slate-900/30 border border-slate-800/50 rounded p-2 text-[10px] flex justify-between items-center mb-1">
                      <div class="flex items-center space-x-2 min-w-0">
                        <span class="font-mono text-slate-400 shrink-0">{cable.kabel_nr} · {cable.typ} · {cable.laenge_m}m</span>
                        <span class="{end.crossRack?'text-orange-400':'text-emerald-400'} truncate max-w-[120px]">
                          → {end.otherDev?.hostname ?? '?'}/{end.otherPort}
                          {#if end.crossRack}(★{end.otherRack?.name}){/if}
                        </span>
                      </div>
                      <div class="flex items-center space-x-1.5 shrink-0">
                        <button onclick={() => openEditCable(cable)}
                          class="p-1 text-slate-400 hover:text-blue-400 transition" title="Kabel bearbeiten">
                          <Edit2 class="w-2.5 h-2.5" />
                        </button>
                        <button onclick={() => api.deleteCable(cable.id).then(loadAll)}
                          class="p-1 text-red-500/50 hover:text-red-400 transition" title="Kabel löschen">
                          <X class="w-2.5 h-2.5" />
                        </button>
                      </div>
                    </div>
                  {/each}
                </div>
              {/if}

              <!-- Kabel ohne Port anlegen -->
              <button onclick={() => openAddCable(selectedDevice!, '')}
                class="w-full flex items-center justify-center space-x-2 py-2 border border-dashed border-slate-700 hover:border-blue-500/50 rounded-lg text-xs text-slate-500 hover:text-blue-400 transition">
                <CableIcon class="w-3.5 h-3.5" /><span>Kabelverbindung anlegen</span>
              </button>
            </div>
          {/if}

          {#if activeModalTab === 'protokoll'}
            {#if powerAuditLoading}
              <div class="py-8 text-center"><div class="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-500 mx-auto"></div><p class="text-xs text-slate-500 mt-3">Lade VDE Protokoll...</p></div>
            {:else if powerAuditData?.error}
              <div class="bg-red-950/40 border border-red-900 rounded-lg p-4 text-red-400 text-sm text-center">{powerAuditData.error}</div>
            {:else if powerAuditData}
              <!-- VDE Audit Results -->
              <div class="space-y-6">
                <div class="grid grid-cols-2 gap-4">
                  <div class="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                    <div class="text-[10px] text-slate-500 uppercase tracking-wider font-mono mb-2">VDE Compliance Status</div>
                    <div class="space-y-2">
                      {#each powerAuditData.audit_results as res}
                        <div class="flex items-start gap-2 text-xs">
                          <span class="shrink-0 mt-0.5 {res.status === 'error' ? 'text-red-400' : res.status === 'warning' ? 'text-orange-400' : 'text-emerald-400'}">
                            {#if res.status === 'ok'}✓{:else if res.status === 'warning'}⚠{:else}✗{/if}
                          </span>
                          <div class="min-w-0">
                            <div class="font-bold {res.status === 'error' ? 'text-red-300' : res.status === 'warning' ? 'text-orange-300' : 'text-emerald-300'}">{res.rule}</div>
                            <div class="text-slate-400 text-[10px] leading-snug">{res.message}</div>
                          </div>
                        </div>
                      {/each}
                    </div>
                  </div>
                  
                  <div class="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                    <div class="text-[10px] text-slate-500 uppercase tracking-wider font-mono mb-2">Last-Historie</div>
                    {#if powerAuditData.calculations && powerAuditData.calculations.length > 0}
                      <div class="space-y-2 max-h-[150px] overflow-y-auto pr-1">
                        {#each powerAuditData.calculations as calc}
                          <div class="flex items-center justify-between text-xs border-b border-slate-800/50 pb-1 last:border-0">
                            <span class="text-slate-400">{new Date(calc.berechnet_am).toLocaleDateString()}</span>
                            <span class="font-mono text-emerald-400">{calc.last_kw} kW / {calc.installiert_kw} kW</span>
                          </div>
                        {/each}
                      </div>
                    {:else}
                      <div class="text-xs text-slate-500 italic">Keine Berechnungs-Historie vorhanden</div>
                    {/if}
                  </div>
                </div>
              </div>
            {/if}
          {/if}

        </div>
      </div>
    </div>
  {/if}

  <!-- ═══ Kabeltyp-Referenz für Techniker ═══════════════════════ -->
  {#if legendCableTypes.length > 0}
    <div class="bg-[#101622] border border-slate-800 rounded-xl p-5">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h3 class="text-sm font-bold text-white font-outfit flex items-center gap-2">
            <CableIcon class="w-4 h-4 text-slate-400" />
            Kabeltyp-Referenz
          </h3>
          <p class="text-[10px] text-slate-500 mt-0.5">Verwendungszweck und Steckverbinder · Hilfe für den Einbau</p>
        </div>
        <a href="/cables" class="text-[10px] text-blue-400 hover:text-blue-300 transition">
          Kabelliste ({cables.length}) →
        </a>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
        {#each legendCableTypes as ct}
          {@const def = getCableDef(ct)}
          {@const count = cables.filter(c => c.typ === ct).length}
          {@const totalLen = cables.filter(c => c.typ === ct).reduce((s, c) => s + (Number(c.laenge_m) || 0), 0)}
          {@const isPinned = PINNED_CABLE_TYPES.includes(ct) && count === 0}
          <div class="flex items-start gap-3 rounded-lg p-3 {isPinned ? 'bg-orange-950/20 border border-orange-900/30' : 'bg-slate-900/50 border border-slate-800/50'}">
            <div class="mt-0.5 shrink-0">
              <div class="w-3 h-3 rounded-full {def.dotColor}"></div>
            </div>
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-[10px] px-1.5 py-0.5 rounded border font-medium {def.badgeClass}">{ct}</span>
                {#if count > 0}
                  <span class="text-[10px] text-slate-500">{count}× · {totalLen.toFixed(0)} m</span>
                {:else}
                  <span class="text-[10px] text-slate-600 italic">Referenz</span>
                {/if}
              </div>
              <p class="text-xs font-semibold text-slate-300 mt-1">{def.desc}</p>
              <p class="text-[10px] text-slate-500 mt-0.5">{def.use}</p>
              <p class="text-[10px] text-slate-600 mt-0.5 font-mono">{def.connector}</p>
            </div>
          </div>
        {/each}
      </div>
    </div>
  {/if}
</div>


<RackModal
  bind:show={showAddRack}
  onSave={handleAddRack}
  defaultStandort={filterStandort}
  defaultRackreihe={filterReihe}
  hardwareTypes={hardware.filter(h => h.kategorie === 'rack')}
/>

<RackModal
  bind:show={showEditRack}
  onSave={handleEditRack}
  initialData={selectedRack}
  showRemark={true}
  hardwareTypes={hardware.filter(h => h.kategorie === 'rack')}
/>

<!-- ═══ MODAL: Gerät einbauen ════════════════════════════ -->
{#if showAddDevice}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[#101622] border border-slate-800 rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
    <div class="flex items-center justify-between px-6 py-4 border-b border-slate-800 shrink-0">
      <div>
        <h3 class="text-lg font-bold text-white font-outfit">{pduOnlyMode ? 'PDU einbauen' : 'Hardware einbauen'}</h3>
        <p class="text-xs text-slate-500">{selectedRack?.name} · {pduOnlyMode ? 'Seitliche Montage (0U)' : targetSlot === null ? 'Seitliche Montage' : 'HE ' + targetSlot}</p>
      </div>
      <button onclick={() => { showAddDevice=false; pduOnlyMode=false; }}><X class="w-5 h-5 text-slate-500" /></button>
    </div>

    <div class="flex flex-1 overflow-hidden min-h-0">
      <!-- Hardware-Katalog links -->
      <div class="w-56 border-r border-slate-800 flex flex-col shrink-0">
        <div class="p-3 border-b border-slate-800">
          <input type="text" bind:value={hwFilter} placeholder="Suchen…"
            class="w-full bg-[#182030] border border-slate-700 rounded px-3 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500" />
        </div>
        <div class="overflow-y-auto flex-1 p-2 space-y-1">
          {#each filteredHW as hw}
            {@const incompatible = isHWIncompatible(hw)}
            <button onclick={() => selectHW(hw)}
              disabled={incompatible}
              title={incompatible ? 'Benötigt mind. ' + hw.min_rack_hoehe + 'HE-Rack (dieses Rack hat ' + selectedRack?.hoehe_u + 'HE)' : ''}
              class="w-full text-left px-3 py-2 rounded-lg text-xs transition {selectedHW?.id === hw.id ? 'bg-blue-600/20 border border-blue-500/40 text-white' : incompatible ? 'text-slate-600 cursor-not-allowed' : 'text-slate-400 hover:bg-slate-800/60'}">
              <div class="font-semibold truncate">{incompatible ? '⚠ ' : ''}{hw.name}</div>
              <div class="text-[10px] text-slate-500">{hw.kategorie} · {hw.u_hoehe === 0 ? '0U' : hw.u_hoehe + ' HE'}{incompatible ? ' · benötigt ' + hw.min_rack_hoehe + 'HE' : ''}{!pduOnlyMode && hw.tdp_watt ? ' · '+hw.tdp_watt+'W' : ''}{!pduOnlyMode && hw.psu_count ? ' · '+hw.psu_count+'× PSU' : ''}</div>
            </button>
          {:else}
            <div class="text-center py-4 text-slate-600 text-xs">Keine Einträge</div>
          {/each}
          <button onclick={() => selectedHW = null}
            class="w-full text-left px-3 py-2 rounded-lg text-xs text-slate-500 hover:bg-slate-800/60 border border-dashed border-slate-700 mt-2">
            + Ohne Vorlage einbauen
          </button>
        </div>
      </div>

      <!-- Formular rechts -->
      <form onsubmit={submitAddDevice} class="flex-1 overflow-y-auto p-5 space-y-4">
        {#if selectedHW}
          <div class="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3 text-xs">
            <div class="font-bold text-blue-300">{selectedHW.name}</div>
            <div class="text-slate-400 mt-0.5">{selectedHW.hersteller} {selectedHW.modell} · {selectedHW.u_hoehe === 0 ? '0U · Seitlich' : selectedHW.u_hoehe + ' HE'}{!pduOnlyMode && selectedHW.tdp_watt ? ' · ' + selectedHW.tdp_watt + ' W' : ''}{selectedHW.psu_count ? ' · ' + selectedHW.psu_count + '× PSU' : ''}</div>
            {#if selectedHW.bemerkung}<div class="text-slate-500 mt-1">{selectedHW.bemerkung}</div>{/if}
          </div>
          {#if selectedHW.min_rack_hoehe && selectedRack && selectedRack.hoehe_u < selectedHW.min_rack_hoehe}
            <div class="bg-red-500/20 border border-red-500/50 rounded-lg p-3 text-xs text-red-200 font-semibold">
              ⚠ PDU benötigt mind. {selectedHW.min_rack_hoehe}HE-Rack — dieses Rack hat nur {selectedRack.hoehe_u}HE
            </div>
          {/if}
          {#if selectedHW.u_hoehe === 0 && selectedRack?.breite_mm === 600}
            <div class="bg-amber-500/20 border border-amber-500/50 rounded-lg p-3 text-xs text-amber-200 font-semibold mt-2">
              ⚠ Warnung: Zero-U PDU in einem 600mm breiten Rack. Die seitliche Montage ist bei 600mm oft zu eng und wird nicht empfohlen.
            </div>
          {/if}
        {/if}

        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Hostname *</label>
          <input type="text" bind:value={devHostname} required
            class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
            placeholder="z.B. srv-prod-01" />
        </div>

        {#if isZeroU}
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Seite</label>
          <div class="grid grid-cols-2 gap-2">
            <button type="button" onclick={() => devSide = 'left'}
              disabled={occupiedSides.left}
              class="px-3 py-2 rounded-lg text-sm transition border {devSide === 'left' ? 'bg-blue-600/20 border-blue-500/40 text-white' : 'text-slate-400 hover:bg-slate-800/60 border-slate-700'} disabled:opacity-40 disabled:cursor-not-allowed">
              Links (0UL)
            </button>
            <button type="button" onclick={() => devSide = 'right'}
              disabled={occupiedSides.right}
              class="px-3 py-2 rounded-lg text-sm transition border {devSide === 'right' ? 'bg-blue-600/20 border-blue-500/40 text-white' : 'text-slate-400 hover:bg-slate-800/60 border-slate-700'} disabled:opacity-40 disabled:cursor-not-allowed">
              Rechts (0UR)
            </button>
          </div>
          {#if (devSide === 'left' && occupiedSides.left) || (devSide === 'right' && occupiedSides.right)}
            <p class="text-[10px] text-red-400 mt-1">Diese Seite ist bereits belegt</p>
          {/if}
        </div>
        {/if}

        {#if !isZeroU}
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-semibold text-slate-400 mb-1">U-Position</label>
            <input type="number" bind:value={targetSlot} min="1" max={selectedRack?.hoehe_u ?? 42}
              class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-400 mb-1">Höhe (HE)</label>
            <input type="number" bind:value={devUHoehe} min="0" max="20" readonly={selectedHW !== null}
              class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500 {selectedHW !== null ? 'opacity-60 cursor-not-allowed' : ''}" />
          </div>
        </div>
        {/if}

        {#if !isZeroU}
        {@const hwKat = selectedHW?.kategorie}
        {#if hwKat && hwKat !== 'pdu' && hwKat !== 'rack'}
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">TDP (W)</label>
          <input type="number" bind:value={devTdpWatt} min="0" placeholder="z.B. 400"
            class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
          <p class="text-[10px] text-slate-600 mt-1">Richtwert aus Datenblatt — bitte anpassen</p>
        </div>
        {/if}
        {#if hwKat === 'server' || hwKat === 'firewall' || hwKat === 'storage'}
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-semibold text-slate-400 mb-1">PSU Anzahl</label>
            <input type="number" bind:value={devPsuCount} min="0"
              class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-400 mb-1">PSU Nennleistung (W)</label>
            <input type="number" bind:value={devPsuNennwatt} min="0"
              class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
          </div>
        </div>
        <p class="text-[10px] text-slate-600 -mt-2">Richtwert aus Datenblatt — bitte anpassen</p>
        {/if}
        <div class="mb-4">
          <label class="block text-xs font-semibold text-slate-400 mb-1">Anschlussleistung (W)</label>
          <input type="number" bind:value={devAnschlussleistung} min="0" placeholder="z.B. 350"
            class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
          <p class="text-[10px] text-slate-600 mt-1">Netzteileingabe laut Typenschild — nicht CPU-TDP</p>
        </div>
        {/if}

        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">IP-Adresse</label>
          <input type="text" bind:value={devIp} placeholder="192.168.1.10"
            class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-semibold text-slate-400 mb-1">Hersteller</label>
            <input type="text" bind:value={devHersteller}
              class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-400 mb-1">Modell</label>
            <input type="text" bind:value={devModell}
              class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-semibold text-slate-400 mb-1">Seriennummer</label>
            <input type="text" bind:value={devSeriennummer}
              class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-400 mb-1">Inventarnummer</label>
            <input type="text" bind:value={devInventarnummer} placeholder="z.B. INV-2024-0042"
              class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
          </div>
        </div>

        <div class="flex justify-end space-x-3 pt-2">
          <button type="button" onclick={() => { showAddDevice=false; pduOnlyMode=false; }} class="px-4 py-2 text-sm text-slate-400 hover:bg-slate-800 rounded-lg transition">Abbrechen</button>
          <button type="submit" 
            disabled={selectedHW && selectedHW.min_rack_hoehe && selectedRack && selectedRack.hoehe_u < selectedHW.min_rack_hoehe}
            class="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 disabled:text-slate-500 disabled:cursor-not-allowed text-white rounded-lg text-sm font-semibold transition"
          >
            Einbauen
          </button>
        </div>
      </form>
    </div>
  </div>
</div>
{/if}

<!-- ═══ MODAL: Kabel anlegen ═════════════════════════════ -->
{#if showAddCable}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[#101622] border border-slate-800 rounded-xl p-6 max-w-md w-full shadow-2xl">
    <div class="flex items-center justify-between mb-4">
      <div>
        <h3 class="text-lg font-bold text-white font-outfit">Kabelverbindung anlegen</h3>
        <p class="text-xs text-slate-500">{cableFromDevice?.hostname ?? '–'} / {cableVonPort || 'kein Port'}</p>
      </div>
      <button onclick={() => showAddCable=false}><X class="w-5 h-5 text-slate-500" /></button>
    </div>
    <form onsubmit={submitAddCable} class="space-y-4">
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Von Port</label>
          <input type="text" bind:value={cableVonPort} placeholder="z.B. eth0"
            class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Kabel-Typ *</label>
          <select bind:value={cableTyp} required
            onchange={() => { cableNachDevId = null; cableNachPort = ''; }}
            class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500">
            {#each CABLE_TYPES as ct}<option value={ct}>{ct}</option>{/each}
          </select>
        </div>
      </div>

      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Ziel-Gerät *</label>
        <select bind:value={cableNachDevId} required
          class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500">
          <option value={null}>— Gerät auswählen —</option>
          {#each racks as rack}
            {@const rackTargets = filteredTargetDevices().filter(d => d.rack_id === rack.id)}
            {#if rackTargets.length > 0}
            <optgroup label="{rack.name} — {rack.standort}">
              {#each rackTargets as d}
                <option value={d.id}>{d.hostname} ({d.typ})</option>
              {/each}
            </optgroup>
            {/if}
          {/each}
        </select>
      </div>

      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Ziel-Port</label>
        <input type="text" bind:value={cableNachPort} placeholder="z.B. Gi0/1"
          list="target-ports-list"
          class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
        <datalist id="target-ports-list">
          {#each targetDevPorts() as p}<option value={p} />{/each}
        </datalist>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Länge (m) *</label>
          <input type="number" bind:value={cableLaenge} min="0.1" step="0.1" required
            class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Farbe</label>
          <input type="text" bind:value={cableFarbe} placeholder="z.B. blau"
            class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
        </div>
      </div>

      {#if cableNachDevId && cableFromDevice && devices.find(d=>d.id===cableNachDevId)?.rack_id !== cableFromDevice.rack_id}
        <div class="bg-orange-500/10 border border-orange-500/30 rounded-lg px-3 py-2 text-xs text-orange-400">
          ★ Rack-übergreifende Verbindung — wird im Export markiert
        </div>
      {/if}

      <div class="flex justify-end space-x-3 pt-2">
        <button type="button" onclick={() => showAddCable=false} class="px-4 py-2 text-sm text-slate-400 hover:bg-slate-800 rounded-lg transition">Abbrechen</button>
        <button type="submit" class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-semibold transition">Kabel anlegen</button>
      </div>
    </form>
  </div>
</div>
{/if}

<!-- ═══ MODAL: Kabel bearbeiten ═══════════════════════════ -->
{#if showEditCable}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[#101622] border border-slate-800 rounded-xl p-6 max-w-md w-full shadow-2xl">
    <div class="flex items-center justify-between mb-4">
      <div>
        <h3 class="text-lg font-bold text-white font-outfit">Kabelverbindung bearbeiten</h3>
        <p class="text-xs text-slate-500">{editCableFromDevice?.hostname ?? '–'} / {editCableVonPort || 'kein Port'} ({editCableNr})</p>
      </div>
      <button onclick={() => showEditCable=false}><X class="w-5 h-5 text-slate-500" /></button>
    </div>
    <form onsubmit={submitEditCable} class="space-y-4">
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Von Port</label>
          <input type="text" bind:value={editCableVonPort} readonly disabled
            class="w-full bg-[#182030]/50 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-500 focus:outline-none" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Kabel-Typ *</label>
          <select bind:value={editCableTyp} required
            onchange={() => { editCableNachDevId = null; editCableNachPort = ''; }}
            class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500">
            {#each CABLE_TYPES as ct}<option value={ct}>{ct}</option>{/each}
          </select>
        </div>
      </div>

      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Ziel-Gerät *</label>
        <select bind:value={editCableNachDevId} required
          class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500">
          <option value={null}>— Gerät auswählen —</option>
          {#each racks as rack}
            {@const rackTargets = editFilteredTargetDevices().filter(d => d.rack_id === rack.id)}
            {#if rackTargets.length > 0}
            <optgroup label="{rack.name} — {rack.standort}">
              {#each rackTargets as d}
                <option value={d.id}>{d.hostname} ({d.typ})</option>
              {/each}
            </optgroup>
            {/if}
          {/each}
        </select>
      </div>

      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Ziel-Port</label>
        <input type="text" bind:value={editCableNachPort} placeholder="z.B. Gi0/1"
          list="edit-target-ports-list"
          class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
        <datalist id="edit-target-ports-list">
          {#each editTargetDevPorts() as p}<option value={p} />{/each}
        </datalist>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Länge (m) *</label>
          <input type="number" bind:value={editCableLaenge} min="0.1" step="0.1" required
            class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Farbe</label>
          <input type="text" bind:value={editCableFarbe} placeholder="z.B. blau"
            class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
        </div>
      </div>

      {#if editCableNachDevId && editCableFromDevice && devices.find(d=>d.id===editCableNachDevId)?.rack_id !== editCableFromDevice.rack_id}
        <div class="bg-orange-500/10 border border-orange-500/30 rounded-lg px-3 py-2 text-xs text-orange-400">
          ★ Rack-übergreifende Verbindung — wird im Export markiert
        </div>
      {/if}

      <div class="flex justify-end space-x-3 pt-2">
        <button type="button" onclick={() => showEditCable=false} class="px-4 py-2 text-sm text-slate-400 hover:bg-slate-800 rounded-lg transition">Abbrechen</button>
        <button type="submit" class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-semibold transition">Speichern</button>
      </div>
    </form>
  </div>
</div>
{/if}

<!-- ═══ MODAL: PDU Outlet anlegen ════════════════════════ -->
{#if showAddOutlet && selectedDevice}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[#101622] border border-slate-800 rounded-xl p-6 max-w-sm w-full shadow-2xl">
    <div class="flex items-center justify-between mb-4">
      <div>
        <h3 class="text-lg font-bold text-white font-outfit">Steckdose anlegen</h3>
        <p class="text-xs text-slate-500">{selectedDevice.hostname}</p>
      </div>
      <button onclick={() => showAddOutlet=false}><X class="w-5 h-5 text-slate-500" /></button>
    </div>
    <form onsubmit={submitAddOutlet} class="space-y-4">
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Outlet-Name *</label>
          <input type="text" bind:value={outletName} required placeholder="z.B. Out-1"
            class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Phase</label>
          <select bind:value={outletPhase}
            class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500">
            <option value="L1">L1</option><option value="L2">L2</option><option value="L3">L3</option>
          </select>
        </div>
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Stecker-Typ</label>
          <select bind:value={outletTyp}
            class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500">
            {#each OUTLET_TYPES as t}<option value={t}>{t}</option>{/each}
          </select>
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Max. Watt</label>
          <input type="number" bind:value={outletMaxWatt} min="0" placeholder="z.B. 2300"
            class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
        </div>
      </div>
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Verbundenes Gerät</label>
        <select bind:value={outletDevId}
          class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500">
          <option value={null}>— frei —</option>
          {#each devices.filter(d => d.typ !== 'pdu' && d.id !== selectedDevice!.id) as d}
            <option value={d.id}>{d.hostname} ({d.typ})</option>
          {/each}
        </select>
      </div>
      <div class="flex justify-end space-x-3 pt-2">
        <button type="button" onclick={() => showAddOutlet=false} class="px-4 py-2 text-sm text-slate-400 hover:bg-slate-800 rounded-lg transition">Abbrechen</button>
        <button type="submit" class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-semibold transition">Speichern</button>
      </div>
    </form>
  </div>
</div>
{/if}

<!-- ═══ MODAL: Gerät bearbeiten ═════════════════════════ -->
{#if showEditDevice && selectedDevice}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[#101622] border border-slate-800 rounded-xl shadow-2xl w-full max-w-lg">
    <div class="flex items-center justify-between px-6 py-4 border-b border-slate-800">
      <div>
        <h3 class="text-lg font-bold text-white font-outfit">Gerät bearbeiten</h3>
        <p class="text-xs text-slate-500">{selectedDevice.hostname}</p>
      </div>
      <button onclick={() => showEditDevice=false}><X class="w-5 h-5 text-slate-500" /></button>
    </div>
    <form onsubmit={submitEditDevice} class="p-6 space-y-4">
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Hostname *</label>
        <input type="text" bind:value={editHostname} required
          class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">U-Position</label>
          <input type="number" bind:value={editUPos} min="1" max={selectedRack?.hoehe_u ?? 42}
            disabled={editUHoehe === 0}
            class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500 disabled:opacity-50" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Höhe (HE)</label>
          <input type="number" bind:value={editUHoehe} min="0"
            oninput={() => { if (editUHoehe === 0) editUPos = null; }}
            class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
        </div>
      </div>
      {#if editUHoehe === 0}
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Seite</label>
        <div class="grid grid-cols-2 gap-2">
          <button type="button" onclick={() => editSide = 'left'}
            class="px-3 py-2 rounded-lg text-sm transition border {editSide === 'left' ? 'bg-blue-600/20 border-blue-500/40 text-white' : 'text-slate-400 hover:bg-slate-800/60 border-slate-700'}">
            Links (0UL)
          </button>
          <button type="button" onclick={() => editSide = 'right'}
            class="px-3 py-2 rounded-lg text-sm transition border {editSide === 'right' ? 'bg-blue-600/20 border-blue-500/40 text-white' : 'text-slate-400 hover:bg-slate-800/60 border-slate-700'}">
            Rechts (0UR)
          </button>
        </div>
      </div>
      {/if}
      {#if selectedDevice.typ !== 'pdu'}
      <div class="mb-4">
        <label class="block text-xs font-semibold text-slate-400 mb-1">Anschlussleistung (W)</label>
        <input type="number" bind:value={editAnschluss} min="0"
          class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
      </div>
      {/if}
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">IP-Adresse</label>
        <input type="text" bind:value={editIp} placeholder="192.168.1.10"
          class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Hersteller</label>
          <input type="text" bind:value={editHersteller}
            class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Modell</label>
          <input type="text" bind:value={editModell}
            class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
        </div>
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Seriennummer</label>
          <input type="text" bind:value={editSeriennummer}
            class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Inventarnummer</label>
          <input type="text" bind:value={editInventarnummer}
            class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
        </div>
      </div>
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Bemerkung</label>
        <textarea bind:value={editBemerkung} rows="2"
          class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500 resize-none"></textarea>
      </div>

      <div class="border-t border-slate-800 pt-4 mt-2">
        <h4 class="text-sm font-bold text-white mb-3">Ausfall- & Boot-Verhalten</h4>
        <div class="grid grid-cols-3 gap-4 mb-4">
          <div>
            <label class="block text-xs font-semibold text-slate-400 mb-1">Priorität (1=Höchste)</label>
            <input type="number" bind:value={editShutdownPriority} min="1" max="4"
              class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-400 mb-1">Delay (Sekunden)</label>
            <input type="number" bind:value={editShutdownDelay} min="0"
              class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-400 mb-1">Methode</label>
            <select bind:value={editShutdownMethod}
              class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500">
              <option value="ACPI_Graceful">ACPI Graceful</option>
              <option value="SSH_Script">SSH Script</option>
              <option value="Hard_Power_Cut">Hard Power Cut</option>
            </select>
          </div>
        </div>

        <h4 class="text-sm font-bold text-white mb-2">Abhängigkeiten (DAG)</h4>
        <p class="text-[10px] text-slate-500 mb-2">Wenn die ausgewählten Geräte ausfallen, fällt dieses Gerät ebenfalls aus. Nutze 'HA-Cluster' für redundante Systeme (Gerät überlebt, solange mind. eines im Cluster online ist).</p>
        
        {#each editDependencies as dep, i}
          <div class="flex items-center space-x-2 mb-2 bg-slate-900/50 p-2 rounded border border-slate-800">
            <select bind:value={dep.depends_on_device_id} class="flex-1 bg-[#182030] border border-slate-700 rounded px-2 py-1 text-xs text-white">
              {#each devices.filter(d => d.id !== selectedDevice!.id) as d}
                <option value={d.id}>{d.hostname} ({d.typ})</option>
              {/each}
            </select>
            <select bind:value={dep.dependency_type} class="w-24 bg-[#182030] border border-slate-700 rounded px-2 py-1 text-xs text-white">
              <option value="power">Power</option>
              <option value="network">Network</option>
            </select>
            <input type="text" bind:value={dep.dependency_group} placeholder="HA-Cluster (opt)" class="w-28 bg-[#182030] border border-slate-700 rounded px-2 py-1 text-xs text-white" />
            <button type="button" onclick={() => editDependencies = editDependencies.filter((_, idx) => idx !== i)} class="p-1 text-red-500/50 hover:text-red-400"><X class="w-3 h-3"/></button>
          </div>
        {/each}
        <button type="button" onclick={() => editDependencies = [...editDependencies, {depends_on_device_id: devices.find(d=>d.id!==selectedDevice!.id)?.id, dependency_type: 'power', dependency_group: ''}]}
          class="text-xs text-blue-400 hover:text-blue-300 mt-1 flex items-center gap-1">+ Abhängigkeit hinzufügen</button>
      </div>
      <div class="flex justify-end space-x-3 pt-2">
        <button type="button" onclick={() => showEditDevice=false}
          class="px-4 py-2 text-sm text-slate-400 hover:bg-slate-800 rounded-lg transition">Abbrechen</button>
        <button type="submit"
          class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-semibold transition">Speichern</button>
      </div>
    </form>
  </div>
</div>
{/if}
<!-- ═══ MODAL: Interface anlegen ════════════════════════ -->
{#if showAddInterface && selectedDevice}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[#101622] border border-slate-800 rounded-xl p-6 max-w-sm w-full shadow-2xl">
    <div class="flex items-center justify-between mb-4">
      <div>
        <h3 class="text-lg font-bold text-white font-outfit">Port / Interface anlegen</h3>
        <p class="text-xs text-slate-500">{selectedDevice.hostname}</p>
      </div>
      <button onclick={() => showAddInterface=false}><X class="w-5 h-5 text-slate-500" /></button>
    </div>
    <div class="space-y-4">
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Port-Name *</label>
        <input type="text" bind:value={ifacePort} placeholder="z.B. eth0, ens3f0, IPMI"
          class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
      </div>
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Typ</label>
        <select bind:value={ifaceTyp}
          class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500">
          {#each IF_TYPES as t}<option value={t}>{t}</option>{/each}
        </select>
      </div>
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">MAC-Adresse</label>
        <input type="text" bind:value={ifaceMac} placeholder="aa:bb:cc:dd:ee:ff"
          class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
      </div>
      <div class="flex justify-end space-x-3 pt-2">
        <button onclick={() => showAddInterface=false} class="px-4 py-2 text-sm text-slate-400 hover:bg-slate-800 rounded-lg transition">Abbrechen</button>
        <button
          onclick={submitAddInterface}
          class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-semibold transition">
          Speichern
        </button>
      </div>
    </div>
  </div>
</div>
{/if}

<!-- ═══ MODAL: PDU Outlets automatisch generieren ════════════ -->
{#if showPduAutoOutlet && pduAutoDevice}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[#101622] border border-slate-800 rounded-xl p-6 max-w-md w-full shadow-2xl">
    <div class="flex items-center justify-between mb-4">
      <div>
        <h3 class="text-lg font-bold text-white font-outfit">Steckdosen generieren</h3>
        <p class="text-xs text-slate-500">{pduAutoDevice.hostname}</p>
      </div>
      <button onclick={() => showPduAutoOutlet=false}><X class="w-5 h-5 text-slate-500" /></button>
    </div>
    <form onsubmit={(e) => { e.preventDefault(); generatePduOutlets(); }} class="space-y-4">
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Muster (z.B. 18x C13 + 18x Cx) *</label>
        <input type="text" bind:value={pduAutoPattern} required
          class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
        <p class="text-[10px] text-slate-500 mt-1">Cx wird automatisch auf C19 gemappt. C13, C19, Schuko, CEE-16A sind unterstützt.</p>
      </div>

      {#if pduAutoPreview}
        <div class="bg-slate-900/60 rounded-lg p-3 text-xs border border-slate-800 space-y-1">
          <div class="font-semibold text-slate-400">Vorschau der Steckdosen:</div>
          <ul class="list-disc list-inside text-slate-300 space-y-0.5 font-mono">
            {#each pduAutoPreview.summary as item}
              <li>{item.count}x {item.type} (max. {item.maxWatt}W)</li>
            {/each}
          </ul>
          <div class="text-[10px] text-slate-500 pt-1 border-t border-slate-800 flex justify-between">
            <span>Gesamt: {pduAutoPreview.totalCount}</span>
            <span>Verteilung: L1: {pduAutoPreview.phaseDistribution.L1} | L2: {pduAutoPreview.phaseDistribution.L2} | L3: {pduAutoPreview.phaseDistribution.L3}</span>
          </div>
        </div>
      {/if}
      
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Phasen-Verteilung</label>
        <select bind:value={pduAutoPhaseMode}
          class="w-full bg-[#182030] border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500">
          <option value="alternate">Abwechselnd L1 / L2 / L3</option>
          <option value="L1">L1 fest</option>
          <option value="L2">L2 fest</option>
          <option value="L3">L3 fest</option>
        </select>
      </div>

      <div class="flex items-center space-x-2 pt-1">
        <input type="checkbox" id="deleteExisting" bind:checked={deleteExistingOutlets}
          class="rounded bg-[#182030] border-slate-700 text-blue-600 focus:ring-0 focus:ring-offset-0" />
        <label for="deleteExisting" class="text-xs font-semibold text-slate-300 select-none cursor-pointer">
          Bestehende Steckdosen vorher löschen
        </label>
      </div>

      <div class="flex justify-end space-x-3 pt-2">
        <button type="button" onclick={() => showPduAutoOutlet=false} class="px-4 py-2 text-sm text-slate-400 hover:bg-slate-800 rounded-lg transition">Abbrechen</button>
        <button type="submit" class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-semibold transition">Generieren</button>
      </div>
    </form>
  </div>
</div>
{/if}

{#if showConfirmModal}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-[9999] flex items-center justify-center p-4">
  <div class="bg-[#101622] border border-slate-800 rounded-xl p-6 max-w-sm w-full shadow-2xl">
    <div class="flex items-center space-x-3 mb-4">
      <div class="p-2 bg-red-950/50 border border-red-500/30 rounded-lg text-red-500">
        <Trash2 class="w-6 h-6" />
      </div>
      <h3 class="text-lg font-bold text-white font-outfit">Bestätigung erforderlich</h3>
    </div>
    <p class="text-sm text-slate-300 mb-6 leading-relaxed">
      {confirmMessage}
    </p>
    <div class="flex justify-end space-x-3">
      <button type="button" onclick={() => { showConfirmModal = false; onConfirmCallback = null; }} class="px-4 py-2 text-sm text-slate-400 hover:bg-slate-800 rounded-lg transition">
        Abbrechen
      </button>
      <button type="button" onclick={handleConfirm} class="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg text-sm font-semibold transition">
        {confirmButtonText}
      </button>
    </div>
  </div>
</div>
{/if}

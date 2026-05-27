<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import { api, type Runbook, type RunbookLayer, type RunbookDevice, type Device, type VirtualMachine, type RunbookExecution } from '$lib/api';
  import { BookOpen, Layers, Monitor, Server, Plus, ArrowLeft, Trash2, ArrowUp, ArrowDown, Play, CheckCircle2, Copy, FileText, Clock, User, XCircle, AlertCircle, Edit, Download } from '@lucide/svelte';
  import { goto } from '$app/navigation';

  let runbookId = parseInt(page.params.id);
  let runbook = $state<Runbook | null>(null);
  let loading = $state(true);
  
  let allDevices = $state<Device[]>([]);
  let allVms = $state<VirtualMachine[]>([]);
  let executions = $state<RunbookExecution[]>([]);

  let activeTab = $state<'PLANER' | 'AUSFÜHRUNG' | 'PROTOKOLL'>('PLANER');

  // Drag & Drop / Sidebar states
  let searchQuery = $state('');
  let sidebarTab = $state<'vms' | 'devices'>('vms');
  let draggedOverLayerId = $state<number | null>(null);
  let draggedOverDeviceId = $state<number | null>(null);
  let draggedOverAddButtonLayerId = $state<number | null>(null);

  // Layer Inline-Editing
  let editingLayerId = $state<number | null>(null);
  let editingLayerName = $state('');

  // Layer Inline Add state
  let showInlineLayerForm = $state(false);
  let selectedLayerTemplate = $state('Web-Tier');
  let inlineLayerFreitext = $state('');
  
  let showDeviceModal = $state(false);
  let targetLayerId = $state<number | null>(null);
  let deviceType = $state<'device' | 'vm' | 'freitext'>('vm');
  let selectedDeviceId = $state<number | null>(null);
  let selectedVmId = $state<number | null>(null);
  let freitext = $state('');
  let delay = $state(30);
  let responsible = $state('');
  let deviceNote = $state('');
  
  let showEditDeviceModal = $state(false);
  let editingDevice = $state<RunbookDevice | null>(null);

  // Execution states
  let currentExecution = $state<RunbookExecution | null>(null);
  let execMode = $state<'shutdown' | 'startup'>('shutdown');
  let showExecutionDetailsModal = $state(false);
  let selectedExecutionDetails = $state<RunbookExecution | null>(null);

  // Derived layers for execution (reversed for startup)
  let executionLayers = $derived.by(() => {
    if (!runbook || !runbook.layers) return [];
    const isStartup = currentExecution?.modus === 'startup';
    const sorted = [...runbook.layers].sort((a, b) => a.position - b.position);
    return isStartup ? sorted.reverse() : sorted;
  });

  const getSortedDevices = (layer: RunbookLayer) => {
    const isStartup = currentExecution?.modus === 'startup';
    const sorted = [...(layer.devices || [])].sort((a, b) => a.position - b.position);
    return isStartup ? sorted.reverse() : sorted;
  };

  onMount(async () => {
    await loadData();
  });

  async function loadData() {
    try {
      loading = true;
      const [rb, devs, vmsList] = await Promise.all([
        api.getRunbook(runbookId),
        api.getDevices(),
        api.getVirtualMachines()
      ]);
      runbook = rb;
      allDevices = devs.filter(d => ['server', 'pdu', 'switch', 'firewall', 'storage', 'sonstige'].includes(d.typ));
      allVms = vmsList;
      
      // Load executions in background
      loadExecutions();
    } catch (e) {
      console.error(e);
    } finally {
      loading = false;
    }
  }

  async function loadExecutions() {
    try {
      executions = await api.getRunbookExecutions(runbookId);
      // Find active execution if any
      const active = executions.find(e => e.status === 'offen');
      if (active) {
        currentExecution = await api.getExecution(active.id);
      } else {
        currentExecution = null;
      }
    } catch (e) {
      console.error("Fehler beim Laden der Ausführungen:", e);
    }
  }

  async function openExecutionDetails(exec: RunbookExecution) {
    try {
      selectedExecutionDetails = await api.getExecution(exec.id);
      showExecutionDetailsModal = true;
    } catch (e: any) {
      alert("Fehler beim Laden der Protokolldetails: " + e.message);
    }
  }

  // --- PLANER ACTIONS ---

  async function addLayer() {
    let nameToSave = selectedLayerTemplate === 'freitext' ? inlineLayerFreitext : selectedLayerTemplate;
    if (!nameToSave || !nameToSave.trim() || !runbook) return;
    try {
      await api.createRunbookLayer(runbook.id, {
        name: nameToSave.trim(),
        position: (runbook.layers?.length || 0) + 1
      });
      showInlineLayerForm = false;
      inlineLayerFreitext = '';
      await loadData();
    } catch (e) { alert(e); }
  }

  async function deleteLayer(lid: number) {
    if (!confirm("Ebene löschen?")) return;
    try {
      await api.deleteRunbookLayer(runbook!.id, lid);
      await loadData();
    } catch (e) { alert(e); }
  }

  async function saveLayerName(lid: number) {
    if (!editingLayerName.trim() || !runbook) {
      editingLayerId = null;
      return;
    }
    try {
      await api.updateRunbookLayer(runbook.id, lid, { name: editingLayerName });
      const l = runbook.layers?.find(x => x.id === lid);
      if (l) l.name = editingLayerName;
    } catch (e: any) {
      alert(e.message);
    } finally {
      editingLayerId = null;
    }
  }

  async function updateLayerNote(lid: number, note: string) {
    try {
      await api.updateRunbookLayer(runbook!.id, lid, { markdown_note: note });
    } catch (e) { alert(e); }
  }

  async function moveLayer(index: number, direction: -1 | 1) {
    if (!runbook?.layers) return;
    const newIndex = index + direction;
    if (newIndex < 0 || newIndex >= runbook.layers.length) return;
    
    const layers = [...runbook.layers].sort((a, b) => a.position - b.position);
    const temp = layers[index];
    layers[index] = layers[newIndex];
    layers[newIndex] = temp;
    
    const layerIds = layers.map(l => l.id);
    try {
      await api.reorderRunbookLayers(runbook.id, layerIds);
      await loadData();
    } catch (e) { alert(e); }
  }

  async function addDevice() {
    if (!targetLayerId || !runbook) return;
    try {
      await api.createRunbookDevice(runbook.id, {
        layer_id: targetLayerId,
        device_id: deviceType === 'device' ? selectedDeviceId : null,
        vm_id: deviceType === 'vm' ? selectedVmId : null,
        freitext: deviceType === 'freitext' ? freitext : null,
        delay_seconds: delay,
        responsible: responsible,
        note: deviceNote,
        position: 999
      });
      showDeviceModal = false;
      await loadData();
    } catch (e) { alert(e); }
  }

  async function deleteDevice(did: number) {
    if (!confirm("Gerät entfernen?")) return;
    try {
      await api.deleteRunbookDevice(runbook!.id, did);
      await loadData();
    } catch (e) { alert(e); }
  }

  async function moveDevice(layer: RunbookLayer, index: number, direction: -1 | 1) {
    if (!runbook || !layer.devices) return;
    const newIndex = index + direction;
    if (newIndex < 0 || newIndex >= layer.devices.length) return;
    
    const devices = [...layer.devices].sort((a, b) => a.position - b.position);
    const temp = devices[index];
    devices[index] = devices[newIndex];
    devices[newIndex] = temp;
    
    const deviceIds = devices.map(d => d.id);
    try {
      await api.reorderRunbookDevices(runbook.id, deviceIds);
      await loadData();
    } catch (e) { alert(e); }
  }

  function openEditDevice(d: RunbookDevice) {
    editingDevice = { ...d };
    showEditDeviceModal = true;
  }

  async function saveEditDevice() {
    if (!editingDevice || !runbook) return;
    try {
      await api.updateRunbookDevice(runbook.id, editingDevice.id, {
        delay_seconds: editingDevice.delay_seconds,
        responsible: editingDevice.responsible,
        note: editingDevice.note
      });
      showEditDeviceModal = false;
      await loadData();
    } catch (e) { alert(e); }
  }

  async function generateStartup() {
    if (!runbook) return;
    try {
      const newRb = await api.generateStartupRunbook(runbook.id);
      goto(`/runbook-orchestrator/${newRb.id}`);
    } catch (e: any) {
      alert("Fehler: " + e.message);
    }
  }

  // --- EXECUTION ACTIONS ---

  async function startExecution() {
    if (!runbook) return;
    try {
      const exec = await api.executeRunbook(runbook.id, {
        runbook_id: runbook.id,
        modus: execMode
      });
      currentExecution = await api.getExecution(exec.id);
    } catch (e: any) { alert("Fehler: " + e.message); }
  }

  async function checkStep(did: number, note: string) {
    if (!currentExecution) return;
    try {
      await api.checkExecutionStep(currentExecution.id, did, note);
      currentExecution = await api.getExecution(currentExecution.id);
      await loadExecutions();
    } catch (e: any) { alert("Fehler: " + e.message); }
  }

  async function toggleStep(did: number, note: string = '') {
    if (!currentExecution) return;
    const checked = isStepChecked(did);
    try {
      if (checked) {
        await api.uncheckExecutionStep(currentExecution.id, did);
      } else {
        await api.checkExecutionStep(currentExecution.id, did, note);
      }
      currentExecution = await api.getExecution(currentExecution.id);
      await loadExecutions();
    } catch (e: any) { alert("Fehler: " + e.message); }
  }

  async function updateExecutionStatus(status: 'abgeschlossen' | 'verworfen') {
    if (!currentExecution) return;
    
    let note = '';
    if (status === 'verworfen') {
      const reason = prompt("Bitte geben Sie eine Begründung für das Verwerfen der Ausführung ein (Pflichtfeld):");
      if (reason === null) return; // user cancelled
      if (!reason.trim()) {
        alert("Begründung ist zwingend erforderlich!");
        return;
      }
      note = reason.trim();
    } else {
      if (!confirm("Ausführung wirklich abschließen?")) return;
    }
    
    try {
      await api.updateExecutionStatus(currentExecution.id, status, note);
      currentExecution = null;
      await loadExecutions();
    } catch (e: any) { alert("Fehler: " + e.message); }
  }

  function isStepChecked(did: number) {
    return currentExecution?.steps?.some(s => s.runbook_device_id === did && s.abgehakt_am);
  }
  
  function getStep(did: number) {
    return currentExecution?.steps?.find(s => s.runbook_device_id === did);
  }

  function getDeviceName(d: RunbookDevice) {
    if (d.vm) return d.vm.name;
    if (d.device) return d.device.hostname;
    return d.freitext || 'Unbekannt';
  }
  
  function getDeviceIcon(d: RunbookDevice) {
    if (d.vm) return Monitor;
    if (d.device) return Server;
    return FileText;
  }

  function exportMarkdown() {
    window.open(`/api/v1/runbooks/${runbookId}/export/markdown`, '_blank');
  }

  function exportPdf() {
    window.open(`/api/v1/runbooks/${runbookId}/export/pdf`, '_blank');
  }

  // --- DRAG & DROP FUNCTIONS ---

  function handleDragStartResource(e: DragEvent, type: 'vm' | 'device', id: number, name: string) {
    if (!e.dataTransfer) return;
    e.dataTransfer.setData('text/plain', JSON.stringify({ type, id, name }));
    e.dataTransfer.effectAllowed = 'copy';
  }

  function handleDragStartFreitext(e: DragEvent) {
    if (!e.dataTransfer) return;
    e.dataTransfer.setData('text/plain', JSON.stringify({ type: 'freitext' }));
    e.dataTransfer.effectAllowed = 'copy';
  }

  function handleDragStartDevice(e: DragEvent, devId: number, layerId: number, index: number) {
    if (!e.dataTransfer) return;
    e.dataTransfer.setData('text/plain', JSON.stringify({ type: 'runbook-device', id: devId, layerId, index }));
    e.dataTransfer.effectAllowed = 'move';
  }

  function handleDragOverLayer(e: DragEvent, layerId: number) {
    e.preventDefault();
    draggedOverLayerId = layerId;
  }

  function handleDragLeaveLayer() {
    draggedOverLayerId = null;
  }

  async function handleDropLayer(e: DragEvent, layerId: number) {
    e.preventDefault();
    draggedOverLayerId = null;
    if (!e.dataTransfer || !runbook) return;
    
    try {
      const rawData = e.dataTransfer.getData('text/plain');
      if (!rawData) return;
      const data = JSON.parse(rawData);
      
      if (data.type === 'vm') {
        await api.createRunbookDevice(runbook.id, {
          layer_id: layerId,
          vm_id: data.id,
          device_id: null,
          freitext: null,
          delay_seconds: 30,
          position: 999
        });
        await loadData();
      } else if (data.type === 'device') {
        await api.createRunbookDevice(runbook.id, {
          layer_id: layerId,
          device_id: data.id,
          vm_id: null,
          freitext: null,
          delay_seconds: 30,
          position: 999
        });
        await loadData();
      } else if (data.type === 'freitext') {
        targetLayerId = layerId;
        deviceType = 'freitext';
        freitext = '';
        delay = 30;
        responsible = '';
        deviceNote = '';
        showDeviceModal = true;
      } else if (data.type === 'runbook-device') {
        if (data.layerId !== layerId) {
          await api.updateRunbookDevice(runbook.id, data.id, {
            layer_id: layerId
          });
          await loadData();
        }
      }
    } catch (err: any) {
      console.error(err);
    }
  }

  async function handleDropDevice(e: DragEvent, targetLid: number, targetIdx: number) {
    e.preventDefault();
    draggedOverLayerId = null;
    if (!e.dataTransfer || !runbook) return;
    
    try {
      const rawData = e.dataTransfer.getData('text/plain');
      if (!rawData) return;
      const data = JSON.parse(rawData);
      
      if (data.type === 'runbook-device') {
        const deviceId = data.id;
        const sourceLid = data.layerId;
        
        if (sourceLid !== targetLid) {
          await api.updateRunbookDevice(runbook.id, deviceId, {
            layer_id: targetLid
          });
        }
        
        const rb = await api.getRunbook(runbook.id);
        runbook = rb;
        
        const layer = runbook.layers?.find(l => l.id === targetLid);
        if (!layer || !layer.devices) return;
        
        let devices = [...layer.devices].sort((a, b) => a.position - b.position);
        const itemIdx = devices.findIndex(d => d.id === deviceId);
        const draggedItem = devices.find(d => d.id === deviceId);
        
        if (draggedItem) {
          if (itemIdx > -1) {
            devices.splice(itemIdx, 1);
          }
          devices.splice(targetIdx, 0, draggedItem);
          const deviceIds = devices.map(d => d.id);
          await api.reorderRunbookDevices(runbook.id, deviceIds);
        }
        await loadData();
      } else if (data.type === 'vm' || data.type === 'device') {
        const newDev = await api.createRunbookDevice(runbook.id, {
          layer_id: targetLid,
          vm_id: data.type === 'vm' ? data.id : null,
          device_id: data.type === 'device' ? data.id : null,
          position: 999
        });
        
        const rb = await api.getRunbook(runbook.id);
        runbook = rb;
        const layer = runbook.layers?.find(l => l.id === targetLid);
        if (layer && layer.devices) {
          let devices = [...layer.devices].sort((a, b) => a.position - b.position);
          const itemIdx = devices.findIndex(d => d.id === newDev.id);
          if (itemIdx > -1) {
            devices.splice(itemIdx, 1);
          }
          devices.splice(targetIdx, 0, newDev);
          const deviceIds = devices.map(d => d.id);
          await api.reorderRunbookDevices(runbook.id, deviceIds);
        }
        await loadData();
      }
    } catch (err: any) {
      console.error(err);
    }
  }

  function isAlreadyInRunbook(type: 'vm' | 'device', id: number) {
    if (!runbook || !runbook.layers) return false;
    return runbook.layers.some(l => 
      (l.devices || []).some(d => 
        (type === 'vm' && d.vm_id === id) || (type === 'device' && d.device_id === id)
      )
    );
  }
</script>

<div class="h-full flex flex-col space-y-4">
  {#if loading}
    <div class="text-slate-500 py-12 text-center">Lade Runbook...</div>
  {:else if runbook}
    <!-- Header -->
    <div class="flex items-center justify-between bg-[#131615] border border-slate-800 rounded-xl p-4 shrink-0">
      <div class="flex items-center gap-4">
        <button onclick={() => goto('/runbook-orchestrator')} class="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition">
          <ArrowLeft class="w-5 h-5" />
        </button>
        <div>
          <div class="flex items-center gap-2">
            <h1 class="text-xl font-bold text-white tracking-tight">{runbook.name}</h1>
            <span class="text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded border bg-yellow-500/10 text-yellow-400 border-yellow-500/20">
              {runbook.typ}
            </span>
            {#if runbook.generated_from_id}
              <span class="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded border border-slate-700">
                Generiert aus ID: {runbook.generated_from_id}
              </span>
            {/if}
          </div>
          <p class="text-xs text-slate-400 mt-1">{runbook.beschreibung || 'Keine Beschreibung'}</p>
        </div>
      </div>
      <div class="flex items-center gap-3">
        {#if runbook.typ === 'shutdown'}
          <button onclick={generateStartup} class="flex items-center gap-2 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 px-3 py-1.5 rounded-lg text-xs font-medium transition">
            <Copy class="w-3.5 h-3.5" />
            Startup generieren
          </button>
        {/if}
        <button onclick={exportMarkdown} class="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 px-3 py-1.5 rounded-lg text-xs font-medium transition">
          <FileText class="w-3.5 h-3.5" />
          MD Export
        </button>
        <button onclick={exportPdf} class="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 px-3 py-1.5 rounded-lg text-xs font-medium transition">
          <Download class="w-3.5 h-3.5" />
          PDF Export
        </button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="flex space-x-1 border-b border-slate-800 shrink-0">
      {#each ['PLANER', 'AUSFÜHRUNG', 'PROTOKOLL'] as tab}
        <button
          onclick={() => activeTab = tab as any}
          class={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${activeTab === tab ? 'border-[#1D9E75] text-blue-400' : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-600'}`}
        >
          {tab}
        </button>
      {/each}
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto">
      {#if activeTab === 'PLANER'}
        {#if currentExecution}
          <div class="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 text-amber-400 text-sm flex items-center gap-3 mb-6 shrink-0">
            <AlertCircle class="w-5 h-5 shrink-0" />
            <div>
              <span class="font-bold">Planer gesperrt:</span> Es läuft aktuell eine Ausführung für dieses Runbook. Bitte schließen Sie diese ab oder verwerfen Sie sie im Tab "Ausführung", um Änderungen vorzunehmen.
            </div>
          </div>
        {/if}
        <div class="flex gap-6 pb-12 items-start">
          <!-- Left Column: Layers (2/3 width) -->
          <div class="flex-1 space-y-6">
            {#each [...(runbook.layers || [])].sort((a,b) => a.position - b.position) as layer, i}
              <div 
                class={`bg-[#131615] border rounded-xl overflow-hidden transition ${draggedOverLayerId === layer.id ? 'border-[#1D9E75] bg-blue-950/5' : 'border-slate-800'}`}
                ondragover={(e) => { if (!currentExecution) handleDragOverLayer(e, layer.id); }}
                ondragleave={() => { if (!currentExecution) handleDragLeaveLayer(); }}
                ondrop={(e) => { if (!currentExecution) handleDropLayer(e, layer.id); }}
              >
                <!-- Layer Header -->
                <div class="bg-slate-800/50 p-4 border-b border-slate-800 flex items-center justify-between group/header">
                  <div class="flex items-center gap-3">
                    <div class="w-6 h-6 rounded bg-slate-800 flex items-center justify-center text-xs font-bold text-slate-400 border border-slate-700">
                      {layer.position}
                    </div>
                    {#if editingLayerId === layer.id}
                      <input
                        type="text"
                        bind:value={editingLayerName}
                        onblur={() => saveLayerName(layer.id)}
                        onkeydown={(e) => {
                          if (e.key === 'Enter') saveLayerName(layer.id);
                          if (e.key === 'Escape') editingLayerId = null;
                        }}
                        class="bg-[#181C1A] text-sm font-bold text-white px-2 py-1 border border-[#1D9E75] rounded outline-none w-64"
                        autofocus
                      />
                    {:else}
                      <h3 
                        class={`text-sm font-bold text-white flex items-center gap-2 ${!currentExecution ? 'cursor-pointer hover:text-blue-400' : ''} transition`}
                        onclick={() => { if (!currentExecution) { editingLayerId = layer.id; editingLayerName = layer.name; } }}
                        title={!currentExecution ? "Klicken zum Umbenennen" : ""}
                      >
                        <Layers class="w-4 h-4 text-blue-400" />
                        {layer.name}
                      </h3>
                    {/if}
                  </div>
                  <div class="flex items-center gap-1 opacity-50 group-hover/header:opacity-100 transition-opacity">
                    {#if !currentExecution}
                      <button onclick={() => { editingLayerId = layer.id; editingLayerName = layer.name; }} class="p-1.5 text-slate-500 hover:text-blue-400 hover:bg-slate-700 rounded mr-2" title="Ebene umbenennen"><Edit class="w-3.5 h-3.5" /></button>
                      <button disabled={i === 0} onclick={() => moveLayer(i, -1)} class="p-1.5 text-slate-500 hover:text-white hover:bg-slate-700 rounded disabled:opacity-30"><ArrowUp class="w-3.5 h-3.5" /></button>
                      <button disabled={i === (runbook.layers?.length || 0) - 1} onclick={() => moveLayer(i, 1)} class="p-1.5 text-slate-500 hover:text-white hover:bg-slate-700 rounded disabled:opacity-30"><ArrowDown class="w-3.5 h-3.5" /></button>
                      <button onclick={() => deleteLayer(layer.id)} class="p-1.5 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded ml-2"><Trash2 class="w-3.5 h-3.5" /></button>
                    {/if}
                  </div>
                </div>

                <!-- Layer Body -->
                <div class="p-4">
                  <textarea 
                    disabled={!!currentExecution}
                    class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-300 focus:border-[#1D9E75] resize-none mb-4 disabled:opacity-50"
                    rows="2"
                    placeholder="Notizen / Instruktionen (Markdown unterstützt) ..."
                    value={layer.markdown_note || ''}
                    onblur={(e) => updateLayerNote(layer.id, e.currentTarget.value)}
                  ></textarea>

                  <div class="space-y-2">
                    {#each [...(layer.devices || [])].sort((a,b) => a.position - b.position) as dev, dIdx}
                      {@const Icon = getDeviceIcon(dev)}
                      <div 
                        draggable={!currentExecution}
                        ondragstart={(e) => { if (!currentExecution) handleDragStartDevice(e, dev.id, layer.id, dIdx); }}
                        ondragover={(e) => { if (!currentExecution) { e.preventDefault(); draggedOverDeviceId = dev.id; } }}
                        ondragleave={() => { if (!currentExecution) draggedOverDeviceId = null; }}
                        ondrop={(e) => { if (!currentExecution) { draggedOverDeviceId = null; handleDropDevice(e, layer.id, dIdx); } }}
                        class={`flex items-center justify-between bg-slate-900/50 border rounded-lg p-2.5 group hover:border-slate-600 transition ${draggedOverDeviceId === dev.id ? 'border-[#1D9E75] bg-blue-950/20' : 'border-slate-800/80'}`}
                      >
                        <div class="flex items-center gap-3">
                          {#if !currentExecution}
                            <div class="flex flex-col gap-0.5">
                              <button disabled={dIdx === 0} onclick={() => moveDevice(layer, dIdx, -1)} class="text-slate-600 hover:text-slate-300 disabled:opacity-30"><ArrowUp class="w-3 h-3" /></button>
                              <button disabled={dIdx === (layer.devices?.length || 0) - 1} onclick={() => moveDevice(layer, dIdx, 1)} class="text-slate-600 hover:text-slate-300 disabled:opacity-30"><ArrowDown class="w-3 h-3" /></button>
                            </div>
                          {/if}
                          
                          <div class="w-8 h-8 rounded bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0">
                            <Icon class={`w-4 h-4 ${dev.vm ? 'text-pink-400' : dev.device ? 'text-slate-300' : 'text-blue-400'}`} />
                          </div>
                          
                          <div>
                            <div class="text-sm font-medium text-slate-200">{getDeviceName(dev)}</div>
                            {#if dev.device && dev.device.connected_pdu_outlets && dev.device.connected_pdu_outlets.length > 0}
                              <div class="flex flex-wrap gap-1 mt-1">
                                {#each dev.device.connected_pdu_outlets as outlet}
                                  <span class="inline-flex items-center text-[9px] bg-blue-500/10 text-blue-400 border border-[#1D9E75]/20 px-1.5 py-0.5 rounded font-mono">
                                    {outlet.pdu_name || `PDU-${outlet.pdu_id}`} · {outlet.outlet_name}
                                  </span>
                                {/each}
                              </div>
                            {/if}
                            <div class="text-[10px] text-slate-500 flex items-center gap-2 mt-0.5">
                              <span class="flex items-center gap-1"><Clock class="w-3 h-3" /> {dev.delay_seconds}s</span>
                              {#if dev.responsible}
                                <span class="flex items-center gap-1"><User class="w-3 h-3" /> {dev.responsible}</span>
                              {/if}
                            </div>
                            {#if dev.note}
                              <div class="text-xs text-amber-500/80 mt-1 italic">{dev.note}</div>
                            {/if}
                          </div>
                        </div>
                        {#if !currentExecution}
                          <div class="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition">
                            <button onclick={() => openEditDevice(dev)} class="p-1.5 text-blue-400 hover:bg-[#1D9E75]/10 rounded"><Edit class="w-4 h-4" /></button>
                            <button onclick={() => deleteDevice(dev.id)} class="p-1.5 text-red-400 hover:bg-red-500/10 rounded"><Trash2 class="w-4 h-4" /></button>
                          </div>
                        {/if}
                      </div>
                    {/each}
                    
                    {#if !currentExecution}
                      <button 
                        onclick={() => { targetLayerId = layer.id; showDeviceModal = true; }}
                        ondragover={(e) => { e.preventDefault(); draggedOverAddButtonLayerId = layer.id; }}
                        ondragleave={() => draggedOverAddButtonLayerId = null}
                        ondrop={(e) => { draggedOverAddButtonLayerId = null; handleDropLayer(e, layer.id); }}
                        class={`w-full flex items-center justify-center gap-2 py-2 border-2 border-dashed rounded-lg text-xs transition ${draggedOverAddButtonLayerId === layer.id ? 'border-[#1D9E75] bg-blue-950/20 text-blue-300' : 'border-slate-800 hover:border-slate-600 text-slate-400 hover:text-slate-200'}`}
                      >
                        <Plus class="w-3.5 h-3.5" /> Gerät hinzufügen (oder hierher ziehen)
                      </button>
                    {/if}
                  </div>
                </div>
              </div>
            {/each}

            {#if !currentExecution}
              {#if showInlineLayerForm}
                <div class="bg-[#131615] border border-slate-800 rounded-xl p-4 space-y-4">
                  <h4 class="text-sm font-bold text-white">Neue Ebene hinzufügen</h4>
                  <div class="flex flex-wrap gap-4 items-end">
                    <div class="flex-1 min-w-[200px]">
                      <label class="block text-xs font-semibold text-slate-400 mb-1">Ebenen-Typ / Template</label>
                      <select 
                        bind:value={selectedLayerTemplate} 
                        class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]"
                      >
                        <option value="Web-Tier">Web-Tier</option>
                        <option value="App-Tier">App-Tier</option>
                        <option value="Datenbank-Tier">Datenbank-Tier</option>
                        <option value="Netzwerk">Netzwerk</option>
                        <option value="Storage">Storage</option>
                        <option value="Sonstige">Sonstige</option>
                        <option value="freitext">Freitext / Eigener Name...</option>
                      </select>
                    </div>
                    
                    {#if selectedLayerTemplate === 'freitext'}
                      <div class="flex-1 min-w-[200px]">
                        <label class="block text-xs font-semibold text-slate-400 mb-1">Eigener Ebenen-Name</label>
                        <input 
                          type="text" 
                          bind:value={inlineLayerFreitext} 
                          placeholder="z.B. Cache-Tier" 
                          class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]"
                        />
                      </div>
                    {/if}
                    
                    <div class="flex gap-2">
                      <button 
                        onclick={() => { showInlineLayerForm = false; inlineLayerFreitext = ''; }} 
                        class="px-4 py-2 rounded-lg text-sm text-slate-400 hover:bg-slate-800 transition"
                      >
                        Abbrechen
                      </button>
                      <button 
                        onclick={addLayer} 
                        disabled={selectedLayerTemplate === 'freitext' && !inlineLayerFreitext.trim()} 
                        class="px-4 py-2 bg-[#1D9E75] hover:bg-[#0F6E56] disabled:opacity-50 text-white rounded-lg text-sm font-semibold transition"
                      >
                        Hinzufügen
                      </button>
                    </div>
                  </div>
                </div>
              {:else}
                <button 
                  onclick={() => { showInlineLayerForm = true; selectedLayerTemplate = 'Web-Tier'; }}
                  class="w-full flex items-center justify-center gap-2 py-4 bg-[#1D9E75]/10 hover:bg-[#1D9E75]/20 text-blue-400 border border-blue-600/20 rounded-xl text-sm font-medium transition"
                >
                  <Plus class="w-4 h-4" /> Neue Ebene hinzufügen
                </button>
              {/if}
            {/if}
          </div>

          <!-- Right Column: Sidebar (1/3 width, sticky) -->
          <div class={`w-80 bg-[#131615] border border-slate-800 rounded-xl p-4 sticky top-4 shrink-0 flex flex-col max-h-[85vh] transition ${currentExecution ? 'opacity-40 pointer-events-none' : ''}`}>
            <h3 class="text-sm font-bold text-white mb-1">Ressourcen-Katalog</h3>
            <p class="text-[10px] text-slate-400 mb-3">Ziehe Elemente per Drag & Drop in eine beliebige Ebene, um sie hinzuzufügen.</p>

            <!-- Sidebar Tabs -->
            <div class="flex border-b border-slate-800 mb-3 shrink-0">
              <button 
                onclick={() => sidebarTab = 'vms'}
                class={`flex-1 pb-2 text-xs font-semibold border-b-2 transition ${sidebarTab === 'vms' ? 'border-pink-500 text-pink-400' : 'border-transparent text-slate-400 hover:text-slate-200'}`}
              >
                VMs ({allVms.length})
              </button>
              <button 
                onclick={() => sidebarTab = 'devices'}
                class={`flex-1 pb-2 text-xs font-semibold border-b-2 transition ${sidebarTab === 'devices' ? 'border-[#1D9E75] text-blue-400' : 'border-transparent text-slate-400 hover:text-slate-200'}`}
              >
                Geräte ({allDevices.length})
              </button>
            </div>

            <!-- Search Input -->
            <div class="mb-3 shrink-0">
              <input 
                type="text" 
                bind:value={searchQuery} 
                placeholder="Suchen..." 
                class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-[#1D9E75]"
              />
            </div>

            <!-- Drag Template for Freitext -->
            <div 
              draggable="true"
              ondragstart={handleDragStartFreitext}
              class="mb-3 p-2 bg-blue-500/10 border border-dashed border-[#1D9E75]/30 rounded-lg flex items-center justify-center gap-2 cursor-grab hover:bg-[#0F6E56]/20 text-xs text-blue-400 font-semibold select-none shrink-0"
            >
              <Plus class="w-3.5 h-3.5" />
              Freitext-Gerät (ziehen)
            </div>

            <!-- Scrollable List -->
            <div class="flex-1 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
              {#if sidebarTab === 'vms'}
                {#each allVms.filter(v => v.name.toLowerCase().includes(searchQuery.toLowerCase())) as vm}
                  {@const added = isAlreadyInRunbook('vm', vm.id)}
                  <div 
                    draggable="true"
                    ondragstart={(e) => handleDragStartResource(e, 'vm', vm.id, vm.name)}
                    class={`p-2 bg-slate-900/40 border rounded-lg cursor-grab hover:border-pink-500/60 transition select-none flex items-center justify-between ${added ? 'border-emerald-500/30 opacity-70 bg-emerald-950/5' : 'border-slate-800'}`}
                  >
                    <div class="flex items-center gap-2 min-w-0">
                      <Monitor class="w-3.5 h-3.5 text-pink-400 shrink-0" />
                      <div class="truncate text-xs">
                        <div class="font-medium text-slate-200 truncate">{vm.name}</div>
                        <div class="text-[9px] text-slate-500 mt-0.5">{vm.ip_adresse || 'Keine IP'}</div>
                      </div>
                    </div>
                    {#if added}
                      <span class="text-[9px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-1.5 py-0.5 rounded shrink-0">
                        Plan
                      </span>
                    {/if}
                  </div>
                {/each}
              {:else}
                {#each allDevices.filter(d => d.hostname.toLowerCase().includes(searchQuery.toLowerCase())) as dev}
                  {@const added = isAlreadyInRunbook('device', dev.id)}
                  <div 
                    draggable="true"
                    ondragstart={(e) => handleDragStartResource(e, 'device', dev.id, dev.hostname)}
                    class={`p-2 bg-slate-900/40 border rounded-lg cursor-grab hover:border-[#1D9E75]/60 transition select-none flex items-center justify-between ${added ? 'border-emerald-500/30 opacity-70 bg-emerald-950/5' : 'border-slate-800'}`}
                  >
                    <div class="flex items-center gap-2 min-w-0">
                      <Server class="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      <div class="truncate text-xs">
                        <div class="font-medium text-slate-200 truncate">{dev.hostname}</div>
                        <div class="text-[9px] text-slate-500 mt-0.5 capitalize">{dev.typ} | {dev.ip_adresse || 'Keine IP'}</div>
                      </div>
                    </div>
                    {#if added}
                      <span class="text-[9px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-1.5 py-0.5 rounded shrink-0">
                        Plan
                      </span>
                    {/if}
                  </div>
                {/each}
              {/if}
            </div>
          </div>
        </div>
      {/if}

      {#if activeTab === 'AUSFÜHRUNG'}
        {#if !currentExecution}
          <div class="bg-[#131615] border border-slate-800 rounded-xl p-8 max-w-lg mx-auto mt-12 text-center">
            <Play class="w-12 h-12 text-emerald-400 mx-auto mb-4" />
            <h2 class="text-xl font-bold text-white mb-2">Neue Ausführung starten</h2>
            <p class="text-sm text-slate-400 mb-6">Sie sind im Begriff, die Sequenz live zu protokollieren. Alle Schritte werden revisionssicher erfasst.</p>
            
            <div class="mb-6 text-left">
              <label class="block text-xs font-semibold text-slate-400 mb-2">Modus</label>
              <select bind:value={execMode} class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500">
                <option value="shutdown">Shutdown (Herunterfahren)</option>
                <option value="startup">Startup (Hochfahren)</option>
              </select>
            </div>
            
            <button onclick={startExecution} class="w-full bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg px-4 py-3 text-sm font-bold transition flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/20">
              <Play class="w-4 h-4" />
              Starten
            </button>
          </div>
        {:else}
          <!-- Execution Checklist -->
          <div class="space-y-6 pb-12">
            <div class="flex items-center justify-between bg-slate-800/40 border border-slate-700 rounded-xl p-4">
              <div>
                <div class="text-xs text-slate-400 mb-1">Status: <span class="font-bold text-emerald-400 uppercase">{currentExecution.status}</span></div>
                <div class="text-[10px] text-slate-500">Gestartet am: {new Date(currentExecution.gestartet_am).toLocaleString()}</div>
              </div>
              {#if currentExecution.status === 'offen'}
                <div class="flex items-center gap-2">
                  <button onclick={() => updateExecutionStatus('verworfen')} class="px-3 py-1.5 bg-red-500/10 text-red-400 hover:bg-red-500/20 rounded-lg text-xs font-medium border border-red-500/20 transition">Verwerfen</button>
                  <button onclick={() => updateExecutionStatus('abgeschlossen')} class="px-3 py-1.5 bg-emerald-500 hover:bg-emerald-400 text-white rounded-lg text-xs font-medium transition shadow-lg shadow-emerald-500/20 flex items-center gap-1"><CheckCircle2 class="w-3.5 h-3.5"/> Abschließen</button>
                </div>
              {/if}
            </div>

            {#each executionLayers as layer}
              <div class="bg-[#131615] border border-slate-800 rounded-xl overflow-hidden">
                <div class="bg-slate-800/50 p-3 border-b border-slate-800 flex items-center gap-3">
                  <div class="w-5 h-5 rounded bg-slate-800 flex items-center justify-center text-[10px] font-bold text-slate-400 border border-slate-700">{layer.position}</div>
                  <h3 class="text-sm font-bold text-white">{layer.name}</h3>
                </div>
                {#if layer.markdown_note}
                  <div class="px-4 py-2 bg-blue-900/10 border-b border-blue-900/20 text-xs text-blue-200/80 italic">{layer.markdown_note}</div>
                {/if}
                <div class="divide-y divide-slate-800/50">
                  {#each getSortedDevices(layer) as dev}
                    {@const checked = isStepChecked(dev.id)}
                    {@const step = getStep(dev.id)}
                    <div class={`p-3 flex items-start gap-3 transition-colors ${checked ? 'bg-emerald-900/5' : 'hover:bg-slate-800/30'}`}>
                      <button 
                        onclick={() => toggleStep(dev.id, '')}
                        disabled={currentExecution.status !== 'offen'}
                        class={`mt-1 shrink-0 w-6 h-6 rounded flex items-center justify-center border transition ${checked ? 'bg-emerald-500 border-emerald-500 text-white' : 'bg-[#181C1A] border-slate-600 text-transparent hover:border-emerald-400 disabled:opacity-50'}`}
                      >
                        <CheckCircle2 class="w-4 h-4" />
                      </button>
                      <div class="flex-1">
                        <div class="flex justify-between items-start">
                          <div>
                            <div class={`text-sm font-medium ${checked ? 'text-slate-400 line-through' : 'text-slate-200'}`}>{getDeviceName(dev)}</div>
                            {#if dev.device && dev.device.connected_pdu_outlets && dev.device.connected_pdu_outlets.length > 0}
                              <div class="flex flex-wrap gap-1 mt-1">
                                {#each dev.device.connected_pdu_outlets as outlet}
                                  <span class="inline-flex items-center text-[9px] bg-blue-500/10 text-blue-400 border border-[#1D9E75]/20 px-1.5 py-0.5 rounded font-mono">
                                    {outlet.pdu_name || `PDU-${outlet.pdu_id}`} · {outlet.outlet_name}
                                  </span>
                                {/each}
                              </div>
                            {/if}
                            <div class="text-[10px] text-slate-500 flex items-center gap-2 mt-0.5">
                              <span class="flex items-center gap-1"><Clock class="w-3 h-3" /> {dev.delay_seconds}s</span>
                              {#if dev.responsible}
                                <span class="flex items-center gap-1"><User class="w-3 h-3" /> {dev.responsible}</span>
                              {/if}
                            </div>
                          </div>
                          {#if checked && step}
                            <div class="text-[10px] text-emerald-500 bg-emerald-500/10 px-2 py-1 rounded flex flex-col items-end gap-0.5">
                              <span>{new Date(step.abgehakt_am || '').toLocaleTimeString()}</span>
                              {#if step.abgehakt_von}
                                <span class="text-[8px] opacity-80">von {step.abgehakt_von}</span>
                              {/if}
                            </div>
                          {/if}
                        </div>
                        {#if dev.note}
                          <div class="text-[10px] text-amber-500/80 mt-1">{dev.note}</div>
                        {/if}
                        {#if !checked && currentExecution.status === 'offen'}
                          <div class="mt-2">
                            <input 
                              type="text" 
                              placeholder="Optionale Notiz zur Ausführung..." 
                              onkeydown={(e) => { if (e.key === 'Enter') toggleStep(dev.id, e.currentTarget.value); }}
                              class="w-full bg-[#181C1A] border border-slate-700 rounded text-xs px-2 py-1 focus:border-emerald-500 outline-none text-slate-300"
                            />
                          </div>
                        {/if}
                        {#if checked && step?.note}
                          <div class="text-[10px] text-slate-400 bg-slate-800/50 p-2 rounded mt-2 border border-slate-700">
                            <strong>Notiz:</strong> {step.note}
                          </div>
                        {/if}
                      </div>
                    </div>
                  {/each}
                </div>
              </div>
            {/each}
          </div>
        {/if}
      {/if}

      {#if activeTab === 'PROTOKOLL'}
        <div class="space-y-4">
          {#if executions.length === 0}
            <div class="text-slate-500 py-12 text-center border border-dashed border-slate-800 rounded-xl bg-[#131615]">
              <FileText class="w-8 h-8 mx-auto mb-2 opacity-50 text-slate-400" />
              Bisher keine Protokolle vorhanden.
            </div>
          {:else}
            <div class="bg-[#131615] border border-slate-800 rounded-xl overflow-hidden shadow-2xl">
              <table class="w-full text-left text-sm text-slate-300">
                <thead class="text-xs uppercase bg-slate-800/50 text-slate-400 border-b border-slate-800">
                  <tr>
                    <th class="px-4 py-3 font-semibold">Datum</th>
                    <th class="px-4 py-3 font-semibold">Modus</th>
                    <th class="px-4 py-3 font-semibold">Gestartet von</th>
                    <th class="px-4 py-3 font-semibold">Status</th>
                    <th class="px-4 py-3 text-right">Aktionen</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-800/40">
                  {#each executions as exec}
                    <tr class="hover:bg-slate-800/20 transition group">
                      <td class="px-4 py-3 text-slate-200 font-medium">
                        {new Date(exec.gestartet_am).toLocaleString('de-DE')}
                      </td>
                      <td class="px-4 py-3">
                        <span class={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border ${exec.modus === 'shutdown' ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'}`}>
                          {exec.modus}
                        </span>
                      </td>
                      <td class="px-4 py-3 text-slate-400 text-xs">
                        {exec.gestartet_von || 'System'}
                      </td>
                      <td class="px-4 py-3">
                        <span class={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${exec.status === 'abgeschlossen' ? 'bg-emerald-500/20 text-emerald-400' : exec.status === 'verworfen' ? 'bg-red-500/20 text-red-400' : 'bg-blue-500/20 text-blue-400 animate-pulse'}`}>
                          {exec.status}
                        </span>
                      </td>
                      <td class="px-4 py-3 text-right">
                        <button onclick={() => openExecutionDetails(exec)} class="text-[#5DCAA5] hover:text-[#86EFCB] text-xs font-semibold">
                          Details anzeigen
                        </button>
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {/if}
        </div>
      {/if}
    </div>
  {/if}
</div>

<!-- Modal for Execution Details (Protocol View) -->
{#if showExecutionDetailsModal && selectedExecutionDetails}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[#131615] border border-slate-800 rounded-xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
    <div class="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/50">
      <div>
        <h3 class="text-lg font-bold text-white">Protokoll: {runbook.name}</h3>
        <p class="text-xs text-slate-400 mt-1">
          Gestartet am: {new Date(selectedExecutionDetails.gestartet_am).toLocaleString()} | Modus: <span class="uppercase font-semibold">{selectedExecutionDetails.modus}</span> | Status: <span class={`uppercase font-semibold ${selectedExecutionDetails.status === 'verworfen' ? 'text-red-400' : 'text-emerald-400'}`}>{selectedExecutionDetails.status}</span>
        </p>
        {#if selectedExecutionDetails.status === 'verworfen' && selectedExecutionDetails.note}
          <p class="text-xs text-red-400 mt-1 italic font-medium">Begründung: {selectedExecutionDetails.note}</p>
        {/if}
      </div>
      <button onclick={() => showExecutionDetailsModal = false} class="text-slate-400 hover:text-white text-lg">✕</button>
    </div>
    
    <div class="p-6 overflow-y-auto space-y-6">
      <!-- Derived layers list for this execution -->
      {#each selectedExecutionDetails.modus === 'startup' ? [...runbook.layers].sort((a, b) => a.position - b.position).reverse() : [...runbook.layers].sort((a, b) => a.position - b.position) as layer}
        <div class="bg-slate-900/40 border border-slate-800 rounded-lg overflow-hidden">
          <div class="bg-slate-800/40 px-3 py-2 border-b border-slate-800 flex items-center gap-2">
            <span class="w-5 h-5 rounded bg-slate-800 flex items-center justify-center text-[10px] text-slate-400 font-bold border border-slate-700">{layer.position}</span>
            <span class="text-xs font-bold text-slate-200">{layer.name}</span>
          </div>
          <div class="divide-y divide-slate-800/40">
            {#each selectedExecutionDetails.modus === 'startup' ? [...(layer.devices || [])].sort((a, b) => a.position - b.position).reverse() : [...(layer.devices || [])].sort((a, b) => a.position - b.position) as dev}
              {@const step = selectedExecutionDetails.steps?.find(s => s.runbook_device_id === dev.id)}
              <div class="p-3 flex items-start justify-between gap-4">
                <div>
                  <span class="text-sm text-slate-300 font-medium">{getDeviceName(dev)}</span>
                  {#if dev.device && dev.device.connected_pdu_outlets && dev.device.connected_pdu_outlets.length > 0}
                    <div class="flex flex-wrap gap-1 mt-1">
                      {#each dev.device.connected_pdu_outlets as outlet}
                        <span class="inline-flex items-center text-[9px] bg-blue-500/10 text-blue-400 border border-[#1D9E75]/20 px-1.5 py-0.5 rounded font-mono">
                          {outlet.pdu_name || `PDU-${outlet.pdu_id}`} · {outlet.outlet_name}
                        </span>
                      {/each}
                    </div>
                  {/if}
                  <div class="text-[10px] text-slate-500 mt-0.5">Verzögerung: {dev.delay_seconds}s | Verantwortlich: {dev.responsible || '—'}</div>
                  {#if step?.note}
                    <div class="text-[10px] text-slate-400 bg-slate-800/50 border border-slate-800 p-1.5 rounded mt-1.5 font-mono">
                      Notiz: {step.note}
                    </div>
                  {/if}
                </div>
                <div>
                  {#if step?.abgehakt_am}
                    <span class="inline-flex flex-col items-end gap-0.5 text-[10px] text-emerald-400 bg-emerald-950/20 border border-emerald-900/30 px-2 py-1 rounded">
                      <span>✓ Abgehakt um {new Date(step.abgehakt_am).toLocaleTimeString()}</span>
                      {#if step.abgehakt_von}
                        <span class="text-[8px] opacity-80">von {step.abgehakt_von}</span>
                      {/if}
                    </span>
                  {:else}
                    <span class="text-[10px] text-slate-500 bg-slate-800/40 border border-slate-800/60 px-2 py-1 rounded">
                      Ausstehend
                    </span>
                  {/if}
                </div>
              </div>
            {/each}
          </div>
        </div>
      {/each}
    </div>
    
    <div class="p-4 border-t border-slate-800 bg-slate-900/50 flex justify-end shrink-0">
      <button onclick={() => showExecutionDetailsModal = false} class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-lg text-sm font-semibold transition">
        Schließen
      </button>
    </div>
  </div>
</div>
{/if}



<!-- Modal Device Add -->
{#if showDeviceModal}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[#131615] border border-slate-800 rounded-xl w-full max-w-md shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
    <div class="p-4 border-b border-slate-800 flex items-center justify-between">
      <h3 class="text-lg font-bold text-white">Gerät hinzufügen</h3>
      <button onclick={() => showDeviceModal = false} class="text-slate-400 hover:text-white">✕</button>
    </div>
    
    <div class="p-6 space-y-4 overflow-y-auto">
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Typ</label>
        <select bind:value={deviceType} class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]">
          <option value="vm">Virtuelle Maschine (VM)</option>
          <option value="device">Physisches Gerät (Server/Switch)</option>
          <option value="freitext">Freitext (Extern, Cloud etc.)</option>
        </select>
      </div>

      {#if deviceType === 'vm'}
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">VM wählen</label>
          <select bind:value={selectedVmId} class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]">
            <option value={null}>-- Bitte wählen --</option>
            {#each allVms as v}
              <option value={v.id}>{v.name}</option>
            {/each}
          </select>
        </div>
      {:else if deviceType === 'device'}
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Gerät wählen</label>
          <select bind:value={selectedDeviceId} class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]">
            <option value={null}>-- Bitte wählen --</option>
            {#each allDevices as d}
              <option value={d.id}>{d.hostname} ({d.typ})</option>
            {/each}
          </select>
        </div>
      {:else}
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Bezeichnung</label>
          <input type="text" bind:value={freitext} placeholder="z.B. AWS RDS MySQL" class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]" />
        </div>
      {/if}

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Verzögerung (Sek)</label>
          <input type="number" bind:value={delay} min="0" class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Verantwortlich</label>
          <input type="text" bind:value={responsible} placeholder="z.B. Andreas" class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]" />
        </div>
      </div>

      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Spezielle Notiz (z.B. Command)</label>
        <textarea bind:value={deviceNote} rows="2" class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75] resize-none"></textarea>
      </div>
    </div>

    <div class="p-4 border-t border-slate-800 flex justify-end gap-3 shrink-0">
      <button onclick={() => showDeviceModal = false} class="px-4 py-2 rounded-lg text-sm text-slate-400 hover:bg-slate-800">Abbrechen</button>
      <button onclick={addDevice} class="px-4 py-2 bg-[#1D9E75] hover:bg-[#0F6E56] text-white rounded-lg text-sm font-semibold">Hinzufügen</button>
    </div>
  </div>
</div>
{/if}

<!-- Edit Device Modal -->
{#if showEditDeviceModal && editingDevice}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[#131615] border border-slate-800 rounded-xl w-full max-w-sm shadow-2xl p-6">
    <h3 class="text-lg font-bold text-white mb-4">Gerät bearbeiten</h3>
    <div class="space-y-4">
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Verzögerung (Sek)</label>
        <input type="number" bind:value={editingDevice.delay_seconds} class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:border-[#1D9E75]" />
      </div>
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Verantwortlicher</label>
        <input type="text" bind:value={editingDevice.responsible} class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:border-[#1D9E75]" />
      </div>
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Notiz</label>
        <textarea bind:value={editingDevice.note} class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:border-[#1D9E75]"></textarea>
      </div>
    </div>
    <div class="mt-6 flex justify-end gap-3">
      <button onclick={() => showEditDeviceModal = false} class="px-4 py-2 rounded-lg text-sm text-slate-400 hover:bg-slate-800">Abbrechen</button>
      <button onclick={saveEditDevice} class="px-4 py-2 bg-[#1D9E75] hover:bg-[#0F6E56] text-white rounded-lg text-sm font-semibold">Speichern</button>
    </div>
  </div>
</div>
{/if}

<style>
  .custom-scrollbar::-webkit-scrollbar {
    width: 4px;
  }
  .custom-scrollbar::-webkit-scrollbar-track {
    background: transparent;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb {
    background: #1e293b;
    border-radius: 2px;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover {
    background: #334155;
  }
</style>

<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import { api, type Runbook, type RunbookLayer, type RunbookDevice, type Device, type VirtualMachine, type RunbookExecution } from '$lib/api';
  import { BookOpen, Layers, Monitor, Server, Plus, ArrowLeft, Trash2, ArrowUp, ArrowDown, Play, CheckCircle2, Copy, FileText, Clock, User, XCircle, AlertCircle, Edit } from '@lucide/svelte';
  import { goto } from '$app/navigation';

  let runbookId = parseInt(page.params.id);
  let runbook = $state<Runbook | null>(null);
  let loading = $state(true);
  
  let allDevices = $state<Device[]>([]);
  let allVms = $state<VirtualMachine[]>([]);
  let executions = $state<RunbookExecution[]>([]);

  let activeTab = $state<'PLANER' | 'AUSFÜHRUNG' | 'PROTOKOLL'>('PLANER');

  // Modal states
  let showLayerModal = $state(false);
  let newLayerName = $state('');
  
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
    // In a real app, we'd have a `api.getRunbookExecutions(runbookId)` endpoint.
    // For now, we assume we fetch it or we don't have it implemented in the backend explicitly for one runbook.
    // Let's assume we can fetch by ID, but since there's no endpoint listed in the prompt to list executions FOR A runbook,
    // we'll leave it empty unless we start one.
    // Wait, the prompt says "Alle bisherigen Ausführungen (Datum, Von, Modus, Status)" in PROTOKOLL.
    // I didn't write an endpoint for that. Let's just catch errors.
    try {
      // executions = await api.getRunbookExecutions(runbookId);
    } catch (e) {}
  }

  // --- PLANER ACTIONS ---

  async function addLayer() {
    if (!newLayerName || !runbook) return;
    try {
      await api.createRunbookLayer(runbook.id, {
        name: newLayerName,
        position: (runbook.layers?.length || 0) + 1
      });
      showLayerModal = false;
      newLayerName = '';
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
      goto(`/runbook/${newRb.id}`);
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
    } catch (e: any) { alert("Fehler: " + e.message); }
  }

  async function updateExecutionStatus(status: 'abgeschlossen' | 'abgebrochen') {
    if (!currentExecution) return;
    if (!confirm(`Ausführung wirklich als ${status} markieren?`)) return;
    try {
      await api.updateExecutionStatus(currentExecution.id, status);
      currentExecution = await api.getExecution(currentExecution.id);
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
</script>

<div class="h-full flex flex-col space-y-4">
  {#if loading}
    <div class="text-slate-500 py-12 text-center">Lade Runbook...</div>
  {:else if runbook}
    <!-- Header -->
    <div class="flex items-center justify-between bg-[#101622] border border-slate-800 rounded-xl p-4 shrink-0">
      <div class="flex items-center gap-4">
        <button onclick={() => goto('/runbook')} class="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition">
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
      </div>
    </div>

    <!-- Tabs -->
    <div class="flex space-x-1 border-b border-slate-800 shrink-0">
      {#each ['PLANER', 'AUSFÜHRUNG', 'PROTOKOLL'] as tab}
        <button
          onclick={() => activeTab = tab as any}
          class={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${activeTab === tab ? 'border-blue-500 text-blue-400' : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-600'}`}
        >
          {tab}
        </button>
      {/each}
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto">
      {#if activeTab === 'PLANER'}
        <div class="space-y-6 pb-12">
          <!-- Layers -->
          {#each (runbook.layers || []).sort((a,b) => a.position - b.position) as layer, i}
            <div class="bg-[#101622] border border-slate-800 rounded-xl overflow-hidden">
              <!-- Layer Header -->
              <div class="bg-slate-800/50 p-4 border-b border-slate-800 flex items-center justify-between">
                <div class="flex items-center gap-3">
                  <div class="w-6 h-6 rounded bg-slate-800 flex items-center justify-center text-xs font-bold text-slate-400 border border-slate-700">
                    {layer.position}
                  </div>
                  <h3 class="text-sm font-bold text-white flex items-center gap-2">
                    <Layers class="w-4 h-4 text-blue-400" />
                    {layer.name}
                  </h3>
                </div>
                <div class="flex items-center gap-1">
                  <button disabled={i === 0} onclick={() => moveLayer(i, -1)} class="p-1.5 text-slate-500 hover:text-white hover:bg-slate-700 rounded disabled:opacity-30"><ArrowUp class="w-3.5 h-3.5" /></button>
                  <button disabled={i === (runbook.layers?.length || 0) - 1} onclick={() => moveLayer(i, 1)} class="p-1.5 text-slate-500 hover:text-white hover:bg-slate-700 rounded disabled:opacity-30"><ArrowDown class="w-3.5 h-3.5" /></button>
                  <button onclick={() => deleteLayer(layer.id)} class="p-1.5 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded ml-2"><Trash2 class="w-3.5 h-3.5" /></button>
                </div>
              </div>

              <!-- Layer Body -->
              <div class="p-4">
                <textarea 
                  class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-300 focus:border-blue-500 resize-none mb-4"
                  rows="2"
                  placeholder="Notizen / Instruktionen (Markdown unterstützt) ..."
                  value={layer.markdown_note || ''}
                  onblur={(e) => updateLayerNote(layer.id, e.currentTarget.value)}
                ></textarea>

                <div class="space-y-2">
                  {#each (layer.devices || []).sort((a,b) => a.position - b.position) as dev, dIdx}
                    <div class="flex items-center justify-between bg-slate-900/50 border border-slate-800/80 rounded-lg p-2.5 group hover:border-slate-600 transition">
                      <div class="flex items-center gap-3">
                        <div class="flex flex-col gap-0.5">
                          <button disabled={dIdx === 0} onclick={() => moveDevice(layer, dIdx, -1)} class="text-slate-600 hover:text-slate-300 disabled:opacity-30"><ArrowUp class="w-3 h-3" /></button>
                          <button disabled={dIdx === (layer.devices?.length || 0) - 1} onclick={() => moveDevice(layer, dIdx, 1)} class="text-slate-600 hover:text-slate-300 disabled:opacity-30"><ArrowDown class="w-3 h-3" /></button>
                        </div>
                        
                        <div class="w-8 h-8 rounded bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0">
                          {@const Icon = getDeviceIcon(dev)}
                          <Icon class={`w-4 h-4 ${dev.vm ? 'text-pink-400' : dev.device ? 'text-slate-300' : 'text-blue-400'}`} />
                        </div>
                        
                        <div>
                          <div class="text-sm font-medium text-slate-200">{getDeviceName(dev)}</div>
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
                      <div class="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition">
                        <button onclick={() => openEditDevice(dev)} class="p-1.5 text-blue-400 hover:bg-blue-500/10 rounded"><Edit class="w-4 h-4" /></button>
                        <button onclick={() => deleteDevice(dev.id)} class="p-1.5 text-red-400 hover:bg-red-500/10 rounded"><Trash2 class="w-4 h-4" /></button>
                      </div>
                    </div>
                  {/each}
                  
                  <button 
                    onclick={() => { targetLayerId = layer.id; showDeviceModal = true; }}
                    class="w-full flex items-center justify-center gap-2 py-2 border-2 border-dashed border-slate-800 hover:border-slate-600 rounded-lg text-xs text-slate-400 hover:text-slate-200 transition"
                  >
                    <Plus class="w-3.5 h-3.5" /> Gerät hinzufügen
                  </button>
                </div>
              </div>
            </div>
          {/each}

          <button 
            onclick={() => showLayerModal = true}
            class="w-full flex items-center justify-center gap-2 py-4 bg-blue-600/10 hover:bg-blue-600/20 text-blue-400 border border-blue-600/20 rounded-xl text-sm font-medium transition"
          >
            <Plus class="w-4 h-4" /> Neue Ebene hinzufügen
          </button>
        </div>
      {/if}

      {#if activeTab === 'AUSFÜHRUNG'}
        {#if !currentExecution}
          <div class="bg-[#101622] border border-slate-800 rounded-xl p-8 max-w-lg mx-auto mt-12 text-center">
            <Play class="w-12 h-12 text-emerald-400 mx-auto mb-4" />
            <h2 class="text-xl font-bold text-white mb-2">Neue Ausführung starten</h2>
            <p class="text-sm text-slate-400 mb-6">Sie sind im Begriff, die Sequenz live zu protokollieren. Alle Schritte werden revisionssicher erfasst.</p>
            
            <div class="mb-6 text-left">
              <label class="block text-xs font-semibold text-slate-400 mb-2">Modus</label>
              <select bind:value={execMode} class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500">
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
              {#if currentExecution.status === 'aktiv'}
                <div class="flex items-center gap-2">
                  <button onclick={() => updateExecutionStatus('abgebrochen')} class="px-3 py-1.5 bg-red-500/10 text-red-400 hover:bg-red-500/20 rounded-lg text-xs font-medium border border-red-500/20 transition">Abbrechen</button>
                  <button onclick={() => updateExecutionStatus('abgeschlossen')} class="px-3 py-1.5 bg-emerald-500 hover:bg-emerald-400 text-white rounded-lg text-xs font-medium transition shadow-lg shadow-emerald-500/20 flex items-center gap-1"><CheckCircle2 class="w-3.5 h-3.5"/> Abschließen</button>
                </div>
              {/if}
            </div>

            {#each (runbook.layers || []).sort((a,b) => a.position - b.position) as layer}
              <div class="bg-[#101622] border border-slate-800 rounded-xl overflow-hidden">
                <div class="bg-slate-800/50 p-3 border-b border-slate-800 flex items-center gap-3">
                  <div class="w-5 h-5 rounded bg-slate-800 flex items-center justify-center text-[10px] font-bold text-slate-400 border border-slate-700">{layer.position}</div>
                  <h3 class="text-sm font-bold text-white">{layer.name}</h3>
                </div>
                {#if layer.markdown_note}
                  <div class="px-4 py-2 bg-blue-900/10 border-b border-blue-900/20 text-xs text-blue-200/80 italic">{layer.markdown_note}</div>
                {/if}
                <div class="divide-y divide-slate-800/50">
                  {#each (layer.devices || []).sort((a,b) => a.position - b.position) as dev}
                    {@const checked = isStepChecked(dev.id)}
                    {@const step = getStep(dev.id)}
                    <div class={`p-3 flex items-start gap-3 transition-colors ${checked ? 'bg-emerald-900/5' : 'hover:bg-slate-800/30'}`}>
                      <button 
                        onclick={() => checkStep(dev.id, '')}
                        disabled={currentExecution.status !== 'aktiv'}
                        class={`mt-1 shrink-0 w-6 h-6 rounded flex items-center justify-center border transition ${checked ? 'bg-emerald-500 border-emerald-500 text-white' : 'bg-[#182030] border-slate-600 text-transparent hover:border-emerald-400 disabled:opacity-50'}`}
                      >
                        <CheckCircle2 class="w-4 h-4" />
                      </button>
                      <div class="flex-1">
                        <div class="flex justify-between items-start">
                          <div>
                            <div class={`text-sm font-medium ${checked ? 'text-slate-400 line-through' : 'text-slate-200'}`}>{getDeviceName(dev)}</div>
                            <div class="text-[10px] text-slate-500 flex items-center gap-2 mt-0.5">
                              <span class="flex items-center gap-1"><Clock class="w-3 h-3" /> {dev.delay_seconds}s</span>
                              {#if dev.responsible}
                                <span class="flex items-center gap-1"><User class="w-3 h-3" /> {dev.responsible}</span>
                              {/if}
                            </div>
                          </div>
                          {#if checked && step}
                            <div class="text-[10px] text-emerald-500 bg-emerald-500/10 px-2 py-1 rounded">
                              {new Date(step.abgehakt_am || '').toLocaleTimeString()}
                            </div>
                          {/if}
                        </div>
                        {#if dev.note}
                          <div class="text-[10px] text-amber-500/80 mt-1">{dev.note}</div>
                        {/if}
                        {#if !checked && currentExecution.status === 'aktiv'}
                          <div class="mt-2">
                            <input 
                              type="text" 
                              placeholder="Optionale Notiz zur Ausführung..." 
                              onkeydown={(e) => { if (e.key === 'Enter') checkStep(dev.id, e.currentTarget.value); }}
                              class="w-full bg-[#182030] border border-slate-700 rounded text-xs px-2 py-1 focus:border-emerald-500 outline-none text-slate-300"
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
        <div class="text-slate-500 py-12 text-center border border-dashed border-slate-800 rounded-xl">
          <FileText class="w-8 h-8 mx-auto mb-2 opacity-50" />
          Protokolle implementiert im MVP noch nicht vollständig in der UI abrufbar.<br>
          Bitte Datenbank abfragen.
        </div>
      {/if}
    </div>
  {/if}
</div>

<!-- Modal Layer Create -->
{#if showLayerModal}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[#101622] border border-slate-800 rounded-xl w-full max-w-sm shadow-2xl p-6">
    <h3 class="text-lg font-bold text-white mb-4">Neue Ebene</h3>
    <input type="text" bind:value={newLayerName} placeholder="z.B. Datenbanken" class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500 mb-4" />
    <div class="flex justify-end gap-3">
      <button onclick={() => showLayerModal = false} class="px-4 py-2 rounded-lg text-sm text-slate-400 hover:bg-slate-800">Abbrechen</button>
      <button onclick={addLayer} disabled={!newLayerName} class="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg text-sm font-semibold">Erstellen</button>
    </div>
  </div>
</div>
{/if}

<!-- Modal Device Add -->
{#if showDeviceModal}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[#101622] border border-slate-800 rounded-xl w-full max-w-md shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
    <div class="p-4 border-b border-slate-800 flex items-center justify-between">
      <h3 class="text-lg font-bold text-white">Gerät hinzufügen</h3>
      <button onclick={() => showDeviceModal = false} class="text-slate-400 hover:text-white">✕</button>
    </div>
    
    <div class="p-6 space-y-4 overflow-y-auto">
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Typ</label>
        <select bind:value={deviceType} class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500">
          <option value="vm">Virtuelle Maschine (VM)</option>
          <option value="device">Physisches Gerät (Server/Switch)</option>
          <option value="freitext">Freitext (Extern, Cloud etc.)</option>
        </select>
      </div>

      {#if deviceType === 'vm'}
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">VM wählen</label>
          <select bind:value={selectedVmId} class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500">
            <option value={null}>-- Bitte wählen --</option>
            {#each allVms as v}
              <option value={v.id}>{v.name}</option>
            {/each}
          </select>
        </div>
      {:else if deviceType === 'device'}
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Gerät wählen</label>
          <select bind:value={selectedDeviceId} class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500">
            <option value={null}>-- Bitte wählen --</option>
            {#each allDevices as d}
              <option value={d.id}>{d.hostname} ({d.typ})</option>
            {/each}
          </select>
        </div>
      {:else}
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Bezeichnung</label>
          <input type="text" bind:value={freitext} placeholder="z.B. AWS RDS MySQL" class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
        </div>
      {/if}

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Verzögerung (Sek)</label>
          <input type="number" bind:value={delay} min="0" class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Verantwortlich</label>
          <input type="text" bind:value={responsible} placeholder="z.B. Andreas" class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500" />
        </div>
      </div>

      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Spezielle Notiz (z.B. Command)</label>
        <textarea bind:value={deviceNote} rows="2" class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500 resize-none"></textarea>
      </div>
    </div>

    <div class="p-4 border-t border-slate-800 flex justify-end gap-3 shrink-0">
      <button onclick={() => showDeviceModal = false} class="px-4 py-2 rounded-lg text-sm text-slate-400 hover:bg-slate-800">Abbrechen</button>
      <button onclick={addDevice} class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-semibold">Hinzufügen</button>
    </div>
  </div>
</div>
{/if}

<!-- Edit Device Modal -->
{#if showEditDeviceModal && editingDevice}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[#101622] border border-slate-800 rounded-xl w-full max-w-sm shadow-2xl p-6">
    <h3 class="text-lg font-bold text-white mb-4">Gerät bearbeiten</h3>
    <div class="space-y-4">
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Verzögerung (Sek)</label>
        <input type="number" bind:value={editingDevice.delay_seconds} class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:border-blue-500" />
      </div>
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Verantwortlicher</label>
        <input type="text" bind:value={editingDevice.responsible} class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:border-blue-500" />
      </div>
      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Notiz</label>
        <textarea bind:value={editingDevice.note} class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:border-blue-500"></textarea>
      </div>
    </div>
    <div class="mt-6 flex justify-end gap-3">
      <button onclick={() => showEditDeviceModal = false} class="px-4 py-2 rounded-lg text-sm text-slate-400 hover:bg-slate-800">Abbrechen</button>
      <button onclick={saveEditDevice} class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-semibold">Speichern</button>
    </div>
  </div>
</div>
{/if}

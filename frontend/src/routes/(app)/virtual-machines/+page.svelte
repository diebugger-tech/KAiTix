<script lang="ts">
  import { onMount } from 'svelte';
  import { api, type VirtualMachine, type Device } from '$lib/api';
  import { Monitor, Plus, Server, CheckCircle2, AlertCircle } from '@lucide/svelte';

  let vms = $state<VirtualMachine[]>([]);
  let devices = $state<Device[]>([]);
  let loading = $state(true);
  
  let showModal = $state(false);
  let editMode = $state(false);
  let currentVm = $state<Partial<VirtualMachine>>({ shutdown_priority: 5 });
  let activeTab = $state<'table' | 'graph'>('table');
  let hoveredVmId = $state<number | null>(null);

  onMount(async () => {
    try {
      loading = true;
      const [v, d] = await Promise.all([
        api.getVirtualMachines(),
        api.getDevices()
      ]);
      vms = v;
      devices = d.filter(dev => ['server', 'sonstige'].includes(dev.typ));
    } catch (e) {
      console.error(e);
    } finally {
      loading = false;
    }
  });

  function getHostName(id?: number | null) {
    if (!id) return '—';
    const dev = devices.find(d => d.id === id);
    return dev ? dev.hostname : 'Unbekannt';
  }

  function getDependencyName(id?: number | null) {
    if (!id) return '—';
    const vm = vms.find(v => v.id === id);
    return vm ? vm.name : 'Unbekannt';
  }

  function openCreate() {
    editMode = false;
    currentVm = { shutdown_priority: 5, hypervisor_typ: 'vmware' };
    showModal = true;
  }

  function openEdit(vm: VirtualMachine) {
    editMode = true;
    currentVm = { ...vm };
    showModal = true;
  }

  async function save() {
    try {
      if (editMode && currentVm.id) {
        await api.updateVirtualMachine(currentVm.id, currentVm);
      } else {
        await api.createVirtualMachine(currentVm);
      }
      showModal = false;
      vms = await api.getVirtualMachines();
    } catch (e: any) {
      alert("Fehler beim Speichern: " + e.message);
    }
  }

  async function deleteVm(id: number) {
    if (confirm("VM wirklich löschen? Dies entfernt sie auch aus allen Runbooks.")) {
      try {
        await api.deleteVirtualMachine(id);
        vms = await api.getVirtualMachines();
      } catch (e: any) {
        alert("Fehler beim Löschen: " + e.message);
      }
    }
  }

  // Finds all ancestor VM IDs that this VM depends on (directly or transitively)
  function getAncestors(vmId: number): Set<number> {
    const ancestors = new Set<number>();
    let queue = [vmId];
    let visited = new Set<number>();
    while (queue.length > 0) {
      const current = queue.shift()!;
      if (visited.has(current)) continue;
      visited.add(current);
      
      const vm = vms.find(v => v.id === current);
      if (vm && vm.depends_on_vm_id) {
        ancestors.add(vm.depends_on_vm_id);
        queue.push(vm.depends_on_vm_id);
      }
    }
    return ancestors;
  }

  // Finds all descendant VM IDs that depend on this VM (directly or transitively)
  function getDescendants(vmId: number): Set<number> {
    const descendants = new Set<number>();
    let queue = [vmId];
    let visited = new Set<number>();
    while (queue.length > 0) {
      const current = queue.shift()!;
      if (visited.has(current)) continue;
      visited.add(current);
      
      // Find all VMs that depend on 'current'
      const children = vms.filter(v => v.depends_on_vm_id === current);
      for (const child of children) {
        descendants.add(child.id);
        queue.push(child.id);
      }
    }
    return descendants;
  }

  const vmLevels = $derived.by(() => {
    let levels = new Map<number, number>();
    vms.forEach(vm => levels.set(vm.id, 0));
    
    for (let i = 0; i < vms.length; i++) {
      let changed = false;
      for (const vm of vms) {
        if (vm.depends_on_vm_id) {
          const depLevel = levels.get(vm.depends_on_vm_id) ?? 0;
          const curLevel = levels.get(vm.id) ?? 0;
          if (curLevel <= depLevel) {
            levels.set(vm.id, depLevel + 1);
            changed = true;
          }
        }
      }
      if (!changed) break;
    }
    return levels;
  });

  const graphData = $derived.by(() => {
    const levels = vmLevels;
    const vmsByLevel = new Map<number, VirtualMachine[]>();
    let maxLevel = 0;
    
    for (const vm of vms) {
      const lvl = levels.get(vm.id) ?? 0;
      if (lvl > maxLevel) maxLevel = lvl;
      if (!vmsByLevel.has(lvl)) vmsByLevel.set(lvl, []);
      vmsByLevel.get(lvl)!.push(vm);
    }
    
    const columnWidth = 280;
    const rowHeight = 110;
    const verticalPadding = 50;
    const horizontalPadding = 50;
    
    let maxRows = 0;
    for (let l = 0; l <= maxLevel; l++) {
      const count = vmsByLevel.get(l)?.length ?? 0;
      if (count > maxRows) maxRows = count;
    }
    
    const canvasHeight = Math.max(500, maxRows * rowHeight + 2 * verticalPadding);
    const canvasWidth = Math.max(900, (maxLevel + 1) * columnWidth + 2 * horizontalPadding);
    
    const coords = new Map<number, {x: number, y: number}>();
    for (let l = 0; l <= maxLevel; l++) {
      const list = vmsByLevel.get(l) ?? [];
      const sortedList = [...list].sort((a, b) => a.name.localeCompare(b.name));
      const colHeight = sortedList.length * rowHeight;
      const startY = (canvasHeight - colHeight) / 2 + rowHeight / 2;
      sortedList.forEach((vm, index) => {
        coords.set(vm.id, {
          x: horizontalPadding + l * columnWidth + columnWidth / 2,
          y: startY + index * rowHeight
        });
      });
    }
    
    return {
      coords,
      canvasWidth,
      canvasHeight,
      maxLevel
    };
  });

  const activeAncestors = $derived(hoveredVmId !== null ? getAncestors(hoveredVmId) : new Set<number>());
  const activeDescendants = $derived(hoveredVmId !== null ? getDescendants(hoveredVmId) : new Set<number>());
</script>

<div class="h-full flex flex-col space-y-6">
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-white tracking-tight flex items-center gap-3">
        <Monitor class="w-6 h-6 text-pink-400" />
        Virtuelle Maschinen
      </h1>
      <p class="text-slate-400 text-sm mt-1">
        Dokumentation der VM-Landschaft und Abhängigkeiten für geordnete Shutdowns.
      </p>
    </div>
    <button 
      onclick={openCreate}
      class="flex items-center space-x-2 bg-pink-500/20 text-pink-400 border border-pink-500/30 hover:bg-pink-500/30 px-4 py-2 rounded-lg text-sm font-medium transition"
    >
      <Plus class="w-4 h-4" />
      <span>VM anlegen</span>
    </button>
  </div>

  <div class="bg-[#131615] border border-slate-800 rounded-xl flex-1 overflow-hidden flex flex-col shadow-2xl">
    <!-- Tabs Header -->
    <div class="flex border-b border-slate-800 bg-slate-900/40 px-4 py-2 justify-between items-center shrink-0 select-none">
      <div class="flex space-x-2">
        <button 
          onclick={() => activeTab = 'table'} 
          class={`px-3 py-1.5 text-xs font-semibold rounded-lg transition ${activeTab === 'table' ? 'bg-slate-800 text-white border border-slate-700' : 'text-slate-400 hover:text-slate-200'}`}
        >
          Tabelle
        </button>
        <button 
          onclick={() => activeTab = 'graph'} 
          class={`px-3 py-1.5 text-xs font-semibold rounded-lg transition ${activeTab === 'graph' ? 'bg-slate-800 text-white border border-slate-700' : 'text-slate-400 hover:text-slate-200'}`}
        >
          Abhängigkeitsgraph
        </button>
      </div>
      
      {#if activeTab === 'graph'}
        <div class="text-[10px] text-slate-400 italic">
          Tipp: Bewege den Mauszeiger über eine VM, um Abhängigkeitsketten anzuzeigen.
        </div>
      {/if}
    </div>

    {#if activeTab === 'table'}
      <div class="overflow-x-auto flex-1">
        <table class="w-full text-left text-sm text-slate-300">
          <thead class="text-xs uppercase bg-slate-800/50 text-slate-400 sticky top-0 z-10">
            <tr>
              <th class="px-4 py-3 font-semibold">Name</th>
              <th class="px-4 py-3 font-semibold">Hypervisor</th>
              <th class="px-4 py-3 font-semibold">Läuft auf (Host)</th>
              <th class="px-4 py-3 font-semibold">Dienst</th>
              <th class="px-4 py-3 font-semibold">IP-Adresse</th>
              <th class="px-4 py-3 font-semibold text-center">Prio</th>
              <th class="px-4 py-3 font-semibold">Verantwortlich</th>
              <th class="px-4 py-3 text-right">Aktionen</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800/50">
            {#if loading}
              <tr><td colspan="8" class="text-center py-8 text-slate-500">Lade VMs...</td></tr>
            {:else if vms.length === 0}
              <tr><td colspan="8" class="text-center py-8 text-slate-500">Keine VMs dokumentiert.</td></tr>
            {:else}
              {#each vms as vm}
                <tr class="hover:bg-slate-800/30 transition group">
                  <td class="px-4 py-3 font-medium text-slate-200">{vm.name}</td>
                  <td class="px-4 py-3 text-xs">
                    <span class="bg-slate-800 border border-slate-700 px-2 py-0.5 rounded text-slate-300">
                      {vm.hypervisor_typ || '—'}
                    </span>
                  </td>
                  <td class="px-4 py-3 flex items-center gap-2">
                    <Server class="w-3.5 h-3.5 text-slate-500" />
                    <span class="font-mono text-xs">{getHostName(vm.host_device_id)}</span>
                  </td>
                  <td class="px-4 py-3 text-slate-400 max-w-[200px] truncate" title={vm.dienst || ''}>{vm.dienst || '—'}</td>
                  <td class="px-4 py-3 font-mono text-xs text-slate-400">{vm.ip_adresse || '—'}</td>
                  <td class="px-4 py-3 text-center">
                    <span class={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${vm.shutdown_priority === 1 ? 'bg-red-500/20 text-red-400' : vm.shutdown_priority === 2 ? 'bg-orange-500/20 text-orange-400' : 'bg-slate-800 text-slate-400'}`}>
                      {vm.shutdown_priority}
                    </span>
                  </td>
                  <td class="px-4 py-3 text-slate-400 text-xs">{vm.responsible || '—'}</td>
                  <td class="px-4 py-3 text-right space-x-2">
                    <button onclick={() => openEdit(vm)} class="text-[#5DCAA5] hover:text-[#86EFCB] text-xs font-medium">Bearbeiten</button>
                    <button onclick={() => deleteVm(vm.id)} class="text-red-400 hover:text-red-300 text-xs font-medium">Löschen</button>
                  </td>
                </tr>
              {/each}
            {/if}
          </tbody>
        </table>
      </div>
    {:else}
      <div class="flex-1 overflow-auto bg-[#0b0f19] relative min-h-[500px]">
        {#if loading}
          <div class="absolute inset-0 flex items-center justify-center text-slate-500">Lade Graph...</div>
        {:else if vms.length === 0}
          <div class="absolute inset-0 flex items-center justify-center text-slate-500">Keine VMs für Graph vorhanden.</div>
        {:else}
          <div style="width: {graphData.canvasWidth}px; height: {graphData.canvasHeight}px; position: relative;">
            
            <!-- SVG Canvas for connections -->
            <svg class="absolute inset-0 pointer-events-none" width={graphData.canvasWidth} height={graphData.canvasHeight}>
              <defs>
                <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#334155" />
                </marker>
                <marker id="arrow-parent" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#10b981" />
                </marker>
                <marker id="arrow-child" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#ec4899" />
                </marker>
              </defs>
              
              <!-- Connections -->
              {#each vms as vm}
                {#if vm.depends_on_vm_id && graphData.coords.has(vm.id) && graphData.coords.has(vm.depends_on_vm_id)}
                  {@const fromCoord = graphData.coords.get(vm.depends_on_vm_id)!}
                  {@const toCoord = graphData.coords.get(vm.id)!}
                  {@const x1 = fromCoord.x + 110}
                  {@const y1 = fromCoord.y}
                  {@const x2 = toCoord.x - 110}
                  {@const y2 = toCoord.y}
                  
                  {@const isParentChain = hoveredVmId !== null && (hoveredVmId === vm.id || (activeAncestors.has(vm.id) && (activeAncestors.has(vm.depends_on_vm_id) || vm.depends_on_vm_id === hoveredVmId)))}
                  {@const isChildChain = hoveredVmId !== null && (hoveredVmId === vm.depends_on_vm_id || (activeDescendants.has(vm.depends_on_vm_id) && (activeDescendants.has(vm.id) || vm.id === hoveredVmId)))}
                  
                  <path
                    d="M {x1} {y1} C {x1 + 80} {y1}, {x2 - 85} {y2}, {x2} {y2}"
                    fill="none"
                    stroke={isParentChain ? '#10b981' : isChildChain ? '#ec4899' : '#1e293b'}
                    stroke-width={isParentChain || isChildChain ? 2.5 : 1.5}
                    stroke-opacity={hoveredVmId === null ? 0.6 : (isParentChain || isChildChain ? 1.0 : 0.15)}
                    marker-end={isParentChain ? 'url(#arrow-parent)' : isChildChain ? 'url(#arrow-child)' : 'url(#arrow)'}
                  />
                {/if}
              {/each}
            </svg>
            
            <!-- VM Cards -->
            {#each vms as vm}
              {#if graphData.coords.has(vm.id)}
                {@const coord = graphData.coords.get(vm.id)!}
                {@const isHovered = hoveredVmId === vm.id}
                {@const isParent = hoveredVmId !== null && activeAncestors.has(vm.id)}
                {@const isChild = hoveredVmId !== null && activeDescendants.has(vm.id)}
                {@const isUnrelated = hoveredVmId !== null && !isHovered && !isParent && !isChild}
                
                <div
                  class="absolute flex flex-col justify-between p-3 rounded-lg border text-left cursor-pointer transition-all duration-200 select-none bg-[#111827] group shadow-md"
                  style="width: 220px; height: 75px; left: {coord.x - 110}px; top: {coord.y - 37}px;
                         border-color: {isHovered ? '#3b82f6' : isParent ? '#10b981' : isChild ? '#ec4899' : '#1f2937'};
                         box-shadow: {isHovered ? '0 0 10px rgba(59, 130, 246, 0.4)' : isParent ? '0 0 10px rgba(16, 185, 129, 0.4)' : isChild ? '0 0 10px rgba(236, 72, 153, 0.4)' : 'none'};
                         opacity: {isUnrelated ? 0.35 : 1};"
                  onmouseenter={() => hoveredVmId = vm.id}
                  onmouseleave={() => hoveredVmId = null}
                  onclick={() => openEdit(vm)}
                >
                  <div class="flex items-start justify-between gap-1.5 min-w-0">
                    <div class="flex items-center gap-1.5 min-w-0">
                      <Monitor class="w-4 h-4 text-pink-400 shrink-0" />
                      <div class="truncate text-xs font-semibold text-slate-100" title={vm.name}>{vm.name}</div>
                    </div>
                    <div class="flex items-center gap-1 shrink-0">
                      <span class={`inline-flex items-center justify-center w-4 h-4 rounded-full text-[9px] font-bold ${vm.shutdown_priority === 1 ? 'bg-red-500/20 text-red-400' : vm.shutdown_priority === 2 ? 'bg-orange-500/20 text-orange-400' : 'bg-slate-800 text-slate-400'}`} title="Shutdown Priorität">
                        {vm.shutdown_priority}
                      </span>
                    </div>
                  </div>
                  
                  <div class="flex items-end justify-between gap-1.5 min-w-0">
                    <div class="truncate text-[10px] text-slate-400">
                      <span class="text-slate-500">Host:</span> {getHostName(vm.host_device_id)}
                    </div>
                    <div class="font-mono text-[9px] text-slate-500 shrink-0">
                      {vm.ip_adresse || 'Keine IP'}
                    </div>
                  </div>
                  
                  <!-- Quick actions on hover -->
                  <div class="absolute -top-2 -right-2 hidden group-hover:flex items-center gap-1 bg-slate-900 border border-slate-700 rounded-md p-1 shadow-lg z-20">
                    <button
                      onclick={(e: Event) => { e.stopPropagation(); openEdit(vm); }}
                      class="p-0.5 text-[#5DCAA5] hover:text-[#86EFCB] hover:bg-slate-800 rounded"
                      title="Bearbeiten"
                    >
                      <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 20h9"></path>
                        <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"></path>
                      </svg>
                    </button>
                    <button
                      onclick={(e: Event) => { e.stopPropagation(); deleteVm(vm.id); }}
                      class="p-0.5 text-red-400 hover:text-red-300 hover:bg-slate-800 rounded"
                      title="Löschen"
                    >
                      <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M3 6h18"></path>
                        <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path>
                        <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path>
                      </svg>
                    </button>
                  </div>
                </div>
              {/if}
            {/each}
          </div>
        {/if}
      </div>
    {/if}
  </div>
</div>

{#if showModal}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[#131615] border border-slate-800 rounded-xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
    <div class="p-4 border-b border-slate-800 flex items-center justify-between">
      <h3 class="text-lg font-bold text-white">{editMode ? 'VM bearbeiten' : 'Neue VM anlegen'}</h3>
      <button onclick={() => showModal = false} class="text-slate-400 hover:text-white">✕</button>
    </div>
    
    <div class="p-6 overflow-y-auto space-y-4">
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Name <span class="text-red-400">*</span></label>
          <input type="text" bind:value={currentVm.name} class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-pink-500" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Hypervisor-Typ</label>
          <select bind:value={currentVm.hypervisor_typ} class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-pink-500">
            <option value="vmware">VMware ESXi</option>
            <option value="hyper-v">Microsoft Hyper-V</option>
            <option value="kvm">KVM (Linux)</option>
            <option value="xcpng">XCP-ng</option>
            <option value="sonstige">Sonstige</option>
          </select>
        </div>
      </div>

      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Läuft auf (Host-System) <span class="text-red-400">*</span></label>
        <select bind:value={currentVm.host_device_id} class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-pink-500">
          <option value={null}>-- Physischen Server wählen --</option>
          {#each devices as dev}
            <option value={dev.id}>{dev.hostname} ({dev.typ})</option>
          {/each}
        </select>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Betriebssystem</label>
          <input type="text" bind:value={currentVm.betriebssystem} placeholder="z.B. Ubuntu 24.04" class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-pink-500" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">IP-Adresse</label>
          <input type="text" bind:value={currentVm.ip_adresse} placeholder="192.168.x.x" class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-pink-500" />
        </div>
      </div>

      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Dienst / Anwendung</label>
        <input type="text" bind:value={currentVm.dienst} placeholder="z.B. Primary Database Server" class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-pink-500" />
      </div>

      <div class="grid grid-cols-3 gap-4">
        <div class="col-span-2">
          <label class="block text-xs font-semibold text-slate-400 mb-1">Abhängig von (VM)</label>
          <select bind:value={currentVm.depends_on_vm_id} class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-pink-500">
            <option value={null}>-- Keine Abhängigkeit --</option>
            {#each vms.filter(v => v.id !== currentVm.id) as v}
              <option value={v.id}>{v.name}</option>
            {/each}
          </select>
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Shutdown-Prio</label>
          <input type="number" bind:value={currentVm.shutdown_priority} min="1" max="99" class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-pink-500" />
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div class="col-span-2">
          <label class="block text-xs font-semibold text-slate-400 mb-1">Verantwortlicher (Team/Person)</label>
          <input type="text" bind:value={currentVm.responsible} placeholder="z.B. Andreas / DBA Team" class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-pink-500" />
        </div>
      </div>

      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Bemerkung</label>
        <textarea bind:value={currentVm.bemerkung} rows="2" class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-pink-500 resize-none"></textarea>
      </div>
    </div>

    <div class="p-4 border-t border-slate-800 bg-slate-900/50 flex justify-end gap-3 shrink-0">
      <button onclick={() => showModal = false} class="px-4 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition">Abbrechen</button>
      <button 
        onclick={save}
        disabled={!currentVm.name || !currentVm.host_device_id}
        class="px-4 py-2 bg-pink-600 hover:bg-pink-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm font-semibold transition flex items-center gap-2"
      >
        <CheckCircle2 class="w-4 h-4" />
        Speichern
      </button>
    </div>
  </div>
</div>
{/if}

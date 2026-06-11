<script lang="ts">
  import { onMount } from 'svelte';
  import { api, type VirtualMachine, type Device } from '$lib/api';
  import { Monitor, Plus, Server, CheckCircle2, AlertCircle, ArrowUp, ArrowDown, GripVertical } from '@lucide/svelte';

  let vms = $state<VirtualMachine[]>([]);
  let devices = $state<Device[]>([]);
  let loading = $state(true);
  
  let panelOpen = $state(false);
  let editMode = $state(false);
  let currentVm = $state<Partial<VirtualMachine>>({ shutdown_priority: 5 });
  let activeTab = $state<'table' | 'graph'>('table');
  let hoveredVmId = $state<number | null>(null);

  let sortColumn = $state<'name' | 'hypervisor_typ' | 'host' | 'dienst' | 'ip_adresse' | 'priority' | 'responsible'>('priority');
  let sortDirection = $state<'asc' | 'desc'>('asc');

  let draggedVmId = $state<number | null>(null);
  let dragOverVmId = $state<number | null>(null);

  const sortedVms = $derived([...vms].sort((a, b) => {
    let cmp = 0;
    if (sortColumn === 'priority') cmp = (a.shutdown_priority || 0) - (b.shutdown_priority || 0);
    else if (sortColumn === 'name') cmp = (a.name || '').localeCompare(b.name || '');
    else if (sortColumn === 'hypervisor_typ') cmp = (a.hypervisor_typ || '').localeCompare(b.hypervisor_typ || '');
    else if (sortColumn === 'host') cmp = getHostName(a.host_device_id).localeCompare(getHostName(b.host_device_id));
    else if (sortColumn === 'dienst') cmp = (a.dienst || '').localeCompare(b.dienst || '');
    else if (sortColumn === 'ip_adresse') cmp = (a.ip_adresse || '').localeCompare(b.ip_adresse || '');
    else if (sortColumn === 'responsible') cmp = (a.responsible || '').localeCompare(b.responsible || '');
    return sortDirection === 'asc' ? cmp : -cmp;
  }));

  function handleSort(col: typeof sortColumn) {
    if (sortColumn === col) {
      sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      sortColumn = col;
      sortDirection = 'asc';
    }
  }

  let dragOverHostId = $state<number | null>(null);

  async function handleHostDrop(e: DragEvent, targetHostId: number) {
    e.preventDefault();
    if (!draggedVmId) {
      dragOverHostId = null;
      return;
    }
    
    const vm = vms.find(v => v.id === draggedVmId);
    if (vm && vm.host_device_id !== targetHostId) {
      try {
        const updated = { ...vm, host_device_id: targetHostId };
        await api.updateVirtualMachine(vm.id, updated);
        vms = await api.getVirtualMachines();
      } catch (err: any) {
        alert("Fehler beim Zuweisen des Hosts: " + err.message);
      }
    }
    
    draggedVmId = null;
    dragOverHostId = null;
  }

  let dragOverDependencyVmId = $state<number | null>(null);

  async function handleDependencyDrop(e: DragEvent, targetVmId: number) {
    e.preventDefault();
    if (!draggedVmId || draggedVmId === targetVmId) {
      dragOverDependencyVmId = null;
      return;
    }
    
    const vm = vms.find(v => v.id === draggedVmId);
    if (vm && vm.depends_on_vm_id !== targetVmId) {
      try {
        const updated = { ...vm, depends_on_vm_id: targetVmId };
        await api.updateVirtualMachine(vm.id, updated);
        vms = await api.getVirtualMachines();
      } catch (err: any) {
        if (err.message?.includes('Zirkuläre Abhängigkeit')) {
          alert("Fehler: " + err.message);
        } else {
          alert("Fehler beim Setzen der Abhängigkeit: " + err.message);
        }
      }
    }
    
    draggedVmId = null;
    dragOverDependencyVmId = null;
  }

  async function handleDrop(e: DragEvent, targetVmId: number) {
    e.preventDefault();
    if (!draggedVmId || draggedVmId === targetVmId) {
      dragOverVmId = null;
      return;
    }
    
    // Wir sortieren für das Reordering streng nach der alten Priorität
    const sortedByPrio = [...vms].sort((a, b) => (a.shutdown_priority || 0) - (b.shutdown_priority || 0));
    
    const draggedIdx = sortedByPrio.findIndex(v => v.id === draggedVmId);
    const targetIdx = sortedByPrio.findIndex(v => v.id === targetVmId);
    
    if (draggedIdx === -1 || targetIdx === -1) return;
    
    const [removed] = sortedByPrio.splice(draggedIdx, 1);
    sortedByPrio.splice(targetIdx, 0, removed);
    
    const reorders = sortedByPrio.map((vm, i) => ({
      id: vm.id,
      shutdown_priority: i + 1
    }));

    try {
      vms = await api.reorderVirtualMachines(reorders);
      // Ansicht auf Prio-Sortierung zurücksetzen, damit der User das Ergebnis sieht
      sortColumn = 'priority';
      sortDirection = 'asc';
    } catch (err: any) {
      alert("Fehler beim Speichern der Reihenfolge: " + err.message);
    }
    
    draggedVmId = null;
    dragOverVmId = null;
  }

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
    panelOpen = true;
  }

  function openEdit(vm: VirtualMachine) {
    editMode = true;
    currentVm = { ...vm };
    panelOpen = true;
  }

  async function save() {
    try {
      if (editMode && currentVm.id) {
        await api.updateVirtualMachine(currentVm.id, currentVm);
      } else {
        await api.createVirtualMachine(currentVm);
      }
      panelOpen = false;
      vms = await api.getVirtualMachines();
    } catch (e: any) {
      if (e.message?.includes('Zirkuläre Abhängigkeit')) {
        alert("Fehler: " + e.message);
      } else {
        alert("Fehler beim Speichern: " + e.message);
      }
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
      <h1 class="text-2xl font-bold text-[var(--color-text)] tracking-tight flex items-center gap-3">
        <Monitor class="w-6 h-6 text-pink-400" />
        Virtuelle Maschinen
      </h1>
      <p class="text-[var(--color-text2)] text-sm mt-1">
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

  <div class="flex gap-4 flex-1 min-h-0">
    <!-- Hosts Sidebar -->
    <div class="w-64 bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl flex flex-col overflow-hidden shrink-0 shadow-lg hidden md:flex">
      <div class="p-3 border-b border-[var(--color-border)] bg-[var(--color-bg3)] font-semibold text-sm text-[var(--color-text)] flex items-center gap-2 shrink-0">
        <Server class="w-4 h-4 text-[var(--color-text3)]"/>
        Physische Hosts
      </div>
      <div class="flex-1 overflow-y-auto p-2 space-y-2">
        {#each devices as dev}
          <div 
            class="p-3 rounded-lg border transition-colors {dragOverHostId === dev.id ? 'border-pink-500 bg-pink-500/10' : 'border-[var(--color-border2)] bg-[var(--color-bg3)]'}"
            ondragover={(e) => { e.preventDefault(); if(draggedVmId) dragOverHostId = dev.id; }}
            ondragleave={() => dragOverHostId = null}
            ondrop={(e) => handleHostDrop(e, dev.id)}
          >
            <div class="font-medium text-sm flex items-center justify-between text-[var(--color-text)]">
              <span class="truncate pr-2" title={dev.hostname}>{dev.hostname}</span>
            </div>
            {@const hostVms = vms.filter(v => v.host_device_id === dev.id)}
            <div class="mt-2 flex flex-col gap-1">
              <span class="text-[10px] text-[var(--color-text2)] font-semibold">{hostVms.length} VMs</span>
              {#if hostVms.length > 0}
                <div class="flex flex-wrap gap-1">
                  {#each hostVms as hv}
                    <span class="px-1.5 py-0.5 bg-[var(--color-border)] text-[var(--color-text2)] rounded text-[9px] truncate max-w-[80px]" title={hv.name}>{hv.name}</span>
                  {/each}
                </div>
              {/if}
            </div>
          </div>
        {/each}
      </div>
    </div>

    <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl flex-1 overflow-hidden flex flex-col shadow-xl min-w-0">
    <!-- Tabs Header -->
    <div class="flex border-b border-[var(--color-border)] bg-[var(--color-bg3)] px-4 py-2 justify-between items-center shrink-0 select-none">
      <div class="flex space-x-2">
        <button 
          onclick={() => activeTab = 'table'} 
          class={`px-3 py-1.5 text-xs font-semibold rounded-lg transition ${activeTab === 'table' ? 'bg-[var(--color-border)] text-[var(--color-text)] border border-[var(--color-border2)]' : 'text-[var(--color-text2)] hover:text-[var(--color-text)]'}`}
        >
          Tabelle
        </button>
        <button 
          onclick={() => activeTab = 'graph'} 
          class={`px-3 py-1.5 text-xs font-semibold rounded-lg transition ${activeTab === 'graph' ? 'bg-[var(--color-border)] text-[var(--color-text)] border border-[var(--color-border2)]' : 'text-[var(--color-text2)] hover:text-[var(--color-text)]'}`}
        >
          Abhängigkeitsgraph
        </button>
      </div>
      
      {#if activeTab === 'graph'}
        <div class="text-[10px] text-[var(--color-text2)] italic">
          Tipp: Bewege den Mauszeiger über eine VM, um Abhängigkeitsketten anzuzeigen.
        </div>
      {/if}
    </div>

    {#if activeTab === 'table'}
      <div class="overflow-x-auto flex-1">
        <table class="w-full text-left text-sm text-[var(--color-text)]">
          <thead class="text-xs uppercase bg-[var(--color-border2)] text-[var(--color-text2)] sticky top-0 z-10 select-none">
            <tr>
              <th class="px-4 py-3 font-semibold cursor-pointer hover:bg-[var(--color-border)] transition" onclick={() => handleSort('name')}>
                <div class="flex items-center gap-1">Name {#if sortColumn === 'name'}{#if sortDirection === 'asc'}<ArrowUp class="w-3 h-3"/>{:else}<ArrowDown class="w-3 h-3"/>{/if}{/if}</div>
              </th>
              <th class="px-4 py-3 font-semibold cursor-pointer hover:bg-[var(--color-border)] transition" onclick={() => handleSort('hypervisor_typ')}>
                <div class="flex items-center gap-1">Hypervisor {#if sortColumn === 'hypervisor_typ'}{#if sortDirection === 'asc'}<ArrowUp class="w-3 h-3"/>{:else}<ArrowDown class="w-3 h-3"/>{/if}{/if}</div>
              </th>
              <th class="px-4 py-3 font-semibold cursor-pointer hover:bg-[var(--color-border)] transition" onclick={() => handleSort('host')}>
                <div class="flex items-center gap-1">Läuft auf (Host) {#if sortColumn === 'host'}{#if sortDirection === 'asc'}<ArrowUp class="w-3 h-3"/>{:else}<ArrowDown class="w-3 h-3"/>{/if}{/if}</div>
              </th>
              <th class="px-4 py-3 font-semibold cursor-pointer hover:bg-[var(--color-border)] transition" onclick={() => handleSort('dienst')}>
                <div class="flex items-center gap-1">Dienst {#if sortColumn === 'dienst'}{#if sortDirection === 'asc'}<ArrowUp class="w-3 h-3"/>{:else}<ArrowDown class="w-3 h-3"/>{/if}{/if}</div>
              </th>
              <th class="px-4 py-3 font-semibold cursor-pointer hover:bg-[var(--color-border)] transition" onclick={() => handleSort('ip_adresse')}>
                <div class="flex items-center gap-1">IP-Adresse {#if sortColumn === 'ip_adresse'}{#if sortDirection === 'asc'}<ArrowUp class="w-3 h-3"/>{:else}<ArrowDown class="w-3 h-3"/>{/if}{/if}</div>
              </th>
              <th class="px-4 py-3 font-semibold text-center cursor-pointer hover:bg-[var(--color-border)] transition" onclick={() => handleSort('priority')}>
                <div class="flex items-center justify-center gap-1">Prio {#if sortColumn === 'priority'}{#if sortDirection === 'asc'}<ArrowUp class="w-3 h-3"/>{:else}<ArrowDown class="w-3 h-3"/>{/if}{/if}</div>
              </th>
              <th class="px-4 py-3 font-semibold cursor-pointer hover:bg-[var(--color-border)] transition" onclick={() => handleSort('responsible')}>
                <div class="flex items-center gap-1">Verantwortlich {#if sortColumn === 'responsible'}{#if sortDirection === 'asc'}<ArrowUp class="w-3 h-3"/>{:else}<ArrowDown class="w-3 h-3"/>{/if}{/if}</div>
              </th>
              <th class="px-4 py-3 text-right">Aktionen</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-[var(--color-border)]/50">
            {#if loading}
              <tr><td colspan="8" class="text-center py-8 text-[var(--color-text3)]">Lade VMs...</td></tr>
            {:else if vms.length === 0}
              <tr><td colspan="8" class="text-center py-8 text-[var(--color-text3)]">Keine VMs dokumentiert.</td></tr>
            {:else}
              {#each sortedVms as vm (vm.id)}
                <tr 
                  class="hover:bg-[var(--color-border2)] transition group cursor-grab active:cursor-grabbing {draggedVmId === vm.id ? 'opacity-50' : ''} {dragOverVmId === vm.id ? 'border-t-2 border-pink-500' : ''}"
                  draggable="true"
                  ondragstart={(e) => {
                    draggedVmId = vm.id;
                    if (e.dataTransfer) {
                      e.dataTransfer.effectAllowed = 'move';
                      e.dataTransfer.setData('text/plain', vm.id.toString());
                    }
                  }}
                  ondragover={(e) => {
                    e.preventDefault();
                    if (draggedVmId && draggedVmId !== vm.id) dragOverVmId = vm.id;
                  }}
                  ondragleave={() => dragOverVmId = null}
                  ondrop={(e) => handleDrop(e, vm.id)}
                  ondragend={() => { draggedVmId = null; dragOverVmId = null; }}
                >
                  <td class="px-4 py-3 font-medium text-[var(--color-text)] flex items-center gap-2">
                    <GripVertical class="w-4 h-4 text-[var(--color-text3)] opacity-0 group-hover:opacity-100 cursor-grab" />
                    {vm.name}
                  </td>
                  <td class="px-4 py-3 text-xs">
                    <span class="bg-[var(--color-border)] border border-[var(--color-border2)] px-2 py-0.5 rounded text-[var(--color-text)]">
                      {vm.hypervisor_typ || '—'}
                    </span>
                  </td>
                  <td class="px-4 py-3">
                    <div class="flex items-center gap-2">
                      <Server class="w-3.5 h-3.5 text-[var(--color-text3)]" />
                      <span class="font-mono text-xs">{getHostName(vm.host_device_id)}</span>
                    </div>
                  </td>
                  <td class="px-4 py-3 text-[var(--color-text2)] max-w-[200px] truncate" title={vm.dienst || ''}>{vm.dienst || '—'}</td>
                  <td class="px-4 py-3 font-mono text-xs text-[var(--color-text2)]">{vm.ip_adresse || '—'}</td>
                  <td class="px-4 py-3 text-center">
                    <span class={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${vm.shutdown_priority === 1 ? 'bg-red-500/20 text-red-400' : vm.shutdown_priority === 2 ? 'bg-orange-500/20 text-orange-400' : 'bg-[var(--color-border)] text-[var(--color-text2)]'}`}>
                      {vm.shutdown_priority}
                    </span>
                  </td>
                  <td class="px-4 py-3 text-[var(--color-text2)] text-xs">{vm.responsible || '—'}</td>
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
      <div class="flex-1 overflow-auto bg-[var(--color-bg2)] relative min-h-[500px]">
        {#if loading}
          <div class="absolute inset-0 flex items-center justify-center text-[var(--color-text3)]">Lade Graph...</div>
        {:else if vms.length === 0}
          <div class="absolute inset-0 flex items-center justify-center text-[var(--color-text3)]">Keine VMs für Graph vorhanden.</div>
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
                  class="absolute flex flex-col justify-between p-3 rounded-lg border text-left cursor-pointer transition-all duration-200 select-none bg-[var(--color-bg2)] group shadow-md {dragOverDependencyVmId === vm.id ? 'ring-2 ring-pink-500 bg-pink-500/10' : ''}"
                  style="width: 220px; height: 75px; left: {coord.x - 110}px; top: {coord.y - 37}px;
                         border-color: {isHovered ? '#3b82f6' : isParent ? '#10b981' : isChild ? '#ec4899' : '#1f2937'};
                         box-shadow: {isHovered ? '0 0 10px rgba(59, 130, 246, 0.4)' : isParent ? '0 0 10px rgba(16, 185, 129, 0.4)' : isChild ? '0 0 10px rgba(236, 72, 153, 0.4)' : 'none'};
                         opacity: {isUnrelated ? 0.35 : draggedVmId === vm.id ? 0.5 : 1};"
                  onmouseenter={() => hoveredVmId = vm.id}
                  onmouseleave={() => hoveredVmId = null}
                  onclick={() => openEdit(vm)}
                  draggable="true"
                  ondragstart={(e) => {
                    draggedVmId = vm.id;
                    if (e.dataTransfer) {
                      e.dataTransfer.effectAllowed = 'link';
                      e.dataTransfer.setData('text/plain', vm.id.toString());
                    }
                  }}
                  ondragover={(e) => {
                    e.preventDefault();
                    if (draggedVmId && draggedVmId !== vm.id) dragOverDependencyVmId = vm.id;
                  }}
                  ondragleave={() => dragOverDependencyVmId = null}
                  ondrop={(e) => handleDependencyDrop(e, vm.id)}
                  ondragend={() => { draggedVmId = null; dragOverDependencyVmId = null; }}
                >
                  <div class="flex items-start justify-between gap-1.5 min-w-0">
                    <div class="flex items-center gap-1.5 min-w-0">
                      <Monitor class="w-4 h-4 text-pink-400 shrink-0" />
                      <div class="truncate text-xs font-semibold text-[var(--color-text)]" title={vm.name}>{vm.name}</div>
                    </div>
                    <div class="flex items-center gap-1 shrink-0">
                      <span class={`inline-flex items-center justify-center w-4 h-4 rounded-full text-[9px] font-bold ${vm.shutdown_priority === 1 ? 'bg-red-500/20 text-red-400' : vm.shutdown_priority === 2 ? 'bg-orange-500/20 text-orange-400' : 'bg-[var(--color-border)] text-[var(--color-text2)]'}`} title="Shutdown Priorität">
                        {vm.shutdown_priority}
                      </span>
                    </div>
                  </div>
                  
                  <div class="flex items-end justify-between gap-1.5 min-w-0">
                    <div class="truncate text-[10px] text-[var(--color-text2)]">
                      <span class="text-[var(--color-text3)]">Host:</span> {getHostName(vm.host_device_id)}
                    </div>
                    <div class="font-mono text-[9px] text-[var(--color-text3)] shrink-0">
                      {vm.ip_adresse || 'Keine IP'}
                    </div>
                  </div>
                  
                  <!-- Quick actions on hover -->
                  <div class="absolute -top-2 -right-2 hidden group-hover:flex items-center gap-1 bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-md p-1 shadow-lg z-20">
                    <button
                      onclick={(e: Event) => { e.stopPropagation(); openEdit(vm); }}
                      class="p-0.5 text-[#5DCAA5] hover:text-[#86EFCB] hover:bg-[var(--color-border)] rounded"
                      title="Bearbeiten"
                    >
                      <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 20h9"></path>
                        <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"></path>
                      </svg>
                    </button>
                    <button
                      onclick={(e: Event) => { e.stopPropagation(); deleteVm(vm.id); }}
                      class="p-0.5 text-red-400 hover:text-red-300 hover:bg-[var(--color-border)] rounded"
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
</div>

{#if panelOpen}
<!-- Backdrop overlay -->
<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 transition-opacity" onclick={() => panelOpen = false}></div>

<!-- Slide Panel -->
<div class="fixed inset-y-0 right-0 w-full max-w-md bg-[var(--color-bg2)] border-l border-[var(--color-border)] shadow-2xl z-50 flex flex-col transform transition-transform duration-300 translate-x-0">
  <div class="p-4 border-b border-[var(--color-border)] flex items-center justify-between shrink-0 bg-[var(--color-bg3)]">
    <h3 class="text-lg font-bold text-[var(--color-text)] flex items-center gap-2">
      <Monitor class="w-5 h-5 text-pink-400" />
      {editMode ? 'VM bearbeiten' : 'Neue VM anlegen'}
    </h3>
    <button onclick={() => panelOpen = false} class="text-[var(--color-text2)] hover:text-[var(--color-text)] transition-colors p-1 hover:bg-[var(--color-border)] rounded">
      ✕
    </button>
  </div>
  
  <div class="p-6 overflow-y-auto flex-1 space-y-5">
    <div class="grid grid-cols-1 gap-4">
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Name <span class="text-red-400">*</span></label>
        <input type="text" bind:value={currentVm.name} class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-pink-500" />
      </div>
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Hypervisor-Typ</label>
        <select bind:value={currentVm.hypervisor_typ} class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-pink-500">
          <option value="vmware">VMware ESXi</option>
          <option value="hyper-v">Microsoft Hyper-V</option>
          <option value="kvm">KVM (Linux)</option>
          <option value="xcpng">XCP-ng</option>
          <option value="sonstige">Sonstige</option>
        </select>
      </div>
    </div>

    <div>
      <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Läuft auf (Host-System) <span class="text-red-400">*</span></label>
      <select bind:value={currentVm.host_device_id} class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-pink-500">
        <option value={null}>-- Physischen Server wählen --</option>
        {#each devices as dev}
          <option value={dev.id}>{dev.hostname} ({dev.typ})</option>
        {/each}
      </select>
    </div>

    <div class="grid grid-cols-1 gap-4">
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Betriebssystem</label>
        <input type="text" bind:value={currentVm.betriebssystem} placeholder="z.B. Ubuntu 24.04" class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-pink-500" />
      </div>
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">IP-Adresse</label>
        <input type="text" bind:value={currentVm.ip_adresse} placeholder="192.168.x.x" class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] font-mono focus:outline-none focus:border-pink-500" />
      </div>
    </div>

    <div>
      <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Dienst / Anwendung</label>
      <input type="text" bind:value={currentVm.dienst} placeholder="z.B. Primary Database Server" class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-pink-500" />
    </div>

    <div class="grid grid-cols-1 gap-4">
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Abhängig von (VM)</label>
        <select bind:value={currentVm.depends_on_vm_id} class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-pink-500">
          <option value={null}>-- Keine Abhängigkeit --</option>
          {#each vms.filter(v => v.id !== currentVm.id) as v}
            <option value={v.id}>{v.name}</option>
          {/each}
        </select>
      </div>
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Shutdown-Prio</label>
        <input type="number" bind:value={currentVm.shutdown_priority} min="1" max="99" class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-pink-500" />
      </div>
    </div>

    <div>
      <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Verantwortlicher (Team/Person)</label>
      <input type="text" bind:value={currentVm.responsible} placeholder="z.B. Andreas / DBA Team" class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-pink-500" />
    </div>

    <div>
      <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Bemerkung</label>
      <textarea bind:value={currentVm.bemerkung} rows="3" class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-pink-500 resize-none"></textarea>
    </div>
  </div>

  <div class="p-4 border-t border-[var(--color-border)] bg-[var(--color-bg3)] flex justify-end gap-3 shrink-0">
    <button onclick={() => panelOpen = false} class="px-4 py-2 rounded-lg text-sm font-medium text-[var(--color-text2)] hover:text-[var(--color-text)] hover:bg-[var(--color-border)] transition">Abbrechen</button>
    <button 
      onclick={save}
      disabled={!currentVm.name || !currentVm.host_device_id}
      class="px-4 py-2 bg-pink-600 hover:bg-pink-500 disabled:opacity-50 disabled:cursor-not-allowed text-[var(--color-text)] rounded-lg text-sm font-semibold transition flex items-center gap-2"
    >
      <CheckCircle2 class="w-4 h-4" />
      Speichern
    </button>
  </div>
</div>
{/if}

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

  <div class="bg-[#101622] border border-slate-800 rounded-xl flex-1 overflow-hidden flex flex-col shadow-2xl">
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
                  <button onclick={() => openEdit(vm)} class="text-blue-400 hover:text-blue-300 text-xs font-medium">Bearbeiten</button>
                  <button onclick={() => deleteVm(vm.id)} class="text-red-400 hover:text-red-300 text-xs font-medium">Löschen</button>
                </td>
              </tr>
            {/each}
          {/if}
        </tbody>
      </table>
    </div>
  </div>
</div>

{#if showModal}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[#101622] border border-slate-800 rounded-xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
    <div class="p-4 border-b border-slate-800 flex items-center justify-between">
      <h3 class="text-lg font-bold text-white">{editMode ? 'VM bearbeiten' : 'Neue VM anlegen'}</h3>
      <button onclick={() => showModal = false} class="text-slate-400 hover:text-white">✕</button>
    </div>
    
    <div class="p-6 overflow-y-auto space-y-4">
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Name <span class="text-red-400">*</span></label>
          <input type="text" bind:value={currentVm.name} class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-pink-500" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Hypervisor-Typ</label>
          <select bind:value={currentVm.hypervisor_typ} class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-pink-500">
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
        <select bind:value={currentVm.host_device_id} class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-pink-500">
          <option value={null}>-- Physischen Server wählen --</option>
          {#each devices as dev}
            <option value={dev.id}>{dev.hostname} ({dev.typ})</option>
          {/each}
        </select>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Betriebssystem</label>
          <input type="text" bind:value={currentVm.betriebssystem} placeholder="z.B. Ubuntu 24.04" class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-pink-500" />
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">IP-Adresse</label>
          <input type="text" bind:value={currentVm.ip_adresse} placeholder="192.168.x.x" class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-pink-500" />
        </div>
      </div>

      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Dienst / Anwendung</label>
        <input type="text" bind:value={currentVm.dienst} placeholder="z.B. Primary Database Server" class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-pink-500" />
      </div>

      <div class="grid grid-cols-3 gap-4">
        <div class="col-span-2">
          <label class="block text-xs font-semibold text-slate-400 mb-1">Abhängig von (VM)</label>
          <select bind:value={currentVm.depends_on_vm_id} class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-pink-500">
            <option value={null}>-- Keine Abhängigkeit --</option>
            {#each vms.filter(v => v.id !== currentVm.id) as v}
              <option value={v.id}>{v.name}</option>
            {/each}
          </select>
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-400 mb-1">Shutdown-Prio</label>
          <input type="number" bind:value={currentVm.shutdown_priority} min="1" max="99" class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-pink-500" />
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div class="col-span-2">
          <label class="block text-xs font-semibold text-slate-400 mb-1">Verantwortlicher (Team/Person)</label>
          <input type="text" bind:value={currentVm.responsible} placeholder="z.B. Andreas / DBA Team" class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-pink-500" />
        </div>
      </div>

      <div>
        <label class="block text-xs font-semibold text-slate-400 mb-1">Bemerkung</label>
        <textarea bind:value={currentVm.bemerkung} rows="2" class="w-full bg-[#182030] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-pink-500 resize-none"></textarea>
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

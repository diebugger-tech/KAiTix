<script lang="ts">
  import type { VirtualMachine, Device } from '$lib/types';

  let { 
    vm = $bindable(),
    devices,
    vms
  } : {
    vm: Partial<VirtualMachine>;
    devices: Device[];
    vms: VirtualMachine[];
  } = $props();
</script>

<div class="space-y-5">
  <div class="grid grid-cols-1 gap-4">
    <div>
      <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Name <span class="text-red-400">*</span></label>
      <input type="text" bind:value={vm.name} autofocus class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-pink-500" />
    </div>
    <div>
      <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Hypervisor-Typ</label>
      <select bind:value={vm.hypervisor_typ} class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-pink-500">
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
    <select bind:value={vm.host_device_id} class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-pink-500">
      <option value={null}>-- Physischen Server wählen --</option>
      {#each devices as dev}
        <option value={dev.id}>{dev.hostname} ({dev.typ})</option>
      {/each}
    </select>
  </div>

  <div class="grid grid-cols-1 gap-4">
    <div>
      <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Betriebssystem</label>
      <input type="text" bind:value={vm.betriebssystem} placeholder="z.B. Ubuntu 24.04" class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-pink-500" />
    </div>
    <div>
      <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">IP-Adresse</label>
      <input type="text" bind:value={vm.ip_adresse} placeholder="192.168.x.x" class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] font-mono focus:outline-none focus:border-pink-500" />
    </div>
    <div>
      <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">IPv6-Adresse</label>
      <input type="text" bind:value={vm.ipv6_adresse} placeholder="2001:db8::x" class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] font-mono focus:outline-none focus:border-pink-500" />
    </div>
  </div>

  <div>
    <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Dienst / Anwendung</label>
    <input type="text" bind:value={vm.dienst} placeholder="z.B. Primary Database Server" class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-pink-500" />
  </div>

  <div class="grid grid-cols-1 gap-4">
    <div>
      <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Abhängig von (VM)</label>
      <select bind:value={vm.depends_on_vm_id} class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-pink-500">
        <option value={null}>-- Keine Abhängigkeit --</option>
        {#each vms as v}
          {#if !vm.id || v.id !== vm.id}
            <option value={v.id}>{v.name}</option>
          {/if}
        {/each}
      </select>
    </div>
    <div>
      <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Shutdown-Prio</label>
      <input type="number" bind:value={vm.shutdown_priority} min="1" max="99" class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-pink-500" />
    </div>
  </div>

  <div>
    <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Verantwortlicher (Team/Person)</label>
    <input type="text" bind:value={vm.responsible} placeholder="z.B. Andreas / DBA Team" class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-pink-500" />
  </div>

  <div>
    <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Bemerkung</label>
    <textarea bind:value={vm.bemerkung} rows="3" class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-pink-500 resize-none"></textarea>
  </div>
</div>

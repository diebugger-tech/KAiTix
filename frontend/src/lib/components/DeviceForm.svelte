<script lang="ts">
  import { X } from '@lucide/svelte';
  import type { Device } from '$lib/types';
  import { validateDevicePosition } from '$lib/validation';

  let { 
    device = $bindable(),
    rackHoeheU,
    devices
  } : {
    device: Partial<Device> & { dependencies?: any[] };
    rackHoeheU: number;
    devices: Device[];
  } = $props();

  let uPositionError = $derived(validateDevicePosition(device.u_position, device.u_hoehe ?? 0, rackHoeheU));

  function addDependency() {
    if (!device.dependencies) device.dependencies = [];
    device.dependencies.push({
      depends_on_device_id: devices.find(d => d.id !== device.id)?.id || null,
      dependency_type: 'power',
      dependency_group: ''
    });
  }

  function removeDependency(idx: number) {
    if (!device.dependencies) return;
    device.dependencies.splice(idx, 1);
  }
</script>

<div class="space-y-4">
  <div>
    <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Hostname *</label>
    <input type="text" bind:value={device.hostname} required autofocus
      class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
  </div>
  
  <div class="grid grid-cols-2 gap-4">
    <div>
      <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">U-Position</label>
      <input type="number" bind:value={device.u_position} min="1" max={rackHoeheU}
        disabled={device.u_hoehe === 0}
        class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75] disabled:opacity-50" />
      {#if uPositionError && device.u_hoehe !== 0}
        <p class="text-red-500 text-[10px] mt-1">{uPositionError}</p>
      {/if}
    </div>
    <div>
      <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Höhe (HE)</label>
      <input type="number" bind:value={device.u_hoehe} min="0"
        oninput={() => { if (device.u_hoehe === 0) device.u_position = null; }}
        class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
    </div>
  </div>

  {#if device.u_hoehe === 0}
  <div>
    <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Seite</label>
    <div class="grid grid-cols-2 gap-2">
      <button type="button" onclick={() => device.side = 'left'}
        class="px-3 py-2 rounded-lg text-sm transition border {device.side === 'left' ? 'bg-[#1D9E75]/20 border-[#1D9E75]/40 text-[var(--color-text)]' : 'text-[var(--color-text2)] hover:bg-[var(--color-border2)] border-[var(--color-border2)]'}">
        Links (0UL)
      </button>
      <button type="button" onclick={() => device.side = 'right'}
        class="px-3 py-2 rounded-lg text-sm transition border {device.side === 'right' ? 'bg-[#1D9E75]/20 border-[#1D9E75]/40 text-[var(--color-text)]' : 'text-[var(--color-text2)] hover:bg-[var(--color-border2)] border-[var(--color-border2)]'}">
        Rechts (0UR)
      </button>
    </div>
  </div>
  {/if}

  {#if device.typ !== 'pdu'}
  <div class="mb-4">
    <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Anschlussleistung (W)</label>
    <input type="number" bind:value={device.anschlussleistung_watt} min="0"
      class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
  </div>
  {/if}

  <div>
    <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">IPv6-Adresse</label>
    <input type="text" bind:value={device.ipv6_adresse} placeholder="2001:db8::1"
      class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] font-mono focus:outline-none focus:border-[#1D9E75]" />
  </div>
  
  <div>
    <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">IP-Adresse</label>
    <input type="text" bind:value={device.ip_adresse} placeholder="192.168.1.10"
      class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] font-mono focus:outline-none focus:border-[#1D9E75]" />
  </div>

  <div class="grid grid-cols-2 gap-4">
    <div>
      <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Hersteller</label>
      <input type="text" bind:value={device.hersteller}
        class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
    </div>
    <div>
      <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Modell</label>
      <input type="text" bind:value={device.modell}
        class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
    </div>
  </div>

  <div class="grid grid-cols-2 gap-4">
    <div>
      <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Seriennummer</label>
      <input type="text" bind:value={device.seriennummer}
        class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
    </div>
    <div>
      <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Inventarnummer</label>
      <input type="text" bind:value={device.inventarnummer}
        class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
    </div>
  </div>

  <div>
    <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Bemerkung</label>
    <textarea bind:value={device.bemerkung} rows="2"
      class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75] resize-none"></textarea>
  </div>

  <div class="border-t border-[var(--color-border)] pt-4 mt-2">
    <h4 class="text-sm font-bold text-[var(--color-text)] mb-3">Ausfall- & Boot-Verhalten</h4>
    <div class="grid grid-cols-3 gap-4 mb-4">
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Priorität (1=Höchste)</label>
        <input type="number" bind:value={device.shutdown_priority} min="1" max="4"
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
      </div>
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Delay (Sekunden)</label>
        <input type="number" bind:value={device.shutdown_delay_sec} min="0"
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]" />
      </div>
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Methode</label>
        <select bind:value={device.shutdown_method}
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]">
          <option value="">Keine Aktion</option>
          <option value="ACPI_Graceful">ACPI Graceful (Soft Power Button)</option>
          <option value="IPMI_Hard_Poweroff">IPMI Hard Poweroff</option>
          <option value="SSH_Script">SSH Script (Fallback)</option>
          <option value="PDU_Outlet_Off">PDU Outlet Off (Hard)</option>
        </select>
      </div>
    </div>

    <div>
      <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Abhängigkeiten (fährt nur hoch, wenn...)</label>
      {#if device.dependencies}
        {#each device.dependencies as dep, i}
          <div class="flex items-center gap-2 mb-2">
            <select bind:value={dep.depends_on_device_id} class="w-48 bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded px-2 py-1 text-xs text-[var(--color-text)]">
              {#each devices as d}
                {#if d.id !== device.id}
                  <option value={d.id}>{d.hostname}</option>
                {/if}
              {/each}
            </select>
            <select bind:value={dep.dependency_type} class="w-24 bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded px-2 py-1 text-xs text-[var(--color-text)]">
              <option value="power">Power</option>
              <option value="network">Network</option>
            </select>
            <input type="text" bind:value={dep.dependency_group} placeholder="HA-Cluster (opt)" class="w-28 bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded px-2 py-1 text-xs text-[var(--color-text)]" />
            <button type="button" onclick={() => removeDependency(i)} class="p-1 text-red-500/50 hover:text-red-400"><X class="w-3 h-3"/></button>
          </div>
        {/each}
      {/if}
      <button type="button" onclick={addDependency}
        class="text-xs text-blue-400 hover:text-[#86EFCB] mt-1 flex items-center gap-1">+ Abhängigkeit hinzufügen</button>
    </div>
  </div>
</div>

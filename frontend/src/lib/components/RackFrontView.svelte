<script lang="ts">
  import type { Rack, Device, HardwareType } from '$lib/api';
  import { Plus, X } from '@lucide/svelte';

  let {
    rack,
    rackDevices = [],
    devices = [],
    hardware = [],
    selectedDevice = null,
    onDeviceClick = undefined,
    onEmptyClick = undefined,
    onEmptySideClick = undefined,
    readonly = false
  } = $props<{
    rack: Rack,
    rackDevices?: Device[],
    devices?: Device[],
    hardware?: HardwareType[],
    selectedDevice?: Device | null,
    onDeviceClick?: (dev: Device, e: MouseEvent) => void,
    onEmptyClick?: (u: number, e: MouseEvent) => void,
    onEmptySideClick?: (side: 'left' | 'right', e: MouseEvent) => void,
    readonly?: boolean,
    maxSlots?: number
  }>();

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

  const occupiedSides = $derived.by(() => {
    return {
      left: rackDevices.some(d => d.u_hoehe === 0 && d.side === 'left'),
      right: rackDevices.some(d => d.u_hoehe === 0 && d.side === 'right')
    };
  });

  const conflictDeviceIds = $derived.by(() => {
    const ids = new Set<number>();
    const mainDevices = rackDevices.filter(d => (d.u_hoehe ?? 0) > 0);
    const usedUs = new Map<number, number[]>();
    for (const d of mainDevices) {
      const up = d.u_position ?? 1;
      const h = d.u_hoehe;
      for (let u = up; u < up + h; u++) {
        if (!usedUs.has(u)) usedUs.set(u, []);
        usedUs.get(u)!.push(d.id);
      }
    }
    for (const [_, devs] of usedUs) {
      if (devs.length > 1) {
        for (const id of devs) ids.add(id);
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

  function isTopU(dev: Device, u: number) { 
    return u === (dev.u_position ?? 0) + dev.u_hoehe - 1; 
  }

  function typColor(typ: string) {
    return typ === 'server'   ? { bg: 'rgba(59,130,246,.18)',  border: 'rgba(59,130,246,.4)'  } :
           typ === 'switch'   ? { bg: 'rgba(6,182,212,.18)',   border: 'rgba(6,182,212,.4)'   } :
           typ === 'pdu'      ? { bg: 'rgba(239,68,68,.18)',   border: 'rgba(239,68,68,.4)'   } :
           typ === 'firewall' ? { bg: 'rgba(234,179,8,.18)',   border: 'rgba(234,179,8,.4)'   } :
           typ === 'storage'  ? { bg: 'rgba(168,85,247,.18)',  border: 'rgba(168,85,247,.4)'  } :
                                { bg: 'rgba(249,115,22,.18)',  border: 'rgba(249,115,22,.4)'  };
  }

  function isDeviceIncompatible(dev: Device) {
    if (!dev.hersteller || !dev.modell || !rack) return false;
    const hw = hardware.find(h => h.hersteller === dev.hersteller && h.modell === dev.modell);
    if (!hw || !hw.min_rack_hoehe) return false;
    return rack.hoehe_u < hw.min_rack_hoehe;
  }

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

  function handleDeviceClick(dev: Device, e: MouseEvent) {
    if (onDeviceClick) onDeviceClick(dev, e);
  }

  function handleEmptyClick(u: number, e: MouseEvent) {
    if (!readonly && onEmptyClick) onEmptyClick(u, e);
  }

  function handleEmptySideClick(side: 'left' | 'right', e: MouseEvent) {
    if (!readonly && onEmptySideClick) onEmptySideClick(side, e);
  }
</script>

<div class="flex border-b border-slate-900 max-h-[60vh]">
  
  <!-- Linke Seite (Zero-U) -->
  <div class="w-10 sm:w-12 bg-[#090d14] border-r border-slate-900 flex flex-col items-stretch p-1.5 min-h-0">
    <div class="text-[7px] text-slate-600 text-center uppercase mb-1">0U L</div>
    {#each leftSide as dev}
      {@const c = typColor(dev.typ)}
      {@const isIncompatible = isDeviceIncompatible(dev)}
      <button
        onclick={(e) => handleDeviceClick(dev, e)}
        class="w-full flex-1 min-h-0 rounded border hover:brightness-110 transition flex items-center justify-center overflow-hidden {selectedDevice?.id === dev.id ? 'ring-1 ring-white/30' : ''} {isIncompatible ? 'ring-1 ring-red-500 border-red-500' : ''}"
        style="background:{isIncompatible ? 'rgba(239,68,68,.22)' : c.bg}; border-color:{isIncompatible ? 'rgba(239,68,68,.7)' : c.border}; writing-mode: vertical-rl; transform: rotate(180deg);"
        title={isIncompatible ? '⚠ Höhenkonflikt: ' + getDeviceTooltip(dev) : getDeviceTooltip(dev)}
      >
        <span class="font-semibold text-white text-[9px] leading-none">{isIncompatible ? '⚠ ' : ''}{dev.hostname}</span>
        <span class="text-[7px] opacity-60">{dev.typ.toUpperCase()}</span>
      </button>
    {/each}
    {#if !readonly}
      {#if !occupiedSides.left}
      <button onclick={(e) => handleEmptySideClick('left', e)} class="w-full aspect-square mt-auto border border-dashed border-slate-800 rounded flex items-center justify-center text-slate-600 hover:text-blue-500 hover:border-[#1D9E75]/50 hover:bg-[#1D9E75]/10 transition shrink-0">
        <Plus class="w-4 h-4" />
      </button>
      {:else}
      <div class="w-full aspect-square mt-auto border border-dashed border-red-800/20 rounded flex items-center justify-center text-red-800/30 shrink-0" title="Seite bereits belegt">
        <X class="w-4 h-4" />
      </div>
      {/if}
    {/if}
  </div>

  <!-- Main HE Slots -->
  <div class="flex-1 p-2 font-mono text-[9px] overflow-y-auto relative bg-[#131615]">
    <div class="text-center text-[8px] text-slate-600 pb-1 mb-1 border-b border-slate-900 sticky top-0 bg-[#131615] z-10">FRONTANSICHT</div>
    {#each Array.from({ length: Math.min(maxSlots || rack.hoehe_u, rack.hoehe_u) }, (_, i) => rack.hoehe_u - i) as u}
      {@const dev = devAt(u)}
      {#if dev}
        {#if isTopU(dev, u)}
          {@const c = typColor(dev.typ)}
          {@const isConflict = conflictDeviceIds.has(dev.id)}
          {@const isIncompatible = isDeviceIncompatible(dev)}
          <button
            onclick={(e) => handleDeviceClick(dev, e)}
            class="w-full px-2 rounded border mb-0.5 text-left hover:brightness-110 transition {selectedDevice?.id === dev.id ? 'ring-1 ring-white/30' : ''} {isConflict || isIncompatible ? 'ring-1 ring-red-500' : ''}"
            style="background:{isConflict || isIncompatible ? 'rgba(239,68,68,.22)' : c.bg}; border-color:{isConflict || isIncompatible ? 'rgba(239,68,68,.7)' : c.border}; min-height:{dev.u_hoehe * 22}px; display:flex; align-items:center; justify-content:space-between;"
            title={isConflict ? '⚠ U-Positions-Konflikt: ' + getDeviceTooltip(dev) : isIncompatible ? '⚠ Höhenkonflikt: ' + getDeviceTooltip(dev) : getDeviceTooltip(dev)}
          >
            <span class="font-semibold {isConflict || isIncompatible ? 'text-red-300' : 'text-white'} truncate">{isIncompatible ? '⚠ ' : ''}{dev.hostname}</span>
            <span class="text-[8px] opacity-60 shrink-0 ml-1">{isConflict || isIncompatible ? '⚠ ' : ''}{dev.typ.toUpperCase()} {dev.u_hoehe}U</span>
          </button>
        {/if}
      {:else}
        {#if !readonly}
        <button
          onclick={(e) => handleEmptyClick(u, e)}
          class="w-full px-2 py-1 mb-0.5 text-slate-700 border border-dashed border-slate-800/50 rounded flex justify-between items-center hover:border-[#1D9E75]/40 hover:text-[#1D9E75]/60 hover:bg-[#1D9E75]/5 transition group"
        >
          <span>HE {u}</span>
          <Plus class="w-3 h-3 opacity-0 group-hover:opacity-100 transition" />
        </button>
        {:else}
        <div class="w-full px-2 py-1 mb-0.5 text-slate-800/50 border border-transparent rounded flex justify-between items-center">
          <span>HE {u}</span>
        </div>
        {/if}
      {/if}
    {/each}
    {#if maxSlots && rack.hoehe_u > maxSlots}
      <div class="text-center text-[8px] py-1 text-slate-600 border-t border-slate-900 mt-1">
        + {rack.hoehe_u - maxSlots} weitere Höheneinheiten...
      </div>
    {/if}
  </div>

  <!-- Rechte Seite (Zero-U) -->
  <div class="w-10 sm:w-12 bg-[#090d14] border-l border-slate-900 flex flex-col items-stretch p-1.5 min-h-0">
    <div class="text-[7px] text-slate-600 text-center uppercase mb-1">0U R</div>
    {#each rightSide as dev}
      {@const c = typColor(dev.typ)}
      {@const isIncompatible = isDeviceIncompatible(dev)}
      <button
        onclick={(e) => handleDeviceClick(dev, e)}
        class="w-full flex-1 min-h-0 rounded border hover:brightness-110 transition flex items-center justify-center overflow-hidden {selectedDevice?.id === dev.id ? 'ring-1 ring-white/30' : ''} {isIncompatible ? 'ring-1 ring-red-500 border-red-500' : ''}"
        style="background:{isIncompatible ? 'rgba(239,68,68,.22)' : c.bg}; border-color:{isIncompatible ? 'rgba(239,68,68,.7)' : c.border}; writing-mode: vertical-rl; transform: rotate(180deg);"
        title={isIncompatible ? '⚠ Höhenkonflikt: ' + getDeviceTooltip(dev) : getDeviceTooltip(dev)}
      >
        <span class="font-semibold text-white text-[9px] leading-none">{isIncompatible ? '⚠ ' : ''}{dev.hostname}</span>
        <span class="text-[7px] opacity-60">{dev.typ.toUpperCase()}</span>
      </button>
    {/each}
    {#if !readonly}
      {#if !occupiedSides.right}
      <button onclick={(e) => handleEmptySideClick('right', e)} class="w-full aspect-square mt-auto border border-dashed border-slate-800 rounded flex items-center justify-center text-slate-600 hover:text-blue-500 hover:border-[#1D9E75]/50 hover:bg-[#1D9E75]/10 transition shrink-0">
        <Plus class="w-4 h-4" />
      </button>
      {:else}
      <div class="w-full aspect-square mt-auto border border-dashed border-red-800/20 rounded flex items-center justify-center text-red-800/30 shrink-0" title="Seite bereits belegt">
        <X class="w-4 h-4" />
      </div>
      {/if}
    {/if}
  </div>

</div>

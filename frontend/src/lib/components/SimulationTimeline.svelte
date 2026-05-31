<script lang="ts">
  import type { SimulationResult, TimelineEvent } from '$lib/api';
  import { Activity, Power, AlertTriangle, ChevronRight, Monitor, Clock, X, Info } from '@lucide/svelte';

  let { result = null, onClose = () => {} } = $props<{
    result: SimulationResult | null;
    onClose: () => void;
  }>();

  let activeTab: 'overview' | 'shutdown' | 'boot' = 'overview';

  function formatSeconds(s: number) {
    if (s === 0) return 'Sofort';
    const mins = Math.floor(s / 60);
    const secs = s % 60;
    if (mins > 0) return `${mins}m ${secs}s`;
    return `${secs}s`;
  }
</script>

{#if result}
<div class="fixed inset-0 bg-black/80 backdrop-blur-sm z-[100] flex flex-col p-4 sm:p-8">
  <div class="bg-[var(--color-bg2)] border border-[var(--color-border2)]/50 rounded-2xl shadow-2xl flex-1 flex flex-col overflow-hidden max-w-6xl mx-auto w-full">
    
    <!-- Header -->
    <div class="flex items-center justify-between px-6 py-4 border-b border-[var(--color-border)]/80 bg-[var(--color-bg2)]">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-[rgba(29,158,117,0.15)] flex items-center justify-center border border-[rgba(29,158,117,0.25)]">
          <Activity class="w-5 h-5 text-[#5DCAA5]" />
        </div>
        <div>
          <h2 class="text-xl font-bold text-[var(--color-text)] font-outfit">Ausfall- & Boot-Simulation</h2>
          <p class="text-xs text-[var(--color-text2)]">Detaillierte Analyse der Kaskadeneffekte und Zeitachsen</p>
        </div>
      </div>
      <button onclick={onClose} class="p-2 text-[var(--color-text2)] hover:text-[var(--color-text)] bg-[var(--color-border2)] hover:bg-[var(--color-border2)] rounded-lg transition">
        <X class="w-5 h-5" />
      </button>
    </div>

    <!-- Tabs -->
    <div class="flex px-6 border-b border-[var(--color-border)]/80 bg-[var(--color-bg2)]/50">
      <button class="px-6 py-3 text-sm font-semibold transition border-b-2 {activeTab === 'overview' ? 'text-[#5DCAA5] border-[#1D9E75]' : 'text-[var(--color-text2)] border-transparent hover:text-[var(--color-text)]'}"
        onclick={() => activeTab = 'overview'}>
        Übersicht & Auswirkungen ({result.affected_devices.length})
      </button>
      <button class="px-6 py-3 text-sm font-semibold transition border-b-2 {activeTab === 'shutdown' ? 'text-[#5DCAA5] border-[#1D9E75]' : 'text-[var(--color-text2)] border-transparent hover:text-[var(--color-text)]'}"
        onclick={() => activeTab = 'shutdown'}>
        Shutdown-Sequenz ({result.shutdown_timeline.length})
      </button>
      <button class="px-6 py-3 text-sm font-semibold transition border-b-2 {activeTab === 'boot' ? 'text-[#5DCAA5] border-[#1D9E75]' : 'text-[var(--color-text2)] border-transparent hover:text-[var(--color-text)]'}"
        onclick={() => activeTab = 'boot'}>
        Boot-Sequenz ({result.boot_timeline.length})
      </button>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto p-6 bg-[var(--color-bg2)]">
      {#if activeTab === 'overview'}
        <div class="space-y-6">
          {#if result.messages.length > 0}
            <div class="bg-[rgba(29,158,117,0.15)] border border-[rgba(29,158,117,0.25)] rounded-xl p-4">
              <h4 class="text-sm font-bold text-[#5DCAA5] mb-2 flex items-center gap-2"><Info class="w-4 h-4"/> Szenario-Log</h4>
              <ul class="list-disc list-inside text-xs text-[#86EFCB]/80 space-y-1">
                {#each result.messages as msg}<li>{msg}</li>{/each}
              </ul>
            </div>
          {/if}

          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {#each result.affected_devices as dev}
              <div class="bg-[var(--color-bg2)] border {dev.state === 'red' ? 'border-red-500/30' : 'border-amber-500/30'} rounded-xl p-4 relative overflow-hidden group">
                <div class="absolute top-0 left-0 w-1 h-full {dev.state === 'red' ? 'bg-red-500' : 'bg-amber-500'}"></div>
                
                <div class="flex items-start justify-between">
                  <div class="flex items-center gap-2">
                    <Monitor class="w-4 h-4 {dev.state === 'red' ? 'text-red-400' : 'text-amber-400'}" />
                    <span class="font-mono text-sm font-bold text-[var(--color-text)]">Gerät ID: {dev.device_id}</span>
                  </div>
                  <span class="text-[10px] uppercase font-bold px-2 py-0.5 rounded {dev.state === 'red' ? 'bg-red-500/10 text-red-400' : 'bg-amber-500/10 text-amber-400'}">
                    {dev.state === 'red' ? 'Ausfall' : 'Degradiert'}
                  </span>
                </div>
                
                <div class="mt-3 space-y-1.5">
                  {#each dev.reasons as reason}
                    <div class="text-xs text-[var(--color-text2)] flex items-start gap-2">
                      <AlertTriangle class="w-3.5 h-3.5 mt-0.5 shrink-0 {dev.state === 'red' ? 'text-red-500/70' : 'text-amber-500/70'}" />
                      <span>{reason}</span>
                    </div>
                  {/each}
                </div>
              </div>
            {/each}
            {#if result.affected_devices.length === 0}
              <div class="col-span-full py-12 flex flex-col items-center justify-center text-[var(--color-text3)] border border-dashed border-[var(--color-border2)]/50 rounded-2xl">
                <Power class="w-8 h-8 mb-3 text-emerald-500/50" />
                <p>Keine Geräte von diesem Ausfall betroffen.</p>
              </div>
            {/if}
          </div>
        </div>

      {:else if activeTab === 'shutdown' || activeTab === 'boot'}
        {@const timeline = activeTab === 'shutdown' ? result.shutdown_timeline : result.boot_timeline}
        <div class="relative py-8">
          <!-- Horizontal Line -->
          <div class="absolute top-1/2 left-0 right-0 h-1 bg-[var(--color-border)] -translate-y-1/2 rounded-full"></div>
          
          <div class="flex items-center gap-8 overflow-x-auto pb-8 pt-8 px-4 snap-x">
            {#each timeline as ev, i}
              <div class="relative flex flex-col items-center min-w-[200px] snap-center group">
                <!-- Timeline Dot -->
                <div class="w-4 h-4 rounded-full border-4 border-[var(--color-border2)] {ev.warning ? 'bg-red-500' : 'bg-[#1D9E75]'} z-10 relative shadow-[0_0_15px_rgba(29,158,117,0.5)] group-hover:scale-125 transition-transform duration-300"></div>
                
                <!-- Time Label -->
                <div class="absolute -top-10 text-xs font-mono font-bold text-[var(--color-text)] bg-[var(--color-border2)] px-2.5 py-1 rounded-md border border-[var(--color-border2)]">
                  T + {formatSeconds(ev.time_seconds)}
                </div>

                <!-- Event Card -->
                <div class="absolute top-10 w-full bg-[var(--color-bg3)] border border-[var(--color-border2)]/50 p-4 rounded-xl shadow-lg backdrop-blur-sm group-hover:border-[#1D9E75]/50 transition-colors">
                  <div class="text-[10px] uppercase text-[var(--color-text3)] font-bold tracking-wider mb-1 flex items-center gap-1">
                    <Clock class="w-3 h-3" />
                    {ev.method}
                  </div>
                  <div class="text-sm text-[var(--color-text)] font-medium leading-tight">
                    {ev.message}
                  </div>
                  {#if ev.warning}
                    <div class="mt-2 text-[10px] text-red-400 flex items-center gap-1">
                      <AlertTriangle class="w-3 h-3" /> Warnung: Kritischer Pfad
                    </div>
                  {/if}
                </div>
              </div>
            {/each}
            {#if timeline.length === 0}
              <div class="w-full text-center text-[var(--color-text3)] py-12 relative z-10">Keine Sequenz generiert.</div>
            {/if}
          </div>
        </div>
      {/if}
    </div>
  </div>
</div>
{/if}

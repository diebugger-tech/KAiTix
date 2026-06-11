<script lang="ts">
  import { onMount } from 'svelte';
  import { api, type Rack, type ShutdownSimResult, type ShutdownTimelinePoint, type ShutdownDeviceStatus } from '$lib/api';
  import {
    Play, Pause, RotateCcw, Server, AlertTriangle, CheckCircle,
    XCircle, Battery, Clock, Zap, ChevronDown, FastForward,
  } from '@lucide/svelte';

  // --- State ---
  let simResult = $state<ShutdownSimResult | null>(null);
  let isLoading = $state(false);
  let error = $state('');

  // Battery config
  let batType = $state('vrla');
  let batSeries = $state(4);
  let batParallel = $state(1);
  let batBlockV = $state(12);
  let batBlockAh = $state(100);
  let batAge = $state(0);
  let batTemp = $state(20);
  let batEff = $state(0.90);
  let showConfig = $state(false);

  // Playback state
  let playbackIdx = $state(0);
  let isPlaying = $state(false);
  let playbackSpeed = $state(1);
  let playbackTimer: ReturnType<typeof setInterval> | null = null;

  const batteryTypeOptions = [
    { value: 'vrla', label: 'VRLA (Blei-Säure)' },
    { value: 'bleisaeure', label: 'Blei-Säure (offen)' },
    { value: 'lfp', label: 'LFP (Lithium)' },
    { value: 'li_ion_nmc', label: 'Li-Ion NMC' },
  ];

  // --- Derived ---
  const currentSnapshot = $derived(
    simResult && simResult.timeline.length > 0
      ? simResult.timeline[Math.min(playbackIdx, simResult.timeline.length - 1)]
      : null
  );

  const totalDuration = $derived(
    simResult && simResult.timeline.length > 0
      ? simResult.timeline[simResult.timeline.length - 1].time_seconds
      : 0
  );

  const crashedCount = $derived(
    simResult ? simResult.device_statuses.filter(d => d.crashed).length : 0
  );

  const safeCount = $derived(
    simResult ? simResult.device_statuses.filter(d => !d.crashed).length : 0
  );

  // Priority labels
  function priorityLabel(p: number): string {
    switch (p) {
      case 1: return 'Kritisch';
      case 2: return 'Standard';
      case 3: return 'Unkritisch';
      case 4: return 'Zuerst aus';
      default: return `P${p}`;
    }
  }

  function priorityColor(p: number): string {
    switch (p) {
      case 1: return 'text-red-400 bg-red-500/10 border-red-500/30';
      case 2: return 'text-[#5DCAA5] bg-[rgba(29,158,117,0.15)] border-[rgba(29,158,117,0.3)]';
      case 3: return 'text-amber-400 bg-amber-500/10 border-amber-500/30';
      case 4: return 'text-[var(--color-text2)] bg-[var(--color-border2)] border-[var(--color-border)]';
      default: return 'text-[var(--color-text2)] bg-[var(--color-border2)] border-[var(--color-border)]';
    }
  }

  function formatSeconds(s: number): string {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    if (m >= 60) {
      const h = Math.floor(m / 60);
      const rm = m % 60;
      return `${h}h ${rm}m`;
    }
    return sec > 0 ? `${m}m ${sec}s` : `${m}m`;
  }

  function socColor(pct: number): string {
    if (pct > 50) return '#22c55e';
    if (pct > 25) return '#f59e0b';
    if (pct > 10) return '#ef4444';
    return '#991b1b';
  }

  // --- Actions ---
  async function runShutdown() {
    isLoading = true;
    error = '';
    stopPlayback();
    playbackIdx = 0;
    try {
      simResult = await api.simulateShutdown({
        battery_type: batType,
        series_blocks: batSeries,
        parallel_strings: batParallel,
        block_voltage_v: batBlockV,
        block_capacity_ah: batBlockAh,
        age_years: batAge,
        temperature_c: batTemp,
        inverter_efficiency: batEff,
      });
    } catch (e: any) {
      error = e.message || 'Fehler bei Shutdown-Simulation';
    } finally {
      isLoading = false;
    }
  }

  function startPlayback() {
    if (!simResult || simResult.timeline.length === 0) return;
    if (playbackIdx >= simResult.timeline.length - 1) playbackIdx = 0;
    isPlaying = true;
    playbackTimer = setInterval(() => {
      if (simResult && playbackIdx < simResult.timeline.length - 1) {
        playbackIdx++;
      } else {
        stopPlayback();
      }
    }, 200 / playbackSpeed);
  }

  function stopPlayback() {
    isPlaying = false;
    if (playbackTimer) {
      clearInterval(playbackTimer);
      playbackTimer = null;
    }
  }

  function togglePlayback() {
    if (isPlaying) stopPlayback();
    else startPlayback();
  }

  function resetPlayback() {
    stopPlayback();
    playbackIdx = 0;
  }

  function isDeviceActiveAt(dev: ShutdownDeviceStatus, timeIdx: number): boolean {
    if (!simResult || !currentSnapshot) return true;
    return currentSnapshot.active_device_ids.includes(dev.id);
  }

  // --- SVG Chart ---
  const chartW = 580, chartH = 120, padL = 45, padR = 10, padT = 10, padB = 25;
  const innerW = chartW - padL - padR;
  const innerH = chartH - padT - padB;

  function socPath(timeline: ShutdownTimelinePoint[]): string {
    if (timeline.length === 0) return '';
    const maxT = timeline[timeline.length - 1].time_seconds || 1;
    let d = '';
    for (let i = 0; i < timeline.length; i++) {
      const x = padL + (timeline[i].time_seconds / maxT) * innerW;
      const y = padT + innerH - (timeline[i].soc_pct / 100) * innerH;
      d += i === 0 ? `M${x},${y}` : `L${x},${y}`;
    }
    return d;
  }

  function socAreaPath(timeline: ShutdownTimelinePoint[]): string {
    if (timeline.length === 0) return '';
    const maxT = timeline[timeline.length - 1].time_seconds || 1;
    let d = `M${padL},${padT + innerH}`;
    for (let i = 0; i < timeline.length; i++) {
      const x = padL + (timeline[i].time_seconds / maxT) * innerW;
      const y = padT + innerH - (timeline[i].soc_pct / 100) * innerH;
      d += `L${x},${y}`;
    }
    d += `L${padL + (timeline[timeline.length - 1].time_seconds / maxT) * innerW},${padT + innerH}Z`;
    return d;
  }

  function playheadX(timeline: ShutdownTimelinePoint[], idx: number): number {
    if (timeline.length === 0) return padL;
    const maxT = timeline[timeline.length - 1].time_seconds || 1;
    const t = timeline[Math.min(idx, timeline.length - 1)].time_seconds;
    return padL + (t / maxT) * innerW;
  }

  // Shutdown event markers (step changes in load)
  function shutdownMarkers(timeline: ShutdownTimelinePoint[]): Array<{ x: number; time_seconds: number }> {
    if (timeline.length < 2) return [];
    const maxT = timeline[timeline.length - 1].time_seconds || 1;
    const markers: Array<{ x: number; time_seconds: number }> = [];
    for (let i = 1; i < timeline.length; i++) {
      if (timeline[i].active_device_ids.length < timeline[i - 1].active_device_ids.length) {
        markers.push({
          x: padL + (timeline[i].time_seconds / maxT) * innerW,
          time_seconds: timeline[i].time_seconds,
        });
      }
    }
    return markers;
  }

  onMount(() => {
    runShutdown();
    return () => { if (playbackTimer) clearInterval(playbackTimer); };
  });
</script>

<div class="space-y-6">
  <!-- Config bar -->
  <div class="bg-[var(--color-bg2)] border border-[var(--color-border2)]/50 rounded-xl p-4">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div class="flex items-center space-x-2">
        <Server class="w-5 h-5 text-[#5DCAA5]" />
        <h3 class="text-sm font-semibold text-[var(--color-text)]">RZ-weiter Shutdown-Plan</h3>
        <span class="text-xs text-[var(--color-text3)] ml-2">Basierend auf Server-Priorität</span>
      </div>

      <div class="flex items-center gap-3">
        <button onclick={() => showConfig = !showConfig}
          class="flex items-center space-x-1 text-xs text-[var(--color-text2)] hover:text-[var(--color-text)] transition px-3 py-2 border border-[var(--color-border2)] rounded-lg">
          <Battery class="w-3.5 h-3.5" />
          <span>Batterie-Konfiguration</span>
          <ChevronDown class="w-3 h-3 transition-transform {showConfig ? 'rotate-180' : ''}" />
        </button>

        <button onclick={runShutdown} disabled={isLoading}
          class="px-5 py-2 rounded-lg text-sm font-medium transition
            {!isLoading
              ? 'bg-gradient-to-r from-amber-600 to-orange-600 text-[var(--color-text)] hover:from-amber-500 hover:to-orange-500 shadow-lg shadow-amber-900/30'
              : 'bg-[var(--color-border2)] text-[var(--color-text2)] cursor-not-allowed'}">
          {#if isLoading}
            <span class="animate-spin inline-block mr-1">⏳</span> Simuliere…
          {:else}
            <Zap class="w-4 h-4 inline mr-1" /> Shutdown simulieren
          {/if}
        </button>
      </div>
    </div>

    {#if showConfig}
      <div class="mt-4 pt-4 border-t border-[var(--color-border2)]/50 grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div>
          <div class="block text-xs text-[var(--color-text3)] mb-1">Batterietyp</div>
          <select bind:value={batType} class="w-full bg-[var(--color-bg2)] border border-[var(--color-border2)] rounded px-2 py-1.5 text-xs text-[var(--color-text)]">
            {#each batteryTypeOptions as opt}
              <option value={opt.value}>{opt.label}</option>
            {/each}
          </select>
        </div>
        <div>
          <div class="block text-xs text-[var(--color-text3)] mb-1">Seriell × Parallel</div>
          <div class="flex space-x-1">
            <input type="number" bind:value={batSeries} min="1" class="w-1/2 bg-[var(--color-bg2)] border border-[var(--color-border2)] rounded px-2 py-1.5 text-xs text-[var(--color-text)]" />
            <input type="number" bind:value={batParallel} min="1" class="w-1/2 bg-[var(--color-bg2)] border border-[var(--color-border2)] rounded px-2 py-1.5 text-xs text-[var(--color-text)]" />
          </div>
        </div>
        <div>
          <div class="block text-xs text-[var(--color-text3)] mb-1">Block V / Ah</div>
          <div class="flex space-x-1">
            <input type="number" bind:value={batBlockV} min="1" class="w-1/2 bg-[var(--color-bg2)] border border-[var(--color-border2)] rounded px-2 py-1.5 text-xs text-[var(--color-text)]" />
            <input type="number" bind:value={batBlockAh} min="1" class="w-1/2 bg-[var(--color-bg2)] border border-[var(--color-border2)] rounded px-2 py-1.5 text-xs text-[var(--color-text)]" />
          </div>
        </div>
        <div>
          <div class="block text-xs text-[var(--color-text3)] mb-1">Alter / Temp</div>
          <div class="flex space-x-1">
            <input type="number" bind:value={batAge} min="0" step="0.5" class="w-1/2 bg-[var(--color-bg2)] border border-[var(--color-border2)] rounded px-2 py-1.5 text-xs text-[var(--color-text)]" />
            <input type="number" bind:value={batTemp} min="-20" class="w-1/2 bg-[var(--color-bg2)] border border-[var(--color-border2)] rounded px-2 py-1.5 text-xs text-[var(--color-text)]" />
          </div>
        </div>
      </div>
    {/if}
  </div>

  {#if error}
    <div class="px-4 py-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm flex items-center space-x-2">
      <XCircle class="w-4 h-4 shrink-0" /><span>{error}</span>
    </div>
  {/if}

  {#if simResult}
    <!-- Summary Cards -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <div class="bg-[var(--color-bg2)] border border-[var(--color-border2)]/50 rounded-xl p-4">
        <div class="text-xs text-[var(--color-text3)] mb-1">Batterie-Kapazität</div>
        <div class="text-lg font-bold text-emerald-400">{simResult.battery_summary.effective_capacity_ah.toFixed(0)} Ah</div>
        <div class="text-xs text-[var(--color-text3)]">{simResult.battery_summary.total_voltage_v}V System</div>
      </div>
      <div class="bg-[var(--color-bg2)] border border-[var(--color-border2)]/50 rounded-xl p-4">
        <div class="text-xs text-[var(--color-text3)] mb-1">Gesamtdauer</div>
        <div class="text-lg font-bold text-[#5DCAA5]">{formatSeconds(totalDuration)}</div>
        <div class="text-xs text-[var(--color-text3)]">{simResult.timeline.length} Datenpunkte</div>
      </div>
      <div class="bg-[var(--color-bg2)] border border-[var(--color-border2)]/50 rounded-xl p-4">
        <div class="text-xs text-[var(--color-text3)] mb-1">Sicher heruntergefahren</div>
        <div class="text-lg font-bold text-emerald-400">{safeCount}</div>
        <div class="text-xs text-[var(--color-text3)]">Geräte korrekt aus</div>
      </div>
      <div class="bg-[var(--color-bg2)] border border-[var(--color-border2)]/50 rounded-xl p-4">
        <div class="text-xs text-[var(--color-text3)] mb-1">Abgestürzt</div>
        <div class="text-lg font-bold {crashedCount > 0 ? 'text-red-400' : 'text-emerald-400'}">{crashedCount}</div>
        <div class="text-xs text-[var(--color-text3)]">{crashedCount > 0 ? '⚠ Datenverlust möglich' : 'Alles sicher'}</div>
      </div>
    </div>

    <!-- SOC Timeline Chart -->
    <div class="bg-[var(--color-bg2)] border border-[var(--color-border2)]/50 rounded-xl p-4">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-sm font-semibold text-[var(--color-text)]">Batterie-Entladekurve & Shutdown-Ablauf</h3>
        <div class="flex items-center space-x-2">
          <!-- Speed -->
          <div class="flex items-center space-x-1 text-xs text-[var(--color-text2)]">
            <FastForward class="w-3 h-3" />
            <select bind:value={playbackSpeed} onchange={() => { const was = isPlaying; stopPlayback(); if (was) startPlayback(); }}
              class="bg-[var(--color-bg2)] border border-[var(--color-border2)] rounded px-1 py-0.5 text-xs text-[var(--color-text)]">
              <option value={0.5}>0.5×</option>
              <option value={1}>1×</option>
              <option value={2}>2×</option>
              <option value={4}>4×</option>
            </select>
          </div>
          <!-- Playback controls -->
          <button onclick={resetPlayback} class="p-1.5 rounded-lg text-[var(--color-text2)] hover:text-[var(--color-text)] hover:bg-[var(--color-border2)] transition">
            <RotateCcw class="w-4 h-4" />
          </button>
          <button onclick={togglePlayback}
            class="p-1.5 rounded-lg transition
              {isPlaying ? 'bg-amber-500/20 text-amber-400' : 'bg-emerald-500/20 text-emerald-400'} hover:opacity-80">
            {#if isPlaying}
              <Pause class="w-4 h-4" />
            {:else}
              <Play class="w-4 h-4" />
            {/if}
          </button>
        </div>
      </div>

      <!-- SVG Chart -->
      <svg viewBox="0 0 {chartW} {chartH}" class="w-full" style="max-height: 160px;">
        <!-- Grid lines -->
        {#each [0, 25, 50, 75, 100] as pct}
          <line x1={padL} y1={padT + innerH - (pct / 100) * innerH}
                x2={padL + innerW} y2={padT + innerH - (pct / 100) * innerH}
                stroke="#334155" stroke-width="0.5" stroke-dasharray="4,4" />
          <text x={padL - 5} y={padT + innerH - (pct / 100) * innerH + 3}
                fill="#64748b" font-size="9" text-anchor="end">{pct}%</text>
        {/each}

        <!-- Area fill gradient -->
        <defs>
          <linearGradient id="socGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#22c55e" stop-opacity="0.3" />
            <stop offset="100%" stop-color="#22c55e" stop-opacity="0.02" />
          </linearGradient>
        </defs>

        <!-- SOC area -->
        <path d={socAreaPath(simResult.timeline)} fill="url(#socGrad)" />
        <!-- SOC line -->
        <path d={socPath(simResult.timeline)} fill="none" stroke="#22c55e" stroke-width="2" />

        <!-- Shutdown markers -->
        {#each shutdownMarkers(simResult.timeline) as marker}
          <line x1={marker.x} y1={padT} x2={marker.x} y2={padT + innerH}
                stroke="#f59e0b" stroke-width="1" stroke-dasharray="3,3" opacity="0.6" />
        {/each}

        <!-- Playhead -->
        <line x1={playheadX(simResult.timeline, playbackIdx)} y1={padT}
              x2={playheadX(simResult.timeline, playbackIdx)} y2={padT + innerH}
              stroke="#e2e8f0" stroke-width="1.5" opacity="0.8" />
        <circle cx={playheadX(simResult.timeline, playbackIdx)}
                cy={padT + innerH - ((currentSnapshot?.soc_pct ?? 0) / 100) * innerH}
                r="4" fill="#e2e8f0" stroke="#111827" stroke-width="2" />
      </svg>

      <!-- Timeline slider -->
      <input type="range" min="0" max={simResult.timeline.length - 1} bind:value={playbackIdx}
        oninput={() => stopPlayback()}
        class="w-full mt-2 accent-amber-500" />

      <!-- Current stats -->
      {#if currentSnapshot}
        <div class="flex flex-wrap gap-4 mt-3 text-xs">
          <div class="flex items-center space-x-1.5">
            <Clock class="w-3.5 h-3.5 text-[var(--color-text2)]" />
            <span class="text-[var(--color-text)] font-medium">{formatSeconds(currentSnapshot.time_seconds)}</span>
          </div>
          <div class="flex items-center space-x-1.5">
            <Battery class="w-3.5 h-3.5" style="color: {socColor(currentSnapshot.soc_pct)}" />
            <span class="font-medium" style="color: {socColor(currentSnapshot.soc_pct)}">{currentSnapshot.soc_pct.toFixed(1)}%</span>
          </div>
          <div class="flex items-center space-x-1.5">
            <Zap class="w-3.5 h-3.5 text-amber-400" />
            <span class="text-[var(--color-text)]">{currentSnapshot.load_kw.toFixed(2)} kW Last</span>
          </div>
          <div class="flex items-center space-x-1.5">
            <Server class="w-3.5 h-3.5 text-[#5DCAA5]" />
            <span class="text-[var(--color-text)]">{currentSnapshot.active_device_ids.length} aktiv</span>
          </div>
          <div class="flex items-center space-x-1.5">
            <Clock class="w-3.5 h-3.5 text-emerald-400" />
            <span class="text-[var(--color-text)]">~{currentSnapshot.remaining_runtime_min.toFixed(1)} min verbleibend</span>
          </div>
        </div>
      {/if}
    </div>

    <!-- Device Status Cards -->
    <div class="bg-[var(--color-bg2)] border border-[var(--color-border2)]/50 rounded-xl p-4">
      <h3 class="text-sm font-semibold text-[var(--color-text)] mb-3">Geräte-Status (Shutdown-Reihenfolge)</h3>
      <div class="grid gap-2">
        {#each simResult.device_statuses.sort((a, b) => a.shutdown_delay_seconds - b.shutdown_delay_seconds) as dev}
          {@const isActive = currentSnapshot ? currentSnapshot.active_device_ids.includes(dev.id) : true}
          <div class="flex items-center justify-between px-3 py-2.5 rounded-lg border transition-all duration-300
            {dev.crashed
              ? 'bg-red-950/30 border-red-500/30'
              : isActive
                ? 'bg-emerald-950/20 border-emerald-500/30'
                : 'bg-[var(--color-border2)] border-[var(--color-border2)]/30 opacity-60'}">
            <div class="flex items-center space-x-3">
              <div class="w-2 h-2 rounded-full transition-colors duration-300
                {dev.crashed ? 'bg-red-500 animate-pulse' : isActive ? 'bg-emerald-500' : 'bg-[var(--color-border2)]'}"></div>
              <div>
                <span class="text-sm font-medium text-[var(--color-text)]">{dev.hostname}</span>
                <span class="text-xs text-[var(--color-text3)] ml-2">{dev.tdp_watt}W</span>
              </div>
            </div>
            <div class="flex items-center space-x-3 text-xs">
              <span class="px-2 py-0.5 rounded border {priorityColor(dev.shutdown_priority)}">
                {priorityLabel(dev.shutdown_priority)}
              </span>
              <span class="text-[var(--color-text2)]">
                {dev.shutdown_delay_seconds > 0 ? `Aus nach ${formatSeconds(dev.shutdown_delay_seconds)}` : 'Sofort aus'}
              </span>
              {#if dev.crashed}
                <span class="flex items-center space-x-1 text-red-400">
                  <XCircle class="w-3.5 h-3.5" />
                  <span>{dev.crash_reason}</span>
                </span>
              {:else if !isActive}
                <span class="flex items-center space-x-1 text-emerald-400">
                  <CheckCircle class="w-3.5 h-3.5" />
                  <span>Sicher aus</span>
                </span>
              {:else}
                <span class="text-[#5DCAA5]">Läuft</span>
              {/if}
            </div>
          </div>
        {/each}
      </div>
    </div>
  {:else if !isLoading}
    <!-- Empty state -->
    <div class="bg-[var(--color-bg2)] border border-[var(--color-border2)]/50 rounded-xl p-8 text-center">
      <Server class="w-12 h-12 mx-auto text-[var(--color-text3)] mb-3" />
      <h3 class="text-sm font-semibold text-[var(--color-text)] mb-1">Globale Shutdown-Simulation</h3>
      <p class="text-xs text-[var(--color-text3)] max-w-md mx-auto">
        Die Simulation zeigt den kontrollierten Shutdown-Ablauf über alle Standorte bei Stromausfall.
        Die Priorisierung erfolgt server-basiert (kritisch vs. unkritisch).
      </p>
      <p class="text-xs text-[var(--color-text3)] mt-3">
        💡 Tipp: Konfiguriere <code class="text-amber-400/60">shutdown_priority</code> und
        <code class="text-amber-400/60">shutdown_delay_seconds</code> in den Geräte-Einstellungen.
      </p>
    </div>
  {/if}
</div>

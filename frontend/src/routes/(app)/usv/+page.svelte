<script lang="ts">
  import { onMount } from 'svelte';
  import { api, type HardwareType, type SystemState, type USVSimulationEvent, type RuntimeCurveData, type DimensioningResult, type SimulationResult } from '$lib/api';
  import ShutdownSimulator from '$lib/components/ShutdownSimulator.svelte';
  import SimulationTimeline from '$lib/components/SimulationTimeline.svelte';
  import {
    Zap, Battery, AlertTriangle, RefreshCw, Activity, Gauge,
    CircleCheck, CircleAlert, CircleX, Power, ChevronDown, ChevronUp,
    Layers, Wrench, TrendingUp, Cpu, Thermometer, Clock,
  } from '@lucide/svelte';

  // --- Tab state ---
  let activeTab = $state<'simulation' | 'battery' | 'schaltbild' | 'shutdown_sequence'>('simulation');

  // --- Topology Simulation ---
  let topologySimResult = $state<SimulationResult | null>(null);
  let isTopologySimulating = $state(false);

  async function triggerScenario(type: string, name: string) {
    isTopologySimulating = true;
    error = '';
    try {
      topologySimResult = await api.runSimulation({ target_type: type, target_name: name });
    } catch (e: any) {
      error = e.message || 'Simulation failed';
    } finally {
      isTopologySimulating = false;
    }
  }

  // --- Simulation state ---
  let l1_kw = $state(4);
  let l2_kw = $state(3);
  let l3_kw = $state(5);
  let module_capacity_kw = $state(10);
  let module_count = $state(3);
  let battery_voltage = $state(48);
  let battery_capacity_ah = $state(100);
  let peukert_exponent = $state(1.2);
  let inverter_efficiency = $state(0.90);

  let systemState = $state<SystemState | null>(null);
  let events = $state<USVSimulationEvent[]>([]);
  let isLoading = $state(false);
  let error = $state('');
  let showBatterySettings = $state(false);

  // Template selection
  let usvModels = $state<HardwareType[]>([]);
  let hwTemplateId = $state(0);
  let templateHint = $state('');

  // --- Battery cabinet state ---
  let batType = $state('vrla');
  let batSeries = $state(4);
  let batParallel = $state(1);
  let batBlockV = $state(12);
  let batBlockAh = $state(100);
  let batAge = $state(0);
  let batTemp = $state(20);
  let batEff = $state(0.90);

  let runtimeCurve = $state<RuntimeCurveData | null>(null);
  let batteryLoading = $state(false);

  // --- Dimensioning state ---
  let dimLoad = $state(12);
  let dimTargetMin = $state(30);
  let dimType = $state('vrla');
  let dimResult = $state<DimensioningResult | null>(null);
  let dimLoading = $state(false);

  // --- Derived ---
  const batteryTypeOptions = [
    { value: 'vrla', label: 'VRLA (Ventilgeregelte Blei-Säure)' },
    { value: 'bleisaeure', label: 'Blei-Säure (offen)' },
    { value: 'lfp', label: 'LFP (Lithium-Eisenphosphat)' },
    { value: 'li_ion_nmc', label: 'Li-Ion NMC/NCA' },
  ];

  const batteryWarnings = $derived.by(() => {
    const warns = [];
    if (batType === 'vrla' && batTemp > 25) warns.push("⚠ Lebensdauer stark verkürzt");
    if (batType === 'lfp' && batTemp < 5) warns.push("⚠ Reduzierte Leistung unter 5°C");
    if (batType === 'vrla' && batAge > 5) warns.push("⚠ Batterietausch prüfen (5-7 Jahre Lebensdauer)");
    if (batType === 'lfp' && batAge > 10) warns.push("⚠ Kapazitätsprüfung empfohlen (>5000 Zyklen)");
    if (batType === 'li_ion_nmc') warns.push("⚠ Brandschutzkonzept für Batterieraum prüfen");
    return warns;
  });

  const batteryDischargeCurrent = $derived(systemState ? Math.round((systemState.total_load_kw * 1000) / (systemState.battery_voltage * systemState.inverter_efficiency)) : 0);
  const cableSection = $derived(Math.ceil(batteryDischargeCurrent / 5));

  // --- Simulation actions ---
  async function runSimulation() {
    isLoading = true; error = '';
    try {
      const res = await api.simulateUsvFault({
        fault_type: 'reset', l1_kw, l2_kw, l3_kw,
        module_capacity_kw, installed_modules_count: module_count,
        battery_voltage, battery_capacity_ah, peukert_exponent, inverter_efficiency,
      });
      systemState = res.system_state;
      events = [res.event, ...events];
    } catch (e: any) { error = e.message || 'Fehler bei der Simulation'; }
    finally { isLoading = false; }
  }

  async function injectFault(faultType: string) {
    if (!systemState) return;
    isLoading = true; error = '';
    try {
      const res = await api.simulateUsvFault({
        fault_type: faultType, l1_kw, l2_kw, l3_kw,
        module_capacity_kw, installed_modules_count: module_count,
        system_state: systemState,
        battery_voltage, battery_capacity_ah, peukert_exponent, inverter_efficiency,
      });
      systemState = res.system_state;
      events = [res.event, ...events];
    } catch (e: any) { error = e.message || 'Fehler beim Fehler-Injekt'; }
    finally { isLoading = false; }
  }

  // --- Battery actions ---
  async function loadRuntimeCurve() {
    batteryLoading = true; error = '';
    try {
      runtimeCurve = await api.getRuntimeCurve({
        l1_kw, l2_kw, l3_kw,
        module_capacity_kw, installed_modules_count: module_count,
        battery_type: batType,
        series_blocks: batSeries, parallel_strings: batParallel,
        block_voltage_v: batBlockV, block_capacity_ah: batBlockAh,
        age_years: batAge, temperature_c: batTemp,
        inverter_efficiency: batEff,
      });
    } catch (e: any) { error = e.message || 'Fehler beim Laden der Runtime-Kurve'; }
    finally { batteryLoading = false; }
  }

  async function runDimensioning() {
    dimLoading = true; error = '';
    try {
      dimResult = await api.getDimensioning({
        load_kw: dimLoad, target_runtime_min: dimTargetMin,
        battery_type: dimType,
        block_voltage_v: batBlockV, block_capacity_ah: batBlockAh,
        inverter_efficiency: batEff,
      });
    } catch (e: any) { error = e.message || 'Fehler bei der Dimensionierung'; }
    finally { dimLoading = false; }
  }

  $effect(() => { if (error) { const t = setTimeout(() => (error = ''), 5000); return () => clearTimeout(t); } });

  onMount(async () => {
    try { usvModels = await api.getHardware('usv'); } catch { /* ignore */ }
  });

  $effect(() => {
    if (hwTemplateId > 0) {
      const hw = usvModels.find(m => m.id === hwTemplateId);
      if (hw) {
        module_count = hw.psu_count ?? 1;
        module_capacity_kw = (hw.psu_nennwatt ?? 10000) / 1000;
        
        if (hw.hersteller === 'Wöhrle SVS') {
          batType = 'lfp';
          batBlockV = 48;
          batSeries = 1;
          batParallel = 1;
          batBlockAh = 50;
          peukert_exponent = 1.05;
          batTemp = 25;
          templateHint = 'Wöhrle WP-LFP — 5000 Zyklen, 10-15 Jahre Lebensdauer';
          battery_voltage = batSeries * batBlockV;
          battery_capacity_ah = batParallel * batBlockAh;
        } else if (hw.hersteller === 'Eaton' && hw.name.includes('93PM')) {
          batType = 'vrla';
          batBlockV = 12;
          batSeries = 36;
          batParallel = 1;
          batBlockAh = 100;
          peukert_exponent = 1.2;
          batTemp = 22;
          templateHint = 'Eaton VRLA — 36 Blöcke à 12V, Belüftung 1.3m³/h erforderlich';
          battery_voltage = batSeries * batBlockV;
          battery_capacity_ah = batParallel * batBlockAh;
        } else if (hw.hersteller === 'Eaton' && hw.name.includes('93PS')) {
          batType = 'vrla';
          batBlockV = 12;
          batSeries = 20;
          batParallel = 1;
          batBlockAh = 100;
          peukert_exponent = 1.2;
          batTemp = 22;
          templateHint = 'Eaton 93PS VRLA, integrierte Batterien';
          battery_voltage = batSeries * batBlockV;
          battery_capacity_ah = batParallel * batBlockAh;
        } else {
          batType = 'vrla';
          batBlockV = 12;
          batSeries = 4;
          batParallel = 1;
          batBlockAh = 100;
          peukert_exponent = 1.2;
          batTemp = 20;
          templateHint = '';
          battery_voltage = batSeries * batBlockV;
          battery_capacity_ah = batParallel * batBlockAh;
        }
      }
    } else {
      batType = 'vrla';
      batBlockV = 12;
      batSeries = 4;
      batParallel = 1;
      batBlockAh = 100;
      peukert_exponent = 1.2;
      batTemp = 20;
      templateHint = '';
      battery_voltage = batSeries * batBlockV;
      battery_capacity_ah = batParallel * batBlockAh;
    }
  });

  function isNonModular(hw: HardwareType): boolean {
    return (hw.bemerkung ?? '').includes('nicht modular');
  }

  function hasWarning(hw: HardwareType): boolean {
    return (hw.bemerkung ?? '').includes('⚠');
  }

  function isRecommended(hw: HardwareType): boolean {
    return (hw.bemerkung ?? '').includes('empfohlen');
  }

  function extractModulesDesc(hw: HardwareType): string {
    const m = (hw.bemerkung ?? '').match(/(\d+×\s*\d+\s*kW[^✓⚠]*)/);
    return m ? m[1].trim() : '';
  }

  const usvGroups = $derived.by(() => {
    const groups: Record<string, HardwareType[]> = {};
    for (const hw of usvModels) {
      const mfr = hw.hersteller || 'Sonstige';
      if (!groups[mfr]) groups[mfr] = [];
      groups[mfr].push(hw);
    }
    return groups;
  });

  function statusLabel(s: SystemState | RuntimeCurveData): string {
    if ('status' in s) {
      if (s.status === 'stable') return 'STABIL';
      if (s.status === 'degraded') return 'BEEINTRÄCHTIGT';
      return 'KRITISCH';
    }
    return s.n1_safe ? 'SICHER' : 'UNSICHER';
  }

  function severityClass(sev: string): string {
    if (sev === 'critical') return 'text-red-400 bg-red-500/10 border-red-500/30';
    if (sev === 'warning') return 'text-amber-400 bg-amber-500/10 border-amber-500/30';
    return 'text-slate-400 bg-slate-500/10 border-slate-500/30';
  }

  function formatTime(ts: string): string {
    const iso = ts.endsWith('Z') || ts.includes('+') ? ts : ts + 'Z';
    return new Date(iso).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }

  function loadPct(): number {
    if (!systemState || systemState.installed_kw <= 0) return 0;
    return Math.min(100, Math.round((systemState.total_load_kw / systemState.installed_kw) * 100));
  }

  // Runtime curve SVG coords
  const svgWidth = 560, svgHeight = 200, padL = 50, padR = 20, padT = 15, padB = 30;
  const chartW = svgWidth - padL - padR, chartH = svgHeight - padT - padB;

  function curvePath(curve: Array<{load_kw: number; runtime_min: number}>, maxX: number, maxY: number): string {
    if (curve.length === 0) return '';
    let d = '';
    for (let i = 0; i < curve.length; i++) {
      const x = padL + (curve[i].load_kw / maxX) * chartW;
      const y = padT + chartH - (curve[i].runtime_min / maxY) * chartH;
      d += i === 0 ? `M${x},${y}` : `L${x},${y}`;
    }
    return d;
  }
</script>

<div class="h-full">
  {#if error}
    <div class="mb-6 px-4 py-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm flex items-center space-x-2">
      <CircleX class="w-4 h-4 shrink-0" /><span>{error}</span>
    </div>
  {/if}

  <!-- Tab Bar -->
  <div class="flex space-x-1 mb-6 bg-[#0d1220] rounded-lg p-1 w-fit border border-slate-800">
    <button
      onclick={() => activeTab = 'simulation'}
      class="px-4 py-2 rounded-md text-sm font-medium transition flex items-center space-x-2
        {activeTab === 'simulation' ? 'bg-[#1D9E75] text-white shadow' : 'text-slate-400 hover:text-slate-200'}"
    >
      <Zap class="w-3.5 h-3.5" /><span>USV N+1 Simulator</span>
    </button>
    <button
      onclick={() => activeTab = 'battery'}
      class="px-4 py-2 rounded-md text-sm font-medium transition flex items-center space-x-2
        {activeTab === 'battery' ? 'bg-emerald-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'}"
    >
      <Battery class="w-3.5 h-3.5" /><span>Batterieschrank</span>
    </button>
    <button
      onclick={() => activeTab = 'schaltbild'}
      class="px-4 py-2 rounded-md text-sm font-medium transition flex items-center space-x-2
        {activeTab === 'schaltbild' ? 'bg-purple-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'}"
    >
      <Layers class="w-3.5 h-3.5" /><span>Stromlaufplan</span>
    </button>
    <button
      onclick={() => activeTab = 'shutdown_sequence'}
      class="px-4 py-2 rounded-md text-sm font-medium transition flex items-center space-x-2
        {activeTab === 'shutdown_sequence' ? 'bg-rose-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'}"
    >
      <Clock class="w-3.5 h-3.5" /><span>Shutdown-Ablauf</span>
    </button>
  </div>

  {#if activeTab === 'simulation'}
    <!-- === USV N+1 SIMULATION TAB === -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Input Panel -->
      <div class="space-y-4">
        <!-- USV Template Selection -->
        <div class="bg-[#131615] border border-slate-800 rounded-xl p-5">
          <h3 class="text-sm font-semibold text-slate-300 flex items-center space-x-2 mb-4">
            <Layers class="w-4 h-4 text-purple-400" /><span>USV-Vorlage</span>
          </h3>
          <select bind:value={hwTemplateId}
            class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-purple-500">
            <option value={0}>— Manuelle Eingabe —</option>
            {#each Object.entries(usvGroups) as [mfr, models]}
              <optgroup label="── {mfr} ──">
                {#each models as hw}
                  <option value={hw.id}>{hw.name} ({extractModulesDesc(hw) || `${hw.psu_count ?? 1}×${(hw.psu_nennwatt ?? 10000) / 1000}kW`}){isRecommended(hw) ? ' ← ✓ empfohlen' : ''}</option>
                {/each}
              </optgroup>
            {/each}
          </select>

          {#if hwTemplateId > 0}
            {@const hw = usvModels.find(m => m.id === hwTemplateId)}
            {#if hw}
              {#if isRecommended(hw)}
                <div class="mt-2 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-xs text-emerald-400 flex items-center space-x-1.5">
                  <CircleCheck class="w-3 h-3" /><span>✓ Empfohlen</span>
                </div>
              {/if}
              {#if hasWarning(hw)}
                <div class="mt-2 px-3 py-1.5 bg-amber-500/10 border border-amber-500/30 rounded-lg text-xs text-amber-400 flex items-center space-x-1.5">
                  <CircleAlert class="w-3 h-3" /><span>⚠ {hw.bemerkung}</span>
                </div>
              {/if}
              {#if isNonModular(hw)}
                <div class="mt-2 px-3 py-1.5 bg-amber-500/10 border border-amber-500/30 rounded-lg text-xs text-amber-400 flex items-center space-x-1.5">
                  <CircleAlert class="w-3 h-3" /><span>⚠ Dieses Modell ist nicht N+1-fähig</span>
                </div>
              {/if}
            {/if}
          {/if}
          <p class="text-[10px] text-slate-600 mt-2">Richtwert — Parameter können angepasst werden</p>
        </div>

        <div class="bg-[#131615] border border-slate-800 rounded-xl p-5">
          <h3 class="text-sm font-semibold text-slate-300 flex items-center space-x-2 mb-4">
            <Gauge class="w-4 h-4 text-blue-400" /><span>Sandbox-Parameter</span>
          </h3>
          <div class="grid grid-cols-3 gap-3 mb-3">
            <div>
              <label class="text-xs text-slate-500 mb-1 block">L1 (kW)</label>
              <input type="number" step="0.1" min="0" bind:value={l1_kw}
                class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]" />
            </div>
            <div>
              <label class="text-xs text-slate-500 mb-1 block">L2 (kW)</label>
              <input type="number" step="0.1" min="0" bind:value={l2_kw}
                class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]" />
            </div>
            <div>
              <label class="text-xs text-slate-500 mb-1 block">L3 (kW)</label>
              <input type="number" step="0.1" min="0" bind:value={l3_kw}
                class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]" />
            </div>
          </div>
          <div class="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label class="text-xs text-slate-500 mb-1 block">Module (Anzahl)</label>
              <input type="number" step="1" min="1" bind:value={module_count}
                class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]" />
            </div>
            <div>
              <label class="text-xs text-slate-500 mb-1 block">Modul-Leistung (kW)</label>
              <input type="number" step="0.5" min="1" bind:value={module_capacity_kw}
                class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]" />
            </div>
          </div>
          <button onclick={() => showBatterySettings = !showBatterySettings}
            class="text-xs text-[#5DCAA5] hover:text-[#86EFCB] mb-2 transition">
            {showBatterySettings ? '▲ Batterie ausblenden' : '▼ Batterie-Einstellungen'}
          </button>
          {#if showBatterySettings}
            <div class="grid grid-cols-2 gap-3 mb-3 p-3 bg-[#181C1A] rounded-lg border border-slate-700">
              <div><label class="text-xs text-slate-500 mb-1 block">Spannung (V)</label><input type="number" step="1" min="12" bind:value={battery_voltage} class="w-full bg-[#0f1720] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]" /></div>
              <div><label class="text-xs text-slate-500 mb-1 block">Kapazität (Ah)</label><input type="number" step="1" min="10" bind:value={battery_capacity_ah} class="w-full bg-[#0f1720] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]" /></div>
              <div><label class="text-xs text-slate-500 mb-1 block">Peukert (k)</label><input type="number" step="0.01" min="1.0" max="1.5" bind:value={peukert_exponent} class="w-full bg-[#0f1720] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]" /></div>
              <div><label class="text-xs text-slate-500 mb-1 block">Wirkungsgrad (η)</label><input type="number" step="0.01" min="0.7" max="1.0" bind:value={inverter_efficiency} class="w-full bg-[#0f1720] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[#1D9E75]" /></div>
            </div>
          {/if}
          <button onclick={runSimulation} disabled={isLoading}
            class="w-full py-2.5 bg-[#1D9E75] hover:bg-[#0F6E56] disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-lg text-sm font-semibold transition flex items-center justify-center space-x-2">
            {#if isLoading}<RefreshCw class="w-4 h-4 animate-spin" /><span>Lädt...</span>{:else}<Activity class="w-4 h-4" /><span>Simulation starten</span>{/if}
          </button>
        </div>

        <!-- Fault Controls -->
        <div class="bg-[#131615] border border-slate-800 rounded-xl p-5">
          <h3 class="text-sm font-semibold text-slate-300 flex items-center space-x-2 mb-4">
            <AlertTriangle class="w-4 h-4 text-orange-400" /><span>Fehler-Simulation</span>
          </h3>
          <div class="space-y-2">
            <button onclick={() => injectFault('grid_failure')} disabled={!systemState || isLoading}
              class="w-full py-2.5 bg-red-500/20 hover:bg-red-500/30 disabled:bg-slate-700/50 disabled:text-slate-600 border border-red-500/30 text-red-400 rounded-lg text-sm font-medium transition flex items-center justify-center space-x-2">
              <Power class="w-4 h-4" /><span>Netzausfall</span></button>
            <button onclick={() => injectFault('battery_defect')} disabled={!systemState || isLoading}
              class="w-full py-2.5 bg-amber-500/20 hover:bg-amber-500/30 disabled:bg-slate-700/50 disabled:text-slate-600 border border-amber-500/30 text-amber-400 rounded-lg text-sm font-medium transition flex items-center justify-center space-x-2">
              <Battery class="w-4 h-4" /><span>Batterie-Defekt</span></button>
            <button onclick={() => injectFault('module_failure')} disabled={!systemState || isLoading || (systemState?.active_modules_count ?? 0) <= 0}
              class="w-full py-2.5 bg-orange-500/20 hover:bg-orange-500/30 disabled:bg-slate-700/50 disabled:text-slate-600 border border-orange-500/30 text-orange-300 rounded-lg text-sm font-medium transition flex items-center justify-center space-x-2">
              <Zap class="w-4 h-4" /><span>Modul-Ausfall</span></button>
            <button onclick={() => injectFault('reset')} disabled={!systemState || isLoading}
              class="w-full py-2.5 bg-slate-500/20 hover:bg-slate-500/30 disabled:bg-slate-700/50 disabled:text-slate-600 border border-slate-500/30 text-slate-400 rounded-lg text-sm font-medium transition flex items-center justify-center space-x-2">
              <RefreshCw class="w-4 h-4" /><span>Reset</span></button>
          </div>
        </div>
      </div>

      <!-- Block Diagram + Results -->
      <div class="lg:col-span-2 space-y-6">
        <div class="bg-[#131615] border border-slate-800 rounded-xl p-6">
          <h3 class="text-sm font-semibold text-slate-300 flex items-center space-x-2 mb-4">
            <Zap class="w-4 h-4 text-yellow-400" /><span>Stromfluss-Diagramm</span>
          </h3>
          {#if systemState}
            <div class="flex items-center justify-center gap-3 py-4 text-sm font-mono flex-wrap">
              <div class="flex flex-col items-center">
                <div class="w-20 h-12 rounded-lg {systemState.grid_online ? 'border-emerald-500/50 bg-emerald-500/10 text-emerald-400' : 'border-red-500/50 bg-red-500/10 text-red-400'} border flex items-center justify-center text-xs font-semibold"><Power class="w-4 h-4" /><span class="ml-1">Netz</span></div>
                <span class="text-[10px] mt-1 {systemState.grid_online ? 'text-emerald-500' : 'text-red-500'}">{systemState.grid_online ? 'ONLINE' : 'AUS'}</span>
              </div>
              <span class="text-slate-600 text-xl">{systemState.grid_online ? '→' : '✕'}</span>
              <div class="flex flex-col items-center"><div class="w-20 h-12 rounded-lg border {systemState.status === 'stable' ? 'border-emerald-500/50 bg-emerald-500/10 text-emerald-400' : systemState.status === 'degraded' ? 'border-amber-500/50 bg-amber-500/10 text-amber-400' : 'border-red-500/50 bg-red-500/10 text-red-400'} flex items-center justify-center text-xs font-semibold">GL</div><span class="text-[10px] text-slate-500 mt-1">Gleichrichter</span></div>
              <span class="text-slate-600 text-xl">→</span>
              <div class="flex flex-col items-center"><div class="w-20 h-12 rounded-lg border {systemState.status === 'stable' ? 'border-emerald-500/50 bg-emerald-500/10 text-emerald-400' : systemState.status === 'degraded' ? 'border-amber-500/50 bg-amber-500/10 text-amber-400' : 'border-red-500/50 bg-red-500/10 text-red-400'} flex items-center justify-center text-xs font-semibold">WR</div><span class="text-[10px] text-slate-500 mt-1">Wechselrichter</span></div>
              <span class="text-slate-600 text-xl">→</span>
              <div class="flex flex-col items-center"><div class="w-20 h-12 rounded-lg border border-slate-600 bg-slate-800/30 text-slate-300 flex items-center justify-center text-xs font-semibold"><Activity class="w-4 h-4" /></div><span class="text-[10px] text-slate-500 mt-1">{systemState.total_load_kw} kW</span></div>
              <div class="flex flex-col items-center mt-6 ml-2"><span class="text-[10px] text-slate-600 mb-1">↕</span><div class="w-20 h-12 rounded-lg border {systemState.battery_soc_pct > 50 ? 'border-emerald-500/50 bg-emerald-500/10 text-emerald-400' : 'border-amber-500/50 bg-amber-500/10 text-amber-400'} flex items-center justify-center text-xs font-semibold"><Battery class="w-4 h-4" /><span class="ml-1">{systemState.battery_soc_pct}%</span></div><span class="text-[10px] text-slate-500 mt-1">Batterie</span></div>
            </div>
            <div class="mt-4 text-center">
              <span class="inline-flex items-center space-x-2 px-4 py-1.5 rounded-full text-xs font-bold
                {systemState.status === 'stable' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : ''}
                {systemState.status === 'degraded' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30' : ''}
                {systemState.status === 'critical' ? 'bg-red-500/10 text-red-400 border border-red-500/30' : ''}">
                {#if systemState.status === 'stable'}<CircleCheck class="w-3.5 h-3.5" />{/if}
                {#if systemState.status === 'degraded'}<CircleAlert class="w-3.5 h-3.5" />{/if}
                {#if systemState.status === 'critical'}<CircleX class="w-3.5 h-3.5" />{/if}
                <span>{statusLabel(systemState)}</span>
              </span>
            </div>
          {:else}
            <div class="flex items-center justify-center py-8 text-slate-600"><p class="text-sm">Simulation starten, um das Diagramm zu sehen</p></div>
          {/if}
        </div>

        <div class="bg-[#131615] border border-slate-800 rounded-xl p-5">
          <h3 class="text-sm font-semibold text-slate-300 flex items-center space-x-2 mb-4"><Activity class="w-4 h-4 text-blue-400" /><span>Messergebnisse</span></h3>
          {#if systemState}
            <div class="grid grid-cols-2 gap-4">
              <div>
                <div class="flex justify-between text-xs text-slate-500 mb-1"><span>Gesamtlast</span><span>{systemState.total_load_kw} / {systemState.installed_kw} kW</span></div>
                <div class="w-full bg-slate-800 rounded-full h-2.5"><div class="h-2.5 rounded-full transition-all duration-300 {loadPct() > 80 ? 'bg-red-500' : loadPct() > 60 ? 'bg-amber-500' : 'bg-emerald-500'}" style="width: {loadPct()}%"></div></div>
              </div>
              <div class="flex items-center space-x-3"><span class="text-xs text-slate-500">N+1 Status:</span>
                {#if systemState.n1_safe}<span class="inline-flex items-center space-x-1 text-xs font-semibold text-emerald-400"><CircleCheck class="w-3.5 h-3.5" /><span>SICHER</span></span>
                {:else}<span class="inline-flex items-center space-x-1 text-xs font-semibold text-red-400"><CircleX class="w-3.5 h-3.5" /><span>UNSICHER</span></span>{/if}
              </div>
              <div class="space-y-1.5"><span class="text-xs text-slate-500">Phasen-Last</span>
                {#each ['l1', 'l2', 'l3'] as phase}
                  <div class="flex items-center space-x-2"><span class="text-xs text-slate-400 w-5 uppercase">{phase}</span>
                    <div class="flex-1 bg-slate-800 rounded-full h-1.5"><div class="h-1.5 rounded-full {phase === 'l1' ? 'bg-blue-500' : phase === 'l2' ? 'bg-yellow-500' : 'bg-purple-500'}" style="width: {Math.min(100, (systemState.loads[phase as keyof typeof systemState.loads] / (systemState.phase_capacity_n1_kw || 1)) * 100)}%"></div></div>
                    <span class="text-xs text-slate-400 w-12 text-right">{systemState.loads[phase as keyof typeof systemState.loads]} kW</span></div>
                {/each}
                <div class="text-[10px] text-slate-500 mt-0.5">Imbalance: {systemState.imbalance_kw} kW | Phase-N-1: {systemState.phase_capacity_n1_kw} kW</div>
              </div>
              <div class="space-y-3">
                <div class="flex items-center space-x-2"><Power class="w-3.5 h-3.5 {systemState.grid_online ? 'text-emerald-400' : 'text-red-400'}" /><span class="text-xs text-slate-400">Grid: </span><span class="text-xs font-semibold {systemState.grid_online ? 'text-emerald-400' : 'text-red-400'}">{systemState.grid_online ? 'Online' : 'AUS'}</span></div>
                <div class="flex items-center space-x-2"><Battery class="w-3.5 h-3.5 {systemState.battery_soc_pct > 50 ? 'text-emerald-400' : systemState.battery_soc_pct > 30 ? 'text-amber-400' : 'text-red-400'}" /><span class="text-xs text-slate-400">Batterie:</span><span class="text-xs font-semibold text-slate-200">{systemState.battery_soc_pct}%</span><span class="text-xs text-slate-500">| {systemState.battery_runtime_min} min</span></div>
                <div class="flex items-center space-x-2"><span class="text-xs text-slate-400">Module:</span><span class="text-xs font-semibold text-slate-200">{systemState.active_modules_count}/{systemState.installed_modules_count} aktiv{#if systemState.failed_modules_count > 0}<span class="text-red-400"> ({systemState.failed_modules_count} defekt)</span>{/if}</span></div>
                <div class="flex items-center space-x-2"><span class="text-xs text-slate-400">N+1 Kapazität:</span><span class="text-xs font-semibold text-slate-200">{systemState.n1_kw} kW</span></div>
              </div>
            </div>
            
            <div class="mt-4 p-3 bg-slate-800/30 border border-slate-700/50 rounded-lg">
              <div class="flex justify-between items-center mb-1">
                <span class="text-xs text-slate-400">Max. Batterie-Entladestrom:</span>
                <span class="text-sm font-semibold {batteryDischargeCurrent > 200 ? 'text-red-400' : 'text-slate-200'}">{batteryDischargeCurrent} A</span>
              </div>
              <div class="flex justify-between items-center">
                <span class="text-[10px] text-slate-500">DC-Kabelquerschnitt empfohlen:</span>
                <span class="text-[10px] font-mono text-slate-400">≥ {cableSection} mm²</span>
              </div>
              {#if batteryDischargeCurrent > 200}
                <div class="mt-2 p-1.5 bg-red-500/10 border border-red-500/20 rounded text-[10px] text-red-400 flex items-center space-x-1.5">
                  <span class="font-bold">⚠</span><span>NH-Sicherung prüfen — Strom überschreitet 200A</span>
                </div>
              {/if}
            </div>
          {:else}
            <div class="flex items-center justify-center py-8 text-slate-600"><p class="text-sm">Simulation starten</p></div>
          {/if}
        </div>
      </div>
    </div>

    <!-- Event Log -->
    <div class="mt-6 bg-[#131615] border border-slate-800 rounded-xl p-5">
      <h3 class="text-sm font-semibold text-slate-300 flex items-center space-x-2 mb-4"><Activity class="w-4 h-4 text-yellow-400" /><span>Event-Log</span><span class="text-xs text-slate-600">({events.length} Einträge)</span></h3>
      {#if events.length > 0}
        <div class="overflow-x-auto"><table class="w-full text-sm">
          <thead><tr class="text-left text-xs text-slate-500 border-b border-slate-800"><th class="pb-2 pr-4 font-medium">Zeit</th><th class="pb-2 pr-4 font-medium">Typ</th><th class="pb-2 pr-4 font-medium">Severity</th><th class="pb-2 font-medium">Beschreibung</th></tr></thead>
          <tbody>
            {#each events as ev}
              <tr class="border-b border-slate-800/50 hover:bg-slate-800/20 transition">
                <td class="py-2 pr-4 text-xs text-slate-500 font-mono whitespace-nowrap">{formatTime(ev.timestamp)}</td>
                <td class="py-2 pr-4"><span class="text-xs font-mono text-slate-400">{ev.event_type}</span></td>
                <td class="py-2 pr-4"><span class="text-[10px] font-semibold px-2 py-0.5 rounded border {severityClass(ev.severity)}">{ev.severity.toUpperCase()}</span></td>
                <td class="py-2 text-xs text-slate-300">{ev.description}</td>
              </tr>
            {/each}
          </tbody>
        </table></div>
      {:else}
        <div class="flex items-center justify-center py-6 text-slate-600"><p class="text-sm">Keine Events. Simulation starten!</p></div>
      {/if}
    </div>

  {:else if activeTab === 'battery'}
    <!-- === BATTERIESCHRANK TAB === -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Battery Configuration -->
      <div class="space-y-4">
        <div class="bg-[#131615] border border-slate-800 rounded-xl p-5">
          <h3 class="text-sm font-semibold text-slate-300 flex items-center space-x-2 mb-4">
            <Cpu class="w-4 h-4 text-emerald-400" /><span>Batterie-Konfiguration</span>
          </h3>

          {#if templateHint}
            <div class="mb-4 p-3 bg-blue-500/10 border border-[#1D9E75]/20 rounded-lg text-xs text-blue-300 leading-relaxed">
              <span class="font-semibold block mb-1">Voreinstellung für {usvModels.find(m => m.id === hwTemplateId)?.hersteller} {usvModels.find(m => m.id === hwTemplateId)?.modell} — Werte können angepasst werden:</span>
              {templateHint}
            </div>
          {/if}

          {#if batteryWarnings.length > 0}
            <div class="mb-4 space-y-2">
              {#each batteryWarnings as warn}
                <div class="px-3 py-2 bg-amber-500/10 border border-amber-500/30 rounded-lg text-xs text-amber-400">
                  {warn}
                </div>
              {/each}
            </div>
          {/if}

          <label class="text-xs text-slate-500 mb-1 block">Batterietyp</label>
          <select bind:value={batType} class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500 mb-2">
            {#each batteryTypeOptions as bt}
              <option value={bt.value}>
                {bt.label}
                {#if bt.value === 'lfp'} ✓ Sicherste Wahl{/if}
                {#if bt.value === 'li_ion_nmc'} ⚠ Thermal Runaway Risiko{/if}
              </option>
            {/each}
          </select>

          {#if batType === 'vrla'}
            <div class="mb-4 p-2 bg-slate-800/50 border border-slate-700 rounded text-[10px] text-slate-400 leading-tight">
              ⚠ Belüftung erforderlich — Wasserstoffgas bei Überladung. Optimale Temperatur 20-25°C. Bei >25°C halbiert sich die Lebensdauer je 10°C Temperaturerhöhung.
            </div>
          {:else if batType === 'lfp'}
            <div class="mb-4 p-2 bg-emerald-500/10 border border-emerald-500/20 rounded text-[10px] text-emerald-400 leading-tight">
              ✓ Sicherste Batterietechnologie für Rechenzentren. Kein Sauerstoff bei Zersetzung — keine Brandgefahr durch Thermal Runaway. Integriertes BMS.
            </div>
          {:else if batType === 'li_ion_nmc'}
            <div class="mb-4 p-2 bg-red-500/10 border border-red-500/20 rounded text-[10px] text-red-400 leading-tight">
              ⚠ Erhöhtes Brandrisiko durch Thermal Runaway. Feuerlöschanlage im Batterieraum empfohlen. Nicht für dichte Serverräume ohne Brandschutz.
            </div>
          {:else}
            <div class="mb-4"></div>
          {/if}

          <div class="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label class="text-xs text-slate-500 mb-1 block">Serie (Blöcke)</label>
              <input type="range" min="1" max="20" bind:value={batSeries} class="w-full accent-emerald-500" />
              <span class="text-xs text-slate-400">{batSeries} × {batBlockV}V = {batSeries * batBlockV}V</span>
            </div>
            <div>
              <label class="text-xs text-slate-500 mb-1 block">Parallel (Strings)</label>
              <input type="range" min="1" max="10" bind:value={batParallel} class="w-full accent-emerald-500" />
              <span class="text-xs text-slate-400">{batParallel} × {batBlockAh}Ah = {batParallel * batBlockAh}Ah</span>
            </div>
          </div>

          <!-- Block visual -->
          <div class="bg-[#181C1A] border border-slate-700 rounded-lg p-3 mb-3">
            <span class="text-[10px] text-slate-500 uppercase mb-2 block">Block-Konfiguration: {batParallel} Strings × {batSeries} Blöcke</span>
            <div class="flex gap-1 justify-center flex-wrap">
              {#each Array(Math.min(batParallel, 3)) as _, si}
                <div class="flex flex-col items-center gap-0.5 px-1 {si > 0 ? 'border-l border-slate-700 ml-1 pl-2' : ''}">
                  {#each Array(Math.min(batSeries, 8)) as _}
                    <div class="w-8 h-4 bg-emerald-500/20 border border-emerald-500/40 rounded text-[8px] text-emerald-400 flex items-center justify-center">{batBlockV}V</div>
                    {#if batParallel > 3 && si === 2}<div class="text-[8px] text-slate-600">…×{batParallel}</div>{/if}
                  {/each}
                  {#if batSeries > 8}<div class="text-[8px] text-slate-600">…×{batSeries}</div>{/if}
                </div>
              {/each}
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label class="text-xs text-slate-500 mb-1 block">Alter (Jahre)</label>
              <input type="range" min="0" max="20" step="0.5" bind:value={batAge} class="w-full accent-amber-500" />
              <span class="text-xs text-slate-400">{batAge} Jahre</span>
            </div>
            <div>
              <label class="text-xs text-slate-500 mb-1 block">Temperatur (°C)</label>
              <input type="range" min="-10" max="50" bind:value={batTemp} class="w-full accent-red-500" />
              <span class="text-xs text-slate-400">{batTemp}°C</span>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3 mb-3">
            <div><label class="text-xs text-slate-500 mb-1 block">Block-Spannung (V)</label><input type="number" step="1" min="2" bind:value={batBlockV} class="w-full bg-[#0f1720] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500" /></div>
            <div><label class="text-xs text-slate-500 mb-1 block">Block-Kapazität (Ah)</label><input type="number" step="5" min="10" bind:value={batBlockAh} class="w-full bg-[#0f1720] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500" /></div>
          </div>

          <button onclick={loadRuntimeCurve} disabled={batteryLoading}
            class="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-lg text-sm font-semibold transition flex items-center justify-center space-x-2">
            {#if batteryLoading}<RefreshCw class="w-4 h-4 animate-spin" /><span>Lädt...</span>{:else}<TrendingUp class="w-4 h-4" /><span>Runtime-Kurve laden</span>{/if}
          </button>
        </div>

        <!-- Dimensioning Calculator -->
        <div class="bg-[#131615] border border-slate-800 rounded-xl p-5">
          <h3 class="text-sm font-semibold text-slate-300 flex items-center space-x-2 mb-4">
            <Wrench class="w-4 h-4 text-purple-400" /><span>Dimensionierungsrechner</span>
          </h3>
          <p class="text-[11px] text-slate-500 mb-3">Wieviele Batterieblöcke für X min Überbrückung bei Y kW?</p>
          <div class="space-y-3">
            <div class="grid grid-cols-2 gap-3">
              <div><label class="text-xs text-slate-500 mb-1 block">Last (kW)</label><input type="number" step="0.1" min="0.1" bind:value={dimLoad} class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-purple-500" /></div>
              <div><label class="text-xs text-slate-500 mb-1 block">Ziel (min)</label><input type="number" step="1" min="1" bind:value={dimTargetMin} class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-purple-500" /></div>
            </div>
            <select bind:value={dimType} class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-purple-500">
              {#each batteryTypeOptions as bt}<option value={bt.value}>{bt.label}</option>{/each}
            </select>
            <button onclick={runDimensioning} disabled={dimLoading}
              class="w-full py-2 bg-purple-600 hover:bg-purple-500 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-lg text-sm font-semibold transition flex items-center justify-center space-x-2">
              {#if dimLoading}<RefreshCw class="w-4 h-4 animate-spin" /><span>Rechnet...</span>{:else}<Wrench class="w-4 h-4" /><span>Berechnen</span>{/if}
            </button>
          </div>
          {#if dimResult}
            <div class="mt-4 p-3 bg-[#181C1A] border border-slate-700 rounded-lg space-y-1">
              <div class="flex justify-between text-xs"><span class="text-slate-400">Benötigt:</span><span class="text-slate-200 font-semibold">{dimResult.required_capacity_ah} Ah</span></div>
              <div class="flex justify-between text-xs"><span class="text-slate-400">Konfiguration:</span><span class="text-slate-200 font-semibold">{dimResult.series_blocks}S × {dimResult.parallel_strings}P = {dimResult.total_blocks} Blöcke</span></div>
              <div class="flex justify-between text-xs"><span class="text-slate-400">Tatsächlich:</span><span class="text-emerald-400 font-semibold">{dimResult.actual_capacity_ah} Ah → {dimResult.actual_runtime_min} min</span></div>
              <div class="flex justify-between text-xs"><span class="text-slate-400">Sicherheit:</span><span class="text-slate-200">{dimResult.safety_margin_pct}% → {dimResult.load_with_margin_kw} kW</span></div>
            </div>
          {/if}
        </div>
      </div>

      <!-- Runtime Curve + Battery Summary -->
      <div class="lg:col-span-2 space-y-6">
        <!-- Battery Summary -->
        {#if runtimeCurve?.battery_summary}
          {@const bs = runtimeCurve.battery_summary}
          <div class="bg-[#131615] border border-slate-800 rounded-xl p-5">
            <h3 class="text-sm font-semibold text-slate-300 flex items-center space-x-2 mb-4">
              <Battery class="w-4 h-4 text-emerald-400" /><span>Batterie-Übersicht</span>
            </h3>
            <div class="grid grid-cols-4 gap-3">
              <div class="bg-[#181C1A] border border-slate-700 rounded-lg p-3 text-center">
                <div class="text-[10px] text-slate-500 uppercase mb-1">Typ</div>
                <div class="text-sm font-semibold text-emerald-400">{bs.battery_type_name}</div>
              </div>
              <div class="bg-[#181C1A] border border-slate-700 rounded-lg p-3 text-center">
                <div class="text-[10px] text-slate-500 uppercase mb-1">Kapazität</div>
                <div class="text-sm font-semibold text-slate-200">{bs.nominal_capacity_ah} Ah</div>
                <div class="text-[10px] text-slate-500">effektiv: <span class="text-amber-400">{bs.effective_capacity_ah} Ah</span></div>
              </div>
              <div class="bg-[#181C1A] border border-slate-700 rounded-lg p-3 text-center">
                <div class="text-[10px] text-slate-500 uppercase mb-1">Energie</div>
                <div class="text-sm font-semibold text-slate-200">{bs.nominal_energy_kwh} kWh</div>
                <div class="text-[10px] text-slate-500">effektiv: <span class="text-amber-400">{bs.effective_energy_kwh} kWh</span></div>
              </div>
              <div class="bg-[#181C1A] border border-slate-700 rounded-lg p-3 text-center">
                <div class="text-[10px] text-slate-500 uppercase mb-1">Blöcke</div>
                <div class="text-sm font-semibold text-slate-200">{bs.total_blocks}</div>
                <div class="text-[10px] text-slate-500">{bs.series_blocks}S × {bs.parallel_strings}P</div>
              </div>
              <div class="bg-[#181C1A] border border-slate-700 rounded-lg p-3 text-center">
                <div class="text-[10px] text-slate-500 uppercase mb-1">Alterung</div>
                <div class="text-sm font-semibold {bs.aging_factor_pct >= 90 ? 'text-emerald-400' : bs.aging_factor_pct >= 70 ? 'text-amber-400' : 'text-red-400'}">{bs.aging_factor_pct}%</div>
                <div class="text-[10px] text-slate-500">{bs.age_years} / {bs.lifespan_years} Jahre</div>
              </div>
              <div class="bg-[#181C1A] border border-slate-700 rounded-lg p-3 text-center">
                <div class="text-[10px] text-slate-500 uppercase mb-1">Temperatur</div>
                <div class="text-sm font-semibold {bs.temperature_factor_pct >= 95 ? 'text-emerald-400' : bs.temperature_factor_pct >= 85 ? 'text-amber-400' : 'text-red-400'}">{bs.temperature_factor_pct}%</div>
                <div class="text-[10px] text-slate-500">{bs.temperature_c}°C</div>
              </div>
              <div class="bg-[#181C1A] border border-slate-700 rounded-lg p-3 text-center">
                <div class="text-[10px] text-slate-500 uppercase mb-1">Peukert k</div>
                <div class="text-sm font-semibold text-slate-200">{bs.peukert_k}</div>
              </div>
              <div class="bg-[#181C1A] border border-slate-700 rounded-lg p-3 text-center">
                <div class="text-[10px] text-slate-500 uppercase mb-1">N+1</div>
                <div class="text-sm font-semibold {runtimeCurve.n1_safe ? 'text-emerald-400' : 'text-red-400'}">{runtimeCurve.n1_safe ? 'SICHER' : 'UNSICHER'}</div>
                <div class="text-[10px] text-slate-500">{runtimeCurve.n1_kw} kW</div>
              </div>
            </div>
            
            {#if runtimeCurve.strangausfall_runtime_min !== undefined}
              <div class="mt-4 p-3 bg-[#181C1A] border border-slate-700 rounded-lg flex justify-between items-center">
                <div>
                  <span class="text-xs text-slate-400 font-semibold block">Strang-Redundanz (Strangausfall N-1)</span>
                  <span class="text-[10px] text-slate-500">Verbleibende Überbrückungszeit bei Ausfall eines parallelen Strangs (Peukert)</span>
                </div>
                <div class="text-right">
                  {#if bs.parallel_strings > 1}
                    <span class="text-lg font-bold {runtimeCurve.strangausfall_runtime_min >= 10 ? 'text-emerald-400' : runtimeCurve.strangausfall_runtime_min >= 5 ? 'text-amber-400' : 'text-red-400'}">
                      {Math.round(runtimeCurve.strangausfall_runtime_min)} min
                    </span>
                  {:else}
                    <span class="text-sm font-bold text-red-400">Keine Redundanz (0 min)</span>
                  {/if}
                </div>
              </div>
            {/if}
          </div>
        {/if}

        <!-- Runtime Curve Chart -->
        <div class="bg-[#131615] border border-slate-800 rounded-xl p-5">
          <h3 class="text-sm font-semibold text-slate-300 flex items-center space-x-2 mb-4">
            <TrendingUp class="w-4 h-4 text-yellow-400" /><span>Überbrückungszeit vs Last (Peukert)</span>
            {#if runtimeCurve}
              <span class="text-xs text-slate-500 ml-2">| {runtimeCurve.total_load_kw} kW aktuell → {runtimeCurve.current_runtime_min} min</span>
            {/if}
          </h3>
          {#if runtimeCurve?.curve && runtimeCurve.curve.length > 0}
            {@const points = runtimeCurve.curve}
            {@const maxX = points[points.length - 1].load_kw}
            {@const maxY = points[0].runtime_min * 1.05}
            {@const gridLines = 5}
            {@const currentIdx = points.findIndex(p => p.load_kw >= runtimeCurve!.total_load_kw) ?? points.length - 1}
            <svg viewBox="0 0 {svgWidth} {svgHeight}" class="w-full">
              <!-- Grid lines -->
              {#each Array(gridLines + 1) as _, i}
                {@const y = padT + (chartH * i) / gridLines}
                <line x1={padL} y1={y} x2={svgWidth - padR} y2={y} stroke="#1e293b" stroke-width="0.5" />
                <text x={padL - 6} y={y + 4} fill="#64748b" font-size="10" text-anchor="end">
                  {Math.round(maxY * (1 - i / gridLines))}
                </text>
              {/each}
              {#each Array(6) as _, i}
                {@const x = padL + (chartW * i) / 5}
                <line x1={x} y1={padT} x2={x} y2={svgHeight - padB} stroke="#1e293b" stroke-width="0.5" />
                <text x={x} y={svgHeight - 8} fill="#64748b" font-size="10" text-anchor="middle">{Math.round(maxX * i / 5)}</text>
              {/each}
              <!-- Axes -->
              <line x1={padL} y1={padT} x2={padL} y2={svgHeight - padB} stroke="#475569" stroke-width="1" />
              <line x1={padL} y1={svgHeight - padB} x2={svgWidth - padR} y2={svgHeight - padB} stroke="#475569" stroke-width="1" />
              <!-- Axis labels -->
              <text x={svgWidth / 2} y={svgHeight - 2} fill="#64748b" font-size="10" text-anchor="middle">Last (kW)</text>
              <text x={12} y={svgHeight / 2} fill="#64748b" font-size="10" text-anchor="middle" transform="rotate(-90 12 {svgHeight / 2})">Laufzeit (min)</text>
              <!-- Curve -->
              <path d={curvePath(points, maxX, maxY)} fill="none" stroke="#10b981" stroke-width="2.5" />
              <path d={curvePath(points, maxX, maxY) + `L${svgWidth - padR},${padT + chartH}L${padL},${padT + chartH}Z`} fill="#10b981" opacity="0.08" />
              <!-- Load marker -->
              {#if currentIdx >= 0 && currentIdx < points.length}
                {@const cx = padL + (points[currentIdx].load_kw / maxX) * chartW}
                {@const cy = padT + chartH - (points[currentIdx].runtime_min / maxY) * chartH}
                <circle cx={cx} cy={cy} r="5" fill="#8b5cf6" stroke="#a78bfa" stroke-width="2" />
                <text x={cx} y={cy - 10} fill="#a78bfa" font-size="11" font-weight="bold" text-anchor="middle">{runtimeCurve.current_runtime_min} min</text>
                <line x1={cx} y1={cy + 5} x2={cx} y2={svgHeight - padB} stroke="#8b5cf6" stroke-width="1" stroke-dasharray="4,3" />
              {/if}
              <!-- Installed capacity marker -->
              {#if runtimeCurve}
                {@const ikX = padL + (runtimeCurve.installed_kw / maxX) * chartW}
                <line x1={ikX} y1={padT} x2={ikX} y2={svgHeight - padB} stroke="#ef4444" stroke-width="1" stroke-dasharray="6,4" />
                <text x={ikX} y={padT - 4} fill="#ef4444" font-size="10" text-anchor="middle">{runtimeCurve.installed_kw}kW</text>
              {/if}
            </svg>
          {:else}
            <div class="flex items-center justify-center py-12 text-slate-600">
              <p class="text-sm">Batterie konfigurieren und "Runtime-Kurve laden" klicken</p>
            </div>
          {/if}
        </div>
      </div>
    </div>
  {:else if activeTab === 'shutdown_sequence'}
    <!-- === SHUTDOWN SEQUENCE TAB === -->
    <ShutdownSimulator />
  {:else}
    <!-- === STROMLAUFPLAN TAB === -->
    <div class="bg-[#131615] border border-slate-800 rounded-xl p-6">
      <h3 class="text-lg font-bold text-white mb-2">Stromlaufplan & Topologie (40kW USV)</h3>
      <p class="text-sm text-slate-400 mb-6">
        Die schematische Einspeisungs- und Verteilerstruktur des RZs. Die Zuleitung zur Unterverteilung ist für 40kW mit <strong>5x25 mm²</strong> dimensioniert.
        <br/><span class="text-blue-400 font-semibold mt-2 inline-block">Interaktiv:</span> Klicke auf Elemente (z.B. Phasen oder USV), um einen Ausfall zu simulieren und die Kaskadeneffekte auf angeschlossene Geräte zu sehen.
      </p>

      {#if isTopologySimulating}
        <div class="mb-4 text-sm text-blue-400 flex items-center gap-2"><RefreshCw class="w-4 h-4 animate-spin"/> Berechne Kaskadeneffekte...</div>
      {/if}

      <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <!-- SVG diagram column (occupies 3 cols) -->
        <div class="lg:col-span-3 bg-[#0d1220] border border-slate-800 rounded-xl p-4 flex justify-center">
          <svg viewBox="0 0 700 850" class="w-full max-w-[650px] h-auto">
            <!-- Definitions for markers and filters -->
            <defs>
              <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#64748b" />
              </marker>
            </defs>

            <!-- Background grid lines (optional decorative) -->
            <g opacity="0.05">
              <line x1="0" y1="60" x2="700" y2="60" stroke="#38bdf8" stroke-width="1" />
              <line x1="0" y1="120" x2="700" y2="120" stroke="#38bdf8" stroke-width="1" />
              <line x1="0" y1="180" x2="700" y2="180" stroke="#38bdf8" stroke-width="1" />
              <line x1="0" y1="240" x2="700" y2="240" stroke="#38bdf8" stroke-width="1" />
              <line x1="0" y1="300" x2="700" y2="300" stroke="#38bdf8" stroke-width="1" />
              <line x1="0" y1="360" x2="700" y2="360" stroke="#38bdf8" stroke-width="1" />
              <line x1="0" y1="420" x2="700" y2="420" stroke="#38bdf8" stroke-width="1" />
              <line x1="0" y1="480" x2="700" y2="480" stroke="#38bdf8" stroke-width="1" />
              <line x1="0" y1="540" x2="700" y2="540" stroke="#38bdf8" stroke-width="1" />
              <line x1="0" y1="600" x2="700" y2="600" stroke="#38bdf8" stroke-width="1" />
              <line x1="0" y1="660" x2="700" y2="660" stroke="#38bdf8" stroke-width="1" />
              <line x1="0" y1="720" x2="700" y2="720" stroke="#38bdf8" stroke-width="1" />
              <line x1="0" y1="780" x2="700" y2="780" stroke="#38bdf8" stroke-width="1" />
              <line x1="0" y1="840" x2="700" y2="840" stroke="#38bdf8" stroke-width="1" />
              <line x1="50" y1="0" x2="50" y2="850" stroke="#38bdf8" stroke-width="1" />
              <line x1="100" y1="0" x2="100" y2="850" stroke="#38bdf8" stroke-width="1" />
              <line x1="150" y1="0" x2="150" y2="850" stroke="#38bdf8" stroke-width="1" />
              <line x1="200" y1="0" x2="200" y2="850" stroke="#38bdf8" stroke-width="1" />
              <line x1="250" y1="0" x2="250" y2="850" stroke="#38bdf8" stroke-width="1" />
              <line x1="300" y1="0" x2="300" y2="850" stroke="#38bdf8" stroke-width="1" />
              <line x1="350" y1="0" x2="350" y2="850" stroke="#38bdf8" stroke-width="1" />
              <line x1="400" y1="0" x2="400" y2="850" stroke="#38bdf8" stroke-width="1" />
              <line x1="450" y1="0" x2="450" y2="850" stroke="#38bdf8" stroke-width="1" />
              <line x1="500" y1="0" x2="500" y2="850" stroke="#38bdf8" stroke-width="1" />
              <line x1="550" y1="0" x2="550" y2="850" stroke="#38bdf8" stroke-width="1" />
              <line x1="600" y1="0" x2="600" y2="850" stroke="#38bdf8" stroke-width="1" />
              <line x1="650" y1="0" x2="650" y2="850" stroke="#38bdf8" stroke-width="1" />
            </g>

            <!-- Flow connection lines -->
            <!-- Main grid feed -->
            <line x1="350" y1="50" x2="350" y2="100" stroke="#475569" stroke-width="2.5" marker-end="url(#arrow)" />
            <!-- HV to NH -->
            <line x1="350" y1="160" x2="350" y2="210" stroke="#475569" stroke-width="2.5" marker-end="url(#arrow)" />
            <!-- NH to UV-RZ-01 -->
            <line x1="350" y1="270" x2="350" y2="320" stroke="#475569" stroke-width="2.5" marker-end="url(#arrow)" />

            <!-- UV-RZ-01 to USV Feed -->
            <path d="M 270 380 L 180 380 L 180 430" fill="none" stroke="#475569" stroke-width="2.5" marker-end="url(#arrow)" />
            <!-- USV to MBS -->
            <line x1="180" y1="490" x2="180" y2="540" stroke="#10b981" stroke-width="2.5" stroke-dasharray="4,2" />
            <path d="M 180 540 L 180 570 L 300 570" fill="none" stroke="#10b981" stroke-width="2.5" stroke-dasharray="4,2" marker-end="url(#arrow)" />

            <!-- UV-RZ-01 Bypass Feed -->
            <path d="M 430 380 L 520 380 L 520 490" fill="none" stroke="#ef4444" stroke-dasharray="5,4" stroke-width="2.5" />
            <path d="M 520 490 L 520 570 L 400 570" fill="none" stroke="#ef4444" stroke-dasharray="5,4" stroke-width="2.5" marker-end="url(#arrow)" />

            <!-- MBS to UV-USV-01 -->
            <line x1="350" y1="600" x2="350" y2="650" stroke="#475569" stroke-width="2.5" marker-end="url(#arrow)" />

            <!-- UV-USV-01 to Outlets -->
            <!-- L1 -->
            <path d="M 230 710 L 130 710 L 130 760" fill="none" stroke="#3b82f6" stroke-width="2" marker-end="url(#arrow)" />
            <!-- L2 -->
            <line x1="350" y1="710" x2="350" y2="760" stroke="#eab308" stroke-width="2" marker-end="url(#arrow)" />
            <!-- L3 -->
            <path d="M 470 710 L 570 710 L 570 760" fill="none" stroke="#a855f7" stroke-width="2" marker-end="url(#arrow)" />

            <!-- Nodes / Boxes -->
            <!-- Netz -->
            <g class="cursor-pointer group" onclick={() => triggerScenario('grid', 'Main Grid')}>
              <rect x="230" y="10" width="240" height="40" rx="6" fill="#1e293b" stroke="#475569" stroke-width="1.5" class="group-hover:fill-slate-800 group-hover:stroke-slate-400 transition" />
              <text x="350" y="28" fill="#f8fafc" font-size="11" font-weight="bold" text-anchor="middle" class="pointer-events-none">Netz 3~ 400V / 50Hz (Totalausfall)</text>
              <text x="350" y="42" fill="#94a3b8" font-size="9" text-anchor="middle" class="pointer-events-none">Hauptverteilung (HV)</text>
            </g>

            <!-- NH Sicherung -->
            <rect x="250" y="100" width="200" height="60" rx="6" fill="#1e1b4b" stroke="#4338ca" stroke-width="1.5" />
            <text x="350" y="120" fill="#f8fafc" font-size="11" font-weight="bold" text-anchor="middle">NH-Sicherung 80A gG</text>
            <text x="350" y="136" fill="#818cf8" font-size="9" text-anchor="middle">Zuleitung: NYY-J 5x25 mm²</text>
            <text x="350" y="150" fill="#6366f1" font-size="8" text-anchor="middle">3-polige Hauptabsicherung</text>

            <!-- UV-RZ-01 -->
            <rect x="210" y="210" width="280" height="60" rx="6" fill="#0f172a" stroke="#334155" stroke-width="1.5" />
            <text x="350" y="232" fill="#f8fafc" font-size="12" font-weight="bold" text-anchor="middle">Unterverteilung UV-RZ-01</text>
            <text x="350" y="248" fill="#94a3b8" font-size="9" text-anchor="middle">Hauptzuleitung ungepuffert</text>
            <text x="350" y="262" fill="#64748b" font-size="8" text-anchor="middle">LS 3P 63A Abgänge</text>

            <!-- USV Schrank (Left Branch) -->
            <g class="cursor-pointer group" onclick={() => triggerScenario('usv', 'USV Total')}>
              <rect x="80" y="430" width="200" height="60" rx="6" fill="#064e3b" stroke="#059669" stroke-width="1.5" class="group-hover:fill-emerald-900 group-hover:stroke-emerald-400 transition" />
              <text x="180" y="452" fill="#ecfdf5" font-size="11" font-weight="bold" text-anchor="middle" class="pointer-events-none">USV-Schrank (Ausfall sim.)</text>
              <text x="180" y="468" fill="#a7f3d0" font-size="9" text-anchor="middle" class="pointer-events-none">WP2-R / 93PM (N+1)</text>
              <text x="180" y="482" fill="#34d399" font-size="8" text-anchor="middle" class="pointer-events-none">Zuleitung: NYY-J 5x16 mm²</text>
            </g>

            <!-- Bypass LS (Right Branch) -->
            <rect x="420" y="430" width="200" height="60" rx="6" fill="#78350f" stroke="#d97706" stroke-width="1.5" />
            <text x="520" y="452" fill="#fffbeb" font-size="11" font-weight="bold" text-anchor="middle">Bypass-Zuleitung (MBS)</text>
            <text x="520" y="468" fill="#fde68a" font-size="9" text-anchor="middle">Direktnetz (LS 3P 63A)</text>
            <text x="520" y="482" fill="#fbbf24" font-size="8" text-anchor="middle">Kabel: NYY-J 5x16 mm²</text>

            <!-- MBS Schalter (Middle) -->
            <polygon points="350,530 410,570 350,610 290,570" fill="#1e293b" stroke="#64748b" stroke-width="2" />
            <text x="350" y="566" fill="#f8fafc" font-size="10" font-weight="bold" text-anchor="middle">Bypass MBS</text>
            <text x="350" y="580" fill="#94a3b8" font-size="8" text-anchor="middle">Mechanisch verriegelt</text>

            <!-- UV-USV-01 -->
            <rect x="210" y="650" width="280" height="60" rx="6" fill="#14532d" stroke="#16a34a" stroke-width="1.5" />
            <text x="350" y="672" fill="#f0fdf4" font-size="12" font-weight="bold" text-anchor="middle">Unterverteilung UV-USV-01</text>
            <text x="350" y="688" fill="#bbf7d0" font-size="9" text-anchor="middle">Gepufferte USV-Schiene</text>
            <text x="350" y="702" fill="#4ade80" font-size="8" text-anchor="middle">LS 1P 32A Abgänge</text>

            <!-- PDU L1 -->
            <g class="cursor-pointer group" onclick={() => triggerScenario('pdu', 'A-0UL')}>
              <rect x="30" y="760" width="200" height="60" rx="6" fill="#1e293b" stroke="#3b82f6" stroke-width="1.5" class="group-hover:fill-blue-900/40 group-hover:stroke-blue-400 transition" />
              <text x="130" y="780" fill="#f8fafc" font-size="10" font-weight="bold" text-anchor="middle" class="pointer-events-none">SmartPDU A-0UL</text>
              <text x="130" y="794" fill="#94a3b8" font-size="8" text-anchor="middle" class="pointer-events-none">Phase L1 | Zuleitung: 3x10 mm²</text>
              <text x="130" y="808" fill="#60a5fa" font-size="8" text-anchor="middle" class="pointer-events-none">Klick für Ausfall (Server A)</text>
            </g>

            <!-- PDU L2 -->
            <g class="cursor-pointer group" onclick={() => triggerScenario('pdu', 'A-0UR')}>
              <rect x="250" y="760" width="200" height="60" rx="6" fill="#1e293b" stroke="#eab308" stroke-width="1.5" class="group-hover:fill-yellow-900/40 group-hover:stroke-yellow-400 transition" />
              <text x="350" y="780" fill="#f8fafc" font-size="10" font-weight="bold" text-anchor="middle" class="pointer-events-none">SmartPDU A-0UR</text>
              <text x="350" y="794" fill="#94a3b8" font-size="8" text-anchor="middle" class="pointer-events-none">Phase L2 | Zuleitung: 3x10 mm²</text>
              <text x="350" y="808" fill="#facc15" font-size="8" text-anchor="middle" class="pointer-events-none">Klick für Ausfall (Server B)</text>
            </g>

            <!-- PDU L3 -->
            <g class="cursor-pointer group" onclick={() => triggerScenario('pdu', 'B-0UL')}>
              <rect x="470" y="760" width="200" height="60" rx="6" fill="#1e293b" stroke="#a855f7" stroke-width="1.5" class="group-hover:fill-purple-900/40 group-hover:stroke-purple-400 transition" />
              <text x="570" y="780" fill="#f8fafc" font-size="10" font-weight="bold" text-anchor="middle" class="pointer-events-none">SmartPDU B-0UL</text>
              <text x="570" y="794" fill="#94a3b8" font-size="8" text-anchor="middle" class="pointer-events-none">Phase L3 | Zuleitung: 3x10 mm²</text>
              <text x="570" y="808" fill="#c084fc" font-size="8" text-anchor="middle" class="pointer-events-none">Klick für Ausfall (Redundanz)</text>
            </g>
          </svg>
        </div>

        <!-- Legend / Info panel (1 col) -->
        <div class="space-y-4">
          <div class="bg-[#181C1A] border border-slate-700/50 rounded-xl p-4">
            <h4 class="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-3">Legende & Kabel</h4>
            <div class="space-y-3 text-xs">
              <div class="flex items-center space-x-2">
                <div class="w-4 h-1 bg-slate-500"></div>
                <span class="text-slate-400">Normalnetz (ungepuffert)</span>
              </div>
              <div class="flex items-center space-x-2">
                <div class="w-4 h-1 bg-emerald-500"></div>
                <span class="text-slate-400">USV-Pfad (aktiv gepuffert)</span>
              </div>
              <div class="flex items-center space-x-2">
                <div class="w-4 h-1 bg-red-500 stroke-dasharray-2"></div>
                <span class="text-slate-400">Direktnetz / Bypass</span>
              </div>
              <div class="pt-3 border-t border-slate-700/50 space-y-2">
                <p class="text-[11px] text-slate-400"><strong>Zuleitung HV ──► UV:</strong><br />NYY-J 5x25 mm² (NH 80A)</p>
                <p class="text-[11px] text-slate-400"><strong>Verbindungen USV/MBS:</strong><br />NYY-J 5x16 mm² (LS 63A)</p>
                <p class="text-[11px] text-slate-400"><strong>Zuleitung PDU:</strong><br />NYY-J 3x10 mm² (LS 32A)</p>
              </div>
            </div>
          </div>

          <div class="bg-[#181C1A] border border-slate-700/50 rounded-xl p-4 text-xs text-slate-400 leading-relaxed space-y-2">
            <h4 class="text-xs font-semibold text-slate-300 uppercase tracking-wider">EPLAN Integration</h4>
            <p>
              Dieses Einspeise-Schema ist mit den tatsächlichen physikalischen Verbindungen im RZ deckungsgleich.
            </p>
            <p>
              Die CSV-Vorlage <code>eplan_power_import.csv</code> im Projekt-Ordner erlaubt es, diese Topologie vollautomatisch in KAiTix zu importieren und als physische Verbindungen anzulegen.
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Timeline overlay -->
    <SimulationTimeline result={topologySimResult} onClose={() => topologySimResult = null} />
  {/if}
</div>

<script lang="ts">
  import { FileText, Grid, Download } from '@lucide/svelte';
  import { onMount } from 'svelte';
  import { api, type UsvUnit } from '$lib/api';

  let activeTab = $state<'block' | 'cad'>('cad');
  let pdfLoading = $state(false);

  interface UsvData {
    id: number;
    bezeichnung: string;
    battery_strings: number;
    blocks_per_string: number;
    block_voltage_v: number;
    block_capacity_ah: number;
  }
  
  let allUsvUnits = $state<UsvUnit[]>([]);
  let selectedUsvId = $state<number | null>(null);
  let usvData = $state<UsvData | null>(null);

  async function loadUsvData(id: number) {
    try {
      const res = await fetch(`/api/v1/usv/${id}`);
      if (res.ok) {
        usvData = await res.json();
      }
    } catch (e) {
      console.error('Fehler beim Laden der USV-Daten', e);
    }
  }

  $effect(() => {
    if (selectedUsvId !== null) {
      loadUsvData(selectedUsvId);
    }
  });

  onMount(async () => {
    try {
      allUsvUnits = await api.getUsvUnits();
      if (allUsvUnits.length > 0) {
        selectedUsvId = allUsvUnits[0].id;
      }
    } catch (e) {
      console.error('Fehler beim Laden der USV-Liste', e);
    }
  });

  function printEplan() {
    pdfLoading = true;
    try {
      const blockSvg = document.querySelector('#eplan-block svg')?.outerHTML ?? '';
      const blatt1Svg = document.querySelector('#eplan-blatt1')?.outerHTML ?? '';
      const blatt2Svg = document.querySelector('#eplan-blatt2')?.outerHTML ?? '';
      const blatt3Svg = document.querySelector('#eplan-blatt3 svg')?.outerHTML ?? '';

      const html = `<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <title>KAiTix Stromlaufplan &amp; Topologie</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { background: white; font-family: sans-serif; }
    .page { width: 297mm; min-height: 210mm; padding: 10mm; page-break-after: always; display: flex; flex-direction: column; align-items: center; justify-content: center; }
    .page:last-child { page-break-after: auto; }
    .page-title { font-size: 12pt; font-weight: bold; color: #0f172a; margin-bottom: 6mm; align-self: flex-start; }
    svg { width: 100%; height: auto; }
    @media print {
      @page { size: A3 landscape; margin: 8mm; }
      .page { width: 100%; padding: 0; }
    }
  </style>
</head>
<body>
  <div class="page">
    <p class="page-title">Blockschaltbild — Einspeisungs- und Verteilerstruktur</p>
    ${blockSvg}
  </div>
  <div class="page">
    <p class="page-title">CAD E-Plan — Blatt 1: USV-Einspeisung RZ</p>
    ${blatt1Svg}
  </div>
  <div class="page">
    <p class="page-title">CAD E-Plan — Blatt 2: UV-USV-01 Verteilung</p>
    ${blatt2Svg}
  </div>
  <div class="page">
    <p class="page-title">CAD E-Plan — Blatt 3: Batterieanlage 2-strängig + BMS</p>
    ${blatt3Svg}
  </div>
</body>
</html>`;

      const win = window.open('', '_blank', 'width=1200,height=900');
      if (!win) { alert('Popup blockiert — bitte Popups für diese Seite erlauben.'); return; }
      win.document.write(html);
      win.document.close();
      win.onload = () => { win.focus(); win.print(); };
    } finally {
      pdfLoading = false;
    }
  }
</script>

<div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-6 min-h-[85vh] flex flex-col">
  <div class="flex items-center justify-between mb-6">
    <div>
      <h3 class="text-xl font-bold text-[var(--color-text)] mb-1">Stromlaufplan & Topologie</h3>
      <p class="text-sm text-[var(--color-text2)]">
        Einspeisungs- und Verteilerstruktur des RZs (USV, Hauptverteilung, PDUs).
      </p>
    </div>
    
    <!-- PDF Button + Tab Toggle -->
    <div class="flex items-center gap-3">
      <!-- USV Selector -->
      {#if allUsvUnits.length > 0}
        <select 
          bind:value={selectedUsvId}
          class="bg-[var(--color-bg3)] border border-[var(--color-border2)] text-[var(--color-text)] text-sm rounded-lg px-3 py-2 outline-none focus:border-emerald-500"
        >
          {#each allUsvUnits as u}
            <option value={u.id}>{u.bezeichnung} ({u.hersteller})</option>
          {/each}
        </select>
      {/if}

      <button
        onclick={printEplan}
        disabled={pdfLoading}
        class="flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium bg-[#1D9E75] hover:bg-[#0F6E56] disabled:opacity-50 text-[var(--color-text)] transition-colors"
      >
        <Download class="w-4 h-4" />
        <span>{pdfLoading ? 'Wird geladen…' : 'PDF Export'}</span>
      </button>
    <div class="flex items-center bg-[var(--color-bg3)] border border-[var(--color-border)] rounded-lg p-1">
      <button 
        class="flex items-center space-x-2 px-4 py-2 rounded-md text-sm font-medium transition-all {activeTab === 'block' ? 'bg-[var(--color-border)] text-[var(--color-text)] shadow' : 'text-[var(--color-text2)] hover:text-[var(--color-text)]'}"
        onclick={() => activeTab = 'block'}
      >
        <Grid class="w-4 h-4" />
        <span>Blockschaltbild</span>
      </button>
      <button
        class="flex items-center space-x-2 px-4 py-2 rounded-md text-sm font-medium transition-all {activeTab === 'cad' ? 'bg-[var(--color-border)] text-[var(--color-text)] shadow' : 'text-[var(--color-text2)] hover:text-[var(--color-text)]'}"
        onclick={() => activeTab = 'cad'}
      >
        <FileText class="w-4 h-4" />
        <span>CAD E-Plan</span>
      </button>
    </div>
    </div>
  </div>

  <div class="flex-1 flex flex-col">
    <div class:hidden={activeTab !== 'block'}>
      <!-- EXISTING BLOCK DIAGRAM -->
      <div class="grid grid-cols-1 lg:grid-cols-4 gap-6 h-full">
        <div id="eplan-block" class="lg:col-span-3 bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-4 flex justify-center">
          <svg viewBox="0 0 700 850" class="w-full max-w-[650px] h-auto">
            <defs>
              <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#64748b" />
              </marker>
            </defs>

            {#each Array(17) as _, i}
              <line x1="0" y1={i * 50} x2="700" y2={i * 50} stroke="#1e293b" stroke-width="0.5" />
            {/each}
            {#each Array(14) as _, i}
              <line x1={i * 50} y1="0" x2={i * 50} y2="850" stroke="#1e293b" stroke-width="0.5" />
            {/each}

            <!-- Netz to UV-RZ-01 (Sicherung moved inside UV) -->
            <line x1="350" y1="50" x2="350" y2="150" stroke="#475569" stroke-width="2.5" marker-end="url(#arrow)" />

            <!-- UV-RZ-01 to Branches -->
            <path d="M 350 270 L 350 320" fill="none" stroke="#475569" stroke-width="2.5" />
            <path d="M 350 320 L 180 320 L 180 430" fill="none" stroke="#475569" stroke-width="2.5" marker-end="url(#arrow)" />
            <path d="M 350 320 L 520 320 L 520 430" fill="none" stroke="#475569" stroke-width="2.5" marker-end="url(#arrow)" />

            <path d="M 180 490 L 180 570 L 290 570" fill="none" stroke="#10b981" stroke-width="3" marker-end="url(#arrow)" />
            <path d="M 430 380 L 520 380 L 520 490" fill="none" stroke="#ef4444" stroke-dasharray="5,4" stroke-width="2.5" />
            <path d="M 520 490 L 520 570 L 400 570" fill="none" stroke="#ef4444" stroke-dasharray="5,4" stroke-width="2.5" marker-end="url(#arrow)" />
            <line x1="350" y1="600" x2="350" y2="650" stroke="#475569" stroke-width="2.5" marker-end="url(#arrow)" />

            <path d="M 230 710 L 130 710 L 130 760" fill="none" stroke="#3b82f6" stroke-width="2" marker-end="url(#arrow)" />
            <line x1="350" y1="710" x2="350" y2="760" stroke="#eab308" stroke-width="2" marker-end="url(#arrow)" />
            <path d="M 470 710 L 570 710 L 570 760" fill="none" stroke="#a855f7" stroke-width="2" marker-end="url(#arrow)" />

            <!-- Netz -->
            <rect x="230" y="10" width="240" height="40" rx="6" fill="#1e293b" stroke="#475569" stroke-width="1.5" />
            <text x="350" y="28" fill="#f8fafc" font-size="11" font-weight="bold" text-anchor="middle">Netz 3~ 400V / 50Hz</text>
            <text x="350" y="42" fill="#94a3b8" font-size="9" text-anchor="middle">Hauptverteilung (HV)</text>

            <!-- UV-RZ-01 (now includes the fuses) -->
            <rect x="210" y="150" width="280" height="120" rx="6" fill="#0f172a" stroke="#334155" stroke-width="1.5" />
            <text x="350" y="172" fill="#f8fafc" font-size="12" font-weight="bold" text-anchor="middle">Unterverteilung UV-RZ-01</text>
            <rect x="250" y="185" width="200" height="40" rx="4" fill="#1e1b4b" stroke="#4338ca" stroke-width="1" />
            <text x="350" y="202" fill="#f8fafc" font-size="10" font-weight="bold" text-anchor="middle">NH-Sicherung 80A gG</text>
            <text x="350" y="215" fill="#818cf8" font-size="8" text-anchor="middle">3-polige Hauptabsicherung</text>
            <text x="350" y="240" fill="#94a3b8" font-size="9" text-anchor="middle">Hauptzuleitung ungepuffert</text>
            <text x="350" y="255" fill="#64748b" font-size="8" text-anchor="middle">LS 3P 63A Abgänge</text>

            <!-- USV Schrank (Left Branch) -->
            <rect x="80" y="430" width="200" height="60" rx="6" fill="#064e3b" stroke="#059669" stroke-width="1.5" />
            <text x="180" y="452" fill="#ecfdf5" font-size="11" font-weight="bold" text-anchor="middle">USV-Schrank 40 kW</text>
            <text x="180" y="468" fill="#a7f3d0" font-size="9" text-anchor="middle">WP2-R / 93PM (N+1)</text>
            <text x="180" y="482" fill="#34d399" font-size="8" text-anchor="middle">Zuleitung: NYY-J 5x16 mm²</text>

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
            <text x="350" y="702" fill="#4ade80" font-size="8" text-anchor="middle">RCBO Typ B 16A Abgänge</text>

            <!-- PDU L1 -->
            <rect x="30" y="760" width="200" height="60" rx="6" fill="#1e293b" stroke="#3b82f6" stroke-width="1.5" />
            <text x="130" y="780" fill="#f8fafc" font-size="10" font-weight="bold" text-anchor="middle">SmartPDU A-0UL</text>
            <text x="130" y="794" fill="#94a3b8" font-size="8" text-anchor="middle">Phase L1 | 3x2.5 mm²</text>
            <text x="130" y="808" fill="#60a5fa" font-size="8" text-anchor="middle">Server Netzteile A</text>

            <!-- PDU L2 -->
            <rect x="250" y="760" width="200" height="60" rx="6" fill="#1e293b" stroke="#eab308" stroke-width="1.5" />
            <text x="350" y="780" fill="#f8fafc" font-size="10" font-weight="bold" text-anchor="middle">SmartPDU A-0UR</text>
            <text x="350" y="794" fill="#94a3b8" font-size="8" text-anchor="middle">Phase L2 | 3x2.5 mm²</text>
            <text x="350" y="808" fill="#facc15" font-size="8" text-anchor="middle">Server Netzteile B</text>

            <!-- PDU L3 -->
            <rect x="470" y="760" width="200" height="60" rx="6" fill="#1e293b" stroke="#a855f7" stroke-width="1.5" />
            <text x="570" y="780" fill="#f8fafc" font-size="10" font-weight="bold" text-anchor="middle">SmartPDU B-0UL</text>
            <text x="570" y="794" fill="#94a3b8" font-size="8" text-anchor="middle">Phase L3 | 3x2.5 mm²</text>
            <text x="570" y="808" fill="#c084fc" font-size="8" text-anchor="middle">Redundante A/B Server</text>
          </svg>
        </div>

        <div class="space-y-4">
          <div class="bg-[var(--color-bg3)] border border-[var(--color-border2)]/50 rounded-xl p-4">
            <h4 class="text-xs font-semibold text-[var(--color-text)] uppercase tracking-wider mb-3">Legende & Kabel</h4>
            <div class="space-y-3 text-xs">
              <div class="flex items-center space-x-2">
                <div class="w-4 h-1 bg-slate-500"></div>
                <span class="text-[var(--color-text2)]">Normalnetz (ungepuffert)</span>
              </div>
              <div class="flex items-center space-x-2">
                <div class="w-4 h-1 bg-emerald-500"></div>
                <span class="text-[var(--color-text2)]">USV-Pfad (aktiv gepuffert)</span>
              </div>
              <div class="flex items-center space-x-2">
                <div class="w-4 h-1 bg-red-500 stroke-dasharray-2"></div>
                <span class="text-[var(--color-text2)]">Direktnetz / Bypass</span>
              </div>
            </div>
          </div>
          <div class="bg-[var(--color-bg3)] border border-[var(--color-border2)]/50 rounded-xl p-4 text-xs text-[var(--color-text2)] leading-relaxed space-y-2">
            <h4 class="text-xs font-semibold text-[var(--color-text)] uppercase tracking-wider">Information</h4>
            <p>
              Dieses Blockschaltbild zeigt die logische Topologie. Die Sicherungen (NH) sind nun korrekt innerhalb der UV-RZ-01 dargestellt. Wechsle auf den Reiter "CAD E-Plan", um den allpoligen Stromlaufplan zu sehen.
            </p>
          </div>
        </div>
      </div>
    
    </div>
    <div class:hidden={activeTab !== 'cad'}>
      <!-- NEW CAD E-PLAN SVG -->
      <div class="bg-white border-2 border-slate-300 rounded shadow-inner p-4 w-full h-full flex justify-center overflow-auto" style="min-height: 800px;">
        <svg id="eplan-blatt1" viewBox="0 0 1000 700" class="w-full max-w-[1200px] h-auto drop-shadow-sm font-sans" shape-rendering="crispEdges">
          
          <!-- Outer Frame (DIN format logic) -->
          <rect x="20" y="20" width="960" height="660" fill="none" stroke="#334155" stroke-width="2" />
          
          <!-- Drawing Area Grid marks -->
          {#each Array(10) as _, i}
            <line x1={20 + (i * 96)} y1="15" x2={20 + (i * 96)} y2="25" stroke="#94a3b8" stroke-width="1" />
            <text x={68 + (i * 96)} y="15" font-size="10" fill="#94a3b8" text-anchor="middle">{i}</text>
          {/each}
          {#each Array(6) as _, i}
            <line x1="15" y1={20 + (i * 110)} x2="25" y2={20 + (i * 110)} stroke="#94a3b8" stroke-width="1" />
            <text x="10" y={75 + (i * 110)} font-size="10" fill="#94a3b8" text-anchor="end">{String.fromCharCode(65 + i)}</text>
          {/each}

          <!-- Title Block (Schriftfeld nach DIN) -->
          <g transform="translate(680, 580)">
            <rect x="0" y="0" width="300" height="100" fill="none" stroke="#334155" stroke-width="2" />
            <!-- Rows -->
            <line x1="0" y1="20" x2="300" y2="20" stroke="#334155" stroke-width="1" />
            <line x1="0" y1="40" x2="300" y2="40" stroke="#334155" stroke-width="1" />
            <line x1="0" y1="80" x2="300" y2="80" stroke="#334155" stroke-width="1" />
            <!-- Cols -->
            <line x1="100" y1="0" x2="100" y2="40" stroke="#334155" stroke-width="1" />
            <line x1="200" y1="80" x2="200" y2="100" stroke="#334155" stroke-width="1" />
            <line x1="250" y1="80" x2="250" y2="100" stroke="#334155" stroke-width="1" />
            
            <text x="5" y="14" font-size="9" fill="#64748b">Datum</text>
            <text x="40" y="14" font-size="10" fill="#0f172a" font-weight="bold">{new Date().toISOString().split('T')[0]}</text>
            
            <text x="105" y="14" font-size="9" fill="#64748b">Bearbeiter</text>
            <text x="155" y="14" font-size="10" fill="#0f172a" font-weight="bold">Andreas</text>
            
            <text x="5" y="34" font-size="9" fill="#64748b">Geprüft</text>
            <text x="105" y="34" font-size="9" fill="#64748b">Norm</text>
            <text x="155" y="34" font-size="10" fill="#0f172a">EN 61082-1</text>
            
            <text x="5" y="55" font-size="11" fill="#64748b">Projektbezeichnung:</text>
            <text x="5" y="72" font-size="16" fill="#0f172a" font-weight="bold">KAiTix</text>

            <text x="5" y="94" font-size="11" fill="#0f172a">Anlage: USV-Einspeisung RZ</text>
            <text x="205" y="94" font-size="10" fill="#64748b">Blatt:</text>
            <text x="235" y="94" font-size="11" fill="#0f172a" font-weight="bold">1</text>
            
            <text x="255" y="94" font-size="10" fill="#64748b">V.Bl.:</text>
            <text x="285" y="94" font-size="11" fill="#0f172a">-</text>
          </g>

          <!-- ============================================== -->
          <!-- SCHALTPLAN LOGIC -->
          <!-- ============================================== -->
          <g stroke-linecap="round" stroke-linejoin="round">
            
            <!-- Horizontal Busbars (Potentiale) -->
            <g stroke-width="1.5">
              <line x1="50" y1="80" x2="950" y2="80" stroke="#78350f" /> <text x="35" y="83" font-size="10" fill="#78350f" font-weight="bold">L1</text>
              <line x1="50" y1="100" x2="950" y2="100" stroke="#0f172a" /> <text x="35" y="103" font-size="10" fill="#0f172a" font-weight="bold">L2</text>
              <line x1="50" y1="120" x2="950" y2="120" stroke="#475569" /> <text x="35" y="123" font-size="10" fill="#475569" font-weight="bold">L3</text>
              <line x1="50" y1="140" x2="950" y2="140" stroke="#2563eb" /> <text x="35" y="143" font-size="10" fill="#2563eb" font-weight="bold">N</text>
              <line x1="50" y1="160" x2="950" y2="160" stroke="#16a34a" stroke-dasharray="8,4" /> <text x="35" y="163" font-size="10" fill="#16a34a" font-weight="bold">PE</text>
            </g>

            <!-- Abzweig 1: UV-RZ-01 Einspeisung (zentriert mit F1) -->
            <!-- Connection Dots on Busbars -->
            <circle cx="300" cy="80" r="3" fill="white" stroke="#78350f" stroke-width="1.5"/>
            <circle cx="320" cy="100" r="3" fill="white" stroke="#0f172a" stroke-width="1.5"/>
            <circle cx="340" cy="120" r="3" fill="white" stroke="#475569" stroke-width="1.5"/>
            <circle cx="260" cy="140" r="3" fill="white" stroke="#2563eb" stroke-width="1.5"/>
            <circle cx="280" cy="160" r="3" fill="white" stroke="#16a34a" stroke-width="1.5"/>
            <circle cx="380" cy="140" r="3" fill="white" stroke="#2563eb" stroke-width="1.5"/>
            <circle cx="400" cy="160" r="3" fill="white" stroke="#16a34a" stroke-width="1.5"/>
            
            <!-- Vertical Drops from Busbars to -F1 -->
            <line x1="300" y1="80" x2="300" y2="250" stroke="#78350f" stroke-width="1"/>
            <line x1="320" y1="100" x2="320" y2="250" stroke="#0f172a" stroke-width="1"/>
            <line x1="340" y1="120" x2="340" y2="250" stroke="#475569" stroke-width="1"/>
            
            <!-- N and PE drops for USV feed (to -X1 terminals 4-5) -->
            <!-- N runs through Q1 -->
            <line x1="260" y1="140" x2="260" y2="350" stroke="#2563eb" stroke-width="1"/>
            <!-- PE goes straight -->
            <line x1="280" y1="160" x2="280" y2="450" stroke="#16a34a" stroke-width="1" stroke-dasharray="6,3"/>
            <!-- N and PE from -X1 terminals 4-5 down to bottom -->
            <line x1="260" y1="453" x2="260" y2="520" stroke="#2563eb" stroke-width="1"/>
            <line x1="280" y1="453" x2="280" y2="520" stroke="#16a34a" stroke-width="1" stroke-dasharray="6,3"/>



            <!-- Box UV-RZ-01 =A1 -->
            <rect x="150" y="220" width="450" height="260" fill="none" stroke="#64748b" stroke-dasharray="10,5" stroke-width="1"/>
            <text x="160" y="215" font-size="12" font-weight="bold" fill="#0f172a">=A1</text>
            <text x="160" y="235" font-size="10" fill="#0f172a">UV-RZ-01</text>

            <!-- -F1 NH-Sicherung 80A im UV -->
            <g stroke="#0f172a" stroke-width="1.5" fill="none">
              <rect x="295" y="250" width="10" height="30"/>
              <line x1="295" y1="250" x2="305" y2="280"/>
              
              <rect x="315" y="250" width="10" height="30"/>
              <line x1="315" y1="250" x2="325" y2="280"/>
              
              <rect x="335" y="250" width="10" height="30"/>
              <line x1="335" y1="250" x2="345" y2="280"/>
              
              <line x1="285" y1="265" x2="355" y2="265" stroke-dasharray="3,3" stroke-width="1"/>
            </g>
            <circle cx="295" cy="250" r="3" fill="white" stroke="#0f172a" stroke-width="1.5"/>
            <circle cx="315" cy="250" r="3" fill="white" stroke="#0f172a" stroke-width="1.5"/>
            <circle cx="335" cy="250" r="3" fill="white" stroke="#0f172a" stroke-width="1.5"/>
            <circle cx="305" cy="280" r="3" fill="white" stroke="#0f172a" stroke-width="1.5"/>
            <circle cx="325" cy="280" r="3" fill="white" stroke="#0f172a" stroke-width="1.5"/>
            <circle cx="345" cy="280" r="3" fill="white" stroke="#0f172a" stroke-width="1.5"/>
            <text x="250" y="265" font-size="10" font-weight="bold" fill="#0f172a">-F1</text>
            <text x="360" y="265" font-size="9" fill="#0f172a">NH 63A</text>

            <!-- Split after fuse (Branch A to USV breaker -Q1, Branch B to Bypass -X1:6-8) -->
            <!-- Branch A to -Q1 -->
            <path d="M 305 280 L 305 290 L 200 290 L 200 350" fill="none" stroke="#78350f" stroke-width="1"/>
            <path d="M 325 280 L 325 295 L 220 295 L 220 350" fill="none" stroke="#0f172a" stroke-width="1"/>
            <path d="M 345 280 L 345 300 L 240 300 L 240 350" fill="none" stroke="#475569" stroke-width="1"/>
            
            <!-- Branch B to -Q2 -->
            <path d="M 305 280 L 305 320 L 320 320 L 320 350" fill="none" stroke="#78350f" stroke-width="1"/>
            <path d="M 325 280 L 325 315 L 340 315 L 340 350" fill="none" stroke="#0f172a" stroke-width="1"/>
            <path d="M 345 280 L 345 310 L 360 310 L 360 350" fill="none" stroke="#475569" stroke-width="1"/>
            <!-- N connection to -Q2 -->
            <path d="M 260 305 L 380 305 L 380 350" fill="none" stroke="#2563eb" stroke-width="1"/>
            <circle cx="260" cy="305" r="2" fill="#0f172a"/>

            <!-- -Q2 Leistungsschalter 63A im UV (Bypass) -->
            <g stroke="#0f172a" stroke-width="1.5" fill="none">
              <!-- Schließer -->
              <line x1="320" y1="350" x2="306" y2="380"/>
              <line x1="340" y1="350" x2="326" y2="380"/>
              <line x1="360" y1="350" x2="346" y2="380"/>
              <!-- N pole (voreilend: angle slightly less steep) -->
              <line x1="380" y1="350" x2="366" y2="380" stroke="#2563eb"/>
              <line x1="305" y1="365" x2="395" y2="365" stroke-dasharray="3,3" stroke-width="1"/>
              <!-- Auslöser 'x' für Leistungsschalter -->
              <path d="M 310 362 L 316 368 M 310 368 L 316 362" stroke="#0f172a" stroke-width="1"/>
              <path d="M 330 362 L 336 368 M 330 368 L 336 362" stroke="#0f172a" stroke-width="1"/>
              <path d="M 350 362 L 356 368 M 350 368 L 356 362" stroke="#0f172a" stroke-width="1"/>
              <path d="M 370 362 L 376 368 M 370 368 L 376 362" stroke="#2563eb" stroke-width="1"/>
            </g>
            <!-- Mechanische Verriegelung Q1 - Q2 -->
            <line x1="255" y1="365" x2="305" y2="365" stroke="#ef4444" stroke-dasharray="4,4" stroke-width="1.5" />
            <polygon points="275,365 285,360 285,370" fill="#ef4444" />
            <circle cx="320" cy="350" r="3" fill="white" stroke="#0f172a" stroke-width="1.5"/>
            <circle cx="340" cy="350" r="3" fill="white" stroke="#0f172a" stroke-width="1.5"/>
            <circle cx="360" cy="350" r="3" fill="white" stroke="#0f172a" stroke-width="1.5"/>
            <circle cx="380" cy="350" r="3" fill="white" stroke="#2563eb" stroke-width="1.5"/>
            <circle cx="306" cy="380" r="3" fill="white" stroke="#0f172a" stroke-width="1.5"/>
            <circle cx="326" cy="380" r="3" fill="white" stroke="#0f172a" stroke-width="1.5"/>
            <circle cx="346" cy="380" r="3" fill="white" stroke="#0f172a" stroke-width="1.5"/>
            <circle cx="366" cy="380" r="3" fill="white" stroke="#2563eb" stroke-width="1.5"/>
            <text x="400" y="360" font-size="10" font-weight="bold" fill="#0f172a">-Q2</text>
            <text x="400" y="370" font-size="9" fill="#0f172a">MCCB 63A 3P+N</text>

            <!-- Drops from -Q2 to -X1 terminals 6-8 -->
            <path d="M 306 380 L 320 380 L 320 450" fill="none" stroke="#78350f" stroke-width="1"/>
            <path d="M 326 380 L 340 380 L 340 450" fill="none" stroke="#0f172a" stroke-width="1"/>
            <path d="M 346 380 L 360 380 L 360 450" fill="none" stroke="#475569" stroke-width="1"/>
            <path d="M 366 380 L 380 380 L 380 450" fill="none" stroke="#2563eb" stroke-width="1"/>

            <!-- -Q1 Leistungsschalter 63A im UV -->
            <g stroke="#0f172a" stroke-width="1.5" fill="none">
              <!-- Schließer -->
              <line x1="200" y1="350" x2="186" y2="380"/>
              <line x1="220" y1="350" x2="206" y2="380"/>
              <line x1="240" y1="350" x2="226" y2="380"/>
              <!-- N pole -->
              <line x1="260" y1="350" x2="246" y2="380" stroke="#2563eb"/>
              <line x1="185" y1="365" x2="275" y2="365" stroke-dasharray="3,3" stroke-width="1"/>
              <!-- Auslöser 'x' für Leistungsschalter -->
              <path d="M 190 362 L 196 368 M 190 368 L 196 362" stroke="#0f172a" stroke-width="1"/>
              <path d="M 210 362 L 216 368 M 210 368 L 216 362" stroke="#0f172a" stroke-width="1"/>
              <path d="M 230 362 L 236 368 M 230 368 L 236 362" stroke="#0f172a" stroke-width="1"/>
              <path d="M 250 362 L 256 368 M 250 368 L 256 362" stroke="#2563eb" stroke-width="1"/>
            </g>
            <circle cx="200" cy="350" r="3" fill="white" stroke="#0f172a" stroke-width="1.5"/>
            <circle cx="220" cy="350" r="3" fill="white" stroke="#0f172a" stroke-width="1.5"/>
            <circle cx="240" cy="350" r="3" fill="white" stroke="#0f172a" stroke-width="1.5"/>
            <circle cx="260" cy="350" r="3" fill="white" stroke="#2563eb" stroke-width="1.5"/>
            <circle cx="186" cy="380" r="3" fill="white" stroke="#0f172a" stroke-width="1.5"/>
            <circle cx="206" cy="380" r="3" fill="white" stroke="#0f172a" stroke-width="1.5"/>
            <circle cx="226" cy="380" r="3" fill="white" stroke="#0f172a" stroke-width="1.5"/>
            <circle cx="246" cy="380" r="3" fill="white" stroke="#2563eb" stroke-width="1.5"/>
            <text x="175" y="360" font-size="10" font-weight="bold" fill="#0f172a" text-anchor="end">-Q1</text>
            <text x="175" y="370" font-size="9" fill="#0f172a" text-anchor="end">MCCB 63A 3P+N</text>
            
            <!-- Drops to Terminal -X1 (bridge diagonal exit → vertical) -->
            <path d="M 186 380 L 200 380 L 200 450" fill="none" stroke="#78350f" stroke-width="1"/>
            <path d="M 206 380 L 220 380 L 220 450" fill="none" stroke="#0f172a" stroke-width="1"/>
            <path d="M 226 380 L 240 380 L 240 450" fill="none" stroke="#475569" stroke-width="1"/>
            <path d="M 246 380 L 260 380 L 260 450" fill="none" stroke="#2563eb" stroke-width="1"/>

            <!-- -X1 Klemmenleiste Abgang USV & Bypass N/PE -->
            <g fill="#ffffff" stroke="#0f172a" stroke-width="1.5">
              <circle cx="200" cy="450" r="4.5"/>
              <circle cx="220" cy="450" r="4.5"/>
              <circle cx="240" cy="450" r="4.5"/>
              <circle cx="260" cy="450" r="4.5"/>
              <circle cx="270" cy="450" r="4.5"/>
              <circle cx="280" cy="450" r="4.5"/>
              <circle cx="290" cy="450" r="4.5"/>
            </g>
            <!-- Terminal Bridges -->
            <line x1="260" y1="450" x2="270" y2="450" stroke="#0f172a" stroke-width="1.5"/>
            <line x1="280" y1="450" x2="290" y2="450" stroke="#0f172a" stroke-width="1.5"/>
            <text x="206" y="452" font-size="7" fill="#64748b" font-weight="bold">1</text>
            <text x="226" y="452" font-size="7" fill="#64748b" font-weight="bold">2</text>
            <text x="246" y="452" font-size="7" fill="#64748b" font-weight="bold">3</text>
            <text x="254" y="440" font-size="7" fill="#64748b" font-weight="bold">4:1</text>
            <text x="264" y="460" font-size="7" fill="#64748b" font-weight="bold">4:2</text>
            <text x="274" y="440" font-size="7" fill="#64748b" font-weight="bold">5:1</text>
            <text x="284" y="460" font-size="7" fill="#64748b" font-weight="bold">5:2</text>
            <text x="160" y="455" font-size="10" font-weight="bold" fill="#0f172a">-X1</text>

            <!-- Zuleitung zur USV -W1 (fächert auf GR + Bypass) -->
            <path d="M 200 453 L 200 495 L 175 516" fill="none" stroke="#78350f" stroke-width="1"/>
            <line x1="220" y1="453" x2="220" y2="516" stroke="#0f172a" stroke-width="1"/>
            <path d="M 240 453 L 240 495 L 285 516" fill="none" stroke="#475569" stroke-width="1"/>
            <!-- W1 designation -->
            <path d="M 180 480 C 190 470, 290 470, 300 480" fill="none" stroke="#64748b" stroke-width="1" stroke-dasharray="2,2"/>
            <text x="310" y="483" font-size="9" fill="#0f172a">-W1 <tspan fill="#64748b">(NYY-J 5x25 mm²)</tspan></text>

            <!-- USV-Anlage =T1 mit GR/WR/Bypass/Batterie -->
            <rect x="130" y="516" width="200" height="134" fill="#f8fafc" stroke="#0f172a" stroke-width="2"/>
            <text x="230" y="534" font-size="12" font-weight="bold" text-anchor="middle" fill="#0f172a">=T1  USV-Anlage 40kW</text>
            
            <!-- GR block -->
            <rect x="143" y="542" width="64" height="36" fill="#f8fafc" stroke="#0f172a" stroke-width="1"/>
            <text x="175" y="557" font-size="10" font-weight="bold" text-anchor="middle" fill="#0f172a">GR</text>
            <text x="175" y="569" font-size="8" text-anchor="middle" fill="#0f172a">[Q1]</text>
            
            <!-- Static Bypass block -->
            <rect x="253" y="542" width="64" height="36" fill="#f8fafc" stroke="#0f172a" stroke-width="1"/>
            <text x="285" y="555" font-size="10" font-weight="bold" text-anchor="middle" fill="#0f172a">Bypass</text>
            <text x="285" y="569" font-size="8" text-anchor="middle" fill="#0f172a">[Q2]</text>
            
            <!-- Connection dots at box top edge (AC IN) -->
            <circle cx="175" cy="516" r="3" fill="white" stroke="#78350f" stroke-width="1.5"/>
            <circle cx="220" cy="516" r="3" fill="white" stroke="#0f172a" stroke-width="1.5"/>
            <circle cx="285" cy="516" r="3" fill="white" stroke="#475569" stroke-width="1.5"/>
            
            <!-- AC IN bus (L1+L2 to GR, L3 to Bypass) -->
            <line x1="175" y1="516" x2="175" y2="542" stroke="#78350f" stroke-width="1"/>
            <line x1="220" y1="516" x2="220" y2="530" stroke="#0f172a" stroke-width="1"/>
            <line x1="220" y1="530" x2="175" y2="530" stroke="#0f172a" stroke-width="0.5"/>
            <line x1="175" y1="530" x2="175" y2="542" stroke="#0f172a" stroke-width="1"/>
            <line x1="285" y1="516" x2="285" y2="542" stroke="#475569" stroke-width="1"/>
            
            <!-- AC bus cross-feed to Bypass (3 phases) -->
            <line x1="175" y1="526" x2="285" y2="526" stroke="#78350f" stroke-width="0.5" stroke-dasharray="2,2"/>
            <line x1="220" y1="526" x2="285" y2="526" stroke="#0f172a" stroke-width="0.5" stroke-dasharray="2,2"/>
            
            <!-- DC bus (horizontal) -->
            <line x1="143" y1="584" x2="317" y2="584" stroke="#0f172a" stroke-width="1"/>
            <!-- DC dots -->
            <circle cx="175" cy="584" r="3" fill="white" stroke="#0f172a" stroke-width="1.5"/>
            <circle cx="285" cy="584" r="3" fill="white" stroke="#0f172a" stroke-width="1.5"/>
            
            <!-- GR → DC bus -->
            <line x1="175" y1="578" x2="175" y2="584" stroke="#0f172a" stroke-width="1"/>
            
            <!-- DC-Abgang Klemmenleiste -X-BAT -->
            <rect x="143" y="590" width="64" height="34" fill="#f8fafc" stroke="#0f172a" stroke-width="1"/>
            <text x="175" y="605" font-size="9" font-weight="bold" text-anchor="middle" fill="#0f172a">-X-BAT</text>
            <text x="175" y="618" font-size="7" text-anchor="middle" fill="#0f172a">DC Abgang</text>
            
            <!-- DC bus → Klemmenleiste -->
            <line x1="175" y1="584" x2="175" y2="590" stroke="#0f172a" stroke-width="1"/>

            <!-- Abgehende Leitung -W3 (DC+ und DC-) nach links -->
            <path d="M 143 600 L 50 600" fill="none" stroke="#dc2626" stroke-width="1.5"/>
            <path d="M 143 614 L 50 614" fill="none" stroke="#1d4ed8" stroke-width="1.5"/>
            
            <!-- Anschluss-Punkte an der Klemmenleiste -->
            <circle cx="143" cy="600" r="2.5" fill="white" stroke="#0f172a" stroke-width="1.5"/>
            <circle cx="143" cy="614" r="2.5" fill="white" stroke="#0f172a" stroke-width="1.5"/>
            <text x="135" y="598" font-size="6" fill="#dc2626" text-anchor="end">DC+</text>
            <text x="135" y="618" font-size="6" fill="#1d4ed8" text-anchor="end">DC−</text>
            
            <!-- Leitungsbezeichnung & Querverweis -->
            <path d="M 60 585 C 70 595, 80 595, 90 585" fill="none" stroke="#64748b" stroke-width="1" stroke-dasharray="2,2"/>
            <text x="95" y="588" font-size="9" fill="#0f172a">-W3 <tspan fill="#64748b">(NYY-J 2x25 mm²)</tspan></text>
            
            <!-- Pfeile am Ende der Leitung (als Querverweis) -->
            <polygon points="50,600 58,597 58,603" fill="#dc2626" />
            <polygon points="50,614 58,611 58,617" fill="#1d4ed8" />
            <text x="45" y="630" font-size="9" font-style="italic" fill="#64748b" text-anchor="start">Weiter zur Batterieanlage (Bl. 3)</text>
            
            <!-- WR block -->
            <rect x="253" y="590" width="64" height="34" fill="#f8fafc" stroke="#0f172a" stroke-width="1"/>
            <text x="285" y="605" font-size="9" font-weight="bold" text-anchor="middle" fill="#0f172a">WR</text>
            <text x="285" y="617" font-size="7" text-anchor="middle" fill="#0f172a">[Q3]</text>
            
            <!-- DC bus → WR -->
            <line x1="285" y1="584" x2="285" y2="590" stroke="#0f172a" stroke-width="1"/>
            
            <!-- WR output → AC OUT (bottom) -->
            <line x1="220" y1="624" x2="220" y2="646" stroke="#0f172a" stroke-width="1"/>
            <line x1="285" y1="624" x2="285" y2="646" stroke="#475569" stroke-width="1"/>
            <!-- Bypass output → AC OUT -->
            <line x1="285" y1="578" x2="285" y2="584" stroke="#475569" stroke-width="0.5" stroke-dasharray="2,2"/>
            
            <!-- Connection dots at box bottom edge (AC OUT) -->
            <circle cx="200" cy="646" r="3" fill="white" stroke="#78350f" stroke-width="1.5"/>
            <circle cx="220" cy="646" r="3" fill="white" stroke="#0f172a" stroke-width="1.5"/>
            <circle cx="240" cy="646" r="3" fill="white" stroke="#475569" stroke-width="1.5"/>
            
            <!-- Internal AC OUT bus -->
            <path d="M 200 640 L 200 646" fill="none" stroke="#78350f" stroke-width="1"/>
            <path d="M 175 640 L 175 646 L 200 646" fill="none" stroke="#78350f" stroke-width="0.5"/>
            <path d="M 220 624 L 220 646" fill="none" stroke="#0f172a" stroke-width="1"/>
            <path d="M 285 646 L 240 646" fill="none" stroke="#475569" stroke-width="0.5"/>
            
            <!-- Output from USV to MBS -->
            <line x1="200" y1="646" x2="200" y2="650" stroke="#78350f" stroke-width="1"/>
            <line x1="220" y1="646" x2="220" y2="645" stroke="#0f172a" stroke-width="1"/>
            <line x1="240" y1="646" x2="240" y2="640" stroke="#475569" stroke-width="1"/>
            
            <path d="M 200 650 L 350 650 L 350 590" fill="none" stroke="#78350f" stroke-width="1"/>
            <path d="M 220 645 L 370 645 L 370 590" fill="none" stroke="#0f172a" stroke-width="1"/>
            <path d="M 240 640 L 390 640 L 390 590" fill="none" stroke="#475569" stroke-width="1"/>

            <!-- Abzweig 2 (Bypass) entfällt, da direkt nach -F1 abgezweigt -->

            <!-- -X1 Klemmenleiste Abgang MBS (Bypass Klemmen 6-9) -->
            <g fill="#ffffff" stroke="#0f172a" stroke-width="1.5">
              <circle cx="320" cy="450" r="4.5"/>
              <circle cx="340" cy="450" r="4.5"/>
              <circle cx="360" cy="450" r="4.5"/>
              <circle cx="380" cy="450" r="4.5"/>
            </g>
            <text x="326" y="452" font-size="7" fill="#64748b" font-weight="bold">6</text>
            <text x="346" y="452" font-size="7" fill="#64748b" font-weight="bold">7</text>
            <text x="366" y="452" font-size="7" fill="#64748b" font-weight="bold">8</text>
            <text x="386" y="452" font-size="7" fill="#64748b" font-weight="bold">9</text>

            <!-- Cable -W2 from -X1 to MBS -->
            <path d="M 310 475 C 320 465, 410 465, 420 475" fill="none" stroke="#64748b" stroke-width="1" stroke-dasharray="2,2"/>
            <text x="430" y="478" font-size="9" fill="#0f172a">-W2 <tspan fill="#64748b">(NYY-J 5x25 mm²)</tspan></text>

            <!-- Wiring from -X1 to MBS (=S1) and N/PE busbars -->
            <path d="M 320 453 L 320 490 L 450 490 L 450 520" fill="none" stroke="#78350f" stroke-width="1"/>
            <path d="M 340 453 L 340 485 L 470 485 L 470 520" fill="none" stroke="#0f172a" stroke-width="1"/>
            <path d="M 360 453 L 360 480 L 490 480 L 490 520" fill="none" stroke="#475569" stroke-width="1"/>
            <!-- Bypass N goes down to join N path at y=475 -->
            <path d="M 380 453 L 380 475" fill="none" stroke="#2563eb" stroke-width="1"/>
            <circle cx="380" cy="475" r="2" fill="#0f172a"/>
            <!-- N and PE von USV Klemmen (4:2, 5:2) zum MBS (im 5-adrigen Kabel -W2) -->
            <path d="M 270 453 L 270 475 L 510 475 L 510 654" fill="none" stroke="#2563eb" stroke-width="1"/>
            <path d="M 290 453 L 290 470 L 530 470 L 530 652" fill="none" stroke="#16a34a" stroke-width="1" stroke-dasharray="6,3"/>

            <rect x="350" y="520" width="200" height="70" fill="#f8fafc" stroke="#0f172a" stroke-width="1.5" stroke-dasharray="5,3"/>
            <text x="450" y="545" font-size="12" font-weight="bold" text-anchor="middle" fill="#0f172a">=S1</text>
            <text x="450" y="560" font-size="10" text-anchor="middle" fill="#0f172a">MBS Schalter (1-0-2)</text>
            <text x="450" y="575" font-size="8" text-anchor="middle" fill="#64748b">Handumgehung</text>
            <text x="450" y="585" font-size="6" text-anchor="middle" fill="#ef4444">Umschaltung nur bei USV-Synchronität (Verriegelt)</text>
            
            <!-- Output from MBS to Load -->
            <line x1="430" y1="590" x2="430" y2="650" stroke="#78350f" stroke-width="1"/>
            <line x1="450" y1="590" x2="450" y2="650" stroke="#0f172a" stroke-width="1"/>
            <line x1="470" y1="590" x2="470" y2="650" stroke="#475569" stroke-width="1"/>
            
            <line x1="430" y1="650" x2="600" y2="650" stroke="#78350f" stroke-width="1"/>
            <line x1="450" y1="645" x2="600" y2="645" stroke="#0f172a" stroke-width="1"/>
            <line x1="470" y1="640" x2="600" y2="640" stroke="#475569" stroke-width="1"/>

            <!-- N and PE feed-through to Blatt 2 (bridge busbar drops) -->
            <line x1="260" y1="520" x2="260" y2="654" stroke="#2563eb" stroke-width="1"/>
            <line x1="280" y1="520" x2="280" y2="545" stroke="#16a34a" stroke-width="1" stroke-dasharray="6,3"/>
            <line x1="280" y1="545" x2="280" y2="652" stroke="#16a34a" stroke-width="1" stroke-dasharray="6,3"/>
            <line x1="260" y1="654" x2="600" y2="654" stroke="#2563eb" stroke-width="1"/>
            <line x1="280" y1="652" x2="600" y2="652" stroke="#16a34a" stroke-width="1" stroke-dasharray="6,3"/>
            <!-- N/PE junction circles -->
            <circle cx="260" cy="520" r="3" fill="white" stroke="#2563eb" stroke-width="1.5"/>
            <circle cx="280" cy="520" r="3" fill="white" stroke="#16a34a" stroke-width="1.5"/>
            <circle cx="260" cy="654" r="3" fill="white" stroke="#2563eb" stroke-width="1.5"/>
            <circle cx="280" cy="652" r="3" fill="white" stroke="#16a34a" stroke-width="1.5"/>
            <circle cx="510" cy="654" r="3" fill="white" stroke="#2563eb" stroke-width="1.5"/>
            <circle cx="530" cy="652" r="3" fill="white" stroke="#16a34a" stroke-width="1.5"/>
            <circle cx="280" cy="520" r="3" fill="white" stroke="#16a34a" stroke-width="1.5"/>
            <circle cx="260" cy="654" r="3" fill="white" stroke="#2563eb" stroke-width="1.5"/>
            <circle cx="280" cy="652" r="3" fill="white" stroke="#16a34a" stroke-width="1.5"/>

            <!-- PE tap to MBS enclosure -->
            <line x1="280" y1="545" x2="350" y2="545" stroke="#16a34a" stroke-width="1" stroke-dasharray="6,3"/>
            <circle cx="280" cy="545" r="3" fill="white" stroke="#16a34a" stroke-width="1.5"/>
            <circle cx="350" cy="545" r="3" fill="white" stroke="#16a34a" stroke-width="1.5"/>
            <text x="315" y="540" font-size="7" fill="#16a34a" text-anchor="middle">PE</text>

            <!-- MBS internal connections: Bypass → Output bus -->
            <line x1="450" y1="520" x2="430" y2="590" stroke="#78350f" stroke-width="0.5" stroke-dasharray="3,3"/>
            <line x1="470" y1="520" x2="450" y2="590" stroke="#0f172a" stroke-width="0.5" stroke-dasharray="3,3"/>
            <line x1="490" y1="520" x2="470" y2="590" stroke="#475569" stroke-width="0.5" stroke-dasharray="3,3"/>
            <circle cx="430" cy="590" r="3" fill="white" stroke="#78350f" stroke-width="1.5"/>
            <circle cx="450" cy="590" r="3" fill="white" stroke="#0f172a" stroke-width="1.5"/>
            <circle cx="470" cy="590" r="3" fill="white" stroke="#475569" stroke-width="1.5"/>
            <!-- MBS internal bus: USV → Output bus -->
            <line x1="350" y1="590" x2="430" y2="590" stroke="#78350f" stroke-width="0.5"/>
            <line x1="370" y1="590" x2="450" y2="590" stroke="#0f172a" stroke-width="0.5"/>
            <line x1="390" y1="590" x2="470" y2="590" stroke="#475569" stroke-width="0.5"/>
            <circle cx="350" cy="590" r="3" fill="white" stroke="#78350f" stroke-width="1.5"/>
            <circle cx="370" cy="590" r="3" fill="white" stroke="#0f172a" stroke-width="1.5"/>
            <circle cx="390" cy="590" r="3" fill="white" stroke="#475569" stroke-width="1.5"/>

            <text x="610" y="645" font-size="10" font-style="italic" fill="#64748b">Weiter zu UV-USV-01 (Blatt 2)</text>
            
          </g>
        </svg>
      </div>

      <!-- BLATT 3: 2-strängige Batterieanlage + BMS -->
      <div id="eplan-blatt3" class="bg-white border-2 border-slate-300 rounded shadow-inner p-4 w-full flex justify-center mt-8" style="min-height: 800px;">
        <svg viewBox="0 0 1000 700" class="w-full max-w-[1200px] h-auto drop-shadow-sm font-sans" shape-rendering="crispEdges">

          <!-- Outer Frame -->
          <rect x="20" y="20" width="960" height="660" fill="none" stroke="#334155" stroke-width="2" />

          <!-- Grid -->
          {#each Array(10) as _, i}
            <line x1={20 + (i * 96)} y1="15" x2={20 + (i * 96)} y2="25" stroke="#94a3b8" stroke-width="1" />
            <text x={68 + (i * 96)} y="15" font-size="10" fill="#94a3b8" text-anchor="middle">{i}</text>
          {/each}
          {#each Array(6) as _, i}
            <line x1="15" y1={20 + (i * 110)} x2="25" y2={20 + (i * 110)} stroke="#94a3b8" stroke-width="1" />
            <text x="10" y={75 + (i * 110)} font-size="10" fill="#94a3b8" text-anchor="end">{String.fromCharCode(65 + i)}</text>
          {/each}

          <!-- Title Block -->
          <g transform="translate(680, 580)">
            <rect x="0" y="0" width="300" height="100" fill="none" stroke="#334155" stroke-width="2" />
            <line x1="0" y1="20" x2="300" y2="20" stroke="#334155" stroke-width="1" />
            <line x1="0" y1="40" x2="300" y2="40" stroke="#334155" stroke-width="1" />
            <line x1="0" y1="80" x2="300" y2="80" stroke="#334155" stroke-width="1" />
            <line x1="100" y1="0" x2="100" y2="40" stroke="#334155" stroke-width="1" />
            <line x1="200" y1="80" x2="200" y2="100" stroke="#334155" stroke-width="1" />
            <line x1="250" y1="80" x2="250" y2="100" stroke="#334155" stroke-width="1" />
            
            <text x="5" y="14" font-size="9" fill="#64748b">Datum</text>
            <text x="40" y="14" font-size="10" fill="#0f172a" font-weight="bold">{new Date().toISOString().split('T')[0]}</text>
            
            <text x="105" y="14" font-size="9" fill="#64748b">Bearbeiter</text>
            <text x="155" y="14" font-size="10" fill="#0f172a" font-weight="bold">Andreas</text>
            <text x="5" y="34" font-size="9" fill="#64748b">Geprüft</text>
            <text x="105" y="34" font-size="9" fill="#64748b">Norm</text><text x="155" y="34" font-size="10" fill="#0f172a">EN 61082-1</text>
            <text x="5" y="55" font-size="11" fill="#64748b">Projektbezeichnung:</text>
            <text x="5" y="72" font-size="16" fill="#0f172a" font-weight="bold">KAiTix</text>
            <text x="5" y="94" font-size="11" fill="#0f172a">Anlage: Batterieanlage 2-strängig + BMS</text>
            <text x="205" y="94" font-size="10" fill="#64748b">Blatt:</text><text x="235" y="94" font-size="11" fill="#0f172a" font-weight="bold">3</text>
            <text x="255" y="94" font-size="10" fill="#64748b">V.Bl.:</text><text x="285" y="94" font-size="11" fill="#0f172a">1</text>
          </g>

          {#if !usvData}
            <text x="500" y="350" font-size="14" fill="#64748b" text-anchor="middle">Lade Batterie-Konfiguration...</text>
          {:else}
            <g stroke-linecap="round" stroke-linejoin="round">
              <text x="30" y="65" font-size="10" font-style="italic" fill="#64748b">Von Blatt 1 — USV =T1 DC-Bus</text>

              <!-- DC+ und DC- Sammelschienen (berechnet) -->
              <line x1="50" y1="80" x2="650" y2="80" stroke="#dc2626" stroke-width="2.5" />
              <text x="35" y="83" font-size="10" fill="#dc2626" font-weight="bold">DC+</text>
              <line x1="50" y1="110" x2="650" y2="110" stroke="#1d4ed8" stroke-width="2.5" />
              <text x="35" y="113" font-size="10" fill="#1d4ed8" font-weight="bold">DC−</text>
              
              <text x="660" y="83" font-size="9" fill="#64748b">USV GR/WR Gleichstromzwischenkreis</text>
              <text x="660" y="113" font-size="9" font-weight="bold" fill="#0f172a">
                ≈ {usvData.blocks_per_string * usvData.block_voltage_v} V DC / Gesamtkapazität: {usvData.battery_strings * usvData.block_capacity_ah} Ah
              </text>

              <!-- Stränge dynamisch generieren -->
              {#each Array(usvData.battery_strings) as _, str_index}
                {@const offsetX = 50 + (str_index * 300)}
                {@const strName = String.fromCharCode(65 + str_index)}
                
                <g transform="translate({offsetX}, 0)">
                  <!-- Strang-Rahmen -->
                  <rect x="0" y="140" width="270" height="380" fill="none" stroke="#059669" stroke-dasharray="8,4" stroke-width="1.5" />
                  <text x="6" y="135" font-size="12" font-weight="bold" fill="#059669">=BAT-{strName}</text>
                  <text x="6" y="150" font-size="10" fill="#059669">Batterie-Strang {strName}</text>

                  <!-- Abgriff DC+ und DC- auf Strang -->
                  <circle cx="122" cy="80" r="3" fill="white" stroke="#dc2626" stroke-width="1.5"/>
                  <line x1="122" y1="80" x2="122" y2="165" stroke="#dc2626" stroke-width="1.5"/>
                  
                  <circle cx="140" cy="110" r="3" fill="white" stroke="#1d4ed8" stroke-width="1.5"/>
                  <line x1="140" y1="110" x2="140" y2="165" stroke="#1d4ed8" stroke-width="1.5"/>

                  <!-- NH-Trennleiter -F-BAT-... -->
                  <g stroke="#0f172a" stroke-width="1.5" fill="none">
                    <rect x="122" y="165" width="10" height="28"/>
                    <line x1="122" y1="165" x2="132" y2="193"/>
                    
                    <rect x="140" y="165" width="10" height="28"/>
                    <line x1="140" y1="165" x2="150" y2="193"/>
                    
                    <line x1="115" y1="179" x2="160" y2="179" stroke-dasharray="3,3" stroke-width="1"/>
                  </g>
                  <circle cx="122" cy="165" r="3" fill="white" stroke="#0f172a" stroke-width="1.5"/>
                  <circle cx="140" cy="165" r="3" fill="white" stroke="#0f172a" stroke-width="1.5"/>
                  <circle cx="132" cy="193" r="3" fill="white" stroke="#0f172a" stroke-width="1.5"/>
                  <circle cx="150" cy="193" r="3" fill="white" stroke="#0f172a" stroke-width="1.5"/>
                  
                  <text x="70" y="182" font-size="10" font-weight="bold" fill="#0f172a">-F-BAT-{strName}</text>
                  <text x="165" y="182" font-size="9" fill="#0f172a">NH00 125A gG 440VDC</text>
                  
                  <!-- Leitungen zu den Blöcken (DC+) und Rückführung (DC-) -->
                  <line x1="132" y1="193" x2="132" y2="230" stroke="#dc2626" stroke-width="1.5"/>
                  <line x1="150" y1="193" x2="150" y2="480" stroke="#1d4ed8" stroke-width="1.5"/>

                  <!-- 4 Blöcke schematisch zeichnen -->
                  {#each Array(4) as _, i}
                    {@const isLast = i === 3}
                    {@const yPos = 230 + (isLast ? 3 * 55 + 50 : i * 55)}

                    {#if isLast}
                      <line x1="132" y1={230 + 3*55 - 15} x2="132" y2={yPos} stroke="#dc2626" stroke-width="1.5" stroke-dasharray="4,4"/>
                      <text x="142" y={yPos - 15} font-size="9" font-style="italic" fill="#64748b">⋯ {usvData.blocks_per_string} Blöcke in Reihe ⋯</text>
                    {:else if i > 0}
                      <line x1="132" y1={230 + (i-1)*55 + 40} x2="132" y2={yPos} stroke="#dc2626" stroke-width="1.5"/>
                    {/if}

                    <!-- Block Gehäuse -->
                    <rect x="105" y={yPos} width="70" height="40" fill="#f0fdf4" stroke="#059669" stroke-width="1.2"/>
                    
                    <!-- Batterie-Symbol (innen) -->
                    <line x1="125" y1={yPos + 18} x2="133" y2={yPos + 18} stroke="#0f172a" stroke-width="1.5"/>
                    <line x1="133" y1={yPos + 13} x2="133" y2={yPos + 23} stroke="#0f172a" stroke-width="2"/>
                    <line x1="136" y1={yPos + 13} x2="136" y2={yPos + 23} stroke="#0f172a" stroke-width="1"/>
                    <line x1="136" y1={yPos + 18} x2="145" y2={yPos + 18} stroke="#0f172a" stroke-width="1.5"/>
                    
                    <text x="140" y={yPos + 33} font-size="7" fill="#059669">{usvData.block_voltage_v}V / {usvData.block_capacity_ah}Ah</text>
                    <text x="108" y={yPos + 12} font-size="8" font-weight="bold" fill="#0f172a">Blk {isLast ? usvData.blocks_per_string : i + 1}</text>
                    
                    <!-- BMS Marker an Block 2 -->
                    {#if i === 1}
                      <rect x="175" y={yPos + 15} width="14" height="14" fill="#ca8a04" rx="2" stroke="#92400e" stroke-width="1"/>
                      <text x="182" y={yPos + 25} font-size="8" font-weight="bold" fill="white" text-anchor="middle">M</text>
                      <line x1="150" y1={yPos + 22} x2="175" y2={yPos + 22} stroke="#ca8a04" stroke-width="1" stroke-dasharray="2,1"/>
                      <!-- BMS Datenbus Abgriff für diesen Strang -->
                      <line x1="189" y1={yPos + 22} x2="255" y2={yPos + 22} stroke="#ca8a04" stroke-width="1" stroke-dasharray="3,2"/>
                      <circle cx="255" cy={yPos + 22} r="2.5" fill="#ca8a04"/>
                    {/if}
                  {/each}

                  <!-- BMS Datenbus (senkrecht für diesen Strang) -->
                  <line x1="255" y1="302" x2="255" y2="525" stroke="#ca8a04" stroke-width="1" stroke-dasharray="3,2"/>
                  <text x="260" y="420" font-size="8" fill="#92400e" transform="rotate(-90,260,420)">BMS-Datenbus Strang {strName}</text>

                  <!-- Brücke vom untersten Block auf den DC- Rückleiter -->
                  <line x1="132" y1={230 + 3 * 55 + 50 + 40} x2="132" y2={480} stroke="#dc2626" stroke-width="1.5"/>
                  <line x1="132" y1={480} x2="150" y2={480} stroke="#1d4ed8" stroke-width="1.5"/>
                  <circle cx="150" cy={480} r="2.5" fill="white" stroke="#1d4ed8" stroke-width="1.5"/>
                </g>
              {/each}

              <!-- ============================================================ -->
              <!-- BMS Controller -->
              <!-- ============================================================ -->
              <!-- Der BMS Controller wird jetzt unter den Strängen fix platziert -->
              <rect x="50" y="550" width="600" height="70" fill="#fefce8" stroke="#ca8a04" stroke-width="2"/>
              <text x="350" y="570" font-size="12" font-weight="bold" text-anchor="middle" fill="#92400e">=BMS  Batterie-Management-System (Controller)</text>
              <text x="350" y="586" font-size="9" text-anchor="middle" fill="#78350f">Einzelblock-Überwachung: U-Block / Innenwiderstand Ri / Temperatur T°</text>
              <text x="350" y="600" font-size="8" text-anchor="middle" fill="#92400e">→ Alarm bei: Δ U > 0.5V | Ri > 150% Referenz | T° > 40°C</text>
              <text x="350" y="614" font-size="8" text-anchor="middle" fill="#64748b">Protokoll: SNMP v3 (Trap → USV-Monitoring / NMS)</text>

              <!-- Bus Linien zum BMS Controller von den Strängen (dynamisch) -->
              {#each Array(usvData.battery_strings) as _, str_index}
                {@const offsetX = 50 + (str_index * 300)}
                <line x1={offsetX + 255} y1="525" x2={offsetX + 255} y2="550" stroke="#ca8a04" stroke-width="1" stroke-dasharray="3,2"/>
                <circle cx={offsetX + 255} cy="550" r="3" fill="#ca8a04"/>
                <text x={offsetX + 240} y="540" font-size="8" fill="#92400e">Bus {String.fromCharCode(65 + str_index)}</text>
              {/each}

              <!-- SNMP-Ausgang BMS → USV -->
              <line x1="650" y1="585" x2="700" y2="585" stroke="#0369a1" stroke-width="1.5" stroke-dasharray="5,3"/>
              <circle cx="650" cy="585" r="3" fill="white" stroke="#0369a1" stroke-width="1.5"/>
              <text x="705" y="589" font-size="9" fill="#0369a1">SNMP v3 → USV / NMS</text>

              <!-- Legende (unverändert) -->
              <rect x="700" y="140" width="280" height="330" fill="#f8fafc" stroke="#334155" stroke-width="1"/>
              <text x="840" y="160" font-size="11" font-weight="bold" text-anchor="middle" fill="#0f172a">Legende & Erläuterung</text>

              <line x1="710" y1="178" x2="740" y2="178" stroke="#dc2626" stroke-width="2.5"/>
              <text x="745" y="182" font-size="9" fill="#0f172a">DC+ Sammelschiene</text>
              <line x1="710" y1="196" x2="740" y2="196" stroke="#1d4ed8" stroke-width="2.5"/>
              <text x="745" y="200" font-size="9" fill="#0f172a">DC− Sammelschiene</text>
              <line x1="710" y1="214" x2="740" y2="214" stroke="#059669" stroke-dasharray="5,3" stroke-width="1.5"/>
              <text x="745" y="218" font-size="9" fill="#0f172a">Strang A (redundanter Pfad)</text>
              <line x1="710" y1="232" x2="740" y2="232" stroke="#7c3aed" stroke-dasharray="5,3" stroke-width="1.5"/>
              <text x="745" y="236" font-size="9" fill="#0f172a">Strang B (redundanter Pfad)</text>
              <line x1="710" y1="250" x2="740" y2="250" stroke="#ca8a04" stroke-dasharray="3,2" stroke-width="1"/>
              <text x="745" y="254" font-size="9" fill="#0f172a">BMS-Datenbus (CAN/RS485)</text>
              <line x1="710" y1="268" x2="740" y2="268" stroke="#0369a1" stroke-dasharray="5,3" stroke-width="1.5"/>
              <text x="745" y="272" font-size="9" fill="#0f172a">SNMP v3 (Monitoring)</text>

              <line x1="700" y1="285" x2="980" y2="285" stroke="#334155" stroke-width="0.5"/>

              <text x="710" y="302" font-size="9" font-weight="bold" fill="#0f172a">Redundanzkonzept (2-strängig):</text>
              <text x="710" y="316" font-size="8" fill="#334155">• Strang A u. B parallel am DC-Bus</text>
              <text x="710" y="328" font-size="8" fill="#334155">• Strangausfall → NH-Trenner auslösen</text>
              <text x="710" y="340" font-size="8" fill="#334155">• Restkapazität: 50 % (≈ 15 min)</text>
              <text x="710" y="352" font-size="8" fill="#334155">• Wartung unter Last möglich</text>
              <text x="710" y="364" font-size="8" fill="#334155">• Kein SPOF durch Einzelblock-Defekt</text>

              <line x1="700" y1="378" x2="980" y2="378" stroke="#334155" stroke-width="0.5"/>

              <text x="710" y="394" font-size="9" font-weight="bold" fill="#0f172a">BMS-Überwachung je Block:</text>
              <text x="710" y="408" font-size="8" fill="#334155">• Blockspannung U [V] → Alterung</text>
              <text x="710" y="420" font-size="8" fill="#334155">• Innenwiderstand Ri [mΩ] → Defekt</text>
              <text x="710" y="432" font-size="8" fill="#334155">• Temperatur T° → Thermal Runaway</text>
              <text x="710" y="444" font-size="8" fill="#334155">• Alarm via SNMP-Trap → USV / NMS</text>

              <line x1="700" y1="458" x2="980" y2="458" stroke="#334155" stroke-width="0.5"/>

              <text x="710" y="472" font-size="9" font-weight="bold" fill="#0f172a">Szenario Zelltod (Strang A):</text>
              <text x="710" y="484" font-size="8" fill="#334155">NH-Trenner A löst → Strang B trägt</text>
              <text x="710" y="496" font-size="8" fill="#059669">Last → RZ läuft weiter (unterbrechungsfrei)</text>
            </g>
          {/if}
        </svg>
      </div>
      <div class="bg-white border-2 border-slate-300 rounded shadow-inner p-4 w-full flex justify-center mt-8" style="min-height: 800px;">
        <svg id="eplan-blatt2" viewBox="0 0 1000 700" class="w-full max-w-[1200px] h-auto drop-shadow-sm font-sans" shape-rendering="crispEdges">
          
          <!-- Outer Frame -->
          <rect x="20" y="20" width="960" height="660" fill="none" stroke="#334155" stroke-width="2" />
          
          <!-- Grid -->
          {#each Array(10) as _, i}
            <line x1={20 + (i * 96)} y1="15" x2={20 + (i * 96)} y2="25" stroke="#94a3b8" stroke-width="1" />
            <text x={68 + (i * 96)} y="15" font-size="10" fill="#94a3b8" text-anchor="middle">{i}</text>
          {/each}
          {#each Array(6) as _, i}
            <line x1="15" y1={20 + (i * 110)} x2="25" y2={20 + (i * 110)} stroke="#94a3b8" stroke-width="1" />
            <text x="10" y={75 + (i * 110)} font-size="10" fill="#94a3b8" text-anchor="end">{String.fromCharCode(65 + i)}</text>
          {/each}

          <!-- Title Block -->
          <g transform="translate(680, 580)">
            <rect x="0" y="0" width="300" height="100" fill="none" stroke="#334155" stroke-width="2" />
            <line x1="0" y1="20" x2="300" y2="20" stroke="#334155" stroke-width="1" />
            <line x1="0" y1="40" x2="300" y2="40" stroke="#334155" stroke-width="1" />
            <line x1="0" y1="80" x2="300" y2="80" stroke="#334155" stroke-width="1" />
            <line x1="100" y1="0" x2="100" y2="40" stroke="#334155" stroke-width="1" />
            <line x1="200" y1="80" x2="200" y2="100" stroke="#334155" stroke-width="1" />
            <line x1="250" y1="80" x2="250" y2="100" stroke="#334155" stroke-width="1" />
            
            <text x="5" y="14" font-size="9" fill="#64748b">Datum</text><text x="40" y="14" font-size="10" fill="#0f172a" font-weight="bold">2026-05-22</text>
            <text x="105" y="14" font-size="9" fill="#64748b">Bearbeiter</text><text x="155" y="14" font-size="10" fill="#0f172a" font-weight="bold">Andreas</text>
            <text x="5" y="34" font-size="9" fill="#64748b">Geprüft</text>
            <text x="105" y="34" font-size="9" fill="#64748b">Norm</text><text x="155" y="34" font-size="10" fill="#0f172a">EN 61082-1</text>
            
            <text x="5" y="55" font-size="11" fill="#64748b">Projektbezeichnung:</text>
            <text x="5" y="72" font-size="16" fill="#0f172a" font-weight="bold">KAiTix</text>
            <text x="5" y="94" font-size="11" fill="#0f172a">Anlage: UV-USV-01 (Verteilung)</text>
            <text x="205" y="94" font-size="10" fill="#64748b">Blatt:</text><text x="235" y="94" font-size="11" fill="#0f172a" font-weight="bold">2</text>
            <text x="255" y="94" font-size="10" fill="#64748b">V.Bl.:</text><text x="285" y="94" font-size="11" fill="#0f172a">1</text>
          </g>

          <g stroke-linecap="round" stroke-linejoin="round">
            <text x="30" y="65" font-size="10" font-style="italic" fill="#64748b">Von Blatt 1</text>
            
            <!-- Busbars -->
            <g stroke-width="1.5">
              <line x1="50" y1="80" x2="950" y2="80" stroke="#78350f" /> <text x="35" y="83" font-size="10" fill="#78350f" font-weight="bold">L1</text>
              <line x1="50" y1="100" x2="950" y2="100" stroke="#0f172a" /> <text x="35" y="103" font-size="10" fill="#0f172a" font-weight="bold">L2</text>
              <line x1="50" y1="120" x2="950" y2="120" stroke="#475569" /> <text x="35" y="123" font-size="10" fill="#475569" font-weight="bold">L3</text>
              <line x1="50" y1="140" x2="950" y2="140" stroke="#2563eb" /> <text x="35" y="143" font-size="10" fill="#2563eb" font-weight="bold">N</text>
              <line x1="50" y1="160" x2="950" y2="160" stroke="#16a34a" stroke-dasharray="8,4" /> <text x="35" y="163" font-size="10" fill="#16a34a" font-weight="bold">PE</text>
            </g>
            
            <!-- -Q0 Zentraler Lasttrennschalter -->
            <g stroke="#0f172a" stroke-width="1.5" fill="none">
              <!-- L1 -->
              <line x1="80" y1="77" x2="100" y2="77" stroke="#f8fafc" stroke-width="3" />
              <line x1="80" y1="80" x2="90" y2="70" stroke="#78350f" />
              <!-- L2 -->
              <line x1="80" y1="97" x2="100" y2="97" stroke="#f8fafc" stroke-width="3" />
              <line x1="80" y1="100" x2="90" y2="90" stroke="#0f172a" />
              <!-- L3 -->
              <line x1="80" y1="117" x2="100" y2="117" stroke="#f8fafc" stroke-width="3" />
              <line x1="80" y1="120" x2="90" y2="110" stroke="#475569" />
              <!-- N -->
              <line x1="80" y1="137" x2="100" y2="137" stroke="#f8fafc" stroke-width="3" />
              <line x1="80" y1="140" x2="90" y2="130" stroke="#2563eb" />
              
              <line x1="85" y1="65" x2="85" y2="140" stroke-dasharray="2,2" stroke-width="1" />
            </g>
            <text x="85" y="60" font-size="9" font-weight="bold" fill="#0f172a" text-anchor="middle">-Q0</text>
            <text x="85" y="152" font-size="7" fill="#64748b" text-anchor="middle">Lasttrennschalter</text>

            <!-- Racks & PDUs (Each Rack gets 2x 16A PDUs) -->
            {#each Array(7) as _, rackIdx}
              {@const rackNum = rackIdx + 1}
              {@const boxX = 140 + rackIdx * 120}
              
              <!-- Rack Box (Ortskasten) -->
              <rect x={boxX} y="380" width="100" height="150" fill="none" stroke="#334155" stroke-dasharray="8,4" stroke-width="1"/>
              <text x={boxX + 5} y="395" font-size="10" font-weight="bold" fill="#0f172a">+Rack {rackNum}</text>
              
              <!-- Feed A and Feed B branches -->
              {#each ['A', 'B'] as feed, feedIdx}
                {@const isA = feed === 'A'}
                {@const xPos = boxX + 28 + feedIdx * 44} <!-- Feed A at boxX+28, Feed B at boxX+72 -->
                {@const qNum = `3.${rackNum}${feed}`} <!-- e.g. -Q3.1A, -Q3.1B -->
                {@const wNum = `3.${rackNum}${isA ? 'A' : 'B'}`} <!-- e.g. -W3.1A, -W3.1B -->
                {@const pduName = `-PDU${isA ? '1' : '2'}`}
                
                <!-- Tap circles from busbars L1, L2, L3, N, PE -->
                <circle cx={xPos - 20} cy="80" r="3" fill="white" stroke="#78350f" stroke-width="1.5"/>
                <circle cx={xPos - 10} cy="100" r="3" fill="white" stroke="#0f172a" stroke-width="1.5"/>
                <circle cx={xPos} cy="120" r="3" fill="white" stroke="#475569" stroke-width="1.5"/>
                <circle cx={xPos + 10} cy="140" r="3" fill="white" stroke="#2563eb" stroke-width="1.5"/>
                <circle cx={xPos + 20} cy="160" r="3" fill="white" stroke="#16a34a" stroke-width="1.5"/>
                
                <!-- Lines from busbars to circuit breaker -->
                <line x1={xPos - 20} y1="80" x2={xPos - 20} y2="220" stroke="#78350f" stroke-width="1"/>
                <line x1={xPos - 10} y1="100" x2={xPos - 10} y2="220" stroke="#0f172a" stroke-width="1"/>
                <line x1={xPos} y1="120" x2={xPos} y2="220" stroke="#475569" stroke-width="1"/>
                <line x1={xPos + 10} y1="140" x2={xPos + 10} y2="220" stroke="#2563eb" stroke-width="1"/>
                <line x1={xPos + 20} y1="160" x2={xPos + 20} y2="405" stroke="#16a34a" stroke-width="1" stroke-dasharray="6,3"/>
                
                <!-- Circuit Breaker (LS C16A 3P+N) -->
                <g stroke="#0f172a" stroke-width="1.5" fill="none">
                  <!-- L1, L2, L3 -->
                  <line x1={xPos - 20} y1="220" x2={xPos - 25} y2="250"/>
                  <line x1={xPos - 10} y1="220" x2={xPos - 15} y2="250"/>
                  <line x1={xPos} y1="220" x2={xPos - 5} y2="250"/>
                  
                  <!-- N (voreilend: steilerer Winkel) -->
                  <line x1={xPos + 10} y1="220" x2={xPos + 8} y2="250" stroke="#2563eb"/>
                  
                  <line x1={xPos - 30} y1="235" x2={xPos + 15} y2="235" stroke-dasharray="2,2" stroke-width="1"/>
                  
                  <!-- Auslöser 'x' -->
                  <path d={`M ${xPos - 24} 233 L ${xPos - 21} 237 M ${xPos - 24} 237 L ${xPos - 21} 233`} stroke-width="1"/>
                  <path d={`M ${xPos - 14} 233 L ${xPos - 11} 237 M ${xPos - 14} 237 L ${xPos - 11} 233`} stroke-width="1"/>
                  <path d={`M ${xPos - 4} 233 L ${xPos - 1} 237 M ${xPos - 4} 237 L ${xPos - 1} 233`} stroke-width="1"/>
                </g>
                <text x={xPos - 28} y="238" font-size="8" font-weight="bold" fill="#0f172a" text-anchor="end">-{qNum}</text>
                <text x={xPos + 20} y="236" font-size="6" fill="#0f172a" text-anchor="start" font-weight="bold">RCBO 16A</text>
                <text x={xPos + 20} y="244" font-size="5" fill="#64748b" text-anchor="start">30mA Typ B (G)</text>
                
                <!-- RCBO Summenstromwandler (FI-Teil) -->
                <ellipse cx={xPos - 5} cy="275" rx="18" ry="4" fill="none" stroke="#0f172a" stroke-width="1.2"/>
                <path d={`M ${xPos - 5} 271 L ${xPos - 5} 265 L ${xPos - 30} 265 L ${xPos - 30} 235`} fill="none" stroke="#0f172a" stroke-width="0.8" stroke-dasharray="1,2"/>

                <line x1={xPos - 20} y1="250" x2={xPos - 20} y2="300" stroke="#78350f" stroke-width="1"/>
                <line x1={xPos - 10} y1="250" x2={xPos - 10} y2="300" stroke="#0f172a" stroke-width="1"/>
                <line x1={xPos} y1="250" x2={xPos} y2="300" stroke="#475569" stroke-width="1"/>
                <line x1={xPos + 10} y1="250" x2={xPos + 10} y2="300" stroke="#2563eb" stroke-width="1"/>
                
                <!-- Terminals -->
                <g fill="#ffffff" stroke="#0f172a" stroke-width="1.5">
                  <circle cx={xPos - 20} cy="300" r="4"/>
                  <circle cx={xPos - 10} cy="300" r="4"/>
                  <circle cx={xPos} cy="300" r="4"/>
                  <circle cx={xPos + 10} cy="300" r="4"/>
                  <circle cx={xPos + 20} cy="300" r="4"/>
                </g>
                <text x={xPos - 28} y="303" font-size="8" font-weight="bold" fill="#0f172a" text-anchor="end">-X{rackNum}{feed}</text>
                
                <!-- Cable to PDU -->
                <line x1={xPos - 20} y1="303" x2={xPos - 20} y2="405" stroke="#78350f" stroke-width="1"/>
                <line x1={xPos - 10} y1="303" x2={xPos - 10} y2="405" stroke="#0f172a" stroke-width="1"/>
                <line x1={xPos} y1="303" x2={xPos} y2="405" stroke="#475569" stroke-width="1"/>
                <line x1={xPos + 10} y1="303" x2={xPos + 10} y2="405" stroke="#2563eb" stroke-width="1"/>
                <line x1={xPos + 20} y1="303" x2={xPos + 20} y2="405" stroke="#16a34a" stroke-width="1" stroke-dasharray="6,3"/>
                
                <!-- Cable Sheath Label -->
                <path d="M {xPos - 22} 340 C {xPos - 22} 330, {xPos + 22} 330, {xPos + 22} 340" fill="none" stroke="#64748b" stroke-width="1" stroke-dasharray="2,2"/>
                <text x={xPos + 15} y="342" font-size="6" fill="#64748b" text-anchor="start">-W{wNum} (5x2.5)</text>
                
                <!-- PDU Box inside Rack -->
                {@const pduX = boxX + 8 + feedIdx * 44}
                <rect x={pduX} y="400" width="40" height="100" fill="#f8fafc" stroke="#0f172a" stroke-width="1.5"/>
                <text x={pduX + 20} y="435" font-size="8" font-weight="bold" text-anchor="middle" fill="#0f172a">{pduName}</text>
                <text x={pduX + 20} y="450" font-size="7" font-weight="bold" text-anchor="middle" fill="#2563eb">Pfad {feed}</text>
                <text x={pduX + 20} y="462" font-size="6" text-anchor="middle" fill="#0f172a">Kentix 16A</text>
                <text x={pduX + 20} y="474" font-size="6" text-anchor="middle" fill="#64748b">SmartPDU</text>
              {/each}
            {/each}
    
          </g>
        </svg>
      </div>
    </div>
  </div>
</div>

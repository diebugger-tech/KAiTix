<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { goto } from '$app/navigation';
  import { FileText } from '@lucide/svelte';

  type TopoData = Awaited<ReturnType<typeof api.getTopology>>;
  type Node = TopoData['nodes'][number];
  type Edge = TopoData['edges'][number];

  let data = $state<TopoData | null>(null);
  let loading = $state(true);
  let error = $state('');

  let hoveredEdge = $state<string | null>(null);
  let selectedNode = $state<Node | null>(null);
  let filterView = $state<string>('all');
  let dropdownOpen = $state(false);
  let showCrossRack = $state(true);
  let showIntraRack = $state(true);
  let showPower = $state(true);
  let showCables = $state(true);

  // Pan / zoom
  let svgEl = $state<SVGSVGElement | undefined>(undefined);
  let viewBox = $state({ x: 0, y: 0, w: 1400, h: 900 });
  let isPanning = $state(false);
  let panStart = $state({ x: 0, y: 0, vx: 0, vy: 0 });

  // Drag nodes
  let dragNodeId = $state<number | null>(null);
  let dragOffset = $state({ x: 0, y: 0 });
  let nodeOffsets = $state(new Map<number, { x: number; y: number }>());

  // PDF export
  let pdfLoading = $state(false);

  async function downloadTopologyPdf() {
    pdfLoading = true;
    try {
      const res = await fetch('http://localhost:8003/api/v1/topology/pdf');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'topologie.pdf';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      alert('PDF-Export fehlgeschlagen: ' + (e.message ?? ''));
    } finally {
      pdfLoading = false;
    }
  }

  onMount(async () => {
    try {
      data = await api.getTopology();
    } catch (e: any) {
      error = e.message ?? 'Fehler';
    } finally {
      loading = false;
    }
  });

  // ── Layout ──────────────────────────────────────────────────────────────────
  const RACK_WIDTH = 180;
  const RACK_GAP = 70;
  const RACK_TOP = 80;
  const U_HEIGHT = 12;
  const DEV_PAD = 4;
  const LABEL_H = 32;

  interface NodeBox {
    x: number; y: number; w: number; h: number;
    cx: number; cy: number;
    node: Node;
  }

  const baseLayout = $derived(() => {
    if (!data) return { rackBoxes: [], nodeBoxes: new Map<number, NodeBox>(), totalW: 0, totalH: 0 };

    const rackBoxes: Array<{ rack: TopoData['racks'][number]; x: number; y: number; w: number; h: number }> = [];
    const nodeBoxes = new Map<number, NodeBox>();
    let x = 20;

    for (const rack of data.racks) {
      const rackH = rack.hoehe_u * U_HEIGHT + LABEL_H + DEV_PAD * 2;
      rackBoxes.push({ rack, x, y: RACK_TOP, w: RACK_WIDTH, h: rackH });

      const placed = data.nodes
        .filter(n => n.rack_id === rack.id && n.u_position != null)
        .sort((a, b) => (b.u_position ?? 0) - (a.u_position ?? 0));
      const unplaced = data.nodes.filter(n => n.rack_id === rack.id && n.u_position == null);

      for (const dev of placed) {
        const uPos = dev.u_position ?? 1;
        const uH = Math.max(dev.u_hoehe ?? 1, 1);
        const dy = RACK_TOP + LABEL_H + DEV_PAD + (rack.hoehe_u - uPos - uH + 1) * U_HEIGHT;
        const dh = Math.max(uH * U_HEIGHT - 1, 10);
        const nx = x + DEV_PAD, nw = RACK_WIDTH - DEV_PAD * 2;
        nodeBoxes.set(dev.id, { x: nx, y: dy, w: nw, h: dh, cx: nx + nw / 2, cy: dy + dh / 2, node: dev });
      }

      let uy = RACK_TOP + rackH + 8;
      for (const dev of unplaced) {
        nodeBoxes.set(dev.id, { x: x + DEV_PAD, y: uy, w: RACK_WIDTH - DEV_PAD * 2, h: 18, cx: x + RACK_WIDTH / 2, cy: uy + 9, node: dev });
        uy += 22;
      }
      x += RACK_WIDTH + RACK_GAP;
    }

    const noRack = data.nodes.filter(n => !n.rack_id);
    let ny = RACK_TOP;
    for (const dev of noRack) {
      nodeBoxes.set(dev.id, { x: x + DEV_PAD, y: ny, w: RACK_WIDTH - DEV_PAD * 2, h: 18, cx: x + RACK_WIDTH / 2, cy: ny + 9, node: dev });
      ny += 22;
    }
    if (noRack.length > 0) x += RACK_WIDTH + RACK_GAP;

    const maxH = Math.max(...Array.from(nodeBoxes.values()).map(b => b.y + b.h), 500);
    return { rackBoxes, nodeBoxes, totalW: x, totalH: maxH + 40 };
  });

  // Apply drag offsets on top of base layout
  function getBox(id: number): NodeBox | undefined {
    const base = baseLayout().nodeBoxes.get(id);
    if (!base) return undefined;
    const off = nodeOffsets.get(id);
    if (!off) return base;
    return {
      ...base,
      x: base.x + off.x, y: base.y + off.y,
      cx: base.cx + off.x, cy: base.cy + off.y,
    };
  }

  // ── Edges ───────────────────────────────────────────────────────────────────
  const filteredEdges = $derived(() => {
    if (!data) return [];
    return data.edges.filter(e => {
      const isPower = (e as any).edge_type === 'power';
      if (!showPower && isPower) return false;
      if (!showCables && !isPower) return false;
      if (!showCrossRack && e.cross_rack) return false;
      if (!showIntraRack && !e.cross_rack) return false;

      if (filterView === 'netzwerk' && isPower) return false;
      if (filterView === 'strom' && !isPower) return false;
      if (filterView === 'crossrack' && !e.cross_rack) return false;
      if (filterView === 'intrarack' && e.cross_rack) return false;

      if (deviceTypes.includes(filterView)) {
        const ids = deviceFilterNodes();
        if (ids && !ids.has(e.von_device_id) && !ids.has(e.nach_device_id)) return false;
      }

      return true;
    });
  });

  function edgePath(edge: Edge): string {
    const a = getBox(edge.von_device_id);
    const b = getBox(edge.nach_device_id);
    if (!a || !b) return '';
    const cpOffset = Math.abs(b.cx - a.cx) * 0.3 + 30;
    const cpy = Math.min(a.cy, b.cy) - cpOffset;
    return `M ${a.cx} ${a.cy} Q ${(a.cx + b.cx) / 2} ${cpy} ${b.cx} ${b.cy}`;
  }

  function edgeColor(edge: Edge): string {
    if ((edge as any).edge_type === 'power') {
      const phase = (edge as any).phase;
      if (phase === 'L1') return '#f97316';
      if (phase === 'L2') return '#84cc16';
      if (phase === 'L3') return '#a855f7';
      return '#ef4444';
    }
    const t = edge.typ.toLowerCase();
    if (t.includes('lc') || t.includes('sc') || t.includes('lwl')) return '#d946ef';
    if (t.startsWith('cat')) return '#3b82f6';
    if (t === 'dac') return '#6b7280';
    if (t.includes('sfp')) return '#06b6d4';
    if (t.startsWith('strom') || t.startsWith('cee')) return '#ef4444';
    return '#94a3b8';
  }

  function nodeColor(typ: string) {
    const map: Record<string, string> = { server: '#1e40af', switch: '#065f46', pdu: '#78350f', firewall: '#7f1d1d', storage: '#4c1d95' };
    return map[typ] ?? '#1e293b';
  }
  function nodeStroke(typ: string) {
    const map: Record<string, string> = { server: '#3b82f6', switch: '#10b981', pdu: '#f59e0b', firewall: '#ef4444', storage: '#8b5cf6' };
    return map[typ] ?? '#475569';
  }

  // ── Pan ─────────────────────────────────────────────────────────────────────
  function onWheel(e: WheelEvent) {
    e.preventDefault();
    const factor = e.deltaY > 0 ? 1.1 : 0.9;
    const rect = (e.currentTarget as SVGSVGElement).getBoundingClientRect();
    const mx = (e.clientX - rect.left) / rect.width * viewBox.w + viewBox.x;
    const my = (e.clientY - rect.top) / rect.height * viewBox.h + viewBox.y;
    viewBox = { x: mx - (mx - viewBox.x) * factor, y: my - (my - viewBox.y) * factor, w: viewBox.w * factor, h: viewBox.h * factor };
  }

  function svgPoint(e: MouseEvent): { x: number; y: number } {
    if (!svgEl) return { x: 0, y: 0 };
    const rect = svgEl.getBoundingClientRect();
    return {
      x: (e.clientX - rect.left) / rect.width * viewBox.w + viewBox.x,
      y: (e.clientY - rect.top) / rect.height * viewBox.h + viewBox.y,
    };
  }

  function onSvgMouseDown(e: MouseEvent) {
    if ((e.target as Element).closest('.node-hit')) return;
    isPanning = true;
    panStart = { x: e.clientX, y: e.clientY, vx: viewBox.x, vy: viewBox.y };
  }

  function onNodeMouseDown(e: MouseEvent, id: number) {
    e.stopPropagation();
    const pt = svgPoint(e);
    const box = getBox(id);
    if (!box) return;
    dragNodeId = id;
    dragOffset = { x: pt.x - box.cx, y: pt.y - box.cy };
  }

  function onMouseMove(e: MouseEvent) {
    if (dragNodeId !== null) {
      const pt = svgPoint(e);
      const base = baseLayout().nodeBoxes.get(dragNodeId);
      if (!base) return;
      const newCx = pt.x - dragOffset.x;
      const newCy = pt.y - dragOffset.y;
      const newOffsets = new Map(nodeOffsets);
      newOffsets.set(dragNodeId, { x: newCx - base.cx, y: newCy - base.cy });
      nodeOffsets = newOffsets;
      return;
    }
    if (!isPanning || !svgEl) return;
    const rect = svgEl.getBoundingClientRect();
    const sx = viewBox.w / rect.width, sy = viewBox.h / rect.height;
    viewBox = { ...viewBox, x: panStart.vx - (e.clientX - panStart.x) * sx, y: panStart.vy - (e.clientY - panStart.y) * sy };
  }

  function onMouseUp() { isPanning = false; dragNodeId = null; }

  function resetView() {
    const l = baseLayout();
    viewBox = { x: 0, y: 0, w: Math.max(l.totalW + 40, 800), h: Math.max(l.totalH + 40, 600) };
    nodeOffsets = new Map();
  }

  function zoomIn() {
    const factor = 0.8;
    viewBox = { x: viewBox.x + viewBox.w * (1 - factor) / 2, y: viewBox.y + viewBox.h * (1 - factor) / 2, w: viewBox.w * factor, h: viewBox.h * factor };
  }

  function zoomOut() {
    const factor = 1.25;
    viewBox = { x: viewBox.x + viewBox.w * (1 - factor) / 2, y: viewBox.y + viewBox.h * (1 - factor) / 2, w: viewBox.w * factor, h: viewBox.h * factor };
  }

  const nodeEdges = $derived(() => {
    if (!data || !selectedNode) return [];
    return data.edges.filter(e => e.von_device_id === selectedNode!.id || e.nach_device_id === selectedNode!.id);
  });

  function connectedNodeId(edge: Edge): number {
    return edge.von_device_id === selectedNode?.id ? edge.nach_device_id : edge.von_device_id;
  }

  const deviceTypes = ['server', 'switch', 'pdu', 'storage', 'firewall'];

  const deviceTypeLabel: Record<string, string> = {
    server: 'Server', switch: 'Switch', pdu: 'PDU',
    storage: 'Storage', firewall: 'Firewall',
  };

  // Rack filter
  let rackFilter = $state<number | null>(null);

  const deviceFilterNodes = $derived(() => {
    if (!data || !deviceTypes.includes(filterView)) return null;
    return new Set(data.nodes.filter(n => n.typ === filterView).map(n => n.id));
  });

  const visibleNodeIds = $derived(() => {
    if (!data) return new Set();
    let ids: Set<number>;
    if (!deviceTypes.includes(filterView)) {
      ids = new Set(data.nodes.map(n => n.id));
    } else {
      ids = new Set(deviceFilterNodes()!);
      for (const edge of data.edges) {
        if (ids.has(edge.von_device_id) || ids.has(edge.nach_device_id)) {
          ids.add(edge.von_device_id);
          ids.add(edge.nach_device_id);
        }
      }
    }
    if (rackFilter !== null) {
      const rackIds = new Set(data.nodes.filter(n => n.rack_id === rackFilter).map(n => n.id));
      ids = new Set([...ids].filter(id => rackIds.has(id)));
    }
    return ids;
  });
</script>

<svelte:head><title>KAiTix – Topologie</title></svelte:head>

<div class="flex flex-col h-[calc(100vh-8rem)] gap-3">
  <!-- Toolbar -->
  <div class="flex items-center gap-4 flex-wrap shrink-0 bg-[#101622] border border-slate-800 rounded-xl px-4 py-2.5">
    <div class="relative" onmouseleave={() => dropdownOpen = false}>
      <span class="text-[10px] uppercase font-bold tracking-wider text-slate-500 mr-2">Ansicht</span>
      <button
        onclick={() => dropdownOpen = !dropdownOpen}
        class="bg-[#182030] border border-slate-700 hover:border-slate-600 rounded-lg px-3 py-1 text-xs text-white focus:outline-none min-w-[130px] text-left"
      >
        {filterView === 'all' ? 'Alle' : filterView.charAt(0).toUpperCase() + filterView.slice(1)}
        <span class="float-right text-slate-500">▾</span>
      </button>
      {#if dropdownOpen}
        <div class="absolute top-full left-0 mt-1 bg-[#182030] border border-slate-700 rounded-lg py-1 min-w-[160px] z-50 shadow-xl">
          <button onclick={() => { filterView = 'all'; dropdownOpen = false; }} class="w-full text-left px-3 py-1.5 text-xs text-white hover:bg-slate-700/50 {filterView === 'all' ? 'bg-slate-700/30' : ''}">Alle</button>
          <div class="text-[9px] text-slate-600 px-3 py-1 font-bold uppercase tracking-wider mt-1 border-t border-slate-800 pt-1">── Geräte ──</div>
          {#each deviceTypes as dt}
            <button
              onclick={() => { filterView = dt; dropdownOpen = false; }}
              class="w-full text-left px-3 py-1.5 text-xs text-white hover:bg-slate-700/50 {filterView === dt ? 'bg-slate-700/30' : ''}"
            >{deviceTypeLabel[dt]}</button>
          {/each}
          <div class="text-[9px] text-slate-600 px-3 py-1 font-bold uppercase tracking-wider mt-1 border-t border-slate-800 pt-1">── Kabel ──</div>
          {#each [['netzwerk', 'Netzwerk'], ['strom', 'Strom']] as [val, label]}
            <button
              onclick={() => { filterView = val; dropdownOpen = false; }}
              class="w-full text-left px-3 py-1.5 text-xs text-white hover:bg-slate-700/50 {filterView === val ? 'bg-slate-700/30' : ''}"
            >{label}</button>
          {/each}
          <div class="text-[9px] text-slate-600 px-3 py-1 font-bold uppercase tracking-wider mt-1 border-t border-slate-800 pt-1">── Ansicht ──</div>
          {#each [['crossrack', 'Rack-übergreifend'], ['intrarack', 'Intra-Rack']] as [val, label]}
            <button
              onclick={() => { filterView = val; dropdownOpen = false; }}
              class="w-full text-left px-3 py-1.5 text-xs text-white hover:bg-slate-700/50 {filterView === val ? 'bg-slate-700/30' : ''}"
            >{label}</button>
          {/each}
        </div>
      {/if}
    </div>
    {#if data}
      <div class="border-l border-slate-800 pl-4 flex items-center gap-2">
        <span class="text-[10px] uppercase font-bold tracking-wider text-slate-500">Rack</span>
        <select
          bind:value={rackFilter}
          class="bg-[#182030] border border-slate-700 hover:border-slate-600 rounded-lg px-2 py-1 text-xs text-white focus:outline-none"
        >
          <option value={null}>Alle Racks</option>
          {#each data.racks as rack}
            <option value={rack.id}>{rack.name}</option>
          {/each}
        </select>
      </div>
    {/if}
    <div class="flex items-center gap-3 border-l border-slate-800 pl-4">
      <label class="flex items-center gap-1.5 cursor-pointer text-xs text-slate-300">
        <input type="checkbox" bind:checked={showCables} class="accent-blue-500" /> Kabel
      </label>
      <label class="flex items-center gap-1.5 cursor-pointer text-xs text-slate-300">
        <input type="checkbox" bind:checked={showPower} class="accent-orange-500" /> Strom (PDU)
      </label>
      <label class="flex items-center gap-1.5 cursor-pointer text-xs text-slate-300">
        <input type="checkbox" bind:checked={showCrossRack} class="accent-violet-500" /> Rack-übergreifend
      </label>
      <label class="flex items-center gap-1.5 cursor-pointer text-xs text-slate-300">
        <input type="checkbox" bind:checked={showIntraRack} class="accent-slate-400" /> Intra-Rack
      </label>
    </div>
    <div class="flex items-center gap-2 ml-auto">
      <button
        onclick={downloadTopologyPdf}
        disabled={pdfLoading}
        class="px-3 py-1 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs text-slate-300 transition disabled:opacity-40 flex items-center gap-1.5"
      >
        <FileText size={13} />
        {pdfLoading ? '…' : 'PDF'}
      </button>
      <button onclick={resetView} class="px-3 py-1 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs text-slate-300 transition">
        Reset
      </button>
    </div>
    {#if data}
      <span class="text-xs text-slate-600">{data.nodes.length} Geräte · {data.edges.length} Verbindungen</span>
    {/if}
  </div>

  <div class="flex gap-4 flex-1 min-h-0">
    <!-- Canvas -->
    <div class="flex-1 bg-[#080c14] border border-slate-800 rounded-xl overflow-hidden relative">
      {#if loading}
        <div class="absolute inset-0 flex items-center justify-center">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-violet-500"></div>
        </div>
      {:else if error}
        <div class="absolute inset-0 flex items-center justify-center text-red-400 text-sm">{error}</div>
      {:else if data && data.nodes.length === 0}
        <div class="absolute inset-0 flex items-center justify-center">
          <div class="text-center">
            <div class="mb-3 text-slate-600">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-16 h-16 mx-auto opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z"/></svg>
            </div>
            <p class="text-slate-400 text-sm font-medium mb-1">Keine Geräte oder Verbindungen gefunden</p>
            <p class="text-slate-600 text-xs">Geräte unter <span class="text-blue-400">Racks → Hardware einbauen</span> anlegen,<br>Kabel unter <span class="text-emerald-400">Kabelliste</span> verbinden.</p>
          </div>
        </div>
      {:else if data}
        {@const l = baseLayout()}
        <svg
          bind:this={svgEl}
          class="w-full h-full {dragNodeId !== null ? 'cursor-grabbing' : isPanning ? 'cursor-grabbing' : 'cursor-grab'}"
          viewBox="{viewBox.x} {viewBox.y} {viewBox.w} {viewBox.h}"
          onwheel={onWheel}
          onmousedown={onSvgMouseDown}
          onmousemove={onMouseMove}
          onmouseup={onMouseUp}
          onmouseleave={onMouseUp}
        >
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <circle cx="0" cy="0" r="0.7" fill="#1e293b" />
            </pattern>
          </defs>
          <rect x={viewBox.x} y={viewBox.y} width={viewBox.w} height={viewBox.h} fill="url(#grid)" />

          <!-- Edges -->
          <g>
            {#each filteredEdges() as edge}
              {@const path = edgePath(edge)}
              {@const isHovered = hoveredEdge === edge.id}
              {@const isPower = (edge as any).edge_type === 'power'}
              {@const isSelected = selectedNode && (edge.von_device_id === selectedNode.id || edge.nach_device_id === selectedNode.id)}
              {@const dimmed = selectedNode && !isSelected}
              {#if path}
                <path
                  d={path}
                  fill="none"
                  stroke={edgeColor(edge)}
                  stroke-width={isHovered || isSelected ? 2.5 : 1.2}
                  stroke-dasharray={isPower ? '3 4' : edge.cross_rack ? '7 3' : 'none'}
                  opacity={dimmed ? 0.06 : isHovered || isSelected ? 1 : 0.4}
                  onmouseenter={() => hoveredEdge = edge.id}
                  onmouseleave={() => hoveredEdge = null}
                />
                {#if isHovered}
                  {@const a = getBox(edge.von_device_id)}
                  {@const b = getBox(edge.nach_device_id)}
                  {#if a && b}
                    <text
                      x={(a.cx + b.cx) / 2}
                      y={Math.min(a.cy, b.cy) - Math.abs(b.cx - a.cx) * 0.3 - 36}
                      text-anchor="middle" font-size="9" fill="#e2e8f0"
                      class="pointer-events-none select-none"
                    >{edge.kabel_nr ?? '—'} · {edge.typ}{(edge as any).phase ? ' · ' + (edge as any).phase : ''}</text>
                  {/if}
                {/if}
              {/if}
            {/each}
          </g>

          <!-- Rack boxes -->
          {#each l.rackBoxes as rb}
            <rect x={rb.x} y={rb.y} width={rb.w} height={rb.h} rx="5" fill="#0f172a" stroke="#1e293b" stroke-width="1" />
            <text x={rb.x + rb.w / 2} y={rb.y + 17} text-anchor="middle" font-size="10" font-weight="bold" fill="#64748b" class="select-none">{rb.rack.name}</text>
            <text x={rb.x + rb.w / 2} y={rb.y + 27} text-anchor="middle" font-size="8" fill="#334155" class="select-none">{rb.rack.standort}</text>
            {#each Array.from({ length: rb.rack.hoehe_u }, (_, i) => i) as u}
              <line x1={rb.x + 2} y1={rb.y + LABEL_H + u * U_HEIGHT} x2={rb.x + 7} y2={rb.y + LABEL_H + u * U_HEIGHT} stroke="#1e293b" stroke-width="0.5" />
            {/each}
          {/each}

          <!-- Nodes -->
          {#each Array.from(l.nodeBoxes.keys()) as id}
            {@const box = getBox(id)}
            {@const hidden = !visibleNodeIds().has(id)}
            {#if box && !hidden}
              {@const isSelected = selectedNode?.id === id}
              {@const isConnected = selectedNode && nodeEdges().some(e => e.von_device_id === id || e.nach_device_id === id) && id !== selectedNode.id}
              {@const dimmed = selectedNode && !isSelected && !isConnected}
              <g
                class="node-hit"
                style="cursor: {dragNodeId === id ? 'grabbing' : 'pointer'}"
                opacity={dimmed ? 0.15 : 1}
                onmousedown={(e) => onNodeMouseDown(e, id)}
                onclick={(e) => {
                  if (dragNodeId !== null) return;
                  selectedNode = isSelected ? null : box.node;
                }}
              >
                <rect
                  x={box.x} y={box.y} width={box.w} height={box.h} rx="3"
                  fill={nodeColor(box.node.typ)}
                  stroke={isSelected ? '#a78bfa' : nodeStroke(box.node.typ)}
                  stroke-width={isSelected ? 2 : 0.8}
                />
                <text
                  x={box.cx} y={box.cy + 3.5}
                  text-anchor="middle" font-size="8" font-weight="600"
                  fill={isSelected ? '#e2e8f0' : '#94a3b8'}
                  class="pointer-events-none select-none"
                >{box.node.hostname}</text>
              </g>
            {/if}
          {/each}
        </svg>
        <!-- Zoom Controls -->
        <div class="absolute top-3 right-3 flex flex-col gap-0.5 z-10">
          <button onclick={zoomIn} class="w-7 h-7 bg-[#182030] hover:bg-slate-700 border border-slate-700 rounded-t-lg text-xs text-white flex items-center justify-center transition">+</button>
          <button onclick={zoomOut} class="w-7 h-7 bg-[#182030] hover:bg-slate-700 border-x border-slate-700 text-xs text-white flex items-center justify-center transition">−</button>
          <button onclick={resetView} class="w-7 h-7 bg-[#182030] hover:bg-slate-700 border border-slate-700 rounded-b-lg text-xs text-white flex items-center justify-center transition">⊙</button>
        </div>
      {/if}
    </div>

    <!-- Detail Panel -->
    <div class="w-72 shrink-0 flex flex-col gap-3">
      <!-- Legend -->
      <div class="bg-[#101622] border border-slate-800 rounded-xl p-4">
        <p class="text-[10px] uppercase font-bold tracking-wider text-slate-500 mb-3">Legende</p>
        <div class="grid grid-cols-2 gap-1.5 text-[10px]">
          {#each deviceTypes as dt}
            {@const col = nodeStroke(dt)}
            {@const label = deviceTypeLabel[dt]}
            <div class="flex items-center gap-1.5">
              <div class="w-2.5 h-2.5 rounded-sm shrink-0" style="background:{col}; opacity:.7"></div>
              <span class="text-slate-400">{label}</span>
            </div>
          {/each}
        </div>
        <div class="border-t border-slate-800 mt-2.5 pt-2.5 space-y-1.5">
          {#each [['#3b82f6','Kupfer (Cat)'],['#d946ef','LWL'],['#06b6d4','SFP+'],['#ef4444','Strom'],['#f97316','Strom L1'],['#84cc16','Strom L2'],['#a855f7','Strom L3']] as [col, label]}
            <div class="flex items-center gap-2">
              <svg width="20" height="8"><line x1="0" y1="4" x2="20" y2="4" stroke={col} stroke-width="1.5"/></svg>
              <span class="text-[10px] text-slate-500">{label}</span>
            </div>
          {/each}
          <div class="flex items-center gap-2">
            <svg width="20" height="8"><line x1="0" y1="4" x2="20" y2="4" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="5 2"/></svg>
            <span class="text-[10px] text-slate-500">Rack-übergreifend</span>
          </div>
          <div class="flex items-center gap-2">
            <svg width="20" height="8"><line x1="0" y1="4" x2="20" y2="4" stroke="#ef4444" stroke-width="1.5" stroke-dasharray="3 3"/></svg>
            <span class="text-[10px] text-slate-500">PDU-Strom</span>
          </div>
        </div>
        <p class="text-[9px] text-slate-600 mt-2">Nodes: Drag zum Verschieben · Scroll: Zoom · Buttons: +/−/⊙</p>
      </div>

      <!-- Node detail -->
      {#if selectedNode}
        <div class="bg-[#101622] border border-violet-800/40 rounded-xl p-4 flex-1 overflow-y-auto">
          <div class="flex items-start justify-between mb-3">
            <div>
              <p class="text-xs font-bold text-white font-mono">{selectedNode.hostname}</p>
              <p class="text-[10px] text-slate-500 mt-0.5">{selectedNode.typ} · {selectedNode.rack_name ?? 'kein Rack'}</p>
            </div>
            <button onclick={() => selectedNode = null} class="text-slate-600 hover:text-slate-400 text-xs">✕</button>
          </div>
          {#if selectedNode.hersteller || selectedNode.modell}
            <p class="text-xs text-slate-400 mb-1">{[selectedNode.hersteller, selectedNode.modell].filter(Boolean).join(' / ')}</p>
          {/if}
          {#if selectedNode.ip_adresse}
            <p class="text-xs font-mono text-blue-400 mb-2">{selectedNode.ip_adresse}</p>
          {/if}
          {#if selectedNode.u_position}
            <p class="text-[10px] text-slate-500 mb-3">HE {selectedNode.u_position} · {selectedNode.u_hoehe}U</p>
          {/if}

          {#if nodeEdges().length > 0}
            <p class="text-[10px] uppercase font-bold tracking-wider text-slate-500 mb-2">Verbindungen ({nodeEdges().length})</p>
            <div class="space-y-1.5">
              {#each nodeEdges() as edge}
                {@const otherId = connectedNodeId(edge)}
                {@const otherNode = data?.nodes.find(n => n.id === otherId)}
                {@const isPower = (edge as any).edge_type === 'power'}
                <div class="bg-slate-900/60 rounded-lg p-2 text-xs border-l-2 {isPower ? 'border-orange-500/50' : 'border-blue-500/30'}">
                  <div class="flex items-center justify-between">
                    <span class="font-mono text-slate-300 truncate">{otherNode?.hostname ?? `#${otherId}`}</span>
                    <div class="flex items-center gap-1 shrink-0 ml-1">
                      {#if isPower}<span class="text-[8px] text-orange-400 font-bold">⚡</span>{/if}
                      {#if edge.cross_rack}<span class="text-[8px] text-violet-400 font-bold">XR</span>{/if}
                    </div>
                  </div>
                  <div class="text-[10px] text-slate-500 mt-0.5">
                    {edge.typ}{(edge as any).phase ? ' · ' + (edge as any).phase : ''}
                    {edge.laenge_m != null ? ' · ' + edge.laenge_m + 'm' : ''}
                  </div>
                </div>
              {/each}
            </div>
          {:else}
            <p class="text-xs text-slate-600 italic">Keine Verbindungen</p>
          {/if}

          {#if selectedNode.rack_id}
            <button
              onclick={() => goto(`/racks?rack=${selectedNode!.rack_id}`)}
              class="mt-3 w-full px-3 py-2 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border border-blue-600/30 rounded-lg text-xs font-medium transition"
            >Im Rack ansehen ↗</button>
          {/if}
        </div>
      {:else}
        <div class="bg-[#101622] border border-slate-800 rounded-xl p-4 text-center flex-1 flex items-center justify-center">
          <p class="text-xs text-slate-600">Gerät anklicken für Details</p>
        </div>
      {/if}
    </div>
  </div>
</div>

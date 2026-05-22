<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { goto } from '$app/navigation';
  import { FileText, Network, List, Search, X, Zap, Building, Wifi } from '@lucide/svelte';
  import { locationStore } from '$lib/locations.svelte';

  type TopoData = Awaited<ReturnType<typeof api.getTopology>>;
  type Node = TopoData['nodes'][number];
  type Edge = TopoData['edges'][number];

  let data = $state<TopoData | null>(null);
  let loading = $state(true);
  let error = $state('');

  let hoveredEdge = $state<string | null>(null);
  let selectedNode = $state<Node | null>(null);
  let showCrossRack = $state(true);
  let showIntraRack = $state(true);
  let showPower = $state(true);
  let showCables = $state(true);
  let viewMode = $state<'rack' | 'netzplan' | 'stromlauf'>('rack');
  let showDeviceTypes = $state(new Set<string>(['server', 'switch', 'pdu', 'storage', 'firewall', 'kvm']));
  let searchQuery = $state('');

  // Pan / zoom
  let svgEl = $state<SVGSVGElement | undefined>(undefined);
  let viewBox = $state({ x: 0, y: 0, w: 1400, h: 900 });
  let isPanning = $state(false);
  let panStart = $state({ x: 0, y: 0, vx: 0, vy: 0 });

  // Drag nodes
  let dragNodeId = $state<number | null>(null);
  let dragOffset = $state({ x: 0, y: 0 });
  let nodeOffsets = $state(new Map<number, { x: number; y: number }>());

  let pdfLoading = $state(false);

  async function downloadTopologyPdf() {
    pdfLoading = true;
    try {
      const res = await fetch('/api/v1/topology/pdf');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'topologie.pdf'; a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      alert('PDF-Export fehlgeschlagen: ' + (e.message ?? ''));
    } finally {
      pdfLoading = false;
    }
  }

  function printNetzplan() {
    const items = netzplanData();
    const racks = data?.racks ?? [];
    const rows = items.flatMap(item => {
      const rack = racks.find(r => r.id === item.node.rack_id);
      return item.connections.map(conn => ({
        device: item.node.hostname, typ: item.node.typ,
        rack: rack?.name ?? '—', he: item.node.u_position ? `HE ${item.node.u_position}` : '—',
        localPort: conn.localPort,
        cable: `${conn.edge.kabel_nr ?? ''} · ${conn.edge.typ}${(conn.edge as any).phase ? ' ' + (conn.edge as any).phase : ''}${conn.edge.laenge_m ? ' · ' + conn.edge.laenge_m + 'm' : ''}`.trim(),
        remoteDevice: conn.remoteNode?.hostname ?? '—', remotePort: conn.remotePort,
        remoteRack: racks.find(r => r.id === conn.remoteNode?.rack_id)?.name ?? '—',
        isPower: conn.isPower,
      }));
    });
    const html = `<!DOCTYPE html><html lang="de"><head><meta charset="UTF-8">
<title>KAiTix – Netzplan</title>
<style>
  body{font-family:monospace;font-size:10px;color:#000;margin:12px}
  h1{font-size:14px;margin-bottom:4px}p.sub{font-size:10px;color:#555;margin-bottom:12px}
  table{width:100%;border-collapse:collapse}
  th{background:#e2e8f0;text-align:left;padding:3px 6px;font-size:9px;text-transform:uppercase}
  td{padding:2px 6px;border-bottom:1px solid #e2e8f0;vertical-align:top}
  tr.power td{background:#fff8f0}
  @media print{body{margin:0}}
</style></head><body>
<h1>KAiTix – Netzplan Port-Routing</h1>
<p class="sub">Export: ${new Date().toLocaleString('de-DE')} · ${rows.length} Verbindungen</p>
<table><thead><tr>
  <th>Gerät</th><th>Typ</th><th>Rack / HE</th>
  <th>Port (lokal)</th><th>Kabel</th>
  <th>Port (remote)</th><th>Gerät (remote)</th><th>Rack (remote)</th>
</tr></thead><tbody>
${rows.map(r => `<tr class="${r.isPower ? 'power' : ''}"><td>${r.device}</td><td>${r.typ}</td><td>${r.rack} ${r.he}</td><td>${r.localPort}</td><td>${r.cable}</td><td>${r.remotePort}</td><td>${r.remoteDevice}</td><td>${r.remoteRack}</td></tr>`).join('\n')}
</tbody></table></body></html>`;
    const win = window.open('', '_blank');
    if (!win) return;
    win.document.write(html);
    win.document.close();
    win.focus();
    win.print();
  }

  onMount(async () => {
    try { data = await api.getTopology(); }
    catch (e: any) { error = e.message ?? 'Fehler'; }
    finally { loading = false; }
  });

  // ── Layout ───────────────────────────────────────────────────────────────────
  const RACK_WIDTH  = 180;
  const RACK_GAP    = 50;
  const RACK_TOP    = 80;
  const U_HEIGHT    = 12;
  const DEV_PAD     = 4;
  const LABEL_H     = 32;
  const PDU_SIDE_W  = 20;
  const PDU_SIDE_GAP = 5;
  const FULL_RACK_W = PDU_SIDE_W + PDU_SIDE_GAP + RACK_WIDTH + PDU_SIDE_GAP + PDU_SIDE_W;

  interface NodeBox {
    x: number; y: number; w: number; h: number;
    cx: number; cy: number;
    node: Node;
    isSide?: boolean;
  }

  const GROUP_GAP = 60;

  const baseLayout = $derived(() => {
    if (!data) return { rackBoxes: [], nodeBoxes: new Map<number, NodeBox>(), totalW: 0, totalH: 0, groupLabels: [] as Array<{ name: string; x: number; w: number }> };
    const rackBoxes: Array<{ rack: TopoData['racks'][number]; x: number; y: number; w: number; h: number }> = [];
    const nodeBoxes = new Map<number, NodeBox>();
    const groupLabels: Array<{ name: string; x: number; w: number }> = [];

    // Sort by standort for geographic grouping
    const sortedRacks = [...data.racks].sort((a, b) => (a.standort ?? '').localeCompare(b.standort ?? ''));

    let x = 20;
    let prevStandort: string | null = null;
    let groupStartX = 20;

    for (const rack of sortedRacks) {
      const standort = rack.standort ?? '';
      if (prevStandort !== null && standort !== prevStandort) {
        groupLabels.push({ name: prevStandort || '—', x: groupStartX, w: x - RACK_GAP - groupStartX });
        x += GROUP_GAP;
        groupStartX = x;
      }
      prevStandort = standort;

      const rackH = rack.hoehe_u * U_HEIGHT + LABEL_H + DEV_PAD * 2;
      const rackX = x + PDU_SIDE_W + PDU_SIDE_GAP;
      rackBoxes.push({ rack, x: rackX, y: RACK_TOP, w: RACK_WIDTH, h: rackH });

      const rackDevices = data.nodes.filter(n => n.rack_id === rack.id);
      const sidePdus = rackDevices.filter(n => n.u_hoehe === 0);
      const slotted = rackDevices
        .filter(n => (n.u_hoehe ?? 1) > 0 && n.u_position != null)
        .sort((a, b) => (b.u_position ?? 0) - (a.u_position ?? 0));
      const floating = rackDevices.filter(n => (n.u_hoehe ?? 1) > 0 && n.u_position == null);

      for (const dev of slotted) {
        const uPos = dev.u_position ?? 1;
        const uH = Math.max(dev.u_hoehe ?? 1, 1);
        const dy = RACK_TOP + LABEL_H + DEV_PAD + (rack.hoehe_u - uPos - uH + 1) * U_HEIGHT;
        const dh = Math.max(uH * U_HEIGHT - 1, 10);
        const nx = rackX + DEV_PAD, nw = RACK_WIDTH - DEV_PAD * 2;
        nodeBoxes.set(dev.id, { x: nx, y: dy, w: nw, h: dh, cx: nx + nw / 2, cy: dy + dh / 2, node: dev });
      }

      const leftPdus  = sidePdus.slice(0, Math.ceil(sidePdus.length / 2));
      const rightPdus = sidePdus.slice(Math.ceil(sidePdus.length / 2));
      const pduSlots  = Math.max(leftPdus.length, rightPdus.length, 1);
      const pduSlotH  = Math.max(rackH / pduSlots, 20);

      leftPdus.forEach((dev, i) => {
        const py = RACK_TOP + i * pduSlotH, ph = Math.max(pduSlotH - 3, 16);
        nodeBoxes.set(dev.id, { x, y: py, w: PDU_SIDE_W, h: ph, cx: x + PDU_SIDE_W / 2, cy: py + ph / 2, node: dev, isSide: true });
      });
      const rightX = rackX + RACK_WIDTH + PDU_SIDE_GAP;
      rightPdus.forEach((dev, i) => {
        const py = RACK_TOP + i * pduSlotH, ph = Math.max(pduSlotH - 3, 16);
        nodeBoxes.set(dev.id, { x: rightX, y: py, w: PDU_SIDE_W, h: ph, cx: rightX + PDU_SIDE_W / 2, cy: py + ph / 2, node: dev, isSide: true });
      });

      let uy = RACK_TOP + rackH + 8;
      for (const dev of floating) {
        nodeBoxes.set(dev.id, { x: rackX + DEV_PAD, y: uy, w: RACK_WIDTH - DEV_PAD * 2, h: 18, cx: rackX + RACK_WIDTH / 2, cy: uy + 9, node: dev });
        uy += 22;
      }
      x += FULL_RACK_W + RACK_GAP;
    }

    // Close last group
    if (prevStandort !== null) {
      groupLabels.push({ name: prevStandort || '—', x: groupStartX, w: x - RACK_GAP - groupStartX });
    }

    const noRack = data.nodes.filter(n => !n.rack_id);
    let ny = RACK_TOP;
    for (const dev of noRack) {
      nodeBoxes.set(dev.id, { x: x + DEV_PAD, y: ny, w: RACK_WIDTH - DEV_PAD * 2, h: 18, cx: x + RACK_WIDTH / 2, cy: ny + 9, node: dev });
      ny += 22;
    }
    if (noRack.length > 0) x += FULL_RACK_W + RACK_GAP;

    const maxH = Math.max(...Array.from(nodeBoxes.values()).map(b => b.y + b.h), 500);
    return { rackBoxes, nodeBoxes, totalW: x, totalH: maxH + 40, groupLabels };
  });

  function getBox(id: number): NodeBox | undefined {
    const base = baseLayout().nodeBoxes.get(id);
    if (!base) return undefined;
    const off = nodeOffsets.get(id);
    if (!off) return base;
    return { ...base, x: base.x + off.x, y: base.y + off.y, cx: base.cx + off.x, cy: base.cy + off.y };
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
      const vn = data!.nodes.find(n => n.id === e.von_device_id);
      const nn = data!.nodes.find(n => n.id === e.nach_device_id);
      if (vn && !showDeviceTypes.has(vn.typ)) return false;
      if (nn && !showDeviceTypes.has(nn.typ)) return false;
      return true;
    });
  });

  function edgePath(edge: Edge): string {
    const a = getBox(edge.von_device_id), b = getBox(edge.nach_device_id);
    if (!a || !b) return '';
    const ax = (a as any).isSide ? (a.cx < b.cx ? a.x + a.w : a.x) : a.cx;
    const bx = (b as any).isSide ? (b.cx < a.cx ? b.x + b.w : b.x) : b.cx;
    const midX = (ax + bx) / 2;
    const cpy = Math.min(a.cy, b.cy) - Math.min(Math.abs(bx - ax) * 0.25 + 20, 60);
    return `M ${ax} ${a.cy} Q ${midX} ${cpy} ${bx} ${b.cy}`;
  }

  function edgeColor(edge: Edge): string {
    // Cross-location validation overrides normal color
    const clStatus = crossLocationStatus(edge);
    if (clStatus === 'invalid') return '#ef4444'; // red — physically impossible
    if (clStatus === 'warning') return '#f59e0b'; // amber — check optics

    if ((edge as any).edge_type === 'power') {
      const p = (edge as any).phase;
      if (p === 'L1') return '#f97316';
      if (p === 'L2') return '#84cc16';
      if (p === 'L3') return '#a855f7';
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
    const m: Record<string, string> = { server: '#1e40af', switch: '#065f46', pdu: '#78350f', firewall: '#7f1d1d', storage: '#4c1d95', kvm: '#1e3a5f' };
    return m[typ] ?? '#1e293b';
  }
  function nodeStroke(typ: string) {
    const m: Record<string, string> = { server: '#3b82f6', switch: '#10b981', pdu: '#f59e0b', firewall: '#ef4444', storage: '#8b5cf6', kvm: '#38bdf8' };
    return m[typ] ?? '#475569';
  }

  // ── Pan / zoom / drag ────────────────────────────────────────────────────────
  function onWheel(e: WheelEvent) {
    e.preventDefault();
    const f = e.deltaY > 0 ? 1.1 : 0.9;
    const rect = (e.currentTarget as SVGSVGElement).getBoundingClientRect();
    const mx = (e.clientX - rect.left) / rect.width * viewBox.w + viewBox.x;
    const my = (e.clientY - rect.top) / rect.height * viewBox.h + viewBox.y;
    viewBox = { x: mx - (mx - viewBox.x) * f, y: my - (my - viewBox.y) * f, w: viewBox.w * f, h: viewBox.h * f };
  }
  function svgPoint(e: MouseEvent) {
    if (!svgEl) return { x: 0, y: 0 };
    const r = svgEl.getBoundingClientRect();
    return { x: (e.clientX - r.left) / r.width * viewBox.w + viewBox.x, y: (e.clientY - r.top) / r.height * viewBox.h + viewBox.y };
  }
  function onSvgMouseDown(e: MouseEvent) {
    if ((e.target as Element).closest('.node-hit')) return;
    isPanning = true;
    panStart = { x: e.clientX, y: e.clientY, vx: viewBox.x, vy: viewBox.y };
  }
  function onNodeMouseDown(e: MouseEvent, id: number) {
    e.stopPropagation();
    const pt = svgPoint(e), box = getBox(id);
    if (!box) return;
    dragNodeId = id;
    dragOffset = { x: pt.x - box.cx, y: pt.y - box.cy };
  }
  function onMouseMove(e: MouseEvent) {
    if (dragNodeId !== null) {
      const pt = svgPoint(e), base = baseLayout().nodeBoxes.get(dragNodeId);
      if (!base) return;
      const next = new Map(nodeOffsets);
      next.set(dragNodeId, { x: pt.x - dragOffset.x - base.cx, y: pt.y - dragOffset.y - base.cy });
      nodeOffsets = next;
      return;
    }
    if (!isPanning || !svgEl) return;
    const r = svgEl.getBoundingClientRect();
    viewBox = { ...viewBox, x: panStart.vx - (e.clientX - panStart.x) * viewBox.w / r.width, y: panStart.vy - (e.clientY - panStart.y) * viewBox.h / r.height };
  }
  function onMouseUp() { isPanning = false; dragNodeId = null; }
  function resetView() {
    const l = baseLayout();
    viewBox = { x: 0, y: 0, w: Math.max(l.totalW + 40, 800), h: Math.max(l.totalH + 40, 600) };
    nodeOffsets = new Map();
  }
  function zoomIn()  { const f = 0.8;  viewBox = { x: viewBox.x + viewBox.w*(1-f)/2, y: viewBox.y + viewBox.h*(1-f)/2, w: viewBox.w*f, h: viewBox.h*f }; }
  function zoomOut() { const f = 1.25; viewBox = { x: viewBox.x + viewBox.w*(1-f)/2, y: viewBox.y + viewBox.h*(1-f)/2, w: viewBox.w*f, h: viewBox.h*f }; }

  const nodeEdges = $derived(() => {
    if (!data || !selectedNode) return [];
    return data.edges.filter(e => e.von_device_id === selectedNode!.id || e.nach_device_id === selectedNode!.id);
  });
  function connectedNodeId(edge: Edge) {
    return edge.von_device_id === selectedNode?.id ? edge.nach_device_id : edge.von_device_id;
  }

  // ── Filter helpers ───────────────────────────────────────────────────────────
  const deviceTypes = ['server', 'switch', 'pdu', 'storage', 'firewall', 'kvm'];
  const deviceTypeLabel: Record<string, string> = { server: 'Server', switch: 'Switch', pdu: 'PDU', storage: 'Storage', firewall: 'Firewall', kvm: 'KVM' };

  function toggleDeviceType(typ: string) {
    const next = new Set(showDeviceTypes);
    if (next.has(typ)) next.delete(typ); else next.add(typ);
    showDeviceTypes = next;
  }
  function applyPreset(preset: 'all' | 'netzwerk' | 'strom') {
    if (preset === 'all') {
      showDeviceTypes = new Set(deviceTypes);
      showCables = true; showPower = true; showCrossRack = true; showIntraRack = true;
    } else if (preset === 'netzwerk') {
      showDeviceTypes = new Set(['server', 'switch', 'storage', 'firewall', 'kvm']);
      showCables = true; showPower = false; showCrossRack = true; showIntraRack = true;
    } else if (preset === 'strom') {
      showDeviceTypes = new Set(['server', 'pdu']);
      showCables = false; showPower = true; showCrossRack = true; showIntraRack = true;
    }
  }

  let rackFilter = $state<number | null>(null);

  // ── Netzplan filters ─────────────────────────────────────────────────────────
  let netzplanStandort = $state('');
  let netzplanCableFilter = $state(new Set([
    'cat', 'lwl', 'sfp', 'dac', 'breakout', 'sonstige-netz',
    'strom-l1', 'strom-l2', 'strom-l3', 'strom-other'
  ]));

  function cableCategory(edge: Edge): string {
    if ((edge as any).edge_type === 'power') {
      const p = (edge as any).phase;
      if (p === 'L1') return 'strom-l1';
      if (p === 'L2') return 'strom-l2';
      if (p === 'L3') return 'strom-l3';
      return 'strom-other';
    }
    const t = (edge.typ ?? '').toLowerCase();
    if (t.startsWith('cat') || t.includes('rj45') || t.includes('kupfer')) return 'cat';
    if (t.includes('lc') || t.includes('sc') || t.includes('lwl') || t.includes('glasfaser') || t.includes(' om') || t.includes(' os') || t === 'lwl') return 'lwl';
    if (t.includes('sfp') || t.includes('qsfp')) return 'sfp';
    if (t === 'dac' || t.includes('direktkabel')) return 'dac';
    if (t.includes('breakout') || t.includes('mpo') || t.includes('mtp')) return 'breakout';
    return 'sonstige-netz';
  }

  // ── Cross-location validation ────────────────────────────────────────────────
  function edgeStandorts(edge: Edge): [string | null, string | null] {
    if (!data) return [null, null];
    const vNode = data.nodes.find(n => n.id === edge.von_device_id);
    const nNode = data.nodes.find(n => n.id === edge.nach_device_id);
    const vRack = vNode?.rack_id ? data.racks.find(r => r.id === vNode.rack_id) : null;
    const nRack = nNode?.rack_id ? data.racks.find(r => r.id === nNode.rack_id) : null;
    return [vRack?.standort ?? null, nRack?.standort ?? null];
  }

  function isCrossLocation(edge: Edge): boolean {
    const [a, b] = edgeStandorts(edge);
    return !!(a && b && a !== b);
  }

  // 'invalid' = Cat/DAC (physisch unmöglich zwischen Standorten)
  // 'warning' = SFP+/Breakout (unklar, abhängig von Optik)
  // 'ok'      = LWL/Glasfaser
  // null      = gleicher Standort, keine Prüfung
  function crossLocationStatus(edge: Edge): 'invalid' | 'warning' | 'ok' | null {
    if (!isCrossLocation(edge)) return null;
    if ((edge as any).edge_type === 'power') return null;
    const cat = cableCategory(edge);
    if (cat === 'cat' || cat === 'dac') return 'invalid';
    if (cat === 'sfp' || cat === 'breakout') return 'warning';
    if (cat === 'lwl') return 'ok';
    return 'warning';
  }

  function toggleCableFilter(key: string) {
    const next = new Set(netzplanCableFilter);
    if (next.has(key)) next.delete(key); else next.add(key);
    netzplanCableFilter = next;
  }

  function setCableGroup(group: 'netz' | 'strom', on: boolean) {
    const netzKeys = ['cat', 'lwl', 'sfp', 'dac', 'breakout', 'sonstige-netz'];
    const stromKeys = ['strom-l1', 'strom-l2', 'strom-l3', 'strom-other'];
    const next = new Set(netzplanCableFilter);
    (group === 'netz' ? netzKeys : stromKeys).forEach(k => on ? next.add(k) : next.delete(k));
    netzplanCableFilter = next;
  }

  // Search: returns null when inactive, Set<id> when active
  const searchMatchIds = $derived(() => {
    if (!data || !searchQuery.trim()) return null;
    const q = searchQuery.toLowerCase();
    return new Set(data.nodes
      .filter(n => n.hostname.toLowerCase().includes(q) ||
                   (n.ip_adresse ?? '').includes(q) ||
                   (n.modell ?? '').toLowerCase().includes(q) ||
                   (n.hersteller ?? '').toLowerCase().includes(q))
      .map(n => n.id));
  });

  const visibleNodeIds = $derived(() => {
    if (!data) return new Set<number>();
    let ids = new Set(data.nodes.filter(n => showDeviceTypes.has(n.typ)).map(n => n.id));
    if (rackFilter !== null) {
      const rIds = new Set(data.nodes.filter(n => n.rack_id === rackFilter).map(n => n.id));
      ids = new Set([...ids].filter(id => rIds.has(id)));
    }
    return ids;
  });

  // ── Netzplan ─────────────────────────────────────────────────────────────────
  interface NetzplanDevice {
    node: Node;
    connections: Array<{ edge: Edge; localPort: string; remoteNode: Node | undefined; remotePort: string; isPower: boolean }>;
  }
  const netzplanData = $derived(() => {
    if (!data) return [];
    const result: NetzplanDevice[] = [];
    const sorted = [...data.nodes].sort((a, b) => {
      if (a.rack_id !== b.rack_id) return (a.rack_id ?? 9999) - (b.rack_id ?? 9999);
      if (a.typ === 'pdu' && b.typ !== 'pdu') return 1;
      if (a.typ !== 'pdu' && b.typ === 'pdu') return -1;
      return (a.u_position ?? 0) - (b.u_position ?? 0);
    });
    for (const node of sorted) {
      const edges = data.edges.filter(e => e.von_device_id === node.id || e.nach_device_id === node.id);
      if (edges.length === 0) continue;
      const connections = edges.map(e => {
        const isPower = (e as any).edge_type === 'power';
        const isSrc = e.von_device_id === node.id;
        return { edge: e, isPower,
          localPort: isSrc ? (e.von_port ?? '–') : (e.nach_port ?? '–'),
          remoteNode: data!.nodes.find(n => n.id === (isSrc ? e.nach_device_id : e.von_device_id)),
          remotePort: isSrc ? (e.nach_port ?? '–') : (e.von_port ?? '–'),
        };
      }).sort((a, b) => a.isPower !== b.isPower ? (a.isPower ? 1 : -1) : (a.localPort).localeCompare(b.localPort));
      result.push({ node, connections });
    }
    return result;
  });

  const filteredNetzplanData = $derived(() => {
    let items = netzplanData();
    if (netzplanStandort) {
      items = items.filter(item => {
        const rack = data?.racks.find(r => r.id === item.node.rack_id);
        return rack?.standort === netzplanStandort;
      });
    }
    return items
      .map(item => ({ ...item, connections: item.connections.filter(c => netzplanCableFilter.has(cableCategory(c.edge))) }))
      .filter(item => item.connections.length > 0);
  });
</script>

<svelte:head><title>KAiTix – Topologie</title></svelte:head>

<div class="flex flex-col h-[calc(100vh-8rem)] gap-3">
  <!-- ── Toolbar ──────────────────────────────────────────────────────────────── -->
  <div class="flex flex-col gap-2 shrink-0">
    <div class="flex items-center gap-3 flex-wrap bg-[#101622] border border-slate-800 rounded-xl px-4 py-2.5">

      <!-- View mode toggle -->
      <div class="flex items-center rounded-lg border border-slate-700 overflow-hidden shrink-0">
        <button onclick={() => viewMode = 'rack'}
          class="flex items-center gap-1.5 px-3 py-1.5 text-xs transition {viewMode === 'rack' ? 'bg-blue-600 text-white' : 'bg-[#182030] text-slate-400 hover:text-white'}">
          <Network size={12} /> Topologie
        </button>
        <button onclick={() => viewMode = 'netzplan'}
          class="flex items-center gap-1.5 px-3 py-1.5 text-xs transition {viewMode === 'netzplan' ? 'bg-blue-600 text-white' : 'bg-[#182030] text-slate-400 hover:text-white'}">
          <List size={12} /> Netzplan
        </button>
      </div>

      {#if viewMode === 'rack'}
        <!-- Search -->
        <div class="flex items-center gap-1.5 bg-[#182030] border border-slate-700 rounded-lg px-2 py-1 shrink-0">
          <Search size={11} class="text-slate-500 shrink-0" />
          <input bind:value={searchQuery} placeholder="Suche…"
            class="bg-transparent text-xs text-white placeholder-slate-600 outline-none w-28" />
          {#if searchQuery}
            <button onclick={() => searchQuery = ''} class="text-slate-600 hover:text-slate-400"><X size={11} /></button>
          {/if}
        </div>

        <!-- Device type checkboxes -->
        <div class="flex items-center gap-2 border-l border-slate-800 pl-3 flex-wrap">
          <span class="text-[10px] uppercase font-bold tracking-wider text-slate-500 shrink-0">Geräte</span>
          {#each deviceTypes as dt}
            <label class="flex items-center gap-1 cursor-pointer text-[11px] text-slate-300 whitespace-nowrap select-none">
              <input type="checkbox" checked={showDeviceTypes.has(dt)} oninput={() => toggleDeviceType(dt)} class="w-3 h-3" />
              <span class="w-2 h-2 rounded-sm shrink-0" style="background:{nodeStroke(dt)};opacity:.8"></span>
              {deviceTypeLabel[dt]}
            </label>
          {/each}
        </div>

        <!-- Cable checkboxes (SVG-Topologie) -->
        <div class="flex items-center gap-2 border-l border-slate-800 pl-3">
          <span class="text-[10px] uppercase font-bold tracking-wider text-slate-500 shrink-0">Kabel</span>
          <label class="flex items-center gap-1 cursor-pointer text-[11px] text-slate-300 select-none">
            <input type="checkbox" bind:checked={showCables} class="accent-blue-500 w-3 h-3" /> Netz
          </label>
          <label class="flex items-center gap-1 cursor-pointer text-[11px] text-slate-300 select-none">
            <input type="checkbox" bind:checked={showPower} class="accent-orange-500 w-3 h-3" /> Strom
          </label>
          <label class="flex items-center gap-1 cursor-pointer text-[11px] text-slate-300 select-none">
            <input type="checkbox" bind:checked={showCrossRack} class="accent-violet-500 w-3 h-3" /> XRack
          </label>
          <label class="flex items-center gap-1 cursor-pointer text-[11px] text-slate-300 select-none">
            <input type="checkbox" bind:checked={showIntraRack} class="accent-slate-400 w-3 h-3" /> Intra
          </label>
        </div>

        <!-- Quick presets (Strom-only, Alle) -->
        <div class="flex items-center gap-1.5 border-l border-slate-800 pl-3">
          <span class="text-[10px] uppercase font-bold tracking-wider text-slate-500 shrink-0">Schnell</span>
          <button onclick={() => applyPreset('all')} class="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded text-[10px] text-slate-300 transition">Alle</button>
          <button onclick={() => applyPreset('strom')} class="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 border border-orange-900/60 rounded text-[10px] text-orange-400 transition">Stromplan</button>
        </div>

        <!-- Rack filter -->
        {#if data}
          <div class="flex items-center gap-2 border-l border-slate-800 pl-3">
            <span class="text-[10px] uppercase font-bold tracking-wider text-slate-500">Rack</span>
            <select bind:value={rackFilter} class="bg-[#182030] border border-slate-700 hover:border-slate-600 rounded-lg px-2 py-1 text-xs text-white focus:outline-none">
              <option value={null}>Alle</option>
              {#each data.racks as rack}<option value={rack.id}>{rack.name}</option>{/each}
            </select>
          </div>
        {/if}
      {/if}

      <div class="flex items-center gap-2 ml-auto">
        {#if viewMode === 'netzplan'}
          <button onclick={printNetzplan}
            class="px-3 py-1 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs text-slate-300 transition flex items-center gap-1.5">
            <FileText size={13} /> Drucken / PDF
          </button>
        {:else}
          <button onclick={downloadTopologyPdf} disabled={pdfLoading}
            class="px-3 py-1 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs text-slate-300 transition disabled:opacity-40 flex items-center gap-1.5">
            <FileText size={13} />{pdfLoading ? '…' : 'PDF'}
          </button>
          <button onclick={resetView} class="px-3 py-1 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs text-slate-300 transition">Reset</button>
        {/if}
      </div>
      {#if data}
        <span class="text-xs text-slate-600 shrink-0">
          {#if viewMode === 'rack' && searchMatchIds()}{searchMatchIds()!.size} Treffer ·{/if}
          {#if viewMode === 'netzplan'}{filteredNetzplanData().length} / {netzplanData().length} Geräte{:else}{data.nodes.length} Geräte · {data.edges.length} Verb.{/if}
        </span>
      {/if}
    </div>

    <!-- Netzplan Filterleiste -->
    {#if viewMode === 'netzplan' && data}
      <div class="flex items-center gap-3 flex-wrap bg-[#101622] border border-slate-800 rounded-xl px-4 py-2">
        <!-- Standort-Filter -->
        <div class="flex items-center gap-2">
          <span class="text-[10px] uppercase font-bold tracking-wider text-slate-500 shrink-0">Standort</span>
          <select bind:value={netzplanStandort}
            class="bg-[#182030] border border-slate-700 rounded-lg px-2 py-1 text-xs text-white focus:outline-none">
            <option value="">Alle</option>
            {#each [...new Set(data.racks.map(r => r.standort).filter(Boolean))] as s}
              <option value={s}>{s}</option>
            {/each}
          </select>
        </div>

        <!-- Netzwerkkabel-Filter -->
        <div class="flex items-center gap-2 border-l border-slate-800 pl-3">
          <button onclick={() => setCableGroup('netz', true)}
            class="text-[9px] text-blue-400 hover:text-blue-300 font-semibold">Netz</button>
          <button onclick={() => setCableGroup('netz', false)}
            class="text-[9px] text-slate-600 hover:text-slate-400">✕</button>
          {#each [['cat','Cat/RJ45','#3b82f6'],['lwl','LWL/Glasfaser','#d946ef'],['sfp','SFP+','#06b6d4'],['dac','DAC','#6b7280'],['breakout','Breakout','#8b5cf6'],['sonstige-netz','Sonstige','#475569']] as [key,label,col]}
            <label class="flex items-center gap-1 cursor-pointer text-[11px] text-slate-300 whitespace-nowrap select-none">
              <input type="checkbox" checked={netzplanCableFilter.has(key)} oninput={() => toggleCableFilter(key)} class="w-3 h-3" />
              <span class="w-2 h-2 rounded-full shrink-0" style="background:{col}"></span>
              {label}
            </label>
          {/each}
        </div>

        <!-- Strom-Filter -->
        <div class="flex items-center gap-2 border-l border-slate-800 pl-3">
          <button onclick={() => setCableGroup('strom', true)}
            class="text-[9px] text-orange-400 hover:text-orange-300 font-semibold">Strom</button>
          <button onclick={() => setCableGroup('strom', false)}
            class="text-[9px] text-slate-600 hover:text-slate-400">✕</button>
          {#each [['strom-l1','L1','#f97316'],['strom-l2','L2','#84cc16'],['strom-l3','L3','#a855f7'],['strom-other','allg.','#ef4444']] as [key,label,col]}
            <label class="flex items-center gap-1 cursor-pointer text-[11px] text-slate-300 whitespace-nowrap select-none">
              <input type="checkbox" checked={netzplanCableFilter.has(key)} oninput={() => toggleCableFilter(key)} class="w-3 h-3" />
              <span class="w-2 h-2 rounded-full shrink-0" style="background:{col}"></span>
              {label}
            </label>
          {/each}
        </div>
      </div>
    {/if}
  </div>

  <!-- ═══ TOPOLOGIE SVG ═══════════════════════════════════════════════════════ -->
  {#if viewMode === 'rack'}
    <div class="flex gap-4 flex-1 min-h-0">
      <div class="flex-1 bg-[#080c14] border border-slate-800 rounded-xl overflow-hidden relative">
        {#if loading}
          <div class="absolute inset-0 flex items-center justify-center">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-violet-500"></div>
          </div>
        {:else if error}
          <div class="absolute inset-0 flex items-center justify-center text-red-400 text-sm">{error}</div>
        {:else if data && data.nodes.length === 0}
          <div class="absolute inset-0 flex items-center justify-center text-center">
            <p class="text-slate-400 text-sm">Keine Geräte gefunden</p>
          </div>
        {:else if data}
          {@const l = baseLayout()}
          <svg bind:this={svgEl}
            class="w-full h-full {dragNodeId !== null || isPanning ? 'cursor-grabbing' : 'cursor-grab'}"
            viewBox="{viewBox.x} {viewBox.y} {viewBox.w} {viewBox.h}"
            onwheel={onWheel} onmousedown={onSvgMouseDown}
            onmousemove={onMouseMove} onmouseup={onMouseUp} onmouseleave={onMouseUp}>
            <defs>
              <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <circle cx="0" cy="0" r="0.7" fill="#1e293b" />
              </pattern>
            </defs>
            <rect x={viewBox.x} y={viewBox.y} width={viewBox.w} height={viewBox.h} fill="url(#grid)" />

            <!-- Geographic group labels -->
            {#each l.groupLabels as gl}
              {#if gl.name && gl.name !== '—'}
                {@const locTyp = locationStore.getTyp(gl.name)}
                <rect x={gl.x - 6} y={RACK_TOP - 28} width={gl.w + 12} height={24} rx="4"
                  fill={locTyp === 'dienstaußenstelle' ? '#1a1030' : '#0a1828'}
                  stroke={locTyp === 'dienstaußenstelle' ? '#3b1f6a' : '#1e3a5a'} stroke-width="0.8" />
                <text x={gl.x} y={RACK_TOP - 12} font-size="10" font-weight="700"
                  fill={locTyp === 'dienstaußenstelle' ? '#a78bfa' : '#60a5fa'}
                  class="select-none">{gl.name}</text>
              {/if}
            {/each}

            <!-- Edges -->
            <g>
              {#each filteredEdges() as edge}
                {@const path = edgePath(edge)}
                {@const isHov = hoveredEdge === edge.id}
                {@const isPow = (edge as any).edge_type === 'power'}
                {@const isSel = selectedNode && (edge.von_device_id === selectedNode.id || edge.nach_device_id === selectedNode.id)}
                {@const dim  = selectedNode && !isSel}
                {@const clStatus = crossLocationStatus(edge)}
                {#if path}
                  <path d={path} fill="none" stroke={edgeColor(edge)}
                    stroke-width={clStatus === 'invalid' ? (isHov || isSel ? 3.5 : 2) : (isHov || isSel ? 2.5 : 1.2)}
                    stroke-dasharray={clStatus ? '6 3 2 3' : isPow ? '3 4' : edge.cross_rack ? '7 3' : 'none'}
                    opacity={dim ? 0.06 : clStatus === 'invalid' ? (isHov || isSel ? 1 : 0.75) : (isHov || isSel ? 1 : 0.4)}
                    onmouseenter={() => hoveredEdge = edge.id}
                    onmouseleave={() => hoveredEdge = null} />
                  {#if isHov}
                    {@const a = getBox(edge.von_device_id)}
                    {@const b = getBox(edge.nach_device_id)}
                    {#if a && b}
                      {@const [sA, sB] = edgeStandorts(edge)}
                      <text x={(a.cx+b.cx)/2} y={Math.min(a.cy,b.cy)-Math.abs(b.cx-a.cx)*0.25-30}
                        text-anchor="middle" font-size="9" fill="#e2e8f0" class="pointer-events-none select-none"
                      >{edge.kabel_nr ?? '—'} · {edge.typ}{(edge as any).phase ? ' · '+(edge as any).phase : ''}{edge.von_port ? ' · '+edge.von_port : ''}{edge.nach_port ? ' → '+edge.nach_port : ''}{clStatus === 'invalid' ? ' ⚠ Standortgrenze!' : clStatus === 'warning' ? ' ⚠ Optik prüfen' : sA && sB && sA !== sB ? ' · '+sA+'→'+sB : ''}</text>
                    {/if}
                  {/if}
                {/if}
              {/each}
            </g>

            <!-- Rack boxes + utilization bar + side PDU brackets -->
            {#each l.rackBoxes as rb}
              {@const usedU = data.nodes.filter(n => n.rack_id === rb.rack.id && (n.u_hoehe ?? 0) > 0).reduce((s, n) => s + (n.u_hoehe ?? 0), 0)}
              {@const utilPct = rb.rack.hoehe_u > 0 ? usedU / rb.rack.hoehe_u : 0}
              {@const utilCol = utilPct > 0.9 ? '#ef4444' : utilPct > 0.7 ? '#f59e0b' : '#10b981'}
              <rect x={rb.x} y={rb.y} width={rb.w} height={rb.h} rx="5" fill="#0f172a" stroke="#1e293b" stroke-width="1" />
              <text x={rb.x+rb.w/2} y={rb.y+17} text-anchor="middle" font-size="10" font-weight="bold" fill="#64748b" class="select-none">{rb.rack.name}</text>
              <text x={rb.x+rb.w/2} y={rb.y+27} text-anchor="middle" font-size="8" fill="#334155" class="select-none">{rb.rack.standort}</text>
              {#each Array.from({ length: rb.rack.hoehe_u }, (_, i) => i) as u}
                <line x1={rb.x+2} y1={rb.y+LABEL_H+u*U_HEIGHT} x2={rb.x+7} y2={rb.y+LABEL_H+u*U_HEIGHT} stroke="#1e293b" stroke-width="0.5" />
              {/each}
              <!-- Utilization bar (right edge) -->
              {@const barY = rb.y + LABEL_H}
              {@const barH = rb.h - LABEL_H - DEV_PAD}
              <rect x={rb.x+rb.w-4} y={barY} width={3} height={barH} rx="1" fill="#1e293b" />
              <rect x={rb.x+rb.w-4} y={barY + barH*(1-utilPct)} width={3} height={barH*utilPct} rx="1" fill={utilCol} opacity="0.85" />
              <text x={rb.x+rb.w-7} y={rb.y+rb.h-3} text-anchor="end" font-size="7" fill={utilCol} class="select-none" opacity="0.7">{usedU}/{rb.rack.hoehe_u}U</text>
              <!-- Side PDU brackets -->
              <rect x={rb.x-PDU_SIDE_GAP-PDU_SIDE_W} y={rb.y} width={PDU_SIDE_W} height={rb.h} rx="3" fill="#0a1020" stroke="#1c2030" stroke-width="0.8" stroke-dasharray="2 2" />
              <rect x={rb.x+rb.w+PDU_SIDE_GAP} y={rb.y} width={PDU_SIDE_W} height={rb.h} rx="3" fill="#0a1020" stroke="#1c2030" stroke-width="0.8" stroke-dasharray="2 2" />
            {/each}

            <!-- Nodes -->
            {#each Array.from(l.nodeBoxes.keys()) as id}
              {@const box = getBox(id)}
              {@const hidden = !visibleNodeIds().has(id)}
              {#if box && !hidden}
                {@const isSel = selectedNode?.id === id}
                {@const isConn = selectedNode && nodeEdges().some(e => e.von_device_id === id || e.nach_device_id === id) && id !== selectedNode.id}
                {@const dimSel = selectedNode && !isSel && !isConn}
                {@const sMatch = searchMatchIds()}
                {@const isMatch = sMatch !== null && sMatch.has(id)}
                {@const dimSearch = sMatch !== null && !isMatch}
                {@const isSide = (box as any).isSide}
                <g class="node-hit" opacity={dimSel || dimSearch ? 0.12 : 1}
                  style="cursor: {dragNodeId === id ? 'grabbing' : 'pointer'}"
                  onmousedown={(e) => onNodeMouseDown(e, id)}
                  onclick={() => { if (dragNodeId !== null) return; selectedNode = isSel ? null : box.node; }}>
                  <rect x={box.x} y={box.y} width={box.w} height={box.h} rx={isSide ? 2 : 3}
                    fill={nodeColor(box.node.typ)}
                    stroke={isSel ? '#a78bfa' : isMatch ? '#fbbf24' : nodeStroke(box.node.typ)}
                    stroke-width={isSel || isMatch ? 2 : 0.8} />
                  {#if isSide}
                    <text x={box.cx} y={box.cy} text-anchor="middle" dominant-baseline="middle"
                      font-size="6" font-weight="600" fill={isSel ? '#e2e8f0' : '#94a3b8'}
                      transform="rotate(-90, {box.cx}, {box.cy})"
                      class="pointer-events-none select-none">{box.node.hostname.slice(0, 10)}</text>
                  {:else}
                    <text x={box.cx} y={box.cy+3.5} text-anchor="middle" font-size="8" font-weight="600"
                      fill={isSel || isMatch ? '#e2e8f0' : '#94a3b8'}
                      class="pointer-events-none select-none">{box.node.hostname}</text>
                  {/if}
                </g>
              {/if}
            {/each}
          </svg>

          <!-- Zoom buttons -->
          <div class="absolute top-3 right-3 flex flex-col gap-0.5 z-10">
            <button onclick={zoomIn}  class="w-7 h-7 bg-[#182030] hover:bg-slate-700 border border-slate-700 rounded-t-lg text-xs text-white flex items-center justify-center transition">+</button>
            <button onclick={zoomOut} class="w-7 h-7 bg-[#182030] hover:bg-slate-700 border-x border-slate-700 text-xs text-white flex items-center justify-center transition">−</button>
            <button onclick={resetView} class="w-7 h-7 bg-[#182030] hover:bg-slate-700 border border-slate-700 rounded-b-lg text-xs text-white flex items-center justify-center transition">⊙</button>
          </div>
        {/if}
      </div>

      <!-- Detail Panel -->
      <div class="w-72 shrink-0 flex flex-col gap-3">
        <div class="bg-[#101622] border border-slate-800 rounded-xl p-4">
          <p class="text-[10px] uppercase font-bold tracking-wider text-slate-500 mb-3">Legende</p>
          <div class="grid grid-cols-2 gap-1.5 text-[10px]">
            {#each deviceTypes as dt}
              <div class="flex items-center gap-1.5">
                <div class="w-2.5 h-2.5 rounded-sm shrink-0" style="background:{nodeStroke(dt)};opacity:.7"></div>
                <span class="text-slate-400">{deviceTypeLabel[dt]}</span>
              </div>
            {/each}
          </div>
          <div class="border-t border-slate-800 mt-2.5 pt-2.5 space-y-1.5">
            {#each [['#3b82f6','Kupfer (Cat)'],['#d946ef','LWL / Glasfaser'],['#06b6d4','SFP+'],['#6b7280','DAC'],['#ef4444','Strom'],['#f97316','Strom L1'],['#84cc16','Strom L2'],['#a855f7','Strom L3']] as [col, label]}
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
          <div class="border-t border-slate-800 mt-2.5 pt-2 flex items-center gap-2">
            <div class="flex gap-0.5">
              <div class="w-2 h-3 rounded-sm bg-emerald-500 opacity-70"></div>
              <div class="w-2 h-3 rounded-sm bg-amber-500 opacity-70"></div>
              <div class="w-2 h-3 rounded-sm bg-red-500 opacity-70"></div>
            </div>
            <span class="text-[10px] text-slate-500">Rack-Auslastung (HE)</span>
          </div>
          <p class="text-[9px] text-slate-600 mt-2">PDUs seitlich · Drag: verschieben · Scroll: Zoom</p>
        </div>

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
                  {@const other = data?.nodes.find(n => n.id === otherId)}
                  {@const isPow = (edge as any).edge_type === 'power'}
                  <div class="bg-slate-900/60 rounded-lg p-2 text-xs border-l-2 {isPow ? 'border-orange-500/50' : 'border-blue-500/30'}">
                    <div class="flex items-center justify-between">
                      <span class="font-mono text-slate-300 truncate">{other?.hostname ?? `#${otherId}`}</span>
                      <div class="flex items-center gap-1 shrink-0 ml-1">
                        {#if isPow}<span class="text-[8px] text-orange-400 font-bold">⚡</span>{/if}
                        {#if edge.cross_rack}<span class="text-[8px] text-violet-400 font-bold">XR</span>{/if}
                      </div>
                    </div>
                    <div class="text-[10px] text-slate-500 mt-0.5">
                      {edge.typ}{(edge as any).phase ? ' · '+(edge as any).phase : ''}
                      {edge.laenge_m != null ? ' · '+edge.laenge_m+'m' : ''}
                    </div>
                    {#if edge.von_port || edge.nach_port}
                      <div class="text-[9px] text-slate-600 mt-0.5 font-mono">
                        {edge.von_device_id === selectedNode.id ? (edge.von_port ?? '–') : (edge.nach_port ?? '–')}
                        → {edge.von_device_id === selectedNode.id ? (edge.nach_port ?? '–') : (edge.von_port ?? '–')}
                      </div>
                    {/if}
                  </div>
                {/each}
              </div>
            {:else}
              <p class="text-xs text-slate-600 italic">Keine Verbindungen</p>
            {/if}
            {#if selectedNode.rack_id}
              <button onclick={() => goto(`/racks?rack=${selectedNode!.rack_id}`)}
                class="mt-3 w-full px-3 py-2 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border border-blue-600/30 rounded-lg text-xs font-medium transition">
                Im Rack ansehen ↗
              </button>
            {/if}
          </div>
        {:else}
          <div class="bg-[#101622] border border-slate-800 rounded-xl p-4 text-center flex-1 flex items-center justify-center">
            <p class="text-xs text-slate-600">Gerät anklicken für Details</p>
          </div>
        {/if}
      </div>
    </div>

  <!-- ═══ NETZPLAN VIEW ═══════════════════════════════════════════════════════ -->
  {:else}
    <div class="flex-1 overflow-y-auto">
      {#if loading}
        <div class="flex items-center justify-center p-12">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        </div>
      {:else if data}
        <div class="space-y-3 pb-6">
          <div class="bg-[#101622] border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-slate-500 flex items-center justify-between">
            <span>Port-Routing · Verbindungen nach Kabeltyp und Standort filterbar.</span>
            <span class="text-slate-600">{filteredNetzplanData().length} / {netzplanData().length} Geräte</span>
          </div>
          {#each filteredNetzplanData() as item, idx}
            {@const rack = data.racks.find(r => r.id === item.node.rack_id)}
            {@const prevItem = filteredNetzplanData()[idx - 1]}
            {@const prevRack = prevItem ? data.racks.find(r => r.id === prevItem.node.rack_id) : null}
            {@const standortChanged = netzplanStandort === null && rack?.standort !== prevRack?.standort}

            {#if standortChanged && rack?.standort}
              {@const locTyp = locationStore.getTyp(rack.standort)}
              <div class="flex items-center gap-2 pt-2">
                {#if locTyp === 'dienstaußenstelle'}
                  <Wifi class="w-3.5 h-3.5 text-violet-400 shrink-0" />
                {:else}
                  <Building class="w-3.5 h-3.5 text-blue-400 shrink-0" />
                {/if}
                <span class="text-xs font-bold {locTyp === 'dienstaußenstelle' ? 'text-violet-400' : 'text-blue-400'}">{rack.standort}</span>
                <span class="text-[9px] px-1.5 py-0.5 rounded-full border {locTyp === 'dienstaußenstelle' ? 'bg-violet-900/30 text-violet-500 border-violet-700/40' : 'bg-blue-900/30 text-blue-500 border-blue-700/40'}">{locTyp === 'dienstaußenstelle' ? 'Außenstelle' : 'RZ'}</span>
                <div class="flex-1 h-px bg-slate-800"></div>
              </div>
            {/if}

            <div class="bg-[#101622] border border-slate-800 rounded-xl overflow-hidden">
              <div class="flex items-center gap-3 px-4 py-2.5 border-b border-slate-800/60" style="border-left: 3px solid {nodeStroke(item.node.typ)}">
                <div>
                  <span class="text-sm font-bold text-white font-mono">{item.node.hostname}</span>
                  <span class="ml-2 text-[10px] text-slate-500">{item.node.typ.toUpperCase()}</span>
                  {#if item.node.hersteller || item.node.modell}
                    <span class="ml-1 text-[10px] text-slate-600">{[item.node.hersteller, item.node.modell].filter(Boolean).join(' ')}</span>
                  {/if}
                </div>
                <div class="ml-auto flex items-center gap-2">
                  {#if rack}<span class="text-[10px] text-slate-600 bg-slate-800/60 px-1.5 py-0.5 rounded">{rack.name}{rack.standort ? ' · '+rack.standort : ''}</span>{/if}
                  {#if item.node.u_position}<span class="text-[10px] text-slate-600 bg-slate-800/60 px-1.5 py-0.5 rounded">HE {item.node.u_position}</span>{/if}
                  {#if item.node.ip_adresse}<span class="text-[10px] font-mono text-blue-400">{item.node.ip_adresse}</span>{/if}
                </div>
              </div>
              <div class="divide-y divide-slate-800/40">
                {#each item.connections as conn}
                  {@const clStatus = crossLocationStatus(conn.edge)}
                  {@const [clA, clB] = edgeStandorts(conn.edge)}
                  <div class="flex items-center gap-3 px-4 py-2 text-xs hover:bg-slate-800/20 transition
                    {clStatus === 'invalid' ? 'bg-red-950/20' : clStatus === 'warning' ? 'bg-amber-950/10' : ''}">
                    <div class="w-28 shrink-0">
                      {#if conn.localPort && conn.localPort !== '–'}
                        <span class="font-mono text-[10px] bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded">{conn.localPort}</span>
                      {:else}
                        <span class="text-slate-700 text-[10px]">—</span>
                      {/if}
                    </div>
                    <div class="flex items-center gap-1.5 flex-1 min-w-0">
                      <div class="w-4 h-px shrink-0" style="background:{edgeColor(conn.edge)}"></div>
                      <span class="text-[10px] font-mono text-slate-500 truncate">
                        {conn.edge.kabel_nr ?? ''}
                        {#if conn.edge.typ}<span class="text-slate-600"> · {conn.edge.typ}</span>{/if}
                        {#if (conn.edge as any).phase}<span class="text-[10px] font-bold" style="color:{edgeColor(conn.edge)}"> {(conn.edge as any).phase}</span>{/if}
                        {#if conn.edge.laenge_m}<span class="text-slate-700"> · {conn.edge.laenge_m}m</span>{/if}
                      </span>
                      <div class="w-4 h-px shrink-0" style="background:{edgeColor(conn.edge)}"></div>
                      {#if clStatus === 'invalid'}
                        <span title="Cat/DAC kann keine Standortgrenzen überqueren — öffentliche Glasfaser erforderlich"
                          class="shrink-0 text-[9px] font-bold px-1.5 py-0.5 rounded bg-red-900/60 text-red-300 border border-red-700/50">
                          ⚠ {clA}→{clB}
                        </span>
                      {:else if clStatus === 'warning'}
                        <span title="Standortgrenze — Optik/Medium prüfen"
                          class="shrink-0 text-[9px] font-bold px-1.5 py-0.5 rounded bg-amber-900/40 text-amber-300 border border-amber-700/40">
                          ⚠ Optik?
                        </span>
                      {:else if clStatus === 'ok'}
                        <span title="Glasfaser — Standortgrenze OK"
                          class="shrink-0 text-[9px] px-1.5 py-0.5 rounded bg-violet-900/30 text-violet-400 border border-violet-700/30">
                          ↔ WAN
                        </span>
                      {/if}
                    </div>
                    <div class="flex items-center gap-2 shrink-0 text-right">
                      <div>
                        <button onclick={() => goto(`/racks?rack=${conn.remoteNode?.rack_id}`)}
                          class="font-mono text-[11px] text-slate-300 hover:text-blue-400 transition"
                        >{conn.remoteNode?.hostname ?? `#${conn.edge.von_device_id === item.node.id ? conn.edge.nach_device_id : conn.edge.von_device_id}`}</button>
                        {#if conn.remotePort && conn.remotePort !== '–'}
                          <div><span class="font-mono text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded">{conn.remotePort}</span></div>
                        {/if}
                      </div>
                      {#if conn.remoteNode?.rack_id}
                        <span class="text-[9px] text-slate-600 bg-slate-800/40 px-1 py-0.5 rounded shrink-0">
                          {data.racks.find(r => r.id === conn.remoteNode?.rack_id)?.name ?? ''}
                        </span>
                      {/if}
                    </div>
                  </div>
                {/each}
              </div>
            </div>
          {/each}
          {#if filteredNetzplanData().length === 0}
            <div class="text-center py-12 text-slate-500 text-sm">Keine Verbindungen für aktive Filter.</div>
          {/if}
        </div>
      {/if}
    </div>
  {/if}
</div>

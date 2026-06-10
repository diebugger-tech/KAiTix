export interface RackMetrics {
  occupiedU: number;
  percent: number;
  totalKw: number;
  L1kw: number;
  L2kw: number;
  L3kw: number;
  imbalancePct: number;
  hasPhasedDevices: boolean;
  pdus: any[];
}

export function calculateRackMetrics(rack: any, allDevices: any[]): RackMetrics {
  const rackDevices = allDevices.filter(d => d.rack_id === rack.id);
  const occupiedU = rackDevices.filter(d => (d.u_hoehe ?? 0) > 0).reduce((sum, d) => sum + (d.u_hoehe || 0), 0);
  const percent = rack.hoehe_u > 0 ? Math.round((occupiedU / rack.hoehe_u) * 100) : 0;
  
  const totalKw = rackDevices.reduce((s, d) => s + (Number(d.anschlussleistung_watt ?? d.tdp_watt) || 0), 0) / 1000;
  
  let L1w = 0;
  let L2w = 0;
  let L3w = 0;

  for (const d of rackDevices) {
    const effectivePhases: Array<'L1' | 'L2' | 'L3'> = [];
    if (d.connected_pdu_outlets && d.connected_pdu_outlets.length > 0) {
      for (const o of d.connected_pdu_outlets) {
        if (o.phase === 'L1' || o.phase === 'L2' || o.phase === 'L3') effectivePhases.push(o.phase);
      }
    } else if (d.phase === 'L1' || d.phase === 'L2' || d.phase === 'L3') {
      effectivePhases.push(d.phase);
    }
    
    const power = Number(d.anschlussleistung_watt ?? d.tdp_watt ?? 0);
    if (effectivePhases.length > 0) {
      const primaryPhase = effectivePhases[0];
      if (primaryPhase === 'L1') L1w += power;
      else if (primaryPhase === 'L2') L2w += power;
      else if (primaryPhase === 'L3') L3w += power;
    }
  }

  const L1kw = L1w / 1000;
  const L2kw = L2w / 1000;
  const L3kw = L3w / 1000;
  
  const rPhTotal = L1kw + L2kw + L3kw;
  const rPhIdeal = rPhTotal / 3;
  const imbalancePct = rPhTotal > 0 ? (Math.max(Math.abs(L1kw - rPhIdeal), Math.abs(L2kw - rPhIdeal), Math.abs(L3kw - rPhIdeal)) / rPhIdeal) * 100 : 0;
  
  const hasPhasedDevices = rackDevices.some(d => d.phase);
  const pdus = rackDevices.filter(d => d.typ === 'pdu');
  
  return {
    occupiedU,
    percent,
    totalKw,
    L1kw,
    L2kw,
    L3kw,
    imbalancePct,
    hasPhasedDevices,
    pdus
  };
}

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
  const occupiedU = rackDevices.reduce((sum, d) => sum + (d.u_hoehe || 0), 0);
  const percent = rack.hoehe_u > 0 ? Math.round((occupiedU / rack.hoehe_u) * 100) : 0;
  
  const totalKw = rackDevices.reduce((s, d) => s + (Number(d.anschlussleistung_watt ?? d.tdp_watt) || 0), 0) / 1000;
  
  const L1kw = rackDevices.filter(d => d.phase === 'L1').reduce((s, d) => s + (Number(d.anschlussleistung_watt ?? d.tdp_watt) || 0), 0) / 1000;
  const L2kw = rackDevices.filter(d => d.phase === 'L2').reduce((s, d) => s + (Number(d.anschlussleistung_watt ?? d.tdp_watt) || 0), 0) / 1000;
  const L3kw = rackDevices.filter(d => d.phase === 'L3').reduce((s, d) => s + (Number(d.anschlussleistung_watt ?? d.tdp_watt) || 0), 0) / 1000;
  
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

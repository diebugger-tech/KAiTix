export function nodeColor(typ: string) {
  const m: Record<string, string> = { 
    server: '#1e40af', 
    switch: '#065f46', 
    pdu: '#78350f', 
    firewall: '#7f1d1d', 
    storage: '#4c1d95', 
    kvm: '#1e3a5f',
    patchpanel: '#b45309'
  };
  return m[typ] ?? '#1e293b';
}

export function nodeStroke(typ: string) {
  const m: Record<string, string> = { 
    server: '#3b82f6', 
    switch: '#10b981', 
    pdu: '#f59e0b', 
    firewall: '#ef4444', 
    storage: '#8b5cf6', 
    kvm: '#38bdf8',
    patchpanel: '#f59e0b'
  };
  return m[typ] ?? '#475569';
}

export function baseEdgeColor(typ: string, phase?: string, isPower?: boolean): string {
  if (isPower) {
    if (phase === 'L1') return '#f97316';
    if (phase === 'L2') return '#84cc16';
    if (phase === 'L3') return '#a855f7';
    return '#ef4444';
  }
  const t = (typ || '').toLowerCase();
  if (t.includes('lc') || t.includes('sc') || t.includes('lwl')) return '#d946ef';
  if (t.startsWith('cat')) return '#3b82f6';
  if (t === 'dac') return '#6b7280';
  if (t.includes('sfp')) return '#06b6d4';
  if (t.startsWith('strom') || t.startsWith('cee')) return '#ef4444';
  return '#94a3b8';
}

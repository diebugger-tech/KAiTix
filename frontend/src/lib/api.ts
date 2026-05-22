import { appState } from './state.svelte';

export interface Device {
  id: number;
  hostname: string;
  typ: 'server' | 'switch' | 'pdu' | 'sonstige';
  ip_adresse?: string;
  hersteller?: string;
  modell?: string;
  seriennummer?: string;
  inventarnummer?: string;
  rack_id?: number;
  u_position?: number;
  u_hoehe: number;
  side?: 'left' | 'right';
  circuit_id?: number;
  phase?: 'L1' | 'L2' | 'L3';
  tdp_watt?: number;
  psu_count?: number;
  psu_nennwatt?: number;
  anschlussleistung_watt?: number;
  einschaltstrom_faktor?: number;
  bemerkung?: string;
  strom_typ?: string;
  spannung_v?: number;
  anschlussleistung_a?: number;
  anschluss_stecker?: string;
  device_ports?: DevicePort[];
  pdu_outlets?: PduOutlet[];
  server_interfaces?: any[];
  connected_pdu_outlets?: PduOutlet[];
}

export interface Rack {
  id: number;
  name: string;
  standort: string;
  hoehe_u: number;
  breite_mm?: number;
  bemerkung?: string;
  max_watt?: number;
  usv_n1_redundant?: boolean;
  devices?: Device[];
  hersteller?: string;
  modell?: string;
  hardware_type_id?: number;
}

export interface Cable {
  id: number;
  kabel_nr: string;
  typ: string;
  laenge_m: number;
  farbe?: string;
  von_device_id?: number;
  von_port?: string;
  nach_device_id?: number;
  nach_port?: string;
  verlegt_am?: string;
  verlegt_von?: string;
  bemerkung?: string;
  von_device?: { hostname: string };
  nach_device?: { hostname: string };
}

export interface DevicePort {
  id: number;
  device_id: number;
  port_name: string;
  typ: string;
  status: 'frei' | 'belegt' | 'defekt';
  kabel_id?: number;
}

export interface PduOutlet {
  id: number;
  pdu_id: number;
  outlet_name: string;
  phase?: 'L1' | 'L2' | 'L3';
  steckdosentyp?: 'C13' | 'C19' | 'C14' | 'C20' | 'Schuko' | 'CEE-16A';
  max_watt?: number;
  schaltbar: boolean;
  connected_device_id?: number;
  connected_port?: string;
  connected_device?: { hostname: string };
}

export interface PduPhaseOverview {
  L1: PduOutlet[];
  L2: PduOutlet[];
  L3: PduOutlet[];
  total_outlets: number;
  total_max_watt: number;
}

export interface HardwareType {
  id: number;
  name: string;
  kategorie: 'server' | 'switch' | 'firewall' | 'storage' | 'pdu' | 'kvm' | 'usv' | 'usv_modul' | 'sonstige' | 'rack';
  hersteller: string;
  modell: string;
  u_hoehe: number;
  breite_mm?: number;
  tiefe_mm?: number;
  tdp_watt?: number;
  psu_count?: number;
  psu_nennwatt?: number;
  leistung_kw?: number;
  n1_faehig?: boolean;
  port_count_rj45: number;
  port_count_lwl: number;
  port_count_sfp: number;
  min_rack_hoehe?: number;
  bemerkung: string;
}

export interface UsvModule {
  id: number;
  usv_unit_id: number;
  slot: number;
  leistung_kw: number;
  status: 'aktiv' | 'reserve' | 'defekt';
  seriennummer?: string;
}

export interface UsvUnit {
  id: number;
  bezeichnung: string;
  hersteller: string;
  rack_id: number;
  max_kw: number;
  modules?: UsvModule[];
}

export interface UsvStatus {
  usv_unit_id: number;
  bezeichnung: string;
  installed_kw: number;
  n1_kw: number;
  phase_capacity_n1_kw: number;
  loads: {
    l1: { load_kw: number; peak_kw: number };
    l2: { load_kw: number; peak_kw: number };
    l3: { load_kw: number; peak_kw: number };
  };
  total_load_kw: number;
  total_peak_kw: number;
  imbalance_kw: number;
  n1_safe: boolean;
  kaltstart_ok: boolean;
  recommended_modules_count: number;
  recommended_module_capacity_kw: number;
  active_modules_count: number;
  devices: Array<Record<string, unknown>>;
}

export interface SystemState {
  status: 'stable' | 'degraded' | 'critical';
  grid_online: boolean;
  battery_soc_pct: number;
  battery_runtime_min: number;
  loads: { l1: number; l2: number; l3: number };
  total_load_kw: number;
  installed_kw: number;
  n1_kw: number;
  phase_capacity_n1_kw: number;
  n1_safe: boolean;
  imbalance_kw: number;
  installed_modules_count: number;
  active_modules_count: number;
  failed_modules_count: number;
  module_capacity_kw: number;
  battery_voltage: number;
  battery_capacity_ah: number;
  peukert_exponent: number;
  inverter_efficiency: number;
}

export interface USVSimulationEvent {
  id: number;
  timestamp: string;
  event_type: string;
  severity: 'info' | 'warning' | 'critical';
  description: string;
  usv_unit_id: number | null;
  snapshot_json: string | null;
}

export interface FaultSimResponse {
  system_state: SystemState;
  event: USVSimulationEvent;
}

export interface BatterySummary {
  battery_type: string;
  battery_type_name: string;
  total_voltage_v: number;
  nominal_capacity_ah: number;
  nominal_energy_kwh: number;
  effective_capacity_ah: number;
  effective_energy_kwh: number;
  aging_factor_pct: number;
  temperature_factor_pct: number;
  peukert_k: number;
  lifespan_years: number;
  series_blocks: number;
  parallel_strings: number;
  total_blocks: number;
  age_years: number;
  temperature_c: number;
}

export interface RuntimeCurvePoint {
  load_kw: number;
  runtime_min: number;
  load_pct: number;
}

export interface RuntimeCurveData {
  curve: RuntimeCurvePoint[];
  battery_summary: BatterySummary;
  current_runtime_min: number;
  installed_kw: number;
  total_load_kw: number;
  n1_kw: number;
  n1_safe: boolean;
}

export interface DimensioningResult {
  required_capacity_ah: number;
  series_blocks: number;
  parallel_strings: number;
  total_blocks: number;
  actual_capacity_ah: number;
  actual_runtime_min: number;
  system_voltage_v: number;
  block_voltage_v: number;
  block_capacity_ah: number;
  target_runtime_min: number;
  load_kw: number;
  load_with_margin_kw: number;
  safety_margin_pct: number;
  battery_type: string;
  battery_type_name: string;
}

async function request(path: string, options: RequestInit = {}) {
  // Vite proxy routes /api to http://localhost:8003
  const url = path.startsWith('/') ? path : `/api/v1/${path}`;
  
  const headers = new Headers(options.headers || {});
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  
  // Inject bearbeiter name in headers for audit-log
  headers.set('X-Username', appState.bearbeiter);

  try {
    const response = await fetch(url, { ...options, headers });
    if (!response.ok) {
      const errText = await response.text();
      let msg = errText || response.statusText;
      try {
        const parsed = JSON.parse(errText);
        if (parsed?.detail) msg = parsed.detail;
      } catch { /* not JSON */ }
      throw new Error(msg);
    }
    appState.setBackendStatus(true);
    if (response.status === 204) {
      return null;
    }
    return response.json();
  } catch (error) {
    console.error(`API request failed on ${url}:`, error);
    appState.setBackendStatus(false);
    throw error;
  }
}

export const api = {
  // Racks
  getRacks: (): Promise<Rack[]> => request('racks/'),
  getRack: (id: number): Promise<Rack> => request(`racks/${id}`),
  createRack: (rack: Partial<Rack>): Promise<Rack> => request('racks/', { method: 'POST', body: JSON.stringify(rack) }),
  updateRack: (id: number, rack: Partial<Rack>): Promise<Rack> => request(`racks/${id}`, { method: 'PUT', body: JSON.stringify(rack) }),
  deleteRack: (id: number): Promise<null> => request(`racks/${id}`, { method: 'DELETE' }),

  // Devices
  getDevices: (): Promise<Device[]> => request('devices/'),
  getDevice: (id: number): Promise<Device> => request(`devices/${id}`),
  createDevice: (device: Partial<Device>): Promise<Device> => request('devices/', { method: 'POST', body: JSON.stringify(device) }),
  updateDevice: (id: number, device: Partial<Device>): Promise<Device> => request(`devices/${id}`, { method: 'PUT', body: JSON.stringify(device) }),
  deleteDevice: (id: number): Promise<null> => request(`devices/${id}`, { method: 'DELETE' }),
  getDevicePorts: (deviceId: number): Promise<DevicePort[]> => request(`devices/${deviceId}/ports`),
  addDeviceInterface: (deviceId: number, data: { port_name: string; typ?: string; mac_adresse?: string | null }): Promise<{ id: number; port_name: string; typ: string }> =>
    request(`devices/${deviceId}/interfaces`, { method: 'POST', body: JSON.stringify(data) }),

  // Cables
  getCables: (): Promise<Cable[]> => request('cables/'),
  getCable: (id: number): Promise<Cable> => request(`cables/${id}`),
  createCable: (cable: Partial<Cable>): Promise<Cable> => request('cables/', { method: 'POST', body: JSON.stringify(cable) }),
  updateCable: (id: number, cable: Partial<Cable>): Promise<Cable> => request(`cables/${id}`, { method: 'PUT', body: JSON.stringify(cable) }),
  deleteCable: (id: number): Promise<null> => request(`cables/${id}`, { method: 'DELETE' }),
  suggestCableColor: (typ: string): Promise<{ typ: string; suggested_color: string; note: string }> => request(`cables/suggest-color?typ=${encodeURIComponent(typ)}`),
  getColorRules: (): Promise<{ version: string; last_updated: string; rules: Array<{ id: string; typ: string; standard_farbe: string; kategorie: string; verwendungszweck: string; standard: string; hex: string }> }> => request('cables/color-rules'),
  updateColorRules: (rules: any[]): Promise<any> => request('cables/color-rules', { method: 'PUT', body: JSON.stringify({ rules }) }),

  // USV
  getUsvUnits: (): Promise<UsvUnit[]> => request('usv/'),
  getUsvStatus: (usvUnitId: number): Promise<UsvStatus> => request(`usv/${usvUnitId}/status`),
  simulateUsv: (data: {
    l1_kw: number;
    l2_kw: number;
    l3_kw: number;
    module_capacity_kw: number;
    installed_modules_count: number;
  }) => request('usv/simulate', { method: 'POST', body: JSON.stringify(data) }),
  simulateUsvFault: (data: {
    fault_type: string;
    l1_kw: number;
    l2_kw: number;
    l3_kw: number;
    module_capacity_kw: number;
    installed_modules_count: number;
    system_state?: SystemState | null;
    battery_voltage?: number;
    battery_capacity_ah?: number;
    peukert_exponent?: number;
    inverter_efficiency?: number;
  }): Promise<FaultSimResponse> =>
    request('usv/simulate/fault', { method: 'POST', body: JSON.stringify(data) }),
  getUsvEvents: (limit?: number): Promise<USVSimulationEvent[]> =>
    request(`usv/events?limit=${limit ?? 50}`),
  getRuntimeCurve: (data: {
    l1_kw: number;
    l2_kw: number;
    l3_kw: number;
    module_capacity_kw: number;
    installed_modules_count: number;
    battery_type: string;
    series_blocks: number;
    parallel_strings: number;
    block_voltage_v?: number;
    block_capacity_ah?: number;
    age_years?: number;
    temperature_c?: number;
    inverter_efficiency?: number;
  }): Promise<RuntimeCurveData> =>
    request('usv/battery/runtime-curve', { method: 'POST', body: JSON.stringify(data) }),
  getDimensioning: (data: {
    load_kw: number;
    target_runtime_min: number;
    battery_type: string;
    block_voltage_v?: number;
    block_capacity_ah?: number;
    inverter_efficiency?: number;
    system_voltage_v?: number;
    safety_margin_pct?: number;
  }): Promise<DimensioningResult> =>
    request('usv/battery/dimension', { method: 'POST', body: JSON.stringify(data) }),

  // PDUs
  getPdus: (): Promise<Device[]> => request('pdus/'),
  getPdu: (id: number): Promise<Device> => request(`pdus/${id}`),
  createPdu: (pdu: Partial<Device>): Promise<Device> => request('pdus/', { method: 'POST', body: JSON.stringify(pdu) }),
  updatePdu: (id: number, pdu: Partial<Device>): Promise<Device> => request(`pdus/${id}`, { method: 'PUT', body: JSON.stringify(pdu) }),
  deletePdu: (id: number): Promise<null> => request(`pdus/${id}`, { method: 'DELETE' }),
  getPduOutlets: (pduId: number): Promise<PduOutlet[]> => request(`pdus/${pduId}/outlets`),
  createPduOutlet: (pduId: number, outlet: Partial<PduOutlet>): Promise<PduOutlet> => request(`pdus/${pduId}/outlets`, { method: 'POST', body: JSON.stringify(outlet) }),
  updatePduOutlet: (pduId: number, outletId: number, data: Partial<PduOutlet>): Promise<PduOutlet> => request(`pdus/${pduId}/outlets/${outletId}`, { method: 'PUT', body: JSON.stringify(data) }),
  deletePduOutlet: (pduId: number, outletId: number): Promise<null> => request(`pdus/${pduId}/outlets/${outletId}`, { method: 'DELETE' }),
  getPduPhaseOverview: (pduId: number): Promise<PduPhaseOverview> => request(`pdus/${pduId}/phase-overview`),

  // Hardware Catalog
  getHardware: (kategorie?: string): Promise<HardwareType[]> => request(`hardware/${kategorie ? '?kategorie=' + encodeURIComponent(kategorie) : ''}`),
  getHardwareItem: (id: number): Promise<HardwareType> => request(`hardware/${id}`),
  createHardware: (item: Partial<HardwareType>): Promise<HardwareType> => request('hardware/', { method: 'POST', body: JSON.stringify(item) }),
  updateHardware: (id: number, item: Partial<HardwareType>): Promise<HardwareType> => request(`hardware/${id}`, { method: 'PUT', body: JSON.stringify(item) }),
  deleteHardware: (id: number): Promise<null> => request(`hardware/${id}`, { method: 'DELETE' }),

  // Device types (for topology filter)
  getDeviceTypes: (): Promise<{ device_types: string[]; has_power_edges: boolean }> => request('devices/types'),

  // Topology
  getTopology: (): Promise<{
    racks: Array<{ id: number; name: string; standort: string; hoehe_u: number }>;
    nodes: Array<{
      id: number; hostname: string; typ: string; rack_id: number | null;
      rack_name: string | null; u_position: number | null; u_hoehe: number;
      hersteller: string | null; modell: string | null; ip_adresse: string | null;
    }>;
    edges: Array<{
      id: string; kabel_nr: string; typ: string; laenge_m: number; farbe: string | null;
      von_device_id: number; von_port: string | null;
      nach_device_id: number; nach_port: string | null; cross_rack: boolean;
    }>;
  }> => request('topology'),

  // CSV Import
  previewDeviceCsv: (file: File): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    return request('import-csv/devices/preview', { method: 'POST', body: formData });
  },
  commitDeviceCsv: (rows: any[], update_mode = false): Promise<{ created: number; updated: number; skipped: number }> =>
    request('import-csv/devices/commit', { method: 'POST', body: JSON.stringify({ rows, update_mode }) }),
  previewCableCsv: (file: File): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    return request('import-csv/cables/preview', { method: 'POST', body: formData });
  },
  commitCableCsv: (rows: any[], update_mode = false): Promise<{ created: number; updated: number }> =>
    request('import-csv/cables/commit', { method: 'POST', body: JSON.stringify({ rows, update_mode }) }),

  // EPLAN Import
  previewEplan: (file: File, mapping: Record<string, string>): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('mapping_json', JSON.stringify(mapping));
    return request('import-eplan/preview', {
      method: 'POST',
      body: formData
    });
  },
  commitEplan: (connections: any[]): Promise<{ message: string; count: number }> => {
    return request('import-eplan/commit', {
      method: 'POST',
      body: JSON.stringify({ connections })
    });
  },

  // Search
  search: (q: string): Promise<{
    devices: Array<{ id: number; hostname: string; typ: string; rack_id: number | null; ip_adresse: string | null; hersteller: string | null; modell: string | null }>;
    cables: Array<{ id: number; kabel_nr: string; typ: string; farbe: string | null; von_port: string | null; nach_port: string | null }>;
    racks: Array<{ id: number; name: string; standort: string }>;
  }> => request(`search?q=${encodeURIComponent(q)}`),

  // Cable trace
  traceCable: (id: number): Promise<{
    trace: Array<{
      id: number; kabel_nr: string | null; typ: string; laenge_m: number | null; farbe: string | null;
      von_device_id: number | null; von_device_hostname: string | null; von_port: string | null;
      nach_device_id: number | null; nach_device_hostname: string | null; nach_port: string | null;
    }>;
    hops: number;
  }> => request(`cables/${id}/trace`),

};

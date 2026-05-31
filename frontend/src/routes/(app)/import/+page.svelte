<script lang="ts">
  import { api } from '$lib/api';
  import { Upload, Download, CheckCircle, AlertCircle, AlertTriangle, FileText, X } from '@lucide/svelte';

  type Tab = 'devices' | 'cables' | 'eplan';

  let activeTab = $state<Tab>('devices');

  // ── Geräte CSV ──────────────────────────────────────────────────────────────
  let deviceFile = $state<File | null>(null);
  let devicePreview = $state<any>(null);
  let deviceLoading = $state(false);
  let deviceCommitting = $state(false);
  let deviceUpdateMode = $state(false);
  let deviceResult = $state<{ created: number; updated: number; skipped: number } | null>(null);
  let deviceError = $state('');

  async function previewDevices() {
    if (!deviceFile) return;
    deviceLoading = true;
    deviceError = '';
    devicePreview = null;
    deviceResult = null;
    try {
      devicePreview = await api.previewDeviceCsv(deviceFile);
    } catch (e: any) {
      deviceError = e.message ?? 'Fehler beim Lesen der Datei';
    } finally {
      deviceLoading = false;
    }
  }

  async function commitDevices() {
    if (!devicePreview) return;
    const rows = deviceUpdateMode
      ? devicePreview.rows.filter((r: any) => r.status === 'new' || r.status === 'exists')
      : devicePreview.rows.filter((r: any) => r.status === 'new');
    if (!rows.length) return;
    deviceCommitting = true;
    try {
      deviceResult = await api.commitDeviceCsv(rows, deviceUpdateMode);
      devicePreview = null;
      deviceFile = null;
    } catch (e: any) {
      deviceError = e.message ?? 'Fehler beim Import';
    } finally {
      deviceCommitting = false;
    }
  }

  function resetDevices() {
    deviceFile = null;
    devicePreview = null;
    deviceResult = null;
    deviceError = '';
  }

  // ── Kabel CSV ───────────────────────────────────────────────────────────────
  let cableFile = $state<File | null>(null);
  let cablePreview = $state<any>(null);
  let cableLoading = $state(false);
  let cableCommitting = $state(false);
  let cableUpdateMode = $state(false);
  let cableResult = $state<{ created: number; updated: number } | null>(null);
  let cableError = $state('');

  async function previewCables() {
    if (!cableFile) return;
    cableLoading = true;
    cableError = '';
    cablePreview = null;
    cableResult = null;
    try {
      cablePreview = await api.previewCableCsv(cableFile);
    } catch (e: any) {
      cableError = e.message ?? 'Fehler beim Lesen der Datei';
    } finally {
      cableLoading = false;
    }
  }

  async function commitCables() {
    if (!cablePreview) return;
    const rows = cableUpdateMode
      ? cablePreview.rows.filter((r: any) => r.status === 'new' || r.status === 'exists')
      : cablePreview.rows.filter((r: any) => r.status === 'new');
    if (!rows.length) return;
    cableCommitting = true;
    try {
      cableResult = await api.commitCableCsv(rows, cableUpdateMode);
      cablePreview = null;
      cableFile = null;
    } catch (e: any) {
      cableError = e.message ?? 'Fehler beim Import';
    } finally {
      cableCommitting = false;
    }
  }

  function resetCables() {
    cableFile = null;
    cablePreview = null;
    cableResult = null;
    cableError = '';
  }

  // ── EPLAN ───────────────────────────────────────────────────────────────────
  let eplanFile = $state<File | null>(null);
  let eplanPreview = $state<any>(null);
  let eplanLoading = $state(false);
  let eplanCommitting = $state(false);
  let eplanResult = $state<{ message: string; count: number } | null>(null);
  let eplanError = $state('');
  const eplanMapping: Record<string, string> = {};

  async function previewEplan() {
    if (!eplanFile) return;
    eplanLoading = true;
    eplanError = '';
    eplanPreview = null;
    eplanResult = null;
    try {
      eplanPreview = await api.previewEplan(eplanFile, eplanMapping);
    } catch (e: any) {
      eplanError = e.message ?? 'Fehler beim Lesen der Datei';
    } finally {
      eplanLoading = false;
    }
  }

  async function commitEplan() {
    if (!eplanPreview?.connections) return;
    eplanCommitting = true;
    try {
      eplanResult = await api.commitEplan(eplanPreview.connections);
      eplanPreview = null;
      eplanFile = null;
    } catch (e: any) {
      eplanError = e.message ?? 'Fehler beim Import';
    } finally {
      eplanCommitting = false;
    }
  }

  function resetEplan() {
    eplanFile = null;
    eplanPreview = null;
    eplanResult = null;
    eplanError = '';
  }

  function getErrorSummary(preview: any): {msg: string, count: number}[] {
    if (!preview || !preview.rows) return [];
    const counts: Record<string, number> = {};
    for (const row of preview.rows) {
      if (row.errors && Array.isArray(row.errors)) {
        for (const err of row.errors) {
          counts[err] = (counts[err] || 0) + 1;
        }
      }
    }
    return Object.entries(counts)
      .map(([msg, count]) => ({msg, count}))
      .sort((a, b) => b.count - a.count);
  }

  // ── Helpers ─────────────────────────────────────────────────────────────────
  function rowClass(status: string) {
    if (status === 'new') return 'bg-emerald-950/30 border-l-2 border-emerald-500';
    if (status === 'exists') return 'bg-amber-950/30 border-l-2 border-amber-500';
    return 'bg-red-950/30 border-l-2 border-red-500';
  }

  function statusBadge(status: string) {
    if (status === 'new') return 'bg-emerald-500/20 text-emerald-400';
    if (status === 'exists') return 'bg-amber-500/20 text-amber-400';
    return 'bg-red-500/20 text-red-400';
  }

  function statusLabel(status: string) {
    if (status === 'new') return 'Neu';
    if (status === 'exists') return 'Vorhanden';
    return 'Fehler';
  }

  const deviceTemplateCsv =
    'hostname,typ,rack,u_position,u_hoehe,hersteller,modell,seriennummer,inventarnummer,ip_adresse,bemerkung\n' +
    'srv-01,server,Rack-A,1,2,Dell,PowerEdge R750,SN123,INV456,192.168.1.10,Datenbankserver\n' +
    'sw-01,switch,Rack-A,20,1,Cisco,Catalyst 9300,SN789,,192.168.1.1,Core Switch\n';

  const cableTemplateCsv =
    'kabel_nr,typ,laenge_m,von_geraet,von_port,zu_geraet,zu_port,farbe,bemerkung\n' +
    'K-001,Cat6A,3.0,sw-01,Gi1/0/1,srv-01,eth0,blau,Uplink\n' +
    'K-002,LC-LC,5.0,sw-01,SFP1,srv-02,SFP0,gelb,LWL\n';

  function downloadTemplate(content: string, filename: string) {
    const blob = new Blob([content], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }
</script>

<div class="max-w-6xl mx-auto space-y-6">
  <!-- Tab Bar -->
  <div class="flex gap-1 bg-[var(--color-bg3)] border border-[var(--color-border)] rounded-xl p-1 w-fit">
    {#each [['devices', 'Geräte CSV'], ['cables', 'Kabel CSV'], ['eplan', 'EPLAN']] as [tab, label]}
      <button
        onclick={() => activeTab = tab as Tab}
        class="px-5 py-2 rounded-lg text-sm font-medium transition-all {activeTab === tab ? 'bg-[#1D9E75] text-[var(--color-text)] shadow-lg shadow-blue-600/20' : 'text-[var(--color-text2)] hover:text-slate-200'}"
      >
        {label}
      </button>
    {/each}
  </div>

  <!-- ── Geräte CSV Tab ───────────────────────────────────────────────────── -->
  {#if activeTab === 'devices'}
    <div class="space-y-4">
      <!-- Header Card -->
      <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-6">
        <div class="flex items-start justify-between">
          <div>
            <h2 class="text-lg font-bold text-[var(--color-text)] mb-1">Geräte importieren</h2>
            <p class="text-sm text-[var(--color-text2)]">
              CSV-Datei mit Gerätestammdaten hochladen. Vorhandene Hostnamen werden übersprungen.
            </p>
            <p class="text-xs text-[var(--color-text3)] mt-1 font-mono">
              Spalten: hostname, typ, rack, u_position, u_hoehe, hersteller, modell, seriennummer, inventarnummer, ip_adresse, bemerkung
            </p>
          </div>
          <button
            onclick={() => downloadTemplate(deviceTemplateCsv, 'geraete-vorlage.csv')}
            class="flex items-center gap-2 px-3 py-2 bg-[var(--color-border)] hover:bg-[var(--color-border2)] border border-[var(--color-border2)] rounded-lg text-xs text-[var(--color-text)] transition shrink-0"
          >
            <Download class="w-3.5 h-3.5" />
            Vorlage CSV
          </button>
        </div>

        <!-- Upload -->
        {#if !devicePreview && !deviceResult}
          <div class="mt-4 flex items-center gap-4">
            <label class="flex-1 flex items-center justify-center gap-3 border-2 border-dashed border-[var(--color-border2)] hover:border-blue-600 rounded-xl p-6 cursor-pointer transition group">
              <input
                type="file"
                accept=".csv"
                class="hidden"
                onchange={(e) => {
                  const f = (e.target as HTMLInputElement).files?.[0];
                  if (f) { deviceFile = f; deviceError = ''; }
                }}
              />
              <Upload class="w-5 h-5 text-[var(--color-text3)] group-hover:text-blue-400 transition" />
              <span class="text-sm text-[var(--color-text2)] group-hover:text-slate-200 transition">
                {deviceFile ? deviceFile.name : 'CSV-Datei auswählen oder hier ablegen'}
              </span>
            </label>
            <button
              onclick={previewDevices}
              disabled={!deviceFile || deviceLoading}
              class="px-5 py-3 bg-[#1D9E75] hover:bg-[#0F6E56] disabled:opacity-40 text-[var(--color-text)] rounded-xl text-sm font-semibold transition shrink-0"
            >
              {deviceLoading ? 'Prüfe…' : 'Vorschau'}
            </button>
          </div>
          {#if deviceError}
            <p class="mt-2 text-xs text-red-400 flex items-center gap-1"><AlertCircle class="w-3.5 h-3.5" />{deviceError}</p>
          {/if}
        {/if}
      </div>

      <!-- Success -->
      {#if deviceResult}
        <div class="bg-emerald-950/30 border border-emerald-700/40 rounded-xl p-6 flex items-center gap-4">
          <CheckCircle class="w-8 h-8 text-emerald-400 shrink-0" />
          <div>
            <p class="font-semibold text-emerald-300">Import abgeschlossen</p>
            <p class="text-sm text-emerald-400/80 mt-0.5">
              {deviceResult.created} Gerät{deviceResult.created !== 1 ? 'e' : ''} erstellt
              {#if deviceResult.updated > 0}, {deviceResult.updated} aktualisiert{/if}
              {#if deviceResult.skipped > 0}, {deviceResult.skipped} übersprungen{/if}
            </p>
          </div>
          <button onclick={resetDevices} class="ml-auto text-[var(--color-text3)] hover:text-[var(--color-text)] transition">
            <X class="w-4 h-4" />
          </button>
        </div>
      {/if}

      <!-- Preview Table -->
      {#if devicePreview}
        <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl overflow-hidden">
          <!-- Summary Bar -->
          <div class="flex flex-col border-b border-[var(--color-border)]">
            <div class="flex items-center gap-6 px-6 py-4">
              <span class="text-sm text-[var(--color-text2)]">{devicePreview.total} Zeilen</span>
              <span class="text-sm text-emerald-400">{devicePreview.new} neu</span>
              {#if devicePreview.exists > 0}
                <span class="text-sm text-amber-400">{devicePreview.exists} vorhanden</span>
              {/if}
              {#if devicePreview.error_count > 0}
                <span class="text-sm text-red-400 font-semibold">{devicePreview.error_count} Fehler</span>
              {/if}
            </div>
            <div class="px-6 pb-4 flex items-center gap-3">
              {#if devicePreview.exists > 0}
                <label class="flex items-center gap-1.5 cursor-pointer text-xs text-[var(--color-text)] select-none">
                  <input type="checkbox" bind:checked={deviceUpdateMode} class="accent-amber-500" />
                  Vorhandene aktualisieren
                </label>
              {/if}
              <button onclick={resetDevices} class="ml-auto px-3 py-1.5 text-xs text-[var(--color-text2)] hover:text-slate-200 transition">
                Abbrechen
              </button>
              <button
                onclick={commitDevices}
                disabled={deviceCommitting || devicePreview.error_count > 0 || (deviceUpdateMode ? devicePreview.new + devicePreview.exists === 0 : devicePreview.new === 0)}
                class="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-[var(--color-text)] rounded-lg text-xs font-semibold transition"
              >
                {deviceCommitting ? 'Importiere…' : deviceUpdateMode
                  ? `${devicePreview.new + devicePreview.exists} Gerät${devicePreview.new + devicePreview.exists !== 1 ? 'e' : ''} importieren/aktualisieren`
                  : `${devicePreview.new} Gerät${devicePreview.new !== 1 ? 'e' : ''} importieren`}
              </button>
            </div>

            <!-- Aggregated Errors -->
            {#if devicePreview.error_count > 0}
              <div class="px-6 pb-4">
                <div class="bg-red-950/30 border border-red-900/50 rounded-lg p-3 flex flex-col gap-1.5">
                  <span class="text-xs font-semibold text-red-400 mb-0.5">Zusammenfassung der Fehler:</span>
                  {#each getErrorSummary(devicePreview) as errSum}
                    <div class="text-xs text-red-300 flex items-center gap-2">
                      <span class="bg-red-900/50 px-1.5 py-0.5 rounded text-center font-mono min-w-[24px]">{errSum.count}x</span>
                      <span>{errSum.msg}</span>
                    </div>
                  {/each}
                </div>
              </div>
            {/if}
          </div>

          <div class="overflow-x-auto">
            <table class="w-full text-xs">
              <thead>
                <tr class="border-b border-[var(--color-border)] text-[var(--color-text3)] uppercase tracking-wider">
                  <th class="px-4 py-2.5 text-left font-medium">#</th>
                  <th class="px-4 py-2.5 text-left font-medium">Status</th>
                  <th class="px-4 py-2.5 text-left font-medium">Hostname</th>
                  <th class="px-4 py-2.5 text-left font-medium">Typ</th>
                  <th class="px-4 py-2.5 text-left font-medium">Rack</th>
                  <th class="px-4 py-2.5 text-left font-medium">HE-Pos.</th>
                  <th class="px-4 py-2.5 text-left font-medium">Höhe</th>
                  <th class="px-4 py-2.5 text-left font-medium">Hersteller / Modell</th>
                  <th class="px-4 py-2.5 text-left font-medium">Fehler</th>
                </tr>
              </thead>
              <tbody>
                {#each devicePreview.rows as row}
                  <tr class="border-b border-[var(--color-border)]/50 {rowClass(row.status)}">
                    <td class="px-4 py-2 text-[var(--color-text3)]">{row.row}</td>
                    <td class="px-4 py-2">
                      <span class="px-2 py-0.5 rounded text-[10px] font-semibold {statusBadge(row.status)}">
                        {statusLabel(row.status)}
                      </span>
                    </td>
                    <td class="px-4 py-2 text-slate-200 font-mono">{row.hostname || '—'}</td>
                    <td class="px-4 py-2 text-[var(--color-text)]">{row.typ}</td>
                    <td class="px-4 py-2 text-[var(--color-text)]">{row.rack || '—'}</td>
                    <td class="px-4 py-2 text-[var(--color-text)]">{row.u_position ?? '—'}</td>
                    <td class="px-4 py-2 text-[var(--color-text)]">{row.u_hoehe}U</td>
                    <td class="px-4 py-2 text-[var(--color-text2)]">{[row.hersteller, row.modell].filter(Boolean).join(' / ') || '—'}</td>
                    <td class="px-4 py-2 text-red-400">{row.errors?.join(', ') || ''}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>
      {/if}
    </div>

  <!-- ── Kabel CSV Tab ────────────────────────────────────────────────────── -->
  {:else if activeTab === 'cables'}
    <div class="space-y-4">
      <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-6">
        <div class="flex items-start justify-between">
          <div>
            <h2 class="text-lg font-bold text-[var(--color-text)] mb-1">Kabel importieren</h2>
            <p class="text-sm text-[var(--color-text2)]">
              CSV-Datei mit Kabelverbindungen. Geräte müssen bereits in der Datenbank existieren.
            </p>
            <p class="text-xs text-[var(--color-text3)] mt-1 font-mono">
              Spalten: kabel_nr, typ, laenge_m, von_geraet, von_port, zu_geraet, zu_port, farbe, bemerkung
            </p>
          </div>
          <button
            onclick={() => downloadTemplate(cableTemplateCsv, 'kabel-vorlage.csv')}
            class="flex items-center gap-2 px-3 py-2 bg-[var(--color-border)] hover:bg-[var(--color-border2)] border border-[var(--color-border2)] rounded-lg text-xs text-[var(--color-text)] transition shrink-0"
          >
            <Download class="w-3.5 h-3.5" />
            Vorlage CSV
          </button>
        </div>

        {#if !cablePreview && !cableResult}
          <div class="mt-4 flex items-center gap-4">
            <label class="flex-1 flex items-center justify-center gap-3 border-2 border-dashed border-[var(--color-border2)] hover:border-blue-600 rounded-xl p-6 cursor-pointer transition group">
              <input
                type="file"
                accept=".csv"
                class="hidden"
                onchange={(e) => {
                  const f = (e.target as HTMLInputElement).files?.[0];
                  if (f) { cableFile = f; cableError = ''; }
                }}
              />
              <Upload class="w-5 h-5 text-[var(--color-text3)] group-hover:text-blue-400 transition" />
              <span class="text-sm text-[var(--color-text2)] group-hover:text-slate-200 transition">
                {cableFile ? cableFile.name : 'CSV-Datei auswählen oder hier ablegen'}
              </span>
            </label>
            <button
              onclick={previewCables}
              disabled={!cableFile || cableLoading}
              class="px-5 py-3 bg-[#1D9E75] hover:bg-[#0F6E56] disabled:opacity-40 text-[var(--color-text)] rounded-xl text-sm font-semibold transition shrink-0"
            >
              {cableLoading ? 'Prüfe…' : 'Vorschau'}
            </button>
          </div>
          {#if cableError}
            <p class="mt-2 text-xs text-red-400 flex items-center gap-1"><AlertCircle class="w-3.5 h-3.5" />{cableError}</p>
          {/if}
        {/if}
      </div>

      {#if cableResult}
        <div class="bg-emerald-950/30 border border-emerald-700/40 rounded-xl p-6 flex items-center gap-4">
          <CheckCircle class="w-8 h-8 text-emerald-400 shrink-0" />
          <div>
            <p class="font-semibold text-emerald-300">Import abgeschlossen</p>
            <p class="text-sm text-emerald-400/80 mt-0.5">
              {cableResult.created} Kabel erstellt
              {#if cableResult.updated > 0}, {cableResult.updated} aktualisiert{/if}
            </p>
          </div>
          <button onclick={resetCables} class="ml-auto text-[var(--color-text3)] hover:text-[var(--color-text)] transition">
            <X class="w-4 h-4" />
          </button>
        </div>
      {/if}

      {#if cablePreview}
        <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl overflow-hidden">
          <div class="flex flex-col border-b border-[var(--color-border)]">
            <div class="flex items-center gap-6 px-6 py-4">
              <span class="text-sm text-[var(--color-text2)]">{cablePreview.total} Zeilen</span>
              <span class="text-sm text-emerald-400">{cablePreview.new} neu</span>
              {#if cablePreview.exists > 0}
                <span class="text-sm text-amber-400">{cablePreview.exists} vorhanden</span>
              {/if}
              {#if cablePreview.error_count > 0}
                <span class="text-sm text-red-400 font-semibold">{cablePreview.error_count} Fehler</span>
              {/if}
            </div>
            <div class="px-6 pb-4 flex items-center gap-3">
              {#if cablePreview.exists > 0}
                <label class="flex items-center gap-1.5 cursor-pointer text-xs text-[var(--color-text)] select-none">
                  <input type="checkbox" bind:checked={cableUpdateMode} class="accent-amber-500" />
                  Vorhandene aktualisieren
                </label>
              {/if}
              <button onclick={resetCables} class="px-3 py-1.5 text-xs text-[var(--color-text2)] hover:text-slate-200 transition">
                Abbrechen
              </button>
              <button
                onclick={commitCables}
                disabled={cableCommitting || cablePreview.error_count > 0 || (cableUpdateMode ? cablePreview.new + cablePreview.exists === 0 : cablePreview.new === 0)}
                class="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-[var(--color-text)] rounded-lg text-xs font-semibold transition"
              >
                {cableCommitting ? 'Importiere…' : cableUpdateMode
                  ? `${cablePreview.new + cablePreview.exists} Kabel importieren/aktualisieren`
                  : `${cablePreview.new} Kabel importieren`}
              </button>
            </div>

            <!-- Aggregated Errors -->
            {#if cablePreview.error_count > 0}
              <div class="px-6 pb-4">
                <div class="bg-red-950/30 border border-red-900/50 rounded-lg p-3 flex flex-col gap-1.5">
                  <span class="text-xs font-semibold text-red-400 mb-0.5">Zusammenfassung der Fehler:</span>
                  {#each getErrorSummary(cablePreview) as errSum}
                    <div class="text-xs text-red-300 flex items-center gap-2">
                      <span class="bg-red-900/50 px-1.5 py-0.5 rounded text-center font-mono min-w-[24px]">{errSum.count}x</span>
                      <span>{errSum.msg}</span>
                    </div>
                  {/each}
                </div>
              </div>
            {/if}
          </div>

          <div class="overflow-x-auto">
            <table class="w-full text-xs">
              <thead>
                <tr class="border-b border-[var(--color-border)] text-[var(--color-text3)] uppercase tracking-wider">
                  <th class="px-4 py-2.5 text-left font-medium">#</th>
                  <th class="px-4 py-2.5 text-left font-medium">Status</th>
                  <th class="px-4 py-2.5 text-left font-medium">Kabel-Nr.</th>
                  <th class="px-4 py-2.5 text-left font-medium">Typ</th>
                  <th class="px-4 py-2.5 text-left font-medium">Länge</th>
                  <th class="px-4 py-2.5 text-left font-medium">Von Gerät</th>
                  <th class="px-4 py-2.5 text-left font-medium">Von Port</th>
                  <th class="px-4 py-2.5 text-left font-medium">Zu Gerät</th>
                  <th class="px-4 py-2.5 text-left font-medium">Zu Port</th>
                  <th class="px-4 py-2.5 text-left font-medium">Farbe</th>
                  <th class="px-4 py-2.5 text-left font-medium">Fehler</th>
                </tr>
              </thead>
              <tbody>
                {#each cablePreview.rows as row}
                  <tr class="border-b border-[var(--color-border)]/50 {rowClass(row.status)}">
                    <td class="px-4 py-2 text-[var(--color-text3)]">{row.row}</td>
                    <td class="px-4 py-2">
                      <span class="px-2 py-0.5 rounded text-[10px] font-semibold {statusBadge(row.status)}">
                        {statusLabel(row.status)}
                      </span>
                    </td>
                    <td class="px-4 py-2 text-[var(--color-text)] font-mono">{row.kabel_nr || '—'}</td>
                    <td class="px-4 py-2 text-[var(--color-text)]">{row.typ}</td>
                    <td class="px-4 py-2 text-[var(--color-text)]">{row.laenge_m} m</td>
                    <td class="px-4 py-2 text-slate-200 font-mono">{row.von_geraet || '—'}</td>
                    <td class="px-4 py-2 text-[var(--color-text2)]">{row.von_port || '—'}</td>
                    <td class="px-4 py-2 text-slate-200 font-mono">{row.zu_geraet || '—'}</td>
                    <td class="px-4 py-2 text-[var(--color-text2)]">{row.zu_port || '—'}</td>
                    <td class="px-4 py-2 text-[var(--color-text2)]">{row.farbe || '—'}</td>
                    <td class="px-4 py-2 text-red-400">{row.errors?.join(', ') || ''}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>
      {/if}
    </div>

  <!-- ── EPLAN Tab ────────────────────────────────────────────────────────── -->
  {:else}
    <div class="space-y-4">
      <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-6">
        <div class="mb-4">
          <h2 class="text-lg font-bold text-[var(--color-text)] mb-1">EPLAN Import</h2>
          <p class="text-sm text-[var(--color-text2)]">
            Topologie- und Kabelverbindungen aus EPLAN importieren. Das Spaltenmapping für Quellen und Ziele (Geräte, Racks, Anschlüsse) wird automatisch erkannt.
          </p>
        </div>

        {#if !eplanPreview && !eplanResult}
          <div class="flex items-center gap-4">
            <label class="flex-1 flex items-center justify-center gap-3 border-2 border-dashed border-[var(--color-border2)] hover:border-blue-600 rounded-xl p-6 cursor-pointer transition group">
              <input
                type="file"
                accept=".csv,.txt"
                class="hidden"
                onchange={(e) => {
                  const f = (e.target as HTMLInputElement).files?.[0];
                  if (f) { eplanFile = f; eplanError = ''; }
                }}
              />
              <Upload class="w-5 h-5 text-[var(--color-text3)] group-hover:text-blue-400 transition" />
              <span class="text-sm text-[var(--color-text2)] group-hover:text-slate-200 transition">
                {eplanFile ? eplanFile.name : 'EPLAN-Exportdatei auswählen'}
              </span>
            </label>
            <button
              onclick={previewEplan}
              disabled={!eplanFile || eplanLoading}
              class="px-5 py-3 bg-[#1D9E75] hover:bg-[#0F6E56] disabled:opacity-40 text-[var(--color-text)] rounded-xl text-sm font-semibold transition shrink-0"
            >
              {eplanLoading ? 'Prüfe…' : 'Vorschau'}
            </button>
          </div>
          {#if eplanError}
            <p class="mt-2 text-xs text-red-400 flex items-center gap-1"><AlertCircle class="w-3.5 h-3.5" />{eplanError}</p>
          {/if}
        {/if}
      </div>

      {#if eplanResult}
        <div class="bg-emerald-950/30 border border-emerald-700/40 rounded-xl p-6 flex items-center gap-4">
          <CheckCircle class="w-8 h-8 text-emerald-400 shrink-0" />
          <div>
            <p class="font-semibold text-emerald-300">{eplanResult.message}</p>
            <p class="text-sm text-emerald-400/80 mt-0.5">{eplanResult.count} Verbindungen importiert</p>
          </div>
          <button onclick={() => { eplanResult = null; }} class="ml-auto text-[var(--color-text3)] hover:text-[var(--color-text)] transition">
            <X class="w-4 h-4" />
          </button>
        </div>
      {/if}

      {#if eplanPreview}
        <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl overflow-hidden">
          <div class="flex items-center gap-6 px-6 py-4 border-b border-[var(--color-border)]">
            <span class="text-sm text-[var(--color-text2)]">{eplanPreview.connections?.length ?? 0} Verbindungen</span>
            <div class="ml-auto flex gap-2">
              <button
                onclick={() => { eplanPreview = null; eplanFile = null; }}
                class="px-3 py-1.5 text-xs text-[var(--color-text2)] hover:text-slate-200 transition"
              >
                Abbrechen
              </button>
              <button
                onclick={commitEplan}
                disabled={eplanCommitting || !eplanPreview.connections?.length}
                class="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-[var(--color-text)] rounded-lg text-xs font-semibold transition"
              >
                {eplanCommitting ? 'Importiere…' : 'Importieren'}
              </button>
            </div>
          </div>
          <div class="overflow-x-auto max-h-[60vh] overflow-y-auto">
            <table class="w-full text-xs">
              <thead class="sticky top-0 bg-[var(--color-bg2)]">
                <tr class="border-b border-[var(--color-border)] text-[var(--color-text3)] uppercase tracking-wider">
                  <th class="px-4 py-2.5 text-left font-medium">Quelle</th>
                  <th class="px-4 py-2.5 text-left font-medium">Anschluss</th>
                  <th class="px-4 py-2.5 text-left font-medium">Ziel</th>
                  <th class="px-4 py-2.5 text-left font-medium">Anschluss</th>
                  <th class="px-4 py-2.5 text-left font-medium">Typ</th>
                  <th class="px-4 py-2.5 text-left font-medium">Länge</th>
                </tr>
              </thead>
              <tbody>
                {#each (eplanPreview.connections ?? []) as conn}
                  <tr class="border-b border-[var(--color-border)]/50 hover:bg-[var(--color-border2)]">
                    <td class="px-4 py-2 text-slate-200 font-mono">{conn.von_geraet ?? '—'}</td>
                    <td class="px-4 py-2 text-[var(--color-text2)]">{conn.von_port ?? '—'}</td>
                    <td class="px-4 py-2 text-slate-200 font-mono">{conn.zu_geraet ?? '—'}</td>
                    <td class="px-4 py-2 text-[var(--color-text2)]">{conn.zu_port ?? '—'}</td>
                    <td class="px-4 py-2 text-[var(--color-text)]">{conn.typ ?? '—'}</td>
                    <td class="px-4 py-2 text-[var(--color-text)]">{conn.laenge_m != null ? conn.laenge_m + ' m' : '—'}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>
      {/if}
    </div>
  {/if}
</div>

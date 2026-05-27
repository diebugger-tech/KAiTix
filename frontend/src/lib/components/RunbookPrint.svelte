<script lang="ts">
  import type { Runbook, RunbookDevice } from '$lib/api';

  interface Props {
    runbook: Runbook;
  }

  let { runbook }: Props = $props();

  // Helper to format date strings
  function formatDate(dateStr: string | undefined): string {
    if (!dateStr) return '';
    try {
      return new Date(dateStr).toLocaleDateString('de-DE', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  }

  // Get name of device
  function getDeviceName(d: RunbookDevice): string {
    if (d.vm) return d.vm.name;
    if (d.device) return d.device.hostname;
    return d.freitext || 'Unbekannt';
  }

  // Get IP Address
  function getIpAddress(d: RunbookDevice): string | null | undefined {
    return d.device?.ip_adresse || d.vm?.ip_adresse;
  }

  // Get Bemerkung / Note
  function getBemerkung(d: RunbookDevice): string | null | undefined {
    return d.note || d.device?.bemerkung || d.vm?.bemerkung;
  }

  // Generate sequence of layers sorted by position
  const sortedLayers = $derived(
    runbook.layers ? [...runbook.layers].sort((a, b) => a.position - b.position) : []
  );

  // Global device counter helper
  function getGlobalDeviceIndex(layerIndex: number, deviceIndex: number): number {
    let count = 0;
    for (let l = 0; l < sortedLayers.length; l++) {
      const layer = sortedLayers[l];
      const sortedDevices = layer.devices ? [...layer.devices].sort((a, b) => a.position - b.position) : [];
      
      if (l < layerIndex) {
        count += sortedDevices.length;
      } else if (l === layerIndex) {
        count += deviceIndex + 1;
        break;
      }
    }
    return count;
  }
</script>

<div class="print-container">
  <!-- Header -->
  <header class="print-header">
    <div class="header-main">
      <h1>{runbook.name}</h1>
      <span class="badge-type">{runbook.typ.toUpperCase()}</span>
    </div>
    <p class="description">{runbook.beschreibung || 'Keine Beschreibung vorhanden'}</p>
    <div class="meta-grid">
      <div><strong>Version:</strong> v1.0.0 (ID: {runbook.id})</div>
      <div><strong>Erstellt am:</strong> {formatDate(runbook.erstellt_am)}</div>
      <div><strong>Gedruckt am:</strong> {new Date().toLocaleDateString('de-DE')}</div>
    </div>
    <hr class="divider" />
  </header>

  <!-- Body -->
  <main class="print-body">
    {#each sortedLayers as layer, lIdx}
      {@const sortedDevices = layer.devices ? [...layer.devices].sort((a, b) => a.position - b.position) : []}
      <section class="layer-section page-break-avoid">
        <h2>Ebene {layer.position}: {layer.name}</h2>
        {#if layer.markdown_note}
          <div class="layer-note">
            <em>{layer.markdown_note}</em>
          </div>
        {/if}

        <div class="devices-list">
          {#each sortedDevices as dev, dIdx}
            {@const globalIdx = getGlobalDeviceIndex(lIdx, dIdx)}
            {@const ip = getIpAddress(dev)}
            {@const bemerkung = getBemerkung(dev)}
            <div class="device-item page-break-avoid">
              <div class="device-title">
                <span class="checkbox">☐</span>
                <span class="device-name">{globalIdx}. {getDeviceName(dev)}</span>
                <span class="delay-tag">({dev.delay_seconds}s)</span>
              </div>
              <div class="device-details">
                {#if dev.device?.phase || dev.device?.tdp_watt}
                  <span class="detail-prop">
                    {#if dev.device.phase}Phase: {dev.device.phase}{/if}
                    {#if dev.device.phase && dev.device.tdp_watt} | {/if}
                    {#if dev.device.tdp_watt}Watt: {dev.device.tdp_watt} W{/if}
                  </span>
                {/if}
                {#if dev.responsible}
                  <span class="detail-prop">Verantwortlich: {dev.responsible}</span>
                {/if}
                {#if ip}
                  <span class="detail-prop">Management: <a href="http://{ip}" target="_blank" rel="noopener noreferrer">http://{ip}</a></span>
                {/if}
              </div>
              {#if bemerkung}
                <div class="device-note">
                  <em>Notiz: {bemerkung}</em>
                </div>
              {/if}
            </div>
          {:else}
            <p class="empty-msg">Keine Geräte in dieser Ebene.</p>
          {/each}
        </div>
      </section>
    {/each}
  </main>

  <!-- Footer -->
  <footer class="print-footer">
    <div class="footer-content">
      <span class="footer-left">KAiTix — Internes Dokument — Vertraulich</span>
      <span class="footer-right">Seite <span class="page-number"></span></span>
    </div>
  </footer>
</div>

<style>
  .print-container {
    color: #000000;
    background-color: #ffffff;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.5;
    padding: 0;
    margin: 0;
    font-size: 11pt;
  }

  .print-header {
    margin-bottom: 20px;
  }

  .header-main {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 5px;
  }

  .print-header h1 {
    font-size: 24pt;
    font-weight: bold;
    margin: 0;
    color: #0f172a;
  }

  .badge-type {
    border: 1px solid #000000;
    padding: 2px 8px;
    font-size: 9pt;
    font-weight: bold;
    text-transform: uppercase;
    border-radius: 4px;
  }

  .description {
    font-size: 10pt;
    color: #475569;
    margin: 5px 0 15px 0;
  }

  .meta-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    font-size: 9pt;
    color: #334155;
    margin-bottom: 15px;
  }

  .divider {
    border: 0;
    border-top: 1px solid #cbd5e1;
    margin: 10px 0;
  }

  .layer-section {
    margin-bottom: 25px;
  }

  .layer-section h2 {
    font-size: 14pt;
    color: #1e3a8a;
    border-bottom: 1.5px solid #1e3a8a;
    padding-bottom: 3px;
    margin-top: 20px;
    margin-bottom: 10px;
  }

  .layer-note {
    background-color: #f8fafc;
    border-left: 3px solid #cbd5e1;
    padding: 6px 12px;
    font-size: 9pt;
    margin-bottom: 12px;
    color: #475569;
  }

  .devices-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .device-item {
    border-bottom: 1px solid #f1f5f9;
    padding-bottom: 6px;
  }

  .device-title {
    display: flex;
    align-items: baseline;
    gap: 10px;
  }

  .checkbox {
    font-size: 14pt;
    font-family: monospace;
    font-weight: bold;
    user-select: none;
  }

  .device-name {
    font-weight: bold;
    color: #1e293b;
  }

  .delay-tag {
    font-size: 9.5pt;
    color: #64748b;
  }

  .device-details {
    margin-left: 28px;
    font-size: 9pt;
    color: #475569;
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }

  .detail-prop {
    display: inline-block;
  }

  .device-details a {
    color: #1e3a8a;
    text-decoration: underline;
  }

  .device-note {
    margin-left: 28px;
    margin-top: 2px;
    font-size: 9pt;
    color: #64748b;
  }

  .empty-msg {
    font-size: 9.5pt;
    color: #94a3b8;
    margin-left: 28px;
    font-style: italic;
  }

  /* Print Media Specific CSS rules inside the component for safety */
  @media print {
    .print-container {
      font-size: 10pt;
    }
    
    .print-footer {
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      border-top: 1px solid #cbd5e1;
      padding-top: 5px;
      font-size: 8pt;
      color: #64748b;
      display: block !important;
    }

    .footer-content {
      display: flex;
      justify-content: space-between;
    }

    .page-number::after {
      content: counter(page);
    }

    .page-break-before {
      page-break-before: always;
    }

    .page-break-avoid {
      page-break-inside: avoid;
    }
  }

  .print-footer {
    display: none;
  }
</style>

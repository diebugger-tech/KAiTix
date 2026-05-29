<script lang="ts">
  import { onMount } from 'svelte';

  let stats = $state({ racks: 0, devices: 0, totalPowerKw: 0.0, online: false, loading: true });

  onMount(async () => {
    try {
      const [racksRes, devicesRes, statsRes] = await Promise.all([
        fetch('/api/v1/racks').then(r => r.json()).catch(() => []),
        fetch('/api/v1/devices').then(r => r.json()).catch(() => []),
        fetch('/api/v1/dashboard/stats').then(r => r.json()).catch(() => ({ total_power_kw: 0.0 }))
      ]);
      stats.racks = Array.isArray(racksRes) ? racksRes.length : 0;
      stats.devices = Array.isArray(devicesRes) ? devicesRes.length : 0;
      stats.totalPowerKw = statsRes.total_power_kw || 0.0;
      stats.online = true;
    } catch {
      // offline
    } finally {
      stats.loading = false;
    }
  });
</script>

<svelte:head>
  <title>KAiTix — Elektriker & E-Plan Dokumentation</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Share+Tech+Mono&display=swap" rel="stylesheet">
</svelte:head>

<div class="bp-root">

  <!-- Blueprint grid overlay -->
  <div class="bp-grid" aria-hidden="true"></div>

  <!-- ─── NAV ─────────────────────────────────────────────── -->
  <nav class="bp-nav">
    <div class="bp-nav-logo">
      <span class="bp-nav-mark">⚡</span>
      <span class="bp-nav-name">KAiTix<span class="bp-nav-sub"> / Elektriker-Modus</span></span>
    </div>
    <div class="bp-nav-links">
      <a href="#eplan">E-Plan</a>
      <a href="#usv">USV</a>
      <a href="#batterie">Batterie</a>
      <a href="#normen">Normen</a>
    </div>
    <a href="/" class="bp-btn-ghost">→ App starten</a>
  </nav>

  <!-- ─── HERO ─────────────────────────────────────────────── -->
  <section class="bp-hero">
    <!-- Schriftfeld oben rechts wie DIN-Zeichnung -->
    <div class="bp-titleblock">
      <div class="bp-tb-row">
        <div class="bp-tb-cell label">Projekt</div>
        <div class="bp-tb-cell value mono">KAiTix RZ-Dokumentation</div>
      </div>
      <div class="bp-tb-row">
        <div class="bp-tb-cell label">Anlage</div>
        <div class="bp-tb-cell value mono">USV-Einspeisung + Batterieanlage</div>
      </div>
      <div class="bp-tb-row">
        <div class="bp-tb-cell label">Norm</div>
        <div class="bp-tb-cell value mono">EN 61082-1 / VDE 0100</div>
      </div>
      <div class="bp-tb-row">
        <div class="bp-tb-cell label">Status</div>
        <div class="bp-tb-cell value mono {stats.online ? 'ok' : 'err'}">{stats.online ? '● ONLINE' : '○ OFFLINE'}</div>
      </div>
    </div>

    <div class="bp-hero-text">
      <p class="bp-kicker">// TECHNISCHE DOKUMENTATION — RECHENZENTRUM</p>
      <h1 class="bp-h1">Stromlaufpläne &<br>USV-Schutzkonzept</h1>
      <p class="bp-lead">
        KAiTix erzeugt CAD-E-Pläne nach <strong>EN 61082-1</strong> für Unterverteilungen,
        USV-Anlagen und 2-strängige Batterieanlagen —
        direkt aus der Dokumentations-Datenbank, druckbar auf A3.
      </p>
      <div class="bp-hero-actions">
        <a href="/eplan" class="bp-btn-primary">E-Plan öffnen</a>
        <a href="/usv" class="bp-btn-ghost">USV-Kalkulation</a>
      </div>
    </div>

    <!-- Mini SVG E-Plan Preview -->
    <div class="bp-hero-preview">
      <div class="bp-preview-label">VORSCHAU — Blatt 1: USV-Einspeisung</div>
      <svg viewBox="0 0 320 180" class="bp-preview-svg">
        <!-- Busbars -->
        <line x1="15" y1="25" x2="305" y2="25" stroke="#93c5fd" stroke-width="1.5"/>
        <text x="5" y="28" font-size="6" fill="#93c5fd" font-family="monospace">L1</text>
        <line x1="15" y1="35" x2="305" y2="35" stroke="#e2e8f0" stroke-width="1.5"/>
        <text x="5" y="38" font-size="6" fill="#e2e8f0" font-family="monospace">L2</text>
        <line x1="15" y1="45" x2="305" y2="45" stroke="#94a3b8" stroke-width="1.5"/>
        <text x="5" y="48" font-size="6" fill="#94a3b8" font-family="monospace">L3</text>
        <line x1="15" y1="55" x2="305" y2="55" stroke="#60a5fa" stroke-width="1" stroke-dasharray="4,2"/>
        <text x="5" y="58" font-size="6" fill="#60a5fa" font-family="monospace">N</text>
        <line x1="15" y1="65" x2="305" y2="65" stroke="#4ade80" stroke-width="1" stroke-dasharray="6,3"/>
        <text x="5" y="68" font-size="6" fill="#4ade80" font-family="monospace">PE</text>

        <!-- UV-RZ-01 Box -->
        <rect x="55" y="72" width="100" height="55" fill="none" stroke="#cbd5e1" stroke-dasharray="6,3" stroke-width="0.8"/>
        <text x="58" y="70" font-size="5.5" font-weight="bold" fill="#e2e8f0" font-family="monospace">=A1 UV-RZ-01</text>
        <!-- NH-Sicherung -->
        <rect x="82" y="78" width="8" height="16" fill="none" stroke="#e2e8f0" stroke-width="0.8"/>
        <line x1="82" y1="78" x2="90" y2="94" stroke="#e2e8f0" stroke-width="0.8"/>
        <text x="65" y="89" font-size="5" fill="#94a3b8" font-family="monospace">-F1</text>
        <text x="93" y="89" font-size="5" fill="#94a3b8" font-family="monospace">NH 80A</text>

        <!-- USV Box -->
        <rect x="35" y="133" width="55" height="35" fill="#0f2040" stroke="#93c5fd" stroke-width="1"/>
        <text x="62" y="147" font-size="5.5" font-weight="bold" text-anchor="middle" fill="#e2e8f0" font-family="monospace">=T1</text>
        <text x="62" y="157" font-size="5" text-anchor="middle" fill="#93c5fd" font-family="monospace">USV 40kW</text>
        <text x="62" y="164" font-size="4.5" text-anchor="middle" fill="#64748b" font-family="monospace">GR|BAT|WR|BP</text>

        <!-- MBS -->
        <polygon points="145,133 165,145 145,157 125,145" fill="#0f2040" stroke="#94a3b8" stroke-width="1"/>
        <text x="145" y="148" font-size="5" font-weight="bold" text-anchor="middle" fill="#e2e8f0" font-family="monospace">MBS</text>

        <!-- Connections -->
        <line x1="90" y1="25" x2="90" y2="78" stroke="#93c5fd" stroke-width="0.8"/>
        <line x1="100" y1="35" x2="100" y2="78" stroke="#e2e8f0" stroke-width="0.8"/>
        <line x1="110" y1="45" x2="110" y2="78" stroke="#94a3b8" stroke-width="0.8"/>
        <line x1="62" y1="127" x2="62" y2="133" stroke="#93c5fd" stroke-width="0.8"/>
        <line x1="62" y1="94" x2="62" y2="100" stroke="#93c5fd" stroke-width="0.8"/>
        <path d="M 62 100 L 62 115 L 40 115 L 40 133" fill="none" stroke="#93c5fd" stroke-width="0.8"/>

        <!-- Weiter Blatt 2 -->
        <text x="195" y="155" font-size="5" fill="#64748b" font-style="italic" font-family="monospace">→ UV-USV-01 (Blatt 2)</text>

        <!-- Schriftfeld -->
        <rect x="200" y="155" width="110" height="22" fill="none" stroke="#334155" stroke-width="0.8"/>
        <line x1="200" y1="162" x2="310" y2="162" stroke="#334155" stroke-width="0.5"/>
        <text x="203" y="160" font-size="5" fill="#64748b" font-family="monospace">KAiTix | EN 61082-1</text>
        <text x="203" y="169" font-size="5" fill="#e2e8f0" font-family="monospace">USV-Einspeisung RZ</text>
        <text x="285" y="175" font-size="5" fill="#64748b" font-family="monospace">Bl. 1</text>
      </svg>
    </div>
  </section>

  <!-- ─── STATS ─────────────────────────────────────────────── -->
  <section class="bp-stats">
    <div class="bp-stat">
      <div class="bp-stat-val mono">{stats.loading ? '...' : stats.racks}</div>
      <div class="bp-stat-label">Racks dokumentiert</div>
    </div>
    <div class="bp-stat">
      <div class="bp-stat-val mono">{stats.loading ? '...' : stats.devices}</div>
      <div class="bp-stat-label">Geräte mit Stromwerten</div>
    </div>
    <div class="bp-stat">
      <div class="bp-stat-val mono">{stats.loading ? '...' : stats.totalPowerKw.toFixed(1)} kW</div>
      <div class="bp-stat-label">Installierte Last gesamt</div>
    </div>
    <div class="bp-stat">
      <div class="bp-stat-val mono">3</div>
      <div class="bp-stat-label">E-Plan Blätter (A3)</div>
    </div>
  </section>

  <!-- ─── E-PLAN MODULE ─────────────────────────────────────── -->
  <section id="eplan" class="bp-section">
    <div class="bp-section-header">
      <div class="bp-section-nr">01</div>
      <div>
        <h2 class="bp-h2">CAD E-Plan — Stromlaufpläne</h2>
        <p class="bp-sub">Allpolige Schaltpläne nach EN 61082-1, exportierbar als PDF (A3 Querformat)</p>
      </div>
    </div>
    <div class="bp-cards">
      <div class="bp-card">
        <div class="bp-card-nr">Blatt 1</div>
        <h3 class="bp-card-title">USV-Einspeisung RZ</h3>
        <p class="bp-card-body">L1/L2/L3/N/PE Sammelschienen · UV-RZ-01 mit NH-Sicherung F1 80A · Leistungsschalter Q1 63A · Klemmleiste X1 · USV-Anlage =T1 (GR/WR/Bypass/Batterie) · MBS-Schalter · Kabelkennzeichnung W1/W2 (NYY-J 5×25 mm²)</p>
        <div class="bp-card-tags"><span>DIN A3</span><span>NH 80A</span><span>NYY-J 5×25</span></div>
      </div>
      <div class="bp-card">
        <div class="bp-card-nr">Blatt 2</div>
        <h3 class="bp-card-title">UV-USV-01 Abgänge</h3>
        <p class="bp-card-body">USV-gepufferte Schiene · 7 Abgänge je LS Q3.1–Q3.7 (32A) · Klemmleisten X1–X7 · Kabel W3.1–W3.7 (5×16 mm²) · Kentix SmartPDU je Rack · N/PE Durchverdrahtung</p>
        <div class="bp-card-tags"><span>LS 32A</span><span>5×16 mm²</span><span>Kentix PDU</span></div>
      </div>
      <div class="bp-card bp-card-highlight">
        <div class="bp-card-nr">Blatt 3 <span class="bp-new">NEU</span></div>
        <h3 class="bp-card-title">Batterieanlage 2-strängig + BMS</h3>
        <p class="bp-card-body">DC-Sammelschiene ≈ 480V · Strang A &amp; B parallel · NH-Trennleiter je Strang (manuell, DC-seitig) · 40 Blöcke à 12V/65Ah je Strang · BMS-Sensoren (U/Ri/T°) je Block · BMS-Controller mit SNMP v3 → USV/NMS</p>
        <div class="bp-card-tags"><span>2-strängig</span><span>BMS SNMP v3</span><span>NH-Trenner DC</span></div>
      </div>
    </div>
  </section>

  <!-- ─── USV SCHUTZKONZEPT ──────────────────────────────────── -->
  <section id="usv" class="bp-section">
    <div class="bp-section-header">
      <div class="bp-section-nr">02</div>
      <div>
        <h2 class="bp-h2">USV-Schutzkonzept</h2>
        <p class="bp-sub">N+1 Modulredundanz + statischer Bypass + mechanisch verriegelter MBS</p>
      </div>
    </div>
    <div class="bp-features">
      <div class="bp-feat">
        <div class="bp-feat-icon">◈</div>
        <h3>N+1 Modulredundanz</h3>
        <p>USV-Leistungsmodule (WP2-R / 93PM) im N+1-Betrieb. Ausfall eines Moduls → verbleibende Module tragen die Last. Kaltstart-Simulation aus dokumentierten TDP-Werten.</p>
      </div>
      <div class="bp-feat">
        <div class="bp-feat-icon">⇄</div>
        <h3>MBS — Bypass-Verriegelung</h3>
        <p>Mechanisch verriegelter Bypass-Schalter (MBS 1-0-2). Umschaltung auf Direktnetz ohne Unterbrechung. Im Schaltplan als =S1 dokumentiert, Kabel -W2.</p>
      </div>
      <div class="bp-feat">
        <div class="bp-feat-icon">⚡</div>
        <h3>Phasen-Lastverteilung</h3>
        <p>Automatische L1/L2/L3-Lastberechnung aus TDP-Werten aller Geräte. Empfehlung bei &gt; 20% Phasenunbalance. PDU-Outlet-Ebene auflösbar.</p>
      </div>
      <div class="bp-feat">
        <div class="bp-feat-icon">⊞</div>
        <h3>Autonomiezeit-Berechnung</h3>
        <p>Peukert-Entladung, Batteriestrang-Konfiguration (1 oder 2 Stränge), Temperaturkorrektur. Ergibt realistische Autonomiezeit unter Vollast.</p>
      </div>
    </div>
  </section>

  <!-- ─── BATTERIE / BMS ─────────────────────────────────────── -->
  <section id="batterie" class="bp-section">
    <div class="bp-section-header">
      <div class="bp-section-nr">03</div>
      <div>
        <h2 class="bp-h2">2-strängige Batterieanlage</h2>
        <p class="bp-sub">Redundanz durch parallele Stränge — kein SPOF durch Einzelblock-Defekt</p>
      </div>
    </div>
    <div class="bp-twocoL">
      <div class="bp-explanation">
        <div class="bp-expl-item">
          <div class="bp-expl-nr">S1</div>
          <div>
            <strong>Szenario: Wartung</strong>
            <p>NH-Trenner Strang A aufschalten → Strang B versorgt weiter → 15 min Autonomie bleiben erhalten → Blocktausch im laufenden Betrieb möglich.</p>
          </div>
        </div>
        <div class="bp-expl-item">
          <div class="bp-expl-nr">S2</div>
          <div>
            <strong>Szenario: Zelltod</strong>
            <p>Einzelne Zelle in Strang A schließt intern kurz → NH-Sicherung löst aus → Strang B übernimmt automatisch und unterbrechungsfrei → USV meldet Alarm, RZ läuft weiter.</p>
          </div>
        </div>
        <div class="bp-expl-item bp-expl-danger">
          <div class="bp-expl-nr">S3</div>
          <div>
            <strong>Szenario: Einsträngig ohne Redundanz</strong>
            <p>Gleicher Zelltod → NH-Sicherung löst aus → kompletter Batteriepfad unterbrochen → nächster Netzausfall: USV fällt sofort durch → RZ-Ausfall.</p>
          </div>
        </div>
        <div class="bp-expl-note">
          Das BMS ist das Frühwarnsystem — die 2-strängige Ausführung ist die Redundanz wenn es trotzdem passiert. Beides zusammen ist das vollständige Sicherheitskonzept.
        </div>
      </div>
      <div class="bp-bms-table">
        <div class="bp-table-title">BMS — Überwachungsparameter je Block</div>
        <table>
          <thead>
            <tr><th>Parameter</th><th>Grenzwert</th><th>Bedeutung</th></tr>
          </thead>
          <tbody>
            <tr><td class="mono">U [V]</td><td>ΔU &gt; 0,5V</td><td>Blockspannung — Alterung / Sulfatierung</td></tr>
            <tr><td class="mono">Ri [mΩ]</td><td>&gt; 150% Ref.</td><td>Innenwiderstand — drohender Ausfall</td></tr>
            <tr><td class="mono">T° [°C]</td><td>&gt; 40°C</td><td>Übertemperatur — Thermal Runaway</td></tr>
            <tr class="mono-row"><td class="mono">SNMP v3</td><td>Trap → NMS</td><td>Alarm an USV-Monitoring weitergeleitet</td></tr>
          </tbody>
        </table>
        <div class="bp-note-box">
          <span class="mono">USV-Steuerung</span> sieht nur Gesamtspannung DC-Bus — kein Einzelblock-Monitoring. BMS ist zwingend für frühzeitige Fehlererkennung.
        </div>
      </div>
    </div>
  </section>

  <!-- ─── NORMEN ─────────────────────────────────────────────── -->
  <section id="normen" class="bp-section">
    <div class="bp-section-header">
      <div class="bp-section-nr">04</div>
      <div>
        <h2 class="bp-h2">Normen & Standards</h2>
        <p class="bp-sub">Dokumentation orientiert sich an geltenden VDE/EN-Normen</p>
      </div>
    </div>
    <div class="bp-norm-grid">
      <div class="bp-norm"><span class="mono">EN 61082-1</span><p>Erstellung von Unterlagen für die Elektrotechnik — Schaltungsunterlagen (Schaltpläne)</p></div>
      <div class="bp-norm"><span class="mono">VDE 0100</span><p>Errichten von Niederspannungsanlagen — Grundsätze für Schutzmaßnahmen</p></div>
      <div class="bp-norm"><span class="mono">EN 62040-3</span><p>USV-Systeme — Methode zur Angabe der Leistungsanforderungen und zur Prüfung</p></div>
      <div class="bp-norm"><span class="mono">EN IEC 62485-2</span><p>Sicherheitsanforderungen für Sekundärbatterien — stationäre Anlagen</p></div>
      <div class="bp-norm"><span class="mono">DIN 43880</span><p>Installationsgeräte — Abmessungen für Einbau in Installationsverteilern</p></div>
      <div class="bp-norm"><span class="mono">IEC 60364-5-54</span><p>Auswahl und Errichtung elektrischer Betriebsmittel — Erdungsanlagen und Schutzleiter</p></div>
    </div>
  </section>

  <!-- ─── FOOTER ─────────────────────────────────────────────── -->
  <footer class="bp-footer">
    <div class="bp-footer-left mono">KAiTix v0.1 — Rechenzentrum-Dokumentation · Elektriker-Modus</div>
    <div class="bp-footer-right">
      <a href="/landingpage">IT-Ansicht</a>
      <a href="/">App öffnen</a>
    </div>
  </footer>

</div>

<style>
  :global(body) {
    margin: 0;
    background: #06091a;
  }

  .bp-root {
    position: relative;
    min-height: 100vh;
    background: #06091a;
    color: #e2e8f0;
    font-family: 'IBM Plex Mono', 'Share Tech Mono', 'Courier New', monospace;
    overflow-x: hidden;
  }

  /* ── Blueprint grid background ── */
  .bp-grid {
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 0;
    background-image:
      linear-gradient(rgba(147,197,253,0.04) 1px, transparent 1px),
      linear-gradient(90deg, rgba(147,197,253,0.04) 1px, transparent 1px),
      linear-gradient(rgba(147,197,253,0.015) 1px, transparent 1px),
      linear-gradient(90deg, rgba(147,197,253,0.015) 1px, transparent 1px);
    background-size: 80px 80px, 80px 80px, 16px 16px, 16px 16px;
  }

  /* ── NAV ── */
  .bp-nav {
    position: relative;
    z-index: 10;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 2rem;
    height: 56px;
    border-bottom: 1px solid rgba(147,197,253,0.12);
    background: rgba(6,9,26,0.85);
    backdrop-filter: blur(8px);
  }

  .bp-nav-logo {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.95rem;
    font-weight: 600;
    color: #e2e8f0;
  }

  .bp-nav-mark { color: #facc15; font-size: 1.1rem; }
  .bp-nav-sub { color: #64748b; font-size: 0.75rem; }

  .bp-nav-links {
    display: flex;
    gap: 1.5rem;
  }

  .bp-nav-links a {
    color: #94a3b8;
    text-decoration: none;
    font-size: 0.8rem;
    letter-spacing: 0.05em;
    transition: color 0.15s;
  }
  .bp-nav-links a:hover { color: #93c5fd; }

  .bp-btn-ghost {
    font-size: 0.8rem;
    color: #93c5fd;
    text-decoration: none;
    border: 1px solid rgba(147,197,253,0.3);
    padding: 0.3rem 0.9rem;
    border-radius: 4px;
    transition: all 0.15s;
  }
  .bp-btn-ghost:hover {
    background: rgba(147,197,253,0.08);
    border-color: #93c5fd;
  }

  /* ── HERO ── */
  .bp-hero {
    position: relative;
    z-index: 1;
    display: grid;
    grid-template-columns: 1fr 380px;
    grid-template-rows: auto 1fr;
    gap: 2rem 3rem;
    padding: 3rem 2rem 2rem;
    max-width: 1200px;
    margin: 0 auto;
  }

  .bp-titleblock {
    grid-column: 2;
    grid-row: 1;
    border: 1px solid rgba(147,197,253,0.2);
    font-size: 0.72rem;
    align-self: start;
  }

  .bp-tb-row {
    display: flex;
    border-bottom: 1px solid rgba(147,197,253,0.12);
  }
  .bp-tb-row:last-child { border-bottom: none; }

  .bp-tb-cell {
    padding: 0.3rem 0.6rem;
  }
  .bp-tb-cell.label {
    width: 72px;
    color: #64748b;
    border-right: 1px solid rgba(147,197,253,0.12);
    font-size: 0.65rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }
  .bp-tb-cell.value { color: #cbd5e1; }
  .bp-tb-cell.value.ok { color: #4ade80; }
  .bp-tb-cell.value.err { color: #f87171; }
  .bp-tb-cell.mono { font-family: inherit; }

  .bp-hero-text {
    grid-column: 1;
    grid-row: 1 / 3;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding-top: 1rem;
  }

  .bp-kicker {
    font-size: 0.7rem;
    color: #4ade80;
    letter-spacing: 0.12em;
    margin: 0 0 1rem;
  }

  .bp-h1 {
    font-size: clamp(1.8rem, 3.5vw, 2.8rem);
    font-weight: 600;
    color: #f1f5f9;
    line-height: 1.2;
    margin: 0 0 1.2rem;
    letter-spacing: -0.02em;
  }

  .bp-lead {
    font-size: 0.875rem;
    color: #94a3b8;
    line-height: 1.7;
    max-width: 520px;
    margin: 0 0 2rem;
  }
  .bp-lead strong { color: #93c5fd; font-weight: 500; }

  .bp-hero-actions {
    display: flex;
    gap: 0.75rem;
  }

  .bp-btn-primary {
    background: #1d4ed8;
    color: #fff;
    text-decoration: none;
    padding: 0.6rem 1.4rem;
    border-radius: 4px;
    font-size: 0.85rem;
    font-weight: 500;
    transition: background 0.15s;
  }
  .bp-btn-primary:hover { background: #2563eb; }

  .bp-hero-preview {
    grid-column: 2;
    grid-row: 2;
    border: 1px solid rgba(147,197,253,0.15);
    background: rgba(15,32,64,0.6);
  }

  .bp-preview-label {
    font-size: 0.62rem;
    color: #475569;
    padding: 0.4rem 0.6rem;
    border-bottom: 1px solid rgba(147,197,253,0.1);
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }

  .bp-preview-svg {
    width: 100%;
    height: auto;
    display: block;
    padding: 0.5rem;
    box-sizing: border-box;
    background: #040812;
  }

  /* ── STATS ── */
  .bp-stats {
    position: relative;
    z-index: 1;
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0;
    border-top: 1px solid rgba(147,197,253,0.1);
    border-bottom: 1px solid rgba(147,197,253,0.1);
    max-width: 1200px;
    margin: 1.5rem auto;
  }

  .bp-stat {
    padding: 1.5rem 2rem;
    border-right: 1px solid rgba(147,197,253,0.1);
    text-align: center;
  }
  .bp-stat:last-child { border-right: none; }

  .bp-stat-val {
    font-size: 2rem;
    font-weight: 600;
    color: #93c5fd;
    margin-bottom: 0.25rem;
  }

  .bp-stat-label {
    font-size: 0.7rem;
    color: #64748b;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }

  /* ── SECTION ── */
  .bp-section {
    position: relative;
    z-index: 1;
    max-width: 1200px;
    margin: 0 auto;
    padding: 2.5rem 2rem;
    border-bottom: 1px solid rgba(147,197,253,0.08);
  }

  .bp-section-header {
    display: flex;
    align-items: flex-start;
    gap: 1.5rem;
    margin-bottom: 2rem;
  }

  .bp-section-nr {
    font-size: 2.5rem;
    font-weight: 600;
    color: rgba(147,197,253,0.12);
    line-height: 1;
    min-width: 3rem;
    margin-top: -0.2rem;
  }

  .bp-h2 {
    font-size: 1.3rem;
    font-weight: 600;
    color: #e2e8f0;
    margin: 0 0 0.3rem;
    letter-spacing: -0.01em;
  }

  .bp-sub {
    font-size: 0.78rem;
    color: #64748b;
    margin: 0;
  }

  /* ── E-PLAN CARDS ── */
  .bp-cards {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1px;
    background: rgba(147,197,253,0.1);
    border: 1px solid rgba(147,197,253,0.1);
  }

  .bp-card {
    background: #06091a;
    padding: 1.5rem;
  }

  .bp-card-highlight {
    background: rgba(15,32,64,0.8);
    border-left: 2px solid #4ade80;
  }

  .bp-card-nr {
    font-size: 0.68rem;
    color: #4ade80;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 0.6rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .bp-new {
    background: #14532d;
    color: #4ade80;
    font-size: 0.6rem;
    padding: 0.1rem 0.4rem;
    border-radius: 2px;
  }

  .bp-card-title {
    font-size: 0.95rem;
    font-weight: 600;
    color: #e2e8f0;
    margin: 0 0 0.75rem;
  }

  .bp-card-body {
    font-size: 0.75rem;
    color: #64748b;
    line-height: 1.6;
    margin: 0 0 1rem;
  }

  .bp-card-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }

  .bp-card-tags span {
    font-size: 0.65rem;
    color: #475569;
    border: 1px solid rgba(147,197,253,0.1);
    padding: 0.15rem 0.5rem;
    border-radius: 2px;
  }

  /* ── FEATURES ── */
  .bp-features {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1.5rem;
  }

  .bp-feat {
    border-left: 1px solid rgba(147,197,253,0.15);
    padding-left: 1rem;
  }

  .bp-feat-icon {
    font-size: 1.3rem;
    color: #93c5fd;
    margin-bottom: 0.5rem;
  }

  .bp-feat h3 {
    font-size: 0.85rem;
    font-weight: 600;
    color: #e2e8f0;
    margin: 0 0 0.5rem;
  }

  .bp-feat p {
    font-size: 0.75rem;
    color: #64748b;
    line-height: 1.6;
    margin: 0;
  }

  /* ── BATTERIE / ZWEISP. ── */
  .bp-twocoL {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 2rem;
  }

  .bp-explanation {
    display: flex;
    flex-direction: column;
    gap: 1.2rem;
  }

  .bp-expl-item {
    display: flex;
    gap: 1rem;
    align-items: flex-start;
  }

  .bp-expl-nr {
    min-width: 2rem;
    height: 2rem;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid rgba(147,197,253,0.2);
    font-size: 0.7rem;
    color: #93c5fd;
    flex-shrink: 0;
  }

  .bp-expl-danger .bp-expl-nr {
    border-color: rgba(248,113,113,0.3);
    color: #f87171;
  }

  .bp-expl-item strong {
    display: block;
    font-size: 0.85rem;
    color: #e2e8f0;
    margin-bottom: 0.3rem;
  }

  .bp-expl-item p {
    font-size: 0.75rem;
    color: #64748b;
    line-height: 1.6;
    margin: 0;
  }

  .bp-expl-danger strong { color: #f87171; }

  .bp-expl-note {
    font-size: 0.75rem;
    color: #4ade80;
    border: 1px solid rgba(74,222,128,0.15);
    background: rgba(74,222,128,0.04);
    padding: 0.75rem 1rem;
    line-height: 1.6;
  }

  /* ── BMS TABLE ── */
  .bp-bms-table {
    border: 1px solid rgba(147,197,253,0.12);
  }

  .bp-table-title {
    font-size: 0.72rem;
    color: #64748b;
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid rgba(147,197,253,0.12);
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.75rem;
  }

  th {
    text-align: left;
    padding: 0.5rem 0.75rem;
    color: #475569;
    font-size: 0.65rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    border-bottom: 1px solid rgba(147,197,253,0.12);
    font-weight: 400;
  }

  td {
    padding: 0.5rem 0.75rem;
    color: #94a3b8;
    border-bottom: 1px solid rgba(147,197,253,0.06);
  }

  td.mono { color: #93c5fd; }

  tr:last-child td { border-bottom: none; }

  .bp-note-box {
    font-size: 0.72rem;
    color: #64748b;
    padding: 0.6rem 0.75rem;
    border-top: 1px solid rgba(147,197,253,0.12);
    background: rgba(0,0,0,0.2);
    line-height: 1.6;
  }

  /* ── NORMEN ── */
  .bp-norm-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1px;
    background: rgba(147,197,253,0.08);
    border: 1px solid rgba(147,197,253,0.08);
  }

  .bp-norm {
    background: #06091a;
    padding: 1.25rem 1.5rem;
  }

  .bp-norm span.mono {
    display: block;
    font-size: 0.8rem;
    color: #93c5fd;
    margin-bottom: 0.4rem;
  }

  .bp-norm p {
    font-size: 0.72rem;
    color: #475569;
    line-height: 1.6;
    margin: 0;
  }

  /* ── FOOTER ── */
  .bp-footer {
    position: relative;
    z-index: 1;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 2rem;
    border-top: 1px solid rgba(147,197,253,0.08);
    max-width: 1200px;
    margin: 0 auto;
  }

  .bp-footer-left {
    font-size: 0.7rem;
    color: #334155;
  }

  .bp-footer-right {
    display: flex;
    gap: 1.5rem;
  }

  .bp-footer-right a {
    font-size: 0.7rem;
    color: #475569;
    text-decoration: none;
  }
  .bp-footer-right a:hover { color: #93c5fd; }

  .mono { font-family: inherit; }

  @media (max-width: 900px) {
    .bp-hero { grid-template-columns: 1fr; }
    .bp-titleblock { grid-column: 1; grid-row: auto; }
    .bp-hero-preview { grid-column: 1; grid-row: auto; }
    .bp-stats { grid-template-columns: repeat(2, 1fr); }
    .bp-cards { grid-template-columns: 1fr; }
    .bp-features { grid-template-columns: repeat(2, 1fr); }
    .bp-twocoL { grid-template-columns: 1fr; }
    .bp-norm-grid { grid-template-columns: repeat(2, 1fr); }
  }
</style>

<script lang="ts">
  import { onMount } from 'svelte';
  import {
    Server,
    Layers,
    Zap,
    Cable,
    BookOpen,
    Activity,
    ArrowRight,
    Network,
    Thermometer
  } from '@lucide/svelte';

  let stats = $state({
    racks: 0,
    devices: 0,
    totalPowerKw: 0.0,
    online: false,
    loading: true
  });

  onMount(async () => {
    try {
      const [racksRes, devicesRes, statsRes, healthRes] = await Promise.all([
        fetch('/api/v1/racks').then(r => r.json()),
        fetch('/api/v1/devices').then(r => r.json()),
        fetch('/api/v1/dashboard/stats').then(r => r.json()),
        fetch('/api/v1/health').then(r => r.json()).catch(() => ({ status: 'offline' }))
      ]);

      stats.racks = racksRes.length;
      stats.devices = devicesRes.length;
      stats.totalPowerKw = statsRes.total_power_kw || 0.0;
      stats.online = healthRes.status === 'healthy';
    } catch (err) {
      console.error('Error fetching landing page stats:', err);
    } finally {
      stats.loading = false;
    }
  });
</script>

<svelte:head>
  <title>KAiTix — Serverraum-Dokumentation</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
</svelte:head>

<div class="landing-page-container">
  <section class="hero">
    <div class="hero-bg"></div>
    <div class="hero-overlay"></div>
    <div class="hero-scanline"></div>
    
    <div class="hero-content">
      <div class="hero-left">
        <div class="hero-eyebrow">Intranet · Single-User · Dokumentation</div>
        
        <h1>Serverraum-Infrastruktur.<br><em>Dokumentiert.</em></h1>
        
        <p class="hero-sub">
          KAiTix bündelt Rack-Verwaltung, Kabelliste, IPAM, USV-Berechnung und Runbook-Orchestrierung in einer einzigen, schlanken Oberfläche — keine Automatisierung, nur saubere Dokumentation.
        </p>
        
        <div class="hero-actions">
          <a href="/dashboard" class="btn-hero-primary">
            <span>Zur App</span>
            <ArrowRight class="w-4 h-4" />
          </a>
          <a href="/racks" class="btn-hero-ghost">
            <Layers class="w-4 h-4" />
            <span>Rack-Übersicht</span>
          </a>
          <a href="/runbook-orchestrator" class="btn-hero-ghost">
            <BookOpen class="w-4 h-4" />
            <span>Runbooks</span>
          </a>
        </div>
      </div>
      
      <div class="hero-right">
        <div class="hero-stats">
          <div class="stat-card">
            <div class="stat-card-icon">
              <Layers class="w-5 h-5 text-teal" />
            </div>
            <div>
              <div class="stat-card-label">Racks & Standorte</div>
              <div class="stat-card-val">
                {#if stats.loading}
                  <span class="opacity-50">Lade...</span>
                {:else}
                  {stats.racks} Rack{stats.racks !== 1 ? 's' : ''}
                {/if}
              </div>
            </div>
          </div>
          
          <div class="stat-card">
            <div class="stat-card-icon">
              <Server class="w-5 h-5 text-teal" />
            </div>
            <div>
              <div class="stat-card-label">Aktive Geräte</div>
              <div class="stat-card-val">
                {#if stats.loading}
                  <span class="opacity-50">Lade...</span>
                {:else}
                  {stats.devices} Gerät{stats.devices !== 1 ? 'e' : ''}
                {/if}
              </div>
            </div>
          </div>
          
          <div class="stat-card">
            <div class="stat-card-icon">
              <Zap class="w-5 h-5 text-teal" />
            </div>
            <div>
              <div class="stat-card-label">Gesamtleistung (TDP)</div>
              <div class="stat-card-val font-mono">
                {#if stats.loading}
                  <span class="opacity-50 text-xs">Lade...</span>
                {:else}
                  {stats.totalPowerKw.toFixed(2)} kW
                {/if}
              </div>
            </div>
          </div>
          
          <div class="stat-card">
            <div class="stat-card-icon">
              <Activity class="w-5 h-5 text-teal" />
            </div>
            <div>
              <div class="stat-card-label">Health-Status</div>
              <div class="stat-card-val flex items-center gap-2">
                {#if stats.loading}
                  <span class="opacity-50">Lade...</span>
                {:else}
                  <span class="w-2.5 h-2.5 rounded-full {stats.online ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}"></span>
                  <span class={stats.online ? 'text-emerald-400' : 'text-red-400'}>
                    {stats.online ? 'System online' : 'System offline'}
                  </span>
                {/if}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section class="section" id="module">
    <div class="section-label">// module</div>
    <h2>Alles an einem Ort</h2>
    <p class="section-sub">Sechs Module, eine Oberfläche — kein Overhead, kein Monitoring, keine Automatisierung.</p>

    <div class="feat-grid">
      <div class="feat-cell">
        <div class="feat-cell-icon">
          <Layers class="w-5 h-5 text-teal" />
        </div>
        <h3>Rack-Verwaltung</h3>
        <p>Standorte, Rackreihen und Racks mit dreistufigem Filter. Topology-View mit Gerätebelegung pro U-Position.</p>
        <span class="feat-cell-tag">racks · topology</span>
      </div>
      
      <div class="feat-cell">
        <div class="feat-cell-icon">
          <Network class="w-5 h-5 text-teal" />
        </div>
        <h3>IPAM</h3>
        <p>VLAN- und Subnet-Verwaltung mit IP-Kollisionserkennung und Netzplan-Ansicht. Seed-Daten inklusive.</p>
        <span class="feat-cell-tag">vlans · subnets · netzplan</span>
      </div>
      
      <div class="feat-cell">
        <div class="feat-cell-icon">
          <Cable class="w-5 h-5 text-teal" />
        </div>
        <h3>Kabelliste</h3>
        <p>Vollständige Kabeldokumentation mit automatischer Nummerierung, Port-Zuordnung und Verbindungsmatrix.</p>
        <span class="feat-cell-tag">cables · ports · interfaces</span>
      </div>
      
      <div class="feat-cell">
        <div class="feat-cell-icon">
          <Zap class="w-5 h-5 text-teal" />
        </div>
        <h3>USV &amp; Phasen</h3>
        <p>N+1-Berechnung, Kaltstart-Check mit Einschaltstromfaktor. Phasen-Imbalance L1/L2/L3 Dokumentation.</p>
        <span class="feat-cell-tag">usv · n+1 · phasen</span>
      </div>
      
      <div class="feat-cell">
        <div class="feat-cell-icon">
          <BookOpen class="w-5 h-5 text-teal" />
        </div>
        <h3>Runbook-Orchestrator</h3>
        <p>Techniker-Checklisten mit Drag &amp; Drop, VM-Abhängigkeitsgraph, Ausführungsprotokoll und 20 Tests.</p>
        <span class="feat-cell-tag">runbooks · vm-graph · protokoll</span>
      </div>
      
      <div class="feat-cell">
        <div class="feat-cell-icon">
          <Thermometer class="w-5 h-5 text-teal" />
        </div>
        <h3>Kentix &amp; PDUs</h3>
        <p>Gerätedokumentation für Umgebungssensoren und PDUs — welcher Socket, welches Rack, welche Phase.</p>
        <span class="feat-cell-tag">kentix · pdu · sockets</span>
      </div>
    </div>

    <div class="stack-bar">
      <span class="stack-item">FastAPI</span>
      <span class="stack-item">async SQLAlchemy</span>
      <span class="stack-item">aiomysql</span>
      <span class="stack-item">MySQL 8</span>
      <span class="stack-item">Alembic</span>
      <span class="stack-item">Svelte 5</span>
      <span class="stack-item">Podman</span>
      <span class="stack-item">Python 3.11+</span>
    </div>
  </section>
</div>

<style>
  .landing-page-container {
    --teal: #1D9E75;
    --teal-light: #5DCAA5;
    --teal-dim: rgba(29, 158, 117, 0.18);
    --teal-border: rgba(29, 158, 117, 0.4);
    --bg: #0D0F0E;
    --bg2: #131615;
    --bg3: #181C1A;
    --border: rgba(255, 255, 255, 0.07);
    --border2: rgba(255, 255, 255, 0.13);
    --text: #E8EDE9;
    --text2: #8A9A8D;
    --text3: #556059;
    --mono: 'IBM Plex Mono', monospace;
    --sans: 'DM Sans', sans-serif;
    --radius: 10px;
    --radius-lg: 16px;

    font-family: var(--sans);
    color: var(--text);
    position: relative;
    z-index: 1;
    max-width: 1200px;
    margin: 0 auto;
    padding-bottom: 4rem;
  }

  .landing-page-container::before {
    content: '';
    position: absolute;
    inset: -32px;
    background-image:
      linear-gradient(rgba(29, 158, 117, 0.04) 1px, transparent 1px),
      linear-gradient(90deg, rgba(29, 158, 117, 0.04) 1px, transparent 1px);
    background-size: 48px 48px;
    pointer-events: none;
    z-index: -1;
  }

  /* HERO */
  .hero {
    position: relative;
    min-height: 480px;
    border-radius: var(--radius-lg);
    overflow: hidden;
    border: 1px solid var(--border);
    padding: 3rem;
    background: var(--bg2);
    display: flex;
    align-items: center;
    margin-bottom: 3rem;
  }

  .hero-bg {
    position: absolute;
    inset: 0;
    background-size: cover;
    background-position: center 30%;
    background-image: url('/assets/hero-serverraum.jpg');
    filter: brightness(0.22) contrast(1.1) saturate(1.15);
    z-index: 1;
  }

  .hero-overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(
      105deg,
      rgba(13, 15, 14, 0.96) 0%,
      rgba(13, 15, 14, 0.3) 100%
    );
    z-index: 2;
  }

  .hero-scanline {
    position: absolute;
    inset: 0;
    background: repeating-linear-gradient(
      0deg,
      transparent,
      transparent 3px,
      rgba(0, 0, 0, 0.08) 3px,
      rgba(0, 0, 0, 0.08) 4px
    );
    pointer-events: none;
    z-index: 3;
  }

  .hero-content {
    position: relative;
    z-index: 4;
    width: 100%;
    display: grid;
    grid-template-columns: 1.2fr 0.8fr;
    gap: 3rem;
    align-items: center;
  }

  .hero-eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-family: var(--mono);
    font-size: 11px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--teal-light);
    background: var(--teal-dim);
    border: 1px solid var(--teal-border);
    padding: 5px 14px;
    border-radius: 20px;
    margin-bottom: 1.5rem;
  }

  .hero-eyebrow::before {
    content: '';
    width: 6px;
    height: 6px;
    background: var(--teal-light);
    border-radius: 50%;
    animation: pulse 2s ease infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(0.7); }
  }

  .hero-left h1 {
    font-size: clamp(32px, 4.5vw, 54px);
    font-weight: 300;
    line-height: 1.1;
    color: var(--text);
    margin-bottom: 1.5rem;
  }

  .hero-left h1 em {
    font-style: normal;
    color: var(--teal-light);
    font-weight: 400;
  }

  .hero-sub {
    font-size: 15px;
    font-weight: 300;
    color: var(--text2);
    line-height: 1.6;
    margin-bottom: 2rem;
    max-width: 560px;
  }

  .hero-actions {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }

  .btn-hero-primary {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    font-weight: 500;
    color: #fff;
    background: var(--teal);
    padding: 10px 20px;
    border-radius: var(--radius);
    text-decoration: none;
    transition: background 0.15s, transform 0.1s;
    border: none;
    cursor: pointer;
  }

  .btn-hero-primary:hover {
    background: #0F6E56;
    transform: translateY(-1px);
  }

  .btn-hero-ghost {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    font-weight: 400;
    color: var(--text2);
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--border2);
    padding: 10px 20px;
    border-radius: var(--radius);
    text-decoration: none;
    transition: color 0.15s, background 0.15s, transform 0.1s;
  }

  .btn-hero-ghost:hover {
    color: var(--text);
    background: rgba(255, 255, 255, 0.09);
    transform: translateY(-1px);
  }

  /* STAT CARDS */
  .hero-stats {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .stat-card {
    display: flex;
    align-items: center;
    gap: 12px;
    background: rgba(13, 15, 14, 0.75);
    backdrop-filter: blur(8px);
    border: 1px solid var(--border2);
    border-radius: var(--radius);
    padding: 12px 16px;
    min-width: 220px;
  }

  .stat-card-icon {
    width: 32px;
    height: 32px;
    background: var(--teal-dim);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .stat-card-icon :global(svg) {
    stroke: var(--teal-light);
    stroke-width: 1.5;
  }

  .stat-card-label {
    font-size: 10px;
    color: var(--text3);
    font-family: var(--mono);
    text-transform: uppercase;
    letter-spacing: 0.07em;
  }

  .stat-card-val {
    font-size: 13px;
    font-weight: 500;
    color: var(--text);
    margin-top: 2px;
  }

  /* SECTIONS */
  .section {
    padding: 2rem 0;
  }

  .section-label {
    font-family: var(--mono);
    font-size: 11px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--teal);
    margin-bottom: 0.75rem;
  }

  .section h2 {
    font-size: 24px;
    font-weight: 400;
    color: var(--text);
    margin-bottom: 0.5rem;
  }

  .section-sub {
    font-size: 14px;
    color: var(--text2);
    margin-bottom: 2rem;
  }

  /* FEATURE GRID */
  .feat-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1px;
    background: var(--border);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    overflow: hidden;
    margin-bottom: 2.5rem;
  }

  .feat-cell {
    background: var(--bg2);
    padding: 2rem;
    transition: background 0.15s;
  }

  .feat-cell:hover {
    background: var(--bg3);
  }

  .feat-cell-icon {
    width: 36px;
    height: 36px;
    background: var(--teal-dim);
    border: 1px solid var(--teal-border);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 1rem;
  }

  .feat-cell-icon :global(svg) {
    stroke: var(--teal-light);
    stroke-width: 1.5;
  }

  .feat-cell h3 {
    font-size: 14px;
    font-weight: 500;
    color: var(--text);
    margin-bottom: 6px;
  }

  .feat-cell p {
    font-size: 12.5px;
    color: var(--text2);
    line-height: 1.6;
  }

  .feat-cell-tag {
    display: inline-block;
    margin-top: 12px;
    font-family: var(--mono);
    font-size: 9px;
    color: var(--teal-light);
    background: var(--teal-dim);
    padding: 3px 8px;
    border-radius: 4px;
  }

  /* STACK BAR */
  .stack-bar {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    padding-top: 2rem;
    border-top: 1px solid var(--border);
  }

  .stack-item {
    font-family: var(--mono);
    font-size: 11px;
    color: var(--text2);
    padding: 4px 10px;
    border: 1px solid var(--border);
    border-radius: 5px;
    background: var(--bg2);
  }

  /* RESPONSIVE */
  @media (max-width: 960px) {
    .hero-content {
      grid-template-columns: 1fr;
      gap: 2rem;
    }
    .feat-grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  @media (max-width: 640px) {
    .hero {
      padding: 2rem;
    }
    .feat-grid {
      grid-template-columns: 1fr;
    }
  }
</style>

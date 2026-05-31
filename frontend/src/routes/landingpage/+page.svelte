<script lang="ts">
  import { onMount } from 'svelte';
  import { appState } from '$lib/state.svelte';
  import { Sun, Moon } from '@lucide/svelte';

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
        fetch('/api/v1/racks').then(r => r.json()).catch(() => []),
        fetch('/api/v1/devices').then(r => r.json()).catch(() => []),
        fetch('/api/v1/dashboard/stats').then(r => r.json()).catch(() => ({ total_power_kw: 0.0 })),
        fetch('/api/v1/health').then(r => r.json()).catch(() => ({ status: 'offline' }))
      ]);

      stats.racks = Array.isArray(racksRes) ? racksRes.length : 0;
      stats.devices = Array.isArray(devicesRes) ? devicesRes.length : 0;
      stats.totalPowerKw = statsRes.total_power_kw || 0.0;
      stats.online = healthRes.status === 'healthy';
    } catch (err) {
      console.error('Error fetching landing page stats:', err);
    } finally {
      stats.loading = false;
    }
  });

  let isLightboxOpen = $state(false);

  function handleKeyDown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      isLightboxOpen = false;
    }
  }
</script>

<svelte:window onkeydown={handleKeyDown} />

<svelte:head>
  <title>KAiTix — Serverraum-Dokumentation</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
</svelte:head>

<div class="landing-page-root">
  <nav>
    <a href="#" class="nav-logo">
      <div class="nav-logo-mark">K</div>
      KAiTix
    </a>
    <div class="nav-links">
      <a href="#module">Module</a>
      <a href="#prinzipien">Prinzipien</a>
      <a href="#stack">Stack</a>
    </div>
    <div style="display: flex; align-items: center; gap: 1rem;">
      <button class="theme-toggle-btn" onclick={() => appState.toggleTheme()} title="Theme wechseln">
        {#if appState.theme === 'dark'}
          <Sun size={18} />
        {:else}
          <Moon size={18} />
        {/if}
      </button>
      <a href="/" class="nav-cta">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
        App öffnen
      </a>
    </div>
  </nav>

  <section class="hero">
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="hero-bg" onclick={() => isLightboxOpen = true}></div>
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="hero-overlay" onclick={() => isLightboxOpen = true}></div>
    <div class="hero-scanline"></div>
    <button class="hero-camera-btn" onclick={() => isLightboxOpen = true} aria-label="Bild vergrößern">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
        <circle cx="12" cy="13" r="4"/>
      </svg>
    </button>
    <div class="hero-content">
      <div class="hero-left">
        <div class="hero-eyebrow">Intranet · Single-User · Dokumentation & Simulation</div>
        <h1>Serverraum-Infrastruktur.<br><em>Dokumentiert & Simuliert.</em></h1>
        <p class="hero-sub">KAiTix bündelt Rack-Verwaltung, Kabelliste, IPAM, präzise USV-Berechnungen und Runbook-Orchestrierung in einer einzigen, schlanken Oberfläche. Plane Ausfälle im Voraus und dokumentiere deine Infrastruktur — ganz ohne Live-Monitoring von RZ-Daten.</p>
        <div class="hero-actions">
          <a href="/" class="btn-hero-primary">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
            Zur App
          </a>
          <a href="/racks" class="btn-hero-ghost">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="4" rx="1"/><rect x="2" y="10" width="20" height="4" rx="1"/><rect x="2" y="17" width="20" height="4" rx="1"/></svg>
            Rack-Übersicht
          </a>
          <a href="/runbook-orchestrator" class="btn-hero-ghost">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2"/><path d="M9 12l2 2 4-4"/></svg>
            Runbooks
          </a>
        </div>
      </div>
      
      <div class="hero-right">
        <div class="hero-stats">
          <div class="stat-card">
            <div class="stat-card-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="4" rx="1"/><rect x="2" y="10" width="20" height="4" rx="1"/><rect x="2" y="17" width="20" height="4" rx="1"/></svg>
            </div>
            <div>
              <div class="stat-card-label">Racks &amp; Standorte</div>
              <div class="stat-card-val">
                {#if stats.loading}
                  <span class="opacity-55">Lade...</span>
                {:else}
                  {stats.racks} Racks
                {/if}
              </div>
            </div>
          </div>
          
          <div class="stat-card">
            <div class="stat-card-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>
            </div>
            <div>
              <div class="stat-card-label">Aktive Geräte</div>
              <div class="stat-card-val">
                {#if stats.loading}
                  <span class="opacity-55">Lade...</span>
                {:else}
                  {stats.devices} Geräte
                {/if}
              </div>
            </div>
          </div>
          
          <div class="stat-card">
            <div class="stat-card-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
            </div>
            <div>
              <div class="stat-card-label">Gesamtleistung (TDP)</div>
              <div class="stat-card-val font-mono">
                {#if stats.loading}
                  <span class="opacity-55">Lade...</span>
                {:else}
                  {stats.totalPowerKw.toFixed(2)} kW
                {/if}
              </div>
            </div>
          </div>
          
          <div class="stat-card">
            <div class="stat-card-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 00-1-1.73L13 2.27a2 2 0 00-2 0L4 6.27A2 2 0 003 8v8a2 2 0 001 1.73L11 21.73a2 2 0 002 0l7-4.27A2 2 0 0021 16z"/></svg>
            </div>
            <div>
              <div class="stat-card-label">System-Health</div>
              <div class="stat-card-val flex items-center gap-2">
                {#if stats.loading}
                  <span class="opacity-55">Lade...</span>
                {:else}
                  <span class="w-2.5 h-2.5 rounded-full {stats.online ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}"></span>
                  <span class={stats.online ? 'text-emerald-400' : 'text-red-400'}>
                    {stats.online ? 'ONLINE' : 'OFFLINE'}
                  </span>
                {/if}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <div id="module"></div>
  <section class="section">
    <div class="section-label">// module</div>
    <h2>Alles an einem Ort</h2>
    <p class="section-sub">Sechs Module, eine Oberfläche — Runbook-Orchestrierung, USV-Berechnung und strukturierte Infrastruktur-Dokumentation — kein Live-Monitoring von RZ-Daten.</p>

    <div class="feat-grid">
      <div class="feat-cell">
        <div class="feat-cell-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="4" rx="1"/><rect x="2" y="10" width="20" height="4" rx="1"/><rect x="2" y="17" width="20" height="4" rx="1"/></svg>
        </div>
        <h3>Rack-Verwaltung</h3>
        <p>Standorte, Rackreihen und Racks mit dreistufigem Filter. Topology-View mit Gerätebelegung pro U-Position.</p>
        <span class="feat-cell-tag">racks · topology</span>
      </div>
      
      <div class="feat-cell">
        <div class="feat-cell-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14"/><circle cx="5" cy="12" r="2"/><circle cx="19" cy="12" r="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v5"/></svg>
        </div>
        <h3>IPAM</h3>
        <p>VLAN- und Subnet-Verwaltung mit IP-Kollisionserkennung und Netzplan-Ansicht. Seed-Daten inklusive.</p>
        <span class="feat-cell-tag">vlans · subnets · netzplan</span>
      </div>
      
      <div class="feat-cell">
        <div class="feat-cell-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/></svg>
        </div>
        <h3>Kabelliste</h3>
        <p>Vollständige Kabeldokumentation mit automatischer Nummerierung, Port-Zuordnung und Verbindungsmatrix.</p>
        <span class="feat-cell-tag">cables · ports · interfaces</span>
      </div>
      
      <div class="feat-cell">
        <div class="feat-cell-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
        </div>
        <h3>USV &amp; Phasen</h3>
        <p>N+1-Berechnung, Kaltstart-Check mit Einschaltstromfaktor. Phasen-Imbalance L1/L2/L3 Dokumentation.</p>
        <span class="feat-cell-tag">usv · n+1 · phasen</span>
      </div>
      
      <div class="feat-cell">
        <div class="feat-cell-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2"/><path d="M9 12l2 2 4-4"/></svg>
        </div>
        <h3>Runbook-Orchestrator</h3>
        <p>Techniker-Checklisten mit Drag &amp; Drop, VM-Abhängigkeitsgraph, Ausführungsprotokoll und 20 Tests.</p>
        <span class="feat-cell-tag">runbooks · vm-graph · protokoll</span>
      </div>
      
      <div class="feat-cell">
        <div class="feat-cell-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 14.76V3.5a2.5 2.5 0 00-5 0v11.26A4.5 4.5 0 1014 14.76z"/></svg>
        </div>
        <h3>Kentix &amp; PDUs</h3>
        <p>Gerätedokumentation für Umgebungssensoren und PDUs — welcher Socket, welches Rack, welche Phase.</p>
        <span class="feat-cell-tag">kentix · pdu · sockets</span>
      </div>
    </div>

    <div id="stack"></div>
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

  <div id="prinzipien"></div>
  <section class="section" style="padding-top: 0;">
    <div class="section-label">// design-prinzipien</div>
    <h2>Dokumentation & Simulation.</h2>
    <p class="section-sub">KAiTix hat einen klaren Scope — und hält ihn konsequent ein.</p>

    <div class="principles">
      <div class="principle-card">
        <h4>Dokumentation & Simulation</h4>
        <p>Infrastruktur wird präzise dokumentiert und Stromausfälle sowie Runbooks werden simuliert. Keine Steuerung, keine automatisierten Eingriffe in die Produktivsysteme.</p>
      </div>
      <div class="principle-card">
        <h4>Kein Echtzeit-Monitoring</h4>
        <p>KAiTix zeigt keine Live-Daten. Runbooks sind Techniker-Checklisten, keine Automation-Trigger.</p>
      </div>
      <div class="principle-card">
        <h4>Single-User Scope</h4>
        <p>Intranet-Only, ein Benutzer. Das vereinfacht den Risikokalkül — blocking I/O ist kein Problem.</p>
      </div>
      <div class="principle-card">
        <h4>Explizite Verifikation</h4>
        <p>Nach jeder Änderung: Verifikation. Bestehendes bleibt erhalten. Claude Code committed nach jedem Fix.</p>
      </div>
    </div>
  </section>

  <footer>
    <p>KAiTix — Serverraum-Dokumentation &amp; Runbook-Orchestrierung</p>
    <a href="/">localhost:5175 →</a>
  </footer>
</div>

{#if isLightboxOpen}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="lightbox" onclick={() => isLightboxOpen = false}>
    <img src="/assets/hero-serverraum.jpg" alt="Serverraum Großansicht" class="lightbox-img" onclick={(e) => e.stopPropagation()} />
    <button class="lightbox-close" onclick={() => isLightboxOpen = false}>&times;</button>
  </div>
{/if}

<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  .landing-page-root {
    --teal: #1D9E75;
    --teal-light: #5DCAA5;
    --teal-dim: rgba(29,158,117,0.18);
    --teal-border: rgba(29,158,117,0.4);
    --bg: #0D0F0E;
    --bg2: #131615;
    --bg3: #181C1A;
    --border: rgba(255,255,255,0.07);
    --border2: rgba(255,255,255,0.13);
    --text: #E8EDE9;
    --text2: #8A9A8D;
    --text3: #556059;
    --mono: 'IBM Plex Mono', monospace;
    --sans: 'DM Sans', sans-serif;
    --radius: 10px;
    --radius-lg: 16px;

    font-family: var(--sans);
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    overflow-x: hidden;
    position: relative;
    z-index: 1;
  }

  .landing-page-root::before {
    content: '';
    position: absolute; inset: 0;
    background-image:
      linear-gradient(rgba(29,158,117,0.04) 1px, transparent 1px),
      linear-gradient(90deg, rgba(29,158,117,0.04) 1px, transparent 1px);
    background-size: 48px 48px;
    pointer-events: none;
    z-index: -1;
  }

  /* Light Theme Overrides */
  :global(html.light) .landing-page-root {
    --bg: #F4F7F5;
    --bg2: #FFFFFF;
    --bg3: #EAEFEA;
    --border: rgba(0,0,0,0.08);
    --border2: rgba(0,0,0,0.15);
    --text: #131615;
    --text2: #556059;
    --text3: #8A9A8D;
    --teal: #14805E;
    --teal-light: #1D9E75;
    --teal-dim: rgba(29,158,117,0.12);
    --teal-border: rgba(29,158,117,0.3);
  }

  :global(html.light) .hero-bg {
    filter: brightness(0.8) contrast(1.0) saturate(1.1);
  }

  :global(html.light) .hero-overlay {
    background: linear-gradient(105deg, rgba(244,247,245,0.85) 0%, rgba(244,247,245,0.3) 100%);
  }

  /* ─── NAV ─── */
  nav {
    position: sticky; top: 0; z-index: 100;
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 2rem;
    height: 56px;
    background: rgba(13,15,14,0.85);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--border);
  }
  .nav-logo {
    display: flex; align-items: center; gap: 10px;
    font-family: var(--mono);
    font-size: 15px; font-weight: 500;
    color: var(--text);
    text-decoration: none;
  }
  .nav-logo-mark {
    width: 30px; height: 30px;
    background: var(--teal);
    border-radius: 7px;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px; font-weight: 500; color: #fff;
  }
  .nav-links {
    display: flex; gap: 0; align-items: center;
  }
  .nav-links a {
    font-size: 13px; color: var(--text2);
    padding: 6px 14px;
    border-radius: var(--radius);
    text-decoration: none;
    transition: color 0.15s, background 0.15s;
  }
  .nav-links a:hover { color: var(--text); background: rgba(255,255,255,0.05); }
  .nav-cta {
    display: inline-flex; align-items: center; gap: 7px;
    font-size: 13px; font-weight: 500; color: #fff;
    background: var(--teal);
    padding: 7px 16px;
    border-radius: var(--radius);
    text-decoration: none;
    transition: background 0.15s;
  }
  .nav-cta:hover { background: #0F6E56; }
  .nav-cta svg { width: 14px; height: 14px; }

  .theme-toggle-btn {
    background: transparent;
    border: none;
    color: var(--text2);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: color 0.15s;
    padding: 4px;
  }
  .theme-toggle-btn:hover {
    color: var(--text);
  }

  /* ─── HERO ─── */
  .hero {
    position: relative;
    min-height: 88vh;
    display: flex; align-items: center;
    overflow: hidden;
    z-index: 1;
    border-bottom: 1px solid var(--border);
  }
  .hero-bg {
    position: absolute; inset: 0;
    background-size: cover;
    background-position: center 30%;
    background-image: url('/assets/hero-serverraum.jpg');
    filter: brightness(0.45) contrast(1.05) saturate(1.2);
    z-index: 1;
    cursor: zoom-in;
    pointer-events: auto;
  }
  .hero-overlay {
    position: absolute; inset: 0;
    background: linear-gradient(
      105deg,
      rgba(13,15,14,0.75) 0%,
      rgba(13,15,14,0.15) 100%
    );
    z-index: 2;
    cursor: zoom-in;
    pointer-events: auto;
  }
  .hero-scanline {
    position: absolute; inset: 0;
    background: repeating-linear-gradient(
      0deg,
      transparent,
      transparent 3px,
      rgba(0,0,0,0.08) 3px,
      rgba(0,0,0,0.08) 4px
    );
    pointer-events: none;
    z-index: 3;
  }
  .hero-content {
    position: relative; z-index: 4;
    max-width: 1200px; margin: 0 auto;
    padding: 0 3rem;
    width: 100%;
    display: grid;
    grid-template-columns: 1.2fr 0.8fr;
    gap: 3rem;
    align-items: center;
  }
  .hero-eyebrow {
    display: inline-flex; align-items: center; gap: 8px;
    font-family: var(--mono);
    font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase;
    color: var(--teal-light);
    background: var(--teal-dim);
    border: 1px solid var(--teal-border);
    padding: 5px 14px;
    border-radius: 20px;
    margin-bottom: 1.5rem;
  }
  .hero-eyebrow::before {
    content: '';
    width: 6px; height: 6px;
    background: var(--teal-light);
    border-radius: 50%;
    animation: pulse 2s ease infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(0.7); }
  }
  .hero h1 {
    font-size: clamp(38px, 5vw, 62px);
    font-weight: 300;
    line-height: 1.08;
    color: var(--text);
    margin-bottom: 1.5rem;
    max-width: 640px;
  }
  .hero h1 em {
    font-style: normal;
    color: var(--teal-light);
    font-weight: 400;
  }
  .hero-sub {
    font-size: 16px;
    font-weight: 300;
    color: var(--text2);
    line-height: 1.7;
    max-width: 480px;
    margin-bottom: 2.5rem;
  }
  .hero-actions {
    display: flex; gap: 12px; flex-wrap: wrap;
  }
  .btn-hero-primary {
    display: inline-flex; align-items: center; gap: 8px;
    font-size: 14px; font-weight: 500;
    color: #fff; background: var(--teal);
    padding: 11px 24px;
    border-radius: var(--radius);
    text-decoration: none;
    transition: background 0.15s, transform 0.1s;
  }
  .btn-hero-primary:hover { background: #0F6E56; transform: translateY(-1px); }
  .btn-hero-primary svg { width: 16px; height: 16px; stroke: currentColor; }
  .btn-hero-ghost {
    display: inline-flex; align-items: center; gap: 8px;
    font-size: 14px; font-weight: 400;
    color: var(--text2);
    background: rgba(255,255,255,0.05);
    border: 1px solid var(--border2);
    padding: 11px 24px;
    border-radius: var(--radius);
    text-decoration: none;
    transition: color 0.15s, background 0.15s, transform 0.1s;
  }
  .btn-hero-ghost:hover { color: var(--text); background: rgba(255,255,255,0.09); transform: translateY(-1px); }
  .btn-hero-ghost svg { width: 16px; height: 16px; stroke: currentColor; }

  /* ─── HERO STATS ─── */
  .hero-stats {
    display: flex; flex-direction: column; gap: 12px;
  }
  .stat-card {
    display: flex; align-items: center; gap: 12px;
    background: rgba(13,15,14,0.72);
    backdrop-filter: blur(8px);
    border: 1px solid var(--border2);
    border-radius: var(--radius);
    padding: 10px 16px;
    min-width: 210px;
  }
  .stat-card-icon {
    width: 32px; height: 32px;
    background: var(--teal-dim);
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
  }
  .stat-card-icon svg { width: 16px; height: 16px; stroke: var(--teal-light); fill: none; stroke-width: 1.5; }
  .stat-card-label { font-size: 11px; color: var(--text3); font-family: var(--mono); text-transform: uppercase; letter-spacing: 0.07em; }
  .stat-card-val { font-size: 14px; font-weight: 500; color: var(--text); }

  /* ─── SECTION ─── */
  .section {
    position: relative; z-index: 1;
    max-width: 1200px; margin: 0 auto;
    padding: 5rem 3rem;
  }
  .section-label {
    font-family: var(--mono);
    font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase;
    color: var(--teal);
    margin-bottom: 1rem;
  }
  .section h2 {
    font-size: 28px; font-weight: 400;
    color: var(--text);
    margin-bottom: 0.5rem;
  }
  .section-sub {
    font-size: 15px; color: var(--text2);
    margin-bottom: 3rem;
  }

  /* ─── FEATURE GRID ─── */
  .feat-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1px;
    background: var(--border);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    overflow: hidden;
  }
  .feat-cell {
    background: var(--bg2);
    padding: 2rem;
    transition: background 0.15s;
    cursor: default;
  }
  .feat-cell:hover { background: var(--bg3); }
  .feat-cell-icon {
    width: 40px; height: 40px;
    background: var(--teal-dim);
    border: 1px solid var(--teal-border);
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    margin-bottom: 1rem;
  }
  .feat-cell-icon svg { width: 18px; height: 18px; stroke: var(--teal-light); fill: none; stroke-width: 1.5; }
  .feat-cell h3 { font-size: 14px; font-weight: 500; color: var(--text); margin-bottom: 6px; }
  .feat-cell p { font-size: 13px; color: var(--text2); line-height: 1.6; }
  .feat-cell-tag {
    display: inline-block; margin-top: 12px;
    font-family: var(--mono); font-size: 10px;
    color: var(--teal);
    background: var(--teal-dim);
    padding: 3px 8px;
    border-radius: 4px;
  }

  /* ─── STACK BAR ─── */
  .stack-bar {
    display: flex; gap: 12px; flex-wrap: wrap;
    margin-top: 4rem;
    padding-top: 2rem;
    border-top: 1px solid var(--border);
  }
  .stack-item {
    font-family: var(--mono);
    font-size: 12px; color: var(--text3);
    padding: 5px 12px;
    border: 1px solid var(--border);
    border-radius: 5px;
    background: var(--bg2);
  }

  /* ─── PRINCIPLES ─── */
  .principles {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
    margin-top: 2.5rem;
  }
  .principle-card {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    border-left: 3px solid var(--teal);
  }
  .principle-card h4 { font-size: 14px; font-weight: 500; color: var(--text); margin-bottom: 6px; }
  .principle-card p { font-size: 13px; color: var(--text2); line-height: 1.6; }

  /* ─── FOOTER ─── */
  footer {
    position: relative; z-index: 1;
    border-top: 1px solid var(--border);
    padding: 1.5rem 3rem;
    display: flex; align-items: center; justify-content: space-between;
    max-width: 100%;
    background: var(--bg);
  }
  footer p { font-family: var(--mono); font-size: 11px; color: var(--text3); }
  footer a {
    font-family: var(--mono); font-size: 11px; color: var(--teal);
    text-decoration: none;
  }

  /* ─── RESPONSIVE ─── */
  @media (max-width: 960px) {
    .hero-content { grid-template-columns: 1fr; gap: 2rem; }
    .feat-grid { grid-template-columns: repeat(2, 1fr); }
    .hero-stats { display: none; }
    .principles { grid-template-columns: 1fr; }
    nav .nav-links { display: none; }
  }
  @media (max-width: 600px) {
    .feat-grid { grid-template-columns: 1fr; }
    .section { padding: 3rem 1.5rem; }
    .hero-content { padding: 0 1.5rem; }
  }

  /* ─── HERO CAMERA BUTTON ─── */
  .hero-camera-btn {
    position: absolute;
    bottom: 1.5rem;
    right: 1.5rem;
    z-index: 5;
    background: rgba(16, 22, 34, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.15);
    color: var(--text2);
    width: 38px;
    height: 38px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.2s ease;
    backdrop-filter: blur(4px);
  }
  .hero-camera-btn:hover {
    background: var(--teal);
    color: #fff;
    border-color: var(--teal);
    box-shadow: 0 0 12px var(--teal-border);
    transform: scale(1.05);
  }
  .hero-camera-btn svg {
    width: 18px;
    height: 18px;
  }

  /* ─── LIGHTBOX ─── */
  .lightbox {
    position: fixed;
    inset: 0;
    z-index: 9999;
    background: rgba(0, 0, 0, 0.92);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: zoom-out;
  }
  .lightbox-img {
    max-width: 90vw;
    max-height: 90vh;
    object-fit: contain;
    border-radius: var(--radius-lg);
    box-shadow: 0 0 30px rgba(0, 0, 0, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.1);
  }
  .lightbox-close {
    position: absolute;
    top: 1.5rem;
    right: 2rem;
    background: none;
    border: none;
    color: var(--text);
    font-size: 2.5rem;
    cursor: pointer;
    line-height: 1;
    transition: color 0.15s;
  }
  .lightbox-close:hover {
    color: var(--teal);
  }
  :global(html.light) nav {
    background: var(--color-bg2);
    border-color: var(--color-border);
  }
  :global(html.light) .stat-card {
    background: var(--color-bg2);
    border-color: var(--color-border);
  }

</style>

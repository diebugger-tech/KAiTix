<script lang="ts">
  import '../layout.css';
  import { appState } from '$lib/state.svelte';
  import { api } from '$lib/api';
  import { page } from '$app/state';
  import {
    LayoutDashboard,
    Zap,
    FileUp,
    Cable,
    User,
    Activity,
    Server,
    Shield,
    Database,
    Download,
    FileSpreadsheet,
    FileText,
    Cpu,
    Layers,
    Network,
    Search,
    Monitor,
    BookOpen,
    Sun,
    Moon
  } from '@lucide/svelte';
  import { goto } from '$app/navigation';

  let { children } = $props();

  let editName = $state(appState.bearbeiter);
  let showEditName = $state(false);

  // Global search
  let searchQ = $state('');
  let searchResults = $state<Awaited<ReturnType<typeof api.search>> | null>(null);
  let searchOpen = $state(false);
  let searchTimer: ReturnType<typeof setTimeout>;

  function onSearchInput() {
    clearTimeout(searchTimer);
    if (searchQ.length < 2) { searchResults = null; searchOpen = false; return; }
    searchTimer = setTimeout(async () => {
      try {
        searchResults = await api.search(searchQ);
        searchOpen = true;
      } catch { /* ignore */ }
    }, 250);
  }

  function closeSearch() { searchOpen = false; searchQ = ''; searchResults = null; }

  function gotoDevice(id: number) { closeSearch(); goto(`/devices?device=${id}`); }
  function gotoCable(id: number)  { closeSearch(); goto(`/cables?cable=${id}`); }
  function gotoRack(id: number)   { closeSearch(); goto(`/racks?rack=${id}`); }

  function saveBearbeiter() {
    if (editName.trim()) {
      appState.setBearbeiter(editName.trim());
      showEditName = false;
    }
  }

  // Get dynamic title based on path
  const pageTitle = $derived(() => {
    const route = page.url.pathname as string;
    if (route === '/') return 'Dashboard';
    if (route === '/racks') return 'Rechenzentrum Racks';
    if (route === '/usv') return 'USV-Auslegungsplanung';
    if (route === '/import') return 'Import';
    if (route === '/topology') return 'Topologie';
    if (route === '/eplan') return 'E-Plan';
    if (route === '/cables') return 'Kabelliste & Export';
    if (route === '/hardware') return 'Hardware-Katalog';
    if (route === '/virtual-machines') return 'Virtuelle Maschinen';
    if (route.startsWith('/runbook-orchestrator')) return 'Runbook Orchestrator';
    return 'KAiTix';
  });

  const navGroups = [
    {
      title: 'Infrastruktur',
      links: [
        { href: '/racks', icon: Layers, label: 'Racks' },
        { href: '/hardware', icon: Cpu, label: 'Hardware' },
        { href: '/cables', icon: Cable, label: 'Kabelliste' },
        { href: '/topology', icon: Network, label: 'Topologie' }
      ]
    },
    {
      title: 'Stromversorgung',
      links: [
        { href: '/usv', icon: Zap, label: 'USV-Auslegung' },
        { href: '/eplan', icon: Zap, label: 'E-Plan' }
      ]
    },
    {
      title: 'Virtualisierung',
      links: [
        { href: '/virtual-machines', icon: Monitor, label: 'Virtuelle Maschinen' }
      ]
    },
    {
      title: 'Betrieb',
      links: [
        { href: '/runbook-orchestrator', icon: BookOpen, label: 'Runbook Orchestrator', matchPrefix: true }
      ]
    },
    {
      title: 'Tools',
      links: [
        { href: '/import', icon: FileUp, label: 'Import' }
      ]
    }
  ];
</script>

<div class="flex h-screen overflow-hidden app-root">
  <!-- Left Sidebar -->
  <aside class="w-64 border-r flex flex-col justify-between z-30" style="background: var(--color-bg2); border-color: var(--color-border);">
    <div>
      <!-- Brand Logo -->
      <a 
        href="/landingpage" 
        class="h-16 flex items-center px-6 border-b space-x-3 hover:opacity-80 transition-opacity no-underline block"
        style="border-color: var(--color-border);"
      >
        <div class="w-8 h-8 rounded bg-gradient-to-tr from-[#1D9E75] to-[#5DCAA5] flex items-center justify-center shadow-lg shadow-[#1D9E75]/20">
          <Server class="w-5 h-5 text-[var(--color-text)]" />
        </div>
        <div>
          <h1 class="text-lg font-bold font-outfit tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-[#5DCAA5] to-[#86EFCB]">KAiTix</h1>
          <span class="text-[10px] text-[var(--color-text3)] font-mono tracking-widest uppercase">Plan. Simulate. Document.</span>
        </div>
      </a>

      <!-- Navigation -->
      <nav class="p-4 space-y-1">
        <!-- Dashboard -->
        <a 
          href="/" 
          class="nav-link {page.url.pathname === '/' ? 'active' : ''}"
        >
          <LayoutDashboard class="w-4.5 h-4.5" />
          <span>Dashboard</span>
        </a>

        {#each navGroups as group, i}
          <!-- Group: {group.title} -->
          <div class="pt-3 pb-1 px-4 {i > 0 ? 'border-t border-[var(--color-border)]/60 mt-3' : ''}">
            <span class="nav-group-title">{group.title}</span>
          </div>
          {#each group.links as link}
            <a
              href={link.href}
              class="nav-link {link.matchPrefix ? (page.url.pathname.startsWith(link.href) ? 'active' : '') : (page.url.pathname === link.href ? 'active' : '')}"
            >
              <svelte:component this={link.icon} class="w-4.5 h-4.5" />
              <span>{link.label}</span>
            </a>
          {/each}
        {/each}
      </nav>

      <!-- Quick Export -->
      <div class="px-4 pb-2 space-y-2">
        <!-- Vollständig -->
        <div class="bg-[var(--color-bg3)] border border-[var(--color-border)] rounded-lg p-3">
          <div class="flex items-center gap-2 mb-2">
            <Download class="w-3.5 h-3.5 text-[var(--color-text3)]" />
            <span class="text-[10px] font-semibold text-[var(--color-text3)] uppercase tracking-wider">Vollexport</span>
          </div>
          <div class="flex gap-1.5">
            <a href="/api/v1/export/xlsx" class="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded text-[10px] font-medium quick-export-btn">
              <FileSpreadsheet class="w-3 h-3" />
              <span>Excel</span>
            </a>
            <a href="/api/v1/export/csv" class="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 border rounded text-[10px] font-medium quick-export-btn">
              <FileText class="w-3 h-3" />
              <span>ZIP</span>
            </a>
            <a href="/api/v1/export/ods" class="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 border rounded text-[10px] font-medium quick-export-btn-teal">
              <FileText class="w-3 h-3" />
              <span>ODS</span>
            </a>
          </div>
        </div>
        <!-- Einzel-Exports -->
        <div class="bg-[var(--color-bg3)] border border-[var(--color-border)] rounded-lg p-3">
          <div class="flex items-center gap-2 mb-2">
            <FileSpreadsheet class="w-3.5 h-3.5 text-[var(--color-text3)]" />
            <span class="nav-group-title">Einzelexport</span>
          </div>
          <div class="flex flex-col gap-1">
            <a href="/api/v1/export/racks" class="flex items-center gap-1.5 px-2 py-1 border rounded text-[10px] quick-export-btn">
              <FileSpreadsheet class="w-3 h-3 shrink-0" />
              <span>Rack-Inventar</span>
            </a>
            <a href="/api/v1/export/interfaces" class="flex items-center gap-1.5 px-2 py-1 border rounded text-[10px] quick-export-btn">
              <FileSpreadsheet class="w-3 h-3 shrink-0" />
              <span>Ports & Interfaces</span>
            </a>
            <a href="/api/v1/export/pdus" class="flex items-center gap-1.5 px-2 py-1 border rounded text-[10px] quick-export-btn">
              <FileSpreadsheet class="w-3 h-3 shrink-0" />
              <span>PDU-Belegung</span>
            </a>
          </div>
        </div>
      </div>
    </div>

    <!-- Sidebar Footer -->
    <div class="p-4 border-t border-[var(--color-border)] space-y-4">
      <!-- Bearbeiter Info -->
      <div class="bg-[var(--color-bg3)] border border-[var(--color-border)] rounded-lg p-3 relative group">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <User class="w-4 h-4 text-[#5DCAA5]" />
            <div class="text-xs">
              <div class="text-[10px] text-[var(--color-text3)] uppercase tracking-wider font-mono">Bearbeiter</div>
              <div class="font-medium text-[var(--color-text)] truncate max-w-[120px]">{appState.bearbeiter}</div>
            </div>
          </div>
          <button 
            onclick={() => { editName = appState.bearbeiter; showEditName = true; }} 
            class="text-[10px] text-[#5DCAA5] hover:text-[#86EFCB] font-semibold"
          >
            Ändern
          </button>
        </div>
      </div>

      <!-- Network status -->
      <div class="flex items-center justify-between px-2 text-xs">
        <span class="text-[var(--color-text3)]">API Status:</span>
        <div class="flex items-center space-x-1.5">
          <div class="w-2.5 h-2.5 rounded-full {appState.backendOnline ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}"></div>
          <span class={appState.backendOnline ? 'text-emerald-400 font-mono' : 'text-red-400 font-mono'}>
            {appState.backendOnline ? 'ONLINE' : 'OFFLINE'}
          </span>
        </div>
      </div>
    </div>
  </aside>

  <!-- Main Content Wrapper -->
  <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
    <!-- Top Header -->
    <header class="h-16 border-b flex items-center justify-between px-8 z-20 shrink-0 relative app-header">
      <div class="flex items-center space-x-3">
        <div>
          <h2 class="text-xl font-bold tracking-tight text-[var(--color-text)] font-outfit">{pageTitle()}</h2>
          {#if (page.url.pathname as string) === '/usv'}
            <p class="text-[10px] text-[var(--color-text3)] mt-0.5">Dimensionierung zur USV-Beschaffung — keine Live-Daten</p>
          {/if}
        </div>
      </div>

      <!-- Global Search -->
      <div class="relative w-72">
        <Search class="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text3)] pointer-events-none" />
        <input
          type="text"
          bind:value={searchQ}
          oninput={onSearchInput}
          onblur={() => setTimeout(closeSearch, 150)}
          placeholder="Suche Gerät, Kabel, Rack…"
          class="w-full border rounded-lg pl-9 pr-4 py-1.5 text-xs focus:outline-none global-search-input"
        />
        {#if searchOpen && searchResults}
          {@const total = searchResults.devices.length + searchResults.cables.length + searchResults.racks.length}
          {#if total > 0}
            <div class="absolute top-full mt-1 w-full border rounded-xl shadow-2xl overflow-hidden z-50 dropdown-menu">
              {#if searchResults.racks.length > 0}
                <div class="px-3 pt-2 pb-1 text-[9px] uppercase font-bold text-[var(--color-text3)] tracking-wider">Racks</div>
                {#each searchResults.racks as r}
                  <button onclick={() => gotoRack(r.id)} class="w-full text-left px-3 py-1.5 hover:bg-[var(--color-border2)] flex items-center gap-2">
                    <Layers class="w-3 h-3 shrink-0 text-[#5DCAA5]" />
                    <span class="text-xs truncate dropdown-text">{r.name}</span>
                    <span class="text-[10px] ml-auto shrink-0 dropdown-subtext">{r.standort}</span>
                  </button>
                {/each}
              {/if}
              {#if searchResults.devices.length > 0}
                <div class="px-3 pt-2 pb-1 text-[9px] uppercase font-bold text-[var(--color-text3)] tracking-wider">Geräte</div>
                {#each searchResults.devices as d}
                  <button onclick={() => gotoDevice(d.id)} class="w-full text-left px-3 py-1.5 hover:bg-[var(--color-border2)] flex items-center gap-2">
                    <Server class="w-3 h-3 shrink-0 text-[var(--color-text2)]" />
                    <span class="text-xs font-mono truncate dropdown-text">{d.hostname}</span>
                    <span class="text-[10px] ml-auto shrink-0 dropdown-subtext">{d.typ}</span>
                  </button>
                {/each}
              {/if}
              {#if searchResults.cables.length > 0}
                <div class="px-3 pt-2 pb-1 text-[9px] uppercase font-bold text-[var(--color-text3)] tracking-wider">Kabel</div>
                {#each searchResults.cables as c}
                  <button onclick={() => gotoCable(c.id)} class="w-full text-left px-3 py-1.5 hover:bg-[var(--color-border2)] flex items-center gap-2">
                    <Cable class="w-3 h-3 shrink-0 text-emerald-400" />
                    <span class="text-xs font-mono truncate dropdown-text">{c.kabel_nr || '—'}</span>
                    <span class="text-[10px] ml-auto shrink-0 dropdown-subtext">{c.typ}</span>
                  </button>
                {/each}
              {/if}
              <div class="px-3 py-1.5 border-t text-[9px] dropdown-subtext dropdown-divider">{total} Treffer</div>
            </div>
          {:else}
            <div class="absolute top-full mt-1 w-full border rounded-xl shadow-2xl p-3 z-50 text-xs text-center dropdown-menu dropdown-subtext">Keine Treffer</div>
          {/if}
        {/if}
      </div>

      <div class="flex items-center space-x-4">
        <!-- Theme Switcher -->
        <button 
          onclick={() => appState.toggleTheme()}
          class="p-2 rounded-lg border border-[var(--color-border2)] global-search-input hover:border-[#1D9E75] hover:opacity-80 transition-all focus:outline-none"
          title="Theme wechseln"
        >
          {#if appState.theme === 'dark'}
            <Sun class="w-4 h-4" />
          {:else}
            <Moon class="w-4 h-4" />
          {/if}
        </button>

        <!-- Bearbeiter quick display -->
        <span class="text-xs border px-3 py-1.5 rounded-full flex items-center space-x-1 bearbeiter-pill">
          <span class="w-1.5 h-1.5 rounded-full bg-[#1D9E75]"></span>
          <span>Sitzung: <strong>{appState.bearbeiter}</strong></span>
        </span>
      </div>
    </header>

    <!-- Page Body -->
    <main class="flex-1 overflow-y-auto p-8 relative">
      {@render children()}
    </main>
  </div>
</div>

<!-- Modal Bearbeiter ändern -->
{#if showEditName}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[var(--color-bg2)] border rounded-xl p-6 max-w-sm w-full shadow-2xl app-header">
    <h3 class="text-lg font-bold text-[var(--color-text)] mb-2">Bearbeiter festlegen</h3>
    <p class="text-xs text-[var(--color-text2)] mb-4">
      Geben Sie Ihren Namen ein. Alle Änderungen, die Sie vornehmen, werden unter diesem Kürzel erfasst.
    </p>
    <input 
      type="text" 
      bind:value={editName}
      class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-4 py-2.5 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75] mb-4"
      placeholder="z.B. Andreas"
    />
    <div class="flex justify-end space-x-3">
      <button 
        onclick={() => showEditName = false} 
        class="px-4 py-2 rounded-lg text-sm text-[var(--color-text2)] hover:bg-[var(--color-border)] transition"
      >
        Abbrechen
      </button>
      <button 
        onclick={saveBearbeiter} 
        class="px-4 py-2 bg-[#1D9E75] hover:bg-[#0F6E56] text-[var(--color-text)] rounded-lg text-sm font-semibold transition"
      >
        Speichern
      </button>
    </div>
  </div>
</div>
{/if}

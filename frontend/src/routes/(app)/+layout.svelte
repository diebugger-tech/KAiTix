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
    BookOpen
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
</script>

<div class="flex h-screen overflow-hidden bg-[#0D0F0E]">
  <!-- Left Sidebar -->
  <aside class="w-64 bg-[#131615] border-r border-slate-800 flex flex-col justify-between z-30">
    <div>
      <!-- Brand Logo -->
      <a 
        href="/landingpage" 
        class="h-16 flex items-center px-6 border-b border-slate-800 space-x-3 hover:opacity-80 transition-opacity no-underline block"
      >
        <div class="w-8 h-8 rounded bg-gradient-to-tr from-[#1D9E75] to-[#5DCAA5] flex items-center justify-center shadow-lg shadow-[#1D9E75]/20">
          <Server class="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 class="text-lg font-bold font-outfit tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-[#5DCAA5] to-[#86EFCB]">KAiTix</h1>
          <span class="text-[10px] text-slate-500 font-mono tracking-widest uppercase">Plan. Simulate. Document.</span>
        </div>
      </a>

      <!-- Navigation -->
      <nav class="p-4 space-y-1">
        <!-- Dashboard -->
        <a 
          href="/" 
          class="flex items-center space-x-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 {page.url.pathname === '/' ? 'bg-[rgba(29,158,117,0.18)] text-[#5DCAA5] border-l-2 border-[#1D9E75] pl-3.5' : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'}"
        >
          <LayoutDashboard class="w-4.5 h-4.5" />
          <span>Dashboard</span>
        </a>

        <!-- Group: Infrastruktur -->
        <div class="pt-3 pb-1 px-4">
          <span class="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">Infrastruktur</span>
        </div>
        <a
          href="/racks"
          class="flex items-center space-x-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 {page.url.pathname === '/racks' ? 'bg-[rgba(29,158,117,0.18)] text-[#5DCAA5] border-l-2 border-[#1D9E75] pl-3.5' : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'}"
        >
          <Layers class="w-4.5 h-4.5" />
          <span>Racks</span>
        </a>
        <a 
          href="/hardware" 
          class="flex items-center space-x-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 {page.url.pathname === '/hardware' ? 'bg-purple-500/20 text-purple-400 border-l-2 border-purple-500 pl-3.5' : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'}"
        >
          <Cpu class="w-4.5 h-4.5" />
          <span>Hardware</span>
        </a>
        <a 
          href="/cables" 
          class="flex items-center space-x-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 {page.url.pathname === '/cables' ? 'bg-emerald-500/20 text-emerald-400 border-l-2 border-emerald-500 pl-3.5' : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'}"
        >
          <Cable class="w-4.5 h-4.5" />
          <span>Kabelliste</span>
        </a>
        <a
          href="/topology"
          class="flex items-center space-x-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 {(page.url.pathname as string) === '/topology' ? 'bg-violet-500/20 text-violet-400 border-l-2 border-violet-500 pl-3.5' : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'}"
        >
          <Network class="w-4.5 h-4.5" />
          <span>Topologie</span>
        </a>

        <!-- Group: Stromversorgung -->
        <div class="pt-3 pb-1 px-4 border-t border-slate-800/60 mt-3">
          <span class="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">Stromversorgung</span>
        </div>
        <a
          href="/usv" 
          class="flex items-center space-x-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 {page.url.pathname === '/usv' ? 'bg-orange-500/20 text-orange-400 border-l-2 border-orange-500 pl-3.5' : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'}"
        >
          <Zap class="w-4.5 h-4.5" />
          <span>USV-Auslegung</span>
        </a>
        <a
          href="/eplan"
          class="flex items-center space-x-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 {(page.url.pathname as string) === '/eplan' ? 'bg-rose-500/20 text-rose-400 border-l-2 border-rose-500 pl-3.5' : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'}"
        >
          <Zap class="w-4.5 h-4.5" />
          <span>E-Plan</span>
        </a>

        <!-- Group: Virtualisierung -->
        <div class="pt-3 pb-1 px-4 border-t border-slate-800/60 mt-3">
          <span class="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">Virtualisierung</span>
        </div>
        <a 
          href="/virtual-machines" 
          class="flex items-center space-x-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 {page.url.pathname === '/virtual-machines' ? 'bg-pink-500/20 text-pink-400 border-l-2 border-pink-500 pl-3.5' : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'}"
        >
          <Monitor class="w-4.5 h-4.5" />
          <span>Virtuelle Maschinen</span>
        </a>

        <!-- Group: Betrieb -->
        <div class="pt-3 pb-1 px-4 border-t border-slate-800/60 mt-3">
          <span class="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">Betrieb</span>
        </div>
        <a 
          href="/runbook-orchestrator" 
          class="flex items-center space-x-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 {page.url.pathname.startsWith('/runbook-orchestrator') ? 'bg-yellow-500/20 text-yellow-400 border-l-2 border-yellow-500 pl-3.5' : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'}"
        >
          <BookOpen class="w-4.5 h-4.5" />
          <span>Runbook Orchestrator</span>
        </a>

        <!-- Group: Tools -->
        <div class="pt-3 pb-1 px-4 border-t border-slate-800/60 mt-3">
          <span class="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">Tools</span>
        </div>
        <a
          href="/import"
          class="flex items-center space-x-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 {(page.url.pathname as string) === '/import' ? 'bg-cyan-500/20 text-cyan-400 border-l-2 border-cyan-500 pl-3.5' : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'}"
        >
          <FileUp class="w-4.5 h-4.5" />
          <span>Import</span>
        </a>
      </nav>

      <!-- Quick Export -->
      <div class="px-4 pb-2 space-y-2">
        <!-- Vollständig -->
        <div class="bg-slate-900/40 border border-slate-800 rounded-lg p-3">
          <div class="flex items-center gap-2 mb-2">
            <Download class="w-3.5 h-3.5 text-slate-500" />
            <span class="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Vollexport</span>
          </div>
          <div class="flex gap-1.5">
            <a href="/api/v1/export/xlsx" class="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 bg-emerald-600/10 text-emerald-400 border border-emerald-600/20 rounded text-[10px] font-medium hover:bg-emerald-600/20 transition">
              <FileSpreadsheet class="w-3 h-3" />
              <span>Excel</span>
            </a>
            <a href="/api/v1/export/csv" class="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 bg-slate-800 text-slate-300 border border-slate-700 rounded text-[10px] font-medium hover:bg-slate-700 transition">
              <FileText class="w-3 h-3" />
              <span>ZIP</span>
            </a>
            <a href="/api/v1/export/ods" class="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 bg-[rgba(29,158,117,0.15)] text-[#5DCAA5] border border-[rgba(29,158,117,0.25)] rounded text-[10px] font-medium hover:bg-[rgba(29,158,117,0.25)] transition">
              <FileText class="w-3 h-3" />
              <span>ODS</span>
            </a>
          </div>
        </div>
        <!-- Einzel-Exports -->
        <div class="bg-slate-900/40 border border-slate-800 rounded-lg p-3">
          <div class="flex items-center gap-2 mb-2">
            <FileSpreadsheet class="w-3.5 h-3.5 text-slate-500" />
            <span class="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Einzelexport</span>
          </div>
          <div class="flex flex-col gap-1">
            <a href="/api/v1/export/racks" class="flex items-center gap-1.5 px-2 py-1 bg-slate-800/60 text-slate-400 border border-slate-700/50 rounded text-[10px] hover:text-slate-200 hover:bg-slate-700 transition">
              <FileSpreadsheet class="w-3 h-3 shrink-0" />
              <span>Rack-Inventar</span>
            </a>
            <a href="/api/v1/export/interfaces" class="flex items-center gap-1.5 px-2 py-1 bg-slate-800/60 text-slate-400 border border-slate-700/50 rounded text-[10px] hover:text-slate-200 hover:bg-slate-700 transition">
              <FileSpreadsheet class="w-3 h-3 shrink-0" />
              <span>Ports & Interfaces</span>
            </a>
            <a href="/api/v1/export/pdus" class="flex items-center gap-1.5 px-2 py-1 bg-slate-800/60 text-slate-400 border border-slate-700/50 rounded text-[10px] hover:text-slate-200 hover:bg-slate-700 transition">
              <FileSpreadsheet class="w-3 h-3 shrink-0" />
              <span>PDU-Belegung</span>
            </a>
          </div>
        </div>
      </div>
    </div>

    <!-- Sidebar Footer -->
    <div class="p-4 border-t border-slate-800 space-y-4">
      <!-- Bearbeiter Info -->
      <div class="bg-slate-900/60 border border-slate-800 rounded-lg p-3 relative group">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <User class="w-4 h-4 text-[#5DCAA5]" />
            <div class="text-xs">
              <div class="text-[10px] text-slate-500 uppercase tracking-wider font-mono">Bearbeiter</div>
              <div class="font-medium text-slate-200 truncate max-w-[120px]">{appState.bearbeiter}</div>
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
        <span class="text-slate-500">API Status:</span>
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
    <header class="h-16 border-b border-slate-800 bg-[#131615] flex items-center justify-between px-8 z-20 shrink-0 relative">
      <div class="flex items-center space-x-3">
        <div>
          <h2 class="text-xl font-bold tracking-tight text-white font-outfit">{pageTitle()}</h2>
          {#if (page.url.pathname as string) === '/usv'}
            <p class="text-[10px] text-slate-500 mt-0.5">Dimensionierung zur USV-Beschaffung — keine Live-Daten</p>
          {/if}
        </div>
      </div>

      <!-- Global Search -->
      <div class="relative w-72">
        <Search class="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
        <input
          type="text"
          bind:value={searchQ}
          oninput={onSearchInput}
          onblur={() => setTimeout(closeSearch, 150)}
          placeholder="Suche Gerät, Kabel, Rack…"
          class="w-full bg-[#181C1A] border border-slate-700 rounded-lg pl-9 pr-4 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#1D9E75]"
        />
        {#if searchOpen && searchResults}
          {@const total = searchResults.devices.length + searchResults.cables.length + searchResults.racks.length}
          {#if total > 0}
            <div class="absolute top-full mt-1 w-full bg-[#131615] border border-slate-700 rounded-xl shadow-2xl overflow-hidden z-50">
              {#if searchResults.racks.length > 0}
                <div class="px-3 pt-2 pb-1 text-[9px] uppercase font-bold text-slate-500 tracking-wider">Racks</div>
                {#each searchResults.racks as r}
                  <button onclick={() => gotoRack(r.id)} class="w-full text-left px-3 py-1.5 hover:bg-slate-800/60 flex items-center gap-2">
                    <Layers class="w-3 h-3 shrink-0 text-[#5DCAA5]" />
                    <span class="text-xs text-slate-200 truncate">{r.name}</span>
                    <span class="text-[10px] text-slate-500 ml-auto shrink-0">{r.standort}</span>
                  </button>
                {/each}
              {/if}
              {#if searchResults.devices.length > 0}
                <div class="px-3 pt-2 pb-1 text-[9px] uppercase font-bold text-slate-500 tracking-wider">Geräte</div>
                {#each searchResults.devices as d}
                  <button onclick={() => gotoDevice(d.id)} class="w-full text-left px-3 py-1.5 hover:bg-slate-800/60 flex items-center gap-2">
                    <Server class="w-3 h-3 shrink-0 text-slate-400" />
                    <span class="text-xs text-slate-200 font-mono truncate">{d.hostname}</span>
                    <span class="text-[10px] text-slate-500 ml-auto shrink-0">{d.typ}</span>
                  </button>
                {/each}
              {/if}
              {#if searchResults.cables.length > 0}
                <div class="px-3 pt-2 pb-1 text-[9px] uppercase font-bold text-slate-500 tracking-wider">Kabel</div>
                {#each searchResults.cables as c}
                  <button onclick={() => gotoCable(c.id)} class="w-full text-left px-3 py-1.5 hover:bg-slate-800/60 flex items-center gap-2">
                    <Cable class="w-3 h-3 shrink-0 text-emerald-400" />
                    <span class="text-xs text-slate-200 font-mono truncate">{c.kabel_nr || '—'}</span>
                    <span class="text-[10px] text-slate-500 ml-auto shrink-0">{c.typ}</span>
                  </button>
                {/each}
              {/if}
              <div class="px-3 py-1.5 border-t border-slate-800 text-[9px] text-slate-600">{total} Treffer</div>
            </div>
          {:else}
            <div class="absolute top-full mt-1 w-full bg-[#131615] border border-slate-700 rounded-xl shadow-2xl p-3 z-50 text-xs text-slate-500 text-center">Keine Treffer</div>
          {/if}
        {/if}
      </div>

      <div class="flex items-center space-x-4">
        <!-- Bearbeiter quick display -->
        <span class="text-xs bg-slate-800 border border-slate-700 px-3 py-1.5 rounded-full text-slate-300 flex items-center space-x-1">
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
  <div class="bg-[#131615] border border-slate-800 rounded-xl p-6 max-w-sm w-full shadow-2xl">
    <h3 class="text-lg font-bold text-white mb-2">Bearbeiter festlegen</h3>
    <p class="text-xs text-slate-400 mb-4">
      Geben Sie Ihren Namen ein. Alle Änderungen, die Sie vornehmen, werden unter diesem Kürzel erfasst.
    </p>
    <input 
      type="text" 
      bind:value={editName}
      class="w-full bg-[#181C1A] border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-white focus:outline-none focus:border-[#1D9E75] mb-4"
      placeholder="z.B. Andreas"
    />
    <div class="flex justify-end space-x-3">
      <button 
        onclick={() => showEditName = false} 
        class="px-4 py-2 rounded-lg text-sm text-slate-400 hover:bg-slate-800 transition"
      >
        Abbrechen
      </button>
      <button 
        onclick={saveBearbeiter} 
        class="px-4 py-2 bg-[#1D9E75] hover:bg-[#0F6E56] text-white rounded-lg text-sm font-semibold transition"
      >
        Speichern
      </button>
    </div>
  </div>
</div>
{/if}

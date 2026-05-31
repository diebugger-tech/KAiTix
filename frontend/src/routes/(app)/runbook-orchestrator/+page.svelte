<script lang="ts">
  import { onMount } from 'svelte';
  import { api, type Runbook } from '$lib/api';
  import { BookOpen, Plus, Search, AlertCircle, FileText, Calendar, User } from '@lucide/svelte';
  import { goto } from '$app/navigation';

  let runbooks = $state<Runbook[]>([]);
  let loading = $state(true);
  let error = $state('');
  
  let showCreateModal = $state(false);
  let newRunbook = $state({
    name: '',
    typ: 'shutdown' as Runbook['typ'],
    beschreibung: ''
  });

  onMount(async () => {
    await loadRunbooks();
  });

  async function loadRunbooks() {
    try {
      loading = true;
      runbooks = await api.getRunbooks();
    } catch (e: any) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  async function createRunbook() {
    try {
      const created = await api.createRunbook(newRunbook);
      showCreateModal = false;
      await loadRunbooks();
      goto(`/runbook-orchestrator/${created.id}`);
    } catch (e: any) {
      alert(e.message);
    }
  }

  function getTypeColor(typ: string) {
    if (typ === 'shutdown') return 'bg-red-500/10 text-red-400 border-red-500/20';
    if (typ === 'startup') return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
    return 'bg-blue-500/10 text-blue-400 border-[#1D9E75]/20';
  }
</script>

<div class="h-full flex flex-col space-y-6">
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-[var(--color-text)] tracking-tight flex items-center gap-3">
        <BookOpen class="w-6 h-6 text-yellow-400" />
        Runbooks
      </h1>
      <p class="text-[var(--color-text2)] text-sm mt-1">
        Planung und Ausführung von IT-Notfall-, Wartungs- und Shutdown-Sequenzen.
      </p>
    </div>
    <button 
      onclick={() => showCreateModal = true}
      class="flex items-center space-x-2 bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 hover:bg-yellow-500/30 px-4 py-2 rounded-lg text-sm font-medium transition"
    >
      <Plus class="w-4 h-4" />
      <span>Neues Runbook</span>
    </button>
  </div>

  {#if error}
    <div class="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl flex items-center gap-3">
      <AlertCircle class="w-5 h-5 shrink-0" />
      <p class="text-sm">{error}</p>
    </div>
  {/if}

  {#if loading}
    <div class="text-center text-[var(--color-text3)] py-12">Lade Runbooks...</div>
  {:else if runbooks.length === 0}
    <div class="text-center py-16 bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl">
      <BookOpen class="w-12 h-12 text-[var(--color-text3)] mx-auto mb-4" />
      <h3 class="text-lg font-semibold text-[var(--color-text)]">Keine Runbooks gefunden</h3>
      <p class="text-sm text-[var(--color-text3)] mt-2 max-w-md mx-auto">
        Erstellen Sie das erste Runbook, um geordnete Shutdowns oder Startups zu orchestrieren.
      </p>
      <button 
        onclick={() => showCreateModal = true}
        class="mt-6 flex items-center space-x-2 bg-[var(--color-border)] hover:bg-[var(--color-border2)] text-[var(--color-text)] px-4 py-2 rounded-lg text-sm font-medium transition mx-auto"
      >
        <Plus class="w-4 h-4" />
        <span>Runbook anlegen</span>
      </button>
    </div>
  {:else}
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {#each runbooks as runbook}
        <div 
          role="button"
          tabindex="0"
          onkeydown={(e) => e.key === 'Enter' && goto(`/runbook-orchestrator/${runbook.id}`)}
          onclick={() => goto(`/runbook-orchestrator/${runbook.id}`)}
          class="bg-[var(--color-bg2)] border border-[var(--color-border)] hover:border-[var(--color-border2)] rounded-xl p-5 flex flex-col transition cursor-pointer group"
        >
          <div class="flex items-start justify-between mb-3">
            <span class={`text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded border ${getTypeColor(runbook.typ)}`}>
              {runbook.typ}
            </span>
            {#if runbook.generated_from_id}
              <span class="text-[9px] text-[var(--color-text3)] bg-[var(--color-border)] px-1.5 py-0.5 rounded" title={`Generiert aus ID: ${runbook.generated_from_id}`}>
                Auto-generiert
              </span>
            {/if}
          </div>
          <h3 class="text-lg font-bold text-[var(--color-text)] group-hover:text-blue-400 transition leading-tight mb-2">
            {runbook.name}
          </h3>
          {#if runbook.beschreibung}
            <p class="text-xs text-[var(--color-text2)] line-clamp-2 mb-4 flex-1">
              {runbook.beschreibung}
            </p>
          {:else}
            <div class="flex-1"></div>
          {/if}
          <div class="pt-3 mt-auto border-t border-[var(--color-border)]/50 flex flex-col gap-1.5 text-[10px] text-[var(--color-text3)]">
            <div class="flex items-center gap-1.5">
              <Calendar class="w-3 h-3" />
              <span>{new Date(runbook.erstellt_am).toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' })}</span>
            </div>
            <div class="flex items-center gap-1.5">
              <User class="w-3 h-3" />
              <span>{runbook.erstellt_von || 'System'}</span>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

{#if showCreateModal}
<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl w-full max-w-lg shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
    <div class="p-4 border-b border-[var(--color-border)] flex items-center justify-between">
      <h3 class="text-lg font-bold text-[var(--color-text)]">Neues Runbook anlegen</h3>
      <button onclick={() => showCreateModal = false} class="text-[var(--color-text2)] hover:text-[var(--color-text)]">✕</button>
    </div>
    
    <div class="p-6 space-y-4 overflow-y-auto">
      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Name / Bezeichnung <span class="text-red-400">*</span></label>
        <input 
          type="text" 
          bind:value={newRunbook.name}
          placeholder="z.B. Data Center Shutdown Notfall"
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-yellow-500"
        />
      </div>

      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Typ <span class="text-red-400">*</span></label>
        <select
          bind:value={newRunbook.typ}
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-yellow-500"
        >
          <option value="shutdown">Shutdown (Herunterfahren)</option>
          <option value="startup">Startup (Hochfahren)</option>
          <option value="wartung">Wartung</option>
          <option value="notfall">Notfall</option>
          <option value="custom">Benutzerdefiniert</option>
        </select>
      </div>

      <div>
        <label class="block text-xs font-semibold text-[var(--color-text2)] mb-1">Beschreibung</label>
        <textarea 
          bind:value={newRunbook.beschreibung}
          rows="3"
          placeholder="Zweck und Kontext dieses Runbooks..."
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-yellow-500 resize-none"
        ></textarea>
      </div>
    </div>

    <div class="p-4 border-t border-[var(--color-border)] bg-[var(--color-bg2)] flex justify-end gap-3">
      <button 
        onclick={() => showCreateModal = false} 
        class="px-4 py-2 rounded-lg text-sm font-medium text-[var(--color-text2)] hover:text-[var(--color-text)] hover:bg-[var(--color-border)] transition"
      >
        Abbrechen
      </button>
      <button 
        onclick={createRunbook} 
        disabled={!newRunbook.name.trim()}
        class="px-4 py-2 bg-yellow-600 hover:bg-yellow-500 disabled:opacity-50 disabled:cursor-not-allowed text-[var(--color-text)] rounded-lg text-sm font-semibold transition"
      >
        Erstellen
      </button>
    </div>
  </div>
</div>
{/if}

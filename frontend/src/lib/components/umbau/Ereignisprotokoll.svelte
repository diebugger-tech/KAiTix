<!-- Aufklappbares Protokoll des Umbaus: Statuswechsel und jede Buchung an einem Ende. -->
<script lang="ts">
  import { STATUS_LABEL, ENDE_STATUS_LABEL, zeit, type UmbauDetail, type UmbauEreignis } from '$lib/umbauApi';
  import { History } from '@lucide/svelte';

  let { umbau }: { umbau: UmbauDetail } = $props();

  const enden = $derived(new Map(umbau.enden.map(e => [e.id, e])));

  function label(status?: string | null): string {
    if (!status) return '—';
    return (
      (STATUS_LABEL as Record<string, string>)[status] ??
      (ENDE_STATUS_LABEL as Record<string, string>)[status] ??
      status
    );
  }

  function gegenstand(ereignis: UmbauEreignis): string {
    if (ereignis.ende_id == null) return 'Umbau';
    const ende = enden.get(ereignis.ende_id);
    if (!ende) return `Ende #${ereignis.ende_id}`;
    return `${ende.kabel_nr ?? 'Kabel'} · ${ende.soll_device_name}:${ende.soll_port}`;
  }
</script>

<details class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl">
  <summary class="flex items-center gap-2 min-h-11 px-4 cursor-pointer text-sm font-semibold text-[var(--color-text)] select-none">
    <History class="w-4 h-4 text-[var(--color-text3)]" />
    Ereignisprotokoll · {umbau.ereignisse.length} {umbau.ereignisse.length === 1 ? 'Eintrag' : 'Einträge'}
  </summary>
  <div class="border-t border-[var(--color-border)] max-h-96 overflow-y-auto">
    <table class="w-full text-xs">
      <thead>
        <tr class="text-left text-[10px] uppercase tracking-wider text-[var(--color-text3)] font-mono">
          <th class="px-4 py-2">Zeit</th>
          <th class="px-4 py-2">Wer</th>
          <th class="px-4 py-2">Was</th>
          <th class="px-4 py-2">Änderung</th>
        </tr>
      </thead>
      <tbody>
        {#each umbau.ereignisse as ereignis (ereignis.id)}
          <tr class="border-t border-[var(--color-border)]">
            <td class="px-4 py-1.5 whitespace-nowrap text-[var(--color-text2)]">{zeit(ereignis.zeitpunkt)}</td>
            <td class="px-4 py-1.5 text-[var(--color-text2)]">{ereignis.benutzer ?? '—'}</td>
            <td class="px-4 py-1.5 font-mono text-[var(--color-text)]">{gegenstand(ereignis)}</td>
            <td class="px-4 py-1.5 text-[var(--color-text2)]">
              {label(ereignis.von_status)} → {label(ereignis.nach_status)}
              {#if ereignis.grund}<span class="text-amber-400"> · {ereignis.grund}</span>{/if}
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</details>

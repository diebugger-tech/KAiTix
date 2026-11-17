<!--
  Anklemmen an einem anderen Port als im Soll: Auswahl Gerät + Port und Pflichtgrund.
  Das Soll bleibt unverändert; das Ende wird als „abweichend angeklemmt“ gebucht.
-->
<script lang="ts">
  import { untrack } from 'svelte';
  import type { Device } from '$lib/api';
  import type { UmbauEnde } from '$lib/umbauApi';
  import FensterKopf from './FensterKopf.svelte';
  import FensterFuss from './FensterFuss.svelte';

  let {
    ende,
    devices,
    onconfirm,
    onclose
  }: {
    ende: UmbauEnde;
    devices: Device[];
    /** Bucht das Anklemmen; wirft bei Ablehnung durch die API. */
    onconfirm: (eingabe: { ist_device_id: number | null; ist_port: string; grund: string }) => Promise<void>;
    onclose: () => void;
  } = $props();

  // Vorbelegt mit dem Soll (einmalig beim Öffnen): meist ändert sich nur der Port.
  let istDeviceId = $state<number | null>(untrack(() => ende.soll_device_id ?? null));
  let istPort = $state('');
  let grund = $state('');
  let busy = $state(false);
  let fehler = $state('');

  const gleichWieSoll = $derived(
    istDeviceId === (ende.soll_device_id ?? null) && istPort.trim() === ende.soll_port
  );
  const sperre = $derived(
    !istPort.trim()
      ? 'Port angeben.'
      : gleichWieSoll
        ? 'Das ist der Soll-Port. Dafür „Soll-Port“ antippen.'
        : !grund.trim()
          ? 'Grund angeben.'
          : null
  );

  async function buchen() {
    if (sperre) return;
    busy = true;
    fehler = '';
    try {
      await onconfirm({ ist_device_id: istDeviceId, ist_port: istPort.trim(), grund: grund.trim() });
      onclose();
    } catch (err) {
      fehler = err instanceof Error ? err.message : 'Buchung fehlgeschlagen.';
    } finally {
      busy = false;
    }
  }

  const feld =
    'w-full min-h-11 bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]';
  const label = 'block text-xs font-semibold text-[var(--color-text2)] mb-1';
</script>

<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl max-w-md w-full shadow-2xl overflow-hidden max-h-[92vh] flex flex-col">
    <FensterKopf titel="An anderem Port anklemmen" onclose={onclose} />
    <div class="px-5 pb-4 space-y-4 overflow-y-auto">
      <p class="text-sm text-[var(--color-text2)]">
        {ende.kabel_nr ?? 'Kabel'} · Soll:
        <span class="font-mono font-bold text-[var(--color-text)]">{ende.soll_device_name}:{ende.soll_port}</span>
      </p>
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label for="ap-geraet" class={label}>Gerät</label>
          <select id="ap-geraet" bind:value={istDeviceId} class={feld}>
            {#if ende.soll_device_id == null}
              <option value={null}>{ende.soll_device_name} (Soll)</option>
            {/if}
            {#each devices as d (d.id)}
              <option value={d.id}>{d.hostname}{d.id === ende.soll_device_id ? ' (Soll)' : ''}</option>
            {/each}
          </select>
        </div>
        <div>
          <label for="ap-port" class={label}>Port *</label>
          <input id="ap-port" type="text" maxlength="50" bind:value={istPort} placeholder={ende.soll_port} autocomplete="off" class={feld} />
        </div>
      </div>
      <div>
        <label for="ap-grund" class={label}>Grund der Abweichung *</label>
        <textarea
          id="ap-grund"
          bind:value={grund}
          rows="2"
          maxlength="255"
          placeholder="z. B. Port defekt, Gerät getauscht"
          class="w-full bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75] resize-none"
        ></textarea>
      </div>
      {#if fehler}
        <p role="alert" class="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">{fehler}</p>
      {/if}
    </div>
    <FensterFuss
      hauptLabel="Abweichend anklemmen"
      onhaupt={buchen}
      onabbrechen={onclose}
      gesperrt={!!sperre}
      grund={sperre}
      {busy}
    />
  </div>
</div>

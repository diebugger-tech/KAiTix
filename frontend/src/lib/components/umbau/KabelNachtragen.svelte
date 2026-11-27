<!--
  Im Rückbau ein Kabel aufnehmen, das nicht in der Kabelliste steht: Kabeltyp, beide
  Enden (bei Breakout n B-Enden), optional Nummer, Farbe, Länge und Bemerkung.
  Gespeichert wird nur im Umbau (POST /umbau/{id}/nachtraege), nicht in der Kabelliste.
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { api, type Device, type Kabeltyp } from '$lib/api';
  import { bEndenFuerTyp, type BEnde } from '$lib/kabel';
  import type { NachtragEingabe } from '$lib/umbauApi';
  import BreakoutEnden from '$lib/components/BreakoutEnden.svelte';
  import FensterKopf from './FensterKopf.svelte';
  import FensterFuss from './FensterFuss.svelte';

  let {
    devices,
    onconfirm,
    onclose
  }: {
    devices: Device[];
    /** Speichert den Nachtrag; wirft bei Ablehnung durch die API. */
    onconfirm: (eingabe: NachtragEingabe) => Promise<void>;
    onclose: () => void;
  } = $props();

  let kabeltypen = $state<Kabeltyp[]>([]);
  let ladeFehler = $state('');
  onMount(async () => {
    try {
      const alle = await api.getKabeltypen(true);
      // Strom gehört nicht zum Umbau; mehrere A-Enden unterstützt der Umbau nicht.
      kabeltypen = alle.filter(k => k.kategorie !== 'strom' && k.enden_a === 1);
    } catch (err) {
      ladeFehler = err instanceof Error ? err.message : 'Kabeltypen konnten nicht geladen werden.';
    }
  });

  let kabeltypId = $state<number | null>(null);
  let kabelNr = $state('');
  let farbe = $state('');
  let laenge = $state<number | null>(null);
  let bemerkung = $state('');
  let aDeviceId = $state<number | null>(null);
  let aPort = $state('');
  let bDeviceId = $state<number | null>(null);
  let bPort = $state('');
  let bEnden = $state<BEnde[]>([]);
  let busy = $state(false);
  let fehler = $state('');

  const kabeltyp = $derived(kabeltypen.find(k => k.id === kabeltypId) ?? null);
  const breakout = $derived((kabeltyp?.enden_b ?? 1) > 1);
  const sortierteGeraete = $derived(
    [...devices].sort((a, b) => a.hostname.localeCompare(b.hostname, 'de', { numeric: true }))
  );

  $effect(() => {
    // B-Zeilen folgen dem Kabeltyp; schon ausgefüllte Zeilen bleiben.
    const endenB = kabeltyp?.enden_b ?? 1;
    if (bEnden.length !== (endenB > 1 ? endenB : 0)) bEnden = bEndenFuerTyp(endenB, null, bEnden);
  });

  const bVollstaendig = $derived(
    breakout
      ? bEnden.every(e => e.nach_device_id !== null && e.nach_port.trim())
      : bDeviceId !== null && !!bPort.trim()
  );
  const sperre = $derived(
    kabeltypId === null
      ? 'Kabeltyp wählen.'
      : aDeviceId === null || !aPort.trim()
        ? 'A-Ende: Gerät und Port angeben.'
        : !bVollstaendig
          ? breakout
            ? 'Alle B-Enden mit Gerät und Port angeben.'
            : 'B-Ende: Gerät und Port angeben.'
          : null
  );

  async function speichern() {
    if (sperre || kabeltypId === null || aDeviceId === null) return;
    busy = true;
    fehler = '';
    const b = breakout
      ? bEnden.map(e => ({ device_id: e.nach_device_id as number, port: e.nach_port.trim() }))
      : [{ device_id: bDeviceId as number, port: bPort.trim() }];
    try {
      await onconfirm({
        kabeltyp_id: kabeltypId,
        kabel_nr: kabelNr.trim() || null,
        farbe: farbe.trim() || null,
        laenge_m: laenge && laenge > 0 ? laenge : null,
        bemerkung: bemerkung.trim() || null,
        a: { device_id: aDeviceId, port: aPort.trim() },
        b
      });
      onclose();
    } catch (err) {
      // z. B. 409 „… ist im Soll schon belegt“
      fehler = err instanceof Error ? err.message : 'Nachtragen fehlgeschlagen.';
    } finally {
      busy = false;
    }
  }

  const feld =
    'w-full min-h-11 bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]';
  const label = 'block text-xs font-semibold text-[var(--color-text2)] mb-1';
</script>

<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl max-w-lg w-full shadow-2xl overflow-hidden max-h-[92vh] flex flex-col">
    <FensterKopf titel="Unbekanntes Kabel nachtragen" onclose={onclose} />
    <form
      class="px-5 pb-4 space-y-4 overflow-y-auto"
      onsubmit={(e) => {
        e.preventDefault();
        void speichern();
      }}
      oninput={() => (fehler = '')}
    >
      <p class="text-xs text-[var(--color-text3)]">
        Für ein Kabel, das beim Abklemmen auftaucht und nicht in der Kabelliste steht. Es wird nur im
        Umbau festgehalten und muss danach abgeklemmt werden. In die Kabelliste kommt es nach dem
        Umbau von Hand.
      </p>
      {#if ladeFehler}
        <p role="alert" class="text-sm text-red-400">{ladeFehler}</p>
      {/if}

      <div class="grid grid-cols-[1fr_8rem] gap-3">
        <div>
          <label for="nt-typ" class={label}>Kabeltyp *</label>
          <select id="nt-typ" bind:value={kabeltypId} class={feld}>
            <option value={null} disabled>— Typ wählen —</option>
            {#each kabeltypen as k (k.id)}<option value={k.id}>{k.name}</option>{/each}
          </select>
        </div>
        <div>
          <label for="nt-nr" class={label}>Kabelnummer</label>
          <input id="nt-nr" type="text" maxlength="50" bind:value={kabelNr} placeholder="automatisch" autocomplete="off" class={feld} />
        </div>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <div>
          <label for="nt-a-geraet" class={label}>A-Ende: Gerät *</label>
          <select id="nt-a-geraet" bind:value={aDeviceId} class={feld}>
            <option value={null}>— Gerät —</option>
            {#each sortierteGeraete as d (d.id)}<option value={d.id}>{d.hostname}</option>{/each}
          </select>
        </div>
        <div>
          <label for="nt-a-port" class={label}>A-Ende: Port *</label>
          <input id="nt-a-port" type="text" maxlength="50" bind:value={aPort} placeholder="z. B. eth3" autocomplete="off" class={feld} />
        </div>
      </div>

      {#if breakout}
        <BreakoutEnden bind:enden={bEnden} devices={sortierteGeraete} idPrefix="nt-b-ende" />
      {:else}
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="nt-b-geraet" class={label}>B-Ende: Gerät *</label>
            <select id="nt-b-geraet" bind:value={bDeviceId} class={feld}>
              <option value={null}>— Gerät —</option>
              {#each sortierteGeraete as d (d.id)}<option value={d.id}>{d.hostname}</option>{/each}
            </select>
          </div>
          <div>
            <label for="nt-b-port" class={label}>B-Ende: Port *</label>
            <input id="nt-b-port" type="text" maxlength="50" bind:value={bPort} placeholder="z. B. Gi1/0/9" autocomplete="off" class={feld} />
          </div>
        </div>
      {/if}

      <div class="grid grid-cols-2 gap-3">
        <div>
          <label for="nt-farbe" class={label}>Farbe</label>
          <input id="nt-farbe" type="text" maxlength="30" bind:value={farbe} autocomplete="off" class={feld} />
        </div>
        <div>
          <label for="nt-laenge" class={label}>Länge (m)</label>
          <input id="nt-laenge" type="number" min="0" step="0.1" bind:value={laenge} class={feld} />
        </div>
      </div>

      <div>
        <label for="nt-bemerkung" class={label}>Bemerkung</label>
        <input
          id="nt-bemerkung"
          type="text"
          maxlength="200"
          bind:value={bemerkung}
          placeholder="z. B. lag hinter dem Kabelkanal"
          autocomplete="off"
          class={feld}
        />
      </div>

      {#if fehler}
        <p role="alert" class="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">{fehler}</p>
      {/if}
      <button type="submit" class="hidden" tabindex="-1" aria-hidden="true">Nachtragen</button>
    </form>
    <FensterFuss hauptLabel="Nachtragen" onhaupt={speichern} onabbrechen={onclose} gesperrt={!!sperre} grund={sperre} {busy} />
  </div>
</div>

<!--
  Kabel in der Erfassung hinzufügen: Kabeltyp aus dem Katalog (letzte Wahl vorbelegt),
  eigener Port mit Vorschlägen, Gegenstelle Gerät + Port, bei Breakout n B-Zeilen.
  Gespeichert wird über /cables. Das Fenster bleibt offen, damit Port für Port erfasst
  werden kann.
-->
<script lang="ts">
  import { api, type Cable, type Device, type Kabeltyp } from '$lib/api';
  import { bEndenFuerTyp, straengeAusEnden, genutztePorts, type BEnde } from '$lib/kabel';
  import BreakoutEnden from '$lib/components/BreakoutEnden.svelte';
  import FensterKopf from './FensterKopf.svelte';
  import FensterFuss from './FensterFuss.svelte';

  const LETZTER_TYP = 'kaitix_umbau_kabeltyp';

  let {
    geraet,
    devices,
    kabeltypen,
    cables,
    onsaved,
    onclose
  }: {
    geraet: { device_id: number; hostname: string };
    devices: Device[];
    /** Aktive Kabeltypen ohne Strom. */
    kabeltypen: Kabeltyp[];
    cables: Cable[];
    onsaved: (cable: Cable) => Promise<void> | void;
    onclose: () => void;
  } = $props();

  function letzterTyp(): number | null {
    try {
      const gespeichert = Number(localStorage.getItem(LETZTER_TYP));
      if (kabeltypen.some(k => k.id === gespeichert)) return gespeichert;
    } catch {
      // localStorage nicht verfügbar: ohne Vorbelegung weiter
    }
    return kabeltypen[0]?.id ?? null;
  }

  let kabeltypId = $state<number | null>(letzterTyp());
  let vonPort = $state('');
  let nachDeviceId = $state<number | null>(null);
  let nachPort = $state('');
  let laenge = $state<number | null>(1);
  let bEnden = $state<BEnde[]>([]);
  let saving = $state(false);
  let fehler = $state('');
  let gespeichert = $state('');

  const kabeltyp = $derived(kabeltypen.find(k => k.id === kabeltypId) ?? null);
  const breakout = $derived((kabeltyp?.enden_b ?? 1) > 1);
  const andereGeraete = $derived(devices.filter(d => d.id !== geraet.device_id));

  $effect(() => {
    // B-Zeilen folgen dem gewählten Kabeltyp; schon ausgefüllte Zeilen bleiben.
    const endenB = kabeltyp?.enden_b ?? 1;
    if (bEnden.length !== (endenB > 1 ? endenB : 0)) bEnden = bEndenFuerTyp(endenB, null, bEnden);
  });

  // Vorschläge: Interfaces des Geräts (falls vorhanden) plus schon genutzte Port-Strings.
  let interfaces = $state<Record<number, string[]>>({});
  async function ladeInterfaces(deviceId: number | null) {
    if (deviceId === null || interfaces[deviceId]) return;
    try {
      const ports = await api.getDevicePorts(deviceId);
      interfaces = { ...interfaces, [deviceId]: ports.map(p => p.port_name) };
    } catch {
      interfaces = { ...interfaces, [deviceId]: [] };
    }
  }
  $effect(() => {
    void ladeInterfaces(geraet.device_id);
  });
  $effect(() => {
    void ladeInterfaces(nachDeviceId);
  });

  function vorschlaege(deviceId: number | null): { port: string; belegt: boolean }[] {
    if (deviceId === null) return [];
    const belegt = genutztePorts(cables, deviceId);
    const alle = new Set([...(interfaces[deviceId] ?? []), ...belegt]);
    return [...alle]
      .sort((a, b) => a.localeCompare(b, 'de', { numeric: true }))
      .map(port => ({ port, belegt: belegt.has(port) }));
  }
  const eigeneVorschlaege = $derived(vorschlaege(geraet.device_id));
  const zielVorschlaege = $derived(vorschlaege(nachDeviceId));

  const sperre = $derived(
    kabeltypId === null ? 'Kabeltyp wählen.' : !vonPort.trim() ? 'Eigenen Port angeben.' : null
  );

  async function speichern() {
    if (sperre || kabeltypId === null) return;
    saving = true;
    fehler = '';
    gespeichert = '';
    try {
      const cable = await api.createCable({
        kabeltyp_id: kabeltypId,
        laenge_m: laenge ?? 1,
        von_device_id: geraet.device_id,
        von_port: vonPort.trim(),
        // Breakout: die B-Enden stehen an den Strängen, das Ziel am Kabel bleibt leer
        nach_device_id: breakout ? undefined : nachDeviceId ?? undefined,
        nach_port: breakout ? undefined : nachPort.trim() || undefined,
        ...(breakout ? { straenge: straengeAusEnden(bEnden) } : {})
      });
      try {
        localStorage.setItem(LETZTER_TYP, String(kabeltypId));
      } catch {
        // ohne Merken weiter
      }
      gespeichert = `${cable.kabel_nr} gespeichert: ${geraet.hostname}:${cable.von_port}`;
      // Für das nächste Kabel: Typ bleibt, Ports leeren.
      vonPort = '';
      nachDeviceId = null;
      nachPort = '';
      bEnden = bEndenFuerTyp(kabeltyp?.enden_b ?? 1);
      await onsaved(cable);
    } catch (err) {
      // z. B. 409 „Port … ist bereits durch Kabel … belegt“ aus der Belegungsprüfung
      fehler = err instanceof Error ? err.message : 'Speichern fehlgeschlagen.';
    } finally {
      saving = false;
    }
  }

  const feld =
    'w-full min-h-11 bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]';
  const label = 'block text-xs font-semibold text-[var(--color-text2)] mb-1';
</script>

<div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl max-w-lg w-full shadow-2xl overflow-hidden max-h-[92vh] flex flex-col">
    <FensterKopf titel="Kabel hinzufügen · {geraet.hostname}" onclose={onclose} />
    <form
      class="px-5 pb-4 space-y-4 overflow-y-auto"
      onsubmit={(e) => {
        e.preventDefault();
        void speichern();
      }}
      oninput={() => {
        // Eine alte Fehlermeldung gilt nicht mehr, sobald weiter getippt wird.
        fehler = '';
      }}
    >
      <div class="grid grid-cols-[1fr_6.5rem] gap-3">
        <div>
          <label for="erf-typ" class={label}>Kabeltyp *</label>
          <select id="erf-typ" bind:value={kabeltypId} class={feld}>
            <option value={null} disabled>— Typ wählen —</option>
            {#each kabeltypen as k (k.id)}<option value={k.id}>{k.name}</option>{/each}
          </select>
        </div>
        <div>
          <label for="erf-laenge" class={label}>Länge (m)</label>
          <input id="erf-laenge" type="number" min="0" step="0.1" bind:value={laenge} class={feld} />
        </div>
      </div>

      <div>
        <label for="erf-von-port" class={label}>Port an {geraet.hostname} *</label>
        <!-- svelte-ignore a11y_autofocus -->
        <input
          id="erf-von-port"
          type="text"
          maxlength="50"
          autofocus
          bind:value={vonPort}
          list="erf-von-ports"
          placeholder="z. B. eth0"
          autocomplete="off"
          class={feld}
        />
        <datalist id="erf-von-ports">
          {#each eigeneVorschlaege as v (v.port)}<option value={v.port} label={v.belegt ? 'belegt' : ''}></option>{/each}
        </datalist>
      </div>

      {#if breakout}
        <BreakoutEnden bind:enden={bEnden} devices={andereGeraete} idPrefix="erf-b-ende" />
      {:else}
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="erf-nach-geraet" class={label}>Gegenstelle: Gerät</label>
            <select id="erf-nach-geraet" bind:value={nachDeviceId} class={feld}>
              <option value={null}>— Gerät —</option>
              {#each andereGeraete as d (d.id)}<option value={d.id}>{d.hostname}</option>{/each}
            </select>
          </div>
          <div>
            <label for="erf-nach-port" class={label}>Gegenstelle: Port</label>
            <input
              id="erf-nach-port"
              type="text"
              maxlength="50"
              bind:value={nachPort}
              list="erf-nach-ports"
              placeholder="z. B. Gi1/0/1"
              autocomplete="off"
              class={feld}
            />
            <datalist id="erf-nach-ports">
              {#each zielVorschlaege as v (v.port)}<option value={v.port} label={v.belegt ? 'belegt' : ''}></option>{/each}
            </datalist>
          </div>
        </div>
      {/if}

      {#if fehler}
        <p role="alert" class="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">{fehler}</p>
      {/if}
      {#if gespeichert}
        <p role="status" class="text-sm text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 rounded-lg px-3 py-2">{gespeichert}</p>
      {/if}
      <!-- Enter im Formular speichert -->
      <button type="submit" class="hidden" tabindex="-1" aria-hidden="true">Speichern</button>
    </form>
    <FensterFuss
      hauptLabel="Speichern"
      onhaupt={speichern}
      abbrechenLabel="Fertig"
      onabbrechen={onclose}
      gesperrt={!!sperre}
      grund={sperre}
      busy={saving}
    />
  </div>
</div>

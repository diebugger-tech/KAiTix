<!--
  Druckliste des Umbaus: alle Enden nach Rack und Gerät, mit Soll-Port, Gegenseite,
  Kabel, Position, Länge und Abhakfeldern für Abklemmen und Anklemmen. Zeigt den Stand
  zum Druckzeitpunkt: vor dem Rückbau als Arbeitsliste, nach dem Abschluss als Nachweis
  Soll gegen Ist. Nur für den Druck (print-only), Muster wie RunbookPrint.svelte.
-->
<script lang="ts">
  import { STATUS_LABEL, zeit, type UmbauDetail, type UmbauEnde } from '$lib/umbauApi';

  let { umbau }: { umbau: UmbauDetail } = $props();

  interface Gruppe {
    rack: string;
    geraet: string;
    position: string | null;
    enden: UmbauEnde[];
  }

  const gruppen = $derived.by(() => {
    const nach = new Map<string, Gruppe>();
    for (const e of umbau.enden) {
      const rack = e.soll_rack_name ?? 'Ohne Rack';
      const schluessel = `${rack}\u0000${e.soll_device_name}`;
      const g = nach.get(schluessel) ?? { rack, geraet: e.soll_device_name, position: e.soll_position ?? null, enden: [] };
      g.enden.push(e);
      nach.set(schluessel, g);
    }
    const liste = [...nach.values()].sort(
      (a, b) => a.rack.localeCompare(b.rack, 'de', { numeric: true }) || a.geraet.localeCompare(b.geraet, 'de', { numeric: true })
    );
    for (const g of liste) g.enden.sort((a, b) => a.soll_port.localeCompare(b.soll_port, 'de', { numeric: true }));
    return liste;
  });
  const racks = $derived([...new Set(gruppen.map(g => g.rack))]);
  const nachtraege = $derived(new Set(umbau.enden.filter(e => e.nachtrag_nr != null).map(e => e.nachtrag_nr)).size);

  const abgeklemmt = (e: UmbauEnde) => e.status !== 'gesteckt';
  const angeklemmt = (e: UmbauEnde) => e.status === 'angeklemmt' || e.status === 'angeklemmt_abweichend';
  const laenge = (e: UmbauEnde) => (e.laenge_m != null ? `${e.laenge_m.toLocaleString('de-DE')} m` : '');
  const gedruckt = new Date().toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' });
</script>

<div class="umbau-druck">
  <h1>Umbau: {umbau.name}</h1>
  <p class="kopf">
    Racks: {umbau.racks.map(r => r.name).join(', ')} · Status: {STATUS_LABEL[umbau.status]}
    · eingefroren {zeit(umbau.eingefroren_am)}{umbau.eingefroren_von ? ` von ${umbau.eingefroren_von}` : ''}
    · gedruckt {gedruckt}
  </p>
  <p class="kopf">
    {umbau.fortschritt.enden_gesamt} Enden · {umbau.fortschritt.abgeklemmt + umbau.fortschritt.angeklemmt} abgeklemmt
    · {umbau.fortschritt.angeklemmt} angeklemmt{umbau.fortschritt.abweichend ? `, davon ${umbau.fortschritt.abweichend} abweichend` : ''}
    {#if nachtraege}· {nachtraege} nachgetragene{nachtraege === 1 ? 's Kabel' : ' Kabel'} (nicht in der Kabelliste){/if}
  </p>

  {#each racks as rack (rack)}
    <h2>{rack}</h2>
    {#each gruppen.filter(g => g.rack === rack) as g (g.geraet)}
      <table>
        <caption>{g.geraet}{g.position ? ` · ${g.position}` : ''}</caption>
        <thead>
          <tr>
            <th class="port">Port (Soll)</th>
            <th>Gegenseite</th>
            <th>Kabel</th>
            <th>Typ · Farbe · Länge</th>
            <th class="haken">Ab</th>
            <th class="haken">An</th>
            <th class="ist">Ist / Bemerkung</th>
          </tr>
        </thead>
        <tbody>
          {#each g.enden as e (e.id)}
            <tr>
              <td class="port mono">{e.soll_port}</td>
              <td class="mono">{e.gegenseite.join(', ') || '—'}</td>
              <td class="mono">{e.kabel_nr ?? '—'}{e.nachtrag_nr != null ? ' (NT)' : ''}</td>
              <td>{[e.kabeltyp_name, e.farbe, laenge(e)].filter(Boolean).join(' · ')}</td>
              <td class="haken">{abgeklemmt(e) ? '☑' : '☐'}</td>
              <td class="haken">{angeklemmt(e) ? '☑' : '☐'}</td>
              <td class="ist">
                {#if e.status === 'angeklemmt_abweichend'}
                  <span class="mono">{e.ist_device_name}:{e.ist_port}</span> · {e.abweichung_grund}
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/each}
  {/each}

  <p class="unterschrift">
    Rückbau geprüft: ______________________ Datum: __________
    &nbsp;&nbsp; Wiederaufbau geprüft: ______________________ Datum: __________
  </p>
  <p class="fuss">NT = im Rückbau nachgetragen, nicht in der Kabelliste. ☑ = in KAiTix gebucht.</p>
</div>

<style>
  .umbau-druck {
    color: #000;
    background: #fff;
    font-family: system-ui, sans-serif;
    font-size: 9pt;
  }
  h1 {
    font-size: 14pt;
    margin: 0 0 2mm;
  }
  h2 {
    font-size: 11pt;
    margin: 5mm 0 1mm;
    border-bottom: 1px solid #000;
  }
  .kopf {
    margin: 0 0 1mm;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 0 0 3mm;
    page-break-inside: avoid;
  }
  caption {
    text-align: left;
    font-weight: bold;
    padding: 1mm 0;
  }
  th,
  td {
    border: 1px solid #888;
    padding: 1mm 1.5mm;
    text-align: left;
    vertical-align: top;
  }
  th {
    background: #eee;
    font-size: 8pt;
  }
  .mono {
    font-family: ui-monospace, monospace;
  }
  .port {
    width: 18%;
    font-weight: bold;
  }
  .haken {
    width: 6%;
    text-align: center;
    font-size: 11pt;
  }
  .ist {
    width: 22%;
  }
  .unterschrift {
    margin-top: 8mm;
  }
  .fuss {
    font-size: 8pt;
    color: #444;
  }
</style>

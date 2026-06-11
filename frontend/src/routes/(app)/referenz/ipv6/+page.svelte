<!--
  NUR-DOKU-VERMERK:
  Diese Seite ist ein Benennungs-/Merkschema für Menschen, die die Doku lesen. 
  Keine Adresse wird geroutet, validiert, aufgelöst oder erreicht. 
  Keine IP-Validierung gegen echte Netze, keine externen Calls.
-->
<script lang="ts">
  import { ipv6Categories, ipv6UlaExample, ipv6VlanExample } from '$lib/ipv6Schema';
  import { Info, BookOpen, AlertCircle, CheckCircle2 } from '@lucide/svelte';
</script>

<div class="max-w-4xl mx-auto space-y-8 pb-12">
  <div>
    <h1 class="text-3xl font-bold font-outfit tracking-tight text-[var(--color-text)] flex items-center gap-3">
      <BookOpen class="w-8 h-8 text-[#5DCAA5]" />
      Referenz: IPv6 Namensschema
    </h1>
    <p class="text-[var(--color-text2)] mt-2 text-sm max-w-2xl">
      Dieses Dokument standardisiert die Vergabe von IPv6-Adressen im Rechenzentrums-Betrieb. Es definiert ein pragmatisches, leicht merkbares Schema, das den Betrieb und das Troubleshooting über mehrere Standorte und Firmen hinweg erleichtert.
    </p>
  </div>

  <div class="text-[var(--color-text2)] text-sm mb-6">
    <h3 class="font-bold text-[var(--color-text)]">Hinweis: DNS First</h3>
    <p>
      Für den täglichen Zugriff (SSH, Web-UIs, API-Calls) sollte <strong>immer auf DNS (Aliasnamen) gesetzt werden</strong>. Nutze IP-Adressen direkt nur da, wo es systembedingt zwingend erforderlich ist.
    </p>
  </div>

  <!-- A: Aufbau -->
  <section class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-6 shadow-sm">
    <h2 class="text-xl font-bold text-[var(--color-text)] mb-4 flex items-center gap-2">
      <div class="w-6 h-6 rounded bg-emerald-500/20 text-emerald-500 flex items-center justify-center text-xs font-bold">A</div>
      Aufbau einer IPv6 Adresse
    </h2>
    <p class="text-sm text-[var(--color-text2)] mb-4">
      Eine IPv6 Adresse besteht aus 128 Bit, unterteilt in 8 Blöcke (Hextets) à 16 Bit. In der Praxis trennen wir sie genau in der Mitte: 
      <strong>64 Bit Präfix</strong> (Netzwerk-Routing) und <strong>64 Bit Interface Identifier (IID)</strong> (Geräte-Identität).
    </p>
    <div class="bg-[var(--color-bg3)] border border-[var(--color-border)] rounded-lg p-4 font-mono text-sm text-center mb-4 overflow-x-auto">
      <span class="text-blue-400">2001:db8:0:10</span><span class="text-[var(--color-text3)]">::</span><span class="text-emerald-400">1:42</span>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
      <div class="border border-blue-500/30 bg-blue-500/5 rounded-lg p-3">
        <h3 class="font-bold text-blue-400 mb-1">Präfix (Erste 64 Bit)</h3>
        <p class="text-[var(--color-text2)] text-xs">Bestimmt durch das Routing/Provider oder als lokales Netz. Enthält in unserem Schema immer die VLAN-ID (z.B. im 4. Block das `10` für VLAN 10).</p>
      </div>
      <div class="border border-emerald-500/30 bg-emerald-500/5 rounded-lg p-3">
        <h3 class="font-bold text-emerald-400 mb-1">IID (Letzte 64 Bit)</h3>
        <p class="text-[var(--color-text2)] text-xs">Frei vergebbare Geräte-ID. Hier wenden wir unsere Namenskonvention an (Kategorie, Host-Nr., Rack-Position). <strong>Die IID bleibt immer konstant!</strong></p>
      </div>
    </div>
  </section>

  <!-- B: Präfix Typen -->
  <section class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-6 shadow-sm">
    <h2 class="text-xl font-bold text-[var(--color-text)] mb-4 flex items-center gap-2">
      <div class="w-6 h-6 rounded bg-blue-500/20 text-blue-500 flex items-center justify-center text-xs font-bold">B</div>
      Präfix-Typen (Netzwerke)
    </h2>
    <div class="overflow-x-auto">
      <table class="w-full text-left text-sm">
        <thead class="text-xs uppercase bg-[var(--color-bg3)] text-[var(--color-text2)]">
          <tr>
            <th class="px-4 py-3 rounded-tl-lg">Präfix</th>
            <th class="px-4 py-3">Typ</th>
            <th class="px-4 py-3 rounded-tr-lg">Verwendung in KAiTix & RZ</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-[var(--color-border)]">
          <tr>
            <td class="px-4 py-3 font-mono text-emerald-400">fd00::/8</td>
            <td class="px-4 py-3 font-semibold">ULA (Unique Local)</td>
            <td class="px-4 py-3 text-[var(--color-text2)] text-xs">Selbstvergebenes, internes Netz (wie 10.0.0.0/8 in IPv4). Hauptnetz für interne Server/Management. <br><span class="opacity-70 italic">Hinweis: Echtes ULA erfordert eine Zufalls-ID (z.B. fd3c:9a2e:1f04::), wir nutzen fd00:: als vereinfachtes Synonym in der Konvention.</span></td>
          </tr>
          <tr>
            <td class="px-4 py-3 font-mono text-blue-400">2000::/3</td>
            <td class="px-4 py-3 font-semibold">GUA (Global Unicast)</td>
            <td class="px-4 py-3 text-[var(--color-text2)] text-xs">Weltweit routbar (öffentliche IPs). Kommt vom Provider. GUA-Präfixe können sich ändern, die IID-Geräte-Nummer bleibt bestehen.</td>
          </tr>
          <tr>
            <td class="px-4 py-3 font-mono text-orange-400">fe80::/10</td>
            <td class="px-4 py-3 font-semibold">Link-Local</td>
            <td class="px-4 py-3 text-[var(--color-text2)] text-xs">Gilt nur auf dem physischen Kabel/Switchport. <strong>Wird niemals als Geräte-Identität dokumentiert!</strong></td>
          </tr>
          <tr>
            <td class="px-4 py-3 font-mono text-purple-400">2001:db8::/32</td>
            <td class="px-4 py-3 font-semibold">Dokumentation</td>
            <td class="px-4 py-3 text-[var(--color-text2)] text-xs">RFC 3849 reservierter Bereich. Wird in dieser Doku für alle Beispiele verwendet.</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>

  <!-- C: Kategorie-Schema -->
  <section class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-6 shadow-sm">
    <h2 class="text-xl font-bold text-[var(--color-text)] mb-4 flex items-center gap-2">
      <div class="w-6 h-6 rounded bg-[#5DCAA5]/20 text-[#5DCAA5] flex items-center justify-center text-xs font-bold">C</div>
      Kategorie-Schema (IID Struktur)
    </h2>
    <p class="text-sm text-[var(--color-text2)] mb-4">
      Um IP-Konflikte zu vermeiden und Adressen logisch zuzuordnen, starten wir den Identifier (IID) direkt nach dem <code>::</code> mit einer Kategorie-Ziffer.
    </p>

    <div class="grid gap-3 mb-6">
      {#each ipv6Categories as cat}
        <div class="flex flex-col sm:flex-row sm:items-center gap-3 p-3 bg-[var(--color-bg3)] border border-[var(--color-border)] rounded-lg">
          <div class="flex-shrink-0 w-16 text-center font-mono text-lg font-bold text-[#5DCAA5]">
            ::{cat.prefix}:
          </div>
          <div class="flex-1">
            <h4 class="font-bold text-[var(--color-text)] text-sm">{cat.name}</h4>
            <p class="text-xs text-[var(--color-text2)] mt-0.5">{cat.description}</p>
          </div>
          <div class="flex-shrink-0 bg-[var(--color-bg2)] px-3 py-1.5 rounded border border-[var(--color-border2)] font-mono text-xs text-[var(--color-text3)]">
            {ipv6VlanExample}{cat.prefix}:<span class="text-[var(--color-text)]">xxxx</span>
          </div>
        </div>
      {/each}
      
      <div class="flex flex-col sm:flex-row sm:items-center gap-3 p-3 bg-blue-500/5 border border-blue-500/20 rounded-lg">
          <div class="flex-shrink-0 w-16 text-center font-mono text-lg font-bold text-blue-400">
            ::[Port]
          </div>
          <div class="flex-1">
            <h4 class="font-bold text-[var(--color-text)] text-sm">Zentrale Infrastruktur-Dienste</h4>
            <p class="text-xs text-[var(--color-text2)] mt-0.5">Sonderfall für globale Dienste, basierend auf Standard-Ports.</p>
          </div>
          <div class="flex-shrink-0 text-xs text-[var(--color-text3)] space-y-1">
            <div><code class="font-mono bg-[var(--color-bg2)] px-1 py-0.5 rounded text-blue-400">::53</code> DNS</div>
            <div><code class="font-mono bg-[var(--color-bg2)] px-1 py-0.5 rounded text-blue-400">::123</code> NTP</div>
            <div><code class="font-mono bg-[var(--color-bg2)] px-1 py-0.5 rounded text-blue-400">::389</code> LDAP</div>
          </div>
        </div>
    </div>

    <div class="mt-6 border-t border-[var(--color-border)] pt-4">
      <h3 class="font-bold text-[var(--color-text)] mb-3 text-sm flex items-center gap-2">
        <Info class="w-4 h-4 text-[#5DCAA5]" /> Pragmatische Vergabe-Muster für den IID
      </h3>
      <div class="grid grid-cols-1 gap-4">
        <div class="p-3 bg-[var(--color-bg3)] rounded-lg">
          <strong class="text-xs block mb-1">Dual-Stack (Die IPv4 Eselsbrücke)</strong>
          <p class="text-xs text-[var(--color-text2)] mb-2">Die letzte Stelle der alten IPv4 Adresse wird als Hex-String übernommen.</p>
          <code class="text-[10px] bg-[var(--color-bg2)] px-1.5 py-0.5 rounded border border-[var(--color-border)]">10.50.1.125 &rarr; 2001:db8:0:10::1:125</code>
          <p class="text-[10px] text-orange-400/90 mt-2">
            <strong>Achtung:</strong> Reine String-Merkhilfe, keine numerische Gleichheit! <code>::1:125</code> liest sich wie 125, ist als Hextet aber dezimal 293. (Gilt ab <code>::1:10</code> = 16)
          </p>
        </div>
      </div>
    </div>
  </section>

  <!-- D & E: Syntax & Kurzschreibung -->
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <section class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-6 shadow-sm">
      <h2 class="text-xl font-bold text-[var(--color-text)] mb-4 flex items-center gap-2">
        <div class="w-6 h-6 rounded bg-orange-500/20 text-orange-500 flex items-center justify-center text-xs font-bold">D</div>
        Hex-Typografie & Sprechende IPs
      </h2>
      <p class="text-sm text-[var(--color-text2)] mb-3">
        IPv6 nutzt das hexadezimale System (0-9, a-f). Das erlaubt es, native Hex-Buchstaben (a-f) und "Leet"-Ziffern (0=O, 1=I/L, 5=S, 7=T) zu Wörtern ("Hexspeak") zu kombinieren. <br />
        <span class="text-xs text-[var(--color-text3)]">Achtung: M, N, K, P, R, U, V, W, X, Y, Z, H, J sind nicht darstellbar.</span>
      </p>
      
      <div class="overflow-x-auto mb-4 border border-[var(--color-border)] rounded-lg">
        <table class="w-full text-left text-sm border-collapse">
          <thead class="text-xs uppercase bg-[var(--color-bg3)] text-[var(--color-text2)]">
            <tr>
              <th class="px-3 py-2 rounded-tl-lg">Zweck</th>
              <th class="px-3 py-2">Suffix</th>
              <th class="px-3 py-2 rounded-tr-lg">Gelesen als</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-[var(--color-border)]">
            <tr><td class="px-3 py-2 font-medium">Storage/NAS</td><td class="px-3 py-2 font-mono text-emerald-400">::da7a</td><td class="px-3 py-2 text-[var(--color-text2)] text-xs">DATA</td></tr>
            <tr><td class="px-3 py-2 font-medium">Webserver</td><td class="px-3 py-2 font-mono text-emerald-400">::443</td><td class="px-3 py-2 text-[var(--color-text2)] text-xs">Port 443</td></tr>
          </tbody>
        </table>
      </div>

      <div class="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg text-xs text-amber-500/90 flex gap-2">
        <AlertCircle class="w-4 h-4 shrink-0" />
        <p>
          <strong>Funktional vs. Humor:</strong> Obige funktionale Begriffe sind als "Profi-Trick" für globale Dienste sehr empfehlenswert. Wir verzichten im professionellen Umfeld jedoch auf reinen Nerd-Humor (wie <code>:babe:</code> oder <code>:dead:</code>) für Produktivsysteme.
        </p>
      </div>
    </section>

    <section class="bg-[var(--color-bg2)] border border-[var(--color-border)] rounded-xl p-6 shadow-sm">
      <h2 class="text-xl font-bold text-[var(--color-text)] mb-4 flex items-center gap-2">
        <div class="w-6 h-6 rounded bg-pink-500/20 text-pink-500 flex items-center justify-center text-xs font-bold">E</div>
        Kurzschreibung (RFC 5952)
      </h2>
      <p class="text-sm text-[var(--color-text2)] mb-3">
        Damit Datenbanken (und unser CSV-Import) Adressen korrekt zusammenführen können, müssen wir sie immer in der kürzesten kanonischen Form schreiben:
      </p>
      <ul class="text-sm space-y-3 text-[var(--color-text2)]">
        <li class="flex items-start gap-2">
          <CheckCircle2 class="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
          <div><strong>Führende Nullen entfallen:</strong> <br><code class="font-mono bg-[var(--color-bg3)] px-1 text-xs">0010</code> &rarr; <code class="font-mono bg-[var(--color-bg3)] px-1 text-xs">10</code></div>
        </li>
        <li class="flex items-start gap-2">
          <CheckCircle2 class="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
          <div><strong>Null-Blöcke kürzen:</strong> Ein zusammenhängender Bereich von Nullen wird <strong class="underline">einmalig</strong> durch <code>::</code> ersetzt. <br><code class="font-mono bg-[var(--color-bg3)] px-1 text-[10px] break-all">2001:db8:0:0:0:0:0:1</code> &rarr; <code class="font-mono bg-[var(--color-bg3)] px-1 text-xs break-all">2001:db8::1</code></div>
        </li>
        <li class="flex items-start gap-2">
          <CheckCircle2 class="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
          <div><strong>Konsequent kleingeschrieben:</strong> <br>Immer <code>a-f</code>, niemals <code>A-F</code>.</div>
        </li>
      </ul>
    </section>
  </div>
</div>

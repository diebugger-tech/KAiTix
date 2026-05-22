with open("frontend/src/routes/eplan/+page.svelte", "r") as f:
    content = f.read()

# Generate Blatt 2 SVG
blatt2_svg = """
      <!-- BLATT 2: Verteilung -->
      <div class="bg-white border-2 border-slate-300 rounded shadow-inner p-4 w-full flex justify-center mt-8" style="min-height: 800px;">
        <svg viewBox="0 0 1000 700" class="w-full max-w-[1200px] h-auto drop-shadow-sm font-sans" shape-rendering="crispEdges">
          
          <!-- Outer Frame -->
          <rect x="20" y="20" width="960" height="660" fill="none" stroke="#334155" stroke-width="2" />
          
          <!-- Grid -->
          {#each Array(10) as _, i}
            <line x1={20 + (i * 96)} y1="15" x2={20 + (i * 96)} y2="25" stroke="#94a3b8" stroke-width="1" />
            <text x={68 + (i * 96)} y="15" font-size="10" fill="#94a3b8" text-anchor="middle">{i}</text>
          {/each}
          {#each Array(6) as _, i}
            <line x1="15" y1={20 + (i * 110)} x2="25" y2={20 + (i * 110)} stroke="#94a3b8" stroke-width="1" />
            <text x="10" y={75 + (i * 110)} font-size="10" fill="#94a3b8" text-anchor="end">{String.fromCharCode(65 + i)}</text>
          {/each}

          <!-- Title Block -->
          <g transform="translate(680, 580)">
            <rect x="0" y="0" width="300" height="100" fill="none" stroke="#334155" stroke-width="2" />
            <line x1="0" y1="20" x2="300" y2="20" stroke="#334155" stroke-width="1" />
            <line x1="0" y1="40" x2="300" y2="40" stroke="#334155" stroke-width="1" />
            <line x1="0" y1="80" x2="300" y2="80" stroke="#334155" stroke-width="1" />
            <line x1="100" y1="0" x2="100" y2="40" stroke="#334155" stroke-width="1" />
            <line x1="200" y1="80" x2="200" y2="100" stroke="#334155" stroke-width="1" />
            <line x1="250" y1="80" x2="250" y2="100" stroke="#334155" stroke-width="1" />
            
            <text x="5" y="14" font-size="9" fill="#64748b">Datum</text><text x="40" y="14" font-size="10" fill="#0f172a" font-weight="bold">2026-05-22</text>
            <text x="105" y="14" font-size="9" fill="#64748b">Bearbeiter</text><text x="155" y="14" font-size="10" fill="#0f172a" font-weight="bold">Andreas</text>
            <text x="5" y="34" font-size="9" fill="#64748b">Geprüft</text>
            <text x="105" y="34" font-size="9" fill="#64748b">Norm</text><text x="155" y="34" font-size="10" fill="#0f172a">EN 61082-1</text>
            
            <text x="5" y="55" font-size="11" fill="#64748b">Projektbezeichnung:</text>
            <text x="5" y="72" font-size="16" fill="#0f172a" font-weight="bold">KAiTix ServerFlow</text>
            <text x="5" y="94" font-size="11" fill="#0f172a">Anlage: UV-USV-01 (Verteilung)</text>
            <text x="205" y="94" font-size="10" fill="#64748b">Blatt:</text><text x="235" y="94" font-size="11" fill="#0f172a" font-weight="bold">2</text>
            <text x="255" y="94" font-size="10" fill="#64748b">V.Bl.:</text><text x="285" y="94" font-size="11" fill="#0f172a">1</text>
          </g>

          <g stroke-linecap="round" stroke-linejoin="round">
            <text x="30" y="65" font-size="10" font-style="italic" fill="#64748b">Von Blatt 1</text>
            
            <!-- Busbars -->
            <g stroke-width="1.5">
              <line x1="50" y1="80" x2="950" y2="80" stroke="#78350f" /> <text x="35" y="83" font-size="10" fill="#78350f" font-weight="bold">L1</text>
              <line x1="50" y1="100" x2="950" y2="100" stroke="#0f172a" /> <text x="35" y="103" font-size="10" fill="#0f172a" font-weight="bold">L2</text>
              <line x1="50" y1="120" x2="950" y2="120" stroke="#475569" /> <text x="35" y="123" font-size="10" fill="#475569" font-weight="bold">L3</text>
              <line x1="50" y1="140" x2="950" y2="140" stroke="#2563eb" /> <text x="35" y="143" font-size="10" fill="#2563eb" font-weight="bold">N</text>
              <line x1="50" y1="160" x2="950" y2="160" stroke="#16a34a" stroke-dasharray="8,4" /> <text x="35" y="163" font-size="10" fill="#16a34a" font-weight="bold">PE</text>
            </g>
"""

# Generate 7 branches
for i in range(1, 8):
    x_offset = 50 + (i * 120)

    blatt2_svg += f"""
            <!-- Branch {i} -->
            <circle cx="{x_offset}" cy="80" r="2.5" fill="#78350f"/>
            <circle cx="{x_offset + 10}" cy="100" r="2.5" fill="#0f172a"/>
            <circle cx="{x_offset + 20}" cy="120" r="2.5" fill="#475569"/>
            <circle cx="{x_offset + 30}" cy="140" r="2.5" fill="#2563eb"/>
            <circle cx="{x_offset + 40}" cy="160" r="2.5" fill="#16a34a"/>
            
            <line x1="{x_offset}" y1="80" x2="{x_offset}" y2="220" stroke="#78350f" stroke-width="1"/>
            <line x1="{x_offset + 10}" y1="100" x2="{x_offset + 10}" y2="220" stroke="#0f172a" stroke-width="1"/>
            <line x1="{x_offset + 20}" y1="120" x2="{x_offset + 20}" y2="220" stroke="#475569" stroke-width="1"/>
            <line x1="{x_offset + 30}" y1="140" x2="{x_offset + 30}" y2="400" stroke="#2563eb" stroke-width="1"/>
            <line x1="{x_offset + 40}" y1="160" x2="{x_offset + 40}" y2="400" stroke="#16a34a" stroke-width="1" stroke-dasharray="6,3"/>

            <!-- LS -Q3.{i} -->
            <g stroke="#0f172a" stroke-width="1.5" fill="none">
              <line x1="{x_offset}" y1="220" x2="{x_offset - 5}" y2="250"/>
              <line x1="{x_offset + 10}" y1="220" x2="{x_offset + 5}" y2="250"/>
              <line x1="{x_offset + 20}" y1="220" x2="{x_offset + 15}" y2="250"/>
              <line x1="{x_offset - 10}" y1="235" x2="{x_offset + 30}" y2="235" stroke-dasharray="2,2" stroke-width="1"/>
            </g>
            <text x="{x_offset - 20}" y="240" font-size="9" font-weight="bold" fill="#0f172a">-Q3.{i}</text>
            <text x="{x_offset + 35}" y="240" font-size="8" fill="#0f172a">LS 32A</text>

            <line x1="{x_offset}" y1="250" x2="{x_offset}" y2="300" stroke="#78350f" stroke-width="1"/>
            <line x1="{x_offset + 10}" y1="250" x2="{x_offset + 10}" y2="300" stroke="#0f172a" stroke-width="1"/>
            <line x1="{x_offset + 20}" y1="250" x2="{x_offset + 20}" y2="300" stroke="#475569" stroke-width="1"/>

            <!-- Terminal -X3.{i} -->
            <g fill="#ffffff" stroke="#0f172a" stroke-width="1.5">
              <circle cx="{x_offset}" cy="300" r="3"/>
              <circle cx="{x_offset + 10}" cy="300" r="3"/>
              <circle cx="{x_offset + 20}" cy="300" r="3"/>
              <circle cx="{x_offset + 30}" cy="300" r="3"/>
              <circle cx="{x_offset + 40}" cy="300" r="3"/>
            </g>
            <text x="{x_offset - 20}" y="303" font-size="9" font-weight="bold" fill="#0f172a">-X{i}</text>

            <!-- Cable -->
            <line x1="{x_offset}" y1="303" x2="{x_offset}" y2="400" stroke="#78350f" stroke-width="1"/>
            <line x1="{x_offset + 10}" y1="303" x2="{x_offset + 10}" y2="400" stroke="#0f172a" stroke-width="1"/>
            <line x1="{x_offset + 20}" y1="303" x2="{x_offset + 20}" y2="400" stroke="#475569" stroke-width="1"/>
            <path d="M {x_offset - 10} 340 C {x_offset - 10} 330, {x_offset + 50} 330, {x_offset + 50} 340" fill="none" stroke="#64748b" stroke-width="1" stroke-dasharray="2,2"/>
            <text x="{x_offset + 55}" y="342" font-size="7" fill="#64748b">-W3.{i} (5x6)</text>

            <!-- Rack Box (Ortskasten) -->
            <rect x="{x_offset - 20}" y="380" width="80" height="150" fill="none" stroke="#0f172a" stroke-dasharray="8,4" stroke-width="1"/>
            <text x="{x_offset - 15}" y="395" font-size="10" font-weight="bold" fill="#0f172a">+Rack {i}</text>

            <!-- Kentix PDU -->
            <rect x="{x_offset - 10}" y="400" width="60" height="100" fill="#f8fafc" stroke="#0f172a" stroke-width="1.5"/>
            <text x="{x_offset + 20}" y="440" font-size="10" font-weight="bold" text-anchor="middle" fill="#0f172a">-PDU1</text>
            <text x="{x_offset + 20}" y="455" font-size="8" text-anchor="middle" fill="#0f172a">Kentix 32A</text>
            <text x="{x_offset + 20}" y="470" font-size="7" text-anchor="middle" fill="#64748b">SmartPDU</text>
    """

blatt2_svg += """
          </g>
        </svg>
      </div>
"""

# Insert Blatt 2 just before the closing </div> of the CAD section
content = content.replace("    {/if}\n  </div>", blatt2_svg + "    {/if}\n  </div>")

with open("frontend/src/routes/eplan/+page.svelte", "w") as f:
    f.write(content)

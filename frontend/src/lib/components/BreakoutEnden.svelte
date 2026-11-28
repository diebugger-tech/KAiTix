<script lang="ts">
  import type { BEnde } from '$lib/kabel';

  // B-Enden eines Breakout-Kabels: je Ende eine Zeile "Gerät + Port".
  // Ersetzt im Kabel-Formular das eine Ziel, wenn der Kabeltyp enden_b > 1 hat.
  let {
    enden = $bindable(),
    devices,
    idPrefix = 'b-ende'
  }: {
    enden: BEnde[];
    devices: { id: number; hostname: string }[];
    idPrefix?: string;
  } = $props();

  const feldClass =
    'w-full min-h-11 bg-[var(--color-bg3)] border border-[var(--color-border2)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:outline-none focus:border-[#1D9E75]';
</script>

<fieldset class="space-y-2">
  <legend class="block text-xs font-semibold text-[var(--color-text2)] mb-1">
    B-Enden ({enden.length}) — je Ende Gerät und Port
  </legend>
  {#each enden as ende, index (index)}
    <div class="grid grid-cols-[5.5rem_1fr_1fr] items-center gap-2">
      <span class="text-xs font-mono text-[var(--color-text3)]">B-Ende {index + 1}</span>
      <select
        id="{idPrefix}-{index}-geraet"
        aria-label="B-Ende {index + 1}: Gerät"
        bind:value={ende.nach_device_id}
        class={feldClass}
      >
        <option value={null}>— Gerät —</option>
        {#each devices as d (d.id)}<option value={d.id}>{d.hostname}</option>{/each}
      </select>
      <input
        id="{idPrefix}-{index}-port"
        aria-label="B-Ende {index + 1}: Port"
        type="text"
        maxlength="50"
        placeholder="Port"
        bind:value={ende.nach_port}
        class={feldClass}
      />
    </div>
  {/each}
</fieldset>

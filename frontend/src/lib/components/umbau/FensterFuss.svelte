<!--
  Fußleiste eines Umbau-Fensters: links Abbrechen, rechts genau EINE Hauptaktion.
  Gesperrt = grau, der Grund steht als Satz daneben (nie nur ausgegraut).
  Minimaler lokaler Baustein nach dem Muster von RackModal.svelte.
-->
<script lang="ts">
  interface Props {
    hauptLabel: string;
    onhaupt: () => void;
    abbrechenLabel?: string;
    onabbrechen?: () => void;
    gesperrt?: boolean;
    grund?: string | null;
    busy?: boolean;
    variante?: 'standard' | 'gefahr';
  }
  let {
    hauptLabel,
    onhaupt,
    abbrechenLabel = 'Abbrechen',
    onabbrechen,
    gesperrt = false,
    grund = null,
    busy = false,
    variante = 'standard'
  }: Props = $props();

  const aus = $derived(gesperrt || busy);
</script>

<footer class="flex flex-wrap items-center gap-3 px-5 py-4 border-t border-[var(--color-border)]">
  {#if onabbrechen}
    <button
      type="button"
      onclick={onabbrechen}
      class="px-4 min-h-11 rounded-lg text-sm text-[var(--color-text2)] hover:bg-[var(--color-border)] transition"
    >
      {abbrechenLabel}
    </button>
  {/if}
  <span class="flex-1"></span>
  {#if gesperrt && grund}
    <span class="text-sm text-[var(--color-text2)]" role="status">{grund}</span>
  {/if}
  <button
    type="button"
    onclick={onhaupt}
    disabled={aus}
    class="px-5 min-h-11 rounded-lg text-sm font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed {variante === 'gefahr'
      ? 'bg-red-600 hover:bg-red-500 text-white'
      : 'bg-[#1D9E75] hover:bg-[#0F6E56] text-white'}"
  >
    {busy ? 'Läuft…' : hauptLabel}
  </button>
</footer>

<!--
  Kopf eines Umbau-Fensters: Titel links, optionale Aktion rechts, Schließen-Knopf.
  Minimaler lokaler Baustein nach dem Muster von RackModal.svelte.
-->
<script lang="ts">
  import type { Snippet } from 'svelte';
  import { X } from '@lucide/svelte';

  interface Props {
    titel: string;
    /** Rote Optik für zurücknehmende Vorgänge (Korrigieren). */
    warnung?: boolean;
    onclose?: () => void;
    rechts?: Snippet;
  }
  let { titel, warnung = false, onclose, rechts }: Props = $props();
</script>

<header class="flex flex-wrap items-center gap-3 px-5 pt-5 pb-3">
  <h3 class="flex-1 min-w-0 text-lg font-bold font-outfit {warnung ? 'text-red-400' : 'text-[var(--color-text)]'}">
    {titel}
  </h3>
  {@render rechts?.()}
  {#if onclose}
    <button
      type="button"
      onclick={onclose}
      aria-label="Schließen"
      class="min-w-11 min-h-11 flex items-center justify-center rounded-lg text-[var(--color-text3)] hover:bg-[var(--color-border)] hover:text-[var(--color-text)] transition"
    >
      <X class="w-5 h-5" />
    </button>
  {/if}
</header>

import re

with open("frontend/src/routes/(app)/import/+page.svelte", "r") as f:
    content = f.read()

# 1. Add deviceConflicts state
content = content.replace(
    "let deviceError = $state('');",
    "let deviceError = $state('');\n  let deviceConflicts = $state<{db_duplicates: string[], csv_duplicates: string[]} | null>(null);"
)

# 2. Fix deviceResult type
content = content.replace(
    "let deviceResult = $state<{ created: number; updated: number; skipped: number } | null>(null);",
    "let deviceResult = $state<{ created: number; updated: number } | null>(null);"
)

# 3. Update device preview reset
content = content.replace(
    "deviceResult = null;",
    "deviceResult = null;\n    deviceConflicts = null;"
)

# 4. Update device commit error handling
old_device_catch = """    } catch (e: any) {
      deviceError = e.message ?? 'Fehler beim Import';
    }"""
new_device_catch = """    } catch (e: any) {
      if (e && e.conflicts) {
        deviceError = e.message;
        deviceConflicts = e.conflicts;
      } else {
        deviceError = e.message ?? 'Fehler beim Import';
      }
    }"""
content = content.replace(old_device_catch, new_device_catch)

# 5. Add cableConflicts state
content = content.replace(
    "let cableError = $state('');",
    "let cableError = $state('');\n  let cableConflicts = $state<{db_duplicates: string[], csv_duplicates: string[]} | null>(null);"
)

# 6. Update cable preview reset
content = content.replace(
    "cableResult = null;",
    "cableResult = null;\n    cableConflicts = null;"
)

# 7. Update cable commit error handling
old_cable_catch = """    } catch (e: any) {
      cableError = e.message ?? 'Fehler beim Import';
    }"""
new_cable_catch = """    } catch (e: any) {
      if (e && e.conflicts) {
        cableError = e.message;
        cableConflicts = e.conflicts;
      } else {
        cableError = e.message ?? 'Fehler beim Import';
      }
    }"""
content = content.replace(old_cable_catch, new_cable_catch)

# 8. Remove device skipped template part
content = content.replace(
    "              {#if deviceResult.skipped > 0}, {deviceResult.skipped} übersprungen{/if}",
    ""
)

# 9. Insert conflicts template before deviceError
conflict_template_device = """          {#if deviceConflicts}
            <div class="mt-4 p-4 bg-red-900/20 border border-red-500/50 rounded-lg text-red-200">
              <h4 class="font-bold mb-2">Konflikte:</h4>
              {#if deviceConflicts.db_duplicates?.length}
                <ul class="list-disc pl-5 mb-2">
                  {#each deviceConflicts.db_duplicates as dup}
                    <li>{dup}</li>
                  {/each}
                </ul>
              {/if}
              {#if deviceConflicts.csv_duplicates?.length}
                <ul class="list-disc pl-5">
                  {#each deviceConflicts.csv_duplicates as dup}
                    <li>{dup}</li>
                  {/each}
                </ul>
              {/if}
            </div>
          {/if}
"""

content = content.replace(
    "          {#if deviceError}",
    conflict_template_device + "\n          {#if deviceError}"
)

# 10. Insert conflicts template before cableError
conflict_template_cable = """          {#if cableConflicts}
            <div class="mt-4 p-4 bg-red-900/20 border border-red-500/50 rounded-lg text-red-200">
              <h4 class="font-bold mb-2">Konflikte:</h4>
              {#if cableConflicts.db_duplicates?.length}
                <ul class="list-disc pl-5 mb-2">
                  {#each cableConflicts.db_duplicates as dup}
                    <li>{dup}</li>
                  {/each}
                </ul>
              {/if}
              {#if cableConflicts.csv_duplicates?.length}
                <ul class="list-disc pl-5">
                  {#each cableConflicts.csv_duplicates as dup}
                    <li>{dup}</li>
                  {/each}
                </ul>
              {/if}
            </div>
          {/if}
"""

content = content.replace(
    "          {#if cableError}",
    conflict_template_cable + "\n          {#if cableError}"
)

with open("frontend/src/routes/(app)/import/+page.svelte", "w") as f:
    f.write(content)

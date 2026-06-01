import os
import re

directory = 'frontend/src'
for root, dirs, files in os.walk(directory):
    for file in files:
        if file.endswith('.svelte') or file.endswith('.ts'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            new_content = content
            # text-slate-100 and 200 => text-[var(--color-text)]
            new_content = re.sub(r'text-slate-[12]00', 'text-[var(--color-text)]', new_content)
            # text-slate-300 and 400 => text-[var(--color-text2)]
            new_content = re.sub(r'text-slate-[34]00', 'text-[var(--color-text2)]', new_content)
            
            # and what about hover:text-slate-*? Regex covers them if we do just the above, 
            # e.g., hover:text-slate-200 becomes hover:text-[var(--color-text)]

            if content != new_content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated {path}")

# 1. export.py
with open("app/domains/import_export/routers/export.py", "r") as f:
    content = f.read()
content = content.replace(
    '"ipv6_adresse": d.ipv6_adresse or "–",', '"ipv6": d.ipv6_adresse or "–",'
)
with open("app/domains/import_export/routers/export.py", "w") as f:
    f.write(content)

# 2. full_csv.py
with open("app/domains/import_export/services/exports/full_csv.py", "r") as f:
    content = f.read()
content = content.replace('d.get("ipv6_adresse", ""),', 'd.get("ipv6", ""),', 1)
with open("app/domains/import_export/services/exports/full_csv.py", "w") as f:
    f.write(content)

# 3. full_ods.py
with open("app/domains/import_export/services/exports/full_ods.py", "r") as f:
    content = f.read()
content = content.replace('d.get("ipv6_adresse", "–"),', 'd.get("ipv6", "–"),', 1)
with open("app/domains/import_export/services/exports/full_ods.py", "w") as f:
    f.write(content)

# 4. full_xlsx.py
with open("app/domains/import_export/services/exports/full_xlsx.py", "r") as f:
    content = f.read()
content = content.replace('d.get("ipv6_adresse", "–"),', 'd.get("ipv6", "–"),', 1)
with open("app/domains/import_export/services/exports/full_xlsx.py", "w") as f:
    f.write(content)

# 5. racks.py
with open("app/domains/import_export/services/exports/racks.py", "r") as f:
    content = f.read()
content = content.replace('d.get("ipv6_adresse", "–"),', 'd.get("ipv6", "–"),')
content = content.replace('d.get("ipv6_adresse", ""),', 'd.get("ipv6", ""),')
with open("app/domains/import_export/services/exports/racks.py", "w") as f:
    f.write(content)

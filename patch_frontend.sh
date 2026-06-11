# api.ts
sed -i 's/ip_adresse?: string | null;/ip_adresse?: string | null; ipv6_adresse?: string | null;/g' frontend/src/lib/api.ts
sed -i 's/ip_adresse?: string;/ip_adresse?: string; ipv6_adresse?: string;/g' frontend/src/lib/api.ts
sed -i 's/ip_adresse: string | null/ip_adresse: string | null; ipv6_adresse: string | null/g' frontend/src/lib/api.ts

# RackFrontView.svelte
sed -i "s/IP: \${dev.ip_adresse || '–'}/IP: \${dev.ip_adresse || '–'}\\\\nIPv6: \${dev.ipv6_adresse || '–'}/g" frontend/src/lib/components/RackFrontView.svelte

# racks/+page.svelte
sed -i "s/ip_adresse: devIp || undefined,/ip_adresse: devIp || undefined,\n        ipv6_adresse: editIpv6 || undefined,/g" frontend/src/routes/\(app\)/racks/+page.svelte
sed -i "s/editIp           = selectedDevice.ip_adresse || '';/editIp           = selectedDevice.ip_adresse || '';\n    editIpv6         = selectedDevice.ipv6_adresse || '';/g" frontend/src/routes/\(app\)/racks/+page.svelte
sed -i "s/ip_adresse:             editIp || undefined,/ip_adresse:             editIp || undefined,\n        ipv6_adresse:           editIpv6 || undefined,/g" frontend/src/routes/\(app\)/racks/+page.svelte
sed -i "s/IP: \${dev.ip_adresse || '–'}/IP: \${dev.ip_adresse || '–'}\\\\nIPv6: \${dev.ipv6_adresse || '–'}/g" frontend/src/routes/\(app\)/racks/+page.svelte
sed -i 's/let editIp = '"''"';/let editIp = '"''"';\n  let editIpv6 = '"''"';/g' frontend/src/routes/\(app\)/racks/+page.svelte

# We need to add the input field for IPv6 in the forms in racks/+page.svelte
# Let's see the form in racks/+page.svelte

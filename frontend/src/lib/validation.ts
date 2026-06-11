export function validateDevicePosition(u_position: number | undefined | null, u_hoehe: number, rackHoeheU: number): string | null {
  if (u_hoehe === 0) return null; // 0U items don't have a strict U-position bound within the rack grid
  if (u_position == null || isNaN(u_position)) return 'U-Position fehlt.';
  if (u_position < 1) return 'U-Position muss mindestens 1 sein.';
  if (u_position + u_hoehe - 1 > rackHoeheU) return `Gerät überschreitet Rack-Höhe (Max: ${rackHoeheU} HE).`;
  return null;
}

export function validateVm(cpu_cores: number, ram_mb: number, disk_gb: number): string | null {
  if (cpu_cores < 1) return 'CPU-Kerne muss mindestens 1 sein.';
  if (ram_mb < 128) return 'RAM muss mindestens 128 MB betragen.';
  if (disk_gb < 1) return 'Disk muss mindestens 1 GB betragen.';
  return null;
}

export interface Store {
  brand: string;
  group: string;
  store_number: string;
  name: string;
  address: string;
  google_maps_url: string;
}

export interface JobStatus {
  status: 'running' | 'done' | 'error';
  phase: string;
  progress: number;
  message: string;
}

export function storeKey(group: string, num: string): string {
  return `${group}::${num}`;
}

export function storeLabel(store: Store): string {
  const words = store.brand.split(/\s+/);
  const prefix = words.map((w) => w[0]).join('').toUpperCase().slice(0, 3);
  const parts = store.address.split(',');
  if (parts.length >= 3) {
    const city = parts[parts.length - 2].trim();
    const state = parts[parts.length - 1].trim().split(' ')[0];
    return `${prefix} #${store.store_number} · ${city}, ${state}`;
  }
  return `${prefix} #${store.store_number}`;
}

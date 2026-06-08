import type { JobStatus, Store } from './types';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function apiUrl(path: string): string {
  return `${API}${path}`;
}

export interface Brand {
  name: string;
  color: string;
}

export async function fetchBrands(): Promise<Brand[]> {
  const res = await fetch(apiUrl('/api/brands'));
  if (!res.ok) throw new Error('Failed to fetch brands');
  return res.json();
}

export async function saveBrand(name: string, color: string): Promise<void> {
  const res = await fetch(apiUrl('/api/brands'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, color }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to save brand');
  }
}

export async function fetchStores(): Promise<Store[]> {
  const res = await fetch(apiUrl('/api/stores'));
  if (!res.ok) throw new Error('Failed to fetch stores');
  return res.json();
}

export async function startJob(startDate: string, endDate?: string, selectedStores?: string[]): Promise<string> {
  const res = await fetch(apiUrl('/api/run'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      start_date: startDate,
      end_date: endDate || null,
      selected_stores: selectedStores ?? null,
    }),
  });
  if (!res.ok) throw new Error('Failed to start job');
  const data = await res.json();
  return data.job_id as string;
}

export async function pollStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(apiUrl(`/api/status/${jobId}`));
  if (!res.ok) throw new Error('Job not found');
  return res.json();
}

export function downloadUrl(): string {
  return apiUrl('/api/download');
}

export async function fillMapsUrls(): Promise<{ updated: number; total: number }> {
  const res = await fetch(apiUrl('/api/fill-maps-urls'), { method: 'POST' });
  if (!res.ok) throw new Error('Failed to fill URLs');
  return res.json();
}

export async function addStore(payload: {
  store_number: string;
  name: string;
  address: string;
  group: string;
  google_maps_url?: string;
}): Promise<void> {
  const res = await fetch(apiUrl('/api/stores'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Failed to add store');
}

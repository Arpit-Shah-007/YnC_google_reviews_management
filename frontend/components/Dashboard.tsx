'use client';

import { useCallback, useEffect, useState } from 'react';
import { type Brand, addStore, fetchBrands, fetchStores, pollStatus, saveBrand, startJob } from '@/lib/api';
import { type JobStatus, type Store, storeKey } from '@/lib/types';
import ActionArea from './ActionArea';
import ManagementPanel from './ManagementPanel';
import Modal from './Modal';
import StoreSelector from './StoreSelector';
import Toast from './Toast';

type AppPhase = 'idle' | 'running' | 'done' | 'error';
type ModalCtx = 'generate' | 'add-store' | 'add-brand';

export default function Dashboard() {
  const [stores, setStores] = useState<Store[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [loadErr, setLoadErr] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [dateFrom, setDateFrom] = useState('2025-03-01');
  const [dateTo, setDateTo] = useState('');
  const [phase, setPhase] = useState<AppPhase>('idle');
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [modalCtx, setModalCtx] = useState<ModalCtx | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const [pendingStore, setPendingStore] = useState<{ num: string; group: string; addr: string } | null>(null);
  const [pendingBrand, setPendingBrand] = useState<{ name: string; color: string } | null>(null);

  useEffect(() => {
    let storesDone = false;
    let brandsDone = false;
    const tryDone = () => { if (storesDone && brandsDone) setIsLoading(false); };

    fetchStores()
      .then((data) => { setStores(data); storesDone = true; tryDone(); })
      .catch(() => { setLoadErr(true); storesDone = true; tryDone(); });
    fetchBrands()
      .then((data) => { setBrands(data); brandsDone = true; tryDone(); })
      .catch(() => { brandsDone = true; tryDone(); });
  }, []);

  useEffect(() => {
    if (!jobId || phase !== 'running') return;
    const interval = setInterval(async () => {
      try {
        const s = await pollStatus(jobId);
        setJobStatus(s);
        if (s.status === 'done') { setPhase('done'); clearInterval(interval); }
        else if (s.status === 'error') { setPhase('error'); clearInterval(interval); }
      } catch {
        // transient — keep polling
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [jobId, phase]);

  const showToast = useCallback((msg: string) => setToast(msg), []);

  function toggle(key: string, checked: boolean) {
    setSelected((prev) => {
      const next = new Set(prev);
      checked ? next.add(key) : next.delete(key);
      return next;
    });
  }

  function toggleAll(groupId: string, checked: boolean) {
    const keys = stores.filter((s) => s.group === groupId).map((s) => storeKey(s.group, s.store_number));
    setSelected((prev) => {
      const next = new Set(prev);
      keys.forEach((k) => (checked ? next.add(k) : next.delete(k)));
      return next;
    });
  }

  function onGenerate() { setModalCtx('generate'); }

  async function doGenerate() {
    setPhase('running');
    setJobStatus({ status: 'running', phase: 'starting', progress: 0, message: 'Queued...' });
    try {
      const id = await startJob(dateFrom, dateTo || undefined, Array.from(selected));
      setJobId(id);
    } catch {
      setPhase('error');
      setJobStatus({ status: 'error', phase: 'error', progress: 0, message: 'Failed to reach server' });
    }
  }

  function resetToIdle() {
    setPhase('idle');
    setJobId(null);
    setJobStatus(null);
    setSelected(new Set());
  }

  function requestSaveStore(num: string, group: string, addr: string) {
    setPendingStore({ num, group, addr });
    setModalCtx('add-store');
  }

  async function doSaveStore() {
    if (!pendingStore) return;
    try {
      await addStore({
        store_number: pendingStore.num,
        name: `${pendingStore.group} #${pendingStore.num}`,
        address: pendingStore.addr,
        group: pendingStore.group,
      });
      setStores((prev) => [
        ...prev,
        {
          brand: pendingStore.group,
          group: pendingStore.group,
          store_number: pendingStore.num,
          name: `${pendingStore.group} #${pendingStore.num}`,
          address: pendingStore.addr,
          google_maps_url: '',
        },
      ]);
      showToast(`Store #${pendingStore.num} saved!`);
    } catch {
      showToast('Failed to save — check server connection.');
    }
    setPendingStore(null);
  }

  function requestSaveBrand(name: string, color: string) {
    setPendingBrand({ name, color });
    setModalCtx('add-brand');
  }

  async function doSaveBrand() {
    if (!pendingBrand) return;
    try {
      await saveBrand(pendingBrand.name, pendingBrand.color);
      setBrands((prev) => [...prev, { name: pendingBrand.name, color: pendingBrand.color, builtin: false }]);
      showToast(`Brand group "${pendingBrand.name}" created!`);
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'Failed to save brand');
    }
    setPendingBrand(null);
  }

  function onModalConfirm() {
    setModalCtx(null);
    if (modalCtx === 'generate') doGenerate();
    else if (modalCtx === 'add-store') doSaveStore();
    else if (modalCtx === 'add-brand') doSaveBrand();
  }

  const storeCounts = Object.fromEntries(
    brands.map((b) => [b.name, stores.filter((s) => s.group === b.name).length])
  );

  return (
    <>
      <header className="header">
        <div className="header-left">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img className="header-logo" src="/logo.png" alt="Y&C Logo" />
          <div className="header-divider" />
          <div>
            <div className="header-title">Review Hub</div>
            <div className="header-sub">Yum &amp; Chill Restaurant Group</div>
          </div>
        </div>
        <div className="header-badge">{stores.length} stores configured</div>
      </header>

      {isLoading ? (
        <main>
          <div className="panel panel-left">
            <div className="skel-card">
              <div className="skel skel-text" style={{ width: '45%', marginBottom: '0.8rem' }} />
              <div className="skel skel-block" />
              <div className="skel skel-block" />
              <div className="skel skel-block" style={{ width: '70%' }} />
            </div>
            <div className="skel-card">
              <div className="skel skel-text" style={{ width: '35%', marginBottom: '0.8rem' }} />
              <div style={{ display: 'flex', gap: '0.65rem' }}>
                <div className="skel skel-block" style={{ flex: 1 }} />
                <div className="skel skel-block" style={{ flex: 1 }} />
              </div>
            </div>
            <div className="skel-card">
              <div className="skel skel-block-tall" />
            </div>
          </div>
          <div className="panel panel-right" style={{ gap: '0' }}>
            <div className="skel-card" style={{ marginBottom: '0', borderBottom: 'none', borderRadius: '12px 12px 0 0' }}>
              <div className="skel skel-text" style={{ width: '50%', marginBottom: '0.8rem' }} />
              <div className="skel skel-block" />
              <div className="skel skel-block" />
              <div className="skel skel-block" />
            </div>
            <div className="skel-card" style={{ borderRadius: '0 0 12px 12px' }}>
              <div className="skel skel-text" style={{ width: '40%', marginBottom: '0.8rem' }} />
              <div className="skel skel-block" />
              <div className="skel skel-block" />
              <div className="skel skel-block" style={{ width: '55%' }} />
            </div>
          </div>
        </main>
      ) : (
      <main>
        <div className="panel panel-left">
          <div className="card">
            <div className="card-header">
              <div className="section-label">Select Stores</div>
              <div className="card-hint">Pick individual stores or select all per group</div>
            </div>
            {loadErr ? (
              <p style={{ fontSize: '0.75rem', color: '#f5a8a8' }}>
                Could not load stores — is the backend running?
              </p>
            ) : (
              <StoreSelector
                stores={stores}
                selected={selected}
                brands={brands}
                onToggle={toggle}
                onToggleAll={toggleAll}
                onRemoveChip={(num) => toggle(num, false)}
                onRemoveGroup={(groupId) => toggleAll(groupId, false)}
              />
            )}
          </div>

          <div className="card">
            <div className="card-header" style={{ marginBottom: '0.85rem' }}>
              <div className="section-label">Review Period</div>
            </div>
            <div className="date-row">
              <div className="date-field">
                <label>From</label>
                <input
                  className="date-input"
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                />
              </div>
              <div className="date-field">
                <label>To (blank = today)</label>
                <input
                  className="date-input"
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                />
              </div>
            </div>
          </div>

          <ActionArea
            totalSelected={selected.size}
            phase={phase}
            jobStatus={jobStatus}
            onGenerate={onGenerate}
            onReset={resetToIdle}
          />
        </div>

        <ManagementPanel
          brands={brands}
          storeCounts={storeCounts}
          onSaveStore={requestSaveStore}
          onSaveBrand={requestSaveBrand}
        />
      </main>
      )}

      <footer>
        Copyright &copy; {new Date().getFullYear()} Yum &amp; Chill Restaurant Group. All rights reserved.
      </footer>

      {modalCtx && (
        <Modal
          ctx={modalCtx}
          onConfirm={onModalConfirm}
          onClose={() => setModalCtx(null)}
        />
      )}

      <Toast message={toast} onDone={() => setToast(null)} />
    </>
  );
}

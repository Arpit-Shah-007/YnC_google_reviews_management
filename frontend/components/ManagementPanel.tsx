'use client';

import { useState } from 'react';
import type { Brand } from '@/lib/api';

interface Props {
  brands: Brand[];
  storeCounts: Record<string, number>;
  onSaveStore: (num: string, group: string, addr: string) => void;
  onSaveBrand: (name: string, color: string) => void;
}

export default function ManagementPanel({
  brands,
  storeCounts,
  onSaveStore,
  onSaveBrand,
}: Props) {
  const [storeNum, setStoreNum] = useState('');
  const [storeGroup, setStoreGroup] = useState('');
  const [storeAddr, setStoreAddr] = useState('');
  const [brandName, setBrandName] = useState('');
  const [brandColor, setBrandColor] = useState('#E8640A');

  const activeGroup = storeGroup || brands[0]?.name || '';

  function handleSaveStore() {
    if (!storeNum.trim() || !storeAddr.trim()) return;
    onSaveStore(storeNum.trim(), activeGroup, storeAddr.trim());
    setStoreNum('');
    setStoreAddr('');
  }

  function handleSaveBrand() {
    if (!brandName.trim()) return;
    onSaveBrand(brandName.trim(), brandColor);
    setBrandName('');
  }

  return (
    <div className="panel panel-right">
      <div className="form-section">
        <div className="form-section-title">Add a New Location</div>
        <div className="form-row" style={{ marginBottom: '0.65rem' }}>
          <div className="form-field">
            <label>Store Number</label>
            <input
              className="form-input"
              placeholder="e.g. 041966"
              value={storeNum}
              onChange={(e) => setStoreNum(e.target.value)}
            />
          </div>
          <div className="form-field">
            <label>Brand Group</label>
            <select
              className="form-select"
              value={activeGroup}
              onChange={(e) => setStoreGroup(e.target.value)}
            >
              {brands.map((b) => (
                <option key={b.name} value={b.name}>{b.name}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="form-field" style={{ marginBottom: 0 }}>
          <label>Full Address</label>
          <input
            className="form-input"
            placeholder="1 Main St, Linden, NJ 07036"
            value={storeAddr}
            onChange={(e) => setStoreAddr(e.target.value)}
          />
          <div style={{ fontSize: '0.6rem', color: '#555', marginTop: '0.3rem', lineHeight: 1.4 }}>
            Verify this address carefully — Google Maps will match the nearest location to it.
          </div>
        </div>
        <button className="save-btn" onClick={handleSaveStore}>&#128274; Save Location</button>
      </div>

      <div className="form-section">
        <div className="form-section-title">Brand Groups</div>
        <div className="brand-list">
          {brands.map((b) => (
            <div key={b.name} className="brand-row">
              <div className="brand-dot-label">
                <span className="dot" style={{ background: b.color }} /> {b.name}
              </div>
              <span className="brand-count">{storeCounts[b.name] ?? 0} stores</span>
            </div>
          ))}
        </div>
        <div className="divider" />
        <div className="form-section-title" style={{ marginBottom: '0.75rem' }}>Add a New Brand Group</div>
        <div className="form-row">
          <div className="form-field">
            <label>Brand Name</label>
            <input
              className="form-input"
              placeholder="e.g. Pizza Hut"
              value={brandName}
              onChange={(e) => setBrandName(e.target.value)}
            />
          </div>
          <div className="form-field">
            <label>Brand Color</label>
            <div className="color-row">
              <input
                type="color"
                className="color-swatch"
                value={brandColor}
                onChange={(e) => setBrandColor(e.target.value)}
              />
              <input
                className="form-input"
                placeholder="#E8640A"
                style={{ flex: 1 }}
                value={brandColor}
                onChange={(e) => {
                  if (/^#[0-9A-Fa-f]{6}$/.test(e.target.value)) setBrandColor(e.target.value);
                }}
              />
            </div>
          </div>
        </div>
        <button className="save-btn" onClick={handleSaveBrand}>&#128274; Create Brand Group</button>
      </div>
    </div>
  );
}

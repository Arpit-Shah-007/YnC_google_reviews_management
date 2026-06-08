'use client';

import { useEffect, useRef, useState } from 'react';

const SECRET = process.env.NEXT_PUBLIC_DASHBOARD_SECRET ?? '';

interface Props {
  ctx: 'generate' | 'add-store' | 'add-brand';
  onConfirm: () => void;
  onClose: () => void;
}

const CFG = {
  generate: { title: 'Generate Report', sub: 'Enter your secret key to start the analysis.', btn: 'Confirm & Generate' },
  'add-store': { title: 'Save Location', sub: 'Enter your secret key to save this location.', btn: 'Confirm & Save' },
  'add-brand': { title: 'Create Brand', sub: 'Enter your secret key to create this brand group.', btn: 'Confirm & Create' },
} as const;

export default function Modal({ ctx, onConfirm, onClose }: Props) {
  const [key, setKey] = useState('');
  const [error, setError] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const cfg = CFG[ctx];

  useEffect(() => {
    setKey('');
    setError(false);
    setTimeout(() => inputRef.current?.focus(), 80);
  }, [ctx]);

  function confirm() {
    if (key === SECRET) {
      onConfirm();
    } else {
      setError(true);
      setKey('');
      inputRef.current?.focus();
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') confirm();
    if (e.key === 'Escape') onClose();
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-icon">&#128272;</div>
        <div className="modal-title">{cfg.title}</div>
        <div className="modal-sub">{cfg.sub}</div>
        <input
          ref={inputRef}
          className="modal-input"
          type="password"
          placeholder="Enter key"
          value={key}
          onChange={(e) => { setKey(e.target.value); setError(false); }}
          onKeyDown={handleKeyDown}
        />
        {error && <div className="modal-error">Incorrect key — try again.</div>}
        <div className="modal-actions">
          <button className="modal-cancel" onClick={onClose}>Cancel</button>
          <button className="modal-confirm" onClick={confirm}>{cfg.btn}</button>
        </div>
      </div>
    </div>
  );
}

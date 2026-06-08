'use client';

import { downloadUrl } from '@/lib/api';
import type { JobStatus } from '@/lib/types';

interface Props {
  totalSelected: number;
  phase: 'idle' | 'running' | 'done' | 'error';
  jobStatus: JobStatus | null;
  onGenerate: () => void;
  onReset: () => void;
}

export default function ActionArea({ totalSelected, phase, jobStatus, onGenerate, onReset }: Props) {
  if (phase === 'idle') {
    return (
      <button
        className="generate-btn"
        disabled={totalSelected === 0}
        onClick={onGenerate}
      >
        Generate Report
      </button>
    );
  }

  if (phase === 'running') {
    const pct = jobStatus?.progress ?? 0;
    const msg = jobStatus?.message ?? 'Working...';
    const phaseLabel = jobStatus?.phase === 'scraping' ? 'Scraping reviews...' : 'Running AI analysis...';
    return (
      <div className="status-bar">
        <div className="status-bar-left">
          <span className="blink" />
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: '0.78rem', color: '#ccc', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {msg}
            </div>
            <div style={{ fontSize: '0.63rem', color: '#555', marginTop: 2 }}>{phaseLabel}</div>
          </div>
        </div>
        <div className="progress-pct">{pct}%</div>
      </div>
    );
  }

  if (phase === 'error') {
    return (
      <>
        <div className="status-error">
          {jobStatus?.message || 'An error occurred. Check the server logs.'}
        </div>
        <div className="reset-link" onClick={onReset}>Try again</div>
      </>
    );
  }

  // done
  return (
    <>
      <a className="download-btn" href={downloadUrl()} download>
        &#11015; Download Report
      </a>
      <div className="reset-link" onClick={onReset}>Run another report</div>
    </>
  );
}

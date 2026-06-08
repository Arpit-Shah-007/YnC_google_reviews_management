'use client';

import { useEffect, useRef, useState } from 'react';
import type { Brand } from '@/lib/api';
import { type Store, storeKey, storeLabel } from '@/lib/types';

interface Props {
  stores: Store[];
  selected: Set<string>;
  brands: Brand[];
  onToggle: (num: string, checked: boolean) => void;
  onToggleAll: (groupId: string, checked: boolean) => void;
  onRemoveChip: (num: string) => void;
  onRemoveGroup: (groupId: string) => void;
}

function chipStyle(color: string): React.CSSProperties {
  return {
    background: color + '22',
    color,
    border: `1px solid ${color}88`,
  };
}

function GroupDropdown({
  groupId,
  label,
  color,
  groupStores,
  selected,
  open,
  onOpen,
  onToggle,
  onToggleAll,
  onRemoveChip,
  onRemoveGroup,
}: {
  groupId: string;
  label: string;
  color: string;
  groupStores: Store[];
  selected: Set<string>;
  open: string | null;
  onOpen: (id: string | null) => void;
  onToggle: (num: string, checked: boolean) => void;
  onToggleAll: (groupId: string, checked: boolean) => void;
  onRemoveChip: (num: string) => void;
  onRemoveGroup: (groupId: string) => void;
}) {
  const checkedCount = groupStores.filter((s) => selected.has(storeKey(s.group, s.store_number))).length;
  const allChecked = checkedCount === groupStores.length && groupStores.length > 0;
  const someChecked = checkedCount > 0 && !allChecked;
  const isOpen = open === groupId;

  let labelText = 'None selected';
  if (allChecked) labelText = `All ${checkedCount} stores`;
  else if (checkedCount > 0) labelText = `${checkedCount} store${checkedCount > 1 ? 's' : ''} selected`;

  return (
    <div className="dd-group">
      <label>
        <span className="dot" style={{ background: color }} />
        {label}
      </label>
      <div className="dd-wrapper">
        <button
          className={`dd-trigger${isOpen ? ' active' : ''}`}
          onClick={() => onOpen(isOpen ? null : groupId)}
        >
          <span className="dd-trigger-text">{labelText}</span>
          <span className="dd-arrow">&#9660;</span>
        </button>
        {isOpen && (
          <div className="dd-menu">
            <div className="dd-item dd-all" onClick={() => onToggleAll(groupId, !allChecked)}>
              <input
                type="checkbox"
                checked={allChecked}
                ref={(el) => { if (el) el.indeterminate = someChecked; }}
                onChange={() => {}}
                onClick={(e) => e.stopPropagation()}
              />
              All {groupStores.length} stores
            </div>
            <div className="dd-divider" />
            {groupStores.map((s) => (
              <div
                key={s.store_number}
                className="dd-item"
                onClick={() => onToggle(storeKey(s.group, s.store_number), !selected.has(storeKey(s.group, s.store_number)))}
              >
                <input
                  type="checkbox"
                  checked={selected.has(storeKey(s.group, s.store_number))}
                  onChange={() => {}}
                  onClick={(e) => e.stopPropagation()}
                />
                <span>{storeLabel(s)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function StoreSelector({
  stores,
  selected,
  brands,
  onToggle,
  onToggleAll,
  onRemoveChip,
  onRemoveGroup,
}: Props) {
  const [open, setOpen] = useState<string | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(null);
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const byGroup = (gid: string) => stores.filter((s) => s.group === gid);
  const totalSelected = selected.size;

  const activeBrands = brands.filter((b) => byGroup(b.name).length > 0);

  return (
    <>
      <div className="dropdowns-grid" ref={ref}>
        {activeBrands.map((b) => (
          <GroupDropdown
            key={b.name}
            groupId={b.name}
            label={b.name}
            color={b.color}
            groupStores={byGroup(b.name)}
            selected={selected}
            open={open}
            onOpen={setOpen}
            onToggle={onToggle}
            onToggleAll={onToggleAll}
            onRemoveChip={onRemoveChip}
            onRemoveGroup={onRemoveGroup}
          />
        ))}
      </div>

      <div className="chips">
        {totalSelected === 0 && (
          <span className="chips-empty">No stores selected — pick at least one above</span>
        )}
        {brands.map((b) => {
          const groupStores = byGroup(b.name);
          const checked = groupStores.filter((s) => selected.has(storeKey(s.group, s.store_number)));
          if (!checked.length) return null;
          if (checked.length === groupStores.length) {
            return (
              <span key={b.name} className="chip" style={chipStyle(b.color)}>
                <span className="chip-text">All {checked.length} {b.name}</span>
                <span className="chip-rm" onClick={() => onRemoveGroup(b.name)}>&#10005;</span>
              </span>
            );
          }
          return checked.map((s) => (
            <span key={storeKey(s.group, s.store_number)} className="chip" style={chipStyle(b.color)}>
              <span className="chip-text">{storeLabel(s)}</span>
              <span className="chip-rm" onClick={() => onRemoveChip(storeKey(s.group, s.store_number))}>&#10005;</span>
            </span>
          ));
        })}
      </div>

      <div className="selection-summary">
        <strong>{totalSelected}</strong> store{totalSelected !== 1 ? 's' : ''} selected
      </div>
    </>
  );
}

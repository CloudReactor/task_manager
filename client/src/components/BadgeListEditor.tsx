import React, { useState } from 'react';
import { Button } from 'react-bootstrap';

export interface BadgeListEditorProps {
  value: string[] | null;
  placeholder?: string;
  onChange: (newValue: string[] | null) => void;
  disabled?: boolean;
  width?: number;
}

function BadgeListEditor({ value, placeholder, onChange, disabled = false, width }: BadgeListEditorProps) {
  const [inputValue, setInputValue] = useState('');
  const items = value ?? [];

  const handleRemove = (index: number) => {
    const next = items.filter((_, i) => i !== index);
    onChange(next.length > 0 ? next : null);
  };

  const handleAdd = () => {
    const trimmed = inputValue.trim();
    if (!trimmed) return;
    onChange([...items, trimmed]);
    setInputValue('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAdd();
    }
  };

  return (
    <div style={{ width: width ? `${width}px` : '260px' }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: items.length ? '9px' : 0 }}>
        {items.map((item, i) => (
          <span key={i} className="badge bg-secondary" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontWeight: 'normal', fontSize: '1.2em' }}>
            <span>{item}</span>
            <button
              type="button"
              onClick={() => handleRemove(i)}
              disabled={disabled}
              style={{ background: 'none', border: 'none', color: disabled ? '#6c757d' : 'inherit', cursor: disabled ? 'not-allowed' : 'pointer', padding: '0 1px', lineHeight: 1 }}
              aria-label={`Remove ${item}`}
            >
              &times;
            </button>
          </span>
        ))}
      </div>
      <div style={{ display: 'flex', gap: '4px', width: '100%', alignItems: 'flex-start' }}>
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder ?? "Add item ..."}
          style={{ flex: 1, minWidth: 0, margin: 0 }}
          disabled={disabled}
        />
        <Button variant="outline-secondary" size="sm" onClick={handleAdd} disabled={disabled || !inputValue.trim()} style={{ flexShrink: 0, padding: '4px 8px', margin: 0 }}>+</Button>
      </div>
    </div>
  );
}

export default BadgeListEditor;

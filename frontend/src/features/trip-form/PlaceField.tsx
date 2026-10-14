import { useId, useState } from 'react';

import type { Place, PlaceInput } from '../../api/types';
import { useAutocomplete } from '../../hooks/useAutocomplete';

interface Props {
  label: string;
  value: PlaceInput;
  onChange: (value: PlaceInput) => void;
  placeholder?: string;
}

export function PlaceField({ label, value, onChange, placeholder }: Props) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const hasCoords = value.lat !== undefined;
  const { data: suggestions = [], isFetching } = useAutocomplete(value.label, open && !hasCoords);

  function choose(place: Place) {
    onChange({ label: place.label, lat: place.lat, lon: place.lon });
    setOpen(false);
    setActive(-1);
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!open || suggestions.length === 0) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActive((i) => (i + 1) % suggestions.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((i) => (i <= 0 ? suggestions.length - 1 : i - 1));
    } else if (e.key === 'Enter' && active >= 0) {
      e.preventDefault();
      choose(suggestions[active]);
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  }

  const listId = `${id}-list`;
  return (
    <div className="field place-field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="text"
        role="combobox"
        aria-expanded={open && suggestions.length > 0}
        aria-controls={listId}
        aria-autocomplete="list"
        autoComplete="off"
        placeholder={placeholder}
        value={value.label}
        onChange={(e) => {
          onChange({ label: e.target.value });
          setOpen(true);
          setActive(-1);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 120)}
        onKeyDown={onKeyDown}
      />
      {hasCoords && (
        <span className="place-check" aria-label="Location confirmed" title="Location confirmed">
          ✓
        </span>
      )}
      {open && !hasCoords && (suggestions.length > 0 || isFetching) && (
        <ul id={listId} role="listbox" className="suggestions">
          {suggestions.map((s, i) => (
            <li
              key={`${s.label}-${s.lat}`}
              role="option"
              aria-selected={i === active}
              className={i === active ? 'active' : undefined}
              onMouseDown={(e) => {
                e.preventDefault();
                choose(s);
              }}
            >
              {s.label}
            </li>
          ))}
          {isFetching && suggestions.length === 0 && <li className="muted">Searching…</li>}
        </ul>
      )}
    </div>
  );
}

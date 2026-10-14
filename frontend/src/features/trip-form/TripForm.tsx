import { useState } from 'react';

import type { PlaceInput, TripRequest } from '../../api/types';
import { defaultDeparture, toLocalInputValue } from '../../lib/format';
import { PlaceField } from './PlaceField';

const MAX_LOAD_LB = 120_000;
const INTERVALS = [10, 25, 50] as const;

interface Props {
  loading: boolean;
  onSubmit: (request: TripRequest) => void;
}

export function TripForm({ loading, onSubmit }: Props) {
  const [origin, setOrigin] = useState<PlaceInput>({ label: '' });
  const [destination, setDestination] = useState<PlaceInput>({ label: '' });
  const [departure, setDeparture] = useState(() => toLocalInputValue(defaultDeparture()));
  const [load, setLoad] = useState('40000');
  const [interval, setIntervalMi] = useState<(typeof INTERVALS)[number]>(25);
  const [error, setError] = useState<string | null>(null);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const loadLb = Number(load);
    const when = new Date(departure);
    if (!origin.label.trim() || !destination.label.trim()) {
      return setError('Enter both an origin and a destination.');
    }
    if (Number.isNaN(when.getTime())) return setError('Choose a valid departure date and time.');
    if (!Number.isFinite(loadLb) || loadLb < 0 || loadLb > MAX_LOAD_LB) {
      return setError(`Load weight must be between 0 and ${MAX_LOAD_LB.toLocaleString()} lb.`);
    }
    setError(null);
    onSubmit({
      origin,
      destination,
      departure: when.toISOString(),
      load_lb: loadLb,
      interval_mi: interval,
    });
  }

  function fillExample() {
    setOrigin({ label: 'Chicago, IL' });
    setDestination({ label: 'Denver, CO' });
    setLoad('42000');
    setError(null);
  }

  return (
    <form className="trip-form" onSubmit={submit} noValidate>
      <PlaceField
        label="Origin"
        value={origin}
        onChange={setOrigin}
        placeholder="City or address"
      />
      <PlaceField
        label="Destination"
        value={destination}
        onChange={setDestination}
        placeholder="City or address"
      />
      <div className="row">
        <div className="field">
          <label htmlFor="departure">Departure</label>
          <input
            id="departure"
            type="datetime-local"
            value={departure}
            onChange={(e) => setDeparture(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="load">Load weight (lb)</label>
          <input
            id="load"
            type="number"
            inputMode="numeric"
            min={0}
            max={MAX_LOAD_LB}
            step={500}
            value={load}
            onChange={(e) => setLoad(e.target.value)}
          />
        </div>
      </div>
      <fieldset className="field">
        <legend>Weather checkpoint spacing</legend>
        <div className="segmented" role="radiogroup">
          {INTERVALS.map((mi) => (
            <label key={mi} className={interval === mi ? 'selected' : undefined}>
              <input
                type="radio"
                name="interval"
                checked={interval === mi}
                onChange={() => setIntervalMi(mi)}
              />
              {mi} mi
            </label>
          ))}
        </div>
      </fieldset>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div className="actions">
        <button type="submit" className="primary" disabled={loading}>
          {loading ? 'Analyzing routes…' : 'Find safest route'}
        </button>
        <button type="button" className="link" onClick={fillExample} disabled={loading}>
          Try an example
        </button>
      </div>
    </form>
  );
}

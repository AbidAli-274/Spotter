import { useState } from 'react';

import type { Route } from '../../api/types';
import { formatDateTime, formatDuration, formatMiles } from '../../lib/format';
import { riskColor, riskLabel } from '../../lib/risk';
import { CheckpointTable } from './CheckpointTable';
import { RiskBar } from './RiskBar';

interface Props {
  route: Route;
  color: string;
  selected: boolean;
  onSelect: () => void;
}

export function RouteCard({ route, color, selected, onSelect }: Props) {
  const [expanded, setExpanded] = useState(false);
  const { metrics } = route;
  return (
    <article
      className={`route-card${selected ? ' selected' : ''}`}
      style={{ borderLeftColor: color }}
    >
      <button type="button" className="route-head" onClick={onSelect} aria-pressed={selected}>
        <span className="route-title">
          <span className="swatch" style={{ background: color }} />
          <strong>{route.name}</strong>
          {route.recommended && <span className="badge">Recommended</span>}
        </span>
        <span className="pill" style={{ background: riskColor(metrics.worst_level) }}>
          Worst: {riskLabel(metrics.worst_level)}
        </span>
      </button>
      {route.summary && <p className="muted small">{route.summary}</p>}
      <dl className="stats">
        <div>
          <dt>Distance</dt>
          <dd>{formatMiles(route.distance_mi)}</dd>
        </div>
        <div>
          <dt>Drive time</dt>
          <dd>{formatDuration(route.duration_s)}</dd>
        </div>
        <div>
          <dt>Arrive</dt>
          <dd>{formatDateTime(route.arrival)}</dd>
        </div>
        <div>
          <dt>Severe mi</dt>
          <dd>{Math.round(metrics.miles_by_level.severe)}</dd>
        </div>
        <div>
          <dt>High mi</dt>
          <dd>{Math.round(metrics.miles_by_level.high)}</dd>
        </div>
        <div>
          <dt>Avg risk</dt>
          <dd>{metrics.avg_risk.toFixed(2)} / 4</dd>
        </div>
      </dl>
      <RiskBar metrics={metrics} total={route.distance_mi} />
      {metrics.miles_by_level.no_travel > 0 && (
        <p className="warning">
          ⚠ {Math.round(metrics.miles_by_level.no_travel)} mi of No Travel conditions on this
          route.
        </p>
      )}
      {metrics.unknown_miles > 0 && (
        <p className="muted small">
          Forecast unavailable for {Math.round(metrics.unknown_miles)} mi (beyond forecast range).
        </p>
      )}
      <button
        type="button"
        className="link"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        {expanded ? 'Hide' : 'Show'} {route.checkpoints.length} checkpoints
      </button>
      {expanded && <CheckpointTable route={route} />}
    </article>
  );
}

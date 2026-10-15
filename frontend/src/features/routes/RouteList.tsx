import type { TripAnalysis } from '../../api/types';
import { ROUTE_COLORS } from '../../lib/risk';
import { RouteCard } from './RouteCard';

interface Props {
  analysis: TripAnalysis;
  selectedId: string;
  onSelect: (id: string) => void;
}

export function RouteList({ analysis, selectedId, onSelect }: Props) {
  const { recommendation, routes } = analysis;
  const best = routes.find((r) => r.id === recommendation.route_id);
  return (
    <section aria-label="Route options" className="route-list">
      <div className={`recommendation${recommendation.all_blocked ? ' blocked' : ''}`}>
        <strong>
          {recommendation.all_blocked ? 'No safe route right now' : `Recommended: ${best?.name}`}
        </strong>
        <p>{recommendation.reason}</p>
      </div>
      <p className="muted small source-note">
        {analysis.weather_source === 'met-norway'
          ? 'Forecast: MET Norway (backup provider). Snowfall is estimated from precipitation and temperature.'
          : 'Forecast: Open-Meteo.'}
      </p>
      {routes.map((route, i) => (
        <RouteCard
          key={route.id}
          route={route}
          color={ROUTE_COLORS[i % ROUTE_COLORS.length]}
          selected={route.id === selectedId}
          onSelect={() => onSelect(route.id)}
        />
      ))}
    </section>
  );
}

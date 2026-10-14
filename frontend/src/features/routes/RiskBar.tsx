import type { RouteMetrics } from '../../api/types';
import { RISK_COLOR, RISK_LABEL, RISK_ORDER, UNKNOWN_COLOR } from '../../lib/risk';

export function RiskBar({ metrics, total }: { metrics: RouteMetrics; total: number }) {
  const parts = [
    ...RISK_ORDER.map((k) => ({
      key: k,
      label: RISK_LABEL[k],
      miles: metrics.miles_by_level[k],
      color: RISK_COLOR[k],
    })),
    { key: 'unknown', label: 'Unknown', miles: metrics.unknown_miles, color: UNKNOWN_COLOR },
  ].filter((p) => p.miles > 0);

  return (
    <div
      className="risk-bar"
      role="img"
      aria-label={parts.map((p) => `${p.label}: ${Math.round(p.miles)} miles`).join(', ')}
    >
      {parts.map((p) => (
        <span
          key={p.key}
          title={`${p.label}: ${Math.round(p.miles)} mi`}
          style={{ width: `${(p.miles / total) * 100}%`, background: p.color }}
        />
      ))}
    </div>
  );
}

import type { Route } from '../../api/types';
import { formatShortDateTime } from '../../lib/format';
import { riskColor, riskLabel } from '../../lib/risk';

export function CheckpointTable({ route }: { route: Route }) {
  return (
    <div className="table-wrap">
      <table className="checkpoints">
        <thead>
          <tr>
            <th>Mile</th>
            <th>ETA</th>
            <th>Wind</th>
            <th>Rain</th>
            <th>Snow</th>
            <th>Risk</th>
          </tr>
        </thead>
        <tbody>
          {route.checkpoints.map((c) => (
            <tr key={c.index}>
              <td>{Math.round(c.mile)}</td>
              <td>{formatShortDateTime(c.eta)}</td>
              <td>{c.weather ? `${c.weather.wind_mph.toFixed(0)} mph` : '—'}</td>
              <td>{c.weather ? `${c.weather.rain_in_hr.toFixed(2)}` : '—'}</td>
              <td>{c.weather ? `${c.weather.snow_in_hr.toFixed(2)}` : '—'}</td>
              <td>
                <span className="pill" style={{ background: riskColor(c.risk) }}>
                  {riskLabel(c.risk)}
                </span>
                {c.load_adjusted && (
                  <span className="load-flag" title="Heavy load raised this risk level">
                    ⚖
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="muted small">Rain and snow in inches per hour. ⚖ = raised by load rules.</p>
    </div>
  );
}

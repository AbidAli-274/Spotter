import type { RiskKey } from '../api/types';

export const RISK_ORDER: RiskKey[] = ['low', 'moderate', 'high', 'severe', 'no_travel'];

export const RISK_LABEL: Record<RiskKey, string> = {
  low: 'Low',
  moderate: 'Moderate',
  high: 'High',
  severe: 'Severe',
  no_travel: 'No Travel',
};

export const RISK_COLOR: Record<RiskKey, string> = {
  low: '#2f9e63',
  moderate: '#e0b400',
  high: '#f08a24',
  severe: '#d93f3f',
  no_travel: '#6d1a8c',
};

export const UNKNOWN_COLOR = '#8b95a5';

/** Colors indexed by numeric risk 0-4, for MapLibre expressions. */
export const RISK_COLORS_BY_VALUE = RISK_ORDER.map((k) => RISK_COLOR[k]);

export const ROUTE_COLORS = ['#1d4ed8', '#7c3aed', '#0e7490'];

export function riskLabel(risk: RiskKey | null): string {
  return risk ? RISK_LABEL[risk] : 'Unknown';
}

export function riskColor(risk: RiskKey | null): string {
  return risk ? RISK_COLOR[risk] : UNKNOWN_COLOR;
}

import type { ExpressionSpecification } from 'maplibre-gl';

import { RISK_COLORS_BY_VALUE, UNKNOWN_COLOR } from '../../lib/risk';

/** Free vector basemap (no API key). */
export const BASEMAP_STYLE = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json';

/** Color expression for a numeric `risk_value` / `level` property (0-4, else unknown). */
export const riskColorExpression = (prop: string): ExpressionSpecification => [
  'match',
  ['get', prop],
  0,
  RISK_COLORS_BY_VALUE[0],
  1,
  RISK_COLORS_BY_VALUE[1],
  2,
  RISK_COLORS_BY_VALUE[2],
  3,
  RISK_COLORS_BY_VALUE[3],
  4,
  RISK_COLORS_BY_VALUE[4],
  UNKNOWN_COLOR,
];

export const HEATMAP_COLOR: ExpressionSpecification = [
  'interpolate',
  ['linear'],
  ['heatmap-density'],
  0,
  'rgba(47,158,99,0)',
  0.08,
  'rgba(47,158,99,0.35)',
  0.25,
  'rgba(224,180,0,0.55)',
  0.45,
  'rgba(240,138,36,0.65)',
  0.7,
  'rgba(217,63,63,0.75)',
  1,
  'rgba(109,26,140,0.85)',
];

/** Kernel radius scales with zoom so coverage stays continuous between ~15-mile sample points. */
export const HEATMAP_RADIUS: ExpressionSpecification = [
  'interpolate',
  ['exponential', 2],
  ['zoom'],
  3,
  8,
  5,
  24,
  7,
  80,
  9,
  300,
];

export const HEATMAP_WEIGHT: ExpressionSpecification = [
  'interpolate',
  ['linear'],
  ['get', 'level'],
  0,
  0.06,
  1,
  0.25,
  2,
  0.5,
  3,
  0.8,
  4,
  1,
];

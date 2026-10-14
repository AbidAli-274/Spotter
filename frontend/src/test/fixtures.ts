import type { Heatmap, Route } from '../api/types';

export const route: Route = {
  id: 'route-1',
  name: 'Route A',
  summary: 'via I-80',
  distance_mi: 200,
  duration_s: 4 * 3600,
  arrival: '2026-10-15T01:00:00Z',
  rank: 1,
  recommended: true,
  geometry: [
    [-100, 40],
    [-100, 43],
  ],
  metrics: {
    miles_by_level: { low: 150, moderate: 20, high: 10, severe: 15, no_travel: 5 },
    unknown_miles: 0,
    avg_risk: 0.52,
    worst_level: 'no_travel',
  },
  checkpoints: [
    {
      index: 0,
      mile: 0,
      lat: 40,
      lon: -100,
      eta: '2026-10-14T21:00:00Z',
      weather: { wind_mph: 12, rain_in_hr: 0, snow_in_hr: 0 },
      risk: 'low',
      risk_value: 0,
      drivers: [],
      load_adjusted: false,
    },
    {
      index: 1,
      mile: 200,
      lat: 43,
      lon: -100,
      eta: '2026-10-15T01:00:00Z',
      weather: null,
      risk: null,
      risk_value: -1,
      drivers: [],
      load_adjusted: false,
    },
  ],
};

export const heatmap: Heatmap = {
  start: '2026-10-14T21:00:00Z',
  hours: 4,
  points: [
    { lat: 40, lon: -100, levels: [0, 2, 4, -1] },
    { lat: 41, lon: -100, levels: [1, 3, 0, -1] },
  ],
};

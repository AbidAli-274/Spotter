export type RiskKey = 'low' | 'moderate' | 'high' | 'severe' | 'no_travel';

export interface Place {
  label: string;
  lat: number;
  lon: number;
}

export interface PlaceInput {
  label: string;
  lat?: number;
  lon?: number;
}

export interface TripRequest {
  origin: PlaceInput;
  destination: PlaceInput;
  /** ISO 8601 */
  departure: string;
  load_lb: number;
  interval_mi: 10 | 25 | 50;
}

export interface Weather {
  wind_mph: number;
  rain_in_hr: number;
  snow_in_hr: number;
}

export interface Checkpoint {
  index: number;
  mile: number;
  lat: number;
  lon: number;
  eta: string;
  weather: Weather | null;
  risk: RiskKey | null;
  /** 0-4, or -1 when weather is unavailable */
  risk_value: number;
  drivers: string[];
  load_adjusted: boolean;
}

export interface RouteMetrics {
  miles_by_level: Record<RiskKey, number>;
  unknown_miles: number;
  avg_risk: number;
  worst_level: RiskKey | null;
}

export interface Route {
  id: string;
  name: string;
  summary: string;
  distance_mi: number;
  duration_s: number;
  arrival: string;
  rank: number;
  recommended: boolean;
  /** [lon, lat] pairs */
  geometry: [number, number][];
  metrics: RouteMetrics;
  checkpoints: Checkpoint[];
}

export interface HeatmapPoint {
  lat: number;
  lon: number;
  /** risk 0-4 per forecast hour, -1 = unknown */
  levels: number[];
}

export interface Heatmap {
  start: string;
  hours: number;
  points: HeatmapPoint[];
}

export interface TripAnalysis {
  origin: Place;
  destination: Place;
  departure: string;
  load_lb: number;
  interval_mi: number;
  recommendation: { route_index: number; route_id: string; reason: string; all_blocked: boolean };
  routes: Route[];
  heatmap: Heatmap;
  weather_source: 'open-meteo' | 'met-norway';
}

export interface ApiErrorBody {
  error: { code: string; message: string; details?: unknown };
}

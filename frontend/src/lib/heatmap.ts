import type { Heatmap } from '../api/types';

export interface HeatFeatureCollection {
  type: 'FeatureCollection';
  features: {
    type: 'Feature';
    properties: { level: number };
    geometry: { type: 'Point'; coordinates: [number, number] };
  }[];
}

/** GeoJSON for one forecast hour. Unknown (-1) is clamped to 0 so it adds no heat. */
export function heatmapFrame(heatmap: Heatmap, hour: number): HeatFeatureCollection {
  const h = Math.min(Math.max(hour, 0), heatmap.hours - 1);
  return {
    type: 'FeatureCollection',
    features: heatmap.points.map((p) => ({
      type: 'Feature',
      properties: { level: Math.max(p.levels[h] ?? 0, 0) },
      geometry: { type: 'Point', coordinates: [p.lon, p.lat] },
    })),
  };
}

export function hourLabel(heatmap: Heatmap, hour: number): string {
  const when = new Date(new Date(heatmap.start).getTime() + hour * 3_600_000);
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    hour: 'numeric',
    timeZoneName: 'short',
  }).format(when);
}

/** Worst level across the whole corridor in a given hour (for the slider's mini-chart). */
export function worstLevelByHour(heatmap: Heatmap): number[] {
  return Array.from({ length: heatmap.hours }, (_, h) =>
    heatmap.points.reduce((worst, p) => Math.max(worst, p.levels[h] ?? -1), -1),
  );
}

import type { FeatureCollection } from 'geojson';
import maplibregl, { type GeoJSONSource, type Map as MapLibreMap } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useEffect, useMemo, useRef, useState } from 'react';

import type { Checkpoint, Route, TripAnalysis } from '../../api/types';
import { formatDateTime, formatMiles } from '../../lib/format';
import { heatmapFrame } from '../../lib/heatmap';
import { RISK_LABEL, RISK_ORDER, ROUTE_COLORS, riskColor, riskLabel } from '../../lib/risk';
import {
  BASEMAP_STYLE,
  HEATMAP_COLOR,
  HEATMAP_RADIUS,
  HEATMAP_WEIGHT,
  riskColorExpression,
} from './mapStyle';

interface Props {
  analysis: TripAnalysis | null;
  selectedId: string;
  onSelectRoute: (id: string) => void;
  heatmapHour: number;
  showHeatmap: boolean;
}

const EMPTY: FeatureCollection = { type: 'FeatureCollection', features: [] };

function routesGeoJSON(routes: Route[]) {
  return {
    type: 'FeatureCollection' as const,
    features: routes.map((r, i) => ({
      type: 'Feature' as const,
      properties: { id: r.id, color: ROUTE_COLORS[i % ROUTE_COLORS.length] },
      geometry: { type: 'LineString' as const, coordinates: r.geometry },
    })),
  };
}

function checkpointsGeoJSON(routes: Route[]) {
  return {
    type: 'FeatureCollection' as const,
    features: routes.flatMap((r) =>
      r.checkpoints.map((c) => ({
        type: 'Feature' as const,
        properties: { route: r.id, index: c.index, risk_value: c.risk_value },
        geometry: { type: 'Point' as const, coordinates: [c.lon, c.lat] },
      })),
    ),
  };
}

function marker(kind: 'origin' | 'destination', label: string) {
  const el = document.createElement('div');
  el.className = `pin pin-${kind}`;
  el.textContent = kind === 'origin' ? 'A' : 'B';
  el.title = label;
  return el;
}

function popupHtml(route: Route, c: Checkpoint): string {
  const w = c.weather;
  const weather = w
    ? `Wind ${w.wind_mph.toFixed(0)} mph · Rain ${w.rain_in_hr.toFixed(2)} in/hr · Snow ${w.snow_in_hr.toFixed(2)} in/hr`
    : 'Forecast unavailable';
  const drivers = c.drivers.length ? `<div class="pop-drivers">${c.drivers.join(' · ')}</div>` : '';
  return `<div class="pop">
    <div class="pop-title">${route.name} · mile ${Math.round(c.mile)}</div>
    <div>ETA ${formatDateTime(c.eta)}</div>
    <div>${weather}</div>
    <div class="pop-risk"><span class="dot" style="background:${riskColor(c.risk)}"></span>${riskLabel(c.risk)}</div>
    ${drivers}
  </div>`;
}

export function MapView({ analysis, selectedId, onSelectRoute, heatmapHour, showHeatmap }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const [ready, setReady] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);

  // Latest props for long-lived map event handlers.
  const analysisRef = useRef(analysis);
  const onSelectRef = useRef(onSelectRoute);
  analysisRef.current = analysis;
  onSelectRef.current = onSelectRoute;

  // --- one-time map + layer setup -------------------------------------------------
  useEffect(() => {
    if (!container.current) return;
    let map: MapLibreMap;
    try {
      map = new maplibregl.Map({
        container: container.current,
        style: BASEMAP_STYLE,
        center: [-96, 38.5],
        zoom: 3.4,
        attributionControl: { compact: true },
      });
    } catch {
      setMapError('The map needs WebGL, which is unavailable in this browser.');
      return;
    }
    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
    map.on('error', (e) => console.warn('[map]', e.error?.message ?? e));

    map.on('load', () => {
      map.addSource('heat', { type: 'geojson', data: EMPTY });
      map.addLayer({
        id: 'heat-layer',
        type: 'heatmap',
        source: 'heat',
        paint: {
          'heatmap-weight': HEATMAP_WEIGHT,
          'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 3, 0.7, 9, 1.4],
          'heatmap-color': HEATMAP_COLOR,
          'heatmap-radius': HEATMAP_RADIUS,
          'heatmap-opacity': 0.9,
        },
      });
      map.addLayer({
        id: 'heat-dots',
        type: 'circle',
        source: 'heat',
        minzoom: 5.5,
        paint: {
          'circle-radius': 3.5,
          'circle-color': riskColorExpression('level'),
          'circle-opacity': 0.55,
          'circle-stroke-width': 1,
          'circle-stroke-color': '#fff',
        },
      });

      map.addSource('routes', { type: 'geojson', data: EMPTY });
      map.addLayer({
        id: 'route-casing',
        type: 'line',
        source: 'routes',
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': '#fff', 'line-width': 8 },
      });
      map.addLayer({
        id: 'route-line',
        type: 'line',
        source: 'routes',
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': ['get', 'color'], 'line-width': 5 },
      });

      map.addSource('checkpoints', { type: 'geojson', data: EMPTY });
      map.addLayer({
        id: 'checkpoint-layer',
        type: 'circle',
        source: 'checkpoints',
        paint: {
          'circle-radius': 6,
          'circle-color': riskColorExpression('risk_value'),
          'circle-stroke-width': 2,
          'circle-stroke-color': '#fff',
        },
      });

      const popup = new maplibregl.Popup({ closeButton: false, offset: 10, maxWidth: '280px' });
      map.on('mouseenter', 'checkpoint-layer', () => (map.getCanvas().style.cursor = 'pointer'));
      map.on('mouseleave', 'checkpoint-layer', () => (map.getCanvas().style.cursor = ''));
      map.on('click', 'checkpoint-layer', (e) => {
        const props = e.features?.[0]?.properties;
        const route = analysisRef.current?.routes.find((r) => r.id === props?.route);
        const checkpoint = route?.checkpoints[Number(props?.index)];
        if (!route || !checkpoint) return;
        popup
          .setLngLat([checkpoint.lon, checkpoint.lat])
          .setHTML(popupHtml(route, checkpoint))
          .addTo(map);
      });
      map.on('mouseenter', 'route-line', () => (map.getCanvas().style.cursor = 'pointer'));
      map.on('mouseleave', 'route-line', () => (map.getCanvas().style.cursor = ''));
      map.on('click', 'route-line', (e) => {
        if (map.queryRenderedFeatures(e.point, { layers: ['checkpoint-layer'] }).length) return;
        const id = e.features?.[0]?.properties?.id;
        if (typeof id === 'string') onSelectRef.current(id);
      });
      setReady(true);
    });

    const resize = new ResizeObserver(() => map.resize());
    resize.observe(container.current);
    return () => {
      resize.disconnect();
      map.remove();
      mapRef.current = null;
      setReady(false);
    };
  }, []);

  // --- new analysis: data, markers, viewport -----------------------------------------
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    (map.getSource('routes') as GeoJSONSource).setData(
      analysis ? routesGeoJSON(analysis.routes) : EMPTY,
    );
    (map.getSource('checkpoints') as GeoJSONSource).setData(
      analysis ? checkpointsGeoJSON(analysis.routes) : EMPTY,
    );
    if (!analysis) return;

    const markers = [
      new maplibregl.Marker({ element: marker('origin', analysis.origin.label) })
        .setLngLat([analysis.origin.lon, analysis.origin.lat])
        .addTo(map),
      new maplibregl.Marker({ element: marker('destination', analysis.destination.label) })
        .setLngLat([analysis.destination.lon, analysis.destination.lat])
        .addTo(map),
    ];
    const bounds = new maplibregl.LngLatBounds();
    analysis.routes.forEach((r) => r.geometry.forEach((p) => bounds.extend(p)));
    // Leave room at the bottom for the heatmap slider panel overlaying the map.
    map.fitBounds(bounds, {
      padding: { top: 60, left: 50, right: 50, bottom: 190 },
      duration: 800,
      maxZoom: 11,
    });
    return () => markers.forEach((m) => m.remove());
  }, [analysis, ready]);

  // --- selection emphasis (paint only: no data re-tiling) ----------------------------
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const isSel: maplibregl.ExpressionSpecification = ['==', ['get', 'id'], selectedId];
    map.setPaintProperty('route-line', 'line-width', ['case', isSel, 6, 3.5]);
    map.setPaintProperty('route-line', 'line-opacity', ['case', isSel, 1, 0.55]);
    map.setPaintProperty('route-casing', 'line-width', ['case', isSel, 9, 6]);
    map.setLayoutProperty('route-line', 'line-sort-key', ['case', isSel, 1, 0]);
    map.setLayoutProperty('route-casing', 'line-sort-key', ['case', isSel, 1, 0]);
    const isSelCp: maplibregl.ExpressionSpecification = ['==', ['get', 'route'], selectedId];
    map.setPaintProperty('checkpoint-layer', 'circle-radius', ['case', isSelCp, 6.5, 3.5]);
    map.setPaintProperty('checkpoint-layer', 'circle-opacity', ['case', isSelCp, 1, 0.6]);
    map.setPaintProperty('checkpoint-layer', 'circle-stroke-width', ['case', isSelCp, 2, 1]);
  }, [selectedId, ready, analysis]);

  // --- heatmap frame: swap one small GeoJSON per slider tick -------------------------
  const frame = useMemo(
    () => (analysis ? heatmapFrame(analysis.heatmap, heatmapHour) : EMPTY),
    [analysis, heatmapHour],
  );
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    (map.getSource('heat') as GeoJSONSource).setData(frame);
  }, [frame, ready]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const visibility = showHeatmap ? 'visible' : 'none';
    map.setLayoutProperty('heat-layer', 'visibility', visibility);
    map.setLayoutProperty('heat-dots', 'visibility', visibility);
  }, [showHeatmap, ready]);

  return (
    <div className="map-shell">
      <div ref={container} className="map" role="application" aria-label="Route map" />
      {mapError && <div className="map-loading">{mapError}</div>}
      {analysis && (
        <div className="map-legend" aria-label="Risk legend">
          {RISK_ORDER.map((k) => (
            <span key={k}>
              <i style={{ background: riskColor(k) }} />
              {RISK_LABEL[k]}
            </span>
          ))}
        </div>
      )}
      {analysis && (
        <div className="map-caption">
          {analysis.origin.label} → {analysis.destination.label} ·{' '}
          {formatMiles(analysis.routes.find((r) => r.id === selectedId)?.distance_mi ?? 0)}
        </div>
      )}
    </div>
  );
}

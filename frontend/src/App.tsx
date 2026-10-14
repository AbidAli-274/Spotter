import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Suspense, lazy, useCallback, useState } from 'react';

import type { TripAnalysis } from './api/types';
import { HeatmapControls } from './features/heatmap/HeatmapControls';
import { RouteList } from './features/routes/RouteList';
import { TripForm } from './features/trip-form/TripForm';
import { useAnalyzeTrip } from './hooks/useAnalyzeTrip';

// MapLibre is large; load it after the form is interactive.
const MapView = lazy(() => import('./features/map/MapView').then((m) => ({ default: m.MapView })));

const queryClient = new QueryClient();

function Planner() {
  const mutation = useAnalyzeTrip();
  const [analysis, setAnalysis] = useState<TripAnalysis | null>(null);
  const [selectedId, setSelectedId] = useState('');
  const [hour, setHour] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [showHeatmap, setShowHeatmap] = useState(true);

  const onSubmit = useCallback(
    (request: Parameters<typeof mutation.mutate>[0]) => {
      setPlaying(false);
      mutation.mutate(request, {
        onSuccess: (result) => {
          setAnalysis(result);
          setSelectedId(result.recommendation.route_id);
          setHour(0);
        },
      });
    },
    [mutation],
  );

  return (
    <div className="app">
      <aside className="sidebar">
        <header className="brand">
          <h1>Weather-Aware Truck Routing</h1>
          <p>Compare routes by weather risk, load and travel time.</p>
        </header>
        <TripForm loading={mutation.isPending} onSubmit={onSubmit} />
        {mutation.isError && (
          <div className="alert" role="alert">
            {mutation.error.message}
          </div>
        )}
        {mutation.isPending && (
          <p className="muted pending">Finding routes and checking the forecast along each one…</p>
        )}
        {analysis && (
          <RouteList analysis={analysis} selectedId={selectedId} onSelect={setSelectedId} />
        )}
      </aside>
      <main className="stage">
        <Suspense fallback={<div className="map-loading">Loading map…</div>}>
          <MapView
            analysis={analysis}
            selectedId={selectedId}
            onSelectRoute={setSelectedId}
            heatmapHour={hour}
            showHeatmap={showHeatmap}
          />
        </Suspense>
        {analysis && (
          <HeatmapControls
            heatmap={analysis.heatmap}
            hour={hour}
            onHourChange={setHour}
            playing={playing}
            onPlayingChange={setPlaying}
            visible={showHeatmap}
            onVisibleChange={setShowHeatmap}
          />
        )}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Planner />
    </QueryClientProvider>
  );
}

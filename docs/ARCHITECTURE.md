# Architecture

```
React (Vite, MapLibre)  ──/api──▶  Django + DRF
                                     │
                    trips.services.TripAnalyzer  (orchestration)
                    ┌────────────┬────────────┬────────────┐
                    ▼            ▼            ▼            ▼
                 routing       weather       risk       (pure, no I/O)
              ORS client    Open-Meteo     rules · metrics · ranking
              + geometry      client
                    └────── Django cache (SQLite table) ──────┘
```

## Request flow (`POST /api/trips/analyze/`)

1. Validate input (DRF serializer) and the departure window (not in the past, within the ~15-day forecast).
2. Resolve places (geocode only when coordinates weren't chosen from autocomplete).
3. **Generate routes** (`routing/alternatives.py`): native ORS alternatives for short trips; via-point corridors for long ones, filtered by overlap and detour ratio. Via-point calls run concurrently.
4. **Checkpoints** every N miles with ETA from the route's distance→time curve.
5. **One batched weather fetch** for all checkpoints and heatmap points (≤ 50 locations per request, requests in parallel, per-location cache).
6. Score each checkpoint, compute mileage-weighted metrics, rank and explain.
7. Serialize routes, checkpoints, recommendation and the 48 h heatmap in one gzip-compressed response.

## Design decisions

- **`risk` is framework-free.** It has no Django, HTTP or clock dependencies, so the logic that carries the most weight is deterministic and exhaustively unit-tested (every threshold boundary and load rule).
- **Providers sit behind small clients** (`OrsClient`, `OpenMeteoClient`) that are injected into `TripAnalyzer`, so tests use fakes and swapping a provider touches one module.
- **Why via-points?** ORS rejects `alternative_routes` for trips over 100 km (error 2004; verified against the live API for `driving-hgv`). Offsetting a via-point perpendicular to the trip (10% then 22% of the straight-line distance, both sides) yields distinct corridors; candidates over 1.6× the fastest distance or overlapping a chosen route by ≥ 75% are dropped.
- **ETA accuracy.** Time knots come from per-maneuver durations, not average speed, so a checkpoint's ETA reflects slow urban legs.
- **Unknown ≠ safe.** Missing forecast data yields `null` risk, tracked as unknown miles and excluded from averages.
- **Structured errors.** Domain errors carry stable codes (`location_not_found`, `route_not_found`, `forecast_out_of_range`, `upstream_unavailable`).

## Weather provider resilience

`ResilientWeatherClient` tries Open-Meteo (batched, 15-day horizon) and on any upstream failure (notably HTTP 429 when a shared host's IP exhausts the free daily allowance) serves the request from MET Norway. A 10-minute cooldown flag in the cache sends later requests straight to the fallback so users aren't made to wait on a failing provider. Both clients return the same `HourlySeries`, so the risk engine is unaware of the source; the API reports it as `weather_source`.

## Caching

A Django `DatabaseCache` (SQLite) keeps data across restarts without extra infrastructure:

| Data | TTL |
|---|---|
| Geocoding / autocomplete | 30 days |
| Routes (keyed by request body) | 7 days |
| Weather (per location and date window) | 30 min |

ORS and Open-Meteo calls get one retry on transport errors and 5xx responses.

## Frontend performance

- **GPU rendering.** Routes, checkpoints and the heatmap are MapLibre layers, not DOM markers.
- **Selection is a paint update.** Switching routes changes an expression on existing layers; no data is re-tiled.
- **Slider has no network cost.** All 48 hourly frames arrive with the analysis. Each tick swaps a ~100-feature GeoJSON source.
- **Lazy map chunk.** The ~800 kB MapLibre bundle loads after the form is interactive. Responses are gzip-compressed (~175 KB → ~25 KB for a cross-country trip).
- **Graceful fallback.** Missing WebGL shows a message instead of breaking the page.

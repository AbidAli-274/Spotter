# Risk rules

## Thresholds

| Condition | Low | Moderate | High | Severe | No Travel |
|---|---|---|---|---|---|
| Wind (mph) | < 25 | 25–34 | 35–44 | 45–54 | ≥ 55 |
| Rain (in/hr) | < 0.10 | 0.10–0.25 | 0.25–0.50 | 0.50–1.00 | > 1.00 |
| Snow (in/hr) | < 0.5 | 0.5–1.0 | 1.0–2.0 | 2.0–3.0 | > 3.0 |

### Boundary conventions

The table is ambiguous at shared edges, so the code makes these choices (all covered by tests in `backend/tests/test_risk_rules.py`):

- **Lower bounds are inclusive.** Wind 25.0 mph is Moderate; rain 0.10 in/hr is Moderate.
- **Shared edges take the more severe band** (rain 0.25 → High, 0.50 → Severe; snow 1.0 → High, 2.0 → Severe). For a safety tool, rounding up is the conservative choice.
- **No Travel for rain/snow is strictly greater** than 1.00 / 3.0, exactly as written, so rain of exactly 1.00 in/hr is Severe. Wind No Travel is ≥ 55 mph.
- Wind bands are continuous in mph (34.9 is Moderate, 35.0 is High).

## Load rules

Applied to the wind level only, and they only ever **raise** a level:

| Wind | Load | Result |
|---|---|---|
| ≥ 55 mph | any | No Travel |
| 45–54 mph | > 30,000 lb | No Travel |
| 35–44 mph | > 40,000 lb | at least Severe |

Load thresholds are strict (exactly 30,000 lb is not "over" 30,000). A checkpoint's level is the **worst of wind (after load rules), rain and snow**.

## Route metrics

Each checkpoint owns the road between the midpoints to its neighbours (the first starts at mile 0, the last ends at the destination), so segment lengths sum exactly to the route length. From that:

- miles at each risk level (the Severe and High miles used for ranking),
- **average risk** — mileage-weighted mean of levels on a 0 (Low) … 4 (No Travel) scale,
- unknown miles (no forecast) — excluded from the average, never counted as safe.

## Recommendation

Strict lexicographic order, per the brief:

1. fewest **No Travel** miles (a route that can't be driven always loses to one that can; if every route has No Travel the least-bad one is returned with a warning),
2. fewest **Severe** miles,
3. fewest **High** miles,
4. lowest **average risk**,
5. **shortest travel time**.

Values are compared at the precision the UI displays (0.1 mi, 0.01 risk), so a route is never preferred for a difference shown as equal. Strict ordering was chosen over a weighted score because it is exactly what the brief specifies and is easy to explain: the response includes the deciding factor, e.g. _"Fewest Severe miles: 0 mi vs 14 and 22 mi on the alternatives."_

## Weather inputs (Open-Meteo)

| Risk input | Source variable | Conversion |
|---|---|---|
| Wind | `wind_speed_10m` (sustained) | requested in mph |
| Rain | `rain` + `showers` | requested in inches per hour |
| Snow | `snowfall` | requested in inches per hour |

Checkpoint weather is the hourly value nearest `departure + elapsed driving time`.

# Loom walkthrough (target ~7 min)

**0:00 – Problem and demo (1 min)** · Open the live app. Enter Chicago → Denver, a 42,000 lb load, departing soon. Click _Find safest route_. Point out the three routes on the map, the recommendation banner and its reason.

**1:00 – Reading the results (1.5 min)** · Select each route card. Show Severe/High miles, average risk, the stacked risk bar. Expand a checkpoint table: ETA and weather at each checkpoint. Click a checkpoint on the map for the popup. Switch checkpoint spacing 25 → 10 mi to show denser sampling.

**2:30 – Heatmap (1 min)** · Drag the 0–48 h slider; press play. Note hour 0 = departure and the strip showing the worst corridor risk per hour. Toggle the heatmap off/on. Mention that scrubbing makes no network requests.

**3:30 – Risk logic (1.5 min)** · Open `backend/apps/risk/rules.py` and `docs/RISK_RULES.md`: thresholds, load escalation, boundary conventions. Show `tests/test_risk_rules.py` (boundary table). Change the load from 38,000 to 45,000 lb on a windy trip and show the same wind becoming Severe / No Travel.

**5:00 – Routing and ETA (1 min)** · `routing/alternatives.py`: ORS caps native alternatives at 100 km, so long trips use perpendicular via-points with an overlap filter. `sampling.py`: ETA from per-maneuver durations, so weather is sampled when the truck actually arrives.

**6:00 – Engineering (1 min)** · Architecture diagram, pure `risk` module, caching, Docker Compose, CI, test counts, `git log --graph` showing the step-by-step history.

**7:00 – Trade-offs / next steps** · Gusts, hazmat/bridge restrictions, time-zone-aware ETAs, user accounts and saved trips.

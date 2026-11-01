---
name: Travel / vlog / map story
description: Travel videos, trip recaps, vlogs and journey stories — animated map routes, pins and location tags, photo/clip sequences with slow cinematic moves, day-by-day structure.
---

# Travel & map stories

Starting point: `$VS new DIR --example travel_map` (9:16, style `cinematic`; `vintage` for nostalgic, `minimal` for clean).

## Building blocks
- **Route map**: map image full frame → dashed `path` with `curve`, drawn with `progress` over 2–4 s → a moving marker
  (circle with `animate.x/y` keyed at the same times as the path points) → `kit.map_pin` at stops (labels "Day 1"…).
  Zoom the camera along the route for long trips.
- **Arrival title**: `kit.location_tag` (place + date/altitude/distance) at the start of each stop.
- **Moments**: photos as backgrounds with `ken_burns` alternating `pan` directions; `kit.polaroid` with handwritten
  captions for people; clips with `trim` and natural sound (`"audio": true`, low volume).
- **Stats**: `kit.stat_card` for km, days, budget; `kit.clock` for long journeys.

## Structure
Teaser (best 3 shots on beats, 5 s) → map overview → day/stop sections (map zooms to the next pin, then photos) →
reflection line (`kit.quote_card`) → end card.

## Rules
Music-led: put the song in `audio.music` with `"beats": "auto"` and cut photo sequences on beats (`"until": "nb:4"`).
Voice-over optional; captions `minimal`. Transitions: `dissolve` (style default) inside a place, `whip` between places.

---
name: Documentary / Vox-style explainer
description: Long or short documentary explainers in the Vox / video-essay style — paper collage, archival photos, maps with routes and pins, timelines, chapter kickers, lower thirds, stamps. Also history and "the story of" videos (use style vintage).
---

# Documentary (Vox-style)

Starting point: `$VS new DIR --example documentary_vox` (16:9, style `documentary`). For older history use `vintage`;
for darker investigations `noir`.

## Structure
| part | content | tools |
|---|---|---|
| Cold open (10–20 s) | the most striking fact or image, a question | full-frame photo + `kit.stamp_rubber` or a typed date (`kit.kicker_bracket`) |
| Title card | name of the piece | `kit.chapter_card` |
| Chapters (1–3 min each) | context → turning points → consequences | `kit.kicker_index` per chapter ("01 How it started") |
| Resolution | what it means now | quote (`kit.quote_card`), `kit.stat_card` |

## Visual vocabulary
- **Collage**: `"layout": "board"` + `kit.print_photo`, `kit.polaroid`, `kit.paper_cutout` (Flow cut-outs) slightly
  rotated, `kit.taped_photo`. Connect with red lines (shape `line` with `progress` draw-on).
- **Maps**: a map image (full frame, `filter` sepia/saturation), a dashed route `path` with `curve` and `progress`,
  `kit.map_pin` at places, `kit.kicker_chip` for distances. Camera `slow_push` toward the destination.
- **Timelines**: `"layout": "timeline"` + `kit.timeline_line` + `kit.timeline_point` per date, `kit.circle_scribble`
  around the key one.
- **Emphasis**: `kit.keyword_marker`, `kit.underline_scribble`, `kit.stamp_rubber` (max 2 per video), `kit.redact`.
- **People**: archival portrait + `kit.lower_third_clean` (name, role, years).
- Grade unifies mixed archive: style look + `"grain": 0.2`. Photos get a slow `ken_burns` (backgrounds do by default).

## Pacing
New visual every 3–6 s; scenes cut on sentence ends (`"until": "w:last.end+0.3"`). Use `dip` only between chapters.
Captions `box` (style default) or `minimal`. Music low (0.2) with `duck`.

## Sources
Use the user's archive photos or ones they have rights to; generated cut-outs via `flow_assets`. Cite sources in the
outro (a small `text` list) when the user provides them.

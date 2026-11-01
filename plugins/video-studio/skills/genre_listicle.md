---
name: Listicle / countdown / top-N
description: "Top 10", "5 things", rankings, tier lists and countdown videos built from one reusable scene template per item, with rank stamps, titles, facts and rising energy toward #1.
---

# Listicles & countdowns

Starting point: `$VS new DIR --example listicle_countdown` (style `bold_explainer`).

## Build it with one scene template
```json
"defs": {"rank": {"params": {"n": "#3", "title": "", "fact": "", "img": "x.jpg"}, "scene": { ...layers using {{n}} ... }}},
"scenes": [{"use": "rank", "with": {"n": "#5", "title": "...", "fact": "...", "img": "a.jpg"}, "id": "r5"}, ...]
```
Every item looks consistent and you only write data per item. Add per-item tweaks next to `use` (e.g. `"duration"`).

## Structure
- Hook (2–3 s): "5 places you must see" + `sfx:riser`.
- Items from least to most impressive; #1 gets a longer scene, a `sfx:riser` before it, `flash` transition, and more motion.
- Each item: `kit.countdown_number` stamp → title by word → one fact → optional `kit.stat_card`/`kit.keyword_marker`.
- Outro: recap grid (`"layout": "trio"`/`"stack"` with small `kit.photo_card`s) + CTA.

## Rules
- Same position for number/title/fact every item; change only image and colors.
- Transitions: `whip_left` between items; scene 3–6 s (short-form) or 20–60 s (long-form, with more facts per item).
- Tier lists: rows of `kit.photo_card` thumbnails (scale 0.3) dropping into labeled rows (`kit.kicker_chip` S/A/B/C).

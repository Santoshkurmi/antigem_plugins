---
name: Whiteboard / doodle / chalkboard explainer
description: Hand-drawn style explainers — whiteboard, notebook doodles, chalkboard lessons, sketchnotes — with handwriting, wobbly draw-on shapes, arrows, stick figures and step-by-step diagrams. Great for education.
---

# Whiteboard & doodle

Starting point: `$VS new DIR --example doodle_whiteboard` (style `chalkboard`; `doodle` for notebook paper).

## The hand-drawn toolkit
- Everything draws itself: shapes with `"rough": 3` and `"animate": {"progress": [[0, 0], [0.5, 1]]}`; arrows
  `kit.arrow_doodle`; circles `kit.circle_scribble`; underlines `kit.underline_scribble`.
- Lines "boil" (subtle redraw jitter): `"loop": "boil"` on text/images, `"rough"` + default `boil` on shapes/stickman.
- Handwriting: styles set `font_display`/`font_body` to `hand` (Kalam). Text appears like writing:
  `"reveal": {"by": "word", "preset": "appear", "stagger": 0.12}` + `sfx:scribble`.
- Characters: `stickman` with `rough` and `color: "$line"`; icons: `kit.idea_bulb`, `kit.doodle_heart`, `kit.check_mark`.
- Sticky notes for side facts (`kit.sticky_note`).

## Structure (lessons)
Title → the question → build the diagram piece by piece **in the order you speak about it** (`at` = word cues) →
the rule/formula big with underline → one worked example → recap list (`kit.checklist_item`).

## Rules
- Don't clear the board too often: build up one diagram per scene (6–12 s), cut to a fresh board for the next idea.
- Camera mostly `still`; zoom into a part with camera `animate.zoom` when explaining a detail.
- No heavy color: ink + one accent (+ second accent for contrast pairs).
- Captions `clean` in handwriting (style default) or off for lessons with lots of on-board text.

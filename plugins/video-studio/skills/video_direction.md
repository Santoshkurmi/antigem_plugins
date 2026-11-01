---
name: Video direction
description: Creative direction for Video Studio videos — structure, pacing, hooks, layout, typography, color, motion and sound rules, plus playbooks for reels, explainers, documentaries, promos and listicles. Read before planning any styled video.
---

# Video direction

Technique comes from `make_video`; genre-specific structure comes from the `genre_*` skills (table in `make_video`).
This skill is about making any video **good**. Use it to plan, then to review the `sheet` and `preview` critically.

## Structure

- **Hook in the first 1.5 s.** A bold claim, question, number or striking visual, plus motion on frame 1 (never a
  slow fade-in from black for social video). The first words on screen are the title of the video.
- **One idea per scene.** If a scene needs two sentences of on-screen text, it is two scenes.
- **Pay off the hook**, then end with a clear outro (CTA, logo, or a closing line). Don't trail off.
- Typical shapes:
  - Reel (15–45 s): hook → 3–6 quick beats → payoff → CTA.
  - Explainer (60–120 s): hook → problem → 3 steps/points → recap → CTA.
  - Documentary (2–6 min): cold open → context (place, date) → chapters → turning point → resolution.
  - Listicle/countdown: hook → items in rising interest (best last) → recap.

## Pacing

- Social: a visual change every 1–2.5 s (new layer, camera punch, cut). Documentary: every 3–6 s, with slow camera moves.
- Cut on the word: put scene boundaries and reveals on word cues (`until: "w:word.end+0.2"`, `at: "w:word"`), not on
  round seconds.
- Vary rhythm: two fast beats, one held beat. Constant speed feels mechanical.
- Silence and stillness are tools: hold a striking frame for 1 s before a reveal.

## Composition and layout

- 9:16: text lives in the middle 70 % of the height; the bottom ~17 % and the top ~8 % are covered by app UI (the
  `safe` slot already excludes them). Captions sit around 65–75 % of the height; keep other text out of that band.
- One focal point per frame. Make it big: titles 90–160 px, body 40–60 px, labels ≥ 36 px on 1080-wide video.
- Use slots for consistency: same title position across scenes of the same kind. Consistency reads as quality.
- Rule of thirds for subjects; leave the subject room to look into. Cut-outs at the frame edge (anchored to the bottom)
  feel grounded; floating mid-frame needs a shadow.
- Contrast: text on photos gets a `plate`, a `stroke`, a `shadow`, or a darkened background (`filter: {"brightness": 0.6}`).

## Typography

- At most 2 fonts per video: a display font for titles (`display`, `serif`, `rounded`) and a clean one for body
  (`sans`, `book`). Monospace only for data, dates and "file" aesthetics.
- Highlight 1–2 key words per line with `*word*` and a single accent color. Highlighting everything means nothing stands out.
- Short lines: 2–5 words per line for social. Uppercase for punchy titles, sentence case for reading.
- Kinetic text: reveal by word, synced to the voice when there is one; stagger 0.05–0.1 s.

## Color

- Pick a palette before building: 1 background family, 1 text color, 1 accent (+1 secondary). Reuse it everywhere
  (put the colors in template params).
- Examples: noir documentary `#0d0d0d / #f4ecd8 / #d9302c`; tech `#0b1020 / #e6f1ff / #00d1ff`; warm explainer
  `#fff7ed / #1f2937 / #f97316`; luxury `#0c0c0c / #e8d8b0 / #b08d57`.
- A unified grade (`look`) glues mixed assets together: slight `warmth`, `grain` 0.1–0.3, `vignette` 0.3–0.5.

## Motion

- Everything that appears should arrive (enter preset), but with **one** motion language per video: e.g. `rise` +
  `out_expo` for elegant, `pop` + `out_back` for playful, `whip`/`stamp`/punches for aggressive.
- Ease out on entrances, ease in on exits, in-out for camera moves. Linear only for constant drifts and spins.
- Entrances 0.3–0.6 s. Slower than 0.8 s feels sluggish on social.
- Keep something subtly alive in long holds: `float`, `breathe`, `ken_burns`, camera `slow_push`, dust particles.
- Stagger groups of items; never pop 6 things in the same frame.
- Transitions: pick 1–2 kinds for the whole video. `cut` is the default; use special ones for chapter changes.

## Sound

- Sound sells motion: whoosh on fast moves, pop on stickers, hit/impact on reveals, typing under typewriter text, riser
  into big reveals. Usually 1–3 sounds per scene, not one per layer.
- Music under voice at 0.2–0.35 with `duck`. Without voice, music carries the edit: cut on its beats (find them by
  listening or ask the user for the BPM; beat = 60/BPM seconds).

## Playbooks

**Faceless explainer (9:16):** gradient or soft-texture backgrounds, a cut-out mascot that reacts (pose per beat, `pop`
+ `float`), kinetic titles synced to the voice, icons and arrows drawn on with `progress`, captions `pop` or `karaoke`,
whoosh/pop SFX, `cut` transitions with occasional `whip`.

**Vox-style documentary (16:9 or 9:16):** archival photos with `ken_burns`, grain 0.3, vignette, collage walls with
paper borders and string lines, typed dates in `mono`, red `stamp` labels, map routes, `dip` between chapters,
minimal captions, quiet music.

**Product promo:** dark or brand gradient, product cut-out on a floating card with a light sweep, feature labels
sliding in with lines pointing to the product, counter for the price or stats, logo reveal outro with `bass_drop`.

**Data story:** one number per scene (counter, big), then the chart, then what it means (one line). Columns grow with
`out_back` + stagger; highlight the key bar with the accent color, others muted gray.

**Countdown/listicle:** a `defs` scene template per item (number stamp + title + background), `whip` transitions,
rising energy, best item last with a `riser` before it.

## Self-review checklist (run on the sheet and preview)

1. Is the hook readable in under 1 s, and does something move on frame 1?
2. Is the subject of every frame obvious? Is anything fighting it?
3. Is text readable on every background, inside the safe area, never overlapping captions?
4. Same fonts, colors, positions and motion language throughout?
5. Does every visual change land on a word or beat?
6. Any dead time (> 3 s with nothing changing on social)?
7. Is the ending clear?

---
name: Retro / 8-bit / VHS / vaporwave
description: Retro-styled videos — 8-bit arcade and pixel-game intros, video-game style explainers, VHS/90s nostalgia and vaporwave edits — with pixelation, scanlines, chromatic shift, chiptune sounds and game UI.
---

# Retro styles

Starting point: `$VS new DIR --example retro_arcade` (style `retro8bit`). Others: `vaporwave` (VHS + pink/cyan),
`vintage` (old film), `neon` (synthwave).

## 8-bit arcade
- Look: `pixelate` 3–6, `scanlines`, `rgb_shift` 1 (style default). Blocky shapes: `rect`, `"cap": "butt"`.
- Game UI kit: `kit.pixel_title` (title screen), `kit.press_start`, `kit.pixel_dialog` (NPC speech, typed with blips),
  `kit.score_counter`, `kit.health_bar` (drains in steps), `kit.countdown_number` for levels.
- Hero: `stickman` colored `$accent` with `run`/`jump` actions, moving with `animate.x`; ground = a `rect` at the bottom;
  stars/coins = `particles` `stars`, small `star` shapes.
- Sounds: `sfx:jump8`, `sfx:coin8`, `sfx:power8`, `sfx:blip8`, `sfx:hit8`. Transitions `pixelize`.
- Fonts: `mono` for UI. For a real pixel font, add a free one to `fonts/` and set `"theme": {"font_display": "PressStart2P"}`.

## VHS / vaporwave
- `"look": {"vhs": true}` (rgb shift + noise + blur + scanlines). `kit.rec_overlay` with a 90s date for camcorder feel.
- `glitch` enter presets and transitions, `sfx:glitch`. Gradients pink→purple, sunburst/grid textures, chrome-ish
  gradient text (`color: {"colors": [...], "angle": 90}`).

## Rules
Keep the low-res look only on the video's grade (the engine renders sharp, then pixelates), so text stays readable at
`pixelate` ≤ 5. Check with `$VS frame` (stills include the look).

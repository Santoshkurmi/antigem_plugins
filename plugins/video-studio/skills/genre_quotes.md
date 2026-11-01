---
name: Quotes / motivation / affirmations
description: Quote posts, motivational and philosophical reels, affirmations, poems and short reflections — atmospheric backgrounds, elegant revealed text, slow movement and calm music.
---

# Quotes & motivation

Starting point: `$VS new DIR --example quote_motivation` (style `luxury`; `cinematic`, `vintage`, `minimal` also fit).

- One idea per scene; 5–8 s per quote (reading time ≈ word count × 0.35 s + 1.5 s).
- Background: darkened photo/clip (`filter.brightness` 0.4–0.6) with slow `ken_burns`, or a gradient/texture;
  `particles` `dust`/`bokeh` for atmosphere.
- Text: `kit.quote_card` or a `text` in `serif` with `reveal` by word (`rise`, 0.05 stagger) or by line (`wipe_up`).
  Highlight the key word only. Author small and muted.
- Motion stays slow: camera `slow_push`, `dissolve` transitions, no punches. Add one late beat (underline or the
  author) so the frame doesn't freeze.
- Sound: soft music (user-provided), optional `sfx:chime` on the key word. Voice-over optional (deep calm voice via
  `$VS tts --voice en-US-GuyNeural --rate "-10%"`).
- Series: one scene template (`defs`) and many quotes; consistent watermark with `kit.corner_bug`.
- Attribute quotes correctly; don't invent quotes for real people.

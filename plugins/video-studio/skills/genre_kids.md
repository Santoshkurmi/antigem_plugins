---
name: Kids / cartoon / educational for children
description: Bright, gentle videos for children — counting, alphabet, colors, shapes, simple science, songs and stories — with rounded fonts, pastel styles, bouncing characters and celebratory effects.
---

# Kids & cartoon

Starting point: `$VS new DIR --example kids_cartoon` (style `cute_toon`; `bold_explainer` for older kids, `chalkboard` for lessons).

- Big and simple: one object or word per screen, text 120–360 px, rounded font (style default).
- Repetition is the teaching tool: show → say → show again with a twist (counting with `counter` `ease: "steps(9)"`
  and a `pulse` loop at the counting rhythm; alphabet with `stamp`/`bounce_in` letters).
- Friendly host: `stickman` with `head_fill`, `accessory: "bow"`/`"cap"`, `expression: "laugh"`, `jump`/`dance`
  actions, `outline` white. Speech: `kit.speech_bubble`.
- Celebrate correct answers: `particles` `confetti`, `kit.burst` "Yay!", `sfx:success`.
- Backgrounds: `sunburst` texture spinning slowly (`"motion": {"preset": "spin", "period": 30}`), pastel gradients, `dots`.
- Calm pacing (2–4 s per item), no scary sounds or flashing (`flash`/`glitch` transitions off; use `circle`/`zoom`).
- Captions `pop` help early readers.

---
name: Faceless explainer video
description: Plan and build faceless explainer videos (YouTube Shorts/Reels/TikTok or long-form) — hook, problem, steps, payoff — with kinetic titles, stickers, stick figures, icons and voice-synced reveals. Use for "explain X", "how does X work", "why X" videos.
---

# Faceless explainer

Visual essay without a presenter: every spoken idea gets a picture, a word on screen or a moving diagram.
Build it with the `make_video` skill. Starting point: `$VS new DIR --example explainer_stickman` (9:16, style `bold_explainer`).

## Pick a look
- `bold_explainer` (bright, punchy), `sticker` (paper + white-border cut-outs), `box` (dark editorial),
  `documentary` (Vox paper), `cute_toon` (kids/wholesome), `doodle` (notebook, hand-drawn), `minimal` (clean/corporate).

## Script shape (write it first, then voice it)
| beat | length (short / long-form) | on screen |
|---|---|---|
| Hook: a question, surprising fact or "you've been doing X wrong" | 2–3 s / 10 s | `kit.headline_underline` or kinetic words synced to the voice, camera punch, `kit.burst` |
| Context: why it matters | 5 s / 30 s | stickman reacting (`shrug`, `think`), a `kit.stat_card` |
| 2–4 points/steps | 5–8 s each / 30–60 s each | one scene per point: `kit.kicker_index` ("01 …"), visual (sticker/diagram), 1 line of text |
| Payoff / recap | 4 s / 20 s | `kit.checklist_item` stack, stickman `cheer` + `jump` |
| CTA | 2 s | `kit.subscribe_button` or a short line |

Keep spoken sentences short (8–14 words). Get word timings with `$VS tts` or `$VS align`.

## Building each point scene
- `"layout": "presenter"` (stickman/character in `cast`, visual in `visual`, line in `title`) or `"hero"` / `"split"`.
- Visual priority: a real cut-out (`kit.sticker`, Flow-generated on magenta, see `flow_assets`) → a diagram from shapes
  (arrows draw on with `progress`, `kit.callout`) → a stickman acting it out.
- Every noun the voice stresses appears **on its word**: `"at": "w:noun"`. Use `"cue_lead": 0.08` at the root.
- Stickman as host: `"talk": true`, change `poses` on key words (`point` when introducing, `think` on questions,
  `cheer` on payoffs), `expressions` to match.

## Motion & sound
- One motion language: `pop` + `out_back` for objects, `rise` for text, camera `punches` on stressed words.
- `sfx:pop` on stickers, `sfx:whoosh` on scene changes, `sfx:ding`/`sfx:success` on answers. Music ducked under voice.
- Captions: `pop` or `karaoke`, 3 words max; keep visuals out of the caption band (65–75 % height).

## Pitfalls
- Walls of text: max 7 words on screen besides captions.
- Same layout every scene: alternate `presenter`, `hero`, `focus`, full-frame visual.
- More than ~3 s with nothing new: `inspect` reports pacing; add a punch or a new element.

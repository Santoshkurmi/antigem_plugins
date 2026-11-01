---
name: Talking-head edit (B-roll and graphics)
description: Edit a recorded talking-head / podcast / interview / vlog clip — punch-in zooms, jump-cut feel, lower thirds, B-roll and image inserts on keywords, stat pop-ups, word captions.
---

# Talking-head edits

Starting point: `$VS new DIR --example talking_head` (9:16, style `minimal`).

## Setup
1. Put the recording in `assets/`. Pick the part you use (START–END seconds) and extract its audio with the same
   trim: `ffmpeg -ss START -to END -i assets/talk.mp4 -vn assets/voice.wav`, then `$VS align assets/voice.wav`.
2. Scene background = the clip with the same trim: `"background": {"video": "talk.mp4", "trim": [START, END]}`;
   voice = `{"src": "voice.wav", "words": "voice.words.json"}`. Picture and words now share one clock.
3. Split long recordings into scenes at sentence ends (`"until": "w:word.end+0.15"`, `"transition": "cut"`), each scene
   using a background `trim` that continues where the previous one stopped.

## Editing grammar
- **Punch-ins**: alternate framing per sentence with camera zoom keyframes using `hold` easing (instant cut-zoom):
  `"zoom": [[0, 1], [2.5, 1], [2.55, 1.18, "hold"]]`. Recenter with `x`/`y` if the face is off-center.
- **Lower third** on first appearance: `kit.lower_third_bar` (name, role), 3–4 s.
- **B-roll on keywords**: full-frame `video`/`image` `"at": "w:keyword"`, `"duration": 2.5`, `fade` in/out — voice continues.
- **Half-screen graphics**: `kit.photo_card` / `kit.stat_card` / `kit.post_card` in the top half while the speaker
  stays visible below.
- **Emphasis**: `kit.keyword_marker` with the exact word, camera punch, `sfx:pop`.
- Captions: `karaoke`/`pop`, 3 words, at 70–75 % height (below the face).

## Rules
- Never cover the face for more than ~3 s in a row without a reason.
- Keep the speaker's own audio as the voice; music ≤ 0.15 with `duck`.

---
name: Stickman story / comedy
description: Animated stick-figure stories, skits, comedy and relatable "when you..." videos with the built-in stickman — walking, poses, expressions, talking mouths, speech bubbles, hand-drawn wobble. No images needed.
---

# Stickman stories

The engine has a procedural stick figure (`"type": "stickman"`), so a full animated skit needs no assets.
Starting point: `$VS new DIR --example stickman_story` (style `doodle`). Read `make_video` → `docs/spec_reference.md` § stickman.

## Characters
- Make each character recognizable: `accessory` (`glasses`, `tie`, `hat`, `cap`, `bow`), `color`, `size` (child 0.7×).
- Hand-drawn feel: `"rough": 1.5, "loop": "boil"` on every figure (and `doodle`/`chalkboard` style).
- Face each other: `"facing": "left"` for the one on the right.
- Talking: `"talk": [[start, end]]` per line of dialogue (or `true` with a single narrator voice).

## Acting
- Poses change on story beats: `"poses": [{"at": 2.0, "pose": "facepalm"}]`; expressions with them.
- Entrances: walk in with `"actions": [{"action": "walk", "until": 1.8}]` + `"animate": {"x": [[0, -200], [1.8, 300]]}`.
- Reactions are the comedy: `surprised` + camera `punch` + `sfx:hit` on the punchline; `shrug`/`facepalm` for awkward beats.
- Dialogue: `kit.speech_bubble` above-right of the speaker's head, one line each, `until` when the other replies.
  Thoughts: `kit.thought_bubble`. Notes/props: `kit.sticky_note`, `kit.stamp_scrawl`, `kit.circle_scribble`.

## Structure (30–60 s)
1. Setup (title + characters enter) 4–6 s · 2. Escalation, 2–4 exchanges, 3–5 s each · 3. Twist/punchline with a
reaction shot (zoom: camera `animate.zoom` to 1.3 on the reacting figure) · 4. Button: one last small joke or caption.

## Tips
- Stage left/right like a comic: speaker 1 at 28 %, speaker 2 at 72 %, feet at ~86–90 % (9:16).
- Cut (`"transition": "cut"`) between beats; use `wipe_left` only for time jumps ("later...").
- Sound: `sfx:pop` on bubbles, `sfx:scribble` on drawn marks, `sfx:buzz` for fails, `sfx:success` for wins.

---
name: Tutorial / screen walkthrough
description: How-to and software tutorial videos — screenshots or screen recordings inside browser/app/phone frames, zooms into UI regions, highlight boxes, spotlights, callouts, numbered steps, checkmarks.
---

# Tutorials & walkthroughs

Starting point: `$VS new DIR --example tutorial_screen` (16:9, style `minimal`). Phone-app tutorials: 9:16 with `kit.phone_frame`.

## Per step (one scene each)
1. `kit.kicker_index` "1 · Open settings" (with `"camera": false` so it stays put during zooms).
2. The screen: `kit.browser_frame` (scrolls with `scroll`), `kit.app_window`, `kit.phone_frame`, or a full-frame `video`
   screen recording (`trim` to the action, `speed` 1.5–2 for boring waits).
3. Guide the eye **in this order**: camera zoom to the region (`"camera": {"animate": {"zoom": [...], "x": [...], "y": [...]}}`)
   → `kit.highlight_box` around the button → `kit.callout` with the instruction → `kit.check_mark` when done.
   Or dim the rest with `kit.spotlight`.
4. Cursor: a white `polygon` arrow (see `kit.subscribe_button` for the shape) moved with `animate.x/y`, `sfx:click` on click.

## Rules
- Zoom levels 1.4–2.0; ease `in_out_cubic`; hold zoomed while explaining; zoom back out before the next step.
  Camera x/y are offsets (negative x looks left of center).
- Never show more than one instruction at a time. Numbers on every step.
- Blur private data: put a small `rect` with `blur` or a `kit.redact` bar over it.
- Captions `minimal`; voice explains *why*, screen shows *where*.

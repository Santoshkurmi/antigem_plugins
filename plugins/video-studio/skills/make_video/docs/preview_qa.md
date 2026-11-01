# Preview and quality checks

You can't watch the video in real time, so check it with these tools. They are cheap; run them after every
meaningful change.

| command | what you get | cost |
|---|---|---|
| `$VS validate video.json` | builds every scene and draws one frame; exact error path + "did you mean" | seconds |
| `$VS timeline video.json` | scene start/end and the words spoken in each | instant |
| `$VS inspect video.json [--scene ID]` | each layer's time span and on-screen box (x, y in px) + warnings | seconds |
| `$VS sheet video.json [--scene ID] [--per 4] [--cell 270]` | `sheet.png`: frames from every scene in a grid. **Open it and look.** | seconds |
| `$VS frame video.json --scene ID --at 1.25 [--scale 1]` | one exact frame as PNG (`--t 12.3` for global time) | instant |
| `$VS preview video.json [--scene ID] [--scale 0.4] [--fps 15]` | low-res MP4 with audio (no audio with `--scene`) | fast |
| `$VS preview video.json --watch` | re-renders on every save; only changed scenes re-render | — |
| `$VS render video.json [--scene ID] [--crf 19] [--scale 1]` | final MP4 | slow |

Scenes are cached by content: a scene re-renders only when its JSON, an asset it uses, or the engine changes. Preview
and final use separate caches.

## Review loop

1. `validate` until clean.
2. `inspect`: fix warnings.
3. `sheet`: look at composition, contrast and hierarchy. Is the main subject obvious? Is text readable on its
   background? Is the frame too empty or too crowded?
4. `frame` at critical moments (a reveal, the frame where a word cue fires).
5. `preview` and give it to the user. Ask for feedback in plain terms ("faster?", "bigger title?").
6. `render` when the user is happy.

## inspect warnings

| warning | fix |
|---|---|
| `X overlaps Y` | move one (different slot, `y`), shorten its time, or ignore if intended (e.g. glitch copies) |
| `leaves the safe area (bottom)` | text would sit under the app's UI buttons; move it up or reduce `size` |
| `is never on screen` | off-canvas position, starts after the scene ends, `opacity` 0, or fully cropped |
| `size N is small for phones` | use ≥ 36 px for body text and ≥ 64 for titles on 1080-wide video |
| `voice ends at … but the video ends at …` | lengthen the last scene or drop its `duration` so it follows the voice |
| `outside the frame when settled` | check x/y and anchor |
| `nothing new appears for N s` | pacing: add a beat — a camera punch, a new layer, a reveal, a cut. The report's `pacing:` line shows changes per second |

The coordinates `inspect` prints are frame pixels: x from the left, y from the top.

## Phone performance

- Preview at `--scale 0.4` (≈ 430×770) is 5–10× faster than final. Iterate with preview.
- Full-frame effects cost the most: `blend` modes on big layers, `blur` animating on large images, `custom` layers drawing
  full-screen every frame, more than 150 particles, many simultaneous videos.
- Static layers are cheap (rendered once, then moved). Text with `reveal` costs a little more until the reveal finishes.
- `--workers N` sets parallel scenes (default 2 on phones). Use `--workers 1` if Android kills the process (low memory).
- Keep source images under ~3000 px; resize huge photos first (`ffmpeg -i big.jpg -vf scale=2000:-1 small.jpg`).
- Long scenes (>10 s) can't be split across workers. Prefer several shorter scenes.

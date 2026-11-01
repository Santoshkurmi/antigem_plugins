---
name: Beat-synced montage / music edit
description: Music-driven edits where cuts, text and effects hit the beat — montages, travel reels, recap videos, event highlights, music visualizers, "edits".
---

# Beat-synced montage

Starting point: `$VS new DIR --example beat_montage` (style `neon`; any style works).

## Setup
```json
"audio": {"music": {"src": "song.mp3", "beats": "auto", "volume": 0.9}}
```
`$VS beats song.mp3` prints BPM and beat times. Cues: `"b:N"` (Nth beat), `"bar:N"` (bar start), `"nb:K"`
(K beats after this scene/layer starts). If detection is off, set `"bpm"` and `"first_beat"` yourself.

## Editing grammar
- Scene length = musical length: `"until": "nb:4"` (one bar) for calm parts, `"nb:2"` or `"nb:1"` in the chorus/drop.
- Build: intro bars hold longer with slow `ken_burns`; pre-drop accelerates (2 beats, then 1); drop = cut every beat with
  `flash`/`whip` transitions and camera `punches` on each beat.
- Text on beats: words `"at": "b:33"` with `stamp`/`zoom_out`, `glow` in neon styles.
- Clips: `video` layers with `trim` to the best moment; `speed` 0.5 for slow-mo on long notes.
- Photos: alternate `ken_burns` directions (`pan` left/right) so consecutive shots don't feel identical.
- End on the final hit: last scene `until` a bar line, then `dip` or a logo.

## Sound
The song is the sound; add only impact sfx on the biggest hits (`sfx:impact` at the drop). Skip captions unless there
is speech. Normalization (−14 LUFS) is automatic.

Only use music the user owns or has licensed.

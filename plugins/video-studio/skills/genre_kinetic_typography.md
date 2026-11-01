---
name: Kinetic typography / lyric video
description: Text-driven videos where words are the visuals — kinetic typography, lyric videos, motivational word animations, quote reels — synced to a voice or song.
---

# Kinetic typography

Starting point: `$VS new DIR --example kinetic` (no style; or `"style": "kinetic"`).

## The core move
Each spoken phrase becomes a text layer whose words appear **as they are spoken**:
```json
{"type": "text", "text": "stop *wasting* time", "font": "display", "size": 150, "uppercase": true, "slot": "middle",
 "at": "w:stop", "until": "w:time.end+0.2", "reveal": {"by": "word", "sync": "voice", "preset": "pop", "duration": 0.25}}
```
For songs: transcribe with `$VS align song.mp3` (lyrics as words), or time lines on beats (`"at": "b:17"`).

## Variety (rotate every 1–2 phrases)
- Size contrast: 1–2 hero words huge (200–300 px), the rest small.
- Presets per phrase: `pop`, `slide_up`, `stamp`, `zoom_out`, `blur_in`, `typewriter` (by char), `wipe_right`.
- Layout: centered stack, left-aligned column, one word per scene (`single` caption style feel), words placed at
  different heights.
- Color: one accent for stressed words (`*word*` + `highlight`), inverted scene (accent background, dark text) for drops.
- Motion: camera `punches` on stressed words, `shake` loop on aggressive words, `float` on soft ones.
- Swap words in place: layer A `until: "w:but"` + `exit`, layer B `at: "w:but"` + `enter`.

## Rules
- No captions (the text is the captions): omit `captions` or set `false`.
- Hard cuts between phrases, `whip`/`flash` on drops. Keep scenes 1–3 s.
- Readable: ≥ 90 px for any word that must be read, 0.3 s minimum on screen per word.

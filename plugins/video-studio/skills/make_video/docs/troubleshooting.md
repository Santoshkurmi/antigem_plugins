# Troubleshooting

**`error in scenes[2](intro).layers[3].enter: unknown preset 'slideup'` / `hint: did you mean 'slide_up'?`**
The path names the exact spot: scene index (and id), layer index, key. Apply the hint. `$VS presets` lists valid names.

**`invalid JSON … near: …`**: a missing comma or quote at that line. Comments (`//`) and trailing commas are allowed.

**`word 'x' not spoken after 12.40s`**: the word cue searches forward from the scene (or layer) start. Check spelling
against `$VS timeline`, use `#2` for a later occurrence, or the cue belongs in a later scene. Numbers in speech may be
transcribed as digits or words ("1946" vs "nineteen"); look at the words file.

**`scene needs "duration" or "until"`**: only the last scene can follow the voice automatically.

**`file not found: x.png` (hint: did you mean 'assets/x.png'?)**: paths are relative to the JSON. `assets/` is also
searched, so `"x.png"` works for `assets/x.png`.

**Hindi/Nepali letters look broken (vowel signs in the wrong place)**: Pillow lacks raqm shaping. `$VS doctor` shows it.
Termux: `pkg install libraqm` then reinstall pillow; Debian/Ubuntu: `apt install libraqm0`. Use `by: "word"` reveals for
Devanagari (never `char`).

**Text is smaller than I set**: the text did not fit `max_width`/`max_height`/`max_lines`, so it was shrunk to fit.
Give it a wider box or fewer words.

**Video looks soft when zoomed**: content is rendered at 1× (or at the layer's biggest keyframed `scale`). Add `"detail": 2`.

**`joining scenes failed … transition`**: the phone's FFmpeg is older and lacks that xfade transition. Use
`fade`/`wipe_*`/`slide_*`/`circle`, or update FFmpeg (`pkg upgrade ffmpeg`).

**Render killed / `BrokenPipe` on a phone**: Android ran out of memory. Use `--workers 1`, smaller source images, or
fewer simultaneous videos.

**Custom layer error**: the message shows the exception and the time. Run `$VS frame … --at T` to reproduce it.

**Audio is silent**: check `audio.voice.src` exists. Music needs `volume` above 0. With `--scene`, preview has no audio
by design.

**It rendered but looks wrong**: run `$VS sheet` and look at it; run `$VS inspect` and read the boxes. Don't guess:
adjust a value, then check the single `frame` again.

**Cache**: it lives in `<project>/.vs_cache/` and can be deleted at any time to force a full re-render.

**Emoji show as empty boxes**: no color-emoji font is bundled. Use kit icons/shapes, or an emoji as a PNG image layer.

**A layer inside a group is cut off**: only with `"clip": true` on the group. Otherwise check its `x`/`y` (they are
relative to the group's box).

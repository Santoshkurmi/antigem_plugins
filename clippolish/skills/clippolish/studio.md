# Making a studio video

A studio video has no recording. It is a stack of **scenes** on a timeline. Each scene has a background,
a slow camera move, a transition into it and a **layout** with named spots ("slots"). **Elements** (text,
keywords, stamps, pictures, videos, counters, lists, characters…) live in a scene and animate in and out.
A **style pack** gives the whole video its colours, fonts, frames and film finish. Optionally, a
**transcript** (spoken words with times) lets everything appear exactly when a word is said.

## 1. Plan, then learn the building blocks

1. Write a short plan: the story in 3–8 beats, one scene per beat, what is on screen in each, and roughly how
   long each lasts. A narrated video is as long as its voice.
2. Call `studio_catalog` once. It returns:
   - `packs`: style packs with colours;
   - `layouts`: with their `slots_wide` / `slots_tall`;
   - `element_types`: with `designs` and `uses` (which fields matter);
   - `anim_kinds`, `eases`, `loops`, `transitions`, `camera_moves`, `background_kinds`, `font_roles`;
   - `text_markup` and the `cues` syntax;
   - `templates` and `motions` (built in, the user's saved ones, and installed plugins).

   `studio_catalog element_type=STAMP` also returns a ready default element of that type.
3. Pick a pack that fits the topic:

   | Pack | Fits |
   | --- | --- |
   | `clean` | anything |
   | `noir` | true crime, mystery, history (grain, cold grade) |
   | `documentary` | paper, cut-out photos |
   | `sticker` | fun, kids, lists |
   | `box` | data, business |
   | `kinetic` | one word at a time |
   | `arcade` | games, tech |
   | `minimal` | clean light |
   | `neon` | night, music |

## 2. Create

```json
{"name": "create_video_project", "arguments": {"name": "The midnight call", "aspect": "PORTRAIT_9_16", "duration_ms": 45000, "pack": "noir"}}
```
`aspect`: `PORTRAIT_9_16` (Reels / Shorts / TikTok), `LANDSCAPE_16_9` (YouTube), `SQUARE`, `PORTRAIT_4_5`.
It starts with one scene covering everything. Change the length any time with `set_canvas_length`; with a
voice-over, make it the voice's length plus about 0.6 s.

Bring in files first (details and rules in `files-and-preview.md` §1; never file contents in a tool call):
- Shared folder: copy the files there, then `import_asset paths=[…]` (many at once). It returns the paths to use
  as `src`. `https://` links work the same way, and the phone downloads them.
- Or `upload_file project_id=…` → run its `curl` command with all your files. The reply's paths
  (`assets/…`) go straight into `src` / `path`.
- Paths given to `add_element` / `add_scene` / `upsert_items` are copied into the project too.
- A voice-over or music track is an audio clip: `upsert_items kind=audio_clip` with `path` (from
  `import_asset` or the upload), `title`, `atUs`, `durationUs`, and `kind` `VOICEOVER`, `MUSIC` or `SFX`. Background music for the whole video: `set_audio music_path`.

## 3. Transcript and word cues (only when there is speech)

ClipPolish does **no** speech recognition. You give it the words with times: from a transcription you made, a
TTS engine's timings, or a file the user has. The user can also import SRT / VTT / TSV / JSON in the editor.

```json
{"name": "set_transcript", "arguments": {"words": [
  {"text": "At", "start_ms": 300, "end_ms": 450, "line": "01"},
  {"text": "midnight", "start_ms": 480, "end_ms": 1020, "line": "01"},
  {"text": "the", "start_ms": 1050, "end_ms": 1150, "line": "01"},
  {"text": "phone", "start_ms": 1180, "end_ms": 1600, "line": "01"}
], "make_captions": true}}
```
Or `text` with a whole SRT / VTT / TSV (`start end word [line]`) / JSON word list, or `path` to such a file.
`line` groups words into sentences for `@` cues. `make_captions=true` adds karaoke captions that follow the
voice.

**Cues** go in `at` / `until` (scenes, elements, list rows, character actions, scene cuts) and `reveal`
(redactions), instead of fixed times:

| Cue | Means |
| --- | --- |
| `"12.4"` | 12.4 seconds |
| `"@05"` / `"@05+0.4"` | start of transcript line 05 / 0.4 s after it |
| `"midnight"` / `"midnight-0.2"` | the first spoken word containing it, searched from the scene's start / 0.2 s before |
| `"w:1846"` | a spoken **number**. A bare `"1846"` would mean 1846 seconds |

Word cues fire 80 ms before the word (`leadMs`), the way editors cut. Everything with a cue re-times itself
when the transcript changes. `get_studio` lists `unresolved_cues`: fix those words.

## 4. Build: templates first, then scenes and elements

**Templates** are the fastest way to good-looking scenes. `place_template template_id=… at_ms=…` puts a
ready-made scene (or element group) there. Built-ins:
- scenes: `title_card`, `big_stat`, `quote`, `compare`, `three_steps`, `history`;
- element groups: `lower_third`, `reveal`, `celebrate`.

It returns the new element ids. Then change their text and pictures with `upsert_items kind=element` (only
the fields you send change):
```json
{"name": "upsert_items", "arguments": {"kind": "element", "items": [{"id": "el_ab12", "text": "Every *night*"}, {"id": "el_cd34", "value": 7, "suffix": " calls"}]}}
```

**Scenes**: `add_scene` with `start_ms` / `end_ms` (or cues `at` / `until`), `name`, `layout`, and `set` for
anything else:
```json
{"name": "add_scene", "arguments": {"at": "@03", "until": "@05", "name": "The board", "layout": "board",
  "set": {"background": {"kind": "IMAGE", "src": "/sdcard/Pictures/kot.jpg", "dim": 0.35, "blur": 0.1},
          "camera": {"kind": "KEN_BURNS", "amount": 0.15}, "transition": {"style": "PUSH_LEFT", "durationMs": 600}}}}
```
Scenes never overlap. A scene added inside another splits it, and elements follow the time they show at.
Background kinds: `COLOR`, `GRADIENT`, `IMAGE`, `VIDEO`, `PAPER`, `GRID`, `DOTS`, `DARK`, `NOISE`,
`SPOTLIGHT`. Use `IMAGE` / `VIDEO` with `src`.

**Elements**: `add_element type=…` gets the pack's look, a fitting slot of the scene's layout and a good
entrance, exactly like the editor's Add button. Give only what matters:
```json
{"name": "add_element", "arguments": {"type": "TEXT", "at": "midnight", "text": "The *midnight* call"}}
{"name": "add_element", "arguments": {"type": "IMAGE", "at": "phone", "src": "/sdcard/Pictures/phone.png", "design": "polaroid+burst", "sub": "Exhibit A"}}
{"name": "add_element", "arguments": {"type": "STAMP", "at": "w:1846", "text": "1846"}}
{"name": "add_element", "arguments": {"type": "COUNTER", "at": "shots", "set": {"value": 3, "valueFrom": 0, "suffix": " shots", "valueMs": 1200}}}
{"name": "add_element", "arguments": {"type": "LIST", "at": "@04", "set": {"parts": [{"text": "Locked door", "at": "door"}, {"text": "No witnesses", "at": "nobody"}]}}}
```
- Without times the element spans its scene. `scene_id` chooses the scene; `overlay=true` puts it above all
  scenes.
- `slot` places it in a spot of the layout; `box` (normalized rect) places it freely.
- `set` takes any element field in model units: µs, ARGB colour numbers such as 4294933061 for 0xFFFF7A45.
- Text markup: `*accent*`, `^accent 2^`, `_highlight_`, `[box]`, `~underline~`, `\n` for a new line.
- Useful `set` fields:
  - `enter` / `exit`: `{"kind": "SLAM", "durationMs": 320, "ease": "BACK", "delayMs": 0}`
  - `loop`: `{"kind": "FLOAT"}`
  - `keys`: keyframes `{t (µs, absolute), x, y, scale, rotation, opacity, ease}`
  - `style`: `{size, font, color, fill, glow, shadow, align, uppercase, gradientTo}`
  - `rotation`, `z` (layer order), `media`: `{fit, crop, trimStartUs, loop, volume, muted, speed, keyColor}`

**Motions**: `apply_motion element_ids=[…] motion_id=…` gives elements a named motion, for example
`float_in`, `pop_wiggle`, `slam`, `slide_settle`, `drop_bounce`, `elastic`, `glitch`, `typewriter`,
`word_by_word`, `heartbeat`, `drift`, `ken_burns`, `fly_through`.

**Look**: `set_studio_look pack=… apply_to_scenes=true` restyles every scene's background, transition and
camera move (pictures and videos stay). `set` overrides colours, fonts, `grain`, `vignette`, `contrast`,
`saturation`, `warmth`, `letterbox` and `highlightWords`. Cinema bars (`letterbox`) are off by default: add them only when the user asks.

## 5. Good videos

- **One idea per scene**, 2–6 s each. Change something on screen every 1–2 s: a word appearing, a stamp, a
  counter, a camera cut (`cuts` on the scene: `{"atUs": 0, "at": "word", "frame": {"left": 0.3, "top": 0.2, "right": 0.7, "bottom": 0.6}, "push": 0.04}`, where `frame` is the part of the background to show).
- **Time visuals to the voice** with word cues, not guessed seconds.
- **Use slots** instead of free boxes, so nothing overlaps in either orientation. Check `slots_tall` for
  portrait videos.
- **Readable text:** at most about 6 words in a title, at least 0.045 size on portrait. Keep body text in
  captions.
- **Vary entrances** (`WIPE_UP` titles, `SLAM` stamps, `POP` keywords, `RISE` cards) but keep one style per
  element type.
- Transitions: soft (`FADE`, `DIP`) for mood, energetic (`PUSH_LEFT`, `WHIP`, `ZOOM_IN`) for pace. Don't mix
  more than 2–3 kinds in one video.

## 6. Check and finish

1. `get_studio`: scene order, element times, `unresolved_cues`.
2. `get_frame` at each scene's middle and at key reveals (`max_size` 900). Look for overlaps, cut-off text,
   empty frames, and captions covering elements. Fix with `upsert_items` / `patch_project`.
3. `get_storyboard count=8–12` for the whole flow.
4. Want to reuse a scene? `save_template scene_id=… name=…` puts it in the user's "My templates".
5. Show it to the user: `preview_video` (`480p`, or `720p` for short videos and small text) and post its
   `markdown` line. It plays in the chat within seconds (no export needed). Make a new preview after each round
   of changes.
6. Export only when asked: `export kind=mp4` (see `recordings.md` §6).

## 7. 2D Video Editing Studio projects

`import_studio_project` takes:
- `path` to a folder or `.zip` with EDIT.json, WORDS.tsv, cues.tsv, VO.wav or mix.wav, elements/ and audio/;
- `uri` of a .zip;
- `edit_json` text (+ `words`, `cues` text, `assets_dir` for its pictures).

It converts scenes, items, camera moves, transitions, cuts and captions, copies every used file and returns
`warnings` for things it couldn't map. Check the result as in §6.

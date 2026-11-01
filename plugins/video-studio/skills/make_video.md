---
name: Make a video
description: Create edited videos (reels, explainers, documentaries, promos, kinetic typography) from images, video clips, fonts, voice and music by writing a JSON timeline that a bundled FFmpeg + Pillow engine renders on the phone. Includes preview, stills, contact sheets and a layout checker.
---

# Make a video

You write **one JSON file** (the timeline). The bundled engine turns it into an MP4. You never write FFmpeg commands or
render code. You describe scenes and layers, and the engine handles timing, animation, compositing, transitions, captions and the audio mix.

## 0. Engine location and setup (once per session)

`get_skill make_video` returns `detail_dir`. The engine is `<detail_dir>/engine/studio.py`. Define a shell variable:

```bash
VS="python3 <detail_dir>/engine/studio.py"
$VS doctor            # checks python, pillow, numpy, ffmpeg, fonts
```

If `doctor` reports something missing, install it. Termux: `pkg install python ffmpeg python-pillow python-numpy`.
Ubuntu/Debian: `apt install -y python3 python3-pil python3-numpy ffmpeg`. Before starting a render, check that one isn't
already running (`ps aux | grep studio.py`). Never run two renders of the same project at once.

## 1. Workflow (follow in order)

1. **Plan.** Identify the genre and read its skill (table below) and `video_direction`. Write a short shot list for the
   user: scenes, duration, what is on screen, what is said. Pick a style pack (`$VS styles`).
2. **Assets.** Put files in `<project>/assets/`. Use the user's files, or generate images/clips with the Google Flow
   plugin (skill `flow_assets`). Cut out objects on solid magenta with `$VS key img.png`.
3. **Voice (optional).** `$VS tts script.txt --voice en-US-AndrewNeural --out assets/voice.mp3` gives audio plus
   `voice.words.json`. For an existing recording, `$VS align assets/voice.wav` gives the word timings. Word timings unlock
   word-synced cues (`"at": "w:money"`), scene ends (`"until": "w:end.end+0.3"`) and captions.
4. **Start the project.** `$VS examples` lists tested example projects (one per genre). `$VS new ~/videos/NAME --example
   GENRE_EXAMPLE` copies one (with placeholder assets) as `video.json`. Edit it; never start from a blank file.
5. **Check before rendering:**
   - `$VS validate video.json`: exact error location plus a "did you mean" hint. Fix and repeat.
   - `$VS inspect video.json`: every layer's time and on-screen box, plus warnings (overlapping text, text outside the safe
     area, layers never visible, voice cut off). Fix every warning unless it is intended.
   - `$VS timeline video.json`: scene start/end times and the words spoken in each.
6. **Look at it.** `$VS sheet video.json` writes `sheet.png` (3 frames per scene). Open the image and check the
   composition. Use `$VS frame video.json --scene ID --at 1.2` for one exact moment.
7. **Preview.** `$VS preview video.json` (432p, 15 fps, fast, cached per scene). Show it to the user; on Android
   `termux-open preview.mp4` opens the gallery. Use `--scene ID` to re-preview only what changed.
8. **Final.** `$VS render video.json` writes `video.mp4` at full quality. Scenes that are already rendered come from the
   cache, so after a small edit only that scene re-renders.

Every check is cheap. Use them after every meaningful edit instead of guessing.

## 2. The JSON in one screen

```jsonc
{
  "style": "documentary",                            // style pack: colors, fonts, background, grade, captions ($VS styles)
  "aspect": "9:16", "fps": 30,                       // 9:16 | 16:9 | 1:1 | 4:5  (or width/height)
  "transition": {"type": "fade", "duration": 0.4},   // default between scenes
  "look": {"vignette": 0.4, "grain": 0.2, "warmth": 0.2},
  "captions": {"style": "karaoke"},                  // needs voice words
  "audio": {
    "voice": {"src": "voice.mp3", "words": "voice.words.json"},
    "music": {"src": "music.mp3", "volume": 0.3, "duck": true},
    "sfx": [{"src": "sfx:impact", "at": "w:boom"}]
  },
  "defs": { /* reusable templates, see spec_reference.md */ },
  "scenes": [
    {
      "id": "hook", "until": "w:secret.end+0.3",     // or "duration": 4
      "background": {"image": "city.jpg", "motion": "ken_burns"},
      "camera": "push_in",
      "layers": [
        {"type": "text", "text": "The *secret* nobody tells you", "font": "display", "size": 110,
         "slot": "middle", "reveal": {"by": "word", "preset": "rise", "stagger": 0.08}, "sfx": "sfx:whoosh"},
        {"type": "image", "src": "hero_cut.png", "slot": "bottom_half", "at": "w:secret", "enter": "pop",
         "loop": "float", "shadow": true},
        {"use": "kit.stamp_rubber", "with": {"text": "TRUE"}, "x": "70%", "y": "60%", "at": "w:true"}   // ready component
      ]
    }
  ]
}
```

Layer types: `image` (also flipbooks, character poses, lip-flap), `video`, `text`, `counter`, `shape` (incl. rough
hand-drawn), `chart`, `particles`, `group` (nesting, masks), `stickman` (built-in animated stick figure: 21 poses, walk/
run/wave/dance, expressions, talking), `texture` (paper, notebook, chalkboard…) and `custom` (your own Python drawing).

**Kit:** ~70 ready components — kickers, headline treatments, polaroids/evidence photos, stamps, doodled marks, callouts,
lower thirds, breaking news + ticker, social post/chat/notification cards, stat cards, rings, charts helpers, map pins,
timelines, device frames, speech bubbles, retro game UI. `$VS kit [word]` lists them with parameters; `docs/kit.md`.
**Styles:** 18 packs (`noir cinematic documentary sticker box cute_toon kinetic crime news neon minimal retro8bit doodle
chalkboard luxury vaporwave vintage bold_explainer`); `docs/styles.md`. **Layouts:** `"layout": "hero"` etc. on a scene
adds non-overlapping slots (`docs/spec_reference.md`). Every layer can have `at`/`until`, position, `enter`/`exit` presets, `loop`
presets, keyframes in `animate`, `shadow`/`glow`, `blend` and `sfx`.

`$VS presets` prints every preset, loop, easing, transition, camera, slot, layout, caption style, particle kind, texture,
stickman pose/action/expression and built-in sound. Use only names from that list.

## 3. Rules that keep complex videos reliable

- **Build in layers of difficulty.** Get the scene list and durations right first, then the layouts (`inspect`, `sheet`),
  then the motion, then the sound. Don't write 30 animated scenes in one pass.
- **Short scenes.** 2–6 s for reels and 4–10 s for documentaries. Each scene renders and caches separately.
- **Position with slots** (`"slot": "top"`, `"hero"`, `"lower_third"`…) before reaching for pixel coordinates. Slots
  respect the phone safe area.
- **Sync with cues, not arithmetic:** `"at": "w:word"`, `"with:other_id+0.2"`, `"after:other_id"`, `"end-0.5"`.
- **Templates for repetition:** define a card or lower third once in `defs` and use it with `{"use": "card", "with": {...}}`.
- **Escalate only when needed:** a kit component or preset first, then `animate` keyframes, then a `custom` Python layer.
- **Music edits:** `"music": {"src": "song.mp3", "beats": "auto"}` and cues `b:9` / `bar:3` / `nb:2` cut on the beat.
- **No emoji glyphs** (no color-emoji font): use kit icons, shapes or PNGs.
- After any edit, run `validate` and `inspect` again; after a layout change, run `sheet` again.
- Tell the user where the output is and how long it took. If a render fails, show the error line and fix the JSON. Don't
  work around the engine.

## 4. Reference files (read with get_skill_file make_video …)

| file | read it when |
|---|---|
| `docs/spec_reference.md` | writing any JSON: every key of root, scene and each layer type, units, slots, layouts, cues, styles/theme, stickman, templates |
| `docs/kit.md` | choosing ready components (all ~70 with parameters) |
| `docs/styles.md` | choosing a style pack and theme tokens |
| `docs/animation.md` | motion: enter/exit presets, loops, keyframes, easing, text reveals, camera, transitions |
| `docs/audio_captions.md` | voice, word timings, music ducking, sound effects, caption styles |
| `docs/recipes.md` | ready patterns: kinetic typography, documentary collage, lower thirds, map route, data story, split screen, video-in-text, parallax, product promo, countdown |
| `docs/custom_layers.md` | something no layer type can draw (custom Python `render(ctx)`) |
| `docs/preview_qa.md` | the review loop, what `inspect` warnings mean, phone performance tips |
| `docs/troubleshooting.md` | an error you don't understand, slow renders, font/Hindi issues |
| `examples/*.json` | complete working videos to copy from (`$VS new DIR --example NAME`) |

## 5. Genre skills (read the one that matches before planning)

| genre skill | for | example |
|---|---|---|
| `genre_explainer` | faceless "how/why" explainers | `explainer_stickman` |
| `genre_stickman_story` | stick-figure skits, comedy, stories | `stickman_story` |
| `genre_documentary` | Vox-style essays, history, "the story of" | `documentary_vox` |
| `genre_true_crime` | true crime, mystery, suspense, horror | `true_crime` |
| `genre_kinetic_typography` | kinetic text, lyric videos | `kinetic` |
| `genre_beat_montage` | music edits, montages, recaps | `beat_montage` |
| `genre_news_social` | news recaps, tweets/posts, chat stories | `news_social` |
| `genre_data_story` | statistics, finance, comparisons | `data_story` |
| `genre_product_promo` | ads, app/product promos, launches | `product_promo` |
| `genre_listicle` | top-N, countdowns, tier lists | `listicle_countdown` |
| `genre_whiteboard` | whiteboard, doodle, chalkboard lessons | `doodle_whiteboard` |
| `genre_retro_arcade` | 8-bit, VHS, vaporwave | `retro_arcade` |
| `genre_tutorial` | software/how-to walkthroughs | `tutorial_screen` |
| `genre_travel` | travel, vlogs, map journeys | `travel_map` |
| `genre_quotes` | quotes, motivation, poems | `quote_motivation` |
| `genre_talking_head` | editing a recorded speaker/podcast | `talking_head` |
| `genre_kids` | children's education and cartoons | `kids_cartoon` |

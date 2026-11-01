# AntiGem Plugins

Custom plugins for the AntiGem app, installable straight from this repository
([github.com/Santoshkurmi/antigem_plugins](https://github.com/Santoshkurmi/antigem_plugins)).

## Install in the app

1. Open **Settings → Custom AntiGem Plugins → Repositories**.
2. Add this repository. Any of these work:
   - `Santoshkurmi/antigem_plugins`
   - `Santoshkurmi/antigem_plugins@main` (a specific branch or tag)
   - `https://github.com/Santoshkurmi/antigem_plugins`
3. Pick a plugin from the list and install it. When a newer version is pushed here, the plugin card offers the update;
   updating keeps the plugin's ID, stored data and MCP connection.

## Plugins

| plugin | version | folder | what it does |
|---|---|---|---|
| **Video Studio** | 1.0.0 | [`plugins/video-studio`](plugins/video-studio) | Make edited videos on the phone from a JSON timeline. Skills only (no MCP tools). |

### Video Studio

The model writes a JSON timeline (scenes, layers, keyframes, text reveals, camera, transitions, captions, sound) and a
bundled Python engine (FFmpeg + Pillow + NumPy) renders it to MP4 on the device.

- **20 skills**: `make_video` (workflow + engine), `video_direction` (creative rules), `flow_assets` (assets via the
  Google Flow plugin) and 17 genre skills: explainer, stickman story, documentary, true crime, kinetic typography, beat
  montage, news & social, data story, product promo, listicle, whiteboard, retro arcade, tutorial, travel, quotes,
  talking head, kids.
- **Engine**: image, video, text, counter, shape, chart, particles, group/mask, built-in stickman, procedural textures
  and custom Python layers; 34 enter/exit presets, 15 loops, keyframes with 40+ easings, camera moves, 40+ transitions,
  word-synced captions, beat detection, voice ducking, 31 built-in sound effects, transparent WebM output.
- **18 style packs** and **~70 ready components** (lower thirds, stamps, polaroids, news tickers, post cards, stat
  cards, speech bubbles, retro game UI…).
- **Review tools for the model**: `validate`, `inspect` (layout + pacing warnings), `sheet` (contact sheet), `frame`,
  fast cached `preview`.

**Requirements on the device** (the `make_video` skill tells the model to run `studio.py doctor` and install what is
missing): Python 3.9+, Pillow, NumPy, FFmpeg.
Termux: `pkg install python ffmpeg python-pillow python-numpy` ·
Ubuntu/Debian: `apt install -y python3 python3-pil python3-numpy ffmpeg`.
Optional: `pip install edge-tts` (voice-over with word timings), `pip install faster-whisper` (timings from a recording).

The Google Flow plugin is only needed to generate images/clips; the engine works with any local assets.

## Repository layout

```
antigem-plugins.json        ← index the app reads (one entry per plugin)
plugins/
  video-studio/             ← one folder per plugin = what you would otherwise ZIP
    manifest.json
    icon.png
    skills/
      make_video.md         ← skill files (listed by the app)
      make_video/           ← detail files: engine/, docs/, kit/, styles/, examples/, fonts/
      genre_*.md
```

## Add another plugin

1. Create `plugins/<name>/` with a `manifest.json` (a unique `id`, a `version`, `name`, optional `icon`) plus a
   `skills/` folder and/or a background worker with `mcp_tools`.
2. Add an entry to `antigem-plugins.json`:
   ```json
   {"path": "plugins/<name>", "id": "<id>", "name": "<Name>", "version": "1.0.0", "description": "…", "icon": "icon.png"}
   ```
   `path`, `id` and `version` must match the plugin folder and its manifest.

## Release an update

1. Change the plugin's files.
2. Raise `version` in its `manifest.json` (e.g. `1.0.0` → `1.1.0`).
3. Raise the same `version` in `antigem-plugins.json`. Keep the two equal, otherwise the app keeps showing an update.
4. Commit and push to `main`:
   ```bash
   git add .
   git commit -m "video-studio 1.1.0: …"
   git push
   ```

## First push (one time)

```bash
git remote add origin https://github.com/Santoshkurmi/antigem_plugins.git
git branch -M main
git add .
git commit -m "Add Video Studio plugin"
git push -u origin main
```

The repository must be **public**; the app installs only from public GitHub repositories.

## Licenses

The bundled fonts are under the SIL Open Font License 1.1
(see [`plugins/video-studio/skills/make_video/fonts/LICENSES.md`](plugins/video-studio/skills/make_video/fonts/LICENSES.md)).
The example placeholder images and clip were generated for this repository. Built-in sound effects are synthesized
by the engine.

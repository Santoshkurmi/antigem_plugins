---
name: Generate video assets with Google Flow
description: Make images, cut-out characters/objects and short clips for a Video Studio project with the Google Flow plugin's tools, then key and organize them into the project's assets folder.
---

# Generate assets with Google Flow

Video Studio composes videos from assets. When the user has none, generate them with the **Google Flow** plugin's MCP
tools (`flow_*`). This plugin has no generation tools of its own. If the Flow tools are not connected, tell the user to
add the Google Flow plugin's MCP and stop. Don't fake assets with crude drawings.

## 0. Before generating

1. `flow_status`: it must say `logged_in: true`. If not, ask the user to sign in to Flow in the AntiGem browser.
   Note the remaining credits and tell the user roughly how many images/clips you plan (and the cost) before a big batch.
2. Use one Flow project per video: `flow_create_project {"title": "<video name>"}`.
3. Plan the asset list from the shot list: backgrounds, cut-outs (characters, objects, props, icons), B-roll clips.
   Name every asset now (`bg_city_night`, `hero_wave`, `prop_coin`). Reuse assets across scenes.

## 1. Prompts that composite well

**Cut-outs (characters, objects, icons):** these are layered over backgrounds, so ask for a solid magenta background:

> `<subject, pose, style>`, full body, centered, isolated on a solid flat magenta background (#FF00FF), no shadow on the
> background, no text, crisp edges, even studio lighting

- Same style keywords for every asset of a video (e.g. "flat vector illustration, thick outlines, warm palette" or
  "photorealistic, soft daylight"). Keep that style line identical in every prompt.
- Characters that recur: generate a reference first, then pass it in `references` for later poses (or use
  `flow_generate_character` / `flow_upload_character` handles) so the face and clothes stay consistent.
- Avoid magenta, pink and purple in the subject itself (they would be keyed out). For pink subjects use a green
  background (#00FF00) and `--color "#00FF00"` when keying.

**Backgrounds:** "wide establishing shot, `<place>`, `<time of day>`, `<style>`, empty space in the `<upper third>` for
titles, no text, no people". Request the video's aspect (`9:16` or `16:9`). Leave room where text will go.

**B-roll clips (`flow_generate_video`):** short (4–8 s), one action, camera move stated ("slow push-in", "static tripod
shot"). Use them as `video` layers or scene backgrounds with `trim`.

## 2. Generate

- Pass several prompts at once in `items` of `flow_generate_image` (each with its own prompt and aspect). The Flow tool
  paces them itself; don't loop one call per image unless the tool tells you to.
- Use `flow_get_job` to wait; results come back as local file paths in `~/flow-media`.
- Look at results (`flow_get_media` with `view: true`). Regenerate the ones that don't match the style or have text
  artifacts. Use `flow_edit_image` for small fixes ("remove the logo on the shirt").
- Upscale only finals that appear large on screen (`flow_upscale_image`).

## 3. Bring into the project

```bash
mkdir -p ~/videos/NAME/assets
cp ~/flow-media/<file>.png ~/videos/NAME/assets/hero_wave_magenta.png
$VS key ~/videos/NAME/assets/hero_wave_magenta.png        # → hero_wave_magenta_cut.png (transparent, trimmed)
```

Open the `_cut.png` once to check the edges. If magenta fringes remain, raise `--tolerance 0.25`; if parts of the
subject vanished, lower it to `0.12`. Use the cut file in JSON: `{"type": "image", "src": "hero_wave_magenta_cut.png", ...}`.
Or skip pre-keying and use `"key": true` on the layer (slower per render).

Keep a short `assets/ASSETS.md` listing each file, its prompt and where it is used. Then regenerating one asset is easy.

## 4. Real (non-AI) assets

Prefer the user's own photos/clips, and footage they say is licensed. Don't download images from the web for the user
without confirming they have the rights. Fonts in `make_video/fonts` are open-licensed (SIL OFL).

# Create easily: ready recipes

Each recipe below is the shortest path to a common result: a few calls you can copy, then a check. Ids such as
`el_title` stand for the ids the earlier calls return.

## Before you start

- **Times:** task tools take ms from the video start. `set_track` keys take ms from the element's start.
- **Positions and sizes:** canvas fractions 0..1 (x right, y down).
- **Colours:**
  - In model fields (`style.color`, `media.key.color`…) colours are ARGB **numbers** (0xFFE63946 = 4293277254).
  - In tracks, effect params and component fields they are **strings** `"#RRGGBB"`, or `"#RRGGBBAA"` with alpha
    **last** (CSS order). Never write `"#AARRGGBB"`.
- **Changing fields after creating something:**
  - `upsert_items kind=element items=[{id: "el_x", …fields}]`. Only the fields you give change.
  - For many changes at once, put them in `batch`: one undo step for everything.
- **Checking your work:** `sample_tracks` checks motion as numbers, `get_frame` checks a moment, and `preview_video`
  lets the user watch.

## Quick start: a video in 4 calls

```json
{"name": "create_video_project", "arguments": {"name": "Launch", "aspect": "PORTRAIT_9_16", "duration_ms": 15000, "pack": "neon"}}
{"name": "place_template", "arguments": {"template_id": "title_card", "at_ms": 0}}
{"name": "add_component", "arguments": {"component_id": "progress_ring", "start_ms": 4000, "values": {"percent": 82, "label": "Faster", "color": "#4CC9F0"}}}
{"name": "preview_video", "arguments": {"quality": "720p"}}
```

## Text and titles

- **Letters that wave, pop or rise:**
  ```json
  {"name": "add_element", "arguments": {"type": "TEXT", "text": "Big *news*", "start_ms": 0, "set": {"letters": {"preset": "pop"}}}}
  ```
  The presets are `wave`, `rise`, `pop`, `typewriter`, `bounce`, `jitter`, `rainbow`, `spin_in`, `drop`,
  `words_up` and `glow_pulse`.
- **A title card, progress ring or subscribe button with editable fields:** use components (see the
  [Components](#components-reusable-pieces-with-fields) section).
- **A neon glow:**
  ```json
  {"name": "add_effect", "arguments": {"element_id": "el_title", "effect": "glow", "params": {"radius": 0.03, "tint": "#FF2BD6"}}}
  ```
- **A glitch hit at 2 s:**
  ```json
  {"name": "add_effect", "arguments": {"element_id": "el_title", "effect": "glitch"}}
  {"name": "set_track", "arguments": {"element_id": "el_title", "prop": "fx.<fx_id>.amount", "keys": [{"ms": 1900, "v": 0}, {"ms": 2000, "v": 1}, {"ms": 2300, "v": 0}]}}
  ```
  Use the `fx_id` the reply gives you.

## Motion

- **A smooth move with overshoot:**
  ```json
  {"name": "set_track", "arguments": {"element_id": "el_x", "prop": "x", "keys": [{"ms": 0, "v": -0.6}, {"ms": 700, "v": 0, "ease": "outBack"}]}}
  ```
- **A curved path:** `prop: "pos"` keys `[{ms: 0, v: [0.1, 0.8], out: [0.2, -0.6]}, {ms: 1500, v: [0.9, 0.8], in: [-0.2, -0.6]}]`.
- **A ready-made motion:**
  ```json
  {"name": "apply_behavior", "arguments": {"element_id": "el_x", "behavior": "float"}}
  ```
  Others: `pendulum`, `pulse`, `spin`, `orbit`, `card_flip`, `heartbeat`, `beat_pulse`…
- **A curve that draws itself, with a dot riding it:**
  ```json
  {"name": "add_element", "arguments": {"type": "PATH", "start_ms": 0, "set": {"d": "M0.1 0.8 C0.35 0.05 0.65 0.05 0.9 0.8"}}}
  {"name": "add_element", "arguments": {"type": "EMOJI", "src": "🚀", "start_ms": 0, "set": {"follow": "el_path", "orient": true}}}
  ```
  A PATH draws itself on by default.
- **Motion blur** on fast moves: `upsert_items kind=element items=[{id: "el_x", motionBlur: 0.5}]`.
- **Pulsing to the music:**
  ```json
  {"name": "set_track", "arguments": {"element_id": "el_logo", "prop": "scale", "expr": "value*(1+0.15*audio.pulse)"}}
  ```
  Call `get_beats` for beat times when you want cuts on the beat.

## Components (reusable pieces with fields)

```json
{"name": "add_component", "arguments": {"component_id": "title_card", "start_ms": 0, "values": {"title": "Big idea", "subtitle": "Why it matters", "accent": "#E63946"}}}
{"name": "set_fields", "arguments": {"element_id": "<group_id>", "values": {"title": "Even bigger idea"}}}
```

- The built-in components are `progress_ring` (`percent`, `label`, `color`), `title_card` (`title`, `subtitle`,
  `accent`) and `subscribe` (`label`, `done`, `color`, `clickAt`). `studio_catalog components` lists them and
  any components from plugins.
- They keep their shape on any format: a ring stays round on 9:16.
- Move or animate the returned group, and all its parts follow.

## Background removal and green screen

- **Cut a person or product out of a photo:**
  ```json
  {"name": "remove_background", "arguments": {"element_id": "el_photo"}}
  ```
  If it reports that the model is unavailable, use the magic wand, which always works:
  ```json
  {"name": "remove_background", "arguments": {"element_id": "el_photo", "method": "wand", "points": [{"x": 0.03, "y": 0.03, "tolerance": 0.25}], "feather": 2}}
  ```
  Tap the background with `mode` `remove`. Or tap the subject and set `invert: true`. `restore: true` brings
  the original back.
- **A green-screen video:**
  ```json
  {"name": "add_element", "arguments": {"type": "VIDEO", "src": "<imported path>", "set": {"media": {"key": {"mode": "chroma", "color": 4278235456, "similarity": 0.4, "smoothness": 0.08, "spill": 0.1}}}}}
  ```
  - For a blue screen, `color` is 4278208443.
  - To judge the key, set `media.key.showMatte: true` and call `get_frame`: white is kept, black is removed.
    Turn it off afterwards.
- **Fire, sparks or light leaks shot on black:** a VIDEO element with `blend: "screen"`. No key is needed.
- **A person cut out of a video without a green screen:** `remove_background` on the VIDEO element. It is
  slow, for clips up to 2 minutes.

## Compositing

- **Video inside big text:**
  ```json
  {"name": "add_element", "arguments": {"type": "TEXT", "text": "OCEAN", "box": {"left": 0.05, "top": 0.35, "right": 0.95, "bottom": 0.65}, "set": {"style": {"size": 0.3}}}}
  {"name": "add_element", "arguments": {"type": "VIDEO", "src": "<waves.mp4>", "box": {"left": 0, "top": 0, "right": 1, "bottom": 1}, "set": {"matte": {"from": "el_text", "mode": "alpha"}}}}
  ```
  The text becomes the window and is hidden itself. Use `lumaInverted` and the other modes for other looks.
- **A film colour grade over everything:**
  ```json
  {"name": "add_element", "arguments": {"type": "ADJUST", "start_ms": 0}}
  {"name": "add_effect", "arguments": {"element_id": "el_adjust", "effect": "lut", "params": {"look": "teal_orange", "amount": 0.8}}}
  ```
  The looks are `teal_orange`, `warm_film`, `cool_blue`, `bleach`, `noir`, `vintage`, `pastel`, `cyberpunk`,
  `golden_hour`, `matrix`, plus plugin `.cube` files (`studio_catalog luts`). An adjustment layer changes
  everything under it (lower `z`) inside its box.
- **A spotlight (darken everything but a circle):**
  ```json
  {"name": "add_element", "arguments": {"type": "ADJUST", "start_ms": 2000, "end_ms": 6000}}
  {"name": "add_effect", "arguments": {"element_id": "el_adjust", "effect": "adjust", "params": {"exposure": -0.6}}}
  {"name": "add_mask", "arguments": {"element_id": "el_adjust", "shape": "ellipse", "box": {"left": 0.3, "top": 0.35, "right": 0.7, "bottom": 0.55}, "invert": true, "feather": 0.12}}
  ```
- **Show only part of an element:**
  ```json
  {"name": "add_mask", "arguments": {"element_id": "el_x", "shape": "ellipse", "feather": 0.05}}
  ```
  Use `mode: "subtract"` to cut a hole instead.
- **A rotoscoped mask (the shape changes over time):** `add_mask shape=path keys=[{ms: 0, d: "M…"}, {ms: 1000, d: "M…"}]`.
- **A screen recording on a phone or billboard in perspective:**
  `upsert_items kind=element items=[{id: "el_video", pin: [{x: 0.30, y: 0.22}, {x: 0.72, y: 0.26}, {x: 0.70, y: 0.62}, {x: 0.31, y: 0.66}]}]`.
  The points go top-left, top-right, bottom-right, bottom-left. Animate them with `set_track prop=pin.0` … `pin.3`.
- **Blends that mix with what's underneath:** `blend` = `overlay`, `softlight`, `hardlight`, `colordodge`,
  `colorburn`, `darken`, `lighten`, `difference`, `exclusion`, `hue`, `saturation`, `color` or `luminosity`.

## Video timing

- **A slow-motion ramp, freeze or reverse:** `set_track prop=time` gives the seconds into the file. The video's
  sound goes silent while it is remapped.
  ```json
  {"name": "set_track", "arguments": {"element_id": "el_video", "prop": "time", "keys": [{"ms": 0, "v": 0}, {"ms": 1500, "v": 1.5}, {"ms": 4500, "v": 2.2, "ease": "inOutSine"}, {"ms": 6000, "v": 3.7}]}}
  ```
  - Freeze: two keys with the same `v`.
  - Reverse: `v` goes down.
  - Plain slow motion: `expr: "time*0.5"`.
- **A label that sticks to something moving:** put the element over the thing at its start, then call:
  ```json
  {"name": "follow_motion", "arguments": {"element_id": "el_label"}}
  ```
  - It follows whatever is under it in the recording or video and writes a `pos` track.
  - Add `with_scale: true` to also follow zooms in recordings.
  - Undo it with `set_track prop=pos remove=true`.

## Particles and sound

- **Fire, sparks, confetti, snow…:**
  1. Read `studio_catalog particle_presets`.
  2. Add the emitter with one preset's values:
     ```json
     {"name": "add_element", "arguments": {"type": "PARTICLES", "design": "emitter", "box": {"left": 0, "top": 0.85, "right": 1, "bottom": 1}, "set": {"params": {"…": "copy the preset's params"}, "blend": "add"}}}
     ```
  3. Set `style.color` and `style.accent` from the preset.
- **A whoosh on entry:** `upsert_items kind=element items=[{id: "el_x", sounds: [{on: "enter", src: "sfx:whoosh", offsetMs: -120}]}]`.
- **A transition sound:** `scene.transition.sound = "sfx:swoosh"`.

## Math and drawings

- **A graph that morphs:**
  ```json
  {"name": "add_element", "arguments": {"type": "GRAPH", "set": {"graph": {"x": [-6.5, 6.5], "y": [-1.6, 1.6], "plots": [{"y": "sin(k*x)"}]}, "params": {"k": 1}}}}
  ```
  Then animate it with `set_track prop=k keys=[{ms: 0, v: 1}, {ms: 2000, v: 3}]`.
- **An equation:** `add_element type=MATH text="\\int_0^1 x^2\\,dx = \\frac{1}{3}"`. For a hand-written
  look, make it into SVG (MathJax) and call `import_svg svg=… draw_on=true`.
- **An icon or logo that draws itself:** `import_svg path=… draw_on=true`.

## Make it reusable

- **Keep a scene for later:** `save_template`.
- **Your own component:** `create_plugin components=[…]` (`describe_model component_def`).
  - Boxes are 0..1 of the component.
  - Text and colour fields appear as `{name}` in texts and as `field.name` in formulas; number fields as
    `param.name`.
  - Then run `test_plugin` and fix any `component_problems`.
- **Your own colour look:** `create_plugin luts=[{id: "my_look", name: "My look", cube: "LUT_3D_SIZE 33\n…"}]`.
- **Effects, transitions and behaviours:** see `plugins.md`.

## If it doesn't look right

| Problem | Fix |
| --- | --- |
| Nothing shows | Is the element inside its time? Does an entrance animation start invisible? Check `get_frame` a second later |
| Colour is wrong | You wrote `"#AARRGGBB"`. Use `"#RRGGBB"` or `"#RRGGBBAA"` |
| A formula does nothing | `check_expression` first; problems are listed in `set_track`'s reply |
| The adjustment layer changes nothing | It only affects elements below it (`z`) and inside its box |
| The track matte hides everything | The `from` element isn't on screen at that moment |
| The key leaves green edges | Raise `similarity` a little, add `spill`, and look with `showMatte` |

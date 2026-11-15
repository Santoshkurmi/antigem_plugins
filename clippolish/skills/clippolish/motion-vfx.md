# Motion, maths, VFX and sound

Use this file for anything that moves in a custom way: curves, orbits, graphs, equations, 3D flips, letter
animations, particles, glows, keying, sound effects, music-reactive motion and scripted layouts. The full
reference is `studio_catalog`. It has these sections: `track_props`, `ease_presets`, `ease_grammar`,
`expressions`, `motion_cookbook`, `effects`, `shader_transitions`, `behaviors`, `particle_params`,
`particle_presets`, `sfx`, `audio_fx`, `blend_modes`, `keying`, `generators`, `layers`, `components`, `luts` and
`fonts`. Read it once. For copy-paste recipes (video in text, film grade, spotlight, speed ramp, green screen,
labels that follow things, components) see `create-easily.md`.

**Colours.**
- In model fields (`style.color`, `media.key.color`) colours are ARGB numbers.
- In track keys, effect params and component fields they are strings: `"#RRGGBB"`, or `"#RRGGBBAA"` with alpha
  last (CSS order). Never `"#AARRGGBB"`; it reads as a different colour.

## 1. Animate any property: `set_track`

Never fake a curve with dozens of keyframes. Use one track per property, with keys and any easing, a formula,
or both.

```json
{"name": "set_track", "arguments": {"element_id": "el_x", "prop": "rotation",
  "keys": [{"ms": 0, "v": 0}, {"ms": 1200, "v": 360, "ease": "outBack"}], "after": "loop"}}
{"name": "set_track", "arguments": {"element_id": "el_x", "prop": "y", "expr": "value + 0.02*sin(time*4)"}}
```

**Properties**
- `x` and `y` move the element (canvas fractions).
- `pos` sets the absolute centre `[x, y]`. Its keys may have `in` / `out` handles for curved motion.
- `scale`, `scaleX`, `scaleY`, `rotation` and `opacity` work as you'd expect.
- `rotX` and `rotY` turn the element in 3D (card flips).
- `style.color`, `style.size`, `style.strokeWidth` and `style.glow` change the look.
- `value` is the number on counters.
- `trimStart`, `trimEnd` and `trimOffset` draw a path on.
- `morph` blends a path into its `morphTo` shape.
- `pathProgress` positions an element along the path it follows.
- `draw` draws a graph's curves on.
- `fx.<fx_id>.<input>` animates an effect setting.
- Any param name works too, such as a graph variable `k`.

**Easings:** `linear`, `smooth`, `outCubic`, `inOutSine`, `outBack`, `overshoot`, `outBounce`,
`outElastic`, `cubic(x1,y1,x2,y2)`, `spring(stiffness,damping)`, `steps(n)`, `hold`, and plugin names.

**After the last key:** `hold`, `loop`, `pingpong`, `offset` (keeps adding) or `continue` (keeps its speed).

- `time` on a VIDEO is time remap: seconds into the file after the trim. Equal values freeze the picture, falling
  values reverse it. Remapped videos are silent.
- `pin.0` … `pin.3` are corner-pin points `[x, y]`; `mask.<i>.feather` / `expand` / `opacity` / `x` / `y` /
  `scale` / `rotation` animate masks.

**Formulas** can use these variables:
- `time` (seconds into the element), `life` (0..1), `value` (the keyed value)
- `index` and `count` (repeater copies)
- `aspect`, `param.k` (also the group's or component's params), `field.name` (a component field: `#hex` gives a
  colour)
- `audio.level`, `audio.bass`, `audio.pulse`, `beat`

and these functions: `sin`, `noise`, `wiggle(freq, amp)`, `interpolate(x, [..], [..], "ease")`,
`ease(x, "spring(…)")`, `spring(t, k, d)`, `ref("el_id", "rotation")`, `hsl()`, and more (see `expressions`).
- A broken formula is reported in `problems` and falls back to `value`.
- Check any formula first with `check_expression`.
- Then confirm the motion with `sample_tracks`. It returns numbers (centre x/y, rotation, scale, opacity,
  params), so you can verify motion without frames.

**Ready-made motion.** `apply_behavior` with `pendulum`, `float`, `wiggle`, `pulse`, `spin`, `orbit`,
`shake_in`, `pop_bounce`, `blink`, `card_flip`, `tilt_3d`, `beat_pulse`, `loudness_bounce` or `heartbeat`.
It adds params (tune them with `params`) and formula tracks.

## 2. Shapes, curves, graphs, equations

- **PATH**:
  - `add_element type=PATH set={d: "M0.1 0.8 C0.35 0.05 0.65 0.05 0.9 0.8"}`. The coordinates are canvas
    fractions (x of the width, y of the height), so a true circle needs `/aspect` on x.
  - Style: `style.stroke`, `style.strokeWidth` (≈0.006–0.015), `style.fill` (+ `gradientTo`), `style.dashed`.
  - Params: `arrowEnd` / `arrowStart` = 1 for arrow heads; `trimEach` = 1 draws every sub-path together
    (handwriting).
  - Draw-on: animate the `trimEnd` track from 0 to 1. The fill fades in at the end.
  - Morph: set `morphTo` plus a `morph` track.
- **SHAPE** path designs: `polygon`, `star`, `arc`, `ring`, `pie`, `spiral`, `wave`, `zigzag`, `burst` and
  `plus`, with params such as `sides`, `points`, `inner`, `start`, `sweep`, `turns`, `cycles` and `amp`.
- **Follow a path**:
  - Set `follow` to a PATH id (or to path data) and `orient` = true; it travels over the element's life.
  - For your own timing, add a `pathProgress` track.
- **GRAPH**: the `graph` object has these fields:
  - `x`, `y` (ranges)
  - `xStep` (1.5708 gives π/2 ticks)
  - `grid`, `axes`, `labels`, `equal`
  - `plots`: `{y: "sin(k*x)"}`, `{x: "cos(3*s)", y: "sin(2*s)", range: [0, 6.283]}` or `{r: "1+cos(th)"}`, each
    with `color`, `width`, `dashed`, `fill`, `label`, `tracer` and `draw`
  - `points`: `{x, y, label, vector, guides}`; formulas are allowed

  Put variables in `params` (`{k: 1}`) and animate them with `set_track prop=k`. Draw it on with
  `prop=draw`.
- **MATH**:
  - `text` = LaTeX (`\frac{a}{b}`, `\int_0^1`, `\sum`, Greek). Check it with `check_expression latex=…`.
  - For a hand-written "Write" effect, render the LaTeX to SVG on your side (MathJax) and call
    `import_svg svg=… draw_on=true`.
- **SVG / icons / logos**: `import_svg path=… | svg=…`. Several colours become a GROUP of PATHs.
- **Lottie**: `type=LOTTIE src=<.json / .lottie>`. It plays over the element's time (params `speed`, `loop`);
  for exact frames, animate a `progress` track.

## 3. Rigs: groups, parents, copies, 3D, letters

- `type=GROUP` is an invisible parent. Children set `parent: <id>` and move, turn, scale and fade with it.
  Animate the group to move them all; nested orbits are parent chains.
- `repeat: {count, dx, dy, rotation, pivot: {x, y}, scale, opacity, delayMs}` makes copies.
  - A ring: put the element above the centre with `rotation: 360/count` and `pivot` at the centre.
  - Staggered rows: `delayMs`.
  - Formulas see `index` and `count`.
- **3D**: the `rotX` and `rotY` tracks, or the `card_flip` behaviour.
- **TEXT letters**:
  - `letters: {preset: wave | rise | pop | typewriter | bounce | jitter | rainbow | spin_in | drop | words_up | glow_pulse}`
  - or per-letter formulas: `{by: letter | word, x, y, rotation, scale, opacity, color}` using `index`,
    `count` and `time`.

## 4. VFX

- **Effects**:
  - `add_effect effect=glow | blur | shadow | outline | adjust | duotone | blackwhite | invert | posterize | pixelate | rgbsplit | glitch | wave | ripple | twirl | bulge | mirror | edges | grain | scanlines | vignette | fadeedges | halftone`,
    plus plugin effects. They stack in order.
  - `params` set the inputs (sizes are fractions of the shorter side).
  - The reply's `fx_id` is what you animate: `fx.<fx_id>.radius`.
  - If a shader fails on this phone, `shader_problems` says why and the element draws without it.
- **Blend**: `blend: add | screen` for fire, sparks, light leaks or smoke shot on black (no key needed);
  `multiply` for shadows and paper.
- **Green / blue screen**:
  - `media.key: {mode: "chroma", color: 4278235456 (0xFF00B140 green) | 4278208443 (0xFF0047BB blue), similarity: 0.4, smoothness: 0.08, spill: 0.1}`
  - `{mode: "luma", lumaMin}` removes dark parts; `{mode: "luma", lumaMax}` removes light parts.
  - The same works for the webcam: `/webcam/key`.
- **Cut a picture out**:
  - `remove_background element_id=…` runs on the phone and may download a model the first time.
  - If it fails, the reply says why and nothing changed; use a key instead.
  - `restore=true` puts the original back.
- **More blends**: `overlay`, `softlight`, `hardlight`, `colordodge`, `colorburn`, `darken`, `lighten`,
  `difference`, `exclusion`, `hue`, `saturation`, `color` and `luminosity` mix with the picture underneath.
- **Masks** (`add_mask`):
  - Shapes in the element's own box (0..1), so they move with it: `ellipse`, `rect`, or `path` (`d`).
  - Modes `add`, `subtract`, `intersect` and `difference`, plus `feather` and `expand` (fractions of the shorter
    side), `invert` and `opacity`.
  - Rotoscoping: `keys [{ms, d, ease}]` gives path shapes over time.
- **Track matte**: the element field `matte: {from: "<id>", mode: alpha | alphaInverted | luma | lumaInverted}`. The
  element shows only where the other one is; the other one is hidden. Video inside text: the VIDEO gets
  `matte {from: <text id>}`.
- **Adjustment layer**: `add_element type=ADJUST`, then `add_effect` on it (`adjust`, `lut`, `blur`, `pixelate`,
  `glitch`…).
  - It changes everything under it inside its box.
  - Use the box, masks and opacity to limit it, and `z` for what it covers.
- **Colour looks**: `add_effect effect=lut params {look: "teal_orange", amount: 0.8}`. `luts` in the catalog lists
  the looks (built-in and plugin `.cube`).
- **Corner pin**: the element field `pin: [{x,y} TL, TR, BR, BL]` in canvas fractions. Use it to put a recording or
  picture onto a screen or sign; animate it with `pin.i` tracks.
- **Motion blur**: the element field `motionBlur: 0.5` (shutter). Fast moves smear like a camera.
- **Follow something moving**: `follow_motion element_id=…` tracks what is under the element in the recording or a
  video and writes its `pos` track. `with_scale` also follows zooms.
- **Check a key**: `media.key.showMatte: true`, then `get_frame` shows white for kept and black for removed. Turn it
  off afterwards.
- **Cut out by colour**: `remove_background method="wand" points=[{x, y, tolerance, mode: remove|keep}]`. It needs
  no model, and it refines an existing cut-out.
- **Particles**:
  - `type=PARTICLES design="emitter"`. The box is the emitter.
  - Params come from `particle_presets` (fire, smoke, sparks, magic, confetti, explosion, rain, bubbles,
    snow, fountain): copy one preset's params, colours (`style.color` → `style.accent` over life) and blend.
  - `src` = an emoji or picture to use as the sprite.
- **Scene transitions**: `scene.transition {style: FADE, custom: "ripple_dissolve" | "burn" | "pixel_dissolve" | "circle_open" | "swirl" | "directional_warp" | <plugin id>, params}`.

## 5. Sound

- **Sounds tied to elements**: `element.sounds: [{on: "enter" | "exit" | "end" | <cue>, src: "sfx:whoosh", volume, offsetMs}]`.
  - They move with the element.
  - Built-in sounds: `sfx:whoosh`, `swoosh`, `swipe`, `pop`, `click`, `tick`, `ding`, `sparkle`, `riser`,
    `impact`.
  - Plugin sounds: `sfx:<plugin>/<id>`.
  - Your own files work too (`import_asset` first).
- **Transitions**: `scene.transition.sound = "sfx:whoosh"`.
- **Clip effects**: `audio.clips[].fx: [{type: eq | lowpass | highpass | reverb | echo | compressor | distortion | telephone | radio | gate, params}]`.
- **Envelopes**: `audio.clips[].tracks {volume: …, pan: …}`; keys are µs from the clip start.
- **Beats**:
  - `get_beats` gives beat times and bpm. Call it again until `ready`.
  - Use the times to cut scenes or place keys on the beat.
  - Formulas react live: `scale: value*(1+0.15*audio.pulse)`.

## 6. Components

- `add_component component_id=progress_ring | title_card | subscribe | <plugin>/<id> values={…}` places a GROUP with
  fields plus its parts.
- `set_fields element_id=<group> values={title: "…", accent: "#00AAFF", percent: 80}` changes them later, and every
  part updates.
- `components` in the catalog lists each component's fields.

## 7. Scripts and plugins

- **Generators**: `run_generator generator_id=… input={…} at_ms=…` places what an installed script makes.
  - To test your own script: `run_generator js="function generate(input, ctx) { return { elements: [...] } }" dry_run=true`.
  - Scripts run sandboxed: separate process, no files or network, 10 s.
- **Plugin parts**: plugins can ship `effects`, `transitions`, `behaviors`, `eases`, `generators`, `sounds`,
  `luts` (`.cube` looks), `fonts` and `components` (see `plugins.md`).

## 8. Check your work

`sample_tracks` (numbers) → `get_frame` at 2–3 moments → `preview_video`. Moving formulas and draw-ons only
show over time, so describe what will happen when you report.

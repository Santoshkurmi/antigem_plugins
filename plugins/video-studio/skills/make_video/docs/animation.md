# Animation

Motion has four sources, and they combine:

1. **Base values**: `x`, `y`, `scale`, `rotation`, `opacity`… on the layer.
2. **Keyframes** in `animate`: they replace a base value over time.
3. **Enter/exit presets** at the start and end of the layer's life.
4. **Loops** for the whole life of the layer (float, sway, pulse…).

Presets and loops add offsets on top of the base/keyframed value, so a layer can have keyframes moving it across the
screen, an enter `pop`, a `float` loop and an exit `fade` all at once.

## Enter / exit presets

`"enter": "pop"` or `"enter": {"preset": "slide_up", "duration": 0.6, "delay": 0.1, "ease": "out_back", "distance": 300}`.
Exits play the same preset in reverse at the end of the layer (`until`/scene end): `"exit": "fade"`.

| preset | effect | good for |
|---|---|---|
| `fade` | opacity | anything calm |
| `pop`, `pop_rotate`, `bounce_in` | scale up with overshoot | stickers, icons, emphasis words |
| `zoom_in` (`from` 0.2), `zoom_out` (`from` 1.8) | big scale change | titles, reveals |
| `slide_up/down/left/right` (`distance`) | short slide + fade | text, cards |
| `fly_up/down/left/right` | enters from off-screen | panels, split screens |
| `rise` | small upward drift + fade | elegant text |
| `drop` | falls in with a bounce | objects, stamps |
| `spin` (`angle`) | rotate + scale | badges, icons |
| `blur_in` (`amount`) | sharpens into focus | cinematic titles |
| `wipe_right/left/up/down` | reveals by cropping | bars, underlines, highlights, maps |
| `flip_x`, `flip_y`, `squash`, `swing` | cartoon/physical | playful explainers |
| `whip_left/right` | very fast slide with motion blur | energetic edits |
| `stamp` (`angle`) | slams down from big | "CLASSIFIED", "SOLD OUT" |
| `glitch` | jittery flicker | tech, horror |
| `typewriter` / `appear` | instant on (use with text reveal by char) | typing |
| `none` | nothing | with reveal timing only |

## Loops

`"loop": "float"` or a list `[{"preset": "float", "amp": 10, "period": 3}, "sway"]`.

| loop | params (defaults) |
|---|---|
| `float` | `amp` 14 px, `period` 3 s (up/down) |
| `bob` | `amp` 8, `period` 0.9 |
| `sway` | `amp` 4°, `period` 2.6 |
| `pulse` | `amp` 0.06 (scale), `period` 1.2 |
| `breathe` | `amp` 0.03, `period` 4 |
| `heartbeat` | `amp` 0.08, `period` 1.1 |
| `wiggle` | `amp` 6 px, `rot` 1.5°, `freq` 2 (smooth noise) |
| `shake` | `amp` 12, `freq` 18 |
| `spin` | `period` 6 s per turn, `reverse` |
| `orbit` | `radius` 20, `period` 4 |
| `drift` | `speed_x` 20 px/s, `speed_y` 0 |
| `flicker` | `amp` 0.35 (opacity), `freq` 9 |
| `ken_burns` | `from` 1.0, `to` 1.15, `pan` [x, y] px over the layer life, `ease` |
| `boil` | `amp` 1.6 px, `rot` 0.6°, `fps` 8 — hand-drawn jitter in steps (doodle / stop-motion feel) |

## Keyframes

```json
"animate": {
  "x":        [[0, "-20%"], [0.8, "50%", "out_expo"], ["end-0.6", "50%"], ["end", "120%", "in_back"]],
  "rotation": [[0, -8], [1.2, 0, "out_elastic"]],
  "opacity":  [[0, 0], [0.3, 1]],
  "progress": [[0, 0], ["w:road.end", 1, "in_out_sine"]]
}
```

- Times are seconds from the layer start, `"end-0.5"` from the layer end, or any cue (`"w:word"`, `"with:id"`, `"@12"`).
- The easing on a key shapes the motion **into** that key (default `in_out_cubic`). Before the first key the value
  holds; after the last it holds.
- Animatable: `x y scale scale_x scale_y rotation opacity blur skew_x skew_y crop_left crop_right crop_top crop_bottom
  progress offset_x offset_y value` (`value` drives counters). Aliases: `rotate`, `alpha`, `sx`, `sy`, `dx`, `dy`.
- `x`/`y` accept `"50%"` and the other length forms.

## Easing

`linear`, `in_X`, `out_X`, `in_out_X` for X = `quad cubic quart quint sine expo circ back elastic bounce`; shortcuts
`in`, `out`, `in_out`, `ease`, `smooth`, `snappy` (= out_expo), `overshoot` (= out_back); `spring`,
`spring(stiffness,damping)` like `spring(220,12)`; `bezier(x1,y1,x2,y2)` (CSS cubic-bezier); `steps(n)`; `hold`.

How it feels:
- `out_expo` / `snappy`: fast in, very soft landing. The modern motion-graphics default.
- `out_back`: slight overshoot, playful. `out_elastic`: springy wobble, cartoon.
- `in_out_sine`: gentle, for camera moves and slow drifts.
- `in_back`: anticipation before leaving, good for exits.

## Text reveals (kinetic typography)

```json
{"type": "text", "text": "Every *second* counts", "font": "display", "size": 130,
 "reveal": {"by": "word", "preset": "pop", "stagger": 0.07, "duration": 0.4}}
```

- `by`: `word`, `char` (Latin only) or `line`. Every enter preset works per unit.
- `order`: `forward`, `reverse`, `center` (from the middle out) or `random`.
- `sync: "voice"`: each word appears exactly when it is spoken (needs voice words). This gives karaoke-style kinetic type.
- Typewriter: `{"by": "char", "preset": "typewriter", "stagger": 0.04}` plus `"sfx": "sfx:typing"`.
- Combine with a layer `enter`/`exit`/`loop`: the reveal animates the units inside, the others move the whole block.

## Timing chains

Use cues instead of computing seconds (beat cues `b:`, `bar:`, `nb:` work everywhere too):

```json
{"type": "shape", "id": "bar", "kind": "rect", "w": 600, "h": 90, "enter": "wipe_right", "at": "w:introducing"},
{"type": "text", "id": "name", "text": "Asha Rao", "at": "with:bar+0.2", "enter": "rise"},
{"type": "text", "text": "Engineer", "at": "with:name+0.15", "enter": "rise"},
{"type": "image", "src": "logo.png", "at": "after:name"}
```

## Camera (per scene)

`"camera": "push_in"` or an object:

```json
"camera": {
  "preset": "push_in", "amount": 1.0, "ease": "in_out_sine",
  "animate": {"zoom": [[0, 1], [2, 1.3, "out_expo"]], "x": [[0, 0], [2, 200]], "y": [...], "rotation": [[0, 0], [3, 2]]},
  "shake": {"at": "w:boom", "until": "w:boom+0.5", "amp": 14, "freq": 14},
  "punches": [{"at": "w:now", "amount": 0.06, "duration": 0.35}]
}
```

Presets: `still`, `push_in`, `slow_push`, `pull_out`, `pan_left`, `pan_right`, `pan_up`, `pan_down`, `rise`, `drift`,
`handheld`. `amount` scales the preset. Camera `x`/`y` is the point the camera looks at, as an offset from the center
(px); `zoom` 1 = no zoom. `punches` are quick zoom bumps on beats or emphasis words. Layers with `"camera": false` don't move.

## Transitions (into a scene)

`"transition": "fade"` or `{"type": "slide_left", "duration": 0.5}`. The new scene overlaps the end of the previous one
by the duration.

`cut fade dissolve dip (dip_black) dip_white flash slide_left/right/up/down cover_left/right/up/down
reveal_left/right/up/down wipe_left/right/up/down whip_left/right/up/down circle (iris) iris_close zoom radial pixelize
glitch blur squeeze squeeze_v diagonal blinds blinds_v distance fade_grays`, or any FFmpeg xfade name as `"xfade:NAME"`.

Guidance: use one or two transition types per video. `cut` is the most professional default for fast edits. Use `fade`
or `dissolve` for calm moments, `dip` for chapter breaks, `whip_*` (0.25–0.3 s) and `flash` for energy, and `zoom` or
`circle` for reveals.

## Patterns for complex motion

- **Stagger many items**: give them the same `enter` and `at` values `0.2, 0.3, 0.4…`, or chain them with `with:prev+0.1`.
- **Move along a path**: keyframe `x` and `y` with the same times. To follow a drawn `path`, draw the path with
  `progress` keyframes and move a marker with matching x/y keys.
- **Parallax**: several layers with the same `drift` loop but different `speed_x`; farther layers move slower and are
  smaller and blurrier.
- **Hold, then leave**: `"exit": {"preset": "slide_left", "duration": 0.4}` plus `until`.
- **Swap a word**: two text layers at the same position; the first gets `"until": "w:but"` + exit `fade`, the second
  `"at": "w:but"` + enter `pop`.
- **Emphasis**: camera `punches` + layer `pop` + `sfx:hit` on the same word cue.

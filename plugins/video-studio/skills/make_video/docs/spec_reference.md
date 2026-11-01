# Video JSON reference

The file is JSON. `//` line comments and trailing commas are allowed. Paths are relative to the JSON file; the engine
also looks in `assets/`. Unknown keys are errors (with a suggestion), so a typo can't fail silently.

## Units and positions

- Lengths are px in the video's coordinate space (1080×1920 for 9:16, 1920×1080 for 16:9, whatever `width`/`height` say).
- Also accepted: `"50%"` (of the parent's width for x/w, height for y/h), `"50%+40"`, `"center"`, `"left"`, `"right"`,
  `"top"`, `"bottom"`, `"10w"`/`"10h"` (10 % of the width/height whatever the axis).
- `x`, `y` place the layer's **anchor** (default the center). `"anchor": "top_left"` | `"bottom"` | `[0.5, 1]`.
- Inside a `group`, coordinates are relative to the group's box (`w`×`h`, default the full frame).
- Sizes in templates and presets scale with the frame: `unit` = min(width, height) / 1080.

## Times (cues)

Layer `at`/`until`, keyframe times, `with:` and the like:

| cue | meaning |
|---|---|
| `"b:9"`, `"bar:3"` | the 9th beat / the first beat of bar 3 of the music (see audio_captions.md) |
| `"nb:2"` | the 2nd beat from the start of this scene/layer (`"nb:1"` = next beat) |
| `2.5` | seconds from the start of the scene (layers) or of the layer (keyframes) |
| `"end"`, `"end-0.4"` | the end of the scene (layers) or of the layer (keyframes) |
| `"w:money"` | when that spoken word starts, searched from the scene start onward |
| `"w:money.end"`, `"w:money+0.2"`, `"w:money#2"` | its end / shifted / its 2nd occurrence |
| `"w:big bang"` | consecutive words |
| `"with:title+0.3"` | when the layer with `"id": "title"` starts (+0.3 s) |
| `"after:title-0.2"` | when the layer `title` ends |
| `"@12.4"` | absolute time in the whole video |

Defaults: a layer starts at 0 and lasts to the end of its scene (or group). Use `duration` instead of `until` for a length.

## Root

| key | default | notes |
|---|---|---|
| `style` | — | style pack: theme colors/fonts, background, camera, transition, look, captions (see styles.md, `$VS styles`) |
| `theme` | from style | override theme tokens: `{"accent": "#00c2ff", "font_display": "serif"}` |
| `cue_lead` | 0 | seconds that word cues (`w:...`) fire early, like editors cut (0.06–0.1 feels tight) |
| `aspect` | `9:16` | `9:16` 1080×1920, `16:9` 1920×1080, `1:1`, `4:5`, `4:3`, `21:9` |
| `width`, `height` | from aspect | even integers |
| `fps` | 30 | 24 for a film look, 30 for social |
| `background` | `#000000` | default scene background (see scene) |
| `transition` | cut | default transition into every scene after the first |
| `camera` | still | default camera for every scene |
| `look` | — | color grade for every scene (scene `look` overrides per key) |
| `captions` | — | word captions, see audio_captions.md |
| `audio` | — | `voice`, `music`, `sfx`, `loudness` (false disables -14 LUFS normalization) |
| `fonts` | — | aliases: `{"brand": "fonts/MyFont-Bold.ttf"}` → `"font": "brand"` |
| `font_dirs` | — | extra folders to search for fonts (`<project>/fonts` is always searched) |
| `slots` | — | custom slots: `{"logo": [40, 40, 200, 120]}` (x, y, w, h) |
| `defs` | — | templates (see below) |
| `output` | — | `{"name": "final.mp4", "folder": "out", "alpha": true}`. `alpha` = transparent WebM overlay (VP9 + alpha, cuts only, no look) for OBS / editors |
| `scenes` | required | list of scenes |

`look` keys: `contrast` (1 = unchanged), `brightness` (1 = unchanged), `saturation`, `gamma`, `warmth` (-1 cool … 1
warm), `vignette` (true or 0–1), `grain` (0–1), `sharpen` (0.5–1.5), `letterbox` (true = 2.39:1, or a ratio; 16:9 only),
`mono`, `sepia`, `blur` (px), `bloom` (0–1 glow), `posterize` (levels, e.g. 6), `pixelate` (block px, e.g. 4),
`scanlines` (true or 0–1), `rgb_shift` (px chromatic offset); shortcuts `crt: true` and `vhs: true`. Stills from `frame`
and `sheet` include the look.

## Theme tokens

Any string value that is exactly `$NAME` becomes that theme value: `$bg $surface $text $muted $accent $accent2 $ink $paper
$line $shadow $font_display $font_body $font_mono $font_hand` (e.g. `"color": "$accent"`, `"font": "$font_display"`).
Text without a `color` uses `$text`. Kit components use tokens, so they restyle with the style/theme.

## Scene

| key | notes |
|---|---|
| `id` | short unique name, used by `--scene` |
| `duration` / `until` | seconds, or a cue such as `"w:last.end+0.4"` / `"@20"`. The last scene may omit both when there is a voice (it ends 0.8 s after the voice). |
| `background` | texture `{"texture": "paper", "color": "#..", "ink": "#..", "scale": 1, "motion": "drift"}` (paper kraft crumpled notebook grid dots blackboard noise halftone stripes sunburst) · color `"#101820"` · gradient `{"colors": ["#a", "#b"], "angle": 90}` or `{"colors": [...], "radial": true}` · image `"photo.jpg"` (slow Ken Burns by default) · `{"image": "x.jpg", "filter": {...}, "motion": "ken_burns" or a loop, "blur": 6, "focus": [0.5, 0.3]}` · `{"video": "x.mp4", "trim": [2, 8], "speed": 1}` |
| `camera` | preset name or object, see animation.md |
| `transition` | into this scene: `"fade"` or `{"type": "whip_left", "duration": 0.3}` |
| `look` | per-scene grade overrides |
| `captions` | `false` hides captions in this scene |
| `layout` | extra named slots for this scene (see Layouts) |
| `layers` | list, drawn in order (later = on top) unless `z` is set |

## Common layer keys (every type)

| key | notes |
|---|---|
| `type` | `image` `video` `text` `counter` `shape` `chart` `particles` `group` `custom` |
| `id` | needed for `with:`/`after:` cues and readable `inspect` output |
| `at`, `until`, `duration` | timing (see cues) |
| `x`, `y`, `anchor` | position (default: slot center, else frame center) |
| `slot` | named area; sets the default position and box. Built-ins: `full safe center top middle bottom top_half bottom_half left right top_left top_right bottom_left bottom_right title hero lower_third caption_zone` |
| `w`, `h` | box size (images/videos fit inside; text wraps to `w`) |
| `scale`, `scale_x`, `scale_y`, `rotation` (deg, clockwise), `skew_x`, `skew_y`, `opacity`, `blur` (px) | base transform |
| `offset_x`, `offset_y` | extra shift (handy for templates) |
| `crop_left/right/top/bottom` | 0–1 of the box hidden |
| `enter`, `exit` | preset name or `{"preset", "duration", "delay", "ease", "distance", "from", "angle"}` |
| `loop` | preset or list of presets running for the whole layer life |
| `animate` | keyframes: `{"x": [[0, 100], [1.2, 540, "out_back"]], "opacity": [...]}` |
| `progress` | 0–1, used by shapes (draw-on) and rings |
| `shadow` | `true` or `{"blur": 18, "dy": 10, "dx": 0, "opacity": 0.45, "color": "#000", "spread": 0}` (blur 0 = hard retro shadow) |
| `outline` | sticker border around the layer's shape: `true`, a color, or `{"width": 12, "color": "#fff"}` |
| `glow` | `true` or `{"color": "#ffd60a", "blur": 24, "opacity": 0.9}` |
| `blend` | `normal multiply screen add overlay soft_light difference darken lighten` |
| `camera` | `false` = not moved by the scene camera (HUD, captions, logos) |
| `z` | stacking order (default 0; background −1000, captions 1000) |
| `sfx` | sound at the layer's start: `"sfx:whoosh"`, `"assets/ding.mp3"` or `{"src", "volume", "offset"}` |
| `detail` | render sharper when the layer is zoomed far in (1–3) |
| `hidden` | `true` skips the layer (quick A/B) |
| `note` | free text, ignored |

## image

`src` (required; a list of files = flipbook played at `fps`, default 8) · `poses`: `[{"at": cue, "src": "pose2.png"}]` swaps
the drawing at layer-relative times (src may be a list) · `talk`: `{"open": "mouth_open.png", "fps": 10, "spans": [[t0, t1]]}`
swaps to the open-mouth drawing while the voice speaks (or only inside `spans`) — together these animate any character
drawn as a few PNGs. Frames/poses fit the same box, bottom-centered. · `fit`: `contain` (default; the box is shrunk to the image aspect) | `cover` (fills `w`×`h`, cropped
at `focus` `[fx, fy]`) | `stretch` · `radius` (px or `"50%"` for a circle) · `border` (`"#fff"` or `{"width", "color"}`)
· `key`: `true` (remove magenta `#FF00FF`) or a color or `{"color", "tolerance", "softness"}` · `trim` (crop transparent
edges; default on when keyed) · `flip` (mirror) · `filter`: `{"grayscale": 0–1, "sepia": 0–1, "brightness",
"contrast", "saturation", "sharpness", "tint": "#hex", "tint_amount", "invert"}`.
Without `w`/`h`/`slot` the image keeps its pixel size.

## video

Same as image, plus `trim: [start, end]` (seconds of the source; end may be null), `speed` (0.25–4), `loop_video`
(default true: loops when the source is shorter than the layer), `audio` (true = include its sound in the mix), `volume`.
`fit` defaults to `cover`. `key` uses FFmpeg's colorkey (green/blue/magenta screens).

## text

`text` (required): `*word*` = highlighted words, `\n` = line break. Style: `font` (alias or file), `size` (px, default 72),
`weight` (variable fonts), `color` (color or gradient `{"colors": [...], "angle": 0}`), `highlight` (color of `*words*`),
`highlight_box` (`"#ff2d55"` or `{"color", "padding": [0.16, 0.04], "radius"}`, a box behind highlighted words),
`stroke_width`, `stroke_color`, `line_height` (1.12), `letter_spacing` (px), `word_spacing` (1.0), `align` (`left`,
`center`, `right`), `uppercase`.
Layout: `max_width` (default: slot width or 88 % of the frame), `max_height`, `max_lines`, `min_size`. The font shrinks
until the text fits (it never overflows).
`plate`: a box behind the whole text, `"#000000aa"` or `{"color", "padding": [0.45, 0.25], "radius": 0.25, "opacity",
"border": {"width": 8, "color"}}` (padding and radius are multiples of the font size).
`reveal`: animates words, characters or lines one after another, `{"by": "word"|"char"|"line", "preset": "rise",
"stagger": 0.06, "duration": 0.45, "delay": 0, "order": "forward"|"reverse"|"center"|"random", "ease", "sync": "voice"}`.
`sync: "voice"` makes each word appear when it is spoken. Use `char` only for Latin text; for Hindi use `word`.

Fonts: aliases `display` (Anton, condensed impact), `sans` (Liberation Sans Bold), `serif` (Playfair Display), `editorial`
(Merriweather), `book` (Lora), `body_serif` (Noto Serif), `mono` (Space Mono), `hand` (Kalam), `rounded` (Baloo 2),
`hindi`, `hindi_display`, `hindi_condensed`, `hindi_serif`, `hindi_title`, `devanagari`. Any `.ttf/.otf` in
`<project>/fonts/` works by file name. Devanagari text automatically falls back to a Devanagari font.

## counter

A text layer that counts: `from`, `to`, `format` (Python format: `"{:,.0f}"`, `"{:.1f}"`, `"{:.0%}"`), `prefix`,
`suffix`, `count: {"duration": 1.6, "delay": 0, "ease": "out_expo"}`. Or drive it with keyframes:
`"animate": {"value": [[0, 0], [2, 50], [3, 42]]}`. All text style keys apply.

## shape

`kind`: `rect` (`w`, `h`, `radius`) · `ellipse` · `circle` (`size`) · `ring` (`size`, `stroke_width`, `start_angle`
−90, `sweep` 360) · `star` (`count`, `inner` 0.45) · `line` / `arrow` / `path` / `polygon` with `points` `[[x, y], ...]`
in parent coordinates (or `from`/`to`), `curve: true` (smooth through the points), `closed`.
Paint: `fill` (color or gradient; `null` = none), `stroke`, `stroke_width`, `dash: [on, off]`, `cap` (`round`), `head`
(arrowhead size), `double` (two heads). Hand-drawn: `rough` (wobble px, 2–6) and `boil` (redraws per second, default 8).
`progress` 0–1 draws the outline on (animate it: `"animate": {"progress": [[0, 0], [1, 1]]}`). Closed shapes fade
their fill in as they draw.

## chart

`kind`: `column` | `bar` (horizontal) | `line`. `values` (numbers), `labels`, `colors` (list, cycles), `max`, `gap`
(0.3), `grow: {"duration": 1.2, "stagger": 0.12, "delay": 0, "ease": "out_cubic"}`, `show_values`, `format`, `font`,
`label_color`, `value_color`, `label_size`, `value_size`, `line_width`, `dots`, `axis`, `radius`. Size with `w`/`h`/`slot`.

## particles

`kind`: `dust` `dots` `snow` `bokeh` `confetti` `sparks` `embers` `rain` `stars` `bubbles`. `count` (≤ 600; keep ≤ 150
on phones), `seed`, `colors`, `size: [min, max]`, `speed: [min, max]`, `direction` (deg, 90 = down, 270 = up), `spread`,
`opacity_range`, `spin`, `wobble`, `fade_edges`. Fills its box (`w`/`h`/`slot`, default the full frame).

## stickman

A built-in stick figure (no images needed). `size` (height px; default 90 % of its slot or 40 % of the frame), `color`,
`line_width`, `head_fill`, `facing` (`right`/`left`), `accessory` (`glasses` `hat` `cap` `tie` `bow`), `rough` + `boil`
(hand-drawn wobble), `talk` (`true` = mouth moves while the voice speaks, or `[[t0, t1], ...]`).
`pose`: `stand wave point point_up think cheer shrug sit facepalm cross_arms hands_on_hips sad present surprised angry
jump run walk kneel look_up dab`, or custom joint angles `{"rs": 90, "re": 0, ...}` (joints `lean head ls le rs re lh lk rh rk`).
`poses`: `[{"at": 1.2, "pose": "point", "dur": 0.3}]` smooth changes (times relative to the layer).
`action` or `actions` (`[{"action": "walk", "at": 0, "until": 2, "speed": 1}]`): `walk run wave nod gesture jump dance
idle type`. Walking happens in place: move the figure with `animate.x` (or a `drift` loop).
`expression` / `expressions` (`[{"at": 2, "expression": "happy"}]`): `neutral happy sad surprised angry thinking wink worried laugh none`.
Anchored at the feet: `x`, `y` = where it stands. In a slot it stands on the slot's bottom edge.

## texture

`kind` (paper kraft crumpled notebook grid dots blackboard noise halftone stripes sunburst), `color`, `ink`, `scale_pattern`,
`seed`, sized by `w`/`h`/`slot` (default full frame). Usually set as a scene `background` instead.

## group

`layers` (children, timed relative to the group's start) · `w`, `h` (default the full frame) · `clip` (true = hide what
spills outside the box; default lets shadows/overshoot spill) · `mask`: one layer spec
whose alpha cuts out the group (video inside text, image inside a shape) · `mask_invert`. A group animates, fades and
blurs as one unit. Use groups for cards, lower thirds, split panels and parallax sets.

## custom

`script` (a `.py` file with `def render(ctx)`) · `params` · `w`, `h` (default full frame). See custom_layers.md.

## Layouts

`"layout": "NAME"` on a scene adds named slots (all inside the safe area, never overlapping), usable as `"slot": "title"`:

| layout | slots | for |
|---|---|---|
| `hero` / `hero_r` | tag, title, label, lower, visual (+cast) | text column + main visual |
| `duo` | tag, title, left, right, label_left, label_right | compare two things |
| `trio` | title, a, b, c, la, lb, lc | three items / steps |
| `board` | tag, a, b, c, d, e | evidence/collage board |
| `focus` | tag, center, l1, l2, r1, r2 | one object with callouts |
| `quote` | tag, title, label | a big statement |
| `split` | tag, title, visual, list | picture + bullet list |
| `timeline` | tag, title, band, lower | dates on a line |
| `presenter` / `presenter_l` | tag, title, visual, cast | host character + visual |
| `stage` | tag, title, cast | full character scene |
| `clean` | tag, lower | a strong picture alone |
| `stack` | title, a, b, c | stacked rows (9:16) / columns (16:9) |

In 9:16 the side-by-side layouts stack vertically (left above right).

## Kit components

About 70 ready templates (`kit.NAME`): kickers, headlines, marker highlights, quote/chapter cards, redaction, lists and
checklists, photo frames (polaroid, evidence, print, card, sticker, paper cut-out, taped), stamps (rubber, seal, tape,
scrawl, tab), bursts, doodled circles/underlines/arrows, ticks/crosses, highlight boxes, spotlight, callouts, lower thirds,
breaking news + ticker, LIVE badge, camcorder REC overlay, subscribe button, location tag, post card, comment,
notification, chat bubbles, stat card, progress ring and bar, versus, countdown number, map pin, timeline, clock,
browser/phone/app frames, speech/thought bubbles, sticky note, idea bulb, heart, pixel dialog/title, PRESS START, score,
health bar. Full list with parameters: kit.md, or `$VS kit [word]`.

## Templates

```jsonc
"defs": {
  "lower_third": {
    "params": {"name": "Name", "role": "Role", "color": "#ff375f"},
    "layer": { "type": "group", "slot": "lower_third", "layers": [ /* use "{{name}}" etc. */ ] }
  },
  "badge_pair": {"params": {"a": "", "b": ""}, "layers": [ {...}, {...} ]}   // several layers at once
}
...
{"use": "lower_third", "with": {"name": "Asha Rao", "role": "Engineer"}, "at": "w:asha", "until": "end-0.5"}
```

`"{{p}}"` on its own is replaced by the value of any type; inside a longer string it is inserted as text.
`"{{= 1 - value / 100 }}"` computes with number parameters (`+ - * / % **`, `min max abs round`), e.g. a fill level or a
point between two others: `["{{= (x1 + x2) / 2 }}", "{{= max(y1, y2) + 80 }}"]`. Keys next to
`use` override the template's top-level keys. Scenes can be templates too: `{"use": "chapter_card", "with": {...}}`
in `scenes`, with the def containing `"scene": {...}`.

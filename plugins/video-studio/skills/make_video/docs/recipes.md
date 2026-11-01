# Recipes

Each recipe is a working fragment. Copy it, then change text, assets and timing. File names like `photo.jpg` stand for
the user's assets in `assets/`. All of these are tested.

## 1. Kinetic typography hook (9:16)

```json
{"id": "hook", "until": "w:money.end+0.25", "background": "#0b0b0f", "camera": {"preset": "slow_push", "punches": [{"at": "w:money"}]},
 "layers": [
  {"type": "text", "text": "STOP", "font": "display", "size": 260, "color": "#ff375f", "y": "34%",
   "enter": {"preset": "zoom_out", "duration": 0.35}, "exit": "fade", "until": "w:wasting", "sfx": "sfx:hit"},
  {"type": "text", "text": "wasting your *money*", "font": "display", "size": 140, "uppercase": true, "slot": "middle",
   "at": "w:wasting", "reveal": {"by": "word", "sync": "voice", "preset": "pop", "duration": 0.3}, "highlight": "#ffd60a"},
  {"type": "shape", "kind": "rect", "w": 520, "h": 14, "radius": 7, "fill": "#ffd60a", "y": "60%", "at": "w:money", "enter": "wipe_right"}
 ]}
```

## 2. Documentary photo with a slow move, a stamp and a typed caption

```json
{"id": "archive", "duration": 6, "background": {"image": "photo.jpg", "filter": {"grayscale": 1, "contrast": 1.2},
  "motion": {"preset": "ken_burns", "from": 1.05, "to": 1.2, "pan": [-40, 20]}},
 "look": {"grain": 0.35, "vignette": 0.6, "warmth": 0.25},
 "layers": [
  {"type": "shape", "kind": "rect", "w": 640, "h": 96, "x": 70, "y": 170, "anchor": "top_left", "fill": "#000000b0", "enter": "wipe_right", "at": 0.4},
  {"type": "text", "text": "MUMBAI · 14 SEPT 1946", "font": "mono", "size": 44, "align": "left", "anchor": "left", "x": 100, "y": 218,
   "at": 0.6, "reveal": {"by": "char", "preset": "typewriter", "stagger": 0.04}, "sfx": "sfx:typing"},
  {"type": "text", "text": "CLASSIFIED", "font": "display", "size": 150, "color": "#d9302c", "rotation": -10, "opacity": 0.9,
   "y": "62%", "at": 2.2, "enter": "stamp", "sfx": "sfx:impact", "blend": "multiply"}
 ]}
```

## 3. Cut-out subject over a background (Flow cutouts on magenta)

```json
{"type": "image", "src": "hero_magenta.png", "key": true, "h": "70%", "x": "70%", "y": "100%", "anchor": "bottom",
 "enter": {"preset": "slide_left", "distance": 300}, "loop": "breathe", "shadow": {"blur": 40, "dy": 24, "opacity": 0.5}}
```

Pre-cut once with `$VS key hero_magenta.png` (gives `hero_magenta_cut.png`). That is faster than `"key": true` on
every render and lets you look at the result first.

## 4. Lower third (template)

```json
"defs": {
  "lower_third": {
    "params": {"name": "Name", "role": "Role", "color": "#0a84ff"},
    "layer": {"type": "group", "slot": "lower_third", "exit": {"preset": "fade", "duration": 0.3}, "layers": [
      {"type": "shape", "id": "bar", "kind": "rect", "w": 14, "h": 150, "x": 0, "y": "50%", "anchor": "left", "fill": "{{color}}", "enter": "wipe_down"},
      {"type": "shape", "id": "panel", "kind": "rect", "w": 760, "h": 150, "x": 22, "y": "50%", "anchor": "left", "fill": "#000000cc",
       "at": "with:bar+0.15", "enter": "wipe_right"},
      {"type": "text", "text": "{{name}}", "font": "sans", "size": 58, "align": "left", "anchor": "left", "x": 56, "y": "50%-28",
       "at": "with:panel+0.2", "enter": "rise"},
      {"type": "text", "text": "{{role}}", "font": "sans", "size": 36, "color": "#bbbbbb", "align": "left", "anchor": "left",
       "x": 56, "y": "50%+32", "at": "with:panel+0.3", "enter": "rise"}
    ]}
  }
}
```

Use: `{"use": "lower_third", "with": {"name": "Asha Rao", "role": "Climate scientist"}, "at": "w:asha", "until": "end-0.3"}`.

## 5. Map route drawn on, with a moving marker

```json
{"type": "image", "src": "map.jpg", "slot": "full", "fit": "cover", "filter": {"saturation": 0.6}},
{"type": "shape", "id": "route", "kind": "path", "points": [[180, 1400], [360, 1150], [620, 1080], [820, 760], [900, 420]],
 "curve": true, "stroke": "#ff375f", "stroke_width": 12, "dash": [28, 14], "at": 0.5,
 "animate": {"progress": [[0, 0], [3, 1, "in_out_sine"]]}, "sfx": "sfx:swish"},
{"type": "shape", "kind": "circle", "size": 44, "fill": "#ff375f", "stroke": "#ffffff", "stroke_width": 6, "at": 0.5,
 "animate": {"x": [[0, 180], [0.75, 360], [1.5, 620], [2.25, 820], [3, 900]],
             "y": [[0, 1400], [0.75, 1150], [1.5, 1080], [2.25, 760], [3, 420]]},
 "loop": {"preset": "pulse", "amp": 0.15}},
{"type": "text", "text": "Day 3: Kathmandu", "font": "display", "size": 70, "x": 720, "y": 340, "at": 3.4, "enter": "pop", "sfx": "sfx:pop",
 "plate": {"color": "#000000aa"}}
```

The marker keys share times with the path's progress. The two stay roughly together because the points are evenly
spaced. For an exact match, use more points with equal spacing.

## 6. Data story: counter + chart + ring

```json
{"type": "counter", "from": 0, "to": 4.2, "format": "{:.1f}", "suffix": " Cr", "prefix": "₹", "font": "display", "size": 160,
 "slot": "top", "count": {"duration": 1.8, "ease": "out_expo"}, "enter": "pop"},
{"type": "chart", "kind": "column", "values": [1.1, 1.9, 2.8, 4.2], "labels": ["2022", "2023", "2024", "2025"],
 "slot": "hero", "at": 0.6, "grow": {"duration": 0.8, "stagger": 0.18, "ease": "out_back"}, "format": "{:.1f}"},
{"type": "shape", "kind": "ring", "size": 220, "stroke": "#30d158", "stroke_width": 24, "slot": "bottom", "at": 1.5,
 "animate": {"progress": [[0, 0], [1.2, 0.73, "out_cubic"]]}},
{"type": "counter", "from": 0, "to": 73, "suffix": "%", "font": "display", "size": 72, "slot": "bottom", "at": 1.5, "count": {"duration": 1.2}}
```

## 7. Split screen / before–after

```json
{"type": "video", "src": "before.mp4", "slot": "top_half", "fit": "cover", "w": "100%", "h": "50%", "enter": "fly_right"},
{"type": "video", "src": "after.mp4", "slot": "bottom_half", "fit": "cover", "w": "100%", "h": "50%", "enter": "fly_left"},
{"type": "shape", "kind": "rect", "w": "100%", "h": 10, "y": "50%", "fill": "#ffffff", "enter": "wipe_right", "at": 0.4},
{"type": "text", "text": "BEFORE", "font": "display", "size": 64, "x": 90, "y": "11%", "anchor": "left", "align": "left", "plate": "#000000aa"},
{"type": "text", "text": "AFTER", "font": "display", "size": 64, "x": 90, "y": "58%", "anchor": "left", "align": "left", "plate": "#ff375fdd"}
```

For a horizontal slider (wipe between two clips), animate the top clip's `crop_right` from 1 to 0.

## 8. Video inside text (mask)

```json
{"type": "group", "slot": "full", "enter": {"preset": "zoom_out", "duration": 0.8},
 "mask": {"type": "text", "text": "OCEAN", "font": "display", "size": 420},
 "layers": [{"type": "video", "src": "waves.mp4", "slot": "full", "fit": "cover"}]}
```

Any layer can be the mask (a circle shape for a round video, an image with alpha). `"mask_invert": true` cuts a hole instead.

## 9. Parallax depth from cut-outs

```json
{"type": "image", "src": "sky.jpg", "slot": "full", "fit": "cover", "loop": {"preset": "drift", "speed_x": -8}, "scale": 1.1},
{"type": "image", "src": "mountains_cut.png", "w": "130%", "y": "70%", "loop": {"preset": "drift", "speed_x": -20}, "blur": 1.5},
{"type": "image", "src": "trees_cut.png", "w": "140%", "y": "85%", "loop": {"preset": "drift", "speed_x": -45}},
{"type": "image", "src": "hero_cut.png", "h": "55%", "y": "100%", "anchor": "bottom", "loop": "breathe", "shadow": true}
```

Pair it with `"camera": "push_in"`. Nearer layers move faster; farther layers are blurrier and less saturated.

## 10. Product promo card with a light sweep

```json
{"type": "group", "w": 820, "h": 1000, "y": "45%", "enter": {"preset": "pop", "duration": 0.6}, "loop": {"preset": "float", "amp": 10},
 "shadow": {"blur": 50, "dy": 30, "opacity": 0.5},
 "mask": {"type": "shape", "kind": "rect", "w": 820, "h": 1000, "radius": 48},
 "layers": [
  {"type": "shape", "kind": "rect", "w": 820, "h": 1000, "fill": {"colors": ["#1c1c28", "#2b2b45"], "angle": 90}},
  {"type": "image", "src": "product_cut.png", "h": 620, "y": "42%", "enter": "zoom_in", "at": 0.3},
  {"type": "text", "text": "Aero Max", "font": "display", "size": 96, "y": "82%", "at": 0.5, "enter": "rise"},
  {"type": "shape", "kind": "rect", "w": 160, "h": 1400, "rotation": 20, "fill": {"colors": ["#ffffff00", "#ffffff66", "#ffffff00"], "angle": 0},
   "blend": "screen", "at": 1.0, "duration": 0.9, "animate": {"x": [[0, -200], [0.9, 1020, "in_out_sine"]]}}
 ]}
```

## 11. Countdown / list item transitions

```json
"defs": {"rank": {"params": {"n": "5", "title": "Title", "img": "x.jpg"}, "scene": {
  "duration": 3.5, "transition": {"type": "whip_left", "duration": 0.3}, "background": {"image": "{{img}}", "filter": {"brightness": 0.6}},
  "layers": [
    {"type": "text", "text": "#{{n}}", "font": "display", "size": 300, "color": "#ffd60a", "slot": "top", "enter": "stamp", "sfx": "sfx:impact"},
    {"type": "text", "text": "{{title}}", "font": "display", "size": 110, "slot": "middle", "uppercase": true,
     "reveal": {"by": "word", "preset": "slide_up", "stagger": 0.08}, "at": 0.4}]}}}
...
"scenes": [{"use": "rank", "with": {"n": "3", "title": "Blue whale", "img": "whale.jpg"}, "id": "r3"}, ...]
```

## 12. Logo reveal outro

```json
{"id": "outro", "duration": 3, "background": {"colors": ["#111", "#000"], "radial": true},
 "layers": [
  {"type": "particles", "kind": "sparks", "count": 60, "at": 0.6, "duration": 0.8},
  {"type": "shape", "kind": "ring", "size": 360, "stroke": "#ffffff", "stroke_width": 6, "animate": {"progress": [[0, 0], [0.7, 1, "in_out_cubic"]]}},
  {"type": "image", "src": "logo.png", "w": 240, "at": 0.6, "enter": {"preset": "zoom_in", "duration": 0.5}, "glow": {"blur": 30, "opacity": 0.6}, "sfx": "sfx:bass_drop"},
  {"type": "text", "text": "Follow for more", "font": "sans", "size": 46, "y": "68%", "at": 1.2, "reveal": {"by": "char", "preset": "fade", "stagger": 0.02}}
 ]}
```

## 13. Talking-head B-roll inserts

The main clip runs as the scene background; cutaways appear on keywords:

```json
{"id": "talk", "until": "w:done.end+0.3", "background": {"video": "talk.mp4", "trim": [3, null]},
 "layers": [
  {"type": "video", "src": "broll_city.mp4", "slot": "full", "fit": "cover", "at": "w:city", "until": "w:city+2.2", "enter": "fade", "exit": "fade"},
  {"type": "image", "src": "chart.png", "slot": "top", "at": "w:growth", "duration": 2.5, "enter": "pop", "exit": "fade", "radius": 24, "shadow": true}
 ]}
```

To use the talking clip's own sound as the voice, extract it with the same trim (`ffmpeg -ss 3 -i talk.mp4 -vn
assets/voice.wav`), run `$VS align assets/voice.wav`, and set `"voice": {"src": "voice.wav", "words": "voice.words.json"}`.

## 14. Collage wall (documentary)

```json
{"type": "group", "slot": "full", "layers": [
  {"type": "image", "src": "a.jpg", "w": 420, "x": "28%", "y": "30%", "rotation": -6, "border": {"width": 14, "color": "#f4ecd8"}, "shadow": true, "enter": "drop", "sfx": "sfx:shutter"},
  {"type": "image", "src": "b.jpg", "w": 420, "x": "70%", "y": "38%", "rotation": 5, "border": {"width": 14, "color": "#f4ecd8"}, "shadow": true, "enter": "drop", "at": 0.5, "sfx": "sfx:shutter"},
  {"type": "image", "src": "c.jpg", "w": 460, "x": "45%", "y": "66%", "rotation": -2, "border": {"width": 14, "color": "#f4ecd8"}, "shadow": true, "enter": "drop", "at": 1.0, "sfx": "sfx:shutter"},
  {"type": "shape", "kind": "line", "points": [[300, 560], [760, 720], [490, 1270]], "stroke": "#c0392b", "stroke_width": 5, "at": 1.6,
   "animate": {"progress": [[0, 0], [0.8, 1]]}}
 ], "loop": {"preset": "wiggle", "amp": 2}}
```

## 15. Glitch tech title

```json
{"type": "text", "text": "SYSTEM BREACH", "font": "mono", "size": 96, "color": "#00ff9c", "enter": {"preset": "glitch", "duration": 0.6},
 "loop": {"preset": "flicker", "amp": 0.25}, "glow": {"color": "#00ff9c", "blur": 20, "opacity": 0.7}, "sfx": "sfx:glitch"},
{"type": "text", "text": "SYSTEM BREACH", "font": "mono", "size": 96, "color": "#ff2d55", "opacity": 0.6, "blend": "screen",
 "offset_x": 6, "loop": {"preset": "shake", "amp": 4, "freq": 25}}
```
The two copies overlap on purpose (`inspect` reports it; ignore that warning). Set the scene transition to `"glitch"` and the look to `{"grain": 0.4, "contrast": 1.2}`.

# Custom layers (Python escape hatch)

Use this only when presets, keyframes, shapes, charts, particles and groups can't express the effect: a procedural
background, an animated graph from data, a map drawn from coordinates, a clock face, a waveform, a physics toss.

```json
{"type": "custom", "script": "fx/rays.py", "params": {"count": 24, "color": "#ffd60a"}, "w": 1080, "h": 1080,
 "slot": "center", "blend": "add", "enter": "fade"}
```

`fx/rays.py` (relative to the JSON):

```python
import math

def render(ctx):
    img = ctx.Image.new("RGBA", (ctx.w, ctx.h), (0, 0, 0, 0))
    d = ctx.ImageDraw.Draw(img)
    cx, cy = ctx.w / 2, ctx.h / 2
    r, g, b, a = ctx.color(ctx.params.get("color", "#ffffff"))
    n = ctx.params.get("count", 18)
    for i in range(n):
        ang = math.radians(i * 360 / n + ctx.t * 20)           # rotate 20°/s
        R = max(ctx.w, ctx.h)
        d.polygon([(cx, cy),
                   (cx + R * math.cos(ang - 0.05), cy + R * math.sin(ang - 0.05)),
                   (cx + R * math.cos(ang + 0.05), cy + R * math.sin(ang + 0.05))],
                  fill=(r, g, b, int(60 * ctx.ease("out_cubic", ctx.progress * 3))))
    return img
```

## ctx

| field | meaning |
|---|---|
| `t` | seconds since the layer started |
| `duration`, `progress` | layer length; `t / duration` (0–1) |
| `w`, `h` | **pixel** size to return. Already scaled for preview, so draw relative to w/h, never hard-coded pixels |
| `d` | pixels per layout px (use it to scale line widths: `width=int(6 * ctx.d)`) |
| `fps`, `frame` | output fps and the frame index within the layer |
| `params` | your `params` object |
| `value` | the keyframed `value` (`"animate": {"value": [[0, 0], [2, 1]]}`), to drive your effect from JSON |
| `global_t` | time in the whole video (sync with `words`) |
| `words` | voice word timings `[{word, start, end}]` (global seconds) |
| `fast` | true during preview: draw cheaper if you can |
| `project_dir` | to load your own data files |
| `ease(name, t)`, `color("#hex")` | helpers |
| `Image`, `ImageDraw`, `np` | Pillow and numpy |

Rules:
- Return an RGBA `Image` of size `(ctx.w, ctx.h)` (or `None` to draw nothing this frame).
- The function must be **pure**: the same `t` gives the same image (frames render in parallel and out of order). For
  randomness use `random.Random(seed)` created inside `render`, or noise based on `t`.
- Keep it fast: no file loading per frame (cache in a module-level dict), and avoid per-pixel Python loops (use numpy).
- The layer is then a normal layer: position, `enter`, `loop`, `blend`, `shadow`, masks and groups all apply.
- Errors are reported with the file name, exception and time. Test one frame with `$VS frame video.json --scene ID --at T`.

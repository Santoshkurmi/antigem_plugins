"""Animation: keyframes, enter/exit presets and loops. All of them produce 'mods' that are combined with a layer's base
transform: dx/dy (px), scale/sx/sy (multipliers), rot/skx/sky (degrees), opacity (multiplier), blur (px), crop_* (0-1)."""
import math

from . import easing
from .util import SpecError, suggest

ANIMATABLE = {"x", "y", "scale", "scale_x", "scale_y", "rotation", "opacity", "blur", "skew_x", "skew_y",
              "crop_left", "crop_right", "crop_top", "crop_bottom", "progress", "offset_x", "offset_y", "value"}
ALIASES = {"rotate": "rotation", "alpha": "opacity", "sx": "scale_x", "sy": "scale_y", "dx": "offset_x", "dy": "offset_y"}


def empty_mods():
    return {"dx": 0.0, "dy": 0.0, "scale": 1.0, "sx": 1.0, "sy": 1.0, "rot": 0.0, "skx": 0.0, "sky": 0.0,
            "opacity": 1.0, "blur": 0.0, "crop_l": 0.0, "crop_r": 0.0, "crop_t": 0.0, "crop_b": 0.0}


def merge(a, b):
    a["dx"] += b.get("dx", 0.0)
    a["dy"] += b.get("dy", 0.0)
    a["rot"] += b.get("rot", 0.0)
    a["skx"] += b.get("skx", 0.0)
    a["sky"] += b.get("sky", 0.0)
    a["blur"] += b.get("blur", 0.0)
    for k in ("scale", "sx", "sy", "opacity"):
        a[k] *= b.get(k, 1.0)
    for k in ("crop_l", "crop_r", "crop_t", "crop_b"):
        a[k] = max(a[k], b.get(k, 0.0))
    return a


def _noise(seed, x):
    """Smooth 1D value noise in [-1, 1]."""
    i = math.floor(x)
    f = x - i

    def h(n):
        n = (n * 374761393 + seed * 668265263) & 0xFFFFFFFF
        n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
        return ((n ^ (n >> 16)) & 0xFFFF) / 32767.5 - 1.0
    u = f * f * (3 - 2 * f)
    return h(i) * (1 - u) + h(i + 1) * u


# --- enter / exit presets: f(p, raw, o, ctx) where p = eased progress (0 hidden → 1 at rest) ---------------------------

def _dist(o, ctx, default):
    return float(o.get("distance", default * ctx["unit"]))


def _fade_in(raw, k=3.0):
    return min(1.0, max(0.0, raw * k))


PRESETS = {
    "none": (None, lambda p, r, o, c: {}),
    "fade": ("out_quad", lambda p, r, o, c: {"opacity": p}),
    "pop": ("out_back", lambda p, r, o, c: {"scale": o.get("from", 0.4) + (1 - o.get("from", 0.4)) * p, "opacity": _fade_in(r)}),
    "pop_rotate": ("out_back", lambda p, r, o, c: {"scale": 0.4 + 0.6 * p, "rot": (1 - p) * o.get("angle", -14), "opacity": _fade_in(r)}),
    "bounce_in": ("out_elastic", lambda p, r, o, c: {"scale": p, "opacity": _fade_in(r, 5)}),
    "zoom_in": ("out_expo", lambda p, r, o, c: {"scale": o.get("from", 0.2) + (1 - o.get("from", 0.2)) * p, "opacity": _fade_in(r, 2)}),
    "zoom_out": ("out_expo", lambda p, r, o, c: {"scale": o.get("from", 1.8) + (1 - o.get("from", 1.8)) * p, "opacity": _fade_in(r, 2)}),
    "slide_up": ("out_cubic", lambda p, r, o, c: {"dy": (1 - p) * _dist(o, c, 160), "opacity": _fade_in(r, 2.5)}),
    "slide_down": ("out_cubic", lambda p, r, o, c: {"dy": -(1 - p) * _dist(o, c, 160), "opacity": _fade_in(r, 2.5)}),
    "slide_left": ("out_cubic", lambda p, r, o, c: {"dx": (1 - p) * _dist(o, c, 220), "opacity": _fade_in(r, 2.5)}),
    "slide_right": ("out_cubic", lambda p, r, o, c: {"dx": -(1 - p) * _dist(o, c, 220), "opacity": _fade_in(r, 2.5)}),
    "fly_up": ("out_expo", lambda p, r, o, c: {"dy": (1 - p) * c["H"] * 0.7}),
    "fly_down": ("out_expo", lambda p, r, o, c: {"dy": -(1 - p) * c["H"] * 0.7}),
    "fly_left": ("out_expo", lambda p, r, o, c: {"dx": (1 - p) * c["W"]}),
    "fly_right": ("out_expo", lambda p, r, o, c: {"dx": -(1 - p) * c["W"]}),
    "rise": ("out_cubic", lambda p, r, o, c: {"dy": (1 - p) * _dist(o, c, 50), "opacity": p}),
    "drop": ("out_bounce", lambda p, r, o, c: {"dy": -(1 - p) * _dist(o, c, 500)}),
    "spin": ("out_back", lambda p, r, o, c: {"rot": (1 - p) * o.get("angle", -180), "scale": max(0.0, p), "opacity": _fade_in(r)}),
    "blur_in": ("out_cubic", lambda p, r, o, c: {"blur": (1 - p) * o.get("amount", 28), "opacity": p, "scale": 1 + (1 - p) * 0.08}),
    "wipe_right": ("in_out_cubic", lambda p, r, o, c: {"crop_r": 1 - p}),
    "wipe_left": ("in_out_cubic", lambda p, r, o, c: {"crop_l": 1 - p}),
    "wipe_up": ("in_out_cubic", lambda p, r, o, c: {"crop_t": 1 - p}),
    "wipe_down": ("in_out_cubic", lambda p, r, o, c: {"crop_b": 1 - p}),
    "flip_x": ("out_back", lambda p, r, o, c: {"sx": max(0.0, p), "opacity": _fade_in(r, 4)}),
    "flip_y": ("out_back", lambda p, r, o, c: {"sy": max(0.0, p), "opacity": _fade_in(r, 4)}),
    "squash": ("out_elastic", lambda p, r, o, c: {"sx": 1 + (1 - p) * 0.5, "sy": max(0.0, p), "opacity": _fade_in(r, 4)}),
    "swing": ("out_back", lambda p, r, o, c: {"rot": (1 - p) * o.get("angle", -30), "opacity": _fade_in(r, 3)}),
    "whip_left": ("out_expo", lambda p, r, o, c: {"dx": (1 - p) * c["W"] * 0.8, "blur": (1 - p) * 30, "skx": (1 - p) * -20}),
    "whip_right": ("out_expo", lambda p, r, o, c: {"dx": -(1 - p) * c["W"] * 0.8, "blur": (1 - p) * 30, "skx": (1 - p) * 20}),
    "stamp": ("out_quart", lambda p, r, o, c: {"scale": 2.4 - 1.4 * p, "opacity": _fade_in(r, 2), "rot": (1 - p) * o.get("angle", 8)}),
    "glitch": ("linear", lambda p, r, o, c: {} if r >= 1 else {
        "dx": _noise(7, r * 40) * 40 * (1 - r) * c["unit"], "skx": _noise(3, r * 30) * 12 * (1 - r),
        "opacity": 1.0 if _noise(11, r * 25) > -0.5 + r else 0.0}),
    "typewriter": ("hold", lambda p, r, o, c: {"opacity": 1.0 if r > 0 else 0.0}),
}
PRESETS["appear"] = PRESETS["typewriter"]
PRESETS["scale_in"] = PRESETS["zoom_in"]


class Motion:
    """One enter or exit preset (resolved durations)."""

    def __init__(self, spec, where, default_duration=0.5):
        if isinstance(spec, str):
            spec = {"preset": spec}
        if not isinstance(spec, dict) or "preset" not in spec:
            raise SpecError(where, "expected a preset name or {\"preset\": ..., \"duration\": ...}")
        name = str(spec["preset"]).lower()
        if name not in PRESETS:
            raise SpecError(where, f"unknown preset '{name}'", suggest(name, PRESETS))
        self.name = name
        self.ease_default, self.fn = PRESETS[name]
        self.opts = spec
        self.duration = max(0.001, float(spec.get("duration", default_duration)))
        self.delay = float(spec.get("delay", 0.0))
        self.ease = spec.get("ease")
        if self.ease:
            easing.get(self.ease, where + ".ease")

    def mods(self, raw, ctx, exiting=False):
        raw = 0.0 if raw < 0 else 1.0 if raw > 1 else raw
        if exiting:
            ease = self.ease or ("in_cubic" if self.ease_default not in ("linear", "hold") else self.ease_default)
            p = 1 - easing.apply(ease, raw)
            r = 1 - raw
        else:
            p = easing.apply(self.ease or self.ease_default, raw)
            r = raw
        return self.fn(p, r, self.opts, ctx)


# --- loops: f(t, D, o, ctx, seed) -------------------------------------------------------------------------------------

def _period(o, d):
    return max(0.05, float(o.get("period", d)))


LOOPS = {
    "float": lambda t, D, o, c, s: {"dy": float(o.get("amp", 14)) * c["unit"] * math.sin(2 * math.pi * t / _period(o, 3.0))},
    "bob": lambda t, D, o, c, s: {"dy": float(o.get("amp", 8)) * c["unit"] * math.sin(2 * math.pi * t / _period(o, 0.9))},
    "sway": lambda t, D, o, c, s: {"rot": float(o.get("amp", 4)) * math.sin(2 * math.pi * t / _period(o, 2.6))},
    "pulse": lambda t, D, o, c, s: {"scale": 1 + float(o.get("amp", 0.06)) * (0.5 - 0.5 * math.cos(2 * math.pi * t / _period(o, 1.2)))},
    "breathe": lambda t, D, o, c, s: {"scale": 1 + float(o.get("amp", 0.03)) * math.sin(2 * math.pi * t / _period(o, 4.0))},
    "heartbeat": lambda t, D, o, c, s: {"scale": 1 + float(o.get("amp", 0.08)) * max(
        math.exp(-((t % _period(o, 1.1)) - 0.08) ** 2 / 0.003), 0.7 * math.exp(-((t % _period(o, 1.1)) - 0.3) ** 2 / 0.003))},
    "wiggle": lambda t, D, o, c, s: {"dx": float(o.get("amp", 6)) * c["unit"] * _noise(s, t * float(o.get("freq", 2))),
                                    "dy": float(o.get("amp", 6)) * c["unit"] * _noise(s + 1, t * float(o.get("freq", 2))),
                                    "rot": float(o.get("rot", 1.5)) * _noise(s + 2, t * float(o.get("freq", 2)))},
    "shake": lambda t, D, o, c, s: {"dx": float(o.get("amp", 12)) * c["unit"] * _noise(s, t * float(o.get("freq", 18))),
                                   "dy": float(o.get("amp", 12)) * c["unit"] * _noise(s + 5, t * float(o.get("freq", 18)))},
    "spin": lambda t, D, o, c, s: {"rot": 360.0 * t / _period(o, 6.0) * (-1 if o.get("reverse") else 1)},
    "orbit": lambda t, D, o, c, s: {"dx": float(o.get("radius", 20)) * c["unit"] * math.cos(2 * math.pi * t / _period(o, 4.0)),
                                   "dy": float(o.get("radius", 20)) * c["unit"] * math.sin(2 * math.pi * t / _period(o, 4.0))},
    "drift": lambda t, D, o, c, s: {"dx": float(o.get("speed_x", 20)) * c["unit"] * t, "dy": float(o.get("speed_y", 0)) * c["unit"] * t},
    "flicker": lambda t, D, o, c, s: {"opacity": 1 - float(o.get("amp", 0.35)) * max(0.0, _noise(s, t * float(o.get("freq", 9))))},
    "boil": lambda t, D, o, c, s: (lambda f: {
        "dx": float(o.get("amp", 1.6)) * c["unit"] * _noise(s, f * 3.7), "dy": float(o.get("amp", 1.6)) * c["unit"] * _noise(s + 4, f * 3.7),
        "rot": float(o.get("rot", 0.6)) * _noise(s + 8, f * 3.7)})(math.floor(t * float(o.get("fps", 8)))),
    "ken_burns": lambda t, D, o, c, s: (lambda k: {
        "scale": float(o.get("from", 1.0)) + (float(o.get("to", 1.15)) - float(o.get("from", 1.0))) * k,
        "dx": float((o.get("pan") or [0, 0])[0]) * c["unit"] * k, "dy": float((o.get("pan") or [0, 0])[1]) * c["unit"] * k})(
        easing.apply(o.get("ease", "in_out_sine"), t / max(D, 0.001))),
}
LOOPS["kenburns"] = LOOPS["ken_burns"]


class Loop:
    def __init__(self, spec, where, seed):
        if isinstance(spec, str):
            spec = {"preset": spec}
        if not isinstance(spec, dict) or "preset" not in spec:
            raise SpecError(where, "expected a loop name or {\"preset\": ..., \"amp\": ..., \"period\": ...}")
        name = str(spec["preset"]).lower()
        if name not in LOOPS:
            raise SpecError(where, f"unknown loop '{name}'", suggest(name, LOOPS))
        self.fn, self.opts, self.seed = LOOPS[name], spec, seed
        self.start = spec.get("start", 0)
        self.until = spec.get("until")

    def mods(self, t, D, ctx):
        return self.fn(t, D, self.opts, ctx, self.seed)


class Track:
    """Keyframes of one property: [[time, value], [time, value, ease], ...]; ease shapes the motion INTO that key."""

    def __init__(self, keys, where, resolve_time, resolve_value):
        if not isinstance(keys, list) or not keys:
            raise SpecError(where, "keyframes must be a non-empty list like [[0, 100], [1.2, 400, \"out_back\"]]")
        out = []
        for i, k in enumerate(keys):
            w = f"{where}[{i}]"
            if isinstance(k, dict):
                t, v, e = k.get("t", k.get("at")), k.get("v", k.get("value")), k.get("ease")
            elif isinstance(k, list) and len(k) in (2, 3):
                t, v, e = k[0], k[1], k[2] if len(k) == 3 else None
            else:
                raise SpecError(w, f"bad keyframe {k!r}", "use [time, value] or [time, value, \"ease\"]")
            if e:
                easing.get(e, w)
            out.append((resolve_time(t, w), resolve_value(v, w), e))
        out.sort(key=lambda k: k[0])
        self.keys = out

    def value(self, t):
        k = self.keys
        if t <= k[0][0]:
            return k[0][1]
        for i in range(1, len(k)):
            if t <= k[i][0]:
                t0, v0, _ = k[i - 1]
                t1, v1, e = k[i]
                span = t1 - t0
                u = 1.0 if span <= 0 else (t - t0) / span
                return v0 + (v1 - v0) * easing.apply(e or "in_out_cubic", u)
        return k[-1][1]

    @property
    def end(self):
        return self.keys[-1][0]

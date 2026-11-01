"""Easing curves. Names: linear, in/out/in_out + quad|cubic|quart|quint|sine|expo|circ|back|elastic|bounce,
plus 'spring', 'spring(stiffness,damping)', 'bezier(x1,y1,x2,y2)', 'steps(n)', 'hold'."""
import math
import re

from .util import SpecError, suggest


def _bounce_out(t):
    n, d = 7.5625, 2.75
    if t < 1 / d:
        return n * t * t
    if t < 2 / d:
        t -= 1.5 / d
        return n * t * t + 0.75
    if t < 2.5 / d:
        t -= 2.25 / d
        return n * t * t + 0.9375
    t -= 2.625 / d
    return n * t * t + 0.984375


_IN = {
    "quad": lambda t: t * t,
    "cubic": lambda t: t ** 3,
    "quart": lambda t: t ** 4,
    "quint": lambda t: t ** 5,
    "sine": lambda t: 1 - math.cos(t * math.pi / 2),
    "expo": lambda t: 0.0 if t == 0 else 2 ** (10 * t - 10),
    "circ": lambda t: 1 - math.sqrt(max(0.0, 1 - t * t)),
    "back": lambda t: 2.70158 * t ** 3 - 1.70158 * t * t,
    "elastic": lambda t: t if t in (0, 1) else -(2 ** (10 * t - 10)) * math.sin((t * 10 - 10.75) * (2 * math.pi / 3)),
    "bounce": lambda t: 1 - _bounce_out(1 - t),
}

CURVES = {"linear": lambda t: t, "hold": lambda t: 0.0 if t < 1 else 1.0}
for _name, _f in _IN.items():
    CURVES[f"in_{_name}"] = _f
    CURVES[f"out_{_name}"] = (lambda f: lambda t: 1 - f(1 - t))(_f)
    CURVES[f"in_out_{_name}"] = (lambda f: lambda t: f(2 * t) / 2 if t < 0.5 else 1 - f(2 - 2 * t) / 2)(_f)
CURVES.update({"in": CURVES["in_cubic"], "out": CURVES["out_cubic"], "in_out": CURVES["in_out_cubic"],
               "ease": CURVES["in_out_sine"], "smooth": CURVES["in_out_quint"], "snappy": CURVES["out_expo"],
               "overshoot": CURVES["out_back"]})


def _spring(stiffness=170.0, damping=14.0):
    """Damped spring from 0 to 1 over normalized time (mass 1, settled ~at t=1)."""
    w0 = math.sqrt(stiffness)
    zeta = damping / (2 * w0)
    span = 6.0 / max(zeta * w0, 0.5)  # seconds until settled, mapped to t=1

    def f(t):
        if t >= 1:
            return 1.0
        s = t * span
        if zeta < 1:
            wd = w0 * math.sqrt(1 - zeta * zeta)
            return 1 - math.exp(-zeta * w0 * s) * (math.cos(wd * s) + zeta * w0 / wd * math.sin(wd * s))
        return 1 - math.exp(-w0 * s) * (1 + w0 * s)
    return f


def _bezier(x1, y1, x2, y2):
    def bx(t):
        return 3 * (1 - t) ** 2 * t * x1 + 3 * (1 - t) * t * t * x2 + t ** 3

    def by(t):
        return 3 * (1 - t) ** 2 * t * y1 + 3 * (1 - t) * t * t * y2 + t ** 3

    def f(x):
        lo, hi = 0.0, 1.0
        for _ in range(30):
            mid = (lo + hi) / 2
            if bx(mid) < x:
                lo = mid
            else:
                hi = mid
        return by((lo + hi) / 2)
    return f


_cache = {}


def get(name, where="ease"):
    if callable(name):
        return name
    if name is None:
        return CURVES["out_cubic"]
    key = str(name).strip().lower().replace("-", "_").replace("ease_", "")
    if key in _cache:
        return _cache[key]
    f = CURVES.get(key)
    if f is None:
        m = re.fullmatch(r"(spring|bezier|cubic_bezier|steps)\(([^)]*)\)", key)
        if key == "spring":
            f = _spring()
        elif m:
            try:
                args = [float(a) for a in m.group(2).split(",") if a.strip()]
            except ValueError:
                raise SpecError(where, f"bad easing {name!r}")
            if m.group(1) == "spring":
                f = _spring(*args[:2])
            elif m.group(1) == "steps":
                n = max(1, int(args[0]) if args else 4)
                f = lambda t, n=n: min(1.0, math.floor(t * n) / n) if t < 1 else 1.0
            elif len(args) == 4:
                f = _bezier(*args)
        if f is None:
            raise SpecError(where, f"unknown easing {name!r}", suggest(key, list(CURVES) + ["spring", "bezier(…)", "steps(n)"]))
    _cache[key] = f
    return f


def apply(name, t, where="ease"):
    t = 0.0 if t <= 0 else 1.0 if t >= 1 else t
    return get(name, where)(t)

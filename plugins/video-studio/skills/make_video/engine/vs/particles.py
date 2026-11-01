"""Deterministic particle systems: dots, snow, dust, bokeh, confetti, sparks, embers, rain, stars, bubbles."""
import math
import random

from PIL import Image, ImageDraw, ImageFilter

from .layers import Layer
from .raster import Content
from .util import SpecError, color as parse_color, length, suggest

KINDS = {
    #          speed(px/s)   size(px)    dir(deg, 90=down)  spread  soft  colors
    "dots":    ((20, 60),    (4, 10),    270,  360, 0.0, ["#ffffff"]),
    "snow":    ((40, 110),   (4, 12),    90,   25,  0.5, ["#ffffff"]),
    "dust":    ((6, 22),     (2, 5),     270,  360, 0.6, ["#fff6e0"]),
    "bokeh":   ((8, 25),     (40, 120),  270,  360, 0.9, ["#ffd27a", "#ff9ec7", "#9ad7ff"]),
    "confetti": ((180, 380), (14, 26),   90,   30,  0.0, ["#ff2d55", "#ffd60a", "#30d158", "#0a84ff", "#bf5af2"]),
    "sparks":  ((260, 520),  (3, 6),     270,  50,  0.2, ["#fff1a8", "#ffb347"]),
    "embers":  ((40, 120),   (3, 8),     270,  40,  0.6, ["#ff8a3d", "#ffcc66", "#ff4d1a"]),
    "rain":    ((1300, 1800), (2, 3),    100,  4,   0.0, ["#cfe8ff"]),
    "stars":   ((0, 0),      (3, 8),     0,    0,   0.4, ["#ffffff"]),
    "bubbles": ((50, 120),   (14, 40),   270,  20,  0.0, ["#ffffff"]),
}


class ParticlesLayer(Layer):
    KEYS = {"kind", "count", "seed", "colors", "size", "speed", "direction", "spread", "opacity_range", "spin", "wobble", "fade_edges"}
    default_anchor = (0.5, 0.5)

    def __init__(self, spec, tl, where):
        super().__init__(spec, tl, where)
        kind = spec.get("kind", "dust")
        if kind not in KINDS:
            raise SpecError(where + ".kind", f"unknown particles '{kind}'", suggest(kind, KINDS))
        self.kind = kind
        W, H = tl.size
        self.bw = length(spec.get("w"), W, where + ".w", W, H) if spec.get("w") is not None else (self.slot[2] if self.slot else W)
        self.bh = length(spec.get("h"), H, where + ".h", W, H) if spec.get("h") is not None else (self.slot[3] if self.slot else H)
        speed, size, direction, spread, self.soft, colors = KINDS[kind]
        speed = spec.get("speed", speed)
        size = spec.get("size", size)
        direction = float(spec.get("direction", direction))
        spread = float(spec.get("spread", spread))
        colors = [parse_color(c, where + ".colors") for c in spec.get("colors", colors)]
        n = int(spec.get("count", {"bokeh": 18, "rain": 120, "confetti": 90, "stars": 80}.get(kind, 60)))
        if n > 600:
            raise SpecError(where + ".count", "count over 600 is too slow on phones")
        rng = random.Random(int(spec.get("seed", 1)))
        orange = spec.get("opacity_range", [0.35, 1.0])
        unit = self.rc.anim_ctx["unit"]
        self.parts = []
        for i in range(n):
            ang = math.radians(direction + rng.uniform(-spread / 2, spread / 2))
            v = rng.uniform(*speed) * unit
            self.parts.append({
                "x": rng.random(), "y": rng.random(), "vx": math.cos(ang) * v, "vy": math.sin(ang) * v,
                "size": rng.uniform(*size) * unit, "color": colors[i % len(colors)], "op": rng.uniform(*orange),
                "rot": rng.uniform(0, 360), "spin": rng.uniform(-1, 1) * float(spec.get("spin", 360)), "phase": rng.uniform(0, 6.28),
                "wob": float(spec.get("wobble", 18 if kind in ("snow", "bubbles", "confetti", "embers") else 0)) * unit * rng.uniform(0.5, 1),
            })
        self._sprites = {}

    def _sprite(self, part, d):
        key = (round(part["size"] * d), part["color"], self.kind)
        sp = self._sprites.get(key)
        if sp is None:
            s = max(1, key[0])
            pad = int(s * self.soft) + 2
            img = Image.new("RGBA", (s + pad * 2, s + pad * 2), (0, 0, 0, 0))
            dr = ImageDraw.Draw(img)
            c = part["color"]
            if self.kind == "bubbles":
                dr.ellipse((pad, pad, pad + s, pad + s), outline=c[:3] + (200,), width=max(1, s // 10))
                dr.ellipse((pad + s * 0.22, pad + s * 0.2, pad + s * 0.42, pad + s * 0.38), fill=c[:3] + (220,))
            else:
                dr.ellipse((pad, pad, pad + s, pad + s), fill=c)
            if self.soft > 0:
                img = img.filter(ImageFilter.GaussianBlur(max(0.6, s * self.soft * 0.35)))
            sp = img
            self._sprites[key] = sp
        return sp

    def content(self, p, d):
        w, h = max(1, int(self.bw * d)), max(1, int(self.bh * d))
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        t = p.lt
        fade = self.spec.get("fade_edges", True)
        for q in self.parts:
            m = q["size"] * 3
            x = (q["x"] * (self.bw + 2 * m) + q["vx"] * t + math.sin(t * 1.3 + q["phase"]) * q["wob"]) % (self.bw + 2 * m) - m
            y = (q["y"] * (self.bh + 2 * m) + q["vy"] * t + math.cos(t * 1.1 + q["phase"]) * q["wob"] * 0.4) % (self.bh + 2 * m) - m
            op = q["op"]
            if self.kind in ("stars", "dust", "embers"):
                op *= 0.55 + 0.45 * math.sin(t * (2.0 if self.kind == "stars" else 3.1) + q["phase"] * 3)
            if fade:
                ef = min(1.0, max(0.0, min(y, self.bh - y, x, self.bw - x) / (0.08 * min(self.bw, self.bh))))
                op *= ef
            if op <= 0.02:
                continue
            X, Y = x * d, y * d
            col = q["color"][:3] + (int(q["color"][3] * op),)
            if self.kind == "confetti":
                a = math.radians(q["rot"] + q["spin"] * t)
                sw, sh = q["size"] * d, q["size"] * d * 0.45 * abs(math.cos(t * 4 + q["phase"]))
                pts = [(X + math.cos(a) * dx - math.sin(a) * dy, Y + math.sin(a) * dx + math.cos(a) * dy)
                       for dx, dy in ((-sw / 2, -sh / 2), (sw / 2, -sh / 2), (sw / 2, sh / 2), (-sw / 2, sh / 2))]
                dr.polygon(pts, fill=col)
            elif self.kind in ("sparks", "rain"):
                L = (0.05 if self.kind == "sparks" else 0.035) * d
                dr.line([(X, Y), (X - q["vx"] * L, Y - q["vy"] * L)], fill=col, width=max(1, int(q["size"] * d * 0.6)))
            else:
                sp = self._sprite(q, d)
                if op < 0.98:
                    sp = sp.copy()
                    sp.putalpha(sp.getchannel("A").point(lambda v, o=op: int(v * o)))
                _paste_clip(img, sp, int(X - sp.width / 2), int(Y - sp.height / 2))
        return self.effects(Content(img, d))

    def density(self, dens):
        return dens


def _paste_clip(img, sp, x, y):
    x0, y0 = max(0, -x), max(0, -y)
    if x0 >= sp.width or y0 >= sp.height or x + sp.width <= 0 or y + sp.height <= 0:
        return
    piece = sp.crop((x0, y0, sp.width, sp.height))
    if x + x0 < img.width and y + y0 < img.height:
        img.alpha_composite(piece.crop((0, 0, min(piece.width, img.width - x - x0), min(piece.height, img.height - y - y0))), (x + x0, y + y0))

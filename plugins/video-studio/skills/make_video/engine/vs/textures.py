"""Procedural backgrounds: paper, kraft, notebook, grid, dots, blackboard, noise, halftone, stripes, sunburst, crumpled."""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .layers import Layer
from .raster import Content
from .util import SpecError, color as parse_color, length, suggest

KINDS = {
    # kind: (base color, ink color)
    "paper": ("#f4ecd8", "#c9b99a"), "kraft": ("#c8a27a", "#8a6a48"), "notebook": ("#fbf8ef", "#9cc3e6"),
    "grid": ("#f7f7f2", "#cfd8e3"), "dots": ("#f8f6ef", "#c9c3b4"), "blackboard": ("#23302b", "#e8efe9"),
    "noise": ("#15151a", "#ffffff"), "halftone": ("#ffe14d", "#e0262c"), "stripes": ("#ffd60a", "#ffb800"),
    "sunburst": ("#ffcf33", "#ffb000"), "crumpled": ("#efe7d6", "#b9ab90"),
}


def _smooth_noise(w, h, cell, seed):
    rng = np.random.default_rng(seed)
    gw, gh = max(2, int(w / cell) + 2), max(2, int(h / cell) + 2)
    small = Image.fromarray((rng.random((gh, gw)) * 255).astype(np.uint8), "L")
    return np.asarray(small.resize((w, h), Image.Resampling.BICUBIC), np.float32) / 255.0


def make_texture(kind, w, h, base, ink, scale=1.0, seed=1):
    b = np.array(base[:3], np.float32)
    k = np.array(ink[:3], np.float32)
    img = np.ones((h, w, 3), np.float32) * b
    rng = np.random.default_rng(seed)
    if kind in ("paper", "kraft", "crumpled", "notebook", "grid", "dots", "blackboard"):
        blot = _smooth_noise(w, h, 220 * scale, seed) - 0.5
        img += blot[..., None] * (26 if kind != "blackboard" else 18)
        img += (rng.random((h, w)) - 0.5)[..., None] * (14 if kind != "blackboard" else 10)
        if kind == "crumpled":
            folds = _smooth_noise(w, h, 90 * scale, seed + 3)
            ridge = np.abs(np.gradient(folds, axis=1)) + np.abs(np.gradient(folds, axis=0))
            img -= (ridge / (ridge.max() or 1))[..., None] * 60
            img += (folds - 0.5)[..., None] * 40
        if kind == "kraft":
            fib = _smooth_noise(w, h, 3 * scale, seed + 5)
            img += (fib - 0.5)[..., None] * 18
    if kind == "blackboard":
        smear = _smooth_noise(w, h, 60 * scale, seed + 7)
        img += (smear[..., None] - 0.5) * 30
    if kind == "noise":
        img += (rng.random((h, w)) - 0.5)[..., None] * 40
    out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")
    d = ImageDraw.Draw(out)
    s = max(4, 60 * scale)
    kc = tuple(int(v) for v in k)
    if kind == "notebook":
        for y in np.arange(s * 2, h, s):
            d.line([(0, y), (w, y)], fill=kc, width=max(1, int(2 * scale)))
        d.line([(s * 1.6, 0), (s * 1.6, h)], fill=(232, 120, 120), width=max(1, int(3 * scale)))
    elif kind == "grid":
        for x in np.arange(0, w, s):
            d.line([(x, 0), (x, h)], fill=kc, width=max(1, int(2 * scale)))
        for y in np.arange(0, h, s):
            d.line([(0, y), (w, y)], fill=kc, width=max(1, int(2 * scale)))
    elif kind == "dots":
        r = max(1.5, 3 * scale)
        for y in np.arange(s / 2, h, s):
            for x in np.arange(s / 2, w, s):
                d.ellipse((x - r, y - r, x + r, y + r), fill=kc)
    elif kind == "halftone":
        step = max(8, 36 * scale)
        for yi, y in enumerate(np.arange(0, h + step, step)):
            for x in np.arange((yi % 2) * step / 2, w + step, step):
                r = step * 0.48 * (0.15 + 0.85 * (1 - y / h))
                d.ellipse((x - r, y - r, x + r, y + r), fill=kc)
    elif kind == "stripes":
        step = max(10, 90 * scale)
        for x in np.arange(-h, w + h, step):
            d.polygon([(x, 0), (x + step / 2, 0), (x + step / 2 + h, h), (x + h, h)], fill=kc)
    elif kind == "sunburst":
        cx, cy = w / 2, h / 2
        R = math.hypot(w, h)
        n = 24
        for i in range(0, n, 2):
            a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
            d.polygon([(cx, cy), (cx + R * math.cos(a0), cy + R * math.sin(a0)), (cx + R * math.cos(a1), cy + R * math.sin(a1))], fill=kc)
    if kind == "blackboard":
        out = out.filter(ImageFilter.GaussianBlur(0.6))
    return out.convert("RGBA")


class TextureLayer(Layer):
    KEYS = {"kind", "color", "ink", "scale_pattern", "seed"}

    def __init__(self, spec, tl, where):
        super().__init__(spec, tl, where)
        self.kind = spec.get("kind", "paper")
        if self.kind not in KINDS:
            raise SpecError(where + ".kind", f"unknown texture '{self.kind}'", suggest(self.kind, KINDS))
        base, ink = KINDS[self.kind]
        self.base_color = parse_color(spec.get("color", base), where + ".color")
        self.ink = parse_color(spec.get("ink", ink), where + ".ink")
        W, H = tl.size
        self.bw = length(spec.get("w"), W, where + ".w", W, H) if spec.get("w") is not None else (self.slot[2] if self.slot else W)
        self.bh = length(spec.get("h"), H, where + ".h", W, H) if spec.get("h") is not None else (self.slot[3] if self.slot else H)

    def content(self, p, d):
        def make():
            w, h = max(1, int(self.bw * d)), max(1, int(self.bh * d))
            img = make_texture(self.kind, w, h, self.base_color, self.ink, float(self.spec.get("scale_pattern", 1)) * d, int(self.spec.get("seed", 1)))
            return self.effects(Content(img, d))
        return self.cached(round(d, 3), make)

    def density(self, dens):
        return dens

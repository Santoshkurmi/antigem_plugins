"""Word-synced captions from voice timings. Chunks are computed once for the whole video so they stay identical
across scene boundaries; each scene draws the chunk that is on screen at its time."""
from PIL import Image, ImageDraw

from . import easing, raster, text as textmod
from .layers import Layer
from .raster import Content, chain, scale, translate
from .util import SpecError, color as parse_color, length, suggest, with_alpha

STYLES = {
    # active word color, active box, words appear as spoken, single-word mode, uppercase, size
    "karaoke": {"active": "#ffd60a", "box": None, "progressive": False, "single": False, "uppercase": False, "size": 68},
    "box":     {"active": "#ffffff", "box": "#ff2d55", "progressive": False, "single": False, "uppercase": True, "size": 66},
    "pop":     {"active": "#ffd60a", "box": None, "progressive": True, "single": False, "uppercase": True, "size": 74},
    "clean":   {"active": None, "box": None, "progressive": False, "single": False, "uppercase": False, "size": 60},
    "single":  {"active": "#ffffff", "box": None, "progressive": False, "single": True, "uppercase": True, "size": 120},
    "minimal": {"active": "#ffffff", "box": None, "progressive": False, "single": False, "uppercase": False, "size": 54},
}
KEYS = {"style", "font", "size", "color", "active_color", "active_box", "stroke_width", "stroke_color", "uppercase",
        "y", "x", "max_width", "max_words", "max_chars", "shadow", "plate", "enabled", "pop", "line_height", "weight", "max_lines"}


def build_chunks(words, max_words, max_chars, single, cuts=()):
    chunks, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        text_len = sum(len(x["word"]) + 1 for x in cur)
        nxt = words[i + 1] if i + 1 < len(words) else None
        crosses = nxt is not None and any(w["start"] < c <= nxt["start"] for c in cuts)
        brk = single or crosses or len(cur) >= max_words or text_len >= max_chars or w["word"][-1:] in ".!?,;:।" or \
            (nxt is not None and nxt["start"] - w["end"] > 0.45)
        if brk or nxt is None:
            chunks.append(cur)
            cur = []
    out = []
    for i, c in enumerate(chunks):
        start = c[0]["start"]
        end = c[-1]["end"]
        nxt = chunks[i + 1][0]["start"] if i + 1 < len(chunks) else end + 0.6
        out.append({"words": c, "start": start, "end": min(nxt, end + 0.6)})
    return out


class CaptionsLayer(Layer):
    KEYS = KEYS

    def __init__(self, spec, tl, where, chunks):
        cfg = {k: v for k, v in spec.items()}
        style = cfg.get("style", "karaoke")
        if style not in STYLES:
            raise SpecError(where + ".style", f"unknown captions style '{style}'", suggest(style, STYLES))
        base = STYLES[style]
        layer_spec = {"type": "captions", "camera": False, "z": 1000}
        if cfg.get("x") is not None:
            layer_spec["x"] = cfg["x"]
        W, H = tl.size
        layer_spec["y"] = cfg.get("y", "70%" if H > W else "84%")
        super().__init__(layer_spec, tl, where)
        self.cfg, self.base_style = cfg, base
        st = {"font": cfg.get("font", "display" if base["uppercase"] else "sans"), "size": cfg.get("size", base["size"] * self.rc.anim_ctx["unit"]),
              "color": cfg.get("color", "#ffffff"), "stroke_width": cfg.get("stroke_width", 6 if style != "box" else 0),
              "stroke_color": cfg.get("stroke_color", "#000000"), "uppercase": cfg.get("uppercase", base["uppercase"]),
              "line_height": cfg.get("line_height", 1.08), "highlight": cfg.get("active_color", base["active"] or cfg.get("color", "#ffffff")),
              "highlight_box": cfg.get("active_box", base["box"]), "weight": cfg.get("weight")}
        sample = " ".join(w["word"] for c in chunks[:20] for w in c["words"])
        self.style = textmod.Style(st, where, self.rc.font_aliases, sample)
        self.max_w = length(cfg.get("max_width", "86%"), W, where + ".max_width", W, H)
        self.chunks = chunks
        self.single = base["single"]
        self.progressive = base["progressive"]
        self.pop = cfg.get("pop", True)
        self._lay = {}

    def resolve_times(self):
        if self._times is None:
            self._times = (0.0, self.tl.duration)

    def _chunk_at(self, g):
        for i, c in enumerate(self.chunks):
            if c["start"] - 0.02 <= g < c["end"]:
                return i, c
        return None, None

    def _layout(self, ci, d):
        key = (ci, round(d, 3))
        if key not in self._lay:
            c = self.chunks[ci]
            tokens = [(w["word"], False) for w in c["words"]]
            lay = textmod.layout(tokens, self.style, self.max_w, None, self.cfg.get("max_lines", 2), None, d, "word")
            normal = [textmod.unit_sprite(u, lay, self.style, d) for u in lay.units]
            active = [textmod.unit_sprite(u, lay, self.style, d, active=True) for u in lay.units] if (self.base_style["active"] or self.style.hi_box) else normal
            if len(self._lay) > 6:
                self._lay.clear()
            self._lay[key] = (lay, normal, active)
        return self._lay[key]

    def content(self, p, d):
        g = self.tl.start_global + p.lt
        ci, c = self._chunk_at(g)
        if c is None:
            return None
        aw = None
        for j, w in enumerate(c["words"]):
            if w["start"] - 0.02 <= g:
                aw = j
        key = (ci, aw, round(d, 3), round(g - c["start"], 2) if (g - c["start"] < 0.2 or self.progressive) else "s")
        return self.cached(key, lambda: self._make(ci, c, aw, g, d))

    def _make(self, ci, c, aw, g, d):
        lay, normal, active = self._layout(ci, d)
        if self.single and aw is not None:
            units = [(lay.units[aw], active[aw])] if aw < len(lay.units) else []
            idx = [aw]
        else:
            units = list(zip(lay.units, [active[j] if j == aw else normal[j] for j in range(len(lay.units))]))
            idx = list(range(len(lay.units)))
        pad = int(lay.size * d * 0.6) + 6
        if self.single and units:
            u0 = units[0][0]
            w, h = int(u0["w"]) + 1, int(u0["h"]) + 1
            offx, offy = -u0["x"], -u0["y"]
        else:
            w, h = int(lay.width) + 1, int(lay.height) + 1
            offx = offy = 0
        img = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
        age = g - c["start"]
        for j, (u, (sp, sx, sy)) in zip(idx, units):
            word = c["words"][j] if j < len(c["words"]) else None
            k, op = 1.0, 1.0
            if self.progressive and word is not None:
                wa = g - word["start"]
                if wa < 0:
                    continue
                k = 0.6 + 0.4 * easing.apply("out_back", wa / 0.18)
                op = min(1.0, wa / 0.06)
            elif self.pop and j == aw and word is not None:
                k = 1 + 0.12 * (1 - easing.apply("out_cubic", (g - word["start"]) / 0.22))
            x = pad + offx + u["x"] + u["w"] / 2
            y = pad + offy + u["y"] + u["h"] / 2
            m = chain(translate(x, y), scale(k), translate(-(u["w"] / 2 + sx), -(u["h"] / 2 + sy)))
            raster.draw(img, Content(sp), m, op, "normal", self.rc.fast)
        if age < 0.12 and not self.progressive:
            e = easing.apply("out_cubic", age / 0.12)
            img.putalpha(img.getchannel("A").point(lambda v: int(v * (0.3 + 0.7 * e))))
        c2 = Content(img, d, (pad, pad, w, h))
        if self.cfg.get("plate"):
            pl = self.cfg["plate"] if isinstance(self.cfg["plate"], dict) else {"color": self.cfg["plate"]}
            bg = Image.new("RGBA", img.size, (0, 0, 0, 0))
            px, py = int(lay.size * d * 0.4), int(lay.size * d * 0.18)
            ImageDraw.Draw(bg).rounded_rectangle((pad - px, pad - py, pad + w + px, pad + h + py), radius=int(lay.size * d * 0.25),
                                                 fill=with_alpha(parse_color(pl.get("color", "#000000b0"), self.where + ".plate"), float(pl.get("opacity", 1))))
            bg.alpha_composite(img)
            c2 = Content(bg, d, (pad, pad, w, h))
        if self.cfg.get("shadow", True):
            c2 = raster.add_shadow(c2, self.cfg["shadow"] if isinstance(self.cfg.get("shadow"), dict) else {"blur": 14, "dy": 6, "opacity": 0.55})
        return c2

    def density(self, dens):
        return dens

"""Text: font lookup, markup, wrapping/auto-fit, word sprites (fill/gradient, stroke, shadow, highlight boxes)."""
import glob
import math
import os
import re

from PIL import Image, ImageDraw, ImageFont, features

from . import raster
from .util import FONTS_DIR, SpecError, color as parse_color, suggest

HAS_RAQM = features.check("raqm")
_DEVA = re.compile(r"[ऀ-ॿ꣠-ꣿ]")
DEVA_FONTS = ("baloo", "khand", "kalam", "devanagari", "yatra", "mukta", "hind", "tiro", "poppins", "martel", "rajdhani")

ALIASES = {
    "display": "Anton-Regular", "impact": "Anton-Regular", "headline": "Anton-Regular",
    "sans": "LiberationSans-Bold", "bold": "LiberationSans-Bold", "ui": "LiberationSans-Bold",
    "serif": "PlayfairDisplay-Bold", "elegant": "PlayfairDisplay-Bold", "editorial": "Merriweather-Bold",
    "book": "Lora-Bold", "body_serif": "NotoSerif-Regular", "mono": "SpaceMono-Bold", "code": "SpaceMono-Bold",
    "hand": "Kalam-Bold", "marker": "Kalam-Bold", "rounded": "Baloo2-ExtraBold", "fun": "Baloo2-ExtraBold",
    "hindi": "Baloo2-Bold", "devanagari": "NotoSansDevanagari-VF", "hindi_display": "Baloo2-ExtraBold",
    "hindi_condensed": "Khand-Bold", "hindi_serif": "NotoSerifDevanagari-VF", "hindi_title": "YatraOne-Regular",
}
DEVA_FALLBACK = {"Anton-Regular": "Khand-Bold", "PlayfairDisplay-Bold": "NotoSerifDevanagari-VF",
                 "Merriweather-Bold": "NotoSerifDevanagari-VF", "Lora-Bold": "NotoSerifDevanagari-VF",
                 "NotoSerif-Regular": "NotoSerifDevanagari-VF", "SpaceMono-Bold": "NotoSansDevanagari-VF"}

_font_dirs = []
_cache = {}


def set_font_dirs(dirs):
    _font_dirs[:] = [d for d in dirs if d and os.path.isdir(d)] + [FONTS_DIR]


def _all_fonts():
    seen = []
    for d in _font_dirs or [FONTS_DIR]:
        seen += glob.glob(os.path.join(d, "**", "*.[ot]tf"), recursive=True) + glob.glob(os.path.join(d, "**", "*.[OT]TF"), recursive=True)
    for d in ("/usr/share/fonts", "/system/fonts", os.path.expanduser("~/.fonts"), os.path.join(os.environ.get("PREFIX", "/usr"), "share/fonts")):
        if os.path.isdir(d):
            seen += glob.glob(os.path.join(d, "**", "*.[ot]tf"), recursive=True)
    return seen


def find_font(name, aliases=None, where="font"):
    name = (aliases or {}).get(name, name) if name else "sans"
    name = ALIASES.get(str(name).lower(), name)
    if os.path.isabs(name) and os.path.exists(name):
        return name
    for d in _font_dirs + [FONTS_DIR]:
        p = os.path.join(d, name)
        if os.path.exists(p) and os.path.isfile(p):
            return p
    stem = os.path.splitext(os.path.basename(str(name)))[0].lower().replace(" ", "").replace("_", "").replace("-", "")
    fonts = _all_fonts()
    best = None
    for f in fonts:
        s = os.path.splitext(os.path.basename(f))[0].lower().replace(" ", "").replace("_", "").replace("-", "")
        if s == stem:
            return f
        if best is None and s.startswith(stem):
            best = f
    if best:
        return best
    names = sorted({os.path.splitext(os.path.basename(f))[0] for f in fonts if FONTS_DIR in f}) + sorted(ALIASES)
    raise SpecError(where, f"font '{name}' not found", suggest(name, names))


def _weight_for(path, weight):
    if weight:
        return float(weight)
    base = os.path.basename(path).lower()
    for key, w in (("black", 900), ("extrabold", 800), ("semibold", 600), ("bold", 700), ("medium", 500), ("light", 300)):
        if key in base:
            return w
    return None


def load_font(path, size, weight=None):
    size = max(1, int(round(size)))
    key = (path, size, weight)
    f = _cache.get(key)
    if f is None:
        layout = ImageFont.Layout.RAQM if HAS_RAQM else ImageFont.Layout.BASIC
        f = ImageFont.truetype(path, size, layout_engine=layout)
        w = _weight_for(path, weight)
        if w:
            try:
                axes = f.get_variation_axes()
                vals = []
                for ax in axes:
                    nm = ax.get("name", b"")
                    nm = nm.decode() if isinstance(nm, bytes) else str(nm)
                    vals.append(max(ax["minimum"], min(ax["maximum"], w)) if nm.lower().startswith("weight") else ax.get("default", ax["minimum"]))
                if axes:
                    f.set_variation_by_axes(vals)
            except Exception:
                pass
        if len(_cache) > 400:
            _cache.clear()
        _cache[key] = f
    return f


def pick_font(name, text, aliases=None, where="font"):
    path = find_font(name, aliases, where)
    if _DEVA.search(text or ""):
        low = os.path.basename(path).lower()
        if not any(k in low for k in DEVA_FONTS):
            stem = os.path.splitext(os.path.basename(path))[0]
            path = find_font(DEVA_FALLBACK.get(stem, "Baloo2-Bold"), None, where)
    return path


def parse_markup(text):
    """'*word*' marks highlighted words (punctuation may follow: '*blue*?'), '\\n' forces a line break.
    Returns [(word, highlighted)] with None for breaks."""
    out = []
    hi = False
    for li, line in enumerate(str(text).split("\n")):
        if li:
            out.append(None)
        for raw in line.split():
            m = re.match(r"^(\*?)(.*?)(\*?)([^\w*]*)$", raw, re.S)
            start, word, end, tail = m.groups() if m else ("", raw, "", "")
            if start:
                hi = True
            if word or tail:
                out.append((word + tail, hi))
            if end:
                hi = False
    return out


class Style:
    def __init__(self, spec, where, aliases=None, text=""):
        self.where = where
        self.font_path = pick_font(spec.get("font"), text, aliases, where + ".font")
        self.size = float(spec.get("size", 72))
        self.weight = spec.get("weight")
        self.fill = spec.get("color", "#ffffff")
        if isinstance(self.fill, dict):
            raster.gradient(2, 2, self.fill, where + ".color")
        else:
            parse_color(self.fill, where + ".color")
        self.hi_fill = spec.get("highlight", spec.get("highlight_color", "#ffd60a"))
        self.hi_box = spec.get("highlight_box")
        self.stroke = float(spec.get("stroke_width", spec.get("stroke", 0)) or 0) if not isinstance(spec.get("stroke"), dict) else float(spec["stroke"].get("width", 4))
        self.stroke_color = parse_color(spec.get("stroke_color", spec["stroke"].get("color", "#000") if isinstance(spec.get("stroke"), dict) else "#000000"), where + ".stroke_color")
        self.line_height = float(spec.get("line_height", 1.12))
        self.letter_spacing = float(spec.get("letter_spacing", 0))
        self.align = spec.get("align", "center")
        if self.align not in ("left", "center", "right"):
            raise SpecError(where + ".align", f"bad align {self.align!r}", "left, center or right")
        self.upper = bool(spec.get("uppercase", False))
        self.word_spacing = float(spec.get("word_spacing", 1.0))


class Layout:
    """Lines of positioned units in logical px. Each unit: dict(text, hi, x, y (top), w, h, line)."""

    def __init__(self, units, width, height, lines, size, ascent):
        self.units, self.width, self.height, self.lines, self.size, self.ascent = units, width, height, lines, size, ascent


def _measure(font, word, spacing):
    if spacing and len(word) > 1:
        return sum(font.getlength(ch) for ch in word) + spacing * (len(word) - 1)
    return font.getlength(word)


def layout(tokens, style, max_width=None, max_height=None, max_lines=None, min_size=None, d=1.0, by="word"):
    """Wrap tokens into lines, shrinking the font until it fits max_width/max_height/max_lines."""
    size = style.size
    min_size = min_size or max(8.0, size * 0.35)
    while True:
        font = load_font(style.font_path, size * d, style.weight)
        sp = style.letter_spacing * d
        asc, desc = font.getmetrics()
        lh = (asc + desc) * style.line_height
        space = font.getlength(" ") * style.word_spacing
        maxw = max_width * d if max_width else None
        lines, cur, cur_w = [], [], 0.0
        too_wide = False
        for tok in tokens:
            if tok is None:
                lines.append(cur)
                cur, cur_w = [], 0.0
                continue
            word = tok[0].upper() if style.upper else tok[0]
            ww = _measure(font, word, sp)
            if maxw and ww > maxw:
                too_wide = True
            add = ww if not cur else space + ww
            if maxw and cur and cur_w + add > maxw:
                lines.append(cur)
                cur, cur_w = [(word, tok[1], ww)], ww
            else:
                cur.append((word, tok[1], ww))
                cur_w += add
        lines.append(cur)
        while lines and not lines[-1] and len(lines) > 1:
            lines.pop()
        total_h = lh * len(lines) - (lh - (asc + desc))
        fits = not too_wide and (not max_height or total_h <= max_height * d + 0.5) and (not max_lines or len(lines) <= max_lines)
        if fits or size <= min_size:
            break
        size = max(min_size, size * 0.92)
    widths = [sum(u[2] for u in ln) + space * max(0, len(ln) - 1) for ln in lines]
    block_w = max(widths) if widths else 0
    units = []
    for li, ln in enumerate(lines):
        x = {"left": 0, "center": (block_w - widths[li]) / 2, "right": block_w - widths[li]}[style.align]
        y = li * lh
        for word, hi, ww in ln:
            units.append({"text": word, "hi": hi, "x": x, "y": y, "w": ww, "h": asc + desc, "line": li})
            x += ww + space
    if by == "char":
        chars = []
        for u in units:
            x = u["x"]
            for ch in u["text"]:
                cw = _measure(font, ch, 0)
                chars.append({"text": ch, "hi": u["hi"], "x": x, "y": u["y"], "w": cw, "h": u["h"], "line": u["line"]})
                x += cw + sp
        units = chars
    elif by == "line":
        merged = {}
        for u in units:
            m = merged.get(u["line"])
            if m is None:
                merged[u["line"]] = dict(u, parts=[u])
            else:
                m["parts"].append(u)
                m["w"] = u["x"] + u["w"] - m["x"]
        units = list(merged.values())
    lay = Layout(units, block_w, max(1.0, total_h), len(lines), size, asc)
    lay.font = font
    return lay


def _draw_word(draw, xy, text, font, fill, stroke, stroke_color, spacing):
    x, y = xy
    kw = {"font": font, "fill": fill}
    if stroke > 0:
        kw.update(stroke_width=int(round(stroke)), stroke_fill=stroke_color)
    if spacing and len(text) > 1:
        for ch in text:
            draw.text((x, y), ch, **kw)
            x += font.getlength(ch) + spacing
    else:
        draw.text((x, y), text, **kw)


def unit_sprite(unit, lay, style, d, active=False, overrides=None):
    """Render one unit (word/char/line) to an RGBA image. Returns (img, ox, oy): where the unit box's top-left sits."""
    o = overrides or {}
    font = lay.font
    stroke = float(o.get("stroke", style.stroke)) * d
    hi = unit["hi"] or active
    fill = o.get("color") or (style.hi_fill if hi else style.fill)
    box = o.get("box") or (style.hi_box if hi else None)
    bspec = None
    bx = by = 0.0
    if box:
        bspec = box if isinstance(box, dict) else {"color": box}
        bpad = bspec.get("padding", [0.16, 0.04])
        bx, by = float(bpad[0]) * lay.size * d, float(bpad[1]) * lay.size * d
    pad = int(math.ceil(max(stroke + lay.size * d * 0.25, bx + 2, by + 2))) + 2
    parts = unit.get("parts") or [unit]
    w = int(math.ceil(unit["w"] + pad * 2))
    h = int(math.ceil(unit["h"] + pad * 2))
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if bspec:
        r = float(bspec.get("radius", 0.16)) * lay.size * d
        ImageDraw.Draw(img).rounded_rectangle((pad - bx, pad - by, pad + unit["w"] + bx, pad + unit["h"] + by), radius=r,
                                              fill=parse_color(bspec.get("color", "#ff2d55"), style.where + ".highlight_box"))
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    stroke_layer = None
    for p in parts:
        px0 = pad + (p["x"] - unit["x"])
        if stroke > 0:
            if stroke_layer is None:
                stroke_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            _draw_word(ImageDraw.Draw(stroke_layer), (px0, pad), p["text"], font, style.stroke_color,
                       stroke, style.stroke_color, style.letter_spacing * d)
        _draw_word(md, (px0, pad), p["text"], font, 255, 0, None, style.letter_spacing * d)
    if stroke_layer is not None:
        img.alpha_composite(stroke_layer)
    img.alpha_composite(raster.fill_mask(mask, fill, style.where + ".color"))
    return img, pad, pad

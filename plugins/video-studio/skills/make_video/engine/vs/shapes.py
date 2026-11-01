"""Vector shapes with draw-on progress, and simple animated charts."""
import math

from PIL import Image, ImageDraw

from . import easing, raster, text as textmod
from .layers import Layer
from .raster import Content
from .util import SpecError, color as parse_color, length, suggest

KINDS = {"rect", "ellipse", "circle", "ring", "line", "arrow", "path", "polygon", "star"}


def catmull_rom(pts, steps=16):
    if len(pts) < 3:
        return pts
    out = []
    p = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        for s in range(steps):
            t = s / steps
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[k]) + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2
                                    + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3) for k in (0, 1)))
    out.append(pts[-1])
    return out


def trim_path(pts, progress):
    """First `progress` (0-1) of a polyline by length."""
    if progress >= 1 or len(pts) < 2:
        return pts
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    total = sum(seg)
    want = total * max(0.0, progress)
    out = [pts[0]]
    acc = 0.0
    for i, L in enumerate(seg):
        if acc + L >= want:
            u = (want - acc) / L if L else 0
            out.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * u, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * u))
            return out
        out.append(pts[i + 1])
        acc += L
    return out


def dash_path(pts, on, off):
    """Split a polyline into dash pieces."""
    pieces, cur, draw_on, left = [], [pts[0]], True, on
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        L = math.dist(a, b)
        pos = 0.0
        while L - pos > left:
            pos += left
            u = pos / L
            p = (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)
            if draw_on:
                cur.append(p)
                pieces.append(cur)
            cur = [p]
            draw_on = not draw_on
            left = on if draw_on else off
        left -= L - pos
        if draw_on:
            cur.append(b)
        else:
            cur = [b]
    if draw_on and len(cur) > 1:
        pieces.append(cur)
    return pieces


def ellipse_pts(cx, cy, rx, ry, start=-90, sweep=360, n=160):
    return [(cx + rx * math.cos(math.radians(start + sweep * i / n)), cy + ry * math.sin(math.radians(start + sweep * i / n))) for i in range(n + 1)]


def rrect_pts(x0, y0, x1, y1, r, n=10):
    """Clockwise outline of a rounded rectangle, starting at the top-left end of the top edge."""
    r = max(0, min(r, (x1 - x0) / 2, (y1 - y0) / 2))
    pts = [(x0 + r, y0)]
    for cx, cy, a in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        pts += [(cx + r * math.cos(math.radians(a + 90 * i / n)), cy + r * math.sin(math.radians(a + 90 * i / n))) for i in range(n + 1)]
    pts.append((x0 + r, y0))
    return pts


def roughen(pts, amount, seed, step):
    """Hand-drawn wobble: subdivide, then push points sideways with smooth noise (changes with seed = boil frame)."""
    from .anim import _noise
    dense = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        n = max(1, int(math.dist(a, b) / max(step, 1)))
        dense += [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(1, n + 1)]
    closed = math.dist(pts[0], pts[-1]) < 1e-6
    out = []
    for i, (x, y) in enumerate(dense):
        u = i * 0.35
        out.append((x + amount * _noise(seed, u), y + amount * _noise(seed + 17, u)))
    if closed:
        out[-1] = out[0]
    return out


def stroke_poly(draw, pts, width, fill, round_caps=True):
    if len(pts) < 2 or width <= 0:
        return
    draw.line(pts, fill=fill, width=max(1, int(round(width))), joint="curve")
    if round_caps:
        r = width / 2
        for p in (pts[0], pts[-1]):
            draw.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=fill)


class ShapeLayer(Layer):
    KEYS = {"kind", "fill", "stroke", "stroke_width", "radius", "points", "from", "to", "curve", "head", "double",
            "dash", "start_angle", "sweep", "inner", "count", "closed", "size", "cap", "rough", "boil"}

    def __init__(self, spec, tl, where):
        kind = spec.get("kind", "rect")
        if kind not in KINDS:
            raise SpecError(where + ".kind", f"unknown shape '{kind}'", suggest(kind, KINDS))
        self.kind = kind
        self.path_mode = kind in ("line", "arrow", "path", "polygon") and (spec.get("points") or spec.get("from"))
        if self.path_mode:
            self.default_anchor = (0.5, 0.5)
        super().__init__(spec, tl, where)
        W, H = tl.size
        if self.path_mode:
            raw = spec.get("points") or [spec.get("from"), spec.get("to")]
            if not isinstance(raw, list) or len(raw) < 2 or any(not isinstance(p, (list, tuple)) or len(p) != 2 for p in raw):
                raise SpecError(where + ".points", "points must be a list of [x, y] (at least 2)")
            pts = [(length(p[0], W, where + ".points", W, H), length(p[1], H, where + ".points", W, H)) for p in raw]
            if spec.get("curve"):
                pts = catmull_rom(pts)
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            self.ox, self.oy = min(xs), min(ys)
            self.bw, self.bh = max(1.0, max(xs) - self.ox), max(1.0, max(ys) - self.oy)
            self.pts = [(x - self.ox, y - self.oy) for x, y in pts]
            if spec.get("x") is None:
                self.base["x"] = self.ox + self.bw * self.anchor[0]
            if spec.get("y") is None:
                self.base["y"] = self.oy + self.bh * self.anchor[1]
        else:
            size = spec.get("size")
            dw = length(size, W, where + ".size", W, H) if size is not None else (self.slot[2] if self.slot else 200)
            self.bw = length(spec.get("w"), W, where + ".w", W, H) if spec.get("w") is not None else dw
            self.bh = length(spec.get("h"), H, where + ".h", W, H) if spec.get("h") is not None else (
                dw if size is not None or kind in ("circle", "ring", "star") else (self.slot[3] if self.slot else 200))
        self.fill = spec.get("fill", None if kind in ("line", "arrow", "path", "ring") else "#ffffff")
        self.stroke = spec.get("stroke", "#ffffff" if kind in ("line", "arrow", "path", "ring") else None)
        self.sw = float(spec.get("stroke_width", 8 if self.stroke else 0))
        for k in ("fill", "stroke"):
            v = getattr(self, k)
            if v is not None and not isinstance(v, dict):
                parse_color(v, f"{where}.{k}")

    def content(self, p, d):
        prog = round(p.progress, 3)
        rough = float(self.spec.get("rough", 0) or 0)
        bf = int(p.lt * float(self.spec.get("boil", 8))) if rough and self.spec.get("boil", 8) else 0
        return self.cached((round(d, 3), prog, bf), lambda: self._make(d, prog, rough, bf))

    def _make(self, d, prog, rough=0.0, bf=0):
        ss = 2 if self.bw * self.bh * d * d < 2.5e6 else 1
        k = d * ss
        sw = self.sw * k
        head = float(self.spec.get("head", max(18.0, self.sw * 3.2))) * k if self.kind == "arrow" else 0
        pad = int(math.ceil(sw / 2 + head + 4 * ss))
        W, H = int(math.ceil(self.bw * k)) + pad * 2, int(math.ceil(self.bh * k)) + pad * 2
        mask_fill = Image.new("L", (W, H), 0)
        mask_stroke = Image.new("L", (W, H), 0)
        df, ds = ImageDraw.Draw(mask_fill), ImageDraw.Draw(mask_stroke)
        x0, y0, x1, y1 = pad, pad, pad + self.bw * k, pad + self.bh * k
        r = length(self.spec.get("radius", 0), min(self.bw, self.bh), self.where + ".radius") * k
        outline = None
        closed = False
        if self.path_mode:
            outline = [(pad + x * k, pad + y * k) for x, y in self.pts]
            closed = self.kind == "polygon" or bool(self.spec.get("closed"))
            if closed:
                outline = outline + [outline[0]]
        elif self.kind == "rect":
            outline, closed = rrect_pts(x0, y0, x1, y1, r), True
        elif self.kind in ("ellipse", "circle", "ring"):
            sweep = float(self.spec.get("sweep", 360))
            outline = ellipse_pts((x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2 - sw / 2, (y1 - y0) / 2 - sw / 2,
                                  float(self.spec.get("start_angle", -90)), sweep)
            closed = sweep >= 360
        elif self.kind == "star":
            n = int(self.spec.get("count", 5))
            inner = float(self.spec.get("inner", 0.45))
            cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
            outline = [(cx + (rx if i % 2 == 0 else rx * inner) * math.cos(math.radians(-90 + 180 * i / n)),
                        cy + (ry if i % 2 == 0 else ry * inner) * math.sin(math.radians(-90 + 180 * i / n))) for i in range(2 * n)]
            outline.append(outline[0])
            closed = True
        else:
            raise SpecError(self.where, f"shape '{self.kind}' needs \"points\" (or \"from\" and \"to\")")
        if rough > 0:
            outline = roughen(outline, rough * k, bf + abs(hash(self.where)) % 997, 18 * k)
        if self.fill is not None and closed and prog >= 1 and rough > 0:
            df.polygon(outline, fill=255)
        elif self.fill is not None and closed and prog >= 1:
            if self.kind == "rect":
                df.rounded_rectangle((x0, y0, x1, y1), radius=r, fill=255)
            elif self.kind in ("ellipse", "circle"):
                df.ellipse((x0, y0, x1, y1), fill=255)
            else:
                df.polygon(outline, fill=255)
        elif self.fill is not None and closed and prog < 1:
            # fill fades in with the outline
            df.polygon(outline, fill=int(255 * prog * prog))
        if self.stroke is not None and sw > 0:
            pts = trim_path(outline, prog)
            dash = self.spec.get("dash")
            pieces = dash_path(pts, float(dash[0]) * k, float(dash[1]) * k) if dash and len(pts) > 1 else [pts]
            cap = self.spec.get("cap", "round") == "round"
            for piece in pieces:
                stroke_poly(ds, piece, sw, 255, cap)
            if self.kind == "arrow" and len(pts) >= 2 and prog > 0.02:
                self._head(ds, pts, head, sw)
                if self.spec.get("double"):
                    self._head(ds, list(reversed(outline[: max(2, len(pts))])), head, sw)
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if self.fill is not None:
            img.alpha_composite(raster.fill_mask(mask_fill, self.fill, self.where + ".fill"))
        if self.stroke is not None:
            img.alpha_composite(raster.fill_mask(mask_stroke, self.stroke, self.where + ".stroke"))
        if ss > 1:
            img = img.resize((W // ss, H // ss), raster.LANCZOS)
            pad //= ss
        c = Content(img, d, (pad, pad, self.bw * d, self.bh * d))
        return self.effects(c)

    @staticmethod
    def _head(draw, pts, size, sw):
        (ax, ay), (bx, by) = pts[-2], pts[-1]
        for i in range(len(pts) - 2, -1, -1):
            if math.dist(pts[i], pts[-1]) > size * 0.5:
                ax, ay = pts[i]
                break
        ang = math.atan2(by - ay, bx - ax)
        left = (bx - size * math.cos(ang - 0.45), by - size * math.sin(ang - 0.45))
        right = (bx - size * math.cos(ang + 0.45), by - size * math.sin(ang + 0.45))
        draw.polygon([(bx + sw * 0.3 * math.cos(ang), by + sw * 0.3 * math.sin(ang)), left, right], fill=255)


class ChartLayer(Layer):
    KEYS = {"kind", "values", "labels", "colors", "max", "gap", "grow", "show_values", "format", "font", "label_color",
            "value_color", "label_size", "value_size", "line_width", "axis", "dots", "radius"}

    def __init__(self, spec, tl, where):
        super().__init__(spec, tl, where)
        W, H = tl.size
        self.kind = spec.get("kind", "bar")
        if self.kind not in ("bar", "column", "line"):
            raise SpecError(where + ".kind", f"unknown chart '{self.kind}'", "bar (horizontal), column or line")
        vals = spec.get("values")
        if not isinstance(vals, list) or not vals or not all(isinstance(v, (int, float)) for v in vals):
            raise SpecError(where + ".values", "values must be a list of numbers")
        self.values = [float(v) for v in vals]
        self.labels = [str(l) for l in spec.get("labels", [])]
        self.bw = length(spec.get("w"), W, where + ".w", W, H) if spec.get("w") is not None else (self.slot[2] if self.slot else W * 0.8)
        self.bh = length(spec.get("h"), H, where + ".h", W, H) if spec.get("h") is not None else (self.slot[3] if self.slot else H * 0.4)
        self.colors = spec.get("colors", ["#0a84ff", "#ff9f0a", "#30d158", "#ff375f", "#bf5af2", "#64d2ff"])
        if not isinstance(self.colors, list):
            self.colors = [self.colors]
        g = spec.get("grow") or {}
        self.grow_dur = float(g.get("duration", 1.2))
        self.grow_stagger = float(g.get("stagger", 0.12))
        self.grow_delay = float(g.get("delay", 0))
        self.grow_ease = g.get("ease", "out_cubic")
        self.font_path = textmod.find_font(spec.get("font", "sans"), self.rc.font_aliases, where + ".font")
        self.fmt = spec.get("format", "{:,.0f}")

    def _grow(self, lt, i):
        return easing.apply(self.grow_ease, (lt - self.grow_delay - i * self.grow_stagger) / self.grow_dur)

    def content(self, p, d):
        n = len(self.values)
        done = p.lt > self.grow_delay + (n - 1) * self.grow_stagger + self.grow_dur
        key = (round(d, 3), "done" if done else round(p.lt, 4))
        return self.cached(key, lambda: self._make(1e9 if done else p.lt, d))

    def _make(self, lt, d):
        s = self.spec
        w, h = int(self.bw * d), int(self.bh * d)
        pad = int(8 * d)
        img = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        vmax = float(s.get("max", max(self.values) or 1))
        lsize = float(s.get("label_size", 34)) * d
        vsize = float(s.get("value_size", 38)) * d
        lfont = textmod.load_font(self.font_path, lsize)
        vfont = textmod.load_font(self.font_path, vsize)
        lcol = parse_color(s.get("label_color", "#ffffff"), self.where + ".label_color")
        vcol = parse_color(s.get("value_color", "#ffffff"), self.where + ".value_color")
        n = len(self.values)
        show = s.get("show_values", True)
        if self.kind == "line":
            lw = float(s.get("line_width", 8)) * d
            top, bottom = pad + vsize * 1.6, pad + h - (lsize * 1.6 if self.labels else 0)
            xs = [pad + (w * (i + 0.5) / n) for i in range(n)]
            ys = [bottom - (bottom - top) * v / vmax for v in self.values]
            prog = self._grow(lt, 0) if self.grow_stagger == 0 else easing.apply(self.grow_ease, (lt - self.grow_delay) / (self.grow_dur + self.grow_stagger * n))
            from .shapes import trim_path
            pts = trim_path(list(zip(xs, ys)), prog)
            col = parse_color(self.colors[0], self.where + ".colors")
            if s.get("axis", True):
                dr.line([(pad, bottom), (pad + w, bottom)], fill=lcol[:3] + (90,), width=max(1, int(2 * d)))
            stroke_poly(dr, pts, lw, col)
            seg_len = 1.0 / max(1, n - 1)
            for i, (x, y) in enumerate(zip(xs, ys)):
                if prog + 1e-6 >= i * seg_len:
                    r = lw * 1.1
                    if s.get("dots", True):
                        dr.ellipse((x - r, y - r, x + r, y + r), fill=col)
                    if show:
                        dr.text((x, y - r - vsize * 0.3), self.fmt.format(self.values[i]), font=vfont, fill=vcol, anchor="ms")
                if i < len(self.labels):
                    dr.text((x, pad + h), self.labels[i], font=lfont, fill=lcol, anchor="md")
        elif self.kind == "column":
            gap = float(s.get("gap", 0.3))
            slot = w / n
            bwid = slot * (1 - gap)
            base = pad + h - (lsize * 1.5 if self.labels else 0)
            room = base - pad - vsize * 1.4
            for i, v in enumerate(self.values):
                g = self._grow(lt, i)
                bh = room * v / vmax * g
                x0 = pad + slot * i + (slot - bwid) / 2
                col = parse_color(self.colors[i % len(self.colors)], self.where + ".colors")
                if bh > 0.5:
                    dr.rounded_rectangle((x0, base - bh, x0 + bwid, base), radius=min(float(s.get("radius", 12)) * d, bwid / 2, bh / 2), fill=col)
                if show and g > 0.02:
                    dr.text((x0 + bwid / 2, base - bh - vsize * 0.25), self.fmt.format(v * g), font=vfont, fill=vcol, anchor="ms")
                if i < len(self.labels):
                    dr.text((x0 + bwid / 2, pad + h), self.labels[i], font=lfont, fill=lcol, anchor="md")
        else:
            gap = float(s.get("gap", 0.3))
            slot = h / n
            bth = slot * (1 - gap)
            label_w = max([lfont.getlength(l) for l in self.labels] + [0]) + (16 * d if self.labels else 0)
            room = w - label_w - vfont.getlength(self.fmt.format(vmax)) - 16 * d
            for i, v in enumerate(self.values):
                g = self._grow(lt, i)
                y0 = pad + slot * i + (slot - bth) / 2
                bl = room * v / vmax * g
                col = parse_color(self.colors[i % len(self.colors)], self.where + ".colors")
                if i < len(self.labels):
                    dr.text((pad + label_w - 16 * d, y0 + bth / 2), self.labels[i], font=lfont, fill=lcol, anchor="rm")
                if bl > 0.5:
                    dr.rounded_rectangle((pad + label_w, y0, pad + label_w + bl, y0 + bth), radius=min(float(s.get("radius", 12)) * d, bth / 2, bl / 2), fill=col)
                if show and g > 0.02:
                    dr.text((pad + label_w + bl + 12 * d, y0 + bth / 2), self.fmt.format(v * g), font=vfont, fill=vcol, anchor="lm")
        return self.effects(Content(img, d, (pad, pad, w, h)))

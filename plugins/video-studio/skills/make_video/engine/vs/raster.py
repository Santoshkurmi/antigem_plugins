"""Pixel work: 2D affine matrices, compositing a content image onto a canvas, gradients, shadows, masks."""
import math

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from .util import color as parse_color

BICUBIC = Image.Resampling.BICUBIC
BILINEAR = Image.Resampling.BILINEAR
LANCZOS = Image.Resampling.LANCZOS

# Matrices are 6-tuples (a, b, c, d, e, f): x' = a*x + b*y + c ; y' = d*x + e*y + f
IDENTITY = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0)


def mul(m, n):
    a, b, c, d, e, f = m
    A, B, C, D, E, F = n
    return (a * A + b * D, a * B + b * E, a * C + b * F + c, d * A + e * D, d * B + e * E, d * C + e * F + f)


def translate(x, y):
    return (1.0, 0.0, x, 0.0, 1.0, y)


def scale(sx, sy=None):
    return (sx, 0.0, 0.0, 0.0, sx if sy is None else sy, 0.0)


def rotate(deg):
    """Clockwise on screen (y points down)."""
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return (c, -s, 0.0, s, c, 0.0)


def skew(kx_deg, ky_deg):
    return (1.0, math.tan(math.radians(kx_deg)), 0.0, math.tan(math.radians(ky_deg)), 1.0, 0.0)


def chain(*ms):
    out = IDENTITY
    for m in ms:
        out = mul(out, m)
    return out


def invert(m):
    a, b, c, d, e, f = m
    det = a * e - b * d
    if abs(det) < 1e-12:
        return None
    ia, ib, id_, ie = e / det, -b / det, -d / det, a / det
    return (ia, ib, -(ia * c + ib * f), id_, ie, -(id_ * c + ie * f))


def apply(m, x, y):
    a, b, c, d, e, f = m
    return a * x + b * y + c, d * x + e * y + f


def bbox(m, w, h):
    pts = [apply(m, x, y) for x, y in ((0, 0), (w, 0), (0, h), (w, h))]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


class Content:
    """A rendered layer image. `d` = image pixels per logical pixel; `box` = the logical box (bx, by, bw, bh) in image
    pixels that anchors and sizes refer to (padding for strokes/shadows lies outside it)."""

    __slots__ = ("img", "d", "box", "_pm")

    def __init__(self, img, d=1.0, box=None):
        self.img = img
        self.d = d
        self.box = box or (0, 0, img.width, img.height)
        self._pm = None

    @property
    def logical_size(self):
        return self.box[2] / self.d, self.box[3] / self.d

    def premultiplied(self):
        if self._pm is None:
            self._pm = self.img.convert("RGBa")
        return self._pm


def _opacity(img, o):
    if o >= 0.999:
        return img
    a = img.getchannel("A").point(lambda v: int(v * o + 0.5))
    img.putalpha(a)
    return img


_FAST_BLEND = {"multiply": ImageChops.multiply, "screen": ImageChops.screen, "add": ImageChops.add,
               "difference": ImageChops.difference, "darken": ImageChops.darker, "lighten": ImageChops.lighter,
               "overlay": ImageChops.overlay, "soft_light": ImageChops.soft_light}


def _blend(canvas, img, x0, y0, mode):
    region = canvas.crop((x0, y0, x0 + img.width, y0 + img.height))
    if region.getchannel("A").getextrema()[0] == 255 and mode in _FAST_BLEND:
        # opaque canvas (the usual case): C implementation, masked by the layer's alpha
        mixed = _FAST_BLEND[mode](region.convert("RGB"), img.convert("RGB")).convert("RGBA")
        canvas.paste(Image.composite(mixed, region, img.getchannel("A")), (x0, y0))
        return
    base = np.asarray(region, dtype=np.float32) / 255.0
    top = np.asarray(img, dtype=np.float32) / 255.0
    cb, ab = base[..., :3], base[..., 3:4]
    cs, as_ = top[..., :3], top[..., 3:4]
    if mode == "multiply":
        mix = cb * cs
    elif mode == "screen":
        mix = 1 - (1 - cb) * (1 - cs)
    elif mode == "add":
        mix = np.minimum(1.0, cb + cs)
    elif mode == "overlay":
        mix = np.where(cb < 0.5, 2 * cb * cs, 1 - 2 * (1 - cb) * (1 - cs))
    elif mode == "soft_light":
        mix = (1 - 2 * cs) * cb * cb + 2 * cs * cb
    elif mode == "difference":
        mix = np.abs(cb - cs)
    elif mode == "darken":
        mix = np.minimum(cb, cs)
    elif mode == "lighten":
        mix = np.maximum(cb, cs)
    else:
        mix = cs
    mix = cs * (1 - ab) + mix * ab  # where the canvas is empty the layer shows as is
    out_rgb = cb * (1 - as_) + mix * as_
    out_a = ab + as_ * (1 - ab)
    out = np.concatenate([out_rgb, out_a], axis=-1)
    canvas.paste(Image.fromarray((out * 255 + 0.5).astype(np.uint8), "RGBA"), (x0, y0))


def draw(canvas, content, m, opacity=1.0, blend="normal", fast=False):
    """Composite `content` onto `canvas` (RGBA) through matrix `m` (content pixels → canvas pixels).
    Returns the canvas-space bbox drawn, or None."""
    if opacity <= 0.002:
        return None
    img = content.img
    w, h = img.size
    if w == 0 or h == 0:
        return None
    a, b, c, d, e, f = m
    W, H = canvas.size
    x0, y0, x1, y1 = bbox(m, w, h)
    ix0, iy0 = max(0, int(math.floor(x0))), max(0, int(math.floor(y0)))
    ix1, iy1 = min(W, int(math.ceil(x1))), min(H, int(math.ceil(y1)))
    if ix1 <= ix0 or iy1 <= iy0:
        return None
    # Pure translation: paste without resampling (keeps text crisp).
    if abs(a - 1) < 1e-6 and abs(e - 1) < 1e-6 and abs(b) < 1e-6 and abs(d) < 1e-6:
        tx, ty = int(round(c)), int(round(f))
        sx0, sy0 = max(0, -tx), max(0, -ty)
        sx1, sy1 = min(w, W - tx), min(h, H - ty)
        if sx1 <= sx0 or sy1 <= sy0:
            return None
        piece = img.crop((sx0, sy0, sx1, sy1)) if (sx0, sy0, sx1, sy1) != (0, 0, w, h) else img
        if opacity < 0.999:
            piece = _opacity(piece.copy(), opacity)
        if blend != "normal":
            _blend(canvas, piece, tx + sx0, ty + sy0, blend)
        else:
            canvas.alpha_composite(piece, (tx + sx0, ty + sy0))
        return (tx + sx0, ty + sy0, tx + sx1, ty + sy1)
    src = content.premultiplied()
    # Strong downscale: pre-shrink with a good filter so the affine sample does not alias.
    kx, ky = math.hypot(a, d), math.hypot(b, e)
    if (kx < 0.6 or ky < 0.6) and w > 4 and h > 4:
        nw, nh = max(1, int(round(w * min(1.0, kx * 1.15)))), max(1, int(round(h * min(1.0, ky * 1.15))))
        if (nw, nh) != (w, h):
            src = src.resize((nw, nh), BILINEAR if fast else LANCZOS, reducing_gap=None if fast else 2.0)
            m = mul(m, scale(w / nw, h / nh))
    inv = invert(m)
    if inv is None:
        return None
    A, B, C, D, E, F = inv
    data = (A, B, A * ix0 + B * iy0 + C, D, E, D * ix0 + E * iy0 + F)
    kx, ky = math.hypot(m[0], m[3]), math.hypot(m[1], m[4])
    near_one = 0.85 < kx < 1.2 and 0.85 < ky < 1.2
    out = src.transform((ix1 - ix0, iy1 - iy0), Image.Transform.AFFINE, data,
                        resample=BILINEAR if (fast or near_one) else BICUBIC).convert("RGBA")
    if opacity < 0.999:
        out = _opacity(out, opacity)
    if blend != "normal":
        _blend(canvas, out, ix0, iy0, blend)
    else:
        canvas.alpha_composite(out, (ix0, iy0))
    return (ix0, iy0, ix1, iy1)


# --- fills ------------------------------------------------------------------------------------------------------------

def gradient(w, h, spec, where="gradient"):
    """spec: {"colors": [...], "angle": deg} (linear, 90 = top→bottom) or {"colors": [...], "radial": true}."""
    w, h = max(1, int(w)), max(1, int(h))
    cols = [parse_color(c, where) for c in spec.get("colors", ["#000", "#fff"])]
    stops = spec.get("stops") or [i / (len(cols) - 1) for i in range(len(cols))] if len(cols) > 1 else [0.0]
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    if spec.get("radial"):
        cx, cy = spec.get("center", [0.5, 0.5])
        r = math.hypot(max(cx, 1 - cx) * w, max(cy, 1 - cy) * h)
        t = np.sqrt((xs - cx * w) ** 2 + (ys - cy * h) ** 2) / max(r, 1)
    else:
        ang = math.radians(float(spec.get("angle", 90)))
        dx, dy = math.cos(ang), math.sin(ang)
        proj = (xs - w / 2) * dx + (ys - h / 2) * dy
        half = abs(w / 2 * dx) + abs(h / 2 * dy)
        t = proj / max(half * 2, 1) + 0.5
    t = np.clip(t, 0, 1)
    out = np.zeros((h, w, 4), np.float32)
    arr = np.array(cols, np.float32)
    if len(cols) == 1:
        out[:] = arr[0]
    else:
        for ch in range(4):
            out[..., ch] = np.interp(t, stops, arr[:, ch])
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def fill_image(w, h, fill, where="fill"):
    if isinstance(fill, dict):
        return gradient(w, h, fill, where)
    return Image.new("RGBA", (max(1, int(w)), max(1, int(h))), parse_color(fill, where))


def fill_mask(mask, fill, where="fill"):
    """Paint an 'L' mask with a color or gradient."""
    img = fill_image(mask.width, mask.height, fill, where)
    a = ImageChops.multiply(img.getchannel("A"), mask)
    img.putalpha(a)
    return img


# --- effects on content -----------------------------------------------------------------------------------------------

def add_shadow(content, spec, where="shadow", glow=False):
    """Drop shadow (or glow) behind content. spec: {"color","opacity","blur","dx","dy","spread"} in logical px."""
    if spec is True:
        spec = {}
    if not spec:
        return content
    d = content.d
    col = parse_color(spec.get("color", "#ffffff" if glow else "#000000"), where + ".color")
    op = float(spec.get("opacity", 0.9 if glow else 0.45))
    blur = float(spec.get("blur", 24 if glow else 18)) * d
    dx = 0.0 if glow else float(spec.get("dx", 0)) * d
    dy = 0.0 if glow else float(spec.get("dy", 10)) * d
    spread = float(spec.get("spread", 0)) * d
    pad = int(math.ceil(blur * 2 + spread + max(abs(dx), abs(dy)))) + 2
    img = content.img
    W, H = img.width + pad * 2, img.height + pad * 2
    alpha = Image.new("L", (W, H), 0)
    alpha.paste(img.getchannel("A"), (pad + int(round(dx)), pad + int(round(dy))))
    if spread > 0:
        alpha = alpha.filter(ImageFilter.MaxFilter(int(spread) * 2 + 1))
    if blur > 0:
        alpha = alpha.filter(ImageFilter.GaussianBlur(blur / 2))
    alpha = alpha.point(lambda v: int(v * op))
    if glow:
        alpha = ImageChops.add(alpha, alpha.point(lambda v: v // 2))
    shadow = Image.new("RGBA", (W, H), col[:3] + (0,))
    shadow.putalpha(alpha)
    shadow.alpha_composite(img, (pad, pad))
    bx, by, bw, bh = content.box
    return Content(shadow, d, (bx + pad, by + pad, bw, bh))


def pad_content(content, pad):
    if pad <= 0:
        return content
    img = Image.new("RGBA", (content.img.width + pad * 2, content.img.height + pad * 2), (0, 0, 0, 0))
    img.paste(content.img, (pad, pad))
    bx, by, bw, bh = content.box
    return Content(img, content.d, (bx + pad, by + pad, bw, bh))


def blur_content(content, radius_logical):
    r = radius_logical * content.d
    if r < 0.3:
        return content
    padded = pad_content(content, int(math.ceil(r * 2.2)))
    padded.img = padded.img.convert("RGBa").filter(ImageFilter.GaussianBlur(r)).convert("RGBA")
    return padded


def crop_content(content, l, r, t, b):
    """Hide fractions of the logical box from each side (used by wipes)."""
    if l <= 0 and r <= 0 and t <= 0 and b <= 0:
        return content
    bx, by, bw, bh = content.box
    img = content.img
    x0 = 0 if l <= 0 else bx + bw * min(1, l)
    x1 = img.width if r <= 0 else bx + bw * (1 - min(1, r))
    y0 = 0 if t <= 0 else by + bh * min(1, t)
    y1 = img.height if b <= 0 else by + bh * (1 - min(1, b))
    if x1 <= x0 or y1 <= y0:
        return Content(Image.new("RGBA", (1, 1), (0, 0, 0, 0)), content.d, (0, 0, 1, 1))
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rectangle((x0, y0, x1 - 1, y1 - 1), fill=255)
    out = img.copy()
    out.putalpha(ImageChops.multiply(img.getchannel("A"), mask))
    return Content(out, content.d, content.box)


def rounded_mask(size, radius, ss=2):
    w, h = size
    r = max(0, min(radius, min(w, h) / 2))
    big = Image.new("L", (w * ss, h * ss), 0)
    ImageDraw.Draw(big).rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), radius=r * ss, fill=255)
    return big.resize((w, h), LANCZOS)


def chroma_key(img, key="#FF00FF", tolerance=0.18, softness=0.12, despill=True):
    """Remove a solid key color with soft edges and color unmixing (good for Flow cutouts on magenta)."""
    arr = np.asarray(img.convert("RGBA"), dtype=np.float32) / 255.0
    rgb, a0 = arr[..., :3], arr[..., 3]
    k = np.array(parse_color(key)[:3], np.float32) / 255.0
    dist = np.sqrt(((rgb - k) ** 2).sum(-1)) / math.sqrt(3)
    alpha = np.clip((dist - tolerance) / max(softness, 1e-3), 0, 1)
    if despill:
        safe = np.maximum(alpha, 1e-3)[..., None]
        rgb = np.clip((rgb - k * (1 - alpha[..., None])) / safe, 0, 1)
        # suppress leftover key tint on edges
        kmax = k.argmax()
        others = [i for i in range(3) if k[i] < 0.5]
        if others and k[kmax] > 0.5:
            limit = rgb[..., others].max(-1)
            for i in range(3):
                if k[i] > 0.5:
                    rgb[..., i] = np.where(alpha < 0.98, np.minimum(rgb[..., i], np.maximum(limit, rgb[..., i] * alpha)), rgb[..., i])
    out = np.concatenate([rgb, (alpha * a0)[..., None]], -1)
    return Image.fromarray((out * 255 + 0.5).astype(np.uint8), "RGBA")


def autocrop(img, pad=4, threshold=8):
    a = np.asarray(img.getchannel("A"))
    ys, xs = np.nonzero(a > threshold)
    if len(xs) == 0:
        return img
    x0, x1 = max(0, xs.min() - pad), min(img.width, xs.max() + 1 + pad)
    y0, y1 = max(0, ys.min() - pad), min(img.height, ys.max() + 1 + pad)
    return img.crop((x0, y0, x1, y1))


def add_outline(content, spec, where="outline"):
    """Sticker-style border around the content's shape. spec: true, a color, or {"width": 10, "color": "#fff"} (logical px)."""
    if spec is True:
        spec = {}
    elif isinstance(spec, str):
        spec = {"color": spec}
    d = content.d
    wpx = max(1.0, float(spec.get("width", 10)) * d)
    col = parse_color(spec.get("color", "#ffffff"), where + ".color")
    pad = int(math.ceil(wpx)) + 2
    padded = pad_content(content, pad)
    a = padded.img.getchannel("A")
    grown = a.filter(ImageFilter.GaussianBlur(wpx / 2)).point(lambda v: 255 if v > 8 else int(v * 30))
    ring = Image.new("RGBA", padded.img.size, col[:3] + (0,))
    ring.putalpha(ImageChops.lighter(grown, a))
    ring.alpha_composite(padded.img)
    return Content(ring, d, padded.box)

"""Layers and timelines. A Timeline (a scene or a group) owns layers and resolves their cues to local seconds."""
import importlib.util
import math
import os
import random

from PIL import Image, ImageDraw, ImageEnhance, ImageOps

from . import anim, raster, text as textmod
from .media import VideoReader, load_image, probe
from .raster import Content, chain, rotate, scale, skew, translate
from .timing import norm_word, parse_cue
from .util import SpecError, clamp, color as parse_color, length, suggest, with_alpha

COMMON_KEYS = {
    "type", "id", "at", "until", "duration", "x", "y", "anchor", "scale", "scale_x", "scale_y", "rotation", "opacity",
    "blur", "skew_x", "skew_y", "crop_left", "crop_right", "crop_top", "crop_bottom", "offset_x", "offset_y", "enter",
    "exit", "loop", "animate", "z", "camera", "blend", "shadow", "glow", "sfx", "slot", "w", "h", "hidden", "note",
    "detail", "progress", "comment", "outline",
}
BLENDS = {"normal", "multiply", "screen", "add", "overlay", "soft_light", "difference", "darken", "lighten"}


class Timeline:
    """Scene or group time frame. `start_global` = where local 0 sits in the whole video."""

    def __init__(self, rc, start_global, duration, size, where, scene_id):
        self.rc, self.start_global, self.duration, self.size, self.where, self.scene_id = rc, start_global, duration, size, where, scene_id
        self.layers = []
        self.by_id = {}

    def add(self, layer):
        self.layers.append(layer)
        if layer.id:
            if layer.id in self.by_id:
                raise SpecError(layer.where, f"duplicate layer id '{layer.id}' in this scene/group")
            self.by_id[layer.id] = layer

    def local(self, value, where, rel_start=0.0, rel_end=None):
        """Cue → seconds on this timeline. Numbers count from rel_start; 'end' means rel_end (default: timeline end)."""
        kind, arg, off = parse_cue(value, where)
        if kind == "num":
            return rel_start + arg
        if kind == "abs":
            return arg - self.start_global + off
        if kind == "end":
            return (self.duration if rel_end is None else rel_end) + off
        if kind == "w":
            lead = 0.0 if arg.endswith(".end") else self.rc.cue_lead
            return self.rc.words.find(arg, after=self.start_global + max(0.0, rel_start) - 0.05, where=where) - self.start_global + off - lead
        if kind in ("b", "bar"):
            n = arg if kind == "b" else (arg - 1) * 4 + 1
            return self.rc.beats.nth(n, where) - self.start_global + off
        if kind == "nb":
            return self.rc.beats.after(self.start_global + max(0.0, rel_start), arg, where) - self.start_global + off
        ref = self.by_id.get(arg)
        if ref is None:
            raise SpecError(where, f"no layer with id '{arg}' here", suggest(arg, self.by_id) if self.by_id else "give that layer an \"id\"")
        ref.resolve_times()
        return (ref.start if kind == "with" else ref.end) + off

    def resolve(self):
        for layer in self.layers:
            layer.resolve_times()
        for layer in self.layers:
            layer.prepare()


class Props:
    __slots__ = ("x", "y", "sx", "sy", "rot", "skx", "sky", "opacity", "blur", "crop", "progress", "value", "lt", "D")


class Layer:
    KEYS = set()
    default_anchor = (0.5, 0.5)

    def __init__(self, spec, tl, where):
        self.spec, self.tl, self.rc, self.where = spec, tl, tl.rc, where
        self.type = spec.get("type")
        unknown = set(spec) - COMMON_KEYS - self.KEYS
        if unknown:
            k = sorted(unknown)[0]
            raise SpecError(where, f"unknown key '{k}' for a {self.type} layer", suggest(k, COMMON_KEYS | self.KEYS))
        self.id = spec.get("id")
        self.z = float(spec.get("z", 0))
        self.use_camera = spec.get("camera", True) is not False
        self.blend = spec.get("blend", "normal")
        if self.blend not in BLENDS:
            raise SpecError(where + ".blend", f"unknown blend '{self.blend}'", suggest(self.blend, BLENDS))
        self._times = None
        self._resolving = False
        self._cache = (None, None)
        W, H = tl.size
        self.slot = None
        if spec.get("slot"):
            s = self.rc.slots.get(spec["slot"])
            if s is None:
                raise SpecError(where + ".slot", f"unknown slot '{spec['slot']}'", suggest(spec["slot"], self.rc.slots))
            self.slot = s
        anchor = spec.get("anchor", self.default_anchor)
        if isinstance(anchor, str):
            names = {"center": (0.5, 0.5), "top": (0.5, 0), "bottom": (0.5, 1), "left": (0, 0.5), "right": (1, 0.5),
                     "top_left": (0, 0), "top_right": (1, 0), "bottom_left": (0, 1), "bottom_right": (1, 1)}
            if anchor not in names:
                raise SpecError(where + ".anchor", f"unknown anchor '{anchor}'", suggest(anchor, names))
            anchor = names[anchor]
        self.anchor = (float(anchor[0]), float(anchor[1]))
        sx, sy = (self.slot[0] + self.slot[2] / 2, self.slot[1] + self.slot[3] / 2) if self.slot else (W / 2, H / 2)
        self.base = {
            "x": length(spec.get("x"), W, where + ".x", W, H) if spec.get("x") is not None else sx,
            "y": length(spec.get("y"), H, where + ".y", W, H) if spec.get("y") is not None else sy,
            "scale": float(spec.get("scale", 1)), "scale_x": float(spec.get("scale_x", 1)), "scale_y": float(spec.get("scale_y", 1)),
            "rotation": float(spec.get("rotation", 0)), "opacity": float(spec.get("opacity", 1)), "blur": float(spec.get("blur", 0)),
            "skew_x": float(spec.get("skew_x", 0)), "skew_y": float(spec.get("skew_y", 0)),
            "crop_left": float(spec.get("crop_left", 0)), "crop_right": float(spec.get("crop_right", 0)),
            "crop_top": float(spec.get("crop_top", 0)), "crop_bottom": float(spec.get("crop_bottom", 0)),
            "offset_x": length(spec.get("offset_x", 0), W, where + ".offset_x", W, H),
            "offset_y": length(spec.get("offset_y", 0), H, where + ".offset_y", W, H),
            "progress": float(spec.get("progress", 1)), "value": 0.0,
        }
        self.enter = anim.Motion(spec["enter"], where + ".enter") if spec.get("enter") else None
        self.exit = anim.Motion(spec["exit"], where + ".exit", 0.4) if spec.get("exit") else None
        loops = spec.get("loop") or []
        if not isinstance(loops, list):
            loops = [loops]
        seed = abs(hash((tl.scene_id, self.id or where))) % 9973
        self.loops = [anim.Loop(l, f"{where}.loop[{i}]", seed + i * 31) for i, l in enumerate(loops)]
        self.tracks = {}
        self.sfx = spec.get("sfx")
        self.hidden = bool(spec.get("hidden", False))
        self.detail = float(spec.get("detail", 0) or 0)

    # --- timing ---------------------------------------------------------------------------------------------------
    def resolve_times(self):
        if self._times is not None:
            return
        if self._resolving:
            raise SpecError(self.where, "circular timing: layers refer to each other with with:/after:")
        self._resolving = True
        s = self.spec
        start = self.tl.local(s["at"], self.where + ".at") if s.get("at") is not None else 0.0
        if s.get("until") is not None:
            end = self.tl.local(s["until"], self.where + ".until", rel_start=0.0)
        elif s.get("duration") is not None:
            end = start + float(s["duration"])
        else:
            end = self.tl.duration
        if end <= start:
            raise SpecError(self.where, f"ends ({end:.2f}s) before it starts ({start:.2f}s)", "check at/until/duration")
        self._times = (start, end)
        self._resolving = False
        W, H = self.tl.size
        for prop, keys in (s.get("animate") or {}).items():
            name = anim.ALIASES.get(prop, prop)
            if name not in anim.ANIMATABLE:
                raise SpecError(f"{self.where}.animate", f"cannot animate '{prop}'", suggest(prop, anim.ANIMATABLE))
            ref = W if name in ("x", "offset_x") else H if name in ("y", "offset_y") else 1.0
            st, en = start, end
            self.tracks[name] = anim.Track(
                keys, f"{self.where}.animate.{prop}",
                lambda t, w, st=st, en=en: self.tl.local(t, w, rel_start=st, rel_end=en) - st,
                lambda v, w, ref=ref: length(v, ref, w, W, H) if name in ("x", "y", "offset_x", "offset_y") else float(v))

    @property
    def start(self):
        self.resolve_times()
        return self._times[0]

    @property
    def end(self):
        self.resolve_times()
        return self._times[1]

    def prepare(self):
        """Called after all times are known."""

    # --- properties -----------------------------------------------------------------------------------------------
    def props(self, t):
        if self.hidden or t < self.start - 1e-6 or t >= self.end - 1e-6:
            return None
        lt, D = t - self.start, self.end - self.start
        tr, b = self.tracks, self.base

        def v(name):
            k = tr.get(name)
            return k.value(lt) if k else b[name]
        m = anim.empty_mods()
        ctx = self.rc.anim_ctx
        if self.enter:
            anim.merge(m, self.enter.mods((lt - self.enter.delay) / self.enter.duration, ctx))
        if self.exit:
            begin = D - self.exit.duration - self.exit.delay
            if lt >= begin:
                anim.merge(m, self.exit.mods((lt - begin) / self.exit.duration, ctx, exiting=True))
        for lp in self.loops:
            anim.merge(m, lp.mods(lt, D, ctx))
        p = Props()
        p.lt, p.D = lt, D
        p.x = v("x") + v("offset_x") + m["dx"]
        p.y = v("y") + v("offset_y") + m["dy"]
        sc = v("scale") * m["scale"]
        p.sx, p.sy = sc * v("scale_x") * m["sx"], sc * v("scale_y") * m["sy"]
        p.rot = v("rotation") + m["rot"]
        p.skx, p.sky = v("skew_x") + m["skx"], v("skew_y") + m["sky"]
        p.opacity = clamp(v("opacity") * m["opacity"], 0.0, 1.0)
        p.blur = max(0.0, v("blur") + m["blur"])
        p.crop = (max(v("crop_left"), m["crop_l"]), max(v("crop_right"), m["crop_r"]),
                  max(v("crop_top"), m["crop_t"]), max(v("crop_bottom"), m["crop_b"]))
        p.progress = clamp(v("progress"), 0.0, 1.0)
        p.value = v("value")
        return p

    def density(self, dens):
        if self.detail:
            return dens * self.detail
        peak = abs(self.base["scale"])
        if "scale" in self.tracks:
            peak = max([peak] + [abs(k[1]) for k in self.tracks["scale"].keys])
        return dens * clamp(peak, 1.0, 3.0)

    # --- drawing --------------------------------------------------------------------------------------------------
    def content(self, p, d):
        raise NotImplementedError

    def cached(self, key, make):
        if self._cache[0] == key:
            return self._cache[1]
        c = make()
        self._cache = (key, c)
        return c

    def render(self, canvas, t, parent_m, dens):
        p = self.props(t)
        if p is None or p.opacity <= 0.002 or abs(p.sx) < 1e-4 or abs(p.sy) < 1e-4:
            return
        c = self.content(p, self.density(dens))
        if c is None:
            return
        if p.blur > 0.3:
            c = raster.blur_content(c, p.blur)
        if any(v > 0 for v in p.crop):
            c = raster.crop_content(c, *p.crop)
        bx, by, bw, bh = c.box
        lw, lh = bw / c.d, bh / c.d
        m = chain(parent_m, translate(p.x, p.y), rotate(p.rot), skew(p.skx, p.sky), scale(p.sx, p.sy),
                  translate(-self.anchor[0] * lw, -self.anchor[1] * lh), scale(1 / c.d), translate(-bx, -by))
        drawn = raster.draw(canvas, c, m, p.opacity, self.blend, self.rc.fast)
        if self.rc.collect is not None and drawn:
            self.rc.record(self, m, c, p)

    def effects(self, c):
        if self.spec.get("outline"):
            c = raster.add_outline(c, self.spec["outline"], self.where + ".outline")
        if self.spec.get("glow"):
            c = raster.add_shadow(c, self.spec["glow"], self.where + ".glow", glow=True)
        if self.spec.get("shadow"):
            c = raster.add_shadow(c, self.spec["shadow"], self.where + ".shadow")
        return c

    def box_size(self, natural_w, natural_h):
        """Logical box from w/h (or slot), keeping the aspect when only one is given."""
        W, H = self.tl.size
        w = length(self.spec.get("w"), W, self.where + ".w", W, H) if self.spec.get("w") is not None else None
        h = length(self.spec.get("h"), H, self.where + ".h", W, H) if self.spec.get("h") is not None else None
        if w is None and h is None and self.slot:
            w, h = self.slot[2], self.slot[3]
            return w, h, True
        if w is None and h is None:
            return float(natural_w), float(natural_h), False
        if w is None:
            w = h * natural_w / max(natural_h, 1)
        elif h is None:
            h = w * natural_h / max(natural_w, 1)
        return w, h, self.spec.get("w") is not None and self.spec.get("h") is not None


# --- media layers -----------------------------------------------------------------------------------------------------

def apply_filters(img, f, where):
    if not f:
        return img
    alpha = img.getchannel("A")
    rgb = img.convert("RGB")
    if f.get("grayscale"):
        g = ImageOps.grayscale(rgb).convert("RGB")
        rgb = Image.blend(rgb, g, float(f["grayscale"]))
    if f.get("sepia"):
        g = ImageOps.colorize(ImageOps.grayscale(rgb), "#2b1d0e", "#f3e3c3")
        rgb = Image.blend(rgb, g, float(f["sepia"]))
    for key, enh in (("brightness", ImageEnhance.Brightness), ("contrast", ImageEnhance.Contrast),
                     ("saturation", ImageEnhance.Color), ("sharpness", ImageEnhance.Sharpness)):
        if f.get(key) is not None:
            rgb = enh(rgb).enhance(float(f[key]))
    if f.get("tint"):
        tint = Image.new("RGB", rgb.size, parse_color(f["tint"], where + ".tint")[:3])
        rgb = Image.blend(rgb, Image.composite(tint, rgb, ImageOps.grayscale(rgb)), float(f.get("tint_amount", 0.35)))
    if f.get("invert"):
        rgb = ImageOps.invert(rgb)
    out = rgb.convert("RGBA")
    out.putalpha(alpha)
    return out


FILTER_KEYS = {"grayscale", "sepia", "brightness", "contrast", "saturation", "sharpness", "tint", "tint_amount", "invert"}


def _check_filters(f, where):
    if f is None:
        return
    if not isinstance(f, dict):
        raise SpecError(where, "filter must be an object like {\"grayscale\": 1, \"contrast\": 1.2}")
    bad = set(f) - FILTER_KEYS
    if bad:
        raise SpecError(where, f"unknown filter '{sorted(bad)[0]}'", suggest(sorted(bad)[0], FILTER_KEYS))


def _fit(img_w, img_h, box_w, box_h, mode):
    if mode == "cover":
        k = max(box_w / img_w, box_h / img_h)
    elif mode == "contain":
        k = min(box_w / img_w, box_h / img_h)
    else:
        return box_w, box_h
    return img_w * k, img_h * k


def speaking(rc, g, spans=None):
    """True while a voice word (or one of the given [start, end] spans, global seconds) is being spoken at g."""
    if spans is not None:
        return any(s0 <= g < s1 for s0, s1 in spans)
    for w in rc.words.words:
        if w["start"] <= g < w["end"]:
            return True
        if w["start"] > g:
            break
    return False


class ImageLayer(Layer):
    KEYS = {"src", "fit", "focus", "radius", "border", "key", "filter", "trim", "flip", "fps", "poses", "talk"}

    def __init__(self, spec, tl, where):
        super().__init__(spec, tl, where)
        if not spec.get("src"):
            raise SpecError(where, "image layer needs \"src\" (a file, or a list of files for a flipbook)")
        self.fit = spec.get("fit", "contain")
        if self.fit not in ("contain", "cover", "stretch"):
            raise SpecError(where + ".fit", f"bad fit '{self.fit}'", "contain, cover or stretch")
        _check_filters(spec.get("filter"), where + ".filter")
        key = spec.get("key")
        self.key = None if not key else {"color": "#FF00FF"} if key is True else {"color": key} if isinstance(key, str) else key
        frames = spec["src"] if isinstance(spec["src"], list) else [spec["src"]]
        self.frames = [self.rc.path(f, f"{where}.src") for f in frames]
        self.poses = []
        for i, ps in enumerate(spec.get("poses") or []):
            if not isinstance(ps, dict) or "src" not in ps or "at" not in ps:
                raise SpecError(f"{where}.poses[{i}]", "a pose is {\"at\": cue, \"src\": \"file.png\"} (src may be a list = flipbook)")
            srcs = ps["src"] if isinstance(ps["src"], list) else [ps["src"]]
            self.poses.append([ps["at"], [self.rc.path(f, f"{where}.poses[{i}].src") for f in srcs], f"{where}.poses[{i}].at"])
        talk = spec.get("talk")
        self.talk_open = None
        if talk:
            if not isinstance(talk, dict) or "open" not in talk:
                raise SpecError(where + ".talk", "talk is {\"open\": \"mouth_open.png\", \"fps\": 10, \"spans\": optional [[start, end], ...]}")
            self.talk_open = self.rc.path(talk["open"], where + ".talk.open")
            self.talk_fps = float(talk.get("fps", 10))
            self.talk_spans = talk.get("spans")
        self.multi = len(self.frames) > 1 or bool(self.poses) or bool(self.talk_open)
        self.trim = spec.get("trim", bool(self.key) and not self.multi)
        first = self._img(self.frames[0])
        nw, nh = first.size
        self.path = self.frames[0]
        self.bw, self.bh, has_box = self.box_size(nw, nh)
        if has_box and self.fit == "contain":
            self.bw, self.bh = _fit(nw, nh, self.bw, self.bh, "contain")
        self.cover = has_box and self.fit == "cover"
        self.fps = float(spec.get("fps", 8))

    def _img(self, path):
        return load_image(path, self.key, self.trim)

    def prepare(self):
        if not getattr(self, "_poses_resolved", False):
            for ps in self.poses:  # pose times count from the layer start, like keyframes
                ps[0] = self.tl.local(ps[0], ps[2], rel_start=self.start, rel_end=self.end) - self.start
            self.poses.sort(key=lambda ps: ps[0])
            self._poses_resolved = True
        if self.talk_open and self.talk_spans:
            self.talk_spans = [(self.tl.local(a, self.where + ".talk.spans") + self.tl.start_global,
                                self.tl.local(b, self.where + ".talk.spans") + self.tl.start_global) for a, b in self.talk_spans]

    def current(self, lt):
        frames = self.frames
        for at, srcs, _ in self.poses:
            if lt >= at:
                frames = srcs
        path = frames[int(lt * self.fps) % len(frames)] if len(frames) > 1 else frames[0]
        if self.talk_open:
            g = self.tl.start_global + self.start + lt
            if speaking(self.rc, g, self.talk_spans) and int(g * self.talk_fps) % 2 == 1:
                path = self.talk_open
        return path

    def content(self, p, d):
        path = self.current(p.lt) if self.multi else self.path
        return self.cached((path, round(d, 3)), lambda: self._make(path, d))

    def _make(self, path, d):
        src = self._img(path)
        tw, th = max(1, int(round(self.bw * d))), max(1, int(round(self.bh * d)))
        if self.cover:
            cw, ch = _fit(src.width, src.height, tw, th, "cover")
            img = src.resize((max(1, int(round(cw))), max(1, int(round(ch)))), raster.LANCZOS)
            fx, fy = self.spec.get("focus", [0.5, 0.5])
            x0, y0 = int((img.width - tw) * float(fx)), int((img.height - th) * float(fy))
            img = img.crop((x0, y0, x0 + tw, y0 + th))
        elif self.multi and self.fit != "stretch":
            # every frame/pose fits the same box, bottom-centered (characters keep their feet in place)
            fw, fh = _fit(src.width, src.height, tw, th, "contain")
            fw, fh = max(1, int(round(fw))), max(1, int(round(fh)))
            img = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
            img.paste(src.resize((fw, fh), raster.LANCZOS), ((tw - fw) // 2, th - fh))
        else:
            img = src.resize((tw, th), raster.LANCZOS) if (tw, th) != src.size else src.copy()
        if self.spec.get("flip"):
            img = ImageOps.mirror(img)
        img = apply_filters(img, self.spec.get("filter"), self.where + ".filter")
        img = _frame(img, self.spec, d, self.where)
        return self.effects(Content(img, d))


def _frame(img, spec, d, where):
    """Rounded corners and border."""
    r = spec.get("radius")
    if r:
        rr = length(r, min(img.size) / d, where + ".radius") * d
        img.putalpha(raster.ImageChops.multiply(img.getchannel("A"), raster.rounded_mask(img.size, rr)))
    b = spec.get("border")
    if b:
        b = b if isinstance(b, dict) else {"width": 6, "color": b}
        bw = float(b.get("width", 6)) * d
        rr = (length(r, min(img.size) / d, where + ".radius") * d) if r else 0
        ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(ov).rounded_rectangle((bw / 2, bw / 2, img.width - bw / 2 - 1, img.height - bw / 2 - 1), radius=max(0, rr - bw / 2),
                                             outline=parse_color(b.get("color", "#ffffff"), where + ".border.color"), width=max(1, int(round(bw))))
        img.alpha_composite(ov)
    return img


class VideoLayer(Layer):
    KEYS = {"src", "fit", "focus", "radius", "border", "key", "filter", "trim", "speed", "loop_video", "audio", "volume", "flip"}

    def __init__(self, spec, tl, where):
        super().__init__(spec, tl, where)
        if not spec.get("src"):
            raise SpecError(where, "video layer needs \"src\"")
        self.path = self.rc.path(spec["src"], where + ".src")
        info = probe(self.path)
        if not info.get("width"):
            raise SpecError(where + ".src", f"cannot read video {self.path}")
        self.info = info
        self.fit = spec.get("fit", "cover")
        _check_filters(spec.get("filter"), where + ".filter")
        trim = spec.get("trim") or [0, None]
        if not isinstance(trim, list) or len(trim) != 2:
            raise SpecError(where + ".trim", "trim must be [start, end] in seconds of the source (end may be null)")
        self.trim = (float(trim[0] or 0), None if trim[1] is None else float(trim[1]))
        self.speed = float(spec.get("speed", 1))
        self.bw, self.bh, has_box = self.box_size(info["width"], info["height"])
        if has_box and self.fit == "contain":
            self.bw, self.bh = _fit(info["width"], info["height"], self.bw, self.bh, "contain")
        self.reader = None

    def content(self, p, d):
        d = round(d, 3)
        if self.reader is None or self.reader.d != d:
            if self.reader:
                self.reader.close()
            tw, th = max(2, int(round(self.bw * d))), max(2, int(round(self.bh * d)))
            key = self.spec.get("key")
            self.reader = VideoReader(self.path, tw, th, self.rc.fps, self.trim, self.speed, self.fit,
                                      bool(self.spec.get("loop_video", True)), key, self.spec.get("focus"))
            self.reader.d = d
        frame = self.reader.frame(int(p.lt * self.rc.fps + 1e-6))
        if frame is None:
            return None
        if self.spec.get("flip"):
            frame = ImageOps.mirror(frame)
        frame = apply_filters(frame, self.spec.get("filter"), self.where + ".filter")
        frame = _frame(frame, self.spec, d, self.where)
        return self.effects(Content(frame, d))

    def close(self):
        if self.reader:
            self.reader.close()
            self.reader = None


# --- text -------------------------------------------------------------------------------------------------------------

STYLE_KEYS = {"font", "size", "weight", "color", "highlight", "highlight_color", "highlight_box", "stroke", "stroke_width",
              "stroke_color", "line_height", "letter_spacing", "align", "uppercase", "word_spacing"}


class TextLayer(Layer):
    KEYS = STYLE_KEYS | {"text", "max_width", "max_height", "max_lines", "min_size", "plate", "reveal"}

    def __init__(self, spec, tl, where):
        super().__init__(spec, tl, where)
        if self.type == "text" and spec.get("text") is None:
            raise SpecError(where, "text layer needs \"text\"")
        W, H = tl.size
        if "color" not in spec:
            spec = {**spec, "color": (self.rc.spec.get("theme") or {}).get("text", "#ffffff")}
            self.spec = spec
        self.style = textmod.Style(spec, where, self.rc.font_aliases, str(spec.get("text", "")) + str(spec.get("prefix", "")))
        mw = spec.get("max_width", spec.get("w"))
        self.max_w = length(mw, W, where + ".max_width", W, H) if mw is not None else (self.slot[2] if self.slot else W * 0.88)
        mh = spec.get("max_height", spec.get("h"))
        self.max_h = length(mh, H, where + ".max_height", W, H) if mh is not None else (self.slot[3] if self.slot else None)
        self.max_lines = spec.get("max_lines")
        self.reveal = spec.get("reveal")
        if self.reveal:
            if isinstance(self.reveal, str):
                self.reveal = {"preset": self.reveal}
            by = self.reveal.get("by", "word")
            if by not in ("word", "char", "line"):
                raise SpecError(where + ".reveal.by", f"bad unit '{by}'", "word, char or line")
            self.reveal_motion = anim.Motion({k: v for k, v in self.reveal.items() if k in ("preset", "duration", "ease", "distance", "from", "angle", "amount")} | {"preset": self.reveal.get("preset", "rise")},
                                             where + ".reveal", 0.45)
        self._lay = None

    def current_text(self, p):
        return str(self.spec.get("text", ""))

    def _layout(self, text, d):
        key = (text, round(d, 3))
        if self._lay and self._lay[0] == key:
            return self._lay[1]
        by = self.reveal.get("by", "word") if self.reveal else "word"
        lay = textmod.layout(textmod.parse_markup(text), self.style, self.max_w, self.max_h, self.max_lines,
                             self.spec.get("min_size"), d, by)
        sprites = [textmod.unit_sprite(u, lay, self.style, d) for u in lay.units]
        self._lay = (key, (lay, sprites))
        return lay, sprites

    def prepare(self):
        if not self.reveal:
            return
        # unit start times (layer-local)
        lay, _ = self._layout(self.current_text(None), 1.0)
        n = len(lay.units)
        stagger = float(self.reveal.get("stagger", 0.06 if self.reveal.get("by", "word") == "word" else 0.03))
        delay = float(self.reveal.get("delay", 0))
        order = self.reveal.get("order", "forward")
        idx = list(range(n))
        if order == "reverse":
            idx = idx[::-1]
        elif order == "random":
            random.Random(7).shuffle(idx)
        elif order == "center":
            c = (n - 1) / 2
            idx = sorted(idx, key=lambda i: abs(i - c))
        elif order != "forward":
            raise SpecError(self.where + ".reveal.order", f"bad order '{order}'", "forward, reverse, random or center")
        starts = [0.0] * n
        for rank, i in enumerate(idx):
            starts[i] = delay + rank * stagger
        if self.reveal.get("sync") in ("voice", True) and self.rc.words.words:
            # each word appears as it is spoken
            g = self.tl.start_global + self.start
            words = [w for w in self.rc.words.words if w["start"] >= g - 0.1]
            j = 0
            for i, u in enumerate(lay.units):
                key = norm_word(u["text"])
                for k in range(j, min(j + 6, len(words))):
                    if words[k]["key"] == key or (len(key) >= 3 and words[k]["key"].startswith(key[:4])):
                        starts[i] = words[k]["start"] - g
                        j = k + 1
                        break
        self.unit_starts = starts
        self.reveal_end = max(starts) + self.reveal_motion.duration if starts else 0

    def content(self, p, d):
        txt = self.current_text(p)
        animating = self.reveal and p.lt < self.reveal_end
        key = (txt, round(d, 3), "static" if not animating else round(p.lt, 4))
        return self.cached(key, lambda: self._make(txt, d, p if animating else None))

    def _make(self, txt, d, p):
        lay, sprites = self._layout(txt, d)
        st = self.style
        pad = int(lay.size * d * 0.5) + int(st.stroke * d) + 4
        plate = self.spec.get("plate")
        ppx = ppy = 0
        if plate:
            plate = plate if isinstance(plate, dict) else {"color": plate}
            pp = plate.get("padding", [0.45, 0.25])
            ppx, ppy = int(float(pp[0]) * lay.size * d), int(float(pp[1]) * lay.size * d)
        bw, bh = int(math.ceil(lay.width)) + ppx * 2, int(math.ceil(lay.height)) + ppy * 2
        img = Image.new("RGBA", (bw + pad * 2, bh + pad * 2), (0, 0, 0, 0))
        if plate:
            r = float(plate.get("radius", 0.25)) * lay.size * d
            pc = with_alpha(parse_color(plate.get("color", "#000000cc"), self.where + ".plate.color"), float(plate.get("opacity", 1)))
            border = plate.get("border")
            if border:
                border = border if isinstance(border, dict) else {"color": border}
                bwid = float(border.get("width", 6)) * d
                ImageDraw.Draw(img).rounded_rectangle((pad, pad, pad + bw - 1, pad + bh - 1), radius=r, fill=pc,
                                                      outline=parse_color(border.get("color", "#ffffff"), self.where + ".plate.border"),
                                                      width=max(1, int(round(bwid))))
            else:
                ImageDraw.Draw(img).rounded_rectangle((pad, pad, pad + bw - 1, pad + bh - 1), radius=r, fill=pc)
        ox, oy = pad + ppx, pad + ppy
        if p is None:
            for u, (sp, sx, sy) in zip(lay.units, sprites):
                img.alpha_composite(sp, (int(round(ox + u["x"] - sx)), int(round(oy + u["y"] - sy))))
        else:
            ctx = self.rc.anim_ctx
            for i, (u, (sp, sx, sy)) in enumerate(zip(lay.units, sprites)):
                raw = (p.lt - self.unit_starts[min(i, len(self.unit_starts) - 1)]) / self.reveal_motion.duration
                if raw <= 0 and self.reveal_motion.name != "none":
                    mods = self.reveal_motion.mods(0, ctx)
                    if mods.get("opacity", 1) <= 0.01 or mods.get("scale", 1) <= 0.01:
                        continue
                m = anim.merge(anim.empty_mods(), self.reveal_motion.mods(raw, ctx))
                if m["opacity"] <= 0.01:
                    continue
                cx, cy = ox + u["x"] + u["w"] / 2, oy + u["y"] + u["h"] / 2
                k = m["scale"]
                mat = chain(translate(cx + m["dx"] * d, cy + m["dy"] * d), rotate(m["rot"]), skew(m["skx"], 0),
                            scale(k * m["sx"], k * m["sy"]), translate(-(u["w"] / 2 + sx), -(u["h"] / 2 + sy)))
                c = Content(sp)
                if m["blur"] > 0.3:
                    c = raster.blur_content(c, m["blur"] * d)
                    mat = chain(mat, translate(-(c.box[0]), -(c.box[1])))
                if any(m[k2] > 0 for k2 in ("crop_l", "crop_r", "crop_t", "crop_b")):
                    c = raster.crop_content(c, m["crop_l"], m["crop_r"], m["crop_t"], m["crop_b"])
                raster.draw(img, c, mat, m["opacity"], "normal", self.rc.fast)
        return self.effects(Content(img, d, (pad, pad, bw, bh)))


class CounterLayer(TextLayer):
    KEYS = TextLayer.KEYS | {"from", "to", "format", "prefix", "suffix", "count"}

    def __init__(self, spec, tl, where):
        spec = dict(spec)
        spec.setdefault("text", "")
        super().__init__(spec, tl, where)
        self.v0, self.v1 = float(spec.get("from", 0)), float(spec.get("to", 100))
        self.fmt = spec.get("format", "{:,.0f}")
        try:
            self.fmt.format(1.5)
        except (ValueError, IndexError, KeyError):
            raise SpecError(where + ".format", f"bad number format {self.fmt!r}", "examples: \"{:,.0f}\", \"{:.1f}\", \"{:.0%}\"")
        c = spec.get("count") or {}
        self.count = anim.Motion({"preset": "none", "duration": c.get("duration", 1.6), "delay": c.get("delay", 0)}, where + ".count")
        self.count_ease = c.get("ease", "out_expo")

    def current_text(self, p):
        if p is None:
            v = self.v1
        elif "value" in self.tracks:
            v = p.value
        else:
            from . import easing
            u = (p.lt - self.count.delay) / self.count.duration
            v = self.v0 + (self.v1 - self.v0) * easing.apply(self.count_ease, u)
        return f"{self.spec.get('prefix', '')}{self.fmt.format(v)}{self.spec.get('suffix', '')}"


# --- groups -----------------------------------------------------------------------------------------------------------

class GroupLayer(Layer):
    KEYS = {"layers", "mask", "mask_invert", "clip"}
    default_anchor = (0.5, 0.5)

    def __init__(self, spec, tl, where):
        super().__init__(spec, tl, where)
        W, H = tl.size
        self.gw = length(spec.get("w"), W, where + ".w", W, H) if spec.get("w") is not None else (self.slot[2] if self.slot else W)
        self.gh = length(spec.get("h"), H, where + ".h", W, H) if spec.get("h") is not None else (self.slot[3] if self.slot else H)
        if not isinstance(spec.get("layers"), list):
            raise SpecError(where, "group needs \"layers\": [...]")
        self.child_specs = spec["layers"]
        self.inner = None
        self.mask = None

    def resolve_times(self):
        first = self._times is None
        super().resolve_times()
        if first and self.inner is None:
            self.inner = Timeline(self.rc, self.tl.start_global + self.start, self.end - self.start, (self.gw, self.gh), self.where, self.tl.scene_id)
            for i, cs in enumerate(self.child_specs):
                self.inner.add(make_layer(cs, self.inner, f"{self.where}.layers[{i}]"))
            if self.spec.get("mask"):
                self.mask = make_layer(self.spec["mask"], self.inner, f"{self.where}.mask")
            self.inner.resolve()
            if self.mask:
                self.mask.resolve_times()
                self.mask.prepare()

    def content(self, p, d):
        # children may overflow the group box (shadows, overshoot, long text) unless "clip": true
        m = 0 if self.spec.get("clip") else int(math.ceil(max(self.gw, self.gh) * 0.3 * d))
        gw, gh = max(1, int(math.ceil(self.gw * d))) + 2 * m, max(1, int(math.ceil(self.gh * d))) + 2 * m
        img = Image.new("RGBA", (gw, gh), (0, 0, 0, 0))
        base = chain(translate(m, m), scale(d))
        collect, self.rc.collect = self.rc.collect, None  # children are reported as part of the group
        for layer in sorted(self.inner.layers, key=lambda l: l.z):
            layer.render(img, p.lt, base, d)
        mimg = None
        if self.mask:
            mimg = Image.new("RGBA", (gw, gh), (0, 0, 0, 0))
            self.mask.render(mimg, p.lt, base, d)
        self.rc.collect = collect
        if mimg is not None:
            ma = mimg.getchannel("A")
            if self.spec.get("mask_invert"):
                ma = ImageOps.invert(ma)
            img.putalpha(raster.ImageChops.multiply(img.getchannel("A"), ma))
        return self.effects(Content(img, d, (m, m, gw - 2 * m, gh - 2 * m)))

    def density(self, dens):
        return dens * (self.detail or 1.0)

    def close(self):
        for layer in self.inner.layers if self.inner else []:
            if hasattr(layer, "close"):
                layer.close()


# --- custom python layer ----------------------------------------------------------------------------------------------

class CustomCtx:
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def ease(self, name, t):
        from . import easing
        return easing.apply(name, t)

    def color(self, value):
        return parse_color(value)


_modules = {}


class CustomLayer(Layer):
    KEYS = {"script", "params"}

    def __init__(self, spec, tl, where):
        super().__init__(spec, tl, where)
        if not spec.get("script"):
            raise SpecError(where, "custom layer needs \"script\": \"fx/my_effect.py\" with def render(ctx)")
        self.path = self.rc.path(spec["script"], where + ".script")
        W, H = tl.size
        self.bw = length(spec.get("w"), W, where + ".w", W, H) if spec.get("w") is not None else (self.slot[2] if self.slot else W)
        self.bh = length(spec.get("h"), H, where + ".h", W, H) if spec.get("h") is not None else (self.slot[3] if self.slot else H)
        key = (self.path, os.path.getmtime(self.path))
        mod = _modules.get(key)
        if mod is None:
            ms = importlib.util.spec_from_file_location(f"vs_custom_{abs(hash(key))}", self.path)
            mod = importlib.util.module_from_spec(ms)
            try:
                ms.loader.exec_module(mod)
            except Exception as e:
                raise SpecError(where + ".script", f"{os.path.basename(self.path)} failed to load: {type(e).__name__}: {e}")
            if not hasattr(mod, "render"):
                raise SpecError(where + ".script", f"{os.path.basename(self.path)} has no render(ctx) function")
            _modules[key] = mod
        self.mod = mod

    def content(self, p, d):
        import numpy as np
        w, h = max(1, int(round(self.bw * d))), max(1, int(round(self.bh * d)))
        ctx = CustomCtx(t=p.lt, duration=p.D, progress=p.lt / max(p.D, 1e-6), w=w, h=h, d=d, fps=self.rc.fps,
                        frame=int(p.lt * self.rc.fps + 1e-6), params=self.spec.get("params", {}), value=p.value,
                        Image=Image, ImageDraw=ImageDraw, np=np, global_t=self.tl.start_global + self.start + p.lt,
                        words=self.rc.words.words, fast=self.rc.fast, project_dir=self.rc.project_dir)
        try:
            img = self.mod.render(ctx)
        except Exception as e:
            raise SpecError(self.where + ".script", f"render() raised {type(e).__name__}: {e} at t={p.lt:.2f}s")
        if img is None:
            return None
        if not isinstance(img, Image.Image):
            raise SpecError(self.where + ".script", "render(ctx) must return a PIL Image (RGBA) of size (ctx.w, ctx.h)")
        img = img.convert("RGBA")
        return self.effects(Content(img, d, (0, 0, img.width, img.height)))

    def density(self, dens):
        return dens * (self.detail or 1.0)


def make_layer(spec, tl, where):
    from .shapes import ShapeLayer, ChartLayer
    from .particles import ParticlesLayer
    from .stickman import StickmanLayer
    from .textures import TextureLayer
    if not isinstance(spec, dict):
        raise SpecError(where, "a layer must be an object with a \"type\"")
    kinds = {"image": ImageLayer, "video": VideoLayer, "text": TextLayer, "counter": CounterLayer, "group": GroupLayer,
             "shape": ShapeLayer, "chart": ChartLayer, "particles": ParticlesLayer, "custom": CustomLayer,
             "stickman": StickmanLayer, "texture": TextureLayer}
    t = spec.get("type")
    if t not in kinds:
        raise SpecError(where, f"unknown layer type {t!r}", suggest(t, kinds))
    return kinds[t](spec, tl, where)

"""Render context, scene timing plan, camera, backgrounds, color grade, and the per-frame scene renderer."""
import json
import math
import os

from PIL import Image

from . import anim, easing, raster, text as textmod
from .captions import KEYS as CAPTION_KEYS, CaptionsLayer, build_chunks
from .layers import Timeline, make_layer
from .raster import chain, rotate, scale, translate
from .spec import layout_slots, slots as make_slots
from .timing import Words, load_words, parse_cue
from .util import NAMED_COLORS, SpecError, color as parse_color, suggest

TRANSITIONS = {
    "cut": None, "fade": "fade", "dissolve": "dissolve", "dip": "fadeblack", "dip_black": "fadeblack", "dip_white": "fadewhite",
    "flash": "fadewhite", "slide_left": "slideleft", "slide_right": "slideright", "slide_up": "slideup", "slide_down": "slidedown",
    "cover_left": "coverleft", "cover_right": "coverright", "cover_up": "coverup", "cover_down": "coverdown",
    "reveal_left": "revealleft", "reveal_right": "revealright", "reveal_up": "revealup", "reveal_down": "revealdown",
    "wipe_left": "wipeleft", "wipe_right": "wiperight", "wipe_up": "wipeup", "wipe_down": "wipedown",
    "whip_left": "smoothleft", "whip_right": "smoothright", "whip_up": "smoothup", "whip_down": "smoothdown",
    "circle": "circleopen", "iris": "circleopen", "iris_close": "circleclose", "zoom": "zoomin", "radial": "radial",
    "pixelize": "pixelize", "glitch": "pixelize", "blur": "hblur", "squeeze": "squeezeh", "squeeze_v": "squeezev",
    "diagonal": "diagtl", "blinds": "hlslice", "blinds_v": "vuslice", "distance": "distance", "fade_grays": "fadegrays",
}
DEFAULT_TRANSITION_DUR = {"flash": 0.3, "whip_left": 0.3, "whip_right": 0.3, "whip_up": 0.3, "whip_down": 0.3, "glitch": 0.25, "pixelize": 0.4}
LOOK_KEYS = {"contrast", "brightness", "saturation", "gamma", "vignette", "grain", "letterbox", "warmth", "sharpen",
             "pixelate", "scanlines", "rgb_shift", "mono", "sepia", "bloom", "posterize", "crt", "vhs", "blur"}
CAMERA_PRESETS = {"still", "push_in", "pull_out", "pan_left", "pan_right", "pan_up", "pan_down", "rise", "drift", "handheld", "slow_push"}
CAMERA_KEYS = {"preset", "amount", "ease", "animate", "shake", "punches"}


class RenderContext:
    def __init__(self, spec, project_dir, q=1.0, fps=None, fast=False):
        self.spec, self.project_dir, self.q, self.fast = spec, project_dir, float(q), fast
        self.W, self.H = spec["width"], spec["height"]
        self.fps = float(fps or spec["fps"])
        self.anim_ctx = {"W": self.W, "H": self.H, "unit": min(self.W, self.H) / 1080.0}
        self.font_aliases = spec.get("fonts") or {}
        textmod.set_font_dirs([os.path.join(project_dir, "fonts")] + [self.abspath(p) for p in spec.get("font_dirs", [])])
        self.slots = make_slots(self.W, self.H, spec.get("slots"))
        voice = (spec.get("audio") or {}).get("voice") or {}
        words = []
        if voice.get("words"):
            words = load_words(self.path(voice["words"], "audio.voice.words"))
            off = float(voice.get("start", 0))
            for w in words:
                w["start"] += off
                w["end"] += off
        self.words = Words(words)
        self.cue_lead = float(spec.get("cue_lead", 0.0))
        from .audio import beat_grid
        from .timing import Beats
        bpm, beats = beat_grid((spec.get("audio") or {}).get("music"), self)
        self.beats = Beats(beats, bpm)
        self.alpha = bool((spec.get("output") or {}).get("alpha")) if isinstance(spec.get("output"), dict) else False
        self.collect = None
        self.records = []
        self.current_scene = None

    def abspath(self, p):
        return p if os.path.isabs(p) else os.path.join(self.project_dir, p)

    def path(self, src, where):
        src = os.path.expanduser(str(src))
        for cand in (src if os.path.isabs(src) else None, os.path.join(self.project_dir, src), os.path.join(self.project_dir, "assets", src)):
            if cand and os.path.exists(cand):
                return os.path.abspath(cand)
        near = []
        for root in (self.project_dir, os.path.join(self.project_dir, "assets")):
            if os.path.isdir(root):
                near += [os.path.relpath(os.path.join(dp, f), self.project_dir) for dp, _, fs in os.walk(root) for f in fs][:400]
        raise SpecError(where, f"file not found: {src}", suggest(src, near) if near else "put files next to the JSON or in assets/")

    def record(self, layer, m, c, p):
        bx, by, bw, bh = c.box
        pts = [raster.apply(m, x, y) for x, y in ((bx, by), (bx + bw, by), (bx, by + bh), (bx + bw, by + bh))]
        q = self.q
        box = (min(x for x, _ in pts) / q, min(y for _, y in pts) / q, max(x for x, _ in pts) / q, max(y for _, y in pts) / q)
        label = layer.id or f"{layer.type} {layer.where.split('.')[-1]}" + (f" \"{str(layer.spec.get('text'))[:24]}\"" if layer.spec.get("text") else "")
        self.collect.append({"id": label, "type": layer.type, "where": layer.where,
                             "bbox": box, "opacity": p.opacity, "text": layer.spec.get("text") if layer.type in ("text",) else None})


def transition_of(value, where):
    if value is None:
        return ("cut", 0.0)
    if isinstance(value, str):
        value = {"type": value}
    if not isinstance(value, dict) or "type" not in value:
        raise SpecError(where, "transition is a name or {\"type\": \"fade\", \"duration\": 0.5}")
    name = value["type"]
    if isinstance(name, str) and name.startswith("xfade:"):
        return (name, float(value.get("duration", 0.5)))
    if name not in TRANSITIONS:
        raise SpecError(where, f"unknown transition '{name}'", suggest(name, TRANSITIONS))
    if name == "cut":
        return ("cut", 0.0)
    return (name, float(value.get("duration", DEFAULT_TRANSITION_DUR.get(name, 0.5))))


def plan(spec, rc):
    """Scene start times and durations in the whole video. Transitions overlap the end of the previous scene."""
    out, prev_end = [], 0.0
    default_tr = spec.get("transition")
    for i, s in enumerate(spec["scenes"]):
        where = f"scenes[{i}]({s['id']})"
        tr = transition_of(s.get("transition", default_tr) if i else None, where + ".transition")
        if rc.alpha:
            tr = ("cut", 0.0)  # transparent output joins scenes with cuts
        start = max(0.0, prev_end - tr[1])
        if s.get("duration") is not None:
            dur = float(s["duration"])
        elif s.get("until") is not None:
            kind, arg, off = parse_cue(s["until"], where + ".until")
            if kind == "w":
                end = rc.words.find(arg, after=start, where=where + ".until") + off
            elif kind == "abs":
                end = arg + off
            elif kind == "num":
                end = start + arg
            elif kind in ("b", "bar"):
                end = rc.beats.nth(arg if kind == "b" else (arg - 1) * 4 + 1, where + ".until") + off
            elif kind == "nb":
                end = rc.beats.after(start + 0.05, arg, where + ".until") + off
            else:
                raise SpecError(where + ".until", "scene 'until' must be a word cue ('w:word.end+0.3'), a beat ('b:16', 'nb:4'), '@seconds' or seconds")
            dur = end - start
        elif i == len(spec["scenes"]) - 1 and rc.words.words:
            dur = rc.words.end + 0.8 - start
        else:
            raise SpecError(where, "scene needs \"duration\" (seconds) or \"until\" (e.g. \"w:word.end+0.3\")")
        if dur <= 0.05:
            raise SpecError(where, f"scene duration {dur:.2f}s is too short", "check its until/duration cue")
        if i and tr[1] >= min(dur, out[-1]["duration"]):
            raise SpecError(where + ".transition", f"transition {tr[1]}s is longer than a scene it joins")
        out.append({"id": s["id"], "index": i, "start": start, "duration": dur, "transition": tr})
        prev_end = start + dur
    return out, prev_end


class Camera:
    def __init__(self, spec, tl, rc, where):
        self.rc, self.tl = rc, tl
        if spec is None or spec == "still":
            spec = {"preset": "still"}
        if isinstance(spec, str):
            spec = {"preset": spec}
        if not isinstance(spec, dict):
            raise SpecError(where, "camera is a preset name or an object")
        bad = set(spec) - CAMERA_KEYS
        if bad:
            raise SpecError(where, f"unknown camera key '{sorted(bad)[0]}'", suggest(sorted(bad)[0], CAMERA_KEYS))
        self.preset = spec.get("preset", "still")
        if self.preset not in CAMERA_PRESETS:
            raise SpecError(where + ".preset", f"unknown camera '{self.preset}'", suggest(self.preset, CAMERA_PRESETS))
        self.amount = float(spec.get("amount", 1.0))
        self.ease = spec.get("ease", "in_out_sine")
        easing.get(self.ease, where + ".ease")
        self.tracks = {}
        W, H = rc.W, rc.H
        for prop, keys in (spec.get("animate") or {}).items():
            if prop not in ("zoom", "x", "y", "rotation"):
                raise SpecError(where + ".animate", f"camera cannot animate '{prop}'", "zoom, x, y or rotation")
            from .util import length
            self.tracks[prop] = anim.Track(keys, f"{where}.animate.{prop}", lambda t, w: tl.local(t, w),
                                           lambda v, w, p=prop: length(v, W if p == "x" else H, w) if p in ("x", "y") else float(v))
        self.shake = spec.get("shake")
        if self.shake:
            sh = self.shake if isinstance(self.shake, dict) else {}
            self.shake_amp = float(sh.get("amp", 10)) * rc.anim_ctx["unit"]
            self.shake_freq = float(sh.get("freq", 14))
            self.shake_from = tl.local(sh["at"], where + ".shake.at") if sh.get("at") is not None else 0.0
            self.shake_until = tl.local(sh["until"], where + ".shake.until") if sh.get("until") is not None else tl.duration
        self.punches = []
        for i, pu in enumerate(spec.get("punches") or []):
            if not isinstance(pu, dict) or "at" not in pu:
                raise SpecError(f"{where}.punches[{i}]", "a punch is {\"at\": cue, \"amount\": 0.06, \"duration\": 0.35}")
            self.punches.append((tl.local(pu["at"], f"{where}.punches[{i}].at"), float(pu.get("amount", 0.06)), float(pu.get("duration", 0.35))))

    def state(self, t):
        D = max(self.tl.duration, 1e-3)
        u = easing.apply(self.ease, t / D)
        W, H, a = self.rc.W, self.rc.H, self.amount
        z, x, y, r = 1.0, 0.0, 0.0, 0.0
        p = self.preset
        if p == "push_in":
            z = 1 + 0.12 * a * u
        elif p == "slow_push":
            z = 1 + 0.05 * a * u
        elif p == "pull_out":
            z = 1 + 0.12 * a * (1 - u)
        elif p in ("pan_left", "pan_right"):
            span = W * 0.05 * a
            z = 1 + 2 * span / W + 0.02
            x = span * (1 - 2 * u) * (1 if p == "pan_left" else -1)
        elif p in ("pan_up", "pan_down"):
            span = H * 0.04 * a
            z = 1 + 2 * span / H + 0.02
            y = span * (1 - 2 * u) * (1 if p == "pan_up" else -1)
        elif p == "rise":
            span = H * 0.03 * a
            z = 1.04 + 0.04 * a * u
            y = span * (1 - 2 * u)
        elif p == "drift":
            z = 1.04 + 0.03 * a * u
            x, y = W * 0.015 * a * (2 * u - 1), H * 0.01 * a * (1 - 2 * u)
        elif p == "handheld":
            z = 1.03
            un = self.rc.anim_ctx["unit"]
            x, y = anim._noise(3, t * 0.8) * 6 * un * a, anim._noise(9, t * 0.7) * 5 * un * a
            r = anim._noise(21, t * 0.5) * 0.35 * a
        if "zoom" in self.tracks:
            z = self.tracks["zoom"].value(t)
        if "x" in self.tracks:
            x = self.tracks["x"].value(t)
        if "y" in self.tracks:
            y = self.tracks["y"].value(t)
        if "rotation" in self.tracks:
            r = self.tracks["rotation"].value(t)
        if self.shake and self.shake_from <= t <= self.shake_until:
            x += anim._noise(41, t * self.shake_freq) * self.shake_amp
            y += anim._noise(57, t * self.shake_freq) * self.shake_amp
            z = max(z, 1 + 2 * self.shake_amp / min(W, H))
        for at, amt, dur in self.punches:
            if at <= t < at + dur:
                k = (t - at) / dur
                env = k / 0.2 if k < 0.2 else easing.apply("in_out_sine", (1 - k) / 0.8)
                z *= 1 + amt * env
        return z, x, y, r

    def matrix(self, t):
        z, x, y, r = self.state(t)
        if z == 1 and x == 0 and y == 0 and r == 0:
            return raster.IDENTITY
        W, H = self.rc.W, self.rc.H
        return chain(translate(W / 2, H / 2), rotate(r), scale(z), translate(-W / 2 - x, -H / 2 - y))


def look_filters(spec_look, where, q=1.0):
    if not spec_look:
        return []
    bad = set(spec_look) - LOOK_KEYS
    if bad:
        raise SpecError(where, f"unknown look key '{sorted(bad)[0]}'", suggest(sorted(bad)[0], LOOK_KEYS))
    spec_look = dict(spec_look)
    if spec_look.get("crt"):
        for k, v in (("scanlines", 0.35), ("rgb_shift", 2), ("vignette", 0.6), ("bloom", 0.3)):
            spec_look.setdefault(k, v)
    if spec_look.get("vhs"):
        for k, v in (("rgb_shift", 4), ("grain", 0.45), ("blur", 0.6), ("saturation", 1.25), ("scanlines", 0.15)):
            spec_look.setdefault(k, v)
    f = []
    if spec_look.get("pixelate"):
        n = max(2, int(round(float(spec_look["pixelate"]) * q)))
        f.append(f"scale=iw/{n}:ih/{n}:flags=neighbor,scale=iw*{n}:ih*{n}:flags=neighbor")
    if spec_look.get("posterize"):
        lv = max(2, int(spec_look["posterize"]))
        step = 256 // lv
        f.append(f"lutrgb=r='floor(val/{step})*{step}':g='floor(val/{step})*{step}':b='floor(val/{step})*{step}'")
    if spec_look.get("mono"):
        f.append("hue=s=0")
    if spec_look.get("sepia"):
        f.append("colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131")
    if spec_look.get("blur"):
        f.append(f"gblur=sigma={max(0.3, float(spec_look['blur']) * 2 * q):.2f}")
    eq = []
    for k in ("contrast", "brightness", "saturation", "gamma"):
        if spec_look.get(k) is not None:
            v = float(spec_look[k])
            eq.append(f"{k}={(v - 1) if k == 'brightness' else v:.3f}")  # brightness 1.0 = unchanged
    if eq:
        f.append("eq=" + ":".join(eq))
    if spec_look.get("warmth"):
        w = max(-1.0, min(1.0, float(spec_look["warmth"]))) * 0.18
        f.append(f"colorbalance=rs={w:.3f}:gs={w * 0.3:.3f}:bs={-w:.3f}:rm={w * 0.6:.3f}:bm={-w * 0.6:.3f}")
    if spec_look.get("sharpen"):
        f.append(f"unsharp=5:5:{float(spec_look['sharpen']):.2f}")
    if spec_look.get("vignette"):
        v = 0.5 if spec_look["vignette"] is True else float(spec_look["vignette"])
        f.append(f"vignette=angle={0.25 + 0.55 * max(0.0, min(1.0, v)):.3f}")
    if spec_look.get("grain"):
        g = max(0.0, min(1.0, float(spec_look["grain"])))
        f.append(f"noise=alls={int(4 + 36 * g)}:allf=t+u")
    if spec_look.get("rgb_shift"):
        px = max(1, int(round(float(spec_look["rgb_shift"]) * q)))
        f.append(f"rgbashift=rh={px}:bh=-{px}")
    if spec_look.get("bloom"):
        b = max(0.0, min(1.0, float(spec_look["bloom"])))
        f.append(f"split[a][b];[b]gblur=sigma={max(2, 18 * q):.1f}[bb];[a][bb]blend=all_mode=screen:all_opacity={0.25 + 0.5 * b:.2f}")
    if spec_look.get("scanlines"):
        o = 0.35 if spec_look["scanlines"] is True else max(0.05, min(0.9, float(spec_look["scanlines"])))
        step = max(2, int(round(4 * q)))
        f.append(f"drawgrid=w=iw+10:h={step}:t={max(1, step // 2)}:c=black@{o:.2f}")
    if spec_look.get("letterbox"):
        ratio = float(spec_look["letterbox"]) if spec_look["letterbox"] is not True else 2.39
        f.append(f"drawbox=x=0:y=0:w=iw:h=max(0\\,(ih-iw/{ratio})/2):color=black:t=fill,"
                 f"drawbox=x=0:y=ih-max(0\\,(ih-iw/{ratio})/2):w=iw:h=max(0\\,(ih-iw/{ratio})/2):color=black:t=fill")
    return f


def _is_color(v):
    return isinstance(v, (list, tuple)) or (isinstance(v, str) and (v.startswith("#") or v.lower() in NAMED_COLORS))


def background_layers(bg, where):
    """Turns a background into (fill color or None, [layer specs])."""
    if bg is None:
        return (0, 0, 0, 255), []
    if isinstance(bg, dict) and bg.get("texture"):
        extra = set(bg) - {"texture", "color", "ink", "scale", "seed", "motion"}
        if extra:
            raise SpecError(where, f"unknown texture key '{sorted(extra)[0]}'", "texture, color, ink, scale, seed, motion")
        layer = {"type": "texture", "kind": bg["texture"], "slot": "full", "z": -1000}
        for k in ("color", "ink", "seed"):
            if bg.get(k) is not None:
                layer[k] = bg[k]
        if bg.get("scale") is not None:
            layer["scale_pattern"] = bg["scale"]
        if bg.get("motion"):
            layer["loop"] = bg["motion"]
            # a rotating texture must cover the frame's diagonal at every angle
            spins = "spin" in json.dumps(bg["motion"]) or "orbit" in json.dumps(bg["motion"])
            layer["scale"] = 2.2 if spins else 1.15
        return (0, 0, 0, 255), [layer]
    if _is_color(bg):
        return parse_color(bg, where), []
    if isinstance(bg, str):
        return (0, 0, 0, 255), [{"type": "image", "src": bg, "slot": "full", "fit": "cover", "z": -1000, "loop": "ken_burns"}]
    if isinstance(bg, dict):
        if "colors" in bg or "gradient" in bg:
            g = bg.get("gradient", bg)
            return (0, 0, 0, 255), [{"type": "shape", "kind": "rect", "slot": "full", "fill": g, "z": -1000}]
        known = {"image", "video", "filter", "motion", "blur", "focus", "opacity", "color", "trim", "speed"}
        bad = set(bg) - known
        if bad:
            raise SpecError(where, f"unknown background key '{sorted(bad)[0]}'", suggest(sorted(bad)[0], known | {"colors"}))
        fill = parse_color(bg.get("color", "#000"), where + ".color")
        layer = {"slot": "full", "fit": "cover", "z": -1000}
        if bg.get("image"):
            layer.update(type="image", src=bg["image"])
        elif bg.get("video"):
            layer.update(type="video", src=bg["video"])
            if bg.get("trim"):
                layer["trim"] = bg["trim"]
            if bg.get("speed"):
                layer["speed"] = bg["speed"]
        else:
            return fill, []
        for k in ("filter", "blur", "focus", "opacity"):
            if bg.get(k) is not None:
                layer[k] = bg[k]
        motion = bg.get("motion", "ken_burns" if bg.get("image") else None)
        if motion:
            layer["loop"] = motion
        return fill, [layer]
    raise SpecError(where, "background is a color, an image path, {\"image\": ...}, {\"video\": ...} or {\"colors\": [...]}")


def caption_config(spec, scene=None):
    cfg = spec.get("captions")
    if not cfg:
        return None
    if cfg is True:
        cfg = {}
    if isinstance(cfg, str):
        cfg = {"style": cfg}
    if scene is not None and scene.get("captions") is False:
        return None
    if cfg.get("enabled") is False:
        return None
    bad = set(cfg) - CAPTION_KEYS
    if bad:
        raise SpecError("root.captions", f"unknown captions key '{sorted(bad)[0]}'", suggest(sorted(bad)[0], CAPTION_KEYS))
    return cfg


class SceneRenderer:
    def __init__(self, rc, spec, entry, chunks=None):
        self.rc, self.entry = rc, entry
        s = spec["scenes"][entry["index"]]
        self.scene = s
        where = f"scenes[{entry['index']}]({s['id']})"
        rc.current_scene = s["id"]
        self.tl = Timeline(rc, entry["start"], entry["duration"], (rc.W, rc.H), where, s["id"])
        base_slots = rc.slots
        if s.get("layout"):
            rc.slots = {**base_slots, **layout_slots(s["layout"], rc.W, rc.H, where + ".layout")}
        try:
            self._build(rc, spec, entry, s, where, chunks)
        finally:
            rc.slots = base_slots

    def _build(self, rc, spec, entry, s, where, chunks):
        default_bg = None if rc.alpha else "#000000"
        self.fill, bg_specs = background_layers(s.get("background", spec.get("background", default_bg)), where + ".background")
        if rc.alpha and s.get("background", spec.get("background")) is None:
            self.fill = (0, 0, 0, 0)
        for i, b in enumerate(bg_specs):
            self.tl.add(make_layer(b, self.tl, f"{where}.background"))
        for i, l in enumerate(s.get("layers", [])):
            self.tl.add(make_layer(l, self.tl, f"{where}.layers[{i}]"))
        cfg = caption_config(spec, s)
        if cfg is not None and rc.words.words:
            if chunks is None:
                chunks = caption_chunks(spec, rc)
            local = [c for c in chunks if c["end"] > entry["start"] and c["start"] < entry["start"] + entry["duration"]]
            if local:
                self.tl.add(CaptionsLayer(cfg, self.tl, f"{where}.captions", local))
        self.tl.resolve()
        self.camera = Camera(s.get("camera", spec.get("camera")), self.tl, rc, where + ".camera")
        self.layers = sorted(self.tl.layers, key=lambda l: l.z)
        self.look = look_filters({**(spec.get("look") or {}), **(s.get("look") or {})}, where + ".look", rc.q)

    def frame(self, t):
        rc = self.rc
        w, h = max(2, int(round(rc.W * rc.q))), max(2, int(round(rc.H * rc.q)))
        canvas = Image.new("RGBA", (w, h), self.fill)
        Q = scale(rc.q)
        cam = chain(Q, self.camera.matrix(t))
        for layer in self.layers:
            layer.render(canvas, t, cam if layer.use_camera else Q, rc.q)
        return canvas

    def close(self):
        for layer in self.tl.layers:
            if hasattr(layer, "close"):
                layer.close()


def caption_chunks(spec, rc):
    cfg = caption_config(spec)
    if cfg is None or not rc.words.words:
        return []
    from .captions import STYLES
    st = STYLES.get(cfg.get("style", "karaoke"), STYLES["karaoke"])
    entries, _ = plan(spec, rc)
    cuts = [e["start"] + e["transition"][1] / 2 for e in entries[1:]]  # a caption never runs across a scene change
    return build_chunks(rc.words.words, int(cfg.get("max_words", 1 if st["single"] else 4)), int(cfg.get("max_chars", 24)), st["single"], cuts)

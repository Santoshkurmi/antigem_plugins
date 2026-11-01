"""A procedural stick figure: poses with smooth transitions, looping actions, expressions and voice-synced talking."""
import math

from PIL import Image, ImageDraw

from . import easing
from .anim import _noise
from .layers import Layer, speaking
from .raster import Content, LANCZOS
from .util import SpecError, color as parse_color, length, suggest

# Angles in degrees. Limbs: 0 = hanging straight down, positive = swung toward the facing direction.
# Elbows bend the forearm forward (+); knees bend the shin backward (+). lean = torso tilt forward; head = nod down (+).
J = ("lean", "head", "ls", "le", "rs", "re", "lh", "lk", "rh", "rk")
POSES = {
    "stand":         dict(lean=0, head=0, ls=-10, le=6, rs=10, re=6, lh=-4, lk=2, rh=4, rk=2),
    "wave":          dict(lean=0, head=-4, ls=-10, le=6, rs=150, re=25, lh=-4, lk=2, rh=4, rk=2),
    "point":         dict(lean=4, head=0, ls=-12, le=8, rs=88, re=0, lh=-6, lk=2, rh=8, rk=2),
    "point_up":      dict(lean=0, head=-10, ls=-12, le=8, rs=165, re=0, lh=-4, lk=2, rh=4, rk=2),
    "think":         dict(lean=4, head=10, ls=10, le=95, rs=28, re=140, lh=-4, lk=2, rh=4, rk=2),
    "cheer":         dict(lean=-4, head=-12, ls=-150, le=-10, rs=150, re=10, lh=-10, lk=4, rh=10, rk=4),
    "shrug":         dict(lean=0, head=12, ls=-35, le=-85, rs=35, re=85, lh=-4, lk=2, rh=4, rk=2),
    "sit":           dict(lean=-4, head=0, ls=10, le=60, rs=20, re=60, lh=85, lk=85, rh=92, rk=92),
    "facepalm":      dict(lean=8, head=22, ls=-8, le=6, rs=38, re=150, lh=-4, lk=2, rh=4, rk=2),
    "cross_arms":    dict(lean=-2, head=-4, ls=22, le=105, rs=26, re=110, lh=-6, lk=2, rh=6, rk=2),
    "hands_on_hips": dict(lean=0, head=-4, ls=-38, le=75, rs=38, re=-75, lh=-8, lk=2, rh=8, rk=2),
    "sad":           dict(lean=14, head=28, ls=4, le=0, rs=-4, re=0, lh=-2, lk=6, rh=2, rk=6),
    "present":       dict(lean=0, head=-4, ls=-10, le=6, rs=55, re=35, lh=-6, lk=2, rh=6, rk=2),
    "surprised":     dict(lean=-8, head=-10, ls=-55, le=-70, rs=55, re=70, lh=-8, lk=2, rh=8, rk=2),
    "angry":         dict(lean=6, head=6, ls=-38, le=75, rs=38, re=-75, lh=-12, lk=2, rh=12, rk=2),
    "jump":          dict(lean=-4, head=-10, ls=-140, le=-20, rs=140, re=20, lh=40, lk=70, rh=25, rk=60),
    "run":           dict(lean=14, head=-4, ls=-40, le=90, rs=40, re=90, lh=-30, lk=40, rh=35, rk=30),
    "walk":          dict(lean=3, head=0, ls=-15, le=15, rs=15, re=15, lh=-15, lk=10, rh=15, rk=10),
    "kneel":         dict(lean=4, head=6, ls=10, le=40, rs=30, re=60, lh=90, lk=90, rh=0, rk=110),
    "look_up":       dict(lean=-6, head=-28, ls=-10, le=6, rs=10, re=6, lh=-4, lk=2, rh=4, rk=2),
    "dab":           dict(lean=6, head=30, ls=-120, le=0, rs=120, re=150, lh=-10, lk=2, rh=10, rk=2),
}
ACTIONS = {"walk", "run", "wave", "nod", "gesture", "jump", "dance", "idle", "shake_head", "type"}
EXPRESSIONS = {"neutral", "happy", "sad", "surprised", "angry", "thinking", "wink", "worried", "laugh", "none"}

# segment lengths as fractions of the figure height
HEAD_R, NECK, TORSO, UPPER, FORE, THIGH, SHIN = 0.085, 0.035, 0.29, 0.155, 0.15, 0.215, 0.215


def _pose(name, where):
    if isinstance(name, dict):
        bad = set(name) - set(J)
        if bad:
            raise SpecError(where, f"unknown joint '{sorted(bad)[0]}'", "joints: " + ", ".join(J))
        return {**POSES["stand"], **{k: float(v) for k, v in name.items()}}
    if name not in POSES:
        raise SpecError(where, f"unknown pose '{name}'", suggest(name, POSES))
    return dict(POSES[name])


class StickmanLayer(Layer):
    KEYS = {"size", "color", "line_width", "head_fill", "pose", "poses", "action", "actions", "expression", "expressions",
            "talk", "facing", "rough", "boil", "speed", "accessory"}
    default_anchor = (0.5, 1.0)

    def __init__(self, spec, tl, where):
        super().__init__(spec, tl, where)
        W, H = tl.size
        self.size = length(spec.get("size"), H, where + ".size", W, H) if spec.get("size") is not None else (self.slot[3] * 0.9 if self.slot else H * 0.4)
        if self.slot and spec.get("y") is None:
            self.base["y"] = self.slot[1] + self.slot[3]
        self.bw, self.bh = self.size * 1.0, self.size * 1.3
        self.ink = parse_color(spec.get("color", "#111111"), where + ".color")
        self.head_fill = parse_color(spec["head_fill"], where + ".head_fill") if spec.get("head_fill") else None
        self.lw = float(spec.get("line_width", self.size * 0.034))
        self.dir = -1 if spec.get("facing", "right") == "left" else 1
        self.base_pose = _pose(spec.get("pose", "stand"), where + ".pose")
        self.pose_keys = []
        for i, ps in enumerate(spec.get("poses") or []):
            if not isinstance(ps, dict) or "at" not in ps or "pose" not in ps:
                raise SpecError(f"{where}.poses[{i}]", "a pose change is {\"at\": cue, \"pose\": \"point\", \"dur\": 0.3}")
            self.pose_keys.append([ps["at"], _pose(ps["pose"], f"{where}.poses[{i}].pose"), float(ps.get("dur", 0.3)), f"{where}.poses[{i}].at"])
        acts = spec.get("actions") or ([{"action": spec["action"]}] if spec.get("action") else [])
        self.actions = []
        for i, a in enumerate(acts):
            if isinstance(a, str):
                a = {"action": a}
            name = a.get("action") if isinstance(a, dict) else None
            if name not in ACTIONS:
                raise SpecError(f"{where}.actions[{i}]", f"unknown action '{name}'", suggest(name, ACTIONS))
            self.actions.append([a.get("at", 0), a.get("until"), name, float(a.get("speed", spec.get("speed", 1))), f"{where}.actions[{i}]"])
        self.expr = spec.get("expression", "neutral")
        if self.expr not in EXPRESSIONS:
            raise SpecError(where + ".expression", f"unknown expression '{self.expr}'", suggest(self.expr, EXPRESSIONS))
        self.expr_keys = []
        for i, e in enumerate(spec.get("expressions") or []):
            if not isinstance(e, dict) or e.get("expression") not in EXPRESSIONS or "at" not in e:
                raise SpecError(f"{where}.expressions[{i}]", "an expression change is {\"at\": cue, \"expression\": \"happy\"}",
                                "expressions: " + ", ".join(sorted(EXPRESSIONS)))
            self.expr_keys.append([e["at"], e["expression"], f"{where}.expressions[{i}].at"])
        self.talk = spec.get("talk")
        self.accessory = spec.get("accessory")
        if self.accessory not in (None, "glasses", "hat", "tie", "cap", "bow"):
            raise SpecError(where + ".accessory", f"unknown accessory '{self.accessory}'", "glasses, hat, cap, tie or bow")
        self._resolved = False

    def prepare(self):
        if self._resolved:
            return
        loc = lambda v, w: self.tl.local(v, w, rel_start=self.start, rel_end=self.end) - self.start  # noqa: E731
        for k in self.pose_keys:
            k[0] = loc(k[0], k[3])
        self.pose_keys.sort(key=lambda k: k[0])
        for k in self.expr_keys:
            k[0] = loc(k[0], k[2])
        self.expr_keys.sort(key=lambda k: k[0])
        for a in self.actions:
            a[0] = loc(a[0], a[4] + ".at")
            a[1] = loc(a[1], a[4] + ".until") if a[1] is not None else 1e9
        self.talk_spans = None
        if isinstance(self.talk, list):
            self.talk_spans = [(self.tl.local(a, self.where + ".talk") + self.tl.start_global,
                                self.tl.local(b, self.where + ".talk") + self.tl.start_global) for a, b in self.talk]
        self._resolved = True

    def angles(self, lt):
        pose = dict(self.base_pose)
        for at, target, dur, _ in self.pose_keys:
            if lt >= at:
                u = easing.apply("out_back" if dur < 0.5 else "in_out_cubic", (lt - at) / max(dur, 1e-3))
                pose = {k: pose[k] + (target[k] - pose[k]) * u for k in J}
        lift = 0.0
        for at, until, name, sp, _ in self.actions:
            if not (at <= lt < until):
                continue
            t = (lt - at) * sp
            if name in ("walk", "run"):
                run = name == "run"
                ph = 2 * math.pi * t * (1.5 if run else 0.95)
                amp, knee, arm = (42, 65, 45) if run else (24, 28, 20)
                s = math.sin(ph)
                pose.update(lh=amp * s, rh=-amp * s, lk=8 + knee * max(0, -math.cos(ph)), rk=8 + knee * max(0, math.cos(ph)),
                            ls=-arm * s, rs=arm * s, le=(85 if run else 15), re=(85 if run else 15), lean=(14 if run else 3))
                lift += abs(math.cos(ph)) * (0.03 if run else 0.012)
            elif name == "wave":
                pose["rs"] = 150
                pose["re"] = 25 + 28 * math.sin(2 * math.pi * 2.2 * t)
            elif name == "nod":
                pose["head"] += 9 * math.sin(2 * math.pi * 1.6 * t)
            elif name == "shake_head":
                pose["head"] += 0  # drawn as a sideways face shift below
            elif name == "gesture":
                pose["rs"] += 22 * (0.5 + 0.5 * _noise(3, t * 1.4)) + 18
                pose["re"] += 40 * (0.5 + 0.5 * _noise(5, t * 1.7))
                pose["ls"] += -10 * (0.5 + 0.5 * _noise(7, t * 1.2))
            elif name == "jump":
                cyc = (t % 0.9) / 0.9
                lift += 4 * cyc * (1 - cyc) * 0.18
                bend = 1 - min(1.0, 4 * cyc * (1 - cyc) * 1.3)
                pose.update(lk=10 + 60 * bend, rk=10 + 60 * bend, lh=-5 + 35 * bend, rh=5 + 35 * bend, ls=-140, rs=140)
            elif name == "dance":
                ph = 2 * math.pi * t * 1.0
                pose.update(ls=-120 + 50 * math.sin(ph), rs=120 + 50 * math.sin(ph + math.pi), le=-40, re=40,
                            lh=-15 + 15 * math.sin(ph), rh=15 + 15 * math.sin(ph), lean=8 * math.sin(ph / 2))
                lift += 0.015 * abs(math.sin(ph))
            elif name == "type":
                pose.update(ls=55, rs=60, le=40 + 10 * math.sin(2 * math.pi * 6 * t), re=40 + 10 * math.sin(2 * math.pi * 6 * t + 1))
            elif name == "idle":
                pose["head"] += 2 * math.sin(2 * math.pi * 0.5 * t)
        return pose, lift

    def expression(self, lt):
        e = self.expr
        for at, ex, _ in self.expr_keys:
            if lt >= at:
                e = ex
        return e

    def mouth_open(self, lt):
        if not self.talk:
            return False
        g = self.tl.start_global + self.start + lt
        return speaking(self.rc, g, self.talk_spans) and int(g * 9) % 2 == 1

    def content_key(self, p, d):
        pose, lift = self.angles(p.lt)
        rough = float(self.spec.get("rough", 0) or 0)
        bf = int(p.lt * float(self.spec.get("boil", 8))) if rough else 0
        return (round(d, 3), tuple(round(pose[k], 1) for k in J), round(lift, 4), self.expression(p.lt), self.mouth_open(p.lt), bf)

    def content(self, p, d):
        key = self.content_key(p, d)
        pose, lift = self.angles(p.lt)
        rough = float(self.spec.get("rough", 0) or 0)
        return self.cached(key, lambda: self._draw(pose, lift, key[3], key[4], d, rough, key[5]))

    def _draw(self, pose, lift, expr, mouth, d, rough, bf):
        ss = 2
        k = d * ss
        S = self.size * k
        W, H = int(self.bw * k), int(self.bh * k)
        pad = int(self.lw * k * 2) + 4
        img = Image.new("RGBA", (W + pad * 2, H + pad * 2), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        dirx = self.dir
        rad = math.radians
        jit = (lambda x, y, i: (x + rough * k * _noise(bf * 31 + i, 0.5), y + rough * k * _noise(bf * 17 + i, 1.5))) if rough else (lambda x, y, i: (x, y))

        def limb(origin, a_deg, L):
            a = rad(a_deg)
            return origin[0] + math.sin(a) * dirx * L * S, origin[1] + math.cos(a) * L * S
        # build at an arbitrary hip, then shift so the lowest point touches the ground
        hip = (0.0, 0.0)
        lean = rad(pose["lean"])
        neck = (hip[0] + math.sin(lean) * dirx * TORSO * S, hip[1] - math.cos(lean) * TORSO * S)
        shoulder = (hip[0] + math.sin(lean) * dirx * (TORSO - 0.02) * S, hip[1] - math.cos(lean) * (TORSO - 0.02) * S)
        ha = lean + rad(pose["head"]) * 0.6
        head_c = (neck[0] + math.sin(ha) * dirx * (NECK + HEAD_R) * S, neck[1] - math.cos(ha) * (NECK + HEAD_R) * S)
        arms, legs = [], []
        for side in ("l", "r"):
            sa = pose[side + "s"] + pose["lean"]
            elbow = limb(shoulder, sa, UPPER)
            hand = limb(elbow, sa + pose[side + "e"], FORE)
            arms.append((shoulder, elbow, hand))
            ta = pose[side + "h"]
            knee = limb(hip, ta, THIGH)
            foot = limb(knee, ta - pose[side + "k"], SHIN)
            legs.append((hip, knee, foot))
        pts = [p for ch in arms + legs for p in ch] + [neck, (head_c[0], head_c[1] - HEAD_R * S)]
        low = max(p[1] for p in legs[0] + legs[1])
        ox = pad + W / 2 - hip[0]
        oy = pad + H - low - lift * S
        lw = max(1.0, self.lw * k)
        ink = self.ink

        def T(p, i=0):
            return jit(p[0] + ox, p[1] + oy, i)

        def seg(chain, i0):
            q = [T(p, i0 + j) for j, p in enumerate(chain)]
            dr.line(q, fill=ink, width=int(round(lw)), joint="curve")
            for x, y in (q[0], q[-1]):
                dr.ellipse((x - lw / 2, y - lw / 2, x + lw / 2, y + lw / 2), fill=ink)
        seg(arms[0], 10)
        seg(legs[0], 20)
        seg([hip, neck], 30)
        seg(legs[1], 40)
        hx, hy = T(head_c, 50)
        r = HEAD_R * S
        dr.ellipse((hx - r, hy - r, hx + r, hy + r), fill=self.head_fill or (0, 0, 0, 0), outline=ink, width=int(round(lw)))
        self._face(dr, hx, hy, r, lw, expr, mouth, dirx)
        self._accessory(dr, hx, hy, r, lw, dirx, T(neck), T(hip))
        seg(arms[1], 60)
        img = img.resize((img.width // ss, img.height // ss), LANCZOS)
        p2 = pad / ss
        return self.effects(Content(img, d, (p2, p2, self.bw * d, self.bh * d)))

    def _face(self, dr, hx, hy, r, lw, expr, mouth, dirx):
        if expr == "none":
            return
        ink = self.ink
        fx = hx + dirx * r * 0.18
        er = r * 0.11
        eyes = [(fx - r * 0.32, hy - r * 0.12), (fx + r * 0.32, hy - r * 0.12)]
        if expr == "thinking":
            eyes = [(x + dirx * r * 0.08, y - r * 0.08) for x, y in eyes]
        for i, (x, y) in enumerate(eyes):
            if expr == "wink" and i == 1:
                dr.line([(x - er, y), (x + er, y)], fill=ink, width=max(1, int(lw * 0.5)))
            elif expr in ("happy", "laugh"):
                dr.arc((x - er * 1.4, y - er, x + er * 1.4, y + er * 1.6), 200, 340, fill=ink, width=max(1, int(lw * 0.5)))
            else:
                big = 1.35 if expr == "surprised" else 1.0
                dr.ellipse((x - er * big, y - er * big, x + er * big, y + er * big), fill=ink)
        if expr in ("angry", "worried"):
            for i, (x, y) in enumerate(eyes):
                s = (1 if i == 0 else -1) * (1 if expr == "angry" else -1)
                dr.line([(x - er * 1.8, y - er * 2.6 - s * er), (x + er * 1.8, y - er * 2.6 + s * er)], fill=ink, width=max(1, int(lw * 0.5)))
        mx, my = fx, hy + r * 0.42
        mw = r * 0.42
        w2 = max(1, int(lw * 0.55))
        if mouth or expr == "laugh":
            dr.ellipse((mx - mw * 0.55, my - r * 0.14, mx + mw * 0.55, my + r * 0.2), fill=ink)
        elif expr == "happy" or expr == "wink":
            dr.arc((mx - mw, my - r * 0.35, mx + mw, my + r * 0.15), 20, 160, fill=ink, width=w2)
        elif expr in ("sad", "worried"):
            dr.arc((mx - mw * 0.8, my - r * 0.02, mx + mw * 0.8, my + r * 0.4), 200, 340, fill=ink, width=w2)
        elif expr == "surprised":
            dr.ellipse((mx - r * 0.13, my - r * 0.13, mx + r * 0.13, my + r * 0.18), outline=ink, width=w2)
        elif expr == "thinking":
            dr.line([(mx - mw * 0.2, my), (mx + mw * 0.7, my - r * 0.08)], fill=ink, width=w2)
        else:
            dr.line([(mx - mw * 0.6, my), (mx + mw * 0.6, my)], fill=ink, width=w2)

    def _accessory(self, dr, hx, hy, r, lw, dirx, neck, hip):
        a = self.accessory
        ink = self.ink
        if a == "glasses":
            fx = hx + dirx * r * 0.18
            for x in (fx - r * 0.32, fx + r * 0.32):
                dr.ellipse((x - r * 0.24, hy - r * 0.34, x + r * 0.24, hy + r * 0.12), outline=ink, width=max(1, int(lw * 0.45)))
            dr.line([(fx - r * 0.08, hy - r * 0.14), (fx + r * 0.08, hy - r * 0.14)], fill=ink, width=max(1, int(lw * 0.45)))
        elif a in ("hat", "cap"):
            top = hy - r * 0.75
            if a == "hat":
                dr.rectangle((hx - r * 0.7, top - r * 0.9, hx + r * 0.7, top), fill=ink)
                dr.rectangle((hx - r * 1.15, top - r * 0.1, hx + r * 1.15, top + r * 0.1), fill=ink)
            else:
                dr.pieslice((hx - r, hy - r * 1.05, hx + r, hy + r * 0.6), 180, 360, fill=ink)
                dr.rectangle((hx, hy - r * 0.35, hx + dirx * r * 1.4, hy - r * 0.2) if dirx > 0 else (hx - r * 1.4, hy - r * 0.35, hx, hy - r * 0.2), fill=ink)
        elif a == "tie":
            nx, ny = neck
            L = (hip[1] - ny) * 0.45
            dr.polygon([(nx - r * 0.12, ny + r * 0.05), (nx + r * 0.12, ny + r * 0.05), (nx + r * 0.16, ny + L), (nx, ny + L + r * 0.25),
                        (nx - r * 0.16, ny + L)], fill=(214, 48, 49, 255))
        elif a == "bow":
            x, y = hx - dirx * r * 0.2, hy - r * 0.95
            col = (255, 64, 129, 255)
            dr.polygon([(x, y), (x - r * 0.45, y - r * 0.28), (x - r * 0.45, y + r * 0.28)], fill=col)
            dr.polygon([(x, y), (x + r * 0.45, y - r * 0.28), (x + r * 0.45, y + r * 0.28)], fill=col)

    def density(self, dens):
        return dens * max(1.0, abs(self.base["scale"]))

"""Load a video JSON: comments, templates (defs/use), root and scene validation, aspect presets, slots."""
import ast
import copy
import glob
import operator
import json
import os
import re

from .util import SKILL_DIR, SpecError, suggest

ROOT_KEYS = {"version", "title", "width", "height", "aspect", "fps", "background", "fonts", "font_dirs", "defs", "slots",
             "look", "captions", "audio", "scenes", "transition", "output", "quality", "note", "comment", "camera",
             "style", "theme", "cue_lead"}
SCENE_KEYS = {"id", "duration", "until", "background", "camera", "transition", "look", "layers", "captions", "note", "comment",
              "use", "with", "layout"}
DEFAULT_THEME = {"bg": "#0b0b0f", "surface": "#1c1c22", "text": "#ffffff", "muted": "#a1a1aa", "accent": "#ffd60a",
                 "accent2": "#ff375f", "ink": "#111111", "paper": "#f4ecd8", "line": "#ffffff", "shadow": "#000000",
                 "font_display": "display", "font_body": "sans", "font_mono": "mono", "font_hand": "hand"}
ASPECTS = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080), "4:5": (1080, 1350), "4:3": (1440, 1080), "21:9": (2520, 1080)}


def _strip_comments(text):
    """Allow // line comments and trailing commas (common model mistakes) outside strings."""
    out, i, n, in_str = [], 0, len(text), False
    while i < n:
        ch = text[i]
        if in_str:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
            out.append(ch)
        elif ch == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                i += 1
            continue
        else:
            out.append(ch)
        i += 1
    return re.sub(r",(\s*[\]}])", r"\1", "".join(out))


def _kit_defs():
    """Built-in templates from make_video/kit/*.json, used as {"use": "kit.NAME"}."""
    out = {}
    for f in sorted(glob.glob(os.path.join(SKILL_DIR, "kit", "*.json"))):
        with open(f, encoding="utf-8") as fh:
            try:
                data = json.loads(_strip_comments(fh.read()))
            except json.JSONDecodeError as e:
                raise SpecError(f"kit/{os.path.basename(f)}", f"invalid JSON: {e}")
        for name, d in data.items():
            out[f"kit.{name}"] = d
    return out


def style_names():
    return sorted(os.path.splitext(os.path.basename(f))[0] for f in glob.glob(os.path.join(SKILL_DIR, "styles", "*.json")))


def load_style(name, where="root.style"):
    path = os.path.join(SKILL_DIR, "styles", f"{name}.json")
    if not os.path.exists(path):
        raise SpecError(where, f"unknown style '{name}'", suggest(name, style_names()))
    with open(path, encoding="utf-8") as f:
        return json.loads(_strip_comments(f.read()))


def _tokens(obj, theme):
    """Replace "$accent"-style theme tokens (whole strings only, so "$5" in text is left alone)."""
    if isinstance(obj, str):
        if obj.startswith("$") and obj[1:] in theme:
            return theme[obj[1:]]
        return obj
    if isinstance(obj, list):
        return [_tokens(v, theme) for v in obj]
    if isinstance(obj, dict):
        return {k: _tokens(v, theme) for k, v in obj.items()}
    return obj


def load(path):
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    try:
        data = json.loads(_strip_comments(raw))
    except json.JSONDecodeError as e:
        lines = raw.splitlines()
        ctx = lines[e.lineno - 1] if 0 < e.lineno <= len(lines) else ""
        raise SpecError(f"{path} line {e.lineno} col {e.colno}", f"invalid JSON: {e.msg}", f"near: {ctx.strip()[:80]}")
    if not isinstance(data, dict):
        raise SpecError(path, "the file must contain one JSON object")
    return normalize(data)


_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Mod: operator.mod,
        ast.Pow: operator.pow, ast.FloorDiv: operator.floordiv, ast.USub: operator.neg, ast.UAdd: operator.pos}
_FUNCS = {"min": min, "max": max, "abs": abs, "round": round}


def _calc(expr, params, where):
    """Safe arithmetic on numeric template parameters: {{= 1 - value/100 }}."""
    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.Name):
            v = params.get(n.id)
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                raise SpecError(where, f"'{n.id}' in {{{{= {expr} }}}} must be a number parameter")
            return v
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.operand))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _FUNCS and not n.keywords:
            return _FUNCS[n.func.id](*[ev(a) for a in n.args])
        raise SpecError(where, f"unsupported expression {{{{= {expr} }}}}", "use numbers, parameters, + - * / % ** and min/max/abs/round")
    try:
        tree = ast.parse(expr.strip(), mode="eval")
    except SyntaxError:
        raise SpecError(where, f"bad expression {{{{= {expr} }}}}")
    try:
        return ev(tree)
    except ZeroDivisionError:
        raise SpecError(where, f"division by zero in {{{{= {expr} }}}}")


def _subst(obj, params, where):
    if isinstance(obj, str):
        m = re.fullmatch(r"\{\{=(.+?)\}\}", obj.strip())
        if m:
            return _calc(m.group(1), params, where)
        if "{{=" in obj:
            obj = re.sub(r"\{\{=(.+?)\}\}", lambda mm: f"{_calc(mm.group(1), params, where):g}", obj)
        m = re.fullmatch(r"\{\{\s*([A-Za-z_][\w]*)\s*\}\}", obj)
        if m:
            if m.group(1) not in params:
                raise SpecError(where, f"template parameter '{m.group(1)}' has no value", suggest(m.group(1), params) if params else "pass it in \"with\"")
            return copy.deepcopy(params[m.group(1)])

        def rep(mm):
            k = mm.group(1)
            if k not in params:
                raise SpecError(where, f"template parameter '{k}' has no value", "pass it in \"with\"")
            return str(params[k])
        return re.sub(r"\{\{\s*([A-Za-z_][\w]*)\s*\}\}", rep, obj)
    if isinstance(obj, list):
        return [_subst(v, params, where) for v in obj]
    if isinstance(obj, dict):
        return {k: _subst(v, params, where) for k, v in obj.items()}
    return obj


def _expand_use(item, defs, where, depth=0):
    """Returns a list (a template may produce several layers)."""
    if not isinstance(item, dict) or "use" not in item:
        return [item]
    if depth > 8:
        raise SpecError(where, "templates nest too deep (a template probably uses itself)")
    name = item["use"]
    if name not in defs:
        raise SpecError(where + ".use", f"unknown template '{name}'", suggest(name, defs) if defs else "define it in \"defs\"")
    d = defs[name]
    params = dict(d.get("params", {})) if isinstance(d, dict) else {}
    given = item.get("with", {})
    if not isinstance(given, dict):
        raise SpecError(where + ".with", "\"with\" must be an object of template parameters")
    unknown = set(given) - set(params) if params else set()
    if unknown and d.get("params") is not None:
        k = sorted(unknown)[0]
        raise SpecError(where + ".with", f"template '{name}' has no parameter '{k}'", suggest(k, params))
    params.update(given)
    overrides = {k: v for k, v in item.items() if k not in ("use", "with")}
    if "layers" in d and "layer" not in d and "scene" not in d:
        body = _subst(copy.deepcopy(d["layers"]), params, where)
        out = []
        for i, l in enumerate(body):
            out += _expand_use(l, defs, f"{where}<{name}>[{i}]", depth + 1)
        if overrides:
            out = [{"type": "group", "layers": out, **overrides}]
        return out
    body = d.get("layer") or d.get("scene") or {k: v for k, v in d.items() if k != "params"}
    body = _subst(copy.deepcopy(body), params, where)
    body.update(overrides)
    return _expand_use(body, defs, where, depth + 1)


def _expand_layers(layers, defs, where):
    if layers is None:
        return []
    if not isinstance(layers, list):
        raise SpecError(where, "\"layers\" must be a list")
    out = []
    for i, l in enumerate(layers):
        for e in _expand_use(l, defs, f"{where}[{i}]"):
            if isinstance(e, dict):
                if e.get("type") == "group":
                    e["layers"] = _expand_layers(e.get("layers"), defs, f"{where}[{i}].layers")
                if isinstance(e.get("mask"), dict):
                    e["mask"] = _expand_layers([e["mask"]], defs, f"{where}[{i}].mask")[0]
            out.append(e)
    return out


def normalize(data):
    unknown = set(data) - ROOT_KEYS
    if unknown:
        k = sorted(unknown)[0]
        raise SpecError("root", f"unknown key '{k}'", suggest(k, ROOT_KEYS))
    data = copy.deepcopy(data)
    theme = dict(DEFAULT_THEME)
    if data.get("style"):
        st = load_style(data["style"])
        theme.update(st.get("theme", {}))
        for k in ("look", "captions"):
            user = data.get(k)
            if k not in st or user is False:
                continue
            if user is True or user is None:
                user = {}
            elif isinstance(user, str):
                user = {"style": user}
            data[k] = {**st[k], **user}
        for k in ("transition", "camera", "background", "fps", "fonts", "cue_lead"):
            if k in st and k not in data:
                data[k] = st[k]
        if st.get("fonts"):
            data["fonts"] = {**st["fonts"], **(data.get("fonts") or {})}
        data["_style_defs"] = st.get("defs", {})
    if data.get("theme") is not None and not isinstance(data["theme"], dict):
        raise SpecError("root.theme", "theme must be an object like {\"accent\": \"#ff375f\"}")
    theme.update(data.get("theme") or {})
    data["theme"] = theme
    if "aspect" in data:
        if data["aspect"] not in ASPECTS:
            raise SpecError("root.aspect", f"unknown aspect '{data['aspect']}'", suggest(data["aspect"], ASPECTS))
        w, h = ASPECTS[data["aspect"]]
        data.setdefault("width", w)
        data.setdefault("height", h)
    data.setdefault("width", 1080)
    data.setdefault("height", 1920)
    data.setdefault("fps", 30)
    for k in ("width", "height"):
        if not isinstance(data[k], int) or data[k] < 64 or data[k] % 2:
            raise SpecError(f"root.{k}", f"{k} must be an even integer ≥ 64")
    if not isinstance(data["fps"], (int, float)) or not 1 <= data["fps"] <= 120:
        raise SpecError("root.fps", "fps must be between 1 and 120")
    audio = data.get("audio") or {}
    bad = set(audio) - {"voice", "music", "sfx", "loudness"}
    if bad:
        raise SpecError("root.audio", f"unknown key '{sorted(bad)[0]}'", suggest(sorted(bad)[0], {"voice", "music", "sfx", "loudness"}))
    for part, keys in (("voice", {"src", "words", "volume", "start"}),
                       ("music", {"src", "volume", "duck", "fade_in", "fade_out", "offset", "start", "loop", "beats", "bpm", "first_beat"})):
        extra = set(audio.get(part) or {}) - keys
        if extra:
            raise SpecError(f"root.audio.{part}", f"unknown key '{sorted(extra)[0]}'", suggest(sorted(extra)[0], keys))
    defs = data.get("defs") or {}
    if not isinstance(defs, dict):
        raise SpecError("root.defs", "defs must be an object of named templates")
    defs = {**_kit_defs(), **data.pop("_style_defs", {}), **defs}
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise SpecError("root.scenes", "needs a non-empty \"scenes\" list")
    out = []
    ids = set()
    for i, s in enumerate(scenes):
        where = f"scenes[{i}]"
        if isinstance(s, dict) and "use" in s:
            s = _expand_use(s, defs, where)[0]
        if not isinstance(s, dict):
            raise SpecError(where, "each scene must be an object")
        bad = set(s) - SCENE_KEYS
        if bad:
            k = sorted(bad)[0]
            raise SpecError(where, f"unknown scene key '{k}'", suggest(k, SCENE_KEYS))
        s = dict(s)
        s.setdefault("id", f"s{i + 1}")
        if s["id"] in ids:
            raise SpecError(where + ".id", f"duplicate scene id '{s['id']}'")
        ids.add(s["id"])
        s["layers"] = _expand_layers(s.get("layers"), defs, f"scenes[{i}]({s['id']}).layers")
        out.append(s)
    data["scenes"] = out
    data.pop("defs", None)
    return _tokens({k: v for k, v in data.items()}, theme) | {"theme": theme}


def slots(W, H, custom=None, where="root.slots"):
    """Named layout rectangles (x, y, w, h) in px. Portrait keeps clear of app UI at the top and bottom."""
    portrait = H > W
    mx = W * 0.06
    top = H * (0.08 if portrait else 0.07)
    bottom = H * (0.17 if portrait else 0.08)
    sx, sy, sw, sh = mx, top, W - 2 * mx, H - top - bottom
    r = {
        "full": (0, 0, W, H), "safe": (sx, sy, sw, sh), "center": (sx + sw * 0.1, sy + sh * 0.25, sw * 0.8, sh * 0.5),
        "top": (sx, sy, sw, sh / 3), "middle": (sx, sy + sh / 3, sw, sh / 3), "bottom": (sx, sy + sh * 2 / 3, sw, sh / 3),
        "top_half": (sx, sy, sw, sh / 2), "bottom_half": (sx, sy + sh / 2, sw, sh / 2),
        "left": (sx, sy, sw / 2, sh), "right": (sx + sw / 2, sy, sw / 2, sh),
        "top_left": (sx, sy, sw / 2, sh / 2), "top_right": (sx + sw / 2, sy, sw / 2, sh / 2),
        "bottom_left": (sx, sy + sh / 2, sw / 2, sh / 2), "bottom_right": (sx + sw / 2, sy + sh / 2, sw / 2, sh / 2),
        "title": (sx, sy, sw, sh * (0.22 if portrait else 0.25)),
        "hero": (sx, sy + sh * (0.22 if portrait else 0.18), sw, sh * (0.5 if portrait else 0.6)),
        "lower_third": (sx, H * (0.62 if portrait else 0.7), sw * (1 if portrait else 0.6), H * 0.12),
        "caption_zone": (sx, H * 0.64, sw, H * 0.14),
    }
    for name, rect in (custom or {}).items():
        if not isinstance(rect, list) or len(rect) != 4:
            raise SpecError(f"{where}.{name}", "a slot is [x, y, w, h] (numbers or '50%' strings)")
        from .util import length
        r[name] = (length(rect[0], W, where, W, H), length(rect[1], H, where, W, H), length(rect[2], W, where, W, H), length(rect[3], H, where, W, H))
    return r


def _safe(W, H):
    portrait = H > W
    mx = W * 0.06
    top = H * (0.08 if portrait else 0.07)
    bottom = H * (0.17 if portrait else 0.08)
    return portrait, mx, top, W - 2 * mx, H - top - bottom


def layout_slots(name, W, H, where="scene.layout"):
    """Extra named slots for a scene layout. Rects are (x, y, w, h) in px inside the safe area; none overlap."""
    portrait, x, y, w, h = _safe(W, H)

    def r(fx, fy, fw, fh):
        return (x + w * fx, y + h * fy, w * fw, h * fh)
    if portrait:
        L = {
            "hero": {"tag": r(0, 0, 1, .06), "title": r(0, .07, 1, .22), "visual": r(0, .31, 1, .45), "label": r(0, .77, 1, .1), "lower": r(0, .88, 1, .12)},
            "duo": {"tag": r(0, 0, 1, .06), "title": r(0, .07, 1, .17), "left": r(0, .26, 1, .3), "label_left": r(0, .56, 1, .07),
                    "right": r(0, .64, 1, .28), "label_right": r(0, .92, 1, .08)},
            "trio": {"title": r(0, 0, 1, .16), "a": r(0, .18, .3, .5), "b": r(.35, .18, .3, .5), "c": r(.7, .18, .3, .5),
                     "la": r(0, .7, .3, .12), "lb": r(.35, .7, .3, .12), "lc": r(.7, .7, .3, .12), "lower": r(0, .85, 1, .15)},
            "board": {"tag": r(0, 0, 1, .06), "a": r(.02, .08, .44, .26), "b": r(.54, .12, .44, .26), "c": r(.25, .4, .5, .26),
                      "d": r(.02, .7, .44, .24), "e": r(.54, .7, .44, .24)},
            "focus": {"tag": r(0, 0, 1, .06), "center": r(.2, .3, .6, .36), "l1": r(0, .08, .48, .18), "r1": r(.52, .08, .48, .18),
                      "l2": r(0, .7, .48, .18), "r2": r(.52, .7, .48, .18), "lower": r(0, .9, 1, .1)},
            "quote": {"tag": r(0, .12, 1, .06), "title": r(.04, .22, .92, .42), "label": r(.1, .68, .8, .08)},
            "split": {"tag": r(0, 0, 1, .06), "title": r(0, .07, 1, .14), "visual": r(0, .23, 1, .37), "list": r(.04, .62, .92, .38)},
            "timeline": {"tag": r(0, 0, 1, .06), "title": r(0, .07, 1, .18), "band": r(0, .3, 1, .5), "lower": r(0, .84, 1, .16)},
            "presenter": {"tag": r(0, 0, 1, .06), "title": r(0, .07, 1, .16), "visual": r(0, .25, 1, .38), "cast": r(.15, .64, .7, .36)},
            "presenter_l": {"tag": r(0, 0, 1, .06), "title": r(0, .07, 1, .16), "visual": r(0, .25, 1, .38), "cast": r(.15, .64, .7, .36)},
            "stage": {"tag": r(0, 0, 1, .06), "title": r(0, .07, 1, .16), "cast": r(0, .3, 1, .7)},
            "clean": {"tag": r(0, 0, 1, .06), "lower": r(0, .86, 1, .14)},
            "stack": {"title": r(0, 0, 1, .2), "a": r(0, .23, 1, .24), "b": r(0, .5, 1, .24), "c": r(0, .77, 1, .23)},
        }
    else:
        L = {
            "hero": {"tag": r(0, 0, .44, .09), "title": r(0, .11, .44, .44), "label": r(0, .58, .44, .14), "lower": r(0, .76, .44, .24),
                     "visual": r(.48, 0, .52, 1)},
            "hero_r": {"tag": r(.56, 0, .44, .09), "title": r(.56, .11, .44, .44), "label": r(.56, .58, .44, .14), "lower": r(.56, .76, .44, .24),
                       "visual": r(0, 0, .52, 1)},
            "duo": {"tag": r(0, 0, 1, .09), "title": r(0, .1, 1, .16), "left": r(0, .28, .48, .56), "right": r(.52, .28, .48, .56),
                    "label_left": r(0, .86, .48, .14), "label_right": r(.52, .86, .48, .14)},
            "trio": {"title": r(0, 0, 1, .18), "a": r(0, .22, .31, .52), "b": r(.345, .22, .31, .52), "c": r(.69, .22, .31, .52),
                     "la": r(0, .78, .31, .16), "lb": r(.345, .78, .31, .16), "lc": r(.69, .78, .31, .16)},
            "board": {"tag": r(0, 0, .3, .09), "a": r(.03, .12, .28, .38), "b": r(.36, .06, .28, .38), "c": r(.69, .12, .28, .38),
                      "d": r(.14, .56, .3, .4), "e": r(.56, .56, .3, .4)},
            "focus": {"tag": r(0, 0, .3, .09), "center": r(.32, .14, .36, .72), "l1": r(0, .14, .28, .3), "l2": r(0, .56, .28, .3),
                      "r1": r(.72, .14, .28, .3), "r2": r(.72, .56, .28, .3)},
            "quote": {"tag": r(.1, .1, .8, .08), "title": r(.1, .2, .8, .5), "label": r(.2, .74, .6, .1)},
            "split": {"tag": r(0, 0, .5, .09), "visual": r(0, .1, .48, .9), "title": r(.52, .1, .48, .2), "list": r(.52, .33, .48, .67)},
            "timeline": {"tag": r(0, 0, .5, .09), "title": r(0, .1, 1, .18), "band": r(0, .36, 1, .44), "lower": r(0, .84, 1, .16)},
            "presenter": {"tag": r(0, 0, .6, .09), "title": r(0, .1, .6, .18), "visual": r(0, .3, .6, .7), "cast": r(.64, .1, .36, .9)},
            "presenter_l": {"tag": r(.4, 0, .6, .09), "title": r(.4, .1, .6, .18), "visual": r(.4, .3, .6, .7), "cast": r(0, .1, .36, .9)},
            "stage": {"tag": r(0, 0, .5, .09), "title": r(0, .1, 1, .15), "cast": r(.05, .28, .9, .72)},
            "clean": {"tag": r(0, 0, .5, .09), "lower": r(0, .82, .6, .18)},
            "stack": {"title": r(0, 0, 1, .22), "a": r(0, .26, .31, .74), "b": r(.345, .26, .31, .74), "c": r(.69, .26, .31, .74)},
        }
        L["hero"]["cast"] = L["hero"]["visual"]
    if portrait:
        L["hero_r"] = L["hero"]
    if name not in L:
        raise SpecError(where, f"unknown layout '{name}'", suggest(name, L))
    return L[name]


LAYOUTS = ["hero", "hero_r", "duo", "trio", "board", "focus", "quote", "split", "timeline", "presenter", "presenter_l", "stage", "clean", "stack"]

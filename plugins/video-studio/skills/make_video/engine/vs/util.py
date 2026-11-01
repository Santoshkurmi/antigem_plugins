"""Shared helpers: errors, colors, lengths, paths."""
import difflib
import hashlib
import json
import math
import os
import re

ENGINE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_DIR = os.path.dirname(ENGINE_DIR)
FONTS_DIR = os.path.join(SKILL_DIR, "fonts")
VERSION = "1.1.0"


class SpecError(Exception):
    """A problem in the video JSON, reported with its location so the model can fix it."""

    def __init__(self, where, message, hint=None):
        self.where, self.message, self.hint = where, message, hint
        super().__init__(f"{where}: {message}" + (f" ({hint})" if hint else ""))


def suggest(word, choices):
    match = difflib.get_close_matches(str(word), list(choices), n=1, cutoff=0.6)
    return f"did you mean '{match[0]}'?" if match else "allowed: " + ", ".join(sorted(choices))


NAMED_COLORS = {
    "white": "#ffffff", "black": "#000000", "red": "#ff3b30", "orange": "#ff9500", "yellow": "#ffd60a",
    "green": "#34c759", "teal": "#30b0c7", "cyan": "#32ade6", "blue": "#0a84ff", "indigo": "#5e5ce6",
    "purple": "#bf5af2", "pink": "#ff2d55", "gray": "#8e8e93", "grey": "#8e8e93", "gold": "#f5c542",
    "cream": "#f4ecd8", "paper": "#efe6d2", "ink": "#16130f", "transparent": "#00000000",
}


def color(value, where="color"):
    """'#rgb', '#rrggbb', '#rrggbbaa', a name, or [r,g,b(,a)] → (r,g,b,a) ints."""
    if isinstance(value, (list, tuple)):
        if len(value) not in (3, 4):
            raise SpecError(where, f"color list needs 3 or 4 numbers, got {value}")
        c = [int(round(v)) for v in value]
        return tuple(c + [255] * (4 - len(c)))
    if not isinstance(value, str):
        raise SpecError(where, f"expected a color, got {value!r}")
    v = NAMED_COLORS.get(value.lower(), value).strip()
    m = re.fullmatch(r"#?([0-9a-fA-F]{3,8})", v)
    if not m or len(m.group(1)) not in (3, 4, 6, 8):
        raise SpecError(where, f"bad color {value!r}", "use #rrggbb, #rrggbbaa or a name like white")
    h = m.group(1)
    if len(h) in (3, 4):
        h = "".join(ch * 2 for ch in h)
    parts = [int(h[i:i + 2], 16) for i in range(0, len(h), 2)]
    return tuple(parts + [255] * (4 - len(parts)))


def with_alpha(c, opacity):
    return (c[0], c[1], c[2], int(round(c[3] * max(0.0, min(1.0, opacity)))))


_LEN = re.compile(r"\s*([+-]?)\s*(\d+(?:\.\d+)?|\.\d+)\s*(%|px|w|h)?")


def length(value, ref, where="value", ref_w=None, ref_h=None):
    """A length or position: 120, '50%', '50%-40', 'center', 'left', 'right', 'top', 'bottom', '10w' (10% of width)."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise SpecError(where, f"expected a number, got {value}")
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        raise SpecError(where, f"expected a number or string like '50%', got {value!r}")
    word = value.strip().lower()
    keywords = {"center": 0.5, "middle": 0.5, "left": 0.0, "top": 0.0, "right": 1.0, "bottom": 1.0, "start": 0.0, "end": 1.0}
    if word in keywords:
        return keywords[word] * ref
    total, pos = 0.0, 0
    text = word.replace(" ", "")
    while pos < len(text):
        m = _LEN.match(text, pos)
        if not m or m.end() == pos:
            raise SpecError(where, f"cannot read length {value!r}", "examples: 120, '50%', '50%+40', 'center'")
        sign = -1 if m.group(1) == "-" else 1
        num, unit = float(m.group(2)), m.group(3)
        if unit == "%":
            num = num / 100.0 * ref
        elif unit == "w":
            num = num / 100.0 * (ref_w if ref_w is not None else ref)
        elif unit == "h":
            num = num / 100.0 * (ref_h if ref_h is not None else ref)
        total += sign * num
        pos = m.end()
    return total


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def file_hash(path):
    try:
        st = os.stat(path)
        return f"{st.st_size}-{int(st.st_mtime)}"
    except OSError:
        return "missing"


def stable_hash(obj):
    return hashlib.sha1(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def is_android():
    return "com.termux" in os.environ.get("PREFIX", "") or os.path.exists("/system/build.prop") or "ANDROID_ROOT" in os.environ


def available_mb():
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) // 1024
    except OSError:
        pass
    return None


def default_workers():
    """All cores but one, limited by free memory (a 1080p worker peaks around 300–500 MB)."""
    cpus = os.cpu_count() or 2
    n = max(1, min(8, cpus - 1 if cpus > 2 else cpus))
    mb = available_mb()
    if mb:
        n = max(1, min(n, mb // 500))
    return n


def fmt_time(t):
    return f"{t:.2f}s"


def rot_matrix(deg):
    r = math.radians(deg)
    return math.cos(r), math.sin(r)

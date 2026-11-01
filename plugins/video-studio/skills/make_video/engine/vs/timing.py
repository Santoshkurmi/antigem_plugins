"""Word timings and cues.

A cue is when something happens, written as:
  2.5            seconds from the start of the scene (layer times) or of the layer (keyframes)
  "end", "end-0.4"            relative to the end of the scene / layer
  "w:crore", "w:crore+0.2"    when that spoken word starts (searched from the scene start onward)
  "w:crore.end", "w:crore#2"  when it ends / its 2nd occurrence;  "w:big bang" matches consecutive words
  "with:title+0.3"            when layer 'title' starts (+0.3 s);  "after:title-0.2" when it ends
  "@12.4"                     absolute time in the whole video
"""
import csv
import json
import os
import re
import unicodedata

from .util import SpecError



def norm_word(w):
    w = unicodedata.normalize("NFC", str(w)).lower()
    return "".join(ch for ch in w if unicodedata.category(ch)[0] in "LMN")


def load_words(path, where="audio.voice.words"):
    """Accepts JSON [{word|text|w, start|s, end|e}] or a TSV/CSV with those columns."""
    if not os.path.exists(path):
        raise SpecError(where, f"word timing file not found: {path}", "create it with `studio.py align` or `studio.py tts`")
    rows = []
    if path.lower().endswith(".json"):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data = data.get("words") or data.get("segments") or []
        rows = data
    else:
        with open(path, encoding="utf-8", newline="") as f:
            sample = f.read(2048)
            f.seek(0)
            delim = "\t" if "\t" in sample else ","
            rows = list(csv.DictReader(f, delimiter=delim))
    words = []
    for i, r in enumerate(rows):
        text = r.get("word") or r.get("text") or r.get("w")
        s, e = r.get("start", r.get("s")), r.get("end", r.get("e"))
        if text is None or s is None:
            raise SpecError(f"{path} row {i + 1}", "each word needs word/text and start (and end)")
        s = float(s)
        e = float(e) if e not in (None, "") else s + 0.3
        words.append({"word": str(text).strip(), "start": s, "end": max(e, s + 0.01), "key": norm_word(text)})
    words.sort(key=lambda w: w["start"])
    return words


def parse_cue(value, where):
    if isinstance(value, bool):
        raise SpecError(where, f"bad time {value!r}")
    if isinstance(value, (int, float)):
        return ("num", float(value), 0.0)
    if not isinstance(value, str):
        raise SpecError(where, f"bad time {value!r}", "use seconds, 'end-0.5', 'w:word', 'b:8', 'after:id', 'with:id' or '@12.5'")
    v = value.strip()
    try:
        return ("num", float(v.rstrip("s")), 0.0)
    except ValueError:
        pass
    if v.startswith("@"):
        try:
            return ("abs", float(v[1:]), 0.0)
        except ValueError:
            raise SpecError(where, f"bad absolute time {value!r}", "example: '@12.5'")
    m = re.match(r"^(w|word|with|after|b|beat|bar|nb):(.+)$", v)
    kind, rest = (m.group(1), m.group(2)) if m else ("end", v[3:]) if v.startswith("end") else (None, v)
    if kind is None:
        raise SpecError(where, f"cannot read time {value!r}", "use seconds, 'end-0.5', 'w:word', 'after:id', 'with:id' or '@12.5'")
    off = 0.0
    om = re.search(r"([+-]\d+(?:\.\d+)?)$", rest)
    if om:
        off = float(om.group(1))
        rest = rest[: om.start()]
    if kind == "end":
        if rest.strip():
            raise SpecError(where, f"cannot read time {value!r}", "examples: 'end', 'end-0.5'")
        return ("end", None, off)
    if kind == "word":
        kind = "w"
    if kind in ("b", "beat", "bar", "nb"):
        try:
            n = int(rest.strip())
        except ValueError:
            raise SpecError(where, f"beat cue needs a whole number: {value!r}", "examples: 'b:9' (9th beat), 'bar:3', 'nb:2' (2nd beat from here)")
        if n < 1:
            raise SpecError(where, f"beat numbers start at 1: {value!r}")
        return ({"beat": "b"}.get(kind, kind), n, off)
    return (kind, rest.strip(), off)


class Beats:
    """Beat grid of the music (global seconds)."""

    def __init__(self, times, bpm=None):
        self.times, self.bpm = list(times or []), bpm

    def nth(self, n, where):
        if not self.times:
            raise SpecError(where, "beat cues need music beats", "set audio.music.bpm, or \"beats\": \"auto\" (see audio_captions.md)")
        if n > len(self.times):
            raise SpecError(where, f"beat {n} is past the last beat ({len(self.times)})")
        return self.times[n - 1]

    def after(self, t, n, where):
        later = [b for b in self.times if b >= t - 0.02]
        if len(later) < n:
            raise SpecError(where, f"only {len(later)} beats left after {t:.2f}s")
        return later[n - 1]


class Words:
    def __init__(self, words):
        self.words = words or []

    def find(self, target, after=0.0, where="cue"):
        """Global start/end of a spoken word (or phrase) at or after `after` seconds."""
        if not self.words:
            raise SpecError(where, f"cue 'w:{target}' needs word timings", "set audio.voice.words (see audio_captions.md)")
        use_end = target.endswith(".end")
        if use_end:
            target = target[:-4]
        nth = 1
        m = re.search(r"#(\d+)$", target)
        if m:
            nth, target = int(m.group(1)), target[: m.start()]
        parts = [norm_word(p) for p in target.split() if norm_word(p)]
        if not parts:
            raise SpecError(where, f"empty word cue 'w:{target}'")
        hits = []
        for strict in (True, False):
            hits = []
            for i, w in enumerate(self.words):
                if w["start"] < after - 0.05 or i + len(parts) > len(self.words):
                    continue
                ok = True
                for j, p in enumerate(parts):
                    k = self.words[i + j]["key"]
                    if not (k == p or (not strict and len(p) >= 3 and k.startswith(p))):
                        ok = False
                        break
                if ok:
                    hits.append((w["start"], self.words[i + len(parts) - 1]["end"]))
            if len(hits) >= nth:
                break
        if len(hits) < nth:
            near = ", ".join([w["word"] for w in self.words if w["start"] >= after - 0.05][:12])
            raise SpecError(where, f"word '{target}' not spoken after {max(0.0, after):.2f}s", f"next words: {near}")
        s, e = hits[nth - 1]
        return e if use_end else s

    def between(self, t0, t1):
        return [w for w in self.words if w["end"] > t0 and w["start"] < t1]

    @property
    def end(self):
        return self.words[-1]["end"] if self.words else 0.0

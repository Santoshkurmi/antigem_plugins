"""Audio: built-in synthesized sound effects ("sfx:whoosh") and the final mix (voice, music with ducking, SFX, clip audio)."""
import json
import math
import os
import random
import subprocess
import wave

import numpy as np

from .timing import parse_cue
from .util import SpecError, suggest

FFMPEG_TIMEOUT = 1800  # seconds; a stuck ffmpeg fails instead of hanging forever

SR = 44100
CACHE = os.path.join(os.path.expanduser("~"), ".cache", "video-studio", "sfx")


def _env(n, attack, curve=3.0):
    """Linear rise over the first `attack` fraction, then a power-curve fall to silence."""
    t = np.linspace(0, 1, n, dtype=np.float64)
    a = max(1e-4, attack)
    return np.where(t < a, t / a, np.power(np.clip(1 - (t - a) / max(1e-4, 1 - a), 0, 1), curve))


def _bandpass_sweep(x, f0, f1, q=1.2, curve=None):
    """Time-varying biquad band-pass (state-variable filter) sweeping f0 → f1."""
    n = len(x)
    out = np.zeros(n)
    low = band = 0.0
    fr = np.geomspace(max(20, f0), max(20, f1), n) if curve is None else curve
    damp = 1.0 / q
    for i in range(n):
        f = 2 * math.sin(math.pi * min(fr[i], SR / 6) / SR)
        high = x[i] - low - damp * band
        band += f * high
        low += f * band
        out[i] = band
    return out


def _noise(n, seed=1):
    return np.random.default_rng(seed).standard_normal(n)


def _sine(freqs, n):
    phase = np.cumsum(2 * np.pi * np.asarray(freqs) / SR)
    return np.sin(phase)


def _norm(x, peak=0.85):
    m = np.max(np.abs(x)) or 1.0
    return x / m * peak


def synth(name):
    n = lambda s: int(SR * s)  # noqa: E731
    if name == "whoosh":
        N = n(0.7)
        x = _bandpass_sweep(_noise(N, 2), 250, 2600, 1.6)
        x = x * _env(N, 0.55, 2.0)
    elif name == "swish":
        N = n(0.32)
        x = _bandpass_sweep(_noise(N, 3), 1200, 5200, 2.0) * _env(N, 0.4, 2.5)
    elif name == "riser":
        N = n(2.2)
        noise = _bandpass_sweep(_noise(N, 4), 300, 5000, 2.5)
        tone = _sine(np.geomspace(180, 900, N), N) * 0.35
        x = (noise + tone) * np.power(np.linspace(0, 1, N), 2.2)
    elif name in ("impact", "boom"):
        N = n(1.6)
        body = _sine(np.geomspace(90, 38, N), N) * np.exp(-np.linspace(0, 6, N))
        crack = _bandpass_sweep(_noise(N, 5), 3000, 400, 0.8) * np.exp(-np.linspace(0, 40, N))
        x = body + crack * 0.6
        x = np.tanh(x * 2.2)
    elif name == "hit":
        N = n(0.45)
        x = _sine(np.geomspace(160, 50, N), N) * np.exp(-np.linspace(0, 9, N)) + _noise(N, 6) * np.exp(-np.linspace(0, 60, N)) * 0.5
    elif name == "pop":
        N = n(0.14)
        x = _sine(np.geomspace(1100, 260, N), N) * np.exp(-np.linspace(0, 10, N))
    elif name == "click":
        N = n(0.04)
        x = _noise(N, 7) * np.exp(-np.linspace(0, 30, N)) * 0.6 + _sine(np.full(N, 3200), N) * np.exp(-np.linspace(0, 25, N))
    elif name == "tick":
        N = n(0.03)
        x = _sine(np.full(N, 2200), N) * np.exp(-np.linspace(0, 20, N))
    elif name in ("ding", "chime"):
        N = n(1.8 if name == "ding" else 2.2)
        base = 1320 if name == "ding" else 988
        x = np.zeros(N)
        notes = [0.0] if name == "ding" else [0.0, 0.12, 0.24]
        for k, start in enumerate(notes):
            s = int(start * SR)
            f = base * (1, 1.26, 1.5)[k] if name == "chime" else base
            m = N - s
            tone = sum(a * _sine(np.full(m, f * r), m) for r, a in ((1, 1), (2.76, 0.4), (5.4, 0.2)))
            x[s:] += tone * np.exp(-np.linspace(0, 6, m))
    elif name == "typing":
        N = n(1.2)
        x = np.zeros(N)
        rng = random.Random(8)
        t = 0.0
        while t < 1.1:
            s = int(t * SR)
            m = min(n(0.03), N - s)
            x[s:s + m] += _noise(m, int(t * 1000)) * np.exp(-np.linspace(0, 25, m)) * rng.uniform(0.5, 1)
            t += rng.uniform(0.06, 0.14)
    elif name == "glitch":
        N = n(0.5)
        rng = np.random.default_rng(9)
        x = np.sign(_sine(np.repeat(rng.uniform(80, 900, 12), N // 12 + 1)[:N], N)) * 0.5
        x *= np.repeat(rng.integers(0, 2, 25), N // 25 + 1)[:N]
        x = np.round(x * 6) / 6
    elif name == "shutter":
        N = n(0.25)
        x = np.zeros(N)
        for st in (0.0, 0.09):
            s = int(st * SR)
            m = n(0.05)
            x[s:s + m] += _noise(m, s + 3) * np.exp(-np.linspace(0, 18, m))
    elif name == "bass_drop":
        N = n(1.8)
        x = np.tanh(_sine(np.geomspace(140, 32, N), N) * 1.8) * np.exp(-np.linspace(0, 3, N))
    elif name == "pluck":
        N = n(0.6)
        period = int(SR / 440)
        buf = np.random.default_rng(10).uniform(-1, 1, period)
        x = np.zeros(N)
        for i in range(N):
            x[i] = buf[i % period]
            buf[i % period] = 0.5 * (buf[i % period] + buf[(i + 1) % period]) * 0.996
    elif name == "swoosh_down":
        N = n(0.8)
        x = _bandpass_sweep(_noise(N, 11), 3500, 220, 1.5) * _env(N, 0.2, 1.6)
    elif name == "heartbeat":
        N = n(1.0)
        x = np.zeros(N)
        for st, a in ((0.0, 1.0), (0.22, 0.7)):
            s = int(st * SR)
            m = n(0.18)
            x[s:s + m] += _sine(np.geomspace(70, 40, m), m) * np.exp(-np.linspace(0, 8, m)) * a
    elif name == "drone":
        N = n(4.0)
        t = np.arange(N) / SR
        x = sum(a * np.sin(2 * np.pi * f * t + p) for f, a, p in ((55, 1, 0), (82.4, 0.6, 1), (110.3, 0.4, 2), (164.6, 0.15, 3)))
        x = x * (0.7 + 0.3 * np.sin(2 * np.pi * 0.25 * t)) + _bandpass_sweep(_noise(N, 12), 200, 400, 3) * 0.3
        x *= np.minimum(1, np.minimum(t / 1.0, (4.0 - t) / 1.0))
    elif name == "stinger":
        N = n(2.0)
        t = np.arange(N) / SR
        cluster = sum(np.sin(2 * np.pi * f * t) for f in (311, 330, 466, 622))
        x = cluster * np.exp(-t * 1.6) * 0.5 + np.tanh(_sine(np.geomspace(80, 40, N), N) * 2) * np.exp(-t * 3)
    elif name == "sub_hit":
        N = n(1.2)
        x = np.tanh(_sine(np.geomspace(60, 30, N), N) * 3) * np.exp(-np.linspace(0, 5, N))
    elif name == "scribble":
        N = n(0.9)
        rng = np.random.default_rng(13)
        x = _bandpass_sweep(_noise(N, 13), 2500, 4500, 1.5) * (0.5 + 0.5 * np.abs(np.sin(np.linspace(0, 18, N) + rng.uniform(0, 1))))
        x *= _env(N, 0.05, 1.0)
    elif name == "paper":
        N = n(0.6)
        x = _bandpass_sweep(_noise(N, 14), 1800, 900, 0.9) * np.random.default_rng(14).uniform(0.2, 1, N) * _env(N, 0.1, 1.5)
    elif name == "coin":
        N = n(0.5)
        x = np.zeros(N)
        h = n(0.08)
        x[:h] = _sine(np.full(h, 988), h)
        x[h:] = _sine(np.full(N - h, 1319), N - h) * np.exp(-np.linspace(0, 6, N - h))
    elif name == "buzz":
        N = n(0.5)
        x = np.sign(_sine(np.full(N, 110), N)) * 0.5 * _env(N, 0.02, 0.5)
    elif name == "success":
        N = n(0.9)
        x = np.zeros(N)
        for k, f in enumerate((523, 659, 784, 1047)):
            s0 = int(k * 0.09 * SR)
            m = N - s0
            x[s0:] += _sine(np.full(m, f), m) * np.exp(-np.linspace(0, 7, m)) * 0.6
    elif name in ("jump8", "coin8", "power8", "blip8", "hit8"):
        N = n({"jump8": 0.3, "coin8": 0.45, "power8": 0.9, "blip8": 0.08, "hit8": 0.25}[name])
        if name == "jump8":
            f = np.geomspace(300, 900, N)
        elif name == "coin8":
            f = np.where(np.arange(N) < n(0.07), 988, 1319)
        elif name == "power8":
            f = 200 * 2 ** (np.floor(np.linspace(0, 12, N)) / 6)
        elif name == "blip8":
            f = np.full(N, 1200)
        else:
            f = np.geomspace(400, 60, N)
        x = np.sign(_sine(f, N)) * 0.45
        if name == "hit8":
            x = np.sign(np.random.default_rng(15).standard_normal(N)) * 0.4 * np.repeat(np.random.default_rng(16).uniform(0, 1, N // 40 + 1), 40)[:N]
        x *= np.exp(-np.linspace(0, 3 if name != "blip8" else 1, N))
        x = np.round(x * 8) / 8
    else:
        raise KeyError(name)
    x = _norm(x)
    fade = min(len(x), 64)
    x[-fade:] *= np.linspace(1, 0, fade)
    return x


SFX_NAMES = ["whoosh", "swish", "swoosh_down", "riser", "impact", "boom", "hit", "pop", "click", "tick", "ding", "chime",
             "typing", "glitch", "shutter", "bass_drop", "pluck", "heartbeat", "drone", "stinger", "sub_hit", "scribble",
             "paper", "coin", "buzz", "success", "jump8", "coin8", "power8", "blip8", "hit8"]


def sfx_path(name, where="sfx"):
    if name not in SFX_NAMES:
        raise SpecError(where, f"unknown built-in sound 'sfx:{name}'", suggest(name, SFX_NAMES))
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, f"{name}.wav")
    if not os.path.exists(p):
        x = synth(name)
        data = (np.clip(x, -1, 1) * 32767).astype(np.int16)
        tmp = p + ".tmp"
        with wave.open(tmp, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(data.tobytes())
        os.replace(tmp, p)
    return p


def resolve_src(rc, src, where):
    if isinstance(src, str) and src.startswith("sfx:"):
        return sfx_path(src[4:], where)
    return rc.path(src, where)


def collect_events(spec, rc, scene_plan, scene_layers):
    """All one-shot sounds with global start times: audio.sfx entries, layer 'sfx', and video layers with audio."""
    events = []
    by_id = {e["id"]: e for e in scene_plan}
    for i, s in enumerate((spec.get("audio") or {}).get("sfx") or []):
        where = f"audio.sfx[{i}]"
        if not isinstance(s, dict) or "src" not in s or "at" not in s:
            raise SpecError(where, "an sfx is {\"src\": \"sfx:whoosh\" or a file, \"at\": cue, \"volume\": 0.8}")
        at = s["at"]
        if isinstance(at, dict):
            sc = by_id.get(at.get("scene"))
            if sc is None:
                raise SpecError(where + ".at", f"unknown scene '{at.get('scene')}'", suggest(at.get("scene"), by_id))
            g = sc["start"] + float(at.get("t", 0))
        else:
            kind, arg, off = parse_cue(at, where + ".at")
            if kind == "num":
                g = arg
            elif kind == "abs":
                g = arg + off
            elif kind == "w":
                g = rc.words.find(arg, 0.0, where + ".at") + off
            else:
                raise SpecError(where + ".at", "use seconds, '@seconds', 'w:word' or {\"scene\": id, \"t\": seconds}")
        events.append({"src": resolve_src(rc, s["src"], where + ".src"), "at": g, "volume": float(s.get("volume", 0.8)),
                       "trim": s.get("trim")})
    for entry, layers in scene_layers:
        for layer in layers:
            g0 = layer.tl.start_global + layer.start
            if layer.sfx:
                sx = layer.sfx if isinstance(layer.sfx, dict) else {"src": layer.sfx}
                events.append({"src": resolve_src(rc, sx["src"], layer.where + ".sfx"), "at": g0 + float(sx.get("offset", 0)),
                               "volume": float(sx.get("volume", 0.7)), "trim": sx.get("trim")})
            if layer.type == "video" and layer.spec.get("audio") and layer.info.get("has_audio"):
                t0, t1 = layer.trim
                dur = layer.end - layer.start
                events.append({"src": layer.path, "at": g0, "volume": float(layer.spec.get("volume", 1.0)),
                               "trim": [t0, min(t1, t0 + dur * layer.speed) if t1 else t0 + dur * layer.speed], "speed": layer.speed})
    return events


def mix(spec, rc, events, total, out_path, final=True):
    """Builds the mixed track with one ffmpeg call. Returns out_path, or None when there is no audio."""
    a = spec.get("audio") or {}
    inputs, filters, labels = [], [], []
    voice_label = None

    def add_input(path, loop=False):
        if loop:
            inputs.extend(["-stream_loop", "-1"])
        inputs.extend(["-i", path])
        return len([x for x in inputs if x == "-i"]) - 1

    voice = a.get("voice")
    if voice and voice.get("src"):
        i = add_input(rc.path(voice["src"], "audio.voice.src"))
        st = int(float(voice.get("start", 0)) * 1000)
        filters.append(f"[{i}:a]aformat=sample_rates={SR}:channel_layouts=stereo,volume={float(voice.get('volume', 1.0))},adelay={st}|{st},asplit=2[vo][vsc]")
        labels.append("[vo]")
        voice_label = "[vsc]"
    music = a.get("music")
    if music and music.get("src"):
        i = add_input(rc.path(music["src"], "audio.music.src"), loop=music.get("loop", True))
        off = float(music.get("offset", 0))
        st = int(float(music.get("start", 0)) * 1000)
        fi, fo = float(music.get("fade_in", 1.0)), float(music.get("fade_out", 2.0))
        chain_ = f"[{i}:a]aformat=sample_rates={SR}:channel_layouts=stereo,atrim=start={off},asetpts=PTS-STARTPTS,volume={float(music.get('volume', 0.3))}"
        if fi > 0:
            chain_ += f",afade=t=in:d={fi}"
        chain_ += f",adelay={st}|{st},atrim=end={total:.3f}"
        if fo > 0:
            chain_ += f",afade=t=out:st={max(0.0, total - fo):.3f}:d={fo}"
        duck = music.get("duck", True)
        if duck and voice_label:
            strength = 0.25 if duck is True else float(duck)
            ratio = max(2, min(20, int(round(1 / max(0.05, strength)))))
            filters.append(chain_ + "[mus]")
            filters.append(f"[mus]{voice_label}sidechaincompress=threshold=0.02:ratio={ratio}:attack=15:release=400:makeup=1[ducked]")
            labels.append("[ducked]")
            voice_label = None
        else:
            filters.append(chain_ + "[mus]")
            labels.append("[mus]")
    if voice_label:
        filters.append(f"{voice_label}anullsink")
    for k, e in enumerate(events):
        i = add_input(e["src"])
        f = f"[{i}:a]aformat=sample_rates={SR}:channel_layouts=stereo"
        if e.get("trim"):
            t0, t1 = e["trim"]
            f += f",atrim=start={float(t0)}" + (f":end={float(t1)}" if t1 is not None else "") + ",asetpts=PTS-STARTPTS"
        if e.get("speed") and e["speed"] != 1:
            sp = float(e["speed"])
            parts = []
            while sp > 2:
                parts.append("atempo=2.0")
                sp /= 2
            while sp < 0.5:
                parts.append("atempo=0.5")
                sp /= 0.5
            parts.append(f"atempo={sp:.4f}")
            f += "," + ",".join(parts)
        ms = int(max(0.0, e["at"]) * 1000)
        f += f",volume={e['volume']},adelay={ms}|{ms}[e{k}]"
        filters.append(f)
        labels.append(f"[e{k}]")
    if not labels:
        return None
    n = len(labels)
    tail = f"{''.join(labels)}amix=inputs={n}:normalize=0:dropout_transition=0,apad,atrim=end={total:.3f}" if n > 1 else \
        f"{labels[0]}apad,atrim=end={total:.3f}"
    tail += ",alimiter=limit=0.95:level=false"
    if final and a.get("loudness", True) is not False:
        tail += ",loudnorm=I=-14:TP=-1.5:LRA=11"
    tail += f",aresample={SR}[out]"
    filters.append(tail)
    cmd = ["ffmpeg", "-y", "-v", "error", "-nostdin"] + inputs + ["-filter_complex", ";".join(filters), "-map", "[out]",
                                                                 "-c:a", "aac", "-b:a", "192k" if final else "128k", out_path]
    r = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=FFMPEG_TIMEOUT)
    if r.returncode != 0:
        raise RuntimeError("audio mix failed: " + r.stderr.strip()[-1500:])
    return out_path


def detect_beats(path, sr=22050):
    """Tempo and beat times of a music file: spectral-flux onsets, autocorrelation tempo (60–200 BPM, sub-frame
    refined, half-tempo corrected) and a phase-fitted grid; each beat is nudged to its nearby onset peak."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], stdin=subprocess.DEVNULL, timeout=FFMPEG_TIMEOUT,
                         capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    if len(x) < sr * 2:
        raise RuntimeError(f"cannot read enough audio from {path}")
    n_fft, hop = 1024, 256
    fps = sr / hop
    frames = np.lib.stride_tricks.sliding_window_view(x, n_fft)[::hop] * np.hanning(n_fft)
    mag = np.log1p(np.abs(np.fft.rfft(frames, axis=1)) * 20)
    diff = np.maximum(0, np.diff(mag, axis=0))
    full = diff.sum(axis=1)
    low = diff[:, : max(2, int(220 / (sr / n_fft)))].sum(axis=1)  # kick drums mark the beat in most music
    flux = np.concatenate([[0], full / (full.max() or 1) + 1.5 * low / (low.max() or 1)])
    win = max(3, int(fps * 0.4))
    onset = np.maximum(0, flux - np.convolve(flux, np.ones(win) / win, mode="same"))
    onset /= onset.max() or 1
    n = len(onset)
    spec = np.fft.rfft(onset - onset.mean(), 2 * n)
    ac = np.fft.irfft(spec * np.conj(spec))[:n]
    lo, hi = int(fps * 60 / 200), int(fps * 60 / 60)
    lags = np.arange(lo, min(hi, n - 1))
    weight = np.exp(-0.5 * (np.log2((60 * fps / lags) / 120) / 1.0) ** 2)
    L = int(lags[int(np.argmax(ac[lags] * weight))])

    def refine(l):
        l = int(round(l))
        a0, a1, a2 = ac[l - 1], ac[l], ac[l + 1]
        den = a0 - 2 * a1 + a2
        return l + (0.5 * (a0 - a2) / den if den != 0 else 0.0)
    period = refine(L)
    half = period / 2
    if 60 * fps / period < 100 and half >= lo * 0.9:
        h_val = max(ac[int(half) - 1:int(half) + 2])
        if h_val > 0.45 * ac[L]:
            period = refine(half)
    best, phase = -1.0, 0.0
    for ph in np.arange(0, period, 1.0):
        idx = np.round(np.arange(ph, n, period)).astype(int)
        sc = onset[idx[idx < n]].sum()
        if sc > best:
            best, phase = sc, ph
    beats = []
    reach = max(1, int(period * 0.08))
    for f in np.arange(phase, n, period):
        i = int(round(f))
        lo_i, hi_i = max(0, i - reach), min(n, i + reach + 1)
        j = lo_i + int(np.argmax(onset[lo_i:hi_i]))
        k = j if onset[j] > 0.25 else i
        beats.append(round((k * hop + n_fft / 2) / sr, 3))
    return round(60 * fps / period, 1), beats


def beat_grid(music, rc, where="audio.music"):
    """Beat times (global seconds) from music.bpm, a beats file, or "beats": "auto"."""
    if not music:
        return None, []
    start = float(music.get("start", 0))
    off = float(music.get("offset", 0))
    if music.get("bpm"):
        bpm = float(music["bpm"])
        first = float(music.get("first_beat", 0))
        step = 60.0 / bpm
        return bpm, [round(start + first + i * step, 4) for i in range(int(3600 / step)) if first + i * step >= 0]
    b = music.get("beats")
    if not b:
        return None, []
    if b == "auto":
        src = rc.path(music["src"], where + ".src")
        cache = os.path.splitext(src)[0] + ".beats.json"
        if os.path.exists(cache) and os.path.getmtime(cache) >= os.path.getmtime(src):
            with open(cache) as f:
                data = json.load(f)
        else:
            bpm, times = detect_beats(src)
            data = {"bpm": bpm, "beats": times}
            with open(cache, "w") as f:
                json.dump(data, f)
    else:
        with open(rc.path(b, where + ".beats")) as f:
            data = json.load(f)
        if isinstance(data, list):
            data = {"bpm": None, "beats": data}
    times = [round(start + t - off, 4) for t in data["beats"] if t - off >= 0]
    return data.get("bpm"), times

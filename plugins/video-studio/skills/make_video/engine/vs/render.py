"""Rendering: per-scene segments (cached, parallel), transitions, audio mux; still frames, contact sheets, inspection."""
import concurrent.futures as cf
import glob
import json
import os
import shutil
import subprocess
import sys
import time

from PIL import Image, ImageDraw

from . import audio, text as textmod
from .compose import TRANSITIONS, RenderContext, SceneRenderer, caption_chunks, plan
from .spec import load
from .util import ENGINE_DIR, VERSION, SpecError, default_workers, file_hash, stable_hash

FFMPEG_TIMEOUT = 1800  # seconds; a stuck ffmpeg fails instead of hanging forever


def log(msg):
    print(msg, flush=True)


class Project:
    def __init__(self, path):
        self.path = os.path.abspath(path)
        if not os.path.exists(self.path):
            raise SpecError(path, "file not found")
        self.dir = os.path.dirname(self.path)
        self.spec = load(self.path)
        self.cache = os.path.join(self.dir, ".vs_cache")
        os.makedirs(os.path.join(self.cache, "segments"), exist_ok=True)

    def context(self, q=1.0, fps=None, fast=False):
        return RenderContext(self.spec, self.dir, q, fps, fast)

    def output(self, name):
        out = self.spec.get("output") or {}
        folder = os.path.join(self.dir, out.get("folder", "")) if isinstance(out, dict) else self.dir
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, name)


def _engine_hash():
    files = sorted(glob.glob(os.path.join(ENGINE_DIR, "vs", "*.py")))
    return stable_hash([VERSION] + [file_hash(f) for f in files])


def _referenced_files(obj, rc, out):
    if isinstance(obj, str):
        if obj.startswith("sfx:"):
            return
        if len(obj) < 300 and ("." in obj or "/" in obj):
            for cand in (obj, os.path.join(rc.project_dir, obj), os.path.join(rc.project_dir, "assets", obj)):
                if os.path.isfile(cand):
                    out.append((obj, file_hash(cand)))
                    break
    elif isinstance(obj, list):
        for v in obj:
            _referenced_files(v, rc, out)
    elif isinstance(obj, dict):
        for v in obj.values():
            _referenced_files(v, rc, out)


def scene_key(spec, rc, entry, settings):
    s = spec["scenes"][entry["index"]]
    files = []
    _referenced_files([s, spec.get("background"), spec.get("fonts")], rc, files)
    for f in glob.glob(os.path.join(rc.project_dir, "fonts", "*")):
        files.append((f, file_hash(f)))
    voice = (spec.get("audio") or {}).get("voice") or {}
    if voice.get("words"):
        files.append(("words", file_hash(rc.abspath(voice["words"]))))
    root = {k: spec.get(k) for k in ("width", "height", "fps", "background", "fonts", "slots", "look", "captions", "camera", "transition")}
    return stable_hash([_engine_hash(), s, root, entry["start"], entry["duration"], files, settings, voice.get("start", 0)])


def _render_segment(job):
    """Runs in a worker process: renders frames [f0, f1) of one scene to a video chunk."""
    t0 = time.time()
    rc = RenderContext(job["spec"], job["dir"], job["q"], job["fps"], job["fast"])
    entry = job["entry"]
    sr = SceneRenderer(rc, job["spec"], entry, job["chunks"])
    w, h = rc_size(rc)
    f0, f1 = job["range"]
    if rc.alpha:
        # transparent overlay (OBS, editors): VP9 with alpha in WebM; looks are skipped
        tmp = job["out"] + ".part.webm"
        cmd = ["ffmpeg", "-y", "-v", "error", "-nostdin", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{w}x{h}", "-r", f"{rc.fps}",
               "-i", "-", "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", str(min(40, job["crf"] + 12)),
               "-deadline", "realtime" if job["fast"] else "good", "-cpu-used", "8" if job["fast"] else "4", "-auto-alt-ref", "0", "-an", tmp]
        mode = "RGBA"
    else:
        vf = sr.look + ["format=yuv420p"]
        tmp = job["out"] + ".part.mp4"
        cmd = ["ffmpeg", "-y", "-v", "error", "-nostdin", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", f"{rc.fps}",
               "-i", "-", "-vf", ",".join(vf), "-c:v", "libx264", "-preset", job["preset"], "-crf", str(job["crf"]),
               "-pix_fmt", "yuv420p", "-g", str(int(rc.fps * 2)), "-threads", str(job["threads"]), "-an", tmp]
        mode = "RGB"
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for i in range(f0, f1):
            frame = sr.frame(i / rc.fps)
            if frame.size != (w, h):
                frame = frame.resize((w, h))
            proc.stdin.write(frame.convert(mode).tobytes())
        proc.stdin.close()
        err = proc.stderr.read().decode(errors="replace")
        if proc.wait() != 0:
            raise RuntimeError(f"ffmpeg failed for scene {entry['id']}: {err[-800:]}")
    except BrokenPipeError:
        err = proc.stderr.read().decode(errors="replace")
        raise RuntimeError(f"ffmpeg stopped for scene {entry['id']}: {err[-800:]}")
    finally:
        sr.close()
    os.replace(tmp, job["out"])
    return entry["id"], f1 - f0, time.time() - t0


def rc_size(rc):
    return max(2, int(round(rc.W * rc.q / 2)) * 2), max(2, int(round(rc.H * rc.q / 2)) * 2)


def render(project, out_path, q=1.0, fps=None, fast=False, crf=19, preset="veryfast", workers=None, scenes=None, with_audio=True, final=True):
    spec = project.spec
    rc = project.context(q, fps, fast)
    entries, total = plan(spec, rc)
    if scenes:
        missing = [s for s in scenes if s not in {e["id"] for e in entries}]
        if missing:
            raise SpecError("--scene", f"unknown scene id '{missing[0]}'", "ids: " + ", ".join(e["id"] for e in entries))
        entries_sel = [e for e in entries if e["id"] in scenes]
    else:
        entries_sel = entries
    # validate every scene in this process first (fast, gives clean errors)
    chunks = caption_chunks(spec, rc)
    renderers = []
    for e in entries_sel:
        sr = SceneRenderer(rc, spec, e, chunks)
        renderers.append((e, sr))
    settings = {"q": q, "fps": rc.fps, "fast": fast, "crf": crf, "preset": preset}
    jobs, segs = [], []
    ext = ".webm" if rc.alpha else ".mp4"
    if rc.alpha and not out_path.endswith(".webm"):
        out_path = os.path.splitext(out_path)[0] + ".webm"
        log("transparent output → WebM (VP9 + alpha); scene transitions become cuts")
    workers = workers or default_workers()
    todo = []
    for e, sr in renderers:
        key = scene_key(spec, rc, e, settings)
        seg = os.path.join(project.cache, "segments", f"{e['id']}-{key}{ext}")
        segs.append((e, seg))
        if not os.path.exists(seg):
            todo.append((e, seg))
    # Split scenes into chunks so every core stays busy (a long scene no longer runs on one core alone).
    total_frames = sum(max(1, int(round(e["duration"] * rc.fps))) for e, _ in todo)
    chunk = int(max(rc.fps, min(rc.fps * 4, total_frames / max(1, workers * 3))))
    threads = max(1, (os.cpu_count() or 2) // max(1, workers))
    parts = {}
    for e, seg in todo:
        n = max(1, int(round(e["duration"] * rc.fps)))
        bounds = list(range(0, n, chunk)) + [n]
        if len(bounds) > 2 and bounds[-1] - bounds[-2] < chunk // 3:  # fold a tiny last piece into the previous one
            bounds.pop(-2)
        parts[seg] = []
        for k in range(len(bounds) - 1):
            part = f"{seg[:-len(ext)]}.c{k:03d}{ext}"
            parts[seg].append(part)
            if not os.path.exists(part):
                jobs.append({"spec": spec, "dir": project.dir, "q": q, "fps": rc.fps, "fast": fast, "entry": e, "chunks": chunks,
                             "out": part, "crf": crf, "preset": preset, "range": (bounds[k], bounds[k + 1]), "threads": threads})
    cached = len(segs) - len(todo)
    log(f"{len(segs)} scene(s), {total:.2f}s total · {cached} cached · rendering {total_frames} frames in {len(jobs)} chunk(s) "
        f"on {min(workers, max(1, len(jobs)))} worker(s) at {rc_size(rc)[0]}x{rc_size(rc)[1]} {rc.fps:g}fps")
    t0 = time.time()
    if jobs:
        done_frames = 0
        jobs.sort(key=lambda j: -(j["range"][1] - j["range"][0]))

        def report(sid, n, dt):
            nonlocal done_frames
            done_frames += n
            el = time.time() - t0
            log(f"  ✓ {sid} +{n} frames ({done_frames}/{total_frames}, {done_frames / max(el, 1e-3):.1f} fps overall)")
        if workers <= 1 or len(jobs) == 1:
            for j in jobs:
                report(*_render_segment(j))
        else:
            with cf.ProcessPoolExecutor(max_workers=min(workers, len(jobs))) as ex:
                for f in cf.as_completed([ex.submit(_render_segment, j) for j in jobs]):
                    report(*f.result())
    for e, seg in todo:
        _concat_parts(parts[seg], seg)
    video_tmp = out_path + ".video" + ext
    _join(segs, video_tmp, rc.fps, crf, preset, joined_all=not scenes and not rc.alpha)
    audio_path = None
    if with_audio and not scenes:
        layers = []
        for e, sr in renderers:
            layers.append((e, _all_layers(sr.tl.layers)))
        events = audio.collect_events(spec, rc, entries, layers)
        apath = os.path.join(project.cache, "mix.m4a")
        audio_path = audio.mix(spec, rc, events, total, apath, final=final)
    for _, sr in renderers:
        sr.close()
    if audio_path:
        acodec = ["-c:v", "copy", "-c:a", "libopus"] if rc.alpha else ["-c", "copy", "-movflags", "+faststart"]
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-nostdin", "-i", video_tmp, "-i", audio_path, "-map", "0:v", "-map", "1:a"]
                           + acodec + ["-shortest", out_path], stdin=subprocess.DEVNULL, timeout=FFMPEG_TIMEOUT, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError("mux failed: " + r.stderr[-800:])
        os.remove(video_tmp)
    else:
        os.replace(video_tmp, out_path)
    log(f"done in {time.time() - t0:.1f}s → {out_path}")
    _prune(project, segs)
    return out_path


def _concat_parts(parts, out):
    """Join a scene's chunks without re-encoding (they share codec settings and each starts on a keyframe)."""
    if len(parts) == 1:
        os.replace(parts[0], out)
        return
    lst = out + ".txt"
    with open(lst, "w") as f:
        for p in parts:
            f.write(f"file '{p}'\n")
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-nostdin", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out],
                       stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=FFMPEG_TIMEOUT)
    os.remove(lst)
    if r.returncode != 0:
        raise RuntimeError("joining chunks failed: " + r.stderr[-800:])
    for p in parts:
        os.remove(p)


def _all_layers(layers):
    out = []
    for l in layers:
        out.append(l)
        inner = getattr(l, "inner", None)
        if inner is not None:
            out += _all_layers(inner.layers)
    return out


def _join(segs, out, fps, crf, preset, joined_all=True):
    if len(segs) == 1:
        shutil.copyfile(segs[0][1], out)
        return
    trans = [e["transition"] for e, _ in segs[1:]] if joined_all else [("cut", 0.0)] * (len(segs) - 1)
    if all(t[0] == "cut" for t in trans):
        lst = out + ".txt"
        with open(lst, "w") as f:
            for _, s in segs:
                f.write(f"file '{s}'\n")
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-nostdin", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out], stdin=subprocess.DEVNULL, timeout=FFMPEG_TIMEOUT,
                           capture_output=True, text=True)
        os.remove(lst)
        if r.returncode != 0:
            raise RuntimeError("concat failed: " + r.stderr[-800:])
        return
    cmd = ["ffmpeg", "-y", "-v", "error", "-nostdin"]
    for _, s in segs:
        cmd += ["-i", s]
    parts = [f"[{i}:v]settb=AVTB,fps={fps},format=yuv420p,setsar=1[v{i}]" for i in range(len(segs))]
    acc = "[v0]"
    for i in range(1, len(segs)):
        e = segs[i][0]
        name, dur = e["transition"]
        lab = f"[x{i}]"
        if name == "cut":
            parts.append(f"{acc}[v{i}]concat=n=2:v=1:a=0,settb=AVTB,fps={fps}{lab}")
        else:
            xf = name[6:] if name.startswith("xfade:") else TRANSITIONS[name]
            parts.append(f"{acc}[v{i}]xfade=transition={xf}:duration={dur:.3f}:offset={e['start']:.3f},settb=AVTB,fps={fps}{lab}")
        acc = lab
    cmd += ["-filter_complex", ";".join(parts), "-map", acc, "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
            "-pix_fmt", "yuv420p", out]
    r = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=FFMPEG_TIMEOUT)
    if r.returncode != 0:
        hint = " (this ffmpeg may not know that transition; try fade/slide_left/wipe_left or update ffmpeg)" if "transition" in r.stderr.lower() else ""
        raise RuntimeError("joining scenes failed" + hint + ": " + r.stderr[-800:])


def _prune(project, keep):
    """Keep the cache small: drop old segments of the same scene id."""
    keep_set = {s for _, s in keep}
    ids = {e["id"] for e, _ in keep}
    files = sorted(glob.glob(os.path.join(project.cache, "segments", "*.mp4")) + glob.glob(os.path.join(project.cache, "segments", "*.webm")),
                   key=os.path.getmtime, reverse=True)
    per_id = {}
    for f in files:
        sid = os.path.splitext(os.path.basename(f))[0].rsplit("-", 1)[0]
        per_id.setdefault(sid, []).append(f)
    for sid, fs in per_id.items():
        for f in fs[3:] if sid in ids else fs[6:]:
            if f not in keep_set:
                try:
                    os.remove(f)
                except OSError:
                    pass


# --- stills -----------------------------------------------------------------------------------------------------------

def graded(img, filters):
    """Run the scene's FFmpeg look (grade, grain, pixelate...) on one still so previews match the video."""
    if not filters:
        return img
    img = img.convert("RGB")
    w, h = img.size
    w2, h2 = w - w % 2, h - h % 2
    if (w2, h2) != (w, h):
        img = img.crop((0, 0, w2, h2))
    r = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w2}x{h2}", "-i", "-",
                        "-vf", ",".join(filters), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], timeout=FFMPEG_TIMEOUT, input=img.tobytes(), capture_output=True)
    if r.returncode != 0 or len(r.stdout) < w2 * h2 * 3:
        return img
    return Image.frombytes("RGB", (w2, h2), r.stdout[: w2 * h2 * 3])


def find_time(entries, t=None, scene=None, at=None):
    if scene is not None:
        e = next((e for e in entries if e["id"] == scene), None)
        if e is None:
            raise SpecError("--scene", f"unknown scene '{scene}'", "ids: " + ", ".join(x["id"] for x in entries))
        local = float(at or 0)
        if local < 0 or local >= e["duration"]:
            raise SpecError("--at", f"scene '{scene}' is {e['duration']:.2f}s long")
        return e, local
    t = float(t or 0)
    hit = None
    for e in entries:
        if e["start"] <= t < e["start"] + e["duration"]:
            hit = e  # the later scene wins inside a transition
    if hit is None:
        hit = entries[-1]
    return hit, min(t - hit["start"], hit["duration"] - 1e-3)


def still(project, out, t=None, scene=None, at=None, q=0.5):
    rc = project.context(q, fast=False)
    entries, _ = plan(project.spec, rc)
    e, local = find_time(entries, t, scene, at)
    sr = SceneRenderer(rc, project.spec, e, caption_chunks(project.spec, rc))
    try:
        img = graded(sr.frame(local), sr.look)
    finally:
        sr.close()
    img.save(out)
    log(f"{e['id']} @ {local:.2f}s (global {e['start'] + local:.2f}s) → {out}")
    return out


def sheet(project, out, scenes=None, per=3, cell=270, times=None):
    rc = project.context(cell / project.spec["width"], fast=True)
    entries, _ = plan(project.spec, rc)
    if scenes:
        entries = [e for e in entries if e["id"] in scenes]
    chunks = caption_chunks(project.spec, rc)
    fracs = times or ([0.5] if per == 1 else [0.12 + 0.76 * i / (per - 1) for i in range(per)])
    w, h = rc_size(rc)
    label_h = 22
    font = textmod.load_font(textmod.find_font("sans"), 14)
    pages, outs = [entries[i:i + 8] for i in range(0, len(entries), 8)], []
    for pi, page in enumerate(pages):
        cols = len(fracs)
        img = Image.new("RGB", (cols * (w + 6) + 6, len(page) * (h + label_h + 6) + 6), (24, 24, 28))
        dr = ImageDraw.Draw(img)
        for r, e in enumerate(page):
            sr = SceneRenderer(rc, project.spec, e, chunks)
            try:
                for c, f in enumerate(fracs):
                    t = min(e["duration"] - 1e-3, e["duration"] * f)
                    fr = graded(sr.frame(t), sr.look)
                    if fr.size != (w, h):
                        fr = fr.resize((w, h))
                    x, y = 6 + c * (w + 6), 6 + r * (h + label_h + 6)
                    img.paste(fr, (x, y))
                    dr.text((x + 2, y + h + 3), f"{e['id']} @{t:.1f}s  (g {e['start'] + t:.1f}s)", font=font, fill=(220, 220, 220))
            finally:
                sr.close()
        p = out if len(pages) == 1 else out.replace(".png", f"_{pi + 1}.png")
        img.save(p)
        outs.append(p)
    log("sheet → " + ", ".join(outs))
    return outs


# --- inspection -------------------------------------------------------------------------------------------------------

TEXTY = {"text", "counter", "captions"}


def _area(b):
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def _inter(a, b):
    return (max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3]))


def _visual_events(layers, offset):
    """Global times when something visibly new happens: layer entrances, word reveals, keyframes, pose changes."""
    out = []
    for l in layers:
        if l.type in ("captions", "particles", "texture"):
            continue
        t0 = offset + l.start
        out.append(t0)
        if getattr(l, "reveal", None) and hasattr(l, "unit_starts"):
            out += [t0 + u for u in l.unit_starts[::2]]
        for tr in l.tracks.values():
            out += [t0 + k[0] for k in tr.keys if 0 <= k[0] <= l.end - l.start]
        for k in getattr(l, "pose_keys", []) + getattr(l, "expr_keys", []):
            out.append(t0 + k[0])
        inner = getattr(l, "inner", None)
        if inner is not None:
            out += _visual_events(inner.layers, t0)
    return out


def inspect(project, scenes=None, verbose=False):
    spec = project.spec
    rc = project.context(0.25, fast=True)
    entries, total = plan(spec, rc)
    chunks = caption_chunks(spec, rc)
    W, H = rc.W, rc.H
    safe = rc.slots["safe"]
    sb = (safe[0], safe[1], safe[0] + safe[2], safe[1] + safe[3])
    lines, warns, starts_all = [], [], []
    lines.append(f"video {W}x{H} @{rc.fps:g}fps · {len(entries)} scenes · {total:.2f}s")
    if rc.words.words:
        lines.append(f"voice: {len(rc.words.words)} words, {rc.words.words[0]['start']:.2f}s → {rc.words.end:.2f}s")
        if rc.words.end > total + 0.05:
            warns.append(f"voice ends at {rc.words.end:.2f}s but the video ends at {total:.2f}s — the last words are cut off")
    for e in entries:
        if scenes and e["id"] not in scenes:
            continue
        sr = SceneRenderer(rc, spec, e, chunks)
        tr = e["transition"]
        lines.append(f"\n[{e['id']}] {e['start']:.2f}s → {e['start'] + e['duration']:.2f}s ({e['duration']:.2f}s)"
                     + (f" · in: {tr[0]} {tr[1]:.2f}s" if tr[0] != "cut" else "") + f" · camera: {sr.camera.preset}")
        layers = [l for l in sr.layers if not l.where.endswith(".background")]
        starts_all.extend(_visual_events(layers, e["start"]))
        starts_all.extend(e["start"] + at for at, _, _ in sr.camera.punches)
        times = sorted({round(min(e["duration"] - 0.01, max(0.0, x)), 2) for l in layers
                        for x in (l.start + (l.enter.duration + l.enter.delay if l.enter else 0) + 0.02, (l.start + l.end) / 2, l.end - 0.05)} |
                       {round(e["duration"] * k, 2) for k in (0.25, 0.5, 0.75)})
        seen = {}
        overlaps = set()
        for t in times:
            rc.collect = []
            sr.frame(t)
            recs = rc.collect
            rc.collect = None
            visible = [r for r in recs if r["opacity"] > 0.4]
            for r in recs:
                seen.setdefault(r["where"], []).append((t, r))
            tx = [r for r in visible if r["type"] in TEXTY]
            for i in range(len(tx)):
                for j in range(i + 1, len(tx)):
                    a, b = tx[i]["bbox"], tx[j]["bbox"]
                    ov = _area(_inter(a, b)) if _inter(a, b)[2] > _inter(a, b)[0] and _inter(a, b)[3] > _inter(a, b)[1] else 0
                    pair = (tx[i]["where"], tx[j]["where"])
                    if ov > 0.12 * min(_area(a), _area(b)) and pair not in overlaps:
                        overlaps.add(pair)
                        warns.append(f"{e['id']} @{t:.2f}s: {tx[i]['id']} overlaps {tx[j]['id']}")
        for l in layers:
            recs = seen.get(l.where, [])
            span = f"{l.start:.2f}–{l.end:.2f}s"
            if not recs:
                if l.type != "captions":
                    warns.append(f"{e['id']}: layer '{l.id or l.where}' ({l.type}, {span}) is never on screen — off-canvas, hidden or transparent?")
                continue
            settled = l.start + (l.enter.duration + l.enter.delay if l.enter else 0) + (l.reveal_end if getattr(l, "reveal", None) else 0)
            later = [(t, r) for t, r in recs if t >= settled - 0.01]
            t_s, r = next(((t, r) for t, r in later + recs if r["opacity"] > 0.95), recs[len(recs) // 2])
            b = r["bbox"]
            desc = f"  {l.id or l.where.split('.')[-1]:<14} {l.type:<9} {span:<13} x {b[0]:.0f}..{b[2]:.0f}  y {b[1]:.0f}..{b[3]:.0f}"
            if l.type == "text":
                desc += f"  \"{str(l.spec.get('text'))[:40]}\""
            lines.append(desc)
            if l.type in ("text", "counter"):
                out = [n for n, cond in (("left", b[0] < sb[0] - 2), ("top", b[1] < sb[1] - 2), ("right", b[2] > sb[2] + 2), ("bottom", b[3] > sb[3] + 2)) if cond]
                if out:
                    warns.append(f"{e['id']}: text {l.id or l.where.split('.')[-1]} \"{str(l.spec.get('text', ''))[:24]}\" leaves the safe area ({', '.join(out)}) at {t_s:.2f}s")
                if l.style.size * l.base["scale"] < 30 * rc.anim_ctx["unit"]:
                    warns.append(f"{e['id']}: text '{l.id or l.where}' size {l.style.size:.0f} is small for phones (use ≥ 36)")
            if b[2] < 0 or b[0] > W or b[3] < 0 or b[1] > H:
                warns.append(f"{e['id']}: '{l.id or l.where}' is outside the frame when settled")
        sr.close()
    # pacing: how long the viewer goes without anything new appearing
    events = sorted({round(e["start"], 2) for e in entries} | set(round(t, 2) for t in starts_all))
    gaps = [(b - a, a) for a, b in zip(events, events[1:] + [total])]
    if gaps:
        longest, at = max(gaps)
        avg = total / max(1, len(events))
        lines.append(f"\npacing: {len(events)} visual changes in {total:.1f}s (one every {avg:.1f}s), longest still stretch {longest:.1f}s at {at:.1f}s")
        limit = 3.5 if spec["height"] > spec["width"] else 6.0
        if longest > limit:
            warns.append(f"nothing new appears for {longest:.1f}s from {at:.1f}s — add a beat (camera punch, new layer, cut) to keep attention")
    lines.append("")
    lines.append("warnings:" if warns else "no warnings")
    seen_w = set()
    for w in warns:
        if w not in seen_w:
            lines.append("  ! " + w)
            seen_w.add(w)
    return "\n".join(lines), len(seen_w)

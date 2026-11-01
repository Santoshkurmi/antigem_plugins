#!/usr/bin/env python3
"""Video Studio — JSON timeline → MP4 with FFmpeg + Pillow. Run `python3 studio.py -h` for commands."""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vs.util import SKILL_DIR, SpecError, VERSION, default_workers, is_android  # noqa: E402


def cmd_doctor(a):
    ok = True

    def line(good, name, info=""):
        nonlocal ok
        ok &= bool(good) or name.startswith("(optional)")
        print(f"  {'✓' if good else '✗'} {name}{(' — ' + info) if info else ''}")
    print(f"Video Studio {VERSION}")
    line(sys.version_info >= (3, 9), "python", sys.version.split()[0] + ("" if sys.version_info >= (3, 9) else " (need 3.9+)"))
    try:
        import PIL
        from PIL import features
        line(True, "pillow", PIL.__version__)
        raqm = features.check("raqm")
        line(raqm, "(optional) raqm text shaping", "ok" if raqm else "missing: Hindi/Nepali (Devanagari) text will render incorrectly")
    except ImportError:
        line(False, "pillow", "missing")
    try:
        import numpy
        line(True, "numpy", numpy.__version__)
    except ImportError:
        line(False, "numpy", "missing")
    ff = shutil.which("ffmpeg")
    line(ff, "ffmpeg", ff or "missing")
    line(shutil.which("ffprobe"), "ffprobe", shutil.which("ffprobe") or "missing")
    if ff:
        ver = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True).stdout.split("\n")[0]
        print(f"    {ver[:80]}")
        filt = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
        for f in ("xfade", "sidechaincompress", "loudnorm", "colorkey", "vignette"):
            line(f" {f} " in filt, f"ffmpeg filter {f}")
        enc = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
        line("libx264" in enc, "encoder libx264")
    for mod, why in (("faster_whisper", "`align` (word timings from any voice file)"), ("edge_tts", "`tts` (free voices with word timings)")):
        try:
            __import__(mod)
            line(True, f"(optional) {mod}", why)
        except ImportError:
            line(False, f"(optional) {mod}", why)
    fonts = [f for f in os.listdir(os.path.join(SKILL_DIR, "fonts")) if f.lower().endswith((".ttf", ".otf"))]
    line(fonts, "bundled fonts", f"{len(fonts)}")
    print(f"  cpu {os.cpu_count()} · android {is_android()} · default workers {default_workers()}")
    if not ok:
        print("\nInstall what is missing:")
        print("  Termux:  pkg install python ffmpeg python-pillow python-numpy")
        print("  Ubuntu/Debian (proot):  apt install -y python3 python3-pil python3-numpy ffmpeg libraqm0")
        print("  pip:     pip install pillow numpy")
    return 0 if ok else 1


def _project(path):
    from vs.render import Project
    return Project(path)


def cmd_validate(a):
    from vs.compose import SceneRenderer, caption_chunks, plan
    p = _project(a.file)
    rc = p.context(0.2, fast=True)
    entries, total = plan(p.spec, rc)
    chunks = caption_chunks(p.spec, rc)
    n = 0
    for e in entries:
        sr = SceneRenderer(rc, p.spec, e, chunks)
        n += len(sr.layers)
        sr.frame(min(e["duration"] - 1e-3, e["duration"] / 2))
        sr.close()
    print(f"ok: {len(entries)} scenes, {n} layers, {total:.2f}s")
    return 0


def cmd_inspect(a):
    from vs.render import inspect
    report, n = inspect(_project(a.file), a.scene)
    print(report)
    return 0


def cmd_timeline(a):
    from vs.compose import plan
    p = _project(a.file)
    rc = p.context(0.2, fast=True)
    entries, total = plan(p.spec, rc)
    for e in entries:
        tr = e["transition"]
        words = " ".join(w["word"] for w in rc.words.between(e["start"], e["start"] + e["duration"]))
        print(f"{e['id']:<14} {e['start']:7.2f} → {e['start'] + e['duration']:7.2f}  ({e['duration']:.2f}s)"
              + (f"  [{tr[0]} {tr[1]:.2f}]" if tr[0] != "cut" else "") + (f"\n    “{words[:160]}”" if words else ""))
    print(f"total {total:.2f}s")
    return 0


def cmd_frame(a):
    from vs.render import still
    p = _project(a.file)
    out = a.out or p.output(f"frame_{(a.scene + '_' + str(a.at)) if a.scene else a.t}.png")
    still(p, out, a.t, a.scene, a.at, a.scale)
    return 0


def cmd_sheet(a):
    from vs.render import sheet
    p = _project(a.file)
    sheet(p, a.out or p.output("sheet.png"), a.scene, a.per, a.cell)
    return 0


def cmd_preview(a):
    from vs.render import render
    p = _project(a.file)
    out = a.out or p.output("preview.mp4")
    fps = a.fps or min(15, p.spec["fps"])

    def once():
        render(_project(a.file), out, q=a.scale, fps=fps, fast=True, crf=30, preset="ultrafast", workers=a.workers,
               scenes=a.scene, with_audio=not a.no_audio, final=False)
    if not a.watch:
        once()
        return 0
    print("watching for changes (Ctrl+C to stop)…")
    last = None
    while True:
        stamp = _watch_stamp(p.dir)
        if stamp != last:
            last = stamp
            try:
                once()
            except SpecError as e:
                print(f"error: {e}")
            except Exception as e:
                print(f"render failed: {e}")
        time.sleep(1.0)


def _watch_stamp(d):
    st = []
    for root, dirs, files in os.walk(d):
        dirs[:] = [x for x in dirs if not x.startswith(".")]
        for f in files:
            if not f.endswith((".mp4", ".png")) or "assets" in root:
                try:
                    st.append((f, os.path.getmtime(os.path.join(root, f))))
                except OSError:
                    pass
    return tuple(sorted(st))


def cmd_render(a):
    from vs.render import render
    p = _project(a.file)
    out = a.out or p.output((p.spec.get("output") or {}).get("name", "video.mp4") if isinstance(p.spec.get("output"), dict) else "video.mp4")
    q = a.scale or 1.0
    render(p, out, q=q, fps=a.fps, fast=False, crf=a.crf, preset=a.preset, workers=a.workers, scenes=a.scene, with_audio=not a.no_audio)
    return 0


def cmd_key(a):
    from PIL import Image
    from vs import raster
    for src in a.images:
        img = Image.open(src)
        out = raster.chroma_key(img, a.color, a.tolerance, a.softness)
        if not a.no_trim:
            out = raster.autocrop(out)
        dst = a.out if (a.out and len(a.images) == 1 and not os.path.isdir(a.out)) else os.path.join(
            a.out or os.path.dirname(os.path.abspath(src)), os.path.splitext(os.path.basename(src))[0] + "_cut.png")
        out.save(dst)
        print(f"{src} → {dst} ({out.width}x{out.height})")
    return 0


def cmd_align(a):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("align needs faster-whisper: pip install faster-whisper  (or use `tts`, which gives timings directly)")
        return 2
    model = WhisperModel(a.model, device="cpu", compute_type="int8")
    segs, info = model.transcribe(a.audio, language=a.lang, word_timestamps=True, vad_filter=True)
    words = [{"word": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3)} for s in segs for w in (s.words or []) if w.word.strip()]
    out = a.out or os.path.splitext(a.audio)[0] + ".words.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=0)
    print(f"{len(words)} words ({info.language}) → {out}")
    return 0


def cmd_tts(a):
    try:
        import edge_tts
    except ImportError:
        print("tts needs edge-tts: pip install edge-tts  (needs internet)")
        return 2
    import asyncio
    text = open(a.text, encoding="utf-8").read() if os.path.exists(a.text) else a.text
    out = a.out or "voice.mp3"
    words = []

    async def run():
        try:
            com = edge_tts.Communicate(text, a.voice, rate=a.rate, boundary="WordBoundary")
        except TypeError:
            com = edge_tts.Communicate(text, a.voice, rate=a.rate)
        with open(out, "wb") as f:
            async for chunk in com.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    s = chunk["offset"] / 1e7
                    words.append({"word": chunk["text"], "start": round(s, 3), "end": round(s + chunk["duration"] / 1e7, 3)})
    asyncio.run(run())
    # edge-tts word boundaries carry no punctuation; copy it back from the script so captions can break at sentences
    from vs.timing import norm_word
    tokens, j = text.split(), 0
    for w in words:
        for k in range(j, min(j + 4, len(tokens))):
            if norm_word(tokens[k]) == norm_word(w["word"]):
                w["word"] = tokens[k].strip("\"'“”‘’()[]")
                j = k + 1
                break
    wpath = os.path.splitext(out)[0] + ".words.json"
    with open(wpath, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=0)
    print(f"voice → {out} · {len(words)} word timings → {wpath}")
    if not words:
        print("warning: no word timings came back; run `align` on the audio instead")
    return 0


def cmd_sfx(a):
    from vs.audio import SFX_NAMES, sfx_path
    if a.name:
        for n in a.name:
            p = sfx_path(n)
            if a.out:
                os.makedirs(a.out, exist_ok=True)
                shutil.copy(p, os.path.join(a.out, f"{n}.wav"))
            print(f"sfx:{n} → {p}")
    else:
        print("built-in sounds (use \"sfx:NAME\" anywhere a sound src is allowed):")
        print("  " + ", ".join(SFX_NAMES))
    return 0


def cmd_presets(a):
    from vs import anim, easing
    from vs.compose import CAMERA_PRESETS, TRANSITIONS
    from vs.captions import STYLES
    from vs.particles import KINDS
    from vs.shapes import KINDS as SHAPES
    from vs.audio import SFX_NAMES
    from vs.text import ALIASES
    from vs.stickman import ACTIONS, EXPRESSIONS, POSES
    from vs.textures import KINDS as TEX
    from vs.spec import LAYOUTS
    rows = [("enter/exit presets", sorted(anim.PRESETS)), ("loops", sorted(anim.LOOPS)), ("easing", sorted(easing.CURVES) + ["spring", "spring(k,d)", "bezier(x1,y1,x2,y2)", "steps(n)"]),
            ("camera", sorted(CAMERA_PRESETS)), ("transitions", sorted(TRANSITIONS)), ("captions styles", sorted(STYLES)),
            ("particles", sorted(KINDS)), ("shapes", sorted(SHAPES)), ("sfx", SFX_NAMES), ("font aliases", sorted(ALIASES)),
            ("layer types", ["image", "video", "text", "counter", "shape", "chart", "particles", "group", "custom", "stickman", "texture"]),
            ("stickman poses", sorted(POSES)), ("stickman actions", sorted(ACTIONS)), ("stickman expressions", sorted(EXPRESSIONS)),
            ("textures", sorted(TEX)), ("layouts", LAYOUTS),
            ("slots", ["full", "safe", "center", "top", "middle", "bottom", "top_half", "bottom_half", "left", "right", "top_left", "top_right",
                       "bottom_left", "bottom_right", "title", "hero", "lower_third", "caption_zone"])]
    for name, vals in rows:
        print(f"{name}:\n  " + ", ".join(vals))
    return 0


def cmd_beats(a):
    from vs.audio import detect_beats
    bpm, beats = detect_beats(a.music)
    out = a.out or os.path.splitext(a.music)[0] + ".beats.json"
    with open(out, "w") as f:
        json.dump({"bpm": bpm, "beats": beats}, f)
    bars = " ".join(f"{b:.2f}" for b in beats[:16])
    print(f"{bpm} BPM, {len(beats)} beats → {out}\nfirst beats: {bars}")
    print('use: "music": {"src": "...", "beats": "auto"} (or this file), then cues "b:9", "bar:3", "nb:2"')
    return 0


def cmd_kit(a):
    from vs.spec import _kit_defs
    defs = _kit_defs()
    names = sorted(defs)
    if a.name:
        names = [n for n in names if any(q.lower() in n.lower() or q.lower() in defs[n].get("about", "").lower() for q in a.name)]
    for n in names:
        d = defs[n]
        params = ", ".join(f"{k}={json.dumps(v, ensure_ascii=False)}" for k, v in (d.get("params") or {}).items())
        print(f"{n}: {d.get('about', '')}\n    params: {params or '-'}")
    if not names:
        print("no matching kit component")
    return 0


def cmd_styles(a):
    from vs.spec import load_style, style_names
    for n in style_names():
        st = load_style(n)
        print(f"{n}: {st.get('about', '')}")
    return 0


def cmd_examples(a):
    from vs.spec import _strip_comments
    ex_dir = os.path.join(SKILL_DIR, "examples")
    for f in sorted(x for x in os.listdir(ex_dir) if x.endswith(".json")):
        with open(os.path.join(ex_dir, f), encoding="utf-8") as fh:
            data = json.loads(_strip_comments(fh.read()))
        print(f"{f[:-5]:<20} {data.get('style', '-'):<15} {data.get('aspect', '9:16'):<5} {data.get('note', '')}")
    return 0


def cmd_new(a):
    ex_dir = os.path.join(SKILL_DIR, "examples")
    src = os.path.join(ex_dir, f"{a.example}.json")
    if not os.path.exists(src):
        names = sorted(f[:-5] for f in os.listdir(ex_dir) if f.endswith(".json"))
        print(f"no example '{a.example}'. examples: {', '.join(names)}")
        return 2
        return 2
    os.makedirs(os.path.join(a.dir, "assets"), exist_ok=True)
    dst = os.path.join(a.dir, "video.json")
    if os.path.exists(dst) and not a.force:
        print(f"{dst} exists (use --force to overwrite)")
        return 2
    shutil.copy(src, dst)
    used = open(src, encoding="utf-8").read()
    copied = []
    for f in sorted(os.listdir(os.path.join(ex_dir, "assets"))):
        if f in used and not os.path.exists(os.path.join(a.dir, "assets", f)):
            shutil.copy(os.path.join(ex_dir, "assets", f), os.path.join(a.dir, "assets", f))
            copied.append(f)
    print(f"created {dst} (from example '{a.example}') and {os.path.join(a.dir, 'assets')}/")
    if copied:
        print("placeholder assets (replace with real ones): " + ", ".join(copied))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="studio.py", description="Video Studio: render JSON timelines to video.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, fn, help_):
        p = sub.add_parser(name, help=help_)
        p.set_defaults(fn=fn)
        return p
    add("doctor", cmd_doctor, "check python, pillow, ffmpeg and fonts")
    p = add("new", cmd_new, "start a project from an example")
    p.add_argument("dir")
    p.add_argument("--example", default="starter")
    p.add_argument("--force", action="store_true")
    for name, fn, h in (("validate", cmd_validate, "check the JSON and build every scene"), ("inspect", cmd_inspect, "layout report + warnings (no video)"),
                        ("timeline", cmd_timeline, "scene times and the words spoken in each")):
        p = add(name, fn, h)
        p.add_argument("file")
        p.add_argument("--scene", action="append")
    p = add("frame", cmd_frame, "render one still PNG")
    p.add_argument("file")
    p.add_argument("--t", type=float, help="global time in seconds")
    p.add_argument("--scene")
    p.add_argument("--at", type=float, default=0.0, help="seconds into --scene")
    p.add_argument("--scale", type=float, default=0.5)
    p.add_argument("--out")
    p = add("sheet", cmd_sheet, "contact sheet of frames from every scene")
    p.add_argument("file")
    p.add_argument("--scene", action="append")
    p.add_argument("--per", type=int, default=3, help="frames per scene")
    p.add_argument("--cell", type=int, default=270, help="cell width in px")
    p.add_argument("--out")
    p = add("preview", cmd_preview, "fast low-res video (cached per scene)")
    p.add_argument("file")
    p.add_argument("--scene", action="append", help="only these scene ids (no audio)")
    p.add_argument("--scale", type=float, default=0.4)
    p.add_argument("--fps", type=float)
    p.add_argument("--workers", type=int)
    p.add_argument("--no-audio", action="store_true")
    p.add_argument("--watch", action="store_true", help="re-render when files change")
    p.add_argument("--out")
    p = add("render", cmd_render, "final video")
    p.add_argument("file")
    p.add_argument("--out")
    p.add_argument("--scene", action="append")
    p.add_argument("--scale", type=float)
    p.add_argument("--fps", type=float)
    p.add_argument("--crf", type=int, default=19)
    p.add_argument("--preset", default="veryfast")
    p.add_argument("--workers", type=int)
    p.add_argument("--no-audio", action="store_true")
    p = add("key", cmd_key, "remove a solid background color (e.g. Flow magenta) → transparent PNG")
    p.add_argument("images", nargs="+")
    p.add_argument("--color", default="#FF00FF")
    p.add_argument("--tolerance", type=float, default=0.18)
    p.add_argument("--softness", type=float, default=0.12)
    p.add_argument("--no-trim", action="store_true")
    p.add_argument("--out")
    p = add("align", cmd_align, "word timings from a voice file (faster-whisper)")
    p.add_argument("audio")
    p.add_argument("--out")
    p.add_argument("--lang")
    p.add_argument("--model", default="base")
    p = add("tts", cmd_tts, "voice-over + word timings with edge-tts")
    p.add_argument("text", help="text or a .txt file")
    p.add_argument("--voice", default="en-US-AndrewNeural")
    p.add_argument("--rate", default="+0%")
    p.add_argument("--out")
    p = add("sfx", cmd_sfx, "list or export built-in sound effects")
    p.add_argument("name", nargs="*")
    p.add_argument("--out")
    add("presets", cmd_presets, "list every preset, loop, easing, transition, style")
    add("examples", cmd_examples, "list example projects (start one with: new DIR --example NAME)")
    p = add("beats", cmd_beats, "detect tempo and beat times of a music file")
    p.add_argument("music")
    p.add_argument("--out")
    p = add("kit", cmd_kit, "list built-in components (use as {\"use\": \"kit.NAME\"}); filter by words")
    p.add_argument("name", nargs="*")
    add("styles", cmd_styles, "list style packs (root \"style\")")
    a = ap.parse_args(argv)
    try:
        return a.fn(a) or 0
    except SpecError as e:
        print(f"error in {e.where}: {e.message}" + (f"\n  hint: {e.hint}" if e.hint else ""), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    except RuntimeError as e:
        print(f"failed: {e}", file=sys.stderr)
        return 1
    except subprocess.TimeoutExpired as e:
        print(f"failed: ffmpeg did not finish in {e.timeout:.0f}s (stuck or the device is too slow): {' '.join(map(str, e.cmd))[:200]}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

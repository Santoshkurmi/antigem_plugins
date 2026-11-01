"""Image loading (cached per process), ffprobe, and sequential video frame decoding through ffmpeg pipes."""
import json
import os
import subprocess

from PIL import Image, ImageOps

from . import raster
from .util import SpecError, color as parse_color


_images = {}
_probes = {}


def load_image(path, key=None, trim=False):
    ck = (path, os.path.getmtime(path), json.dumps(key, sort_keys=True), trim)
    img = _images.get(ck)
    if img is None:
        try:
            img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
        except Exception as e:
            raise SpecError(path, f"cannot open image: {e}")
        if key:
            img = raster.chroma_key(img, key.get("color", "#FF00FF"), float(key.get("tolerance", 0.18)), float(key.get("softness", 0.12)))
        if trim:
            img = raster.autocrop(img)
        if len(_images) > 64:
            _images.clear()
        _images[ck] = img
    return img


def probe(path):
    ck = (path, os.path.getmtime(path))
    if ck in _probes:
        return _probes[ck]
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration",
                              "-of", "json", path], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30).stdout
        data = json.loads(out or "{}")
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        data = {}
    info = {"duration": float((data.get("format") or {}).get("duration") or 0), "has_audio": False}
    for s in data.get("streams", []):
        if s.get("codec_type") == "video" and "width" not in info:
            info["width"], info["height"] = s.get("width"), s.get("height")
            num, _, den = (s.get("r_frame_rate") or "30/1").partition("/")
            info["fps"] = float(num) / float(den or 1) if float(den or 1) else 30.0
        if s.get("codec_type") == "audio":
            info["has_audio"] = True
    _probes[ck] = info
    return info


class VideoReader:
    """Decodes frames of size (w, h) at the output fps, starting at trim[0], already speed-adjusted and fitted."""

    def __init__(self, path, w, h, fps, trim, speed, fit, loop, key=None, focus=None, src_duration=0.0):
        self.path, self.w, self.h, self.fps, self.trim, self.speed, self.fit, self.loop = path, w, h, fps, trim, speed, fit, loop
        end = trim[1] if trim[1] is not None else (src_duration or 0.0)
        self.length = max(0.0, end - trim[0]) if end else 0.0  # seconds of source in use (0 = unknown)
        self.start_off = 0.0
        self.key, self.focus = key, focus
        self.proc = None
        self.index = -1
        self.last = None
        self.ended = False

    def _vf(self):
        f = []
        if self.trim[1] is not None:
            f.append(f"trim=end={max(0.04, self.trim[1] - self.trim[0] - self.start_off):.3f},setpts=PTS-STARTPTS")
        if self.speed != 1:
            f.append(f"setpts=PTS/{self.speed}")
        f.append(f"fps={self.fps}")
        if self.fit == "cover":
            fx, fy = (self.focus or [0.5, 0.5])
            f.append(f"scale={self.w}:{self.h}:force_original_aspect_ratio=increase:flags=bicubic")
            f.append(f"crop={self.w}:{self.h}:(iw-{self.w})*{float(fx)}:(ih-{self.h})*{float(fy)}")
        else:
            f.append(f"scale={self.w}:{self.h}:flags=bicubic")
        if self.key:
            k = self.key if isinstance(self.key, dict) else {"color": self.key if isinstance(self.key, str) else "#FF00FF"}
            c = parse_color(k.get("color", "#FF00FF"))
            f.append(f"colorkey=0x{c[0]:02x}{c[1]:02x}{c[2]:02x}:{float(k.get('tolerance', 0.3))}:{float(k.get('softness', 0.1))}")
        f.append("format=rgba")
        return ",".join(f)

    def _open(self, start=0):
        """Start decoding at output frame `start` (seeks, so a chunk in the middle of a scene starts instantly)."""
        self.close()
        off = start * self.speed / self.fps
        if self.length:
            off = off % self.length if self.loop else min(off, max(0.0, self.length - 0.05))
        self.start_off = off
        cmd = ["ffmpeg", "-v", "error", "-nostdin"]
        if self.loop:
            cmd += ["-stream_loop", "-1"]
        if self.trim[0] + off > 0:
            cmd += ["-ss", f"{self.trim[0] + off:.3f}"]
        cmd += ["-i", self.path, "-an", "-vf", self._vf(), "-f", "rawvideo", "-pix_fmt", "rgba", "-"]
        self.proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=self.w * self.h * 4 * 2)
        self.index = start - 1
        self.ended = False

    def frame(self, i):
        if self.proc is None or i < self.index or i > self.index + self.fps * 2:
            self._open(i)
        size = self.w * self.h * 4
        while self.index < i and not self.ended:
            buf = self.proc.stdout.read(size)
            if len(buf) < size:
                self.ended = True
                break
            self.index += 1
            if self.index >= i:
                self.last = Image.frombuffer("RGBA", (self.w, self.h), buf, "raw", "RGBA", 0, 1).copy()
        return self.last.copy() if self.last is not None else None

    def close(self):
        if self.proc:
            try:
                self.proc.stdout.close()
                self.proc.kill()
                self.proc.wait(timeout=2)
            except Exception:
                pass
            self.proc = None

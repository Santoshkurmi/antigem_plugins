#!/usr/bin/env python3
"""Regenerates docs/kit.md and docs/styles.md from kit/*.json and styles/*.json. Run after editing them."""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vs.spec import _strip_comments, load_style, style_names  # noqa: E402
from vs.util import SKILL_DIR  # noqa: E402

lines = ["# Kit components", "",
         "Ready-made templates. Use: `{\"use\": \"kit.NAME\", \"with\": {params}, \"x\": ..., \"y\": ..., \"at\": ...}`.",
         "Keys next to `use` (x, y, slot, at, until, scale, rotation, enter, exit, loop...) override the component's own.",
         "Colors like `$accent` follow the video's style/theme. List them live with `$VS kit` or `$VS kit WORD`.", ""]
for f in sorted(glob.glob(os.path.join(SKILL_DIR, "kit", "*.json"))):
    with open(f, encoding="utf-8") as fh:
        data = json.loads(_strip_comments(fh.read()))
    lines += [f"## {os.path.splitext(os.path.basename(f))[0]}", "", "| component | what it is | params (defaults) |", "|---|---|---|"]
    for name, d in data.items():
        params = ", ".join(f"`{k}`={json.dumps(v, ensure_ascii=False)}" for k, v in (d.get("params") or {}).items())
        lines.append(f"| `kit.{name}` | {d.get('about', '')} | {params} |")
    lines.append("")
with open(os.path.join(SKILL_DIR, "docs", "kit.md"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))

lines = ["# Style packs", "",
         "`\"style\": \"NAME\"` at the root sets theme colors and fonts, background, camera, transition, color grade and captions.",
         "Anything you set yourself wins (e.g. your own `look` keys are merged over the style's). Override theme colors with",
         "`\"theme\": {\"accent\": \"#00c2ff\"}`. Theme tokens usable in any string value: `$bg $surface $text $muted $accent $accent2 $ink",
         "$paper $line $shadow $font_display $font_body $font_mono $font_hand`.", "",
         "| style | look | accent | fonts (display / body) | background |", "|---|---|---|---|---|"]
for n in style_names():
    st = load_style(n)
    th = st.get("theme", {})
    bg = st.get("background")
    bg = bg if isinstance(bg, str) else (f"texture {bg['texture']}" if isinstance(bg, dict) and bg.get("texture") else "gradient")
    lines.append(f"| `{n}` | {st.get('about', '')} | `{th.get('accent')}` / `{th.get('accent2')}` | {th.get('font_display')} / {th.get('font_body')} | {bg} |")
with open(os.path.join(SKILL_DIR, "docs", "styles.md"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
print("docs/kit.md and docs/styles.md written")

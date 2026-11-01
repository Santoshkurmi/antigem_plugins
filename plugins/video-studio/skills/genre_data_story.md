---
name: Data story / infographic video
description: Numbers-driven videos — statistics explainers, reports, finance, sports stats, comparisons — with counters, charts, progress rings, versus cards and highlighted takeaways.
---

# Data stories

Starting point: `$VS new DIR --example data_story` (16:9). Styles: `box`, `minimal`, `neon`, `news`.

## One number at a time
Each beat: **the number** (big, counting) → **the context** (chart) → **the meaning** (one line). Never show two new
numbers at once.
- Big numbers: `kit.stat_card` or a `counter` at 160–300 px; `format` for money/percent (`"{:,.0f}"`, `"{:.1f}"`), `prefix` "₹"/"$".
- Parts of a whole: `kit.ring_stat`, `kit.progress_bar`.
- Comparisons: `kit.versus`, `chart` `kind: "bar"` with the key bar in `$accent` and others muted gray (`colors` list).
- Trends: `chart` `kind: "line"` with `grow` over 2 s, then `kit.stamp_rubber`/`kit.circle_scribble` on the key point.
- Rankings: `chart` `column` with `grow.stagger`.
- Time passing: `kit.clock`. Many items: `kit.list_item` stack.

## Rules
- Round numbers on screen (say "4.2 million", show `4.2M`).
- Units always visible (suffix or label). Source line (small `text`, 28–32 px, muted) at the bottom when known.
- Sound: `sfx:tick` on chart bars, `sfx:hit` on the big reveal; keep music subtle.
- Check numbers with the user; never invent statistics.

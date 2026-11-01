---
name: True crime / suspense
description: True-crime, mystery, horror and high-suspense videos — cold opens, camcorder footage look, evidence boards with red string, redacted names, heartbeat and drone sound design, tension pacing and cliffhangers.
---

# True crime & suspense

Starting point: `$VS new DIR --example true_crime` (9:16, style `crime`; `noir` for a film look).

## Tension structure (five beats)
1. **Cold open** — the strangest moment first, no context (camcorder look: `kit.rec_overlay`, grayscale photo,
   typewriter text, `sfx:drone` bed). End on a short ominous line (`blur_in` + `sfx:sub_hit`).
2. **Normality** — who, where, when: calm, slower cuts, `kit.lower_third_clean`, `kit.location_tag`.
3. **Disruption** — the event; faster cuts, camera `shake` on the reveal word, `sfx:stinger`.
4. **Investigation** — evidence board (`"layout": "board"`, `kit.evidence_photo`, red string lines, `kit.sticky_note`,
   `kit.redact` names revealed on their word, `kit.stamp_rubber` "UNSOLVED"/"CLOSED").
5. **The question** — a cliffhanger line alone on black, then cut (or "Part 2" `kit.stamp_tab`).

## Rules
- Darkness and space: let text sit alone on black; hold 1–1.5 s of near-silence before reveals.
- Red is the only accent. Fonts: `mono` for facts/dates, `display` for verdict lines.
- Sound carries the fear: `sfx:drone` under scenes, `sfx:heartbeat` during build-ups, `sfx:stinger`/`sfx:sub_hit` on reveals,
  `sfx:typing` under typed facts. Keep voice clear; music volume ≤ 0.2.
- Transitions: `dip` (to black) between beats, hard `cut` inside them.
- Captions `minimal` (mono). Use `kit.spotlight` to focus one detail of a photo.
- Be careful with real cases: stick to facts the user provides; never present speculation as fact.

# Style packs

`"style": "NAME"` at the root sets theme colors and fonts, background, camera, transition, color grade and captions.
Anything you set yourself wins (e.g. your own `look` keys are merged over the style's). Override theme colors with
`"theme": {"accent": "#00c2ff"}`. Theme tokens usable in any string value: `$bg $surface $text $muted $accent $accent2 $ink
$paper $line $shadow $font_display $font_body $font_mono $font_hand`.

| style | look | accent | fonts (display / body) | background |
|---|---|---|---|---|
| `bold_explainer` | Bright faceless explainer: saturated flat colors, bold display type, white stickers, punchy pops. | `#facc15` / `#fb7185` | display / sans | gradient |
| `box` | Dark editorial cards: deep indigo, yellow highlights, clean sans, box captions. | `#ffd60a` / `#7c6cff` | display / sans | gradient |
| `chalkboard` | Classroom chalkboard: chalk-white handwriting on green-black board, yellow chalk highlights. | `#ffd166` / `#ff8fa3` | hand / hand | texture blackboard |
| `cinematic` | Warm cinematic film look with elegant serif titles and soft dissolves (add look.letterbox for 16:9). | `#e8b04b` / `#c2452d` | serif / sans | #0d0b09 |
| `crime` | True-crime suspense: cold desaturated grade, crushing vignette, blood-red accents, typewriter labels, dips to black. | `#c1121f` / `#c1121f` | display / sans | texture noise |
| `cute_toon` | Soft pastel cartoon: rounded type, pink/purple accents, bouncy motion — kids, lifestyle, wholesome stories. | `#ff6f91` / `#6c5ce7` | rounded / rounded | gradient |
| `documentary` | Vox-style explainer documentary: cream paper, black ink, red/yellow accents, paper cut-outs, box captions. | `#e63946` / `#f4a261` | display / sans | texture paper |
| `doodle` | Hand-drawn whiteboard/notebook: handwriting everywhere, wobbly 'boiling' lines, stick figures, marker colors. | `#ff6b35` / `#2a9d8f` | hand / hand | texture notebook |
| `kinetic` | High-contrast kinetic typography: black, white and one loud yellow; hard cuts and camera punches. (no captions by default) | `#ffd60a` / `#ff375f` | display / sans | #0a0a0a |
| `luxury` | Luxury / premium: black and gold, serif display, slow moves, dissolves. | `#c9a45c` / `#e8d3a3` | serif / book | gradient |
| `minimal` | Clean minimal: white space, black type, one blue accent, gentle fades — tutorials, corporate, product. | `#2563eb` / `#f59e0b` | sans / sans | #fafafa |
| `neon` | Neon tech / cyber: near-black, cyan and magenta glow, monospace accents, bloom. | `#00e5ff` / `#ff2bd6` | display / sans | gradient |
| `news` | Broadcast news: navy and red, strong sans, lower thirds and tickers, quick wipes. | `#d62828` / `#ffd60a` | display / sans | gradient |
| `noir` | Dark film-noir documentary: teal/amber grade, heavy grain and vignette, red emphasis, slow push-ins. | `#e0a33a` / `#d62828` | display / sans | texture noise |
| `retro8bit` | 8-bit arcade: black screen, pixelated image, scanlines, chiptune blips, pixelize transitions. | `#ffd60a` / `#ff004d` | display / mono | #000000 |
| `sticker` | Bold sticker explainer: dotted paper, chunky rounded type, cut-outs with white borders, pop captions. | `#ff5a5f` / `#00a6ed` | rounded / rounded | texture dots |
| `vaporwave` | Vaporwave/VHS: pink-purple gradients, cyan accents, chromatic shift, tape noise, glitch transitions. | `#00f0ff` / `#ff71ce` | display / sans | gradient |
| `vintage` | Old film / archival: sepia-warm, heavy grain, vignette, serif type, dips — history and nostalgia. | `#d9a441` / `#a63d2a` | serif / book | texture paper |

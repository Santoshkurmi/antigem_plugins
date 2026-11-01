# Kit components

Ready-made templates. Use: `{"use": "kit.NAME", "with": {params}, "x": ..., "y": ..., "at": ...}`.
Keys next to `use` (x, y, slot, at, until, scale, rotation, enter, exit, loop...) override the component's own.
Colors like `$accent` follow the video's style/theme. List them live with `$VS kit` or `$VS kit WORD`.

## broadcast

| component | what it is | params (defaults) |
|---|---|---|
| `kit.lower_third_bar` | Name + role strap: accent bar, dark panel wiping in, two lines of text. Use slot lower_third. | `name`="Name Surname", `role`="Role / title", `color`="$accent" |
| `kit.lower_third_clean` | Minimal lower third: name, thin accent line, role. No panel. Anchored left. | `name`="Name Surname", `role`="Role", `color`="$accent", `text_color`="$text" |
| `kit.breaking_news` | News banner: red BREAKING tag + white headline bar + scrolling ticker. Full width, put near the bottom (y ~ 78%). | `label`="BREAKING", `headline`="Headline goes here", `ticker`="More news • more news • more news", `color`="#d62828" |
| `kit.live_badge` | LIVE badge with blinking dot (corner). | `text`="LIVE", `color`="#ff3b30" |
| `kit.rec_overlay` | Camcorder overlay: blinking REC, corner brackets, timestamp text (found footage, vlogs, crime reconstruction). Full frame. | `stamp`="PLAY ▶  00:12:47", `date`="OCT 14 1999" |
| `kit.subscribe_button` | YouTube-style subscribe: button pops, a cursor clicks it, it turns grey 'SUBSCRIBED' with a bell. | `click`=0.9 |
| `kit.location_tag` | Place + date tag with a map-pin icon (travel, documentary). Anchored left. | `place`="Kathmandu, Nepal", `date`="March 2024", `color`="$accent" |
| `kit.corner_bug` | Small persistent channel/brand text in a corner (put x/y near a corner, camera false). | `text`="@channel", `opacity`=0.75 |

## data

| component | what it is | params (defaults) |
|---|---|---|
| `kit.stat_card` | Big counting number + label on a card. | `value`=87, `prefix`="", `suffix`="%", `label`="of people agree", `format`="{:,.0f}", `color`="$accent", `card`="$surface" |
| `kit.ring_stat` | Progress ring filling to value% with the number inside. | `value`=72, `label`="", `size`=320, `color`="$accent", `track`="#ffffff22" |
| `kit.progress_bar` | Labeled bar that fills to value% over 'dur' seconds. | `label`="Progress", `value`=65, `w`=800, `dur`=1.2, `color`="$accent" |
| `kit.versus` | A vs B comparison: two names split by a VS badge. | `a`="Cats", `b`="Dogs", `color_a`="#0a84ff", `color_b`="#ff375f" |
| `kit.countdown_number` | Huge rank number that stamps in (#5, #4...). Pair with a title. | `number`="#5", `color`="$accent", `size`=320 |
| `kit.map_pin` | Map pin that drops onto (x, y) with a pulsing ring and a label above. | `label`="Here", `color`="#ff375f", `size`=80 |
| `kit.timeline_point` | One timeline stop: dot + year above + text below. Place several along a kit.timeline_line. | `year`="1990", `text`="Something happened", `color`="$accent" |
| `kit.timeline_line` | Horizontal line that draws across at height y (frame px). Put kit.timeline_point items on it (their center = this y). | `y`=960, `x1`=80, `x2`=1000, `dur`=1.5, `color`="$muted" |
| `kit.clock` | Analog clock whose hands spin `turns` times during `dur` seconds (time passing). | `size`=300, `turns`=3, `dur`=2.5, `color`="$text", `face`="$surface" |

## devices

| component | what it is | params (defaults) |
|---|---|---|
| `kit.browser_frame` | Browser window showing a screenshot; `scroll` px scrolls the page down over `dur` seconds. | `src`="screenshot.png", `url`="example.com", `w`=960, `h`=640, `scroll`=0, `dur`=3 |
| `kit.phone_frame` | Phone mock-up with a screenshot/video frame on screen. | `src`="screenshot.png", `h`=1100, `color`="#111111" |
| `kit.app_window` | Dark app/editor window with a title bar and an image inside (code, dashboards). | `src`="screenshot.png", `title`="app", `w`=960, `h`=620 |

## doodle

| component | what it is | params (defaults) |
|---|---|---|
| `kit.speech_bubble` | Speech bubble with a tail pointing down-left (put it above-right of a character's head). | `text`="Hello!", `size`=48, `w`=520, `h`=240, `fill`="#ffffff", `color`="#111111" |
| `kit.thought_bubble` | Thought cloud with trailing dots toward the lower left. | `text`="Hmm...", `size`=48, `w`=520, `h`=260, `fill`="#ffffff", `color`="#111111" |
| `kit.sticky_note` | Yellow sticky note with handwritten text, slightly tilted. | `text`="Remember this!", `color`="#ffe66d", `rotation`=4, `size`=54 |
| `kit.idea_bulb` | Light-bulb 'idea!' icon with rays that pop out. | `size`=220, `color`="#ffd60a", `ink`="#111111" |
| `kit.doodle_heart` | Hand-drawn heart that draws itself and beats. | `size`=220, `color`="#ff375f" |

## frames

| component | what it is | params (defaults) |
|---|---|---|
| `kit.polaroid` | Instant photo: white frame, image, handwritten caption; drops in tilted. | `src`="photo.jpg", `caption`="", `rotation`=-4, `w`=520, `focus`=[0.5, 0.5] |
| `kit.evidence_photo` | Polaroid pinned to a board with a red pin (true crime / investigation boards). | `src`="photo.jpg", `caption`="", `rotation`=3, `pin`="#d62828" |
| `kit.print_photo` | Photo print with thin white border and soft shadow. | `src`="photo.jpg", `w`=640, `rotation`=2 |
| `kit.photo_card` | Rounded photo card with shadow (modern/clean). | `src`="photo.jpg", `w`=720, `h`=480, `radius`=32 |
| `kit.sticker` | Cut-out with a thick white sticker border and small shadow (explainers, Vox collage). Use transparent PNGs. | `src`="cutout.png", `h`=520, `rotation`=-3, `border`="#ffffff", `width`=14 |
| `kit.paper_cutout` | Cut-out with a cream paper border, slight hand-made wobble (documentary collage). | `src`="cutout.png", `h`=520, `rotation`=2 |
| `kit.taped_photo` | Photo stuck on with two strips of tape. | `src`="photo.jpg", `w`=600, `rotation`=-2 |

## marks

| component | what it is | params (defaults) |
|---|---|---|
| `kit.stamp_rubber` | Rubber stamp (CLASSIFIED, SOLD OUT...): slams in tilted, inky multiply blend. Use at most twice per video. | `text`="CLASSIFIED", `color`="$accent2", `size`=92, `rotation`=-9 |
| `kit.stamp_seal` | Round seal (APPROVED, VERIFIED) with a double ring. | `text`="VERIFIED", `color`="$accent", `size`=300 |
| `kit.stamp_tape` | Diagonal hazard/caution tape with text. | `text`="DO NOT CROSS", `color`="#ffd60a", `text_color`="#111111", `w`=1300, `rotation`=-7 |
| `kit.stamp_scrawl` | Handwritten red note with a scribbled underline ("the real reason?"). | `text`="really?!", `color`="$accent2", `size`=96 |
| `kit.stamp_tab` | File-folder tab label (case files, chapters). | `text`="CASE #07", `color`="$accent", `text_color`="$ink" |
| `kit.burst` | Starburst badge behind short text (NEW!, 50% OFF, WOW). | `text`="NEW!", `color`="$accent", `text_color`="$ink", `size`=260 |
| `kit.circle_scribble` | Hand-drawn circle that draws itself around something. | `w`=420, `h`=240, `color`="$accent2", `width`=9 |
| `kit.underline_scribble` | Rough marker underline that draws on (put it under a word). | `w`=400, `color`="$accent", `width`=10 |
| `kit.arrow_doodle` | Curvy hand-drawn arrow from (x1,y1) to (x2,y2), drawn on. Coordinates are frame px; don't set x/y. | `x1`=200, `y1`=400, `x2`=600, `y2`=700, `bend_x`=520, `bend_y`=420, `color`="$accent2", `width`=9 |
| `kit.check_mark` | Green tick that draws on. | `size`=160, `color`="#30d158" |
| `kit.cross_mark` | Red X that draws on (wrong / myth). | `size`=160, `color`="#ff3b30" |
| `kit.highlight_box` | Pulsing outline box to point at part of an image/screen. Set x/y/w/h. | `w`=400, `h`=200, `color`="$accent", `radius`=16 |
| `kit.spotlight` | Darkens the whole frame except a circle at (x, y) — draws the eye. Put it above the layers it dims. | `x`=540, `y`=800, `size`=420, `dim`=0.7 |
| `kit.callout` | Dot on a point (px, py) with a leader line to a label at (lx, ly). Frame px coordinates; don't set x/y. | `text`="Label", `px`=540, `py`=900, `lx`=820, `ly`=650, `color`="$accent", `text_color`="$text", `size`=42 |

## retro

| component | what it is | params (defaults) |
|---|---|---|
| `kit.pixel_dialog` | Game dialogue box: thick border, text typed on with blips, blinking ▼. | `name`="HERO", `text`="It's dangerous to go alone!", `w`=960, `h`=300 |
| `kit.pixel_title` | Arcade title: chunky text with hard drop shadow, slams down, flickers. | `text`="GAME OVER", `color`="$accent", `shadow`="$accent2", `size`=150 |
| `kit.press_start` | Blinking PRESS START prompt. | `text`="PRESS START", `color`="#ffffff", `size`=56 |
| `kit.score_counter` | Arcade SCORE readout that counts up. Anchored left. | `label`="SCORE", `to`=12500, `dur`=1.5 |
| `kit.health_bar` | Segmented health/XP bar that drains in steps from full to `value` (0–1). | `label`="HP", `value`=0.3, `color`="#30d158", `w`=640 |

## social

| component | what it is | params (defaults) |
|---|---|---|
| `kit.post_card` | Social post card: avatar, name, handle, text, like counter that counts up. Avatar optional (src). | `name`="Display Name", `handle`="@handle", `text`="Post text goes here.", `likes`=12400, `initial`="A", `color`="$accent" |
| `kit.comment_bubble` | Viewer comment card (avatar letter, name, comment) — 'you asked' moments. | `name`="viewer123", `text`="How does this work??", `initial`="V", `color`="#5e5ce6" |
| `kit.notification` | Phone notification banner sliding down (app name, title, message). | `app`="MESSAGES", `title`="Mom", `text`="Call me when you see this", `color`="#34c759" |
| `kit.chat_left` | Incoming chat bubble (grey, left). Stack several for a conversation. Anchored left. | `text`="hey, you up?", `size`=44 |
| `kit.chat_right` | Outgoing chat bubble (blue, right). Anchored right. | `text`="on my way", `size`=44, `color`="#0a84ff" |

## text

| component | what it is | params (defaults) |
|---|---|---|
| `kit.kicker_bar` | Small uppercase label with an accent bar on its left (section tag). Anchored left. | `text`="CHAPTER ONE", `color`="$accent", `text_color`="$text", `size`=38 |
| `kit.kicker_chip` | Label on a solid rounded chip that pops in. | `text`="BREAKING", `color`="$accent", `text_color`="$ink", `size`=36 |
| `kit.kicker_bracket` | Monospace label in [ brackets ], typed on. | `text`="FILE 07", `color`="$accent", `size`=40 |
| `kit.kicker_rule` | Thin accent rule that draws, with a label under it. Anchored left. | `text`="THE BACKSTORY", `color`="$accent", `text_color`="$muted", `size`=34 |
| `kit.kicker_index` | Big number + label ("01  The setup") for numbered parts. Anchored left. | `number`="01", `text`="The setup", `color`="$accent", `text_color`="$text" |
| `kit.headline_underline` | Big title revealed word by word, then an accent underline sweeps under it. | `text`="The *big* question", `size`=110, `color`="$text", `accent`="$accent", `line_width`=420 |
| `kit.headline_box` | Title printed on a solid block that wipes in (tabloid / news headline). | `text`="HEADLINE", `size`=96, `color`="$ink", `box`="$accent" |
| `kit.keyword_marker` | Words on a highlighter-pen sweep (marks the key term). | `text`="key term", `size`=80, `color`="$ink", `marker`="$accent" |
| `kit.quote_card` | Pull quote with big quotation mark, revealed word by word, and the author. | `text`="Quote text goes here.", `author`="Someone", `color`="$text", `accent`="$accent", `size`=64 |
| `kit.chapter_card` | Full-frame chapter opener: big number, title, rule. Several layers; best in an otherwise empty scene. | `number`="1", `title`="Chapter title", `color`="$text", `accent`="$accent" |
| `kit.redact` | Text hidden under a black redaction bar that slides away at `reveal` (a cue relative to this layer: seconds, 'w:word', 'end'). | `text`="TOP SECRET NAME", `size`=64, `font`="$font_mono", `color`="$text", `bar`="#000000", `reveal`=1.5 |
| `kit.list_item` | One bullet point (dot + text) sliding in. Stack several with increasing y and at. Anchored left. | `text`="A point worth making", `color`="$text", `bullet`="$accent", `size`=46 |
| `kit.checklist_item` | Checkbox + text; the tick draws itself at `check` seconds. Anchored left. | `text`="Done thing", `color`="$text", `tick`="$accent", `size`=46, `check`=0.5 |

# Polishing a screen recording

Times are **ms on the original recording**. Positions are **normalized 0..1 of the recorded screen** and move
with zooms. Items you add are marked as AI items. `auto_edit` replaces only automatic items, never yours or
the user's.

## 1. Understand the recording

1. `list_projects` → pick the `recording` (the newest is first by default). Note `smart_mode_data`.
2. `get_project`: length, trim, cuts, what is already edited.
3. With Smart mode data:
   - `get_timeline` lists taps with the element label and rect, typing, scrolls, screen changes, the keyboard
     and the user's marks. Filter with `types` and `limit` on long recordings.
   - `get_screen_at` `time_ms` shows what was on screen. `interactive_only=true` gives just the buttons and
     fields.
   - `find_ui_element` `query="Settings"` tells you when that element was visible, and its rect.
4. Without Smart mode data (imported videos, or apps that hide their UI from accessibility), look at frames:
   `get_frame` `styled=false` at a few times, or `get_storyboard`. Taps found from the pixels still appear in
   the project's taps.

## 2. Quick path

```json
{"name": "auto_edit", "arguments": {"zoom_intensity": 0.55, "captions": true, "highlights": true, "chapters": true, "privacy_blur": true, "smart_speed": false}}
```
Then `get_storyboard` `count=8`. Fix only what looks wrong, using the task tools below. Re-running `auto_edit`
with other options replaces its own items; `clear_auto_edit` removes them all.

Goals map to settings:

| Goal | Settings |
| --- | --- |
| Tutorial | captions on, chapters on, highlights `OUTLINE`, moderate zoom (0.5), then `set_card` intro |
| Social / Shorts | `set_style aspect=PORTRAIT_9_16`, tighter zoom (0.7), `set_caption_style animation=KARAOKE` or `POP`, `smart_speed` on |
| Bug report | zoom low (0.3), captions on, no speed changes, `add_annotation` arrows at the problem, export `guide_md` too |
| App Store preview | `set_style device_frame=…`, `set_layout` showcase panel, no tap indicators |

## 3. Task tools

| Do | Tool and key arguments |
| --- | --- |
| Zoom | `add_zoom` `start_ms, end_ms` with `x, y, scale` (2 = twice), **or** `rect` (zoom fits it), **or** `element` (label tapped near `start_ms`). Change one with `update_zoom zoom_id=…`. Keep zooms ≥ 1.2 s; leave about 0.3 s before the tap so the viewer sees it coming |
| Captions | `add_caption start_ms end_ms text`. Wrap key words in “curly quotes” to highlight them. `set_captions items=[…]` replaces all of them (rewrite, translate, voice-over script). Style: `set_caption_style` (font, size 0.025–0.08, colours, position, `animation`, uppercase) |
| Arrows, text, boxes, steps, emoji | `add_annotation type=TEXT\|ARROW\|RECT\|ELLIPSE\|LINE\|HIGHLIGHTER\|STEP_BADGE\|EMOJI\|CALLOUT`, placed with `x, y` (`to_x, to_y` for arrows), `rect`, or `element` |
| Point at a control | `add_highlight style=GLOW\|OUTLINE\|SPOTLIGHT\|BLUR_OTHERS\|HIDE_OTHERS` with `element` or `rect` |
| Magnify | `add_lens` (`lift=true` lifts the element out of the screen instead of a loupe) |
| Hide private things | `add_blur kind=BLUR\|PIXELATE\|ERASE\|BLACKOUT\|SOLID` with `element` or `rect`. `track_region id=…` makes it follow scrolling content |
| Timeline | `set_trim`, `cut_range` (`restore=true` undoes a cut), `set_speed` (0.25–8×), `add_freeze`, `add_chapter` |
| Look | `set_style` (aspect, background, wallpaper, padding, corners, shadow, device frame), `set_layout` (device mockups, showcase panel, colour grade, camera layouts), `set_motion` (frame animation presets, keyframes, float, 3D tilt, transitions at cuts), `set_tap_style`, `set_card` (intro / outro) |
| Camera bubble | `set_webcam` (corner or `x, y`, shape, size). Different positions over time: kind `camera_move` with `upsert_items` (see `json-editing.md`) |
| Sound | `set_audio` (mic / app volume, voice leveling, `music_path`, ducking) |
| Show / hide | `set_item id enabled=false` (one item) or `set_layers` (whole layers). Nothing is lost |
| Remove | `remove_items ids=[…]` |

Prefer `element` over raw coordinates when Smart mode knows the label: the app snaps to the real control.

## 4. Privacy check

Run `get_review` before any export of a recording that will be shared. It lists:
- the notification panel and popups;
- passwords, e-mails, phone and card numbers, OTPs;
- the keyboard, the recording bubble, the status bar, idle parts.

Each entry has a `key` and possible actions. Apply the ones that matter with `apply_review key=… action=BLUR`
(or `CUT`, `SPEED_UP`, `ERASE`, `CLEAN`, `DISMISS`…). Ask the user when it is a judgement call (for example,
whether their e-mail address may be shown).

## 5. Recording

- `recorder_status` tells you whether a recording is idle, running or paused.
- `start_recording` asks the user. The phone shows the system consent dialog, and nothing records until they
  accept. Poll `recorder_status`.
- While recording: `pause_recording`, `resume_recording`, `mark_recording` (a mark plugins can react to).
- `stop_recording` stops it; the new project appears in `list_projects` (auto-polished if the user turned on "Auto-polish when you stop").
- Recordings are saved in pieces (default every 5 minutes), so a crash keeps what was recorded.
- `list_device_videos` + `import_video` bring in a recording made with another app. Listing needs the
  "Let AI find videos on this phone" switch in AI access.

## 6. Export

`export` `kind=mp4` (`resolution`, `fps`, `quality`, `codec`, `max_size_mb`, `start_ms`/`end_ms` for a part,
`aspects=[…]` for several formats at once). Other kinds: `gif`, `guide_pdf` / `guide_md` (step-by-step guide
from captions and taps), `html_demo` (interactive click-through), `srt` / `vtt`, `chapters`, `frame_png`
(`time_ms`). Then:
1. Poll `get_export_status job_id=…` until the state is `done`.
2. `get_export_result` gives the saved location. Text kinds return their content inline.

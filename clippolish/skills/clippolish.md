---
name: ClipPolish videos (screen recordings and studio videos)
description: Use the ClipPolish MCP server well. Polish screen recordings (zooms on taps, captions, blur, highlights, styles, speed, export), make studio videos from scenes, pictures, videos, text and animation timed to a transcript, and write or install ClipPolish plugins. Check the connection, look before and after every edit, and verify with frames.
---

# ClipPolish videos

ClipPolish is an Android screen recorder with an editor, and it also builds **studio videos**: videos made
from scenes, pictures, videos, text and motion graphics instead of a recording. Its MCP server
works **directly on the app's data**. It never taps the app, so it works with ClipPolish in the background.
Every edit is one undoable step named "AI: …" that shows up live in the editor.
**Follow this guide** and read a detail file when your task needs it.

Detail files (read with `get_skill_file`, name `clippolish`):

| File | When |
| --- | --- |
| `recordings.md` | Polishing a screen recording: what happened in it, zooms, captions, privacy, styles, speed, review, export |
| `studio.md` | Making a studio video: look, scenes, elements, transcript and word cues, templates, motions, checking, export |
| `json-editing.md` | Anything the task tools don't cover: `describe_model`, `get_project_json`, `patch_project`, `upsert_items`, `batch`, units |
| `plugins.md` | Writing, testing and installing ClipPolish plugins (rules, live rules, looks, style packs, layouts, templates, motions), plugin websites |
| `troubleshooting.md` | A tool returned an error or the result looks wrong |

## 0. Check the connection

You need tools such as `list_projects`, `get_frame`, `studio_catalog` and `help`. Depending on the client
they may have a prefix (`clippolish_list_projects`, `mcp__clippolish__list_projects`). Call `help` once: it
returns the map of tools.

If the tools are missing or every call fails to connect, stop and tell the user how to connect:

1. ClipPolish → home → **Let your AI edit your videos → Connect** (or Settings → AI access).
2. Switch **MCP server** on. With the AI on the same phone, choose **This phone only**.
3. AntiGem often holds port 8765 already. If the server does not start, or another app answers on 8765, set the
   **Port** to 8766.
4. Copy the URL (`http://127.0.0.1:<port>/mcp`) and the key from that screen. In AntiGem → Settings → the
   agent's MCP page, add an HTTP server named `clippolish` with that URL and the header
   `Authorization: Bearer <key>`. The screen also has a ready "Claude Code" command and a JSON config to copy.
5. Reload the tools or start a new chat.

Never print or repeat the key in chat.

## 1. Golden rules

1. **Look before you edit.** Use `list_projects` to see what exists. Each project has a `kind`: `recording` or
   `studio_video`. Then use `get_project` / `get_studio`, and `get_timeline` for recordings.
2. **Check after you edit.** Use `get_frame` (`styled=true` is exactly what the export renders) at the moments
   you changed, or `get_storyboard` for the whole video in one image. Fix what looks wrong before you report.
3. **Units.** Task tools take **milliseconds** (`start_ms`, `time_ms`). For recordings these are times on the
   original recording, so cuts and speed changes don't shift them. The generic JSON tools use **model units**:
   µs for `*Us` and `t` fields. Positions are always **normalized 0..1** (x right, y down).
4. **Many edits = one step.** Put them in `batch` (`atomic` by default: any failure rolls back everything). The
   user can then undo your whole change at once.
5. **`project_id`.** It defaults to the most recently edited project. Pass it explicitly once you know it.
6. **Ask the user first** before anything that leaves the app or is hard to undo:
   - `export` saves a file to the gallery;
   - `delete_project`;
   - `start_recording` shows the system consent dialog;
   - `install_plugin` from the internet;
   - `set_captions` replaces all captions.

   `delete_project` and `export` can also be turned off in the app; if a call says so, tell the user.
7. **Nothing runs on its own in ClipPolish.** Suggestions from `get_review` are only applied when you or the
   user choose one (`apply_review`).

## 2. Pick the workflow

| The user wants | Do |
| --- | --- |
| "Polish / edit my recording", tutorials, bug reports, app demos | `recordings.md`. Quick path: `auto_edit` → look → fix with task tools → `get_storyboard` |
| A video that is **not** a recording: explainer, story, quote, data, promo, "make a video about…" | `studio.md`. `studio_catalog` → `create_video_project` → `set_transcript` (if there is speech) → `place_template` / `add_scene` / `add_element` → check frames |
| A 2D Video Editing Studio project (EDIT.json, WORDS.tsv, VO.wav) | `import_studio_project` (folder, .zip, or the JSON text), then check it like a studio video |
| Something reusable ("always do X to my recordings", a look, templates) | `plugins.md` |
| Anything the task tools can't express | `json-editing.md`. The generic tools reach **every** field the app has |

## 3. Seeing

| Need | Tool |
| --- | --- |
| One moment exactly as exported | `get_frame` `time_ms`, `styled=true` (default), `max_size` 768–1024 |
| The raw recording without the edit | `get_frame` `styled=false` |
| The whole edit at a glance | `get_storyboard` `count` 6–12 |
| What the user tapped, typed, scrolled (recordings with Smart mode) | `get_timeline`, then `get_screen_at` / `find_ui_element` for labels and rects |
| The full edit state | `get_project` (readable) or `get_project_json` with `paths` (exact JSON) |
| A studio video's scenes and elements, and cues that don't match the spoken words | `get_studio` |

Frames cost tokens. Check the moments you changed rather than every second, and use a storyboard for the
overview.

## 4. Finishing

1. Use `get_storyboard` and look at it critically: overlapping text, text too small, wrong timing, empty
   frames, private data visible.
2. Tell the user what you did, in plain words, with times. Tell them that everything can be undone in the
   editor (`undo` also works).
3. Export only when asked: `export` (`kind` mp4 / gif / guide_pdf / guide_md / html_demo / srt / vtt /
   chapters / frame_png). Poll `get_export_status` every few seconds, then `get_export_result` for where it was
   saved.

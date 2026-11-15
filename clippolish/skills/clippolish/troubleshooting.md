# Troubleshooting

| You see | Do |
| --- | --- |
| No ClipPolish tools, or "connection refused" | The server is off or on another port. Tell the user: ClipPolish → AI access → switch MCP server on, "This phone only", check the Port (8766 if 8765 is taken), copy the URL and key into the agent's MCP settings, then reload the tools |
| 401 / "unauthorized" | Wrong or regenerated key. Ask the user to copy the key again from AI access. Never ask them to paste it in chat if the agent's settings can hold it |
| Tools worked, then stopped while the app was in the background | The phone paused ClipPolish to save battery. Ask the user to allow it to run unrestricted (AI access → Open battery settings) |
| "No projects yet" | Nothing recorded or created. `create_video_project`, `import_video`, or ask the user to record (`start_recording` asks them) |
| "Unknown project_id" | Use an id from `list_projects`; ids look like `p_ab12cd34ef` |
| "Unknown field(s) for element: …" / "Invalid …" | The JSON doesn't match the model. Run `describe_model` for that type; fields are case-sensitive camelCase, enums UPPER_CASE, times µs, colours ARGB numbers |
| "Cue '…' not found in the transcript" | The word isn't in the transcript (spelling, other language form, or no transcript yet). `get_project_json paths=["/transcript/words"]` shows the words; use another word, `@line`, or seconds |
| "start is past the end … a number cue is seconds" | `"1846"` means 1846 s. For a spoken number use `"w:1846"` |
| "IMAGE needs src" | Bring the file in first (`files-and-preview.md` §1), then use the returned path as `src` |
| "ClipPolish can't read /storage/… (Android keeps other apps' files private)" | Expected for files outside the shared folder. Copy the file into the shared folder, use `upload_file` + curl, or pass an `https://` link. Never send the file's contents |
| "No shared folder yet" | The user hasn't set one up. Use `upload_file` + curl, or ask them: ClipPolish → Settings → AI access → Shared folder → Set up folder |
| Upload answers 401 "expired upload key" | The 10-minute key ran out (or it was for another session). Call `upload_file` again |
| A preview shows as a plain link, not a player | Post the `markdown` line exactly, on its own line: `![…](…/index.m3u8)` |
| A preview says "This video was deleted" / won't play | The project was deleted, or the user reset preview links: make a new one. If AI access is off, it can't play until the user switches it on |
| A preview stutters | The project is heavy for live rendering (several video layers). Make a new preview with `quality=480p`; finished pieces replay smoothly |
| An element doesn't appear | Check its time against its scene. Scene elements only show while their scene is on screen, and `enabled` must be true. A `get_frame` right at the start shows the first frame of the entrance; look about 0.6 s later |
| Text overlaps or is cut off | Use layout slots (`slot`), a smaller `style.size`, shorter text, or another layout. Check portrait slots (`slots_tall`) |
| A plugin's style pack, layout or template is missing | `list_plugins`: is it installed? Pack and layout ids must be unique; a later plugin with the same id wins |
| "'…' can't run inside batch" | Run that call on its own, then batch the rest |
| "Exporting via AI is disabled…" / "Deleting is disabled…" | The user turned it off in AI access → Permissions. Tell them; don't work around it |
| Export takes long | Normal for long or 4K videos. Poll `get_export_status` every 3–5 s; don't start it twice |
| The app crashed | `get_crash_log` returns the last crash report; include it when you tell the user |
| A colour comes out wrong (pink instead of blue…) | A string colour was written as `"#AARRGGBB"`. Strings are `"#RRGGBB"`, or `"#RRGGBBAA"` with alpha last |
| A mask, matte, blend or adjustment layer seems to do nothing | Check with `get_frame` at a moment the element is fully in. Adjustment layers only change elements below them (`z`) inside their box; a matte's `from` element must be on screen |

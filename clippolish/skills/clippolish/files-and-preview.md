# Files in, preview out

## 1. Getting files into a project (pictures, sounds, videos, fonts…)

**Never put file contents in a tool call.** No base64, no file text. Everything in a tool call passes through
your context: a 5 MB picture would cost about 7 MB of it. Only paths and links go in tool calls.

Android keeps each app's files private. ClipPolish usually **can't read** a path like
`/sdcard/Download/logo.png` or a file in your own app folder (e.g. Termux's home). It can read files in three
cases:

| Situation | Do |
| --- | --- |
| You can write to the phone's storage (e.g. Termux with storage access) and the user set up the **shared folder** | Copy the files into the shared folder, then `import_asset project_id=… paths=[…]`. Many files in one call. `list_shared_files` shows where the folder is and what's in it (usually `/storage/emulated/0/Documents/ClipPolish`). |
| You can run shell commands | `upload_file project_id=…` returns a key for **that project only**. The key works for **10 minutes**, for any number of files, and nothing else. The reply also has a ready `curl` command; run it with your files. |
| The file is on the web | Pass the `https://` link to `import_asset` (or as `src` / `music_path`). The phone downloads it. |

Uploading many files at once with the command from `upload_file`:

```sh
curl -sS -H 'Authorization: Bearer up_…' -F f=@/path/intro.png -F f=@/path/voice.m4a -F f=@/path/clip.mp4 http://127.0.0.1:8766/upload
```

The answer lists each file's `path` (like `assets/intro.png`). Use those paths directly:
- `src` of an `IMAGE` / `VIDEO` element or a scene background;
- `path` of an `audio_clip`;
- `music_path` in `set_audio`, `image_path` in `set_style`.

One file without a form: `curl -sS -H 'Authorization: Bearer up_…' -T a.png 'http://127.0.0.1:8766/upload?name=a.png'`.
Files stream to disk, so size is limited only by free space. When the key has expired (401), call
`upload_file` again.

Rules:
- The upload key is not the MCP key. Never ask the user for the MCP key, and never print either key in chat.
- If there's no shared folder and you can't run commands, ask the user to set one up: **ClipPolish → Settings →
  AI access → Shared folder → Set up folder** (one tap, then "Use this folder" and "Allow").
- If `import_asset` lists a path under `failed`, its `how_to_fix` says which of the ways above to use.
- Every path you put in `add_element`, `add_scene`, `upsert_items` or `patch_project` goes through the same
  lookup. The file is copied into the project, so the video keeps working if the original is deleted.

## 2. Showing the video to the user: `preview_video`

`preview_video project_id=… quality=480p|720p` returns a `markdown` line like
`![▶ My video (preview)](http://127.0.0.1:8766/preview/pv_…/index.m3u8)`. Post that line **on its own line**
in your answer. AntiGem shows it as a video the user plays right in the chat, with sound, **without exporting**:
- **It plays within seconds.** It's a stream (`.m3u8`): the first seconds render the moment you call the tool,
  and after that the phone renders just ahead of what the user is watching. The user sees the full length and
  can seek; seeking renders from the new spot in about a second.
- **It's cheap, even for long videos.** Nothing renders while nobody watches, so making a preview of a long
  video doesn't load the phone.
- **It's the same picture as the export.** It uses the export renderer. Nothing goes to the gallery.
- **It keeps this version.** The link is a snapshot of the edit when you made it, so old previews in the chat
  still play what you showed then. Make a new preview after each round of changes.
- **It doesn't expire.** It stops working only when the project is deleted or the user taps "Reset preview
  links" in AI access. ClipPolish's AI access must be on for it to play.
- **It's view-only.** Nothing can be changed through it.

Choosing `quality`:
- `480p` (default): quick checks, long videos, heavy projects (several video layers playing at once).
- `720p`: short videos, or when small text and fine detail matter.

When to use it:
- After making a video or a visible change: post the preview with a short summary of what changed.
- Before asking "shall I export?": the user can watch first.
- Use `get_frame` / `get_storyboard` when **you** need to see the video, and `preview_video` when the **user**
  should watch it.

Don't post the link as a plain `[text](url)` link: only the `![…](…index.m3u8)` form becomes a player.
`export` is still how the user gets a file. Only export when asked, and only if "Allow exporting" is on in AI
access.

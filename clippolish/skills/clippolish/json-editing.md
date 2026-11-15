# Editing anything: the generic JSON tools

The task tools cover common edits. **Every** field the app has, for recordings and studio videos, is reachable
through a small generic layer generated from the real data model. Use it when no task tool fits.

## Units (different from the task tools)

- Times: **µs** in fields ending in `Us` and in `t`. 1 s = 1 000 000.
- Positions and boxes: normalized 0..1, as `{"left", "top", "right", "bottom"}` or `{"x", "y"}`.
- Colours: ARGB **numbers** in model fields. 0xFFFF7A45 = 4294933061. Compute the number; don't write hex strings
  there. Track keys, effect params and component fields take strings instead: `"#RRGGBB"`, or `"#RRGGBBAA"` with
  alpha last (never `"#AARRGGBB"`).
- Field names exactly as `describe_model` shows them. Unknown fields and wrong types are rejected, so typos
  never get silently dropped.

## Learn the shape

`describe_model type=…` returns the fields, types, enum values, an example and, for item kinds, the JSON path.
Types include:
- the project: `project`;
- every item kind (below);
- recording looks: `style`, `background`, `motion`, `caption_style`, `tap_style`, `webcam`, `audio`,
  `export_settings`, `title_card`, `auto_edit_options`;
- plugins: `plugin`, `rule`, `live_rule`, `look`;
- studio videos: `scene`, `element`, `studio_style`, `transcript`, `scene_background`, `camera_motion`,
  `scene_transition`, `element_style`, `anim_spec`, `element_key`, `media_opts`, `style_pack`,
  `studio_layout`, `studio_template`, `scene_look`, `motion_preset`, `plugin_index`.

## Item kinds

| Kind | Path |
| --- | --- |
| `zoom` | `/zooms` |
| `caption` | `/captions/items` |
| `annotation` | `/annotations` |
| `blur` | `/blurs` |
| `highlight` | `/effects/highlights` |
| `tap` | `/effects/taps` |
| `lens` | `/lenses` |
| `chapter` | `/chapters` |
| `speed` | `/timeline/speeds` |
| `freeze` | `/timeline/freezes` |
| `cut` | `/timeline/cuts` |
| `audio_clip` | `/audio/clips` |
| `mute` | `/audio/mutes` |
| `camera_scene` | `/webcam/scenes` |
| `camera_move` | `/webcam/moves` |
| `frame_key` | `/motion/keys` |
| `scene` | `/scenes` |
| `element` | `/elements` |

- `list_items kind=… from_ms to_ms`: raw items in a time window.
- `upsert_items kind=… items=[…]`: items with an existing `id` are **merged** (only the fields you send
  change); items without an `id` are added with a new one. The result lists the ids.
- `remove_items ids=[…]`: any kind. Frame keys use `fk:<µs>`, cuts use `cut:<startUs>:<endUs>`.

## Read and patch the document

- `get_project_json paths=["/studio", "/elements/@el_ab12"]` returns parts of the project. Without `paths` it
  returns the whole project, which is large.
- `patch_project` takes `ops` (RFC 6902) and/or `merge` (RFC 7396). It is validated strictly,
  all-or-nothing, and one undo step. Path segments `@<id>` address list items by id, so you never need indexes.
  `"op": "merge"` deep-merges an object at a path, and `-` appends.

```json
{"name": "patch_project", "arguments": {"label": "tighter zoom, warmer look", "ops": [
  {"op": "replace", "path": "/zooms/@z_ab12/scale", "value": 2.4},
  {"op": "merge", "path": "/style", "value": {"padding": 0.08, "cornerRadius": 0.05}},
  {"op": "merge", "path": "/elements/@el_cd34/style", "value": {"glow": 0.6, "size": 0.09}},
  {"op": "add", "path": "/captions/items/-", "value": {"startUs": 1000000, "endUs": 3000000, "text": "Tap “Save”"}}
]}}
```
Studio cues (`at`, `until`…) are re-resolved after every patch, the same as in the editor.

## Many changes as one step

```json
{"name": "batch", "arguments": {"label": "Intro scene", "calls": [
  {"tool": "place_template", "arguments": {"template_id": "title_card", "at_ms": 0}},
  {"tool": "set_studio_look", "arguments": {"pack": "documentary", "apply_to_scenes": true}},
  {"tool": "add_element", "arguments": {"type": "EMOJI", "start_ms": 500, "src": "🕵️"}}
]}}
```
- `project_id` is filled in for every call.
- `atomic` (default true) means any error rolls everything back.
- Calls run in order, but a later call can't use ids returned by an earlier one in the same batch. When you need
  them, run the first call alone and batch the rest.
- These tools can't run inside a batch: `create_video_project`, `import_studio_project`, `set_canvas_length`,
  `import_video`, `duplicate_project`, `delete_project`, recording.

## Other projects and settings

- `copy_style from_project_id=…` copies a recording's look to another project.
- `get_settings` / `update_settings`: recording settings, auto-edit defaults, the default look for new
  recordings. Change them only when the user asks.
- `duplicate_project` before a risky experiment; `undo` / `redo` step through every change (the user's and
  yours).

# ClipPolish plugins

A ClipPolish plugin is **data, not code**: one JSON document, optionally zipped with the pictures it uses.
Plugins are safe to share and install. One plugin can hold any mix of:

| Part | Does | Shows up in the app |
| --- | --- | --- |
| `rules` | edits recordings automatically: trigger → conditions → actions | Plugins → "Run on every new recording"; `apply_plugin` |
| `live` | controls the recorder while recording (pause while a password field is open…) | Plugins → "Live rules while recording" |
| `look` | style preset for recordings | `apply_plugin with_look=true` |
| `animations` | named frame animations (rule action `ANIMATE`) | |
| `packs` | style packs for studio videos | Look, New video |
| `layouts` | layouts with named slots | Scenes → Layout |
| `templates` | ready-made scenes / element groups | + Add → Templates, `place_template` |
| `motions` | element motions | Elements → Motion presets, `apply_motion` |

Run `describe_model` for each part: `plugin`, `rule`, `live_rule`, `look`, `style_pack`, `studio_layout`,
`studio_template`, `scene_look`, `motion_preset`. Units are as in `json-editing.md` (µs, normalized boxes,
ARGB numbers).

## Rules for recordings

```json
{"name": "create_plugin", "arguments": {"name": "Settings tutorial", "icon": "⚙️", "rules": [
  {"name": "Zoom on taps", "trigger": "TAP", "where": {"app": "settings"},
   "actions": [{"type": "ZOOM", "beforeMs": 300, "afterMs": 1500}, {"type": "CAPTION", "text": "Tap “{label}”"}], "minGapMs": 800},
  {"name": "Chapters", "trigger": "SCREEN", "actions": [{"type": "CHAPTER", "text": "{screen}"}]}
]}}
```
- **Triggers:** `TAP`, `LONG_PRESS`, `TYPING`, `SCROLL`, `SCREEN`, `KEYBOARD`, `NOTIFICATION`, `TEXT_ON_SCREEN`,
  `PASSWORD_FIELD`, `MARK`, `IDLE`, `START`, `END`, `CHAPTER`.
- **Conditions (`where`):** `label`, `labelRegex`, `element`, `app`, `screen`, `checked`, `password`,
  `minSize`, `maxSize`, `region`, `fromMs`, `toMs`.
- **Actions:** `ZOOM`, `HIGHLIGHT`, `CAPTION`, `BLUR`, `ERASE`, `PIXELATE`, `ARROW`, `STEP_BADGE`, `TEXT`,
  `EMOJI`, `CALLOUT`, `LENS`, `LIFT`, `SPEED`, `CUT`, `FREEZE`, `CHAPTER`, `ANIMATE`, `CAMERA`, `MUTE`,
  `TAP_DOT`. Their `text` may use `{label}`, `{text}`, `{app}`, `{screen}`, `{n}`, `{time}`.
- `every`, `max` and `minGapMs` thin out the matches.

Workflow:
1. `create_plugin` (or `save_plugin json=…`).
2. `test_plugin` dry-runs it on a recording and reports the match count and what it would add, without
   changing anything.
3. `patch_plugin` adjusts it.
4. `apply_plugin` runs it. Re-applying replaces its earlier results; `remove_plugin_results` undoes them.

`create_plugin look_from_project=<id>` saves a recording's current look into the plugin.
`set_plugin_options` turns "run on every new recording" and live rules on or off. Only do that when the user
asks.

**Live rules:** a `trigger` (`APP_OPEN`, `SCREEN`, `TEXT_VISIBLE`, `PASSWORD_FOCUSED`, `KEYBOARD`,
`NOTIFICATION_SHADE`), a `match` text, and an `action` (`PAUSE_WHILE`, `MARK`, `STOP`). They only control
ClipPolish's own recorder.

## Studio kits (packs, layouts, templates, motions)

The easiest way to make a template is to build it in a project and run
`save_template scene_id=… name=… plugin_id=…`. It goes into "My templates" by default, with its pictures
copied into the plugin. To write one by hand:

```json
{"name": "create_plugin", "arguments": {"name": "Neon titles", "icon": "💡", "version": 1, "tags": ["titles"],
  "templates": [{"id": "neon_title", "name": "Neon title", "durationMs": 4000,
    "scene": {"layout": "quote", "background": {"kind": "SPOTLIGHT"}},
    "elements": [
      {"id": "k", "type": "KICKER", "startUs": 0, "endUs": 0, "slot": "tag", "text": "EPISODE 1", "design": "chip"},
      {"id": "t", "type": "TEXT", "startUs": 250000, "endUs": 0, "slot": "title", "text": "The *big* idea",
       "enter": {"kind": "WIPE_UP", "durationMs": 600}, "style": {"size": 0.11, "glow": 0.6}}]}],
  "motions": [{"id": "fly_through", "name": "Fly through", "stretch": true,
    "keys": [{"t": 0, "scale": 0.85, "opacity": 0}, {"t": 850000, "scale": 1.15}, {"t": 1000000, "scale": 1.3, "opacity": 0}]}]}}
```
- **Templates:** element times are relative to where the template is placed, and `endUs: 0` means "until the
  template ends". `scene` is optional; without it the elements join the scene showing there. Prefer `slot`
  over `box` so the template fits both portrait and landscape. `id`s inside a template only need to be unique
  in it. Connectors' `from` / `to` may point at them.
- **Motions:** `enter` / `exit` / `loop` replace the element's own. `keys` count from the element's start, or
  with `"stretch": true` the range 0..1 000 000 spans the element's whole length.
- **Style packs** need `id`, `name`, `paper`, `ink`, `accent`, `accent2`; the rest has defaults.
- **Layouts:** `{id, name, wide: {slot: rect}, tall: {slot: rect}}`.
- Check a new template: `place_template` into a scratch project (`duplicate_project` or
  `create_video_project`), then `get_frame` in portrait and landscape.

## Files, sharing, websites

- A plugin with pictures is a **.zip**: `plugin.json` plus files (`assets/sparkle.png`, character poses
  `assets/host_idle.png`, `assets/host_talk.png`…), referenced by relative paths. Placing a template copies the
  files it uses into the project.
- `install_plugin url=https://… | path=/…` installs a .json or .zip. Ask the user before installing from the
  internet. Installing the same `id` again updates it; raise `version` for every change.
- **Plugin websites:** an HTTPS folder with `index.json`:

  ```json
  {"name": "…", "plugins": [{"id": "…", "name": "…", "description": "…", "icon": "…", "author": "…",
     "version": 3, "tags": ["…"], "url": "neon.zip", "contents": "6 templates · 1 style"}]}
  ```

  `url` may be relative to the index. Use `browse_plugins source=<index.json link>` (or no source for the
  websites the user added), `plugin_sources add=…|remove=…`, then `install_plugin url=…`.
- `list_plugins` shows what is installed; `get_plugin` returns one plugin's JSON; `delete_plugin` removes a
  user plugin (built-ins are reset instead). Built-in plugins include Tutorial Pro, Privacy Guard,
  Social Shorts, Bug Report, App Store Preview, Spotlight Walkthrough and the Studio starter kit.

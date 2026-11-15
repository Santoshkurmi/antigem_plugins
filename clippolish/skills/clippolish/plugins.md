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
| `effects` | shader effects: GLSL defining `vec4 effect(vec2 uv)` + typed `inputs` | Elements → Effects, `add_effect` |
| `transitions` | shader scene transitions, gl-transitions style `vec4 transition(vec2 uv)` | Scenes → Shader transitions |
| `behaviors` | reusable animations: `inputs` + `tracks` with formulas | Elements → Ready-made motion, `apply_behavior` |
| `eases` | named curves `{id, curve: "cubic(…)" / "spring(…)"}` | any key's `ease` |
| `generators` | sandboxed JavaScript `generate(input, ctx)` returning `{elements, scenes}` | + Add → Generators, `run_generator` |
| `sounds` | sound files in the zip `{id, name, file}` | Sounds, as `"sfx:<plugin>/<id>"` |
| `luts` | colour looks: `.cube` 3D LUTs `{id, name, file}` or inline `cube` text | Effects → Colour look, `add_effect effect=lut` |
| `fonts` | typefaces in the zip `{id, name, file}` | `style.font = "<plugin>/<id>"` |
| `components` | element groups with fields `{id, name, inputs, box, elements}` | + Add → Components, `add_component` |

Run `describe_model` for each part: `plugin`, `rule`, `live_rule`, `look`, `style_pack`, `studio_layout`,
`studio_template`, `scene_look`, `motion_preset`, `effect_def`, `transition_def`, `behavior_def`, `generator_def`,
`component_def`, `lut_def`, `font_def`. Units are as in `json-editing.md` (µs, normalized boxes,
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


## Effects, transitions, behaviours, generators

- **Effects.** An effect's code defines `vec4 effect(vec2 uv)` (uv 0..1, top-left).
  - Helpers you can call: `src(uv)` (the layer so far, premultiplied), `orig(uv)` (the untouched layer),
    `hash()` and `noise()`.
  - Uniforms you get: `uSize` (px), `uUnit` (px per canvas short side), `uTime` and `uPass`.
  - Each input becomes a uniform with the same name (`float`, `vec4` colour, `vec2` point).
  - For blur-like effects, write several `passes`.
  - Set `margin` to leave room for glows.
- **Transitions.** Use the gl-transitions convention: `getFromColor` / `getToColor`, `progress`, `ratio`. Code
  from gl-transitions usually works as is.
- **Behaviours.** Inputs become element params, and tracks use them in formulas (`param.swing` or just
  `swing`).
- **Generators.** Write `function generate(input, ctx) { return { elements: [...], scenes: [...] } }`.
  - Elements use the same JSON as `describe_model("element")`.
  - Times are µs from where the generator is placed; `endUs: 0` = until the end.
  - `ctx` has `durationMs`, `aspect`, `width`, `height`, `startMs` and `pack` colours.
  - Test one before installing: `run_generator js=… dry_run=true`.
- **Effect inputs of type `lut` / `image`.**
  - `lut` gives `sampler2D name` + `float nameSize`; use `lutApply(name, nameSize, rgb)`. Its value is a look id.
  - `image` gives `sampler2D name`; its value is a picture path.
- **Components.**
  - Element boxes are 0..1 of the component's box, and times run from its start (`endUs: 0` = to its end).
  - Inputs of type `text` / `color` become fields: `{name}` in texts, `field.name` in formulas (e.g.
    `style.fill: {expr: "field.color"}`).
  - Number inputs become params (`param.name`).
- **Looks.** A `.cube` with `LUT_3D_SIZE` 2–128. `create_plugin` takes looks inline as `cube` text; files need a zip.
- **Testing a plugin.** `test_plugin` compiles its shaders on the phone's GPU (`shader_problems`) and checks
  eases, formulas, components (`component_problems`), looks (`lut_problems`) and fonts (`font_problems`). Fix everything it reports before telling the user the plugin is ready.

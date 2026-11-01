# AntiGem Plugins

Custom plugins for the AntiGem app. Add this repository in **Settings → Custom AntiGem Plugins → Repositories**
(`owner/repo`, `owner/repo@branch` or the GitHub URL), then install a plugin from the list.

| plugin | folder | what it does |
|---|---|---|
| Video Studio | [plugins/video-studio](plugins/video-studio) | Edited videos from a JSON timeline (FFmpeg + Pillow engine in the skill), genre skills, styles, components |

## Layout

```
antigem-plugins.json        ← index the app reads (one entry per plugin)
plugins/
  video-studio/             ← one folder per plugin = what you would otherwise ZIP
    manifest.json
    icon.png
    skills/
```

## Adding a plugin

1. Create `plugins/<name>/` with `manifest.json` (unique `id`, `version`) plus `skills/` and/or a worker.
2. Add an entry to `antigem-plugins.json` with the same `path`, `id` and `version`.

## Releasing an update

Raise `version` in the plugin's `manifest.json` **and** in `antigem-plugins.json` (keep them equal), commit and push.
The app offers the update the next time it checks.

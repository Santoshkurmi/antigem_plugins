# AntiGem plugins

Plugins for [AntiGem](https://github.com/Santoshkurmi/antigem). AntiGem adds this repository to
**Settings → Custom AntiGem Plugins → Repositories** by default (once; add `Santoshkurmi/antigem_plugins` again
there if you removed it). Install a plugin from the list; updates show up there when a plugin's version goes up.

| Plugin | What it is |
| --- | --- |
| [`rea`](rea/) | Skills-only plugin for **REA** (Reverse Engineer Anything): teaches agents to set up REA, check its MCP server and analyze APKs, installed apps, Flutter, React Native and native code. Also holds REA's setup scripts. |

## REA

```
rea/
  manifest.json
  icon.svg
  skills/
    rea.md                  ← main skill: check REA first, find the target, pick the workflow
    rea/                    ← detail files the main skill points to
      setup.md  mcp.md  android.md  flutter.md  react-native.md  native.md  device.md  troubleshooting.md
      scripts/              ← REA's setup, downloaded by the app (Settings → REA) and runnable by agents
        files.json          ← version + file list the app downloads
        rea-setup.sh        ← modular installer: container base java node rea jadx apktool native launcher …
        rea-mcp             ← the MCP server command agents start (proot-distro Ubuntu + tool group filter)
        rea-shell           ← a shell / one command in the container with REA's tools on PATH
        rea-filter.mjs      ← shows only the tools of the groups in REA_GROUPS
        groups.default.json ← built-in tool groups (REA 6.8.0 tool names)
```

The app does not ship any of this: **Settings → REA → Get setup files** downloads `scripts/` (from
`raw.githubusercontent.com/<repo>/<branch>/rea/skills/rea/scripts/`) into `$PREFIX/share/antigem-rea/`, and every
install button runs `rea-setup.sh <step>`. Agents using the skill run the same script from the installed plugin.

### Releasing a change

1. Change the files.
2. Scripts changed → raise `version` in `rea/skills/rea/scripts/files.json` (the app offers "Update to vX").
3. Skills or scripts changed → raise `version` in `rea/manifest.json` **and** the same version in
   `antigem-plugins.json` (the plugin list offers the update).
4. Commit and push to `main`.

### Testing a script change before pushing

Push to a branch or fork, then in the app use **Settings → REA → Setup files → Change** and enter
`owner/repo@branch`. Or copy the folder to the phone and run `bash rea-setup.sh <step>` from it.

### When REA adds tools

New tools appear in the app under *Tool groups → In no group*. To give them a built-in group, add their names to
`groups.default.json` (the app adds new built-in groups to users' files, but does not change groups users
already have), then release as above.

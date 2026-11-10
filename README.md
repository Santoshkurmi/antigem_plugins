# AntiGem plugins

Plugins for [AntiGem](https://github.com/Santoshkurmi/antigem). AntiGem adds this repository to
**Settings → Custom AntiGem Plugins → Repositories** by default (once; add `Santoshkurmi/antigem_plugins` again
there if you removed it). Install a plugin from the list; updates show up there when a plugin's version goes up.

| Plugin | What it is |
| --- | --- |
| [`rea`](rea/) | Skills-only plugin for **REA** (Reverse Engineer Anything): teaches agents to set up REA, check its MCP server and analyze APKs, installed apps, Flutter, React Native and native code. Also holds REA's setup scripts. |
| [`android-dev`](android-dev/) | Skills-only plugin for **building Android apps on the phone**: Kotlin / Java with Jetpack Compose, Flutter and React Native, in the same proot-distro Ubuntu container as REA. Teaches agents to check and install the tools, create projects, build and install APKs. Also holds the setup scripts. |
| [`browser_skill`](browser_skill/) | Skills-only plugin for **AntiGem's built-in browser**: teaches agents to use the Browser Automation MCP (`browser_*` tools) well: lock the tab while working, find elements by ref, click / type / fill forms, search sites, read pages, handle dialogs, popups, new tabs and errors. |

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

## Android Development

```
android-dev/
  manifest.json
  icon.svg
  skills/
    android-dev.md          ← main skill: check the setup, where projects go, create / build / install
    android-dev/            ← detail files the main skill points to
      setup.md  kotlin-compose.md  flutter.md  react-native.md  run-on-phone.md  troubleshooting.md
      scripts/              ← downloaded by the app (Settings → Android Development) and runnable by agents
        files.json          ← version + file list the app downloads
        android-setup.sh    ← modular installer: container base java sdk launcher flutter node ndk adb, test, gradle-dist …
        adev                ← runs a command in the container with Java, the SDK, Gradle, Flutter, Node on PATH
        adev-new            ← creates a hello-world Compose / Flutter / React Native project
```

The app downloads `scripts/` into `$PREFIX/share/antigem-android/` and every install button runs
`android-setup.sh <step>`; the test builds run `android-setup.sh test compose|flutter|rn`. Releasing works as for
REA: raise `scripts/files.json`'s version when scripts change, and `manifest.json` + `antigem-plugins.json` when
anything changes.

The template's versions are pinned in `adev-new` (tested on a phone); `adev-new compose … --latest` tries the
newest ones of the same major versions. When updating the pins, build the template once on a phone
(`android-setup.sh test compose`).

## Browser Automation

```
browser_skill/
  manifest.json
  icon.svg
  skills/
    browser_skill.md        ← main skill: lock → look → act → check → unlock, which tool when, searching, batching
    browser_skill/          ← detail files the main skill points to
      workflows.md          ← recipes: search, forms, logins, multi-page, extracting data, popups, iframes, debugging
      troubleshooting.md    ← every tool message and what to do
```

No scripts: the tools are built into the app (MCP endpoint `/browser`, preset "Browser Automation"). When the tools
change (new tools, renamed parameters, different messages), update the skill to match, then raise the version in
`manifest.json` and `antigem-plugins.json`.

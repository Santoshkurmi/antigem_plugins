---
name: Reverse engineering with REA
description: Analyze Android apps (APK, installed apps, Flutter, React Native, Unity) and native code with the REA MCP server; check REA works first, and set it up or tell the user how when it does not.
---

# Reverse engineering with REA

REA (Reverse Engineer Anything, github.com/morluto/rea) is an MCP server with static analysis tools: JADX for
Java/Kotlin, apktool for resources, Flutter/Dart snapshot facts, objdump and rizin for native code, adb for the
phone. In AntiGem it runs in a proot-distro Ubuntu container of the terminal and agents reach it through the
`rea-mcp` launcher. Only analyze apps and files the user owns or is allowed to analyze.

Detail files (read with `get_skill_file`, name `rea`):

| File | When |
| --- | --- |
| `setup.md` | REA is missing or broken: what to install, terminal steps, what each step does |
| `mcp.md` | The REA MCP server is missing, failing or lacks a tool; tool groups; Claude Code / OpenCode config |
| `android.md` | APKs and installed apps: find the APK and its splits, framework detection, JADX, resources |
| `flutter.md` | Flutter apps (libapp.so, libflutter.so) |
| `react-native.md` | React Native apps: Hermes bytecode and plain JS bundles |
| `native.md` | .so libraries and other binaries: objdump, rizin, exports, JNI, Unity IL2CPP, gdb |
| `device.md` | REA's adb tools on this phone: installed packages, pulling APKs, logcat, screenshots |
| `troubleshooting.md` | Errors and their fixes |

## 1. Check REA before anything else

1. Look at your tools. An REA server (usually named `rea`) offers its tools in one of two ways:
   - **On demand**: four tools `rea_tools`, `rea_tool_info`, `rea_call`, `rea_call_change` (see "On-demand
     servers" below). Check it with `rea_tools` (no arguments): a list of tools means REA works.
   - **Directly**: REA's own tool names (`inspect_android_package`, `identify_flutter_build`,
     `inspect_with_objdump`…). Check it with `inspect_apktool_client` (no arguments, small answer). Do not use
     `binary_session` as a check: its answer is very large.
2. If the check answers, continue with step 2 below.
3. If you have no REA tools, check the terminal (run these yourself if you can run commands):
   - `command -v rea-mcp` → missing: REA is not installed.
   - `rea-mcp --doctor` → prints which engines are ready.
4. Then tell the user exactly what is missing and the easiest fix. Never install ~1 GB without asking:
   - **Not installed** → "Open Settings → REA · Reverse Engineering and install the parts (the 'Needed for APK
     analysis' set), then Add to Antigravity." Offer to install it from the terminal instead (`setup.md`).
   - **Installed, but no REA tools** → "Settings → REA → Add to Antigravity (or Settings → Antigravity → MCP
     Servers → REA tile), then refresh the server and start a new chat." For Claude Code or OpenCode see `mcp.md`.
   - **Server added but erroring** → ask the user to tap Restart on it in Settings → REA, and see `troubleshooting.md`.
5. A call that fails with "not in this server's tool groups" means the tool exists but is hidden. Tell the user
   which group to add (Settings → REA → Tool groups, or choose more groups for the server), see `mcp.md`.

### On-demand servers

The four gateway tools stand for all of REA's tools, so the agent's context stays small:

1. `rea_tools` lists every tool the server allows, by group, names only (once per task is enough). Then
   `rea_tools {group: "android"}` or `rea_tools {query: "manifest"}` gives one line per tool.
2. `rea_tool_info {names: ["inspect_android_package", "search_android_classes"]}` gives each tool's full
   description and argument schema. Read it before the first call of a tool.
3. `rea_call {name: "inspect_android_package", arguments: {path: "...", detail: "summary"}}` runs it. The result
   is the tool's own result. Tools marked ✎ change things (installing apps, pushing files, debugger and Frida
   commands): run those with `rea_call_change` instead; the user may be asked to approve it.

Everywhere this skill names an REA tool, on an on-demand server call it through `rea_call` (or
`rea_call_change` when it is marked ✎).

## 2. Find the target

- An APK file: use its absolute path. Termux paths (`/data/data/com.termux/files/home/...`) work the same inside
  REA. Prefer files in the Termux home over `/sdcard`.
- An installed app: `pm path <package>` in the terminal lists `base.apk` and every split; those paths are
  readable directly. Find the package with `pm list packages | grep -i <name>`, or REA's
  `resolve_adb_packages` / `pull_adb_package` when adb is connected (`device.md`).
- Native code of a Play Store app is usually in a split: `split_config.arm64_v8a.apk`, not `base.apk`.

## 3. Identify what the app is built with

List the APK (and its ABI split): `unzip -l <apk> | grep -E 'lib/|assets/'`.

| You see | It is | Read |
| --- | --- | --- |
| `libflutter.so`, `libapp.so` | Flutter | `flutter.md` |
| `assets/index.android.bundle` (+ `libhermes.so`) | React Native | `react-native.md` |
| `libil2cpp.so`, `assets/bin/Data/Managed/Metadata/global-metadata.dat` | Unity IL2CPP | `native.md` |
| `assemblies/*.dll` or `libmonodroid.so` | .NET MAUI / Xamarin | managed code: needs ILSpy (not set up) |
| only `classes*.dex` (+ maybe JNI `.so`) | Java / Kotlin | `android.md` |

Every app also has a Java/Kotlin layer (`android.md`): start with `inspect_android_package` (detail `summary`).

## 4. Work economically

- REA results can be large. Use `detail: "summary"` where offered, then page retained results with
  `inspect_analysis_view {source: {kind: "retained-evidence", evidence_id: <normalized_result.parent_evidence_id>},
  view: {...}}`.
- Narrow down before decompiling: `search_android_classes` with a query, then one class, then one method.
- Save big outputs (decompiled Hermes JS, rizin listings) to files in the Termux home and grep them, rather than
  printing them.
- Say what you verified and what you inferred. REA's evidence is static: it never runs the app.

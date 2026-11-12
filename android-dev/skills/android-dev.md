---
name: Android development on the phone
description: Create, build and install Android apps on this phone (Kotlin / Java with Jetpack Compose, Flutter, React Native) with Gradle, the Android SDK and Flutter in AntiGem's proot-distro Ubuntu container; check the setup first, and set it up or tell the user how when it is missing.
---

# Android development on the phone

**Follow this skill as closely as you can.** Building on a phone is different from building on a PC: Google's
tools are made for x86-64 PCs, and this setup works around that in specific ways. Use the commands, paths and
rules given here and in the detail files, instead of what you would normally do on a PC, and read the matching
detail file before you start a task it covers.

AntiGem builds Android apps on the phone itself. Gradle, the Android SDK, Flutter and Node.js live in a
proot-distro Ubuntu 24.04 container named `ubuntu` (the same one REA uses); you reach them from the terminal with
two commands:

- `adev <command>`: runs the command **inside the container, in the current folder**, with `java`, `sdkmanager`,
  `flutter`, `dart`, `node`, `npm`, `npx` and `adb` on PATH and `ANDROID_HOME` set. Example:
  `cd ~/AndroidProjects/notes && adev ./gradlew assembleDebug`. Without arguments it opens a shell.
- `adev-new compose|flutter|rn <dir> [--package com.example.app] [--name Name]`: creates a hello-world project
  that builds.

Edit the project files directly with your normal file tools (they are in the Termux home); only builds, `flutter`,
`npm` and `npx` need `adev`.

**Builds are arm64-v8a only.** Apps built here are for this phone, so the setup makes every build package only
arm64 native code: a Gradle init script sets `abiFilters` to `arm64-v8a` for every module, React Native gets
`reactNativeArchitectures=arm64-v8a`, and `flutter build apk|appbundle` adds `--target-platform android-arm64`.
That keeps builds fast (Flutter compiles Dart once, not three times) and needs no x86 tools. Do not add other
ABIs to a project to "fix" this. If the user needs an APK for other devices (x86 emulators, 32-bit phones),
tell them to build it on a PC; `ADEV_ALL_ABIS=1 adev …` turns the rule off for one build, but it is slow and may
need tools that do not exist for arm64.

Detail files (read with `get_skill_file`, name `android-dev`):

| File | When |
| --- | --- |
| `setup.md` | Something is missing: what to install, the setup script and its steps |
| `kotlin-compose.md` | Kotlin / Java / Jetpack Compose apps: the template, Gradle, dependencies, release builds |
| `flutter.md` | Flutter apps |
| `react-native.md` | React Native apps (and Expo) |
| `run-on-phone.md` | Installing the APK on this phone, starting it, logcat, screenshots |
| `troubleshooting.md` | Build errors and their fixes |

## 1. Check the setup before anything else

Run `bash $PREFIX/share/antigem-android/android-setup.sh status` (it prints `key=yes|no` lines):

| Line | Needed for |
| --- | --- |
| `container base java sdk launcher` | every Android app (Kotlin / Java / Compose; Flutter and React Native build on it) |
| `flutter` | Flutter apps |
| `flutter-release` | Flutter release / profile builds |
| `node ndk` | React Native / Expo apps (React Native compiles C++) |
| `adb` | installing and starting apps from the terminal, logcat |

If the script itself is missing, nothing is set up yet. If something you need says `no`:

- Tell the user exactly what is missing and the easiest fix: **"Open Settings → Android Development and install
  Kotlin / Java (and Flutter or React Native)."** The page installs everything with buttons and can build a test app.
- Or offer to install it from the terminal: read `setup.md` and follow it. **Ask first**: Kotlin / Java needs about
  1 GB, Flutter about 1.6 GB more, React Native about 1.8 GB more (Node.js + the NDK), and each takes 5–20 minutes.

Never assume x86 tools work: Google's Linux SDK tools are x86_64 builds and this phone is arm64. The setup replaces
every one that builds need: aapt2 and adb with Termux's arm64 builds, the NDK's compilers with Ubuntu's arm64 LLVM,
and Flutter's and Hermes' release compilers run through qemu (`setup.md` explains each). See `troubleshooting.md`
when a tool says `not found` or `Exec format error`.

## 2. Where projects go

- Put projects under the Termux home, by default `~/AndroidProjects/<name>`. Not on `/sdcard` or
  `/storage/emulated/0`: Gradle and npm need a real Linux file system (permissions, symlinks, exec).
- The container sees the Termux home at the same path, so the paths you edit and the paths `adev` builds are
  the same. Projects outside the home are not visible inside the container.

## 3. Create, build, install

| Kind | Create | Build (debug APK) | APK |
| --- | --- | --- | --- |
| Kotlin / Compose | `adev-new compose ~/AndroidProjects/app` | `cd ~/AndroidProjects/app && adev ./gradlew assembleDebug` | `app/build/outputs/apk/debug/app-debug.apk` |
| Flutter | `adev-new flutter ~/AndroidProjects/app` | `cd ~/AndroidProjects/app && adev flutter build apk --debug` | `build/app/outputs/flutter-apk/app-debug.apk` |
| React Native | `adev-new rn ~/AndroidProjects/app` | `cd ~/AndroidProjects/app/android && adev ./gradlew assembleDebug` | `android/app/build/outputs/apk/debug/app-debug.apk` |

Then install it (`run-on-phone.md`): `adb install -r <apk>` when adb is connected, else `termux-open <apk>`
opens Android's installer for the user to confirm.

An existing project (cloned, or from the user) builds the same way, as long as it is in the Termux home. Its
first build may need SDK platforms it targets; Gradle downloads them by itself (the licenses are accepted).

## 4. Work economically

- The first build of a project downloads Gradle and libraries (hundreds of MB) and takes 5–15 minutes in proot.
  Later builds take 1–3 minutes. Tell the user before a first build, and run builds with a long timeout (≥ 20
  minutes) or in the background; do not start a second build while one runs.
- Gradle's daemon does not survive between `adev` calls (proot ends its processes), so every build starts cold.
  Batch your edits, then build once.
- Pass `--console=plain` to Gradle (or `-q`) to keep its output short, and read only the end of a failed build's
  output: the first `e:` / `error:` / `What went wrong` lines are what matter.
- **Build debug APKs by default.** Phones are slow, and release builds are much slower (R8 shrinking, a release
  C++ build for React Native, Flutter's and Hermes' release compilers running through an x86-64 emulator):
  roughly 3 minutes or more for a small Flutter app and 7 minutes or more for React Native, versus 1–3 minutes
  for debug. Only build a release APK (or AAB) when the user asks for a release build, or for an APK to share or
  install on another phone. Before you start one, warn the user that it may take a long time.
- **Do not clean before building.** No `./gradlew clean`, `flutter clean`, deleting `build/`, `.cxx/`,
  `.dart_tool/` or `node_modules/`, and no `android-setup.sh clean-cache`, as a routine step or "to be safe".
  Each one throws away the work the next build would reuse and turns it into a slow first build again
  (C++ and Dart are recompiled, libraries downloaded again). Clean only when it is really needed: a build error
  that points at stale or corrupt outputs and does not go away otherwise, the disk is full, or the user asks.
  Then clean the smallest thing that fixes it (one module's `build/`, not Gradle's whole cache), and tell the user
  why.

## 5. Keep the project's run commands in `.antigem/run.json`

The user builds and runs apps without the terminal from AntiGem's **Run panel** (and the IDE's Run button). Both
read the project's `.antigem/run.json`; `adev-new` writes one for every project it creates. Keep it in step:

- A project without one (cloned, made by hand): create it with the commands below for its kind.
- You change how the app is built, installed or started (a new flavor, a package name, Metro's port, a script):
  update the matching commands. Keep the user's own commands; don't reorder or rename them.
- Write commands as they run on this phone (`adev …` for Gradle, Flutter and npm/npx; `adb` and `termux-open`
  as they are). Each runs in the project folder, or in `cwd` (relative to the project) when given.

```json
{
  "version": "1.0",
  "configurations": [
    { "name": "Build debug APK", "type": "terminal", "command": "adev ./gradlew assembleDebug --console=plain" },
    { "name": "Build, install & open", "type": "terminal", "command": "adev ./gradlew assembleDebug --console=plain && adb install -r app/build/outputs/apk/debug/app-debug.apk && adb shell monkey -p com.example.notes -c android.intent.category.LAUNCHER 1 >/dev/null" },
    { "name": "Install with Android's installer", "type": "terminal", "command": "termux-open app/build/outputs/apk/debug/app-debug.apk" }
  ]
}
```

React Native: the Gradle commands get `"cwd": "android"` (APK path relative to it), plus a `Start Metro` command
(`adev npx react-native start --port 8081`) in the project folder. Flutter: `adev flutter build apk --debug`,
`build/app/outputs/flutter-apk/app-debug.apk`, and `adev flutter run` for hot reload.

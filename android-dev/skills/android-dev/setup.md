# Setting up Android development

Everything runs in the proot-distro Ubuntu 24.04 container named `ubuntu` inside AntiGem's terminal (com.termux
builds only). REA uses the same container: Java 21 and Node.js installed for one are reused by the other.

The easy way is **Settings → Android Development** in the app: the user picks Kotlin / Java, Flutter and/or React
Native, and the page installs the parts with a log, then builds a test app. Suggest that first.

If the user prefers, install from the terminal. **Ask before installing**: Kotlin / Java needs about 1 GB (more
after the first Gradle build), Flutter about 1.6 GB more (with release builds), React Native about 1.8 GB more
(Node.js + the NDK) plus ≈400 MB per project. Run
long steps one at a time so a failure is easy to see, with a long timeout (30 minutes).

## The setup script

The script ships with this skill: `scripts/android-setup.sh` in this skill's detail folder (`get_skill` returns
`detail_dir`; the full path is `<detail_dir>/scripts/android-setup.sh`). Once installed it is also at
`$PREFIX/share/antigem-android/android-setup.sh`. If neither is reachable, download the scripts:

```sh
mkdir -p $PREFIX/share/antigem-android && cd $PREFIX/share/antigem-android
for f in files.json android-setup.sh adev adev-new; do
  curl -fsSLO https://raw.githubusercontent.com/Santoshkurmi/antigem_plugins/main/android-dev/skills/android-dev/scripts/$f
done
```

`bash <folder>/android-setup.sh help` lists every step. Steps can be given together; each can be run again to
repair or update it.

| Step | Installs | Needed for |
| --- | --- | --- |
| `container` | proot-distro (Termux) and the Ubuntu 24.04 container (≈30 MB download) | everything |
| `base` | curl, git, zip, unzip, xz, Python, binutils in Ubuntu | sdk, flutter, node |
| `java` | OpenJDK 21 headless | Gradle, SDK tools |
| `sdk` | Android command-line tools 21.0, `platforms;android-37.0` and `android-36`, `build-tools;36.0.0`, Termux's arm64 `aapt2`, Termux's `adb` as `platform-tools/adb`, `/root/.gradle/gradle.properties`, the arm64-only init script and the strip-only NDK | every app |
| `launcher` | `adev` and `adev-new` in `$PREFIX/bin` | every app |
| `flutter` | Flutter stable (git clone) + `flutter precache --android` | Flutter |
| `flutter-release` | Termux `qemu-user-x86-64` + Ubuntu `libc6-amd64-cross`, `gen_snapshot` wrappers | Flutter release / profile builds |
| `node` | Node.js 24 through nvm, at `/root/tools/node`; Termux `qemu-user-x86-64` for React Native's x86-64 `hermesc` | React Native, Expo |
| `ndk` | NDK 28.2 + CMake 3.22.1 packages with their x86-64 programs swapped for Ubuntu's arm64 LLVM 19, CMake and Ninja (≈1.5 GB) | C/C++ code: React Native, CMake apps and plugins (`troubleshooting.md` → the NDK) |
| `adb` | Termux android-tools | `adb install`, logcat |

Shortcuts: `kotlin` = container base java sdk launcher; `flutter-all` = kotlin + flutter flutter-release; `rn` = kotlin + node ndk;
`all` = kotlin + flutter flutter-release node ndk adb.

Recommended sequence (check each step's last line: `✓` is success, `✗` names the problem):

```sh
S=$PREFIX/share/antigem-android        # or the skill's scripts folder
bash $S/android-setup.sh kotlin        # container base java sdk launcher
bash $S/android-setup.sh flutter flutter-release   # only for Flutter
bash $S/android-setup.sh node ndk      # only for React Native
bash $S/android-setup.sh status        # what you need should say yes
bash $S/android-setup.sh test compose  # creates ~/AndroidProjects/hello-compose and builds it
```

`test flutter` and `test rn` do the same for the other kinds.

## What the sdk step changes, and why

- Google's `aapt2` (Gradle downloads it from maven) is an x86_64 Linux binary. Termux builds aapt2 for arm64, and
  it runs inside the container, so `/root/.gradle/gradle.properties` has
  `android.aapt2FromMavenOverride=/data/data/com.termux/files/usr/bin/aapt2`. The build-tools folders' `aapt2` is
  a link to it too.
- Command-line tools are pinned to 21.0: from 22.0 on, `sdkmanager` is a wrapper around a native `android` binary
  that only exists for x86_64.
- arm64-v8a only: `/root/.gradle/init.d/antigem-arm64.gradle` sets `abiFilters = arm64-v8a` on every Android
  module (through `androidComponents.finalizeDsl`) and keeps `.so` files unstripped (stripping needs Google's x86
  NDK); `reactNativeArchitectures=arm64-v8a` for React Native; the flutter step puts a `flutter` wrapper in
  `/root/tools/adev-bin` (first on PATH) that adds `--target-platform android-arm64` to `flutter build`.
  `ADEV_ALL_ABIS=1` turns all three off.
- React Native: the same init script wraps `hermesc` (Hermes compiler, static x86-64) with Termux's qemu.
- Gradle settings for proot: `org.gradle.vfs.watch=false` (file watching is unreliable in proot),
  `kotlin.compiler.execution.strategy=in-process` (no separate Kotlin daemon), a 2 GB heap and 4 workers.

## Other commands

- `bash $S/android-setup.sh doctor`: versions of every tool.
- `bash $S/android-setup.sh flutter`: also updates Flutter to the latest stable.
- `bash $S/android-setup.sh clean-cache`: deletes Gradle's caches (frees GBs; every project's next build is slow and
  downloads again). Only when the disk is full or the user asks; never as part of a build.
- `bash $S/android-setup.sh uninstall-flutter` / `uninstall`: remove Flutter / the SDK, Flutter, Gradle's files
  and adev. The container, Java and Node.js stay (REA uses them). Only with the user's OK.
- `sdkmanager` (through `adev`) installs other SDK packages: `adev "sdkmanager 'platforms;android-35'"`.

## Notes

- `proot-distro login ubuntu` opens the container by hand; `/etc/profile.d/antigem-android.sh` sets the same PATH
  there for login shells.
- If `apt` reports a lock, another install is running (maybe REA's, or the app's). Wait; never delete lock files.

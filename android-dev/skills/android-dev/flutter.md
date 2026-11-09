# Flutter apps

Needs the `flutter` step (Flutter stable in `/root/tools/flutter`) and, for release / profile builds, the
`flutter-release` step. `status` shows `flutter=yes` and `flutter-release=yes`.

## A new app

```sh
adev-new flutter ~/AndroidProjects/counter --package com.example.counter
cd ~/AndroidProjects/counter
adev flutter build apk --debug        # build/app/outputs/flutter-apk/app-debug.apk   (≈75 MB, debug engine)
adev flutter build apk --release      # build/app/outputs/flutter-apk/app-release.apk (≈15 MB): only when asked
```

`adev-new flutter` runs `flutter create --platforms android` and then:
- removes `ndkVersion = flutter.ndkVersion` from `android/app/build.gradle.kts`. Otherwise AGP downloads Google's
  x86-64 NDK (≈700 MB) that cannot run here.
- sets `applicationId` to `--package` and keeps the `namespace` (the Kotlin package of `MainActivity`). Never change
  the namespace without moving `MainActivity.kt`, or the app crashes on start with `ClassNotFoundException`.

Write the app in `lib/main.dart` and add packages with `adev flutter pub add <name>`. `flutter analyze` and
`flutter test` run the same way (`adev flutter test`).

## How builds work here

- **arm64 only.** `/root/tools/adev-bin/flutter` (first on PATH) adds `--target-platform android-arm64` to
  `flutter build apk|appbundle|aar`, so Dart is compiled once, not for arm, arm64 and x64. Do not pass other
  targets.
- **Release / profile builds** compile Dart ahead of time with `gen_snapshot`, which Google ships only for x86-64
  Linux. The `flutter-release` step runs it through Termux's `qemu-x86_64` (with Ubuntu's x86-64 C library), via
  wrappers in `bin/cache/artifacts/engine/<target>/linux-arm64/gen_snapshot`. Under emulation that compile takes
  about 1–3 minutes for a small app, longer for big ones. Debug builds (JIT) do not use it.
- `.so` files are stripped by the strip-only NDK (`setup.md`), so APK sizes are normal.
- Flutter prints `Woah! You appear to be trying to run flutter as root`: harmless (the container user is root).
- After `flutter upgrade` or a Flutter update by the setup, rerun `android-setup.sh flutter-release` if a release
  build says it cannot find `linux-arm64/gen_snapshot`. The flutter step already does this when qemu is installed.

## Installing, running

Build, then install (`run-on-phone.md`): `adb install -r build/app/outputs/flutter-apk/app-release.apk`.
`flutter run` needs adb connected and stays attached to the app (hot reload through its keyboard); in an agent,
prefer build + `adb install` + `adb shell am start -n <applicationId>/<namespace>.MainActivity`.

An app installed as debug and then as release with the template's debug signing installs over it. A real release
key needs a `signingConfigs` block (`kotlin-compose.md` → a release key).

## Plugins with native code

Most plugins (path_provider, shared_preferences, http, sqflite…) are Kotlin / Java and build fine. Plugins that
compile C/C++ with CMake (some FFI and media plugins) need a real NDK; see `troubleshooting.md` → the NDK.

# React Native apps

Needs the `node` and `ndk` steps (`status`: `node=yes`, `ndk=yes`). React Native (0.82 and newer) always uses the
New Architecture, which compiles C++ for every app, so the arm64 NDK (`setup.md`, `troubleshooting.md` → the NDK)
is required even for a hello world.

## A new app

```sh
adev-new rn ~/AndroidProjects/hello-rn --package com.example.hellorn    # --name HelloRn (letters / digits)
cd ~/AndroidProjects/hello-rn/android
adev ./gradlew assembleDebug --console=plain     # app/build/outputs/apk/debug/app-debug.apk
adev ./gradlew assembleRelease --console=plain   # app/build/outputs/apk/release/app-release.apk: only when asked
```

`adev-new rn` runs `npx @react-native-community/cli@latest init` (npm downloads ≈300 MB into `node_modules`).
Write the app in `App.tsx`; add packages with `adev npm install <name>` in the project folder.

The first build compiles React Native's C++ for arm64 (a few minutes); later builds reuse it. Only `arm64-v8a` is
built: `reactNativeArchitectures=arm64-v8a` in `/root/.gradle/gradle.properties` overrides the project's list.

## Debug builds need Metro

A debug APK loads its JavaScript from the Metro bundler on port 8081 of the same phone. Start Metro in the project
folder, in the background, before opening the app:

```sh
cd ~/AndroidProjects/hello-rn && nohup adev "npx react-native start --port 8081" > ~/metro.log 2>&1 &
```

The app shows "Bundling …%" the first time (about a minute), then the UI. Edits to `App.tsx` reload while Metro
runs. Stop Metro when done: `pkill -f "react-native start"`. Without Metro the app shows "Unable to load script".

## Release builds

`assembleRelease` bundles the JavaScript into the APK (no Metro needed) and compiles it with Hermes' `hermesc`,
which React Native ships as a static x86-64 program. The Gradle init script swaps
`node_modules/hermes-compiler/hermesc/linux64-bin/hermesc` for a wrapper that runs it with Termux's `qemu-x86_64`
(installed by the `node` step); the original stays as `hermesc.x86_64`. `npm install` may restore the original;
the next build wraps it again.

The template signs release builds with the debug key; for a real key see `kotlin-compose.md` → a release key.

## Expo

`npx create-expo-app` works the same way through `adev`. Build the Android app with `adev npx expo prebuild -p android`
and then Gradle in `android/` as above (EAS cloud builds are separate and need an Expo account).

## Installing, running

`adb install -r <apk>`, then start it with `adb shell monkey -p <applicationId> -c android.intent.category.LAUNCHER 1`
(`run-on-phone.md`). `npx react-native run-android` also works when adb is connected, but it tries to open a
terminal for Metro; prefer the commands above in an agent.

# Installing and running apps on this phone

## Without adb (always works)

```sh
termux-open ~/AndroidProjects/notes/app/build/outputs/apk/debug/app-debug.apk
```

AntiGem opens Android's package installer; the user taps Install. The first time Android asks to allow AntiGem to
install apps. Tell the user to confirm on screen. You cannot start the app or read its logs this way.

Settings → Android Development also has Install buttons for its test apps.

## With adb (install, start, logs, screenshots)

adb is Termux's (`android-setup.sh adb`) and must be connected to this phone once over Wireless debugging:
Settings → ADB Connect. Check with `adb devices` (a `device` line, not `unauthorized` / empty). Run adb from the
Termux side (no `adev` needed); inside `adev` it is on PATH too.

```sh
adb install -r app-debug.apk                                  # -r: replace, keeps data; -d also allows a downgrade
adb shell monkey -p com.example.notes -c android.intent.category.LAUNCHER 1   # start it
adb shell am start -n com.example.notes/.MainActivity         # or start an activity by name
adb shell am force-stop com.example.notes
adb uninstall com.example.notes
adb logcat -d -t 300 --pid=$(adb shell pidof -s com.example.notes)            # recent log of the app
adb logcat -d -t 200 AndroidRuntime:E '*:S'                   # crashes (stack traces)
adb exec-out screencap -p > ~/shot.png                        # screenshot, then look at it
```

- `INSTALL_FAILED_UPDATE_INCOMPATIBLE`: an app with that package is installed with another signature (for
  example a release build). `adb uninstall <package>` first (it deletes the app's data: ask the user).
- `INSTALL_FAILED_VERSION_DOWNGRADE`: add `-d`, or raise `versionCode`.
- Flutter: `adev flutter install` and `adev flutter run` need adb too; `flutter run` stays attached (hot reload
  through its keys), so prefer `flutter build apk --debug` + `adb install` in an agent.
- React Native debug APKs load JavaScript from Metro on port 8081 (`react-native.md`); a release build bundles it.

If the phone has Android Automation enabled in AntiGem, its MCP tools can also tap through the installed app to
check that it works.

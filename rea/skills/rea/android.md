# Android apps: APKs and installed apps

## Get the APK

- **A file the user gave**: use its absolute path. If it is on `/sdcard`, copy it into the Termux home first
  (`cp /sdcard/Download/app.apk ~/apks/`), which avoids storage-permission surprises.
- **An installed app** (no adb needed):

  ```sh
  pm list packages | grep -i <name>      # find the package name
  pm path <package>                      # base.apk and every split, e.g.
  # package:/data/app/~~…==/com.example-…==/base.apk
  # package:/data/app/~~…==/com.example-…==/split_config.arm64_v8a.apk
  ```

  These paths are readable as they are; pass them straight to REA's tools. `ls /data/app` is not allowed, but the
  exact paths work. To keep a stable copy: `mkdir -p ~/apks/<package> && cp <paths> ~/apks/<package>/`.
- **With adb connected** (`device.md`): `resolve_adb_packages` then `pull_adb_package` pulls base and all splits
  into a folder.
- **Splits**: `base.apk` holds the dex code, manifest and most resources. Native libraries (`lib/arm64-v8a/*.so`)
  usually sit in `split_config.arm64_v8a.apk`; language and density resources in other splits. An `.xapk`/`.apks`
  bundle is a zip of these: `unzip` it first.

## Overview first

1. `inspect_android_package {path, detail: "summary"}`: package, version, min/target SDK, permissions,
   activities, services, receivers, providers (with exported flags and permissions), class and resource counts.
   The decoded manifest stays retained: read it with `inspect_analysis_view {source: {kind: "retained-evidence",
   evidence_id: <normalized_result.parent_evidence_id>}, view: {kind: "android", facet: "manifest", offset: 0,
   limit: 4096}}` and follow `coverage.next_offset`.
2. `inspect_apk_signature {path}`: signing schemes and certificates.
3. `decode_android_resources {path}`: readable AndroidManifest.xml, apktool.yml SDK facts and string resources
   (`locale` / `locales` for translations, `include_strings`). Good for URLs, keys and feature names in strings.

## Java / Kotlin code (JADX)

1. `search_android_classes {path, query}`: case-sensitive substring of class names (`""` lists all, which can be
   huge). Search for the package name, `MainActivity`, `Api`, `Login`, `Crypto`, `Firebase`, a host name…
2. `inspect_android_class {path, class_name}`: methods (with overload indices), fields and static final values
   (constants such as URLs and keys often show up here), inner classes.
3. `inspect_android_method {path, class_name, method_name, overload_index?}`: decompiled Java of one method
   (smali when JADX cannot decompile it). Give `overload_index` when the name has overloads.
4. `trace_android_references {path, class_name, method_name?, overload_index?}`: who uses this class or method.

Obfuscated apps (R8/ProGuard) have names like `a.b.c`: follow references from manifest components and from
string constants instead of names. `project_android_application_graph` builds a graph from the retained package
evidence (`inventory_evidence`) when you need the big picture.

The first JADX call on an APK loads it (15–60 s in proot); later calls on the same file are faster.

## Then, by framework

- Flutter → `flutter.md`; React Native → `react-native.md`; native `.so`, Unity → `native.md`.
- WebView apps: look for `assets/www/` or `assets/public/` (Cordova/Capacitor); the JS there is plain files.

## Report

Summarize: what the app is (package, version, framework), what it can access (permissions, exported components),
where its interesting logic lives (classes, libraries, endpoints from strings), and what you could not see
(native code without a decompiler, encrypted assets, server-side behavior).

# Flutter apps

A Flutter app has `lib/<abi>/libflutter.so` (the engine) and `lib/<abi>/libapp.so` (the app's compiled Dart AOT
snapshot). On Play Store installs these are in `split_config.arm64_v8a.apk`; pass that split's path (or the
pulled/merged APK that contains `lib/`).

## What REA tells you

1. `identify_flutter_build {path}`: per ABI, the Dart snapshot hash of `libapp.so`, library digests, the engine's
   GNU build-id and any Dart/toolchain version strings. The snapshot hash identifies the Dart SDK release (via
   public datasets such as reFlutter's); REA does no lookup.
2. `inspect_dart_aot {path, abi?, detail?}`: the snapshot's exports, headers and a string-pool projection:
   `package:` URIs (the app's own Dart files and its packages), `dart:` SDK URIs, and identifier-like tokens.
   Use `detail: "summary"` and page with `inspect_analysis_view {source: {kind: "retained-evidence", evidence_id:
   <normalized_result.parent_evidence_id>}, view: {kind: "dart-aot", collection: "package_uris" | "dart_uris" |
   "class_like_tokens", offset: 0, limit: 64}}`.
   Full structural coverage is for the legacy split snapshot layout (Dart 2.14-era); newer unified layouts give
   partial results. Say so when it happens.

## What that gives you

- The app's own Dart file layout (`package:<app_name>/screens/login.dart`…) and third-party packages
  (`package:dio/…`, `package:firebase_auth/…`): a good map of features and SDKs.
- Strings in the pool: endpoints, keys, messages.

## Limits

REA does not decompile Dart code. Typed class and function recovery needs an SDK-version-specific tool such as
blutter (not part of this setup). For native view: `native.md` on `libapp.so` (exports, objdump, rizin strings
`izz`) works, but the code is Dart AOT, not C.

The Java/Kotlin side still matters: `MainActivity`, plugins' platform channels (`MethodChannel` names) and
manifest components (`android.md`).

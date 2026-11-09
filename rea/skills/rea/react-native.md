# React Native apps

The JavaScript is `assets/index.android.bundle` in the APK. First find out which kind it is:

```sh
mkdir -p ~/re/<package> && cd ~/re/<package>
unzip -o -q <base.apk> assets/index.android.bundle
file assets/index.android.bundle        # "Hermes JavaScript bytecode, version 96" or plain text/JavaScript
# without `file` (pkg install file): Hermes starts with the bytes c6 1f bc 03 c1 03 19 1f
head -c 8 assets/index.android.bundle | od -An -tx1
```

## Hermes bytecode (most apps since React Native 0.70)

REA has no Hermes decompiler. AntiGem's setup step `hermes` installs **hermes-dec** in the REA container (check:
`rea-shell 'command -v hbc-decompiler'`; if missing, suggest Settings → REA → React Native (hermes-dec), or
`bash <setup>/rea-setup.sh hermes`). Run it through `rea-shell` from the folder with the bundle:

```sh
cd ~/re/<package>
rea-shell 'hbc-file-parser assets/index.android.bundle | head -30'            # header: version, counts
rea-shell 'hbc-decompiler assets/index.android.bundle decompiled.js'           # pseudo-JS (can be 100+ MB, minutes)
rea-shell 'hbc-disassembler assets/index.android.bundle disassembled.hasm'     # lower level, if decompiling fails
```

hermes-dec warns that newer bytecode versions (97, 98…) are not formally supported; output is usually still
usable. The decompiled file is huge: never print it. Search it:

```sh
grep -n -o 'https\?://[^"'"'"' ]*' decompiled.js | sort -u | head -100     # endpoints
grep -n -i -E 'apikey|api_key|secret|token|password' decompiled.js | head -50
grep -n 'fetch\|XMLHttpRequest\|axios' decompiled.js | head -50
grep -n -A30 '<function or string you found>' decompiled.js
```

Strings are also in the parser's string table; `hbc-file-parser` lists counts and `strings -n 8` on the bundle
works as a quick first look.

## Plain JavaScript bundles (older apps, Hermes off)

The bundle is minified JavaScript. Use REA's JavaScript tools (group `javascript`):
`analyze_javascript_application {input_path: "<folder with the bundle>", detail: "summary"}` reconstructs modules
and routes; `recover_javascript_sources` writes recovered sources (and source maps, if any) to a folder. Plain
`grep` on the bundle works too.

## Native and Java sides

React Native apps also have Java/Kotlin code (`MainApplication`, native modules: classes implementing
`ReactContextBaseJavaModule`), see `android.md`, and `.so` libraries (`libhermes.so`, `libreactnative*.so`, the
app's own JNI code), see `native.md`.

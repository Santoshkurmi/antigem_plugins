# Kotlin / Java / Jetpack Compose apps

## A new app

```sh
adev-new compose ~/AndroidProjects/notes --package com.example.notes --name "Notes"
cd ~/AndroidProjects/notes && adev ./gradlew assembleDebug --console=plain
```

`adev-new compose` writes a single-module Compose app and looks up the current stable versions within the majors
it was tested with (AGP 9, Kotlin 2, Compose BOM 2026, Gradle 9), falling back to pinned ones offline:

```
settings.gradle.kts            google() + mavenCentral(), include(":app")
build.gradle.kts               plugins … apply false (android.application, kotlin.android, kotlin.compose)
gradle/libs.versions.toml      every version and library in one place
gradle/wrapper/                wrapper jar + properties (retries=6: GitHub sometimes answers 5xx)
app/build.gradle.kts           namespace, compileSdk/targetSdk 36, minSdk 24, compose = true
app/src/main/AndroidManifest.xml
app/src/main/java/<package>/MainActivity.kt   ComponentActivity + setContent { MaterialTheme { … } }
app/src/main/res/values/{strings,themes}.xml, res/drawable/ic_launcher.xml
```

AGP 9 compiles Kotlin itself ("built-in Kotlin"): the app module applies only `com.android.application` and
`org.jetbrains.kotlin.plugin.compose`. Do **not** apply `org.jetbrains.kotlin.android` in the app module; the root
`kotlin.android … apply false` only pins the Kotlin version so it matches the Compose compiler plugin (both use
the `kotlin` version in the catalog).

The theme is the platform's `android:Theme.Material.Light.NoActionBar`, so there is no AppCompat / Material
Components dependency; Compose's `MaterialTheme` styles the UI.

## Adding things

- Libraries: add them to `gradle/libs.versions.toml` (`[versions]` + `[libraries]`), then
  `implementation(libs.xxx)` in `app/build.gradle.kts`. Compose libraries take their version from the BOM (no
  `version.ref`). Look up the latest version on `https://dl.google.com/dl/android/maven2/<group path>/<artifact>/maven-metadata.xml`
  (AndroidX) or `https://repo1.maven.org/maven2/…/maven-metadata.xml` (Maven Central).
- Common ones: navigation-compose (`androidx.navigation:navigation-compose`), lifecycle-viewmodel-compose
  (`androidx.lifecycle:lifecycle-viewmodel-compose`), material-icons-extended (`androidx.compose.material:material-icons-extended`, large),
  Room (needs KSP: `com.google.devtools.ksp` plugin with the version matching Kotlin), Retrofit / OkHttp, Coil.
- Permissions go in `AndroidManifest.xml`; ask for dangerous ones at run time
  (`rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission())`).
- New SDK platform (`compileSdk = 37`): Gradle downloads `platforms;android-37` by itself, or
  `adev "sdkmanager 'platforms;android-37'"`.

## Java or XML views instead of Compose

- Java sources go in `app/src/main/java/<package>/` next to Kotlin; nothing to configure.
- For an XML-views app, remove the Compose plugin, `buildFeatures.compose` and the Compose dependencies; add
  `androidx.appcompat:appcompat` and `com.google.android.material:material`, use `AppCompatActivity` +
  `setContentView(R.layout.activity_main)`, and a `Theme.Material3.DayNight.NoActionBar` parent theme.

## Building

| Task | What |
| --- | --- |
| `adev ./gradlew assembleDebug` | debug APK: `app/build/outputs/apk/debug/app-debug.apk` |
| `adev ./gradlew assembleRelease` | release APK, only when the user asks (slower; the template signs it with the debug key so it installs; use a real key to publish) |
| `adev ./gradlew bundleRelease` | AAB for Play: `app/build/outputs/bundle/release/` |
| `adev ./gradlew testDebugUnitTest` | JVM unit tests |
| `adev ./gradlew lint` | lint (slow on a phone) |
| `adev ./gradlew --stop` | not needed: each adev call ends Gradle's daemon anyway |

Instrumented tests (`connectedAndroidTest`) need adb connected (`run-on-phone.md`).

### A release key

```sh
cd ~/AndroidProjects/notes
adev "keytool -genkeypair -v -keystore release.jks -alias release -keyalg RSA -keysize 2048 -validity 10000"
```

Then a `signingConfigs { create("release") { … } }` reading the passwords from `~/.gradle/gradle.properties` or
environment variables, never committed. Ask the user for the passwords; do not invent and hide them.

## Existing projects

A project from Android Studio builds the same way. If it pins an old Gradle / AGP, it usually still works with
Java 21 from AGP 8.2 / Gradle 8.5 on; older ones need upgrading (`troubleshooting.md`). Keep the wrapper the
project has unless the build fails because of it.

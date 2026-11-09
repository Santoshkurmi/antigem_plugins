# Troubleshooting builds on the phone

Read the first error of a failed build (`What went wrong`, `e:` lines, `error:`), not the whole log.

| Error | Cause | Fix |
| --- | --- | --- |
| `adev: command not found` | the launcher step is missing | `bash $PREFIX/share/antigem-android/android-setup.sh launcher` (or Settings → Android Development) |
| `SDK location not found` / `ANDROID_HOME` not set | the build ran outside `adev` | run it through `adev`; or write `sdk.dir=/root/android-sdk` to the project's `local.properties` |
| `Server returned HTTP response code: 5xx` downloading `gradle-…-bin.zip` | GitHub (where services.gradle.org redirects) is having trouble | run the build again later; or `bash $S/android-setup.sh gradle-dist <project dir>` (curl with retries). If GitHub stays down, add `--mirror <url>` with a Gradle mirror the user agrees to; the zip must match Gradle's official checksum or it is refused |
| `AAPT2 … Daemon startup failed`, `aapt2 … Syntax error`, `Exec format error` for aapt2 | Gradle uses Google's x86_64 aapt2 | check `/root/.gradle/gradle.properties` has `android.aapt2FromMavenOverride=/data/data/com.termux/files/usr/bin/aapt2` (the sdk step writes it); a project's own `gradle.properties` must not set another one; `pkg install aapt2` if Termux's is missing |
| `… requires … to compile against version NN or later of the Android APIs` | a library needs a newer compileSdk | raise `compileSdk` (Gradle downloads the platform) |
| `Dependency requires at least JVM runtime version 17` / `Unsupported class file major version` | old Gradle / AGP with Java 21 | upgrade the wrapper (`distributionUrl`) to Gradle ≥ 8.5 and AGP ≥ 8.2 |
| `sdkmanager: … android: not found` | command-line tools ≥ 22 (native x86_64 `android` binary) | rerun the sdk step: it reinstalls the Java-based 21.0 tools |
| `Could not GET https://dl.google.com/…` / `Could not resolve …` | network, or a typo in a dependency | check the network; check the coordinates on maven |
| Build killed, `Gradle build daemon disappeared unexpectedly`, `Killed` | Android killed it for memory | close other apps; lower `org.gradle.jvmargs` (`-Xmx1536m`) and `org.gradle.workers.max` (2) in `/root/.gradle/gradle.properties`; keep AntiGem in the foreground |
| Very slow first build | proot + downloads | normal: 5–15 min the first time, 1–3 min after |
| `Unable to delete directory … build` | a file is still open, or the build ran from two places at once | wait for the other build; delete the `build` folder and retry |
| `No space left on device` | Gradle's caches grow by GBs | `bash $S/android-setup.sh clean-cache`; delete old projects' `build` folders |
| `INSTALL_FAILED_*` | see `run-on-phone.md` | |
| `llvm-strip … linux-x86_64 … problem occurred starting process`, a 700 MB `ndk;…` download | the project sets `ndkVersion` and AGP fetched Google's x86 NDK to strip `.so` files | remove `ndkVersion` from `app/build.gradle(.kts)` (not needed without C/C++), delete `/root/android-sdk/ndk`; rerun the sdk step if `/root/.gradle/init.d/antigem-arm64.gradle` is missing |
| The APK has only `lib/arm64-v8a` | intended: phone builds are arm64-only | build other ABIs on a PC |
| `CMake … not found`, `NDK is not installed`, `ninja` errors | the project compiles C/C++ (`externalNativeBuild`, React Native's new architecture, some Flutter plugins) and the ndk step is missing | `android-setup.sh ndk`; see the NDK note below |

## The NDK (C/C++ code)

Google ships the NDK and the SDK's CMake only for x86-64 Linux. The `ndk` step installs them anyway and swaps their
programs for Ubuntu's arm64 ones: the NDK's `clang` / `clang++` become wrappers around Ubuntu's clang of the same
LLVM major version (NDK r28 = LLVM 19), run with the NDK's sysroot, runtime libraries, compiler-rt and libunwind;
`ld.lld` and the `llvm-*` tools link to Ubuntu's; `cmake/3.22.1/bin/{cmake,ninja}` link to Ubuntu's CMake and
Ninja. Builds then work like on a PC, for arm64-v8a.

- Every module with C/C++ (`externalNativeBuild`) is pinned to that NDK by the Gradle init script, whatever
  `ndkVersion` it asks for (`/root/android-sdk/ndk-arm64.txt` names it). So Gradle does not download another
  x86-64 NDK.
- `ndk-build` (Android.mk) projects need `make` from the NDK's x86-64 prebuilt folder, which is removed; install
  Ubuntu's `make` (`adev "apt-get install -y make"`) and call it with `NDK_HOST_AWK=awk`, or port to CMake.
- `CMake … not found`, `NDK is not installed`, `ninja … Exec format error` → `bash $S/android-setup.sh ndk`
  (rerun after a Gradle update that brought another NDK, or to repair).
- A project that needs a CMake feature newer than Ubuntu's 3.28 fails at configure: lower `cmake_minimum_required`
  or ask the user.

## Flutter

| Error | Fix |
| --- | --- |
| `Woah! You appear to be trying to run flutter as root` | a warning only: the container's user is root |
| `gen_snapshot: … Exec format error` / `cannot execute binary file` (release or profile builds) | Flutter has no arm64-Linux gen_snapshot (see `flutter.md` → release builds) |
| `Android sdkmanager not found` in `flutter doctor` | harmless when builds work; rerun the sdk step if a build says it |
| `Unable to locate Android SDK` | `adev flutter config --android-sdk /root/android-sdk` |

## React Native

| Error | Fix |
| --- | --- |
| `npx … EACCES` / `ENOSPC` | the project is outside the Termux home, or the disk is full |
| `Unable to load script. Make sure you're running Metro` on the phone | the debug APK loads JS from Metro: start Metro (`react-native.md`), or build release |
| `Could not start '/root/android-sdk/cmake/3.22.1/bin/cmake'` | the ndk step is missing: `android-setup.sh ndk` |

`S` above is the folder with `android-setup.sh`: `$PREFIX/share/antigem-android`.

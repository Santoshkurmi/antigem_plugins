#!/data/data/com.termux/files/usr/bin/bash
# AntiGem · Android development setup (Kotlin / Jetpack Compose, Flutter, React Native) for Termux + proot-distro
# Ubuntu. AntiGem's Settings → Android Development runs these steps; you (or an agent) can run them in the terminal.
#
#   bash android-setup.sh help                list the steps
#   bash android-setup.sh kotlin              everything for Kotlin / Java / Compose apps
#   bash android-setup.sh container base java any steps, in the order given
#
# It shares the 'ubuntu' container (and Java 21 and Node.js) with REA, so nothing is installed twice.
# Source: antigem_plugins/android-dev/skills/android-dev/scripts/ (AntiGem downloads it into $PREFIX/share/antigem-android/).
set -uo pipefail

P=/data/data/com.termux/files/usr
H=/data/data/com.termux/files/home
export PREFIX="$P" PATH="$P/bin:$PATH" TMPDIR="${TMPDIR:-$P/tmp}" DEBIAN_FRONTEND=noninteractive
C="${ADEV_CONTAINER:-ubuntu}"
IMAGE="${ADEV_IMAGE:-ubuntu:24.04}"
ROOTFS="$P/var/lib/proot-distro/containers/$C/rootfs"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARE="$P/share/antigem-android"
FILES="files.json android-setup.sh adev adev-new"
SDK=/root/android-sdk
NODE_MAJOR=24
NVM_VERSION=v0.40.3
# android-37.0: the Compose template (current AndroidX needs compileSdk 37); android-36: Flutter's and React Native's
SDK_PLATFORMS="${ADEV_PLATFORMS:-android-37.0 android-36}"
SDK_BUILD_TOOLS="${ADEV_BUILD_TOOLS:-36.0.0}"
# Command-line tools 21.0: the last build whose sdkmanager is Java. From 22.0 on it is a wrapper around a native
# 'android' binary that Google builds for x86_64 only.
CMDLINE_TOOLS="${ADEV_CMDLINE_TOOLS:-15641748}"
STRIP_NDK_VERSION=28.2.13676358
# The NDK the ndk step prepares (its LLVM must exist in Ubuntu 24.04: r27 = 18, r28 = 19) and the SDK's CMake package
NDK_VERSION="${ADEV_NDK_VERSION:-28.2.13676358}"
SDK_CMAKE=3.22.1
KEEP="-o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold"
JAVA_HOME_IN=/usr/lib/jvm/java-21-openjdk-arm64
AAPT2="$P/bin/aapt2"
IN_PATH=/root/tools/adev-bin:/root/tools/flutter/bin:/root/tools/node/bin:$SDK/cmdline-tools/latest/bin:$SDK/platform-tools:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

say() { printf '==> %s\n' "$*"; }
ok() { printf '✓ %s\n' "$*"; }
die() { printf '✗ %s\n' "$*" >&2; exit 1; }

has_container() { [ -x "$ROOTFS/usr/bin/apt-get" ]; }
need_container() { has_container || die "The '$C' Ubuntu container is not installed yet. Run the 'container' step first."; }
# Runs a bash script inside the container, with a clean environment (no Termux PATH)
inside() {
    proot-distro login "$C" --shared-tmp -b "$H:/data/user/0/com.termux/files/home" -- /usr/bin/env -i HOME=/root TERM=dumb LANG=C.UTF-8 \
        DEBIAN_FRONTEND=noninteractive "PATH=$IN_PATH" "JAVA_HOME=$JAVA_HOME_IN" "ANDROID_HOME=$SDK" "ANDROID_SDK_ROOT=$SDK" \
        /bin/bash -c "$1"
}

TERMUX_UPDATED=""
termux_install() {
    dpkg --configure -a >/dev/null 2>&1   # finishes an install that was stopped half way
    if [ -z "$TERMUX_UPDATED" ]; then apt-get update -q || die "apt-get update failed in Termux (check the network, or run: pkg upgrade)"; TERMUX_UPDATED=1; fi
    # shellcheck disable=SC2086
    apt-get install -y -q $KEEP "$@" || die "Could not install $* in Termux"
}

IN_UPDATED=""
ubuntu_install() {
    need_container
    local update=""
    [ -z "$IN_UPDATED" ] && update="apt-get update -q && "
    inside "dpkg --configure -a >/dev/null 2>&1; ${update}apt-get install -y -q --no-install-recommends $KEEP $*" || die "Could not install $* in Ubuntu"
    IN_UPDATED=1
}

need_in() { # need_in <path inside the container> <step that provides it>
    [ -e "$ROOTFS$1" ] || die "Needs the '$2' step first."
}

# ---------------- steps ----------------

step_container() {
    command -v proot-distro >/dev/null 2>&1 || termux_install proot-distro
    if has_container; then
        ok "Container '$C' is installed: $(grep -m1 '^PRETTY_NAME=' "$ROOTFS/etc/os-release" 2>/dev/null | cut -d'"' -f2)"
        return 0
    fi
    if [ -d "$P/var/lib/proot-distro/containers/$C" ]; then
        die "A container named '$C' exists but is not an apt-based distribution. Remove it (proot-distro remove $C) or set ADEV_CONTAINER to another name."
    fi
    say "Installing $IMAGE as container '$C' (about 30 MB download)…"
    if [ "$C" = ubuntu ]; then proot-distro install "$IMAGE"; else proot-distro install -n "$C" "$IMAGE"; fi
    has_container || die "proot-distro could not create the container"
    ok "Container '$C' installed"
}

step_base() {
    # zip/unzip/xz/git: Flutter; python3: some Gradle and npm scripts; binutils: strips .so files (strip-only NDK)
    say "Installing base tools in Ubuntu (curl, git, zip, unzip, xz, Python, binutils, procps)…"
    ubuntu_install ca-certificates curl xz-utils procps file zip unzip python3 git binutils
    ok "Base tools installed"
}

step_java() {
    say "Installing OpenJDK 21 (headless) in Ubuntu…"
    ubuntu_install openjdk-21-jdk-headless
    inside 'java -version 2>&1 | head -1'
    ok "Java installed"
}

step_sdk() {
    need_in /usr/bin/curl base
    need_in "$JAVA_HOME_IN/bin/java" java
    # Google's aapt2 (in Gradle's maven) is x86_64 only; Termux builds it for arm64 and it runs in the container
    [ -x "$AAPT2" ] || termux_install aapt2
    "$AAPT2" version >/dev/null 2>&1 || die "Termux's aapt2 does not run: try 'pkg upgrade' in the terminal"
    say "Installing the Android SDK: command-line tools, $SDK_PLATFORMS, build-tools $SDK_BUILD_TOOLS…"
    inside "
set -e
mkdir -p $SDK/cmdline-tools
if [ ! -f $SDK/cmdline-tools/latest/lib/sdkmanager-classpath.jar ] || [ -e $SDK/cmdline-tools/latest/bin/android ]; then
    echo 'command-line tools build $CMDLINE_TOOLS'
    curl -fsSL --retry 3 -o /tmp/cmdline-tools.zip 'https://dl.google.com/android/repository/commandlinetools-linux-${CMDLINE_TOOLS}_latest.zip'
    rm -rf $SDK/cmdline-tools/latest $SDK/cmdline-tools/cmdline-tools
    unzip -q /tmp/cmdline-tools.zip -d $SDK/cmdline-tools
    mv $SDK/cmdline-tools/cmdline-tools $SDK/cmdline-tools/latest
    rm -f /tmp/cmdline-tools.zip
fi
yes | sdkmanager --licenses >/dev/null 2>&1 || true
# platform-tools as a real package (else Flutter / AGP install Google's again as platform-tools-2); its adb is
# replaced with Termux's below. A folder without package.xml is an older setup's adb link only.
[ -f $SDK/platform-tools/package.xml ] || rm -rf $SDK/platform-tools
rm -rf $SDK/platform-tools-[0-9]*
set -- 'platform-tools' 'build-tools;$SDK_BUILD_TOOLS'
for pl in $SDK_PLATFORMS; do set -- \"\$@\" \"platforms;\$pl\"; done
sdkmanager --install \"\$@\" | grep -vE '^\\[=*' || true
for pl in $SDK_PLATFORMS; do [ -d $SDK/platforms/\$pl ] || { echo \"platform \$pl missing after sdkmanager\"; exit 1; }; done
# build-tools ships x86_64 binaries: point their aapt2 at Termux's arm64 one (Gradle itself uses the override below)
for bt in $SDK/build-tools/*/; do ln -sf $AAPT2 \"\$bt/aapt2\"; done
# platform-tools: Termux's adb (Google's is x86_64); Flutter and React Native look for it here
mkdir -p $SDK/platform-tools
if [ -e $P/bin/adb ]; then ln -sf $P/bin/adb $SDK/platform-tools/adb; else rm -f $SDK/platform-tools/adb; fi
# Gradle settings for every project in the container
mkdir -p /root/.gradle
f=/root/.gradle/gradle.properties
touch \$f
setp() { grep -v \"^\$1=\" \$f > \$f.new || true; echo \"\$1=\$2\" >> \$f.new; mv \$f.new \$f; }
setp android.aapt2FromMavenOverride $AAPT2
setp org.gradle.jvmargs '-Xmx2g -XX:MaxMetaspaceSize=768m -Dfile.encoding=UTF-8'
setp org.gradle.vfs.watch false
setp kotlin.compiler.execution.strategy in-process
setp org.gradle.workers.max 4
# Phone builds are for this phone: arm64-v8a only (React Native's C++ and prebuilt libraries)
setp reactNativeArchitectures arm64-v8a
# Strip-only NDK: Google's NDK has no arm64 Linux build, but AGP needs an NDK's llvm-strip / llvm-objcopy for the .so
# files of every app (Flutter's engine, libraries). Builds here are arm64-only, so the container's arm64 GNU
# binutils do the job.
N=$SDK/ndk-strip
rm -rf \$N; mkdir -p \$N/meta \$N/toolchains/llvm/prebuilt/linux-x86_64/bin
printf 'Pkg.Desc = Android NDK (AntiGem: strip only, arm64 GNU binutils)\nPkg.Revision = $STRIP_NDK_VERSION\n' > \$N/source.properties
cat > \$N/meta/abis.json <<'J'
{
  \"armeabi-v7a\": {\"bitness\": 32, \"default\": true, \"deprecated\": false, \"proc\": \"armv7-a\", \"arch\": \"arm\", \"triple\": \"arm-linux-androideabi\", \"llvm_triple\": \"armv7-none-linux-androideabi\"},
  \"arm64-v8a\": {\"bitness\": 64, \"default\": true, \"deprecated\": false, \"proc\": \"aarch64\", \"arch\": \"arm64\", \"triple\": \"aarch64-linux-android\", \"llvm_triple\": \"aarch64-none-linux-android\"},
  \"x86\": {\"bitness\": 32, \"default\": true, \"deprecated\": false, \"proc\": \"i686\", \"arch\": \"x86\", \"triple\": \"i686-linux-android\", \"llvm_triple\": \"i686-none-linux-android\"},
  \"x86_64\": {\"bitness\": 64, \"default\": true, \"deprecated\": false, \"proc\": \"x86_64\", \"arch\": \"x86_64\", \"triple\": \"x86_64-linux-android\", \"llvm_triple\": \"x86_64-none-linux-android\"}
}
J
printf '{\"min\": 21, \"max\": 36, \"aliases\": {}}\n' > \$N/meta/platforms.json
for t in strip objcopy readelf objdump nm; do ln -sf /usr/bin/\$t \$N/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-\$t; done
mkdir -p \$N/build/cmake
printf 'message(FATAL_ERROR \"This project compiles C/C++ code. Install the NDK first: AntiGem Settings > Android Development > C/C++ (NDK), or: bash \$PREFIX/share/antigem-android/android-setup.sh ndk\")\n' > \$N/build/cmake/android.toolchain.cmake
mkdir -p /root/.gradle/init.d
cat > /root/.gradle/init.d/antigem-arm64.gradle <<'INIT'
// AntiGem (android-setup.sh sdk): apps built on the phone are for the phone, so only arm64-v8a native code is
// packaged. Google's NDK has no arm64 Linux build: every module uses the NDK the ndk step rebuilt on Ubuntu's arm64
// LLVM ($SDK/ndk-arm64.txt), or without it a strip-only NDK ($SDK/ndk-strip: llvm-strip / llvm-objcopy are the
// container's arm64 GNU binutils), so .so files are always stripped. ADEV_ALL_ABIS=1 turns this off; build other
// ABIs on a PC.
if (System.getenv('ADEV_ALL_ABIS') != '1') {
    def stripNdk = new File('$SDK/ndk-strip')
    def armNdk = new File('$SDK/ndk-arm64.txt')
    def qemu = new File('$P/bin/qemu-x86_64')
    allprojects {
        // React Native's Hermes compiler (release builds) is a static x86-64 program: run it through Termux's qemu
        pluginManager.withPlugin('com.facebook.react') {
            if (!qemu.canExecute()) return
            def react = extensions.getByName('react')
            def root = react.root.get().asFile
            def f = ['node_modules/hermes-compiler/hermesc/linux64-bin/hermesc', 'node_modules/react-native/sdks/hermesc/linux64-bin/hermesc']
                .collect { new File(root, it) }.find { it.isFile() }
            if (f == null) return
            def head = new byte[4]
            f.withInputStream { it.read(head) }
            if (new String(head, 1, 3, 'US-ASCII') == 'ELF') {
                def real = new File(f.path + '.x86_64')
                real.delete()
                f.renameTo(real)
                f.text = '#!/bin/sh\n# AntiGem (android-setup.sh): the x86-64 hermesc through qemu\nexec ' + qemu.path + ' ' + real.path + ' \"\$@\"\n'
                f.setExecutable(true)
            }
            // without it React Native says: OS not recognized (it does not know Linux on arm64)
            react.hermesCommand.set(f.path)
        }
        ['com.android.application', 'com.android.library'].each { id ->
            pluginManager.withPlugin(id) {
                extensions.getByName('androidComponents').finalizeDsl { ext ->
                    ext.defaultConfig.ndk.abiFilters.clear()
                    ext.defaultConfig.ndk.abiFilters.add('arm64-v8a')
                    if (armNdk.isFile()) {
                        // the NDK the ndk step made work on arm64 (compiles C/C++ and strips), whatever version is asked for
                        ext.ndkVersion = armNdk.text.trim()
                    } else if (stripNdk.isDirectory()) {
                        // strip-only; a C/C++ build stops with a message to install the ndk step
                        ext.ndkPath = stripNdk.path
                        ext.ndkVersion = '$STRIP_NDK_VERSION'
                    }
                }
            }
        }
    }
}
INIT
# A shell in the container (proot-distro login ubuntu) gets the same tools
cat > /etc/profile.d/antigem-android.sh <<'PROFILE'
export JAVA_HOME=$JAVA_HOME_IN
export ANDROID_HOME=$SDK ANDROID_SDK_ROOT=$SDK
export PATH=/root/tools/adev-bin:/root/tools/flutter/bin:/root/tools/node/bin:$SDK/cmdline-tools/latest/bin:$SDK/platform-tools:\$PATH
PROFILE
ls $SDK/platforms $SDK/build-tools
" || die "Android SDK install failed"
    ok "Android SDK installed in $SDK (aapt2: Termux's arm64 build)"
}

# The NDK for C/C++ code (React Native's new architecture, Flutter / Kotlin apps with CMake). Google builds the NDK's
# compilers for x86-64 only, but its sysroot, CMake toolchain file and Android runtime libraries do not depend on the
# host. So: install Google's NDK and CMake packages, then swap their x86-64 programs for Ubuntu's arm64 LLVM of the
# same major version (NDK r28 = LLVM 19), CMake and Ninja, and delete the x86-64 leftovers.
step_ndk() {
    need_in "$SDK/cmdline-tools/latest/lib/sdkmanager-classpath.jar" sdk
    say "Installing NDK $NDK_VERSION and CMake $SDK_CMAKE (Google's packages, x86-64 parts replaced afterwards)…"
    inside "
set -e
[ -f $SDK/ndk/$NDK_VERSION/source.properties ] || sdkmanager --install 'ndk;$NDK_VERSION' | grep -vE '^\\[=*' || true
[ -f $SDK/cmake/$SDK_CMAKE/package.xml ] || sdkmanager --install 'cmake;$SDK_CMAKE' | grep -vE '^\\[=*' || true
[ -f $SDK/ndk/$NDK_VERSION/source.properties ] && [ -f $SDK/cmake/$SDK_CMAKE/package.xml ]
" || die "sdkmanager could not install the NDK or CMake"
    local major
    major=$(head -1 "$ROOTFS$SDK/ndk/$NDK_VERSION/toolchains/llvm/prebuilt/linux-x86_64/AndroidVersion.txt" 2>/dev/null | cut -d. -f1)
    [ -n "$major" ] || major=$(cat "$ROOTFS$SDK/ndk/$NDK_VERSION/.antigem-llvm" 2>/dev/null)
    [ -n "$major" ] || die "Cannot read the NDK's LLVM version"
    say "Installing Ubuntu's arm64 LLVM $major (clang, lld, llvm tools), CMake and Ninja…"
    ubuntu_install "clang-$major" "lld-$major" "llvm-$major" cmake ninja-build
    say "Pointing the NDK and CMake at the arm64 tools…"
    inside "
set -e
N=$SDK/ndk/$NDK_VERSION
T=\$N/toolchains/llvm/prebuilt/linux-x86_64
L=/usr/lib/llvm-$major/bin
NR=\$(ls -d \$T/lib/clang/[0-9]* | head -1)
[ -d \"\$NR/lib/linux\" ] || { echo \"No Android runtime libraries in \$NR\"; exit 1; }
# clang's built-in headers (arm_neon.h…) must be the compiler's own; the Android runtime libraries are the NDK's
R=\$T/lib/clang/antigem
rm -rf \$R; mkdir -p \$R
ln -s \$(ls -d /usr/lib/llvm-$major/lib/clang/*/include | head -1) \$R/include
ln -s \$NR/lib \$R/lib
[ -d \$NR/share ] && ln -s \$NR/share \$R/share
for f in \$T/bin/*; do
    n=\$(basename \$f)
    case \$n in
        clang|clang-[0-9]*|clang++) continue ;;
    esac
    # the <target><api>-clang scripts call ./clang and stay; x86-64 programs are replaced or removed
    if head -c 4 \$f 2>/dev/null | grep -q ELF || [ -L \$f ]; then
        rm -f \$f
        [ -x \$L/\$n ] && ln -s \$L/\$n \$f
    fi
done
rm -f \$T/bin/clang \$T/bin/clang++ \$T/bin/clang-[0-9]*
# NDK clang finds its runtime libraries and sysroot next to itself and links with compiler-rt + libunwind; Ubuntu's
# clang is told all of that (the link-only flags only when linking: RN compiles with -Werror)
cat > /tmp/antigem-clang.in <<'WRAP'
#!/bin/sh
# AntiGem (android-setup.sh ndk): Ubuntu's arm64 clang with this NDK's runtime libraries and sysroot
link=1
for a in \"\$@\"; do case \"\$a\" in -c|-S|-E|-M|-MM|-fsyntax-only) link=0 ;; esac; done
if [ \$link = 1 ]; then
    exec @CC@ -resource-dir @RES@ --sysroot=@SYS@ --rtlib=compiler-rt --unwindlib=libunwind \"\$@\"
fi
exec @CC@ -resource-dir @RES@ --sysroot=@SYS@ \"\$@\"
WRAP
for c in clang clang++; do
    sed -e \"s#@CC@#\$L/\$c#g\" -e \"s#@RES@#\$R#g\" -e \"s#@SYS@#\$T/sysroot#g\" /tmp/antigem-clang.in > \$T/bin/\$c
    chmod 755 \$T/bin/\$c
done
rm -f /tmp/antigem-clang.in
ln -sf clang \$T/bin/clang-$major
for t in ld ld.lld lld; do ln -sf \$L/ld.lld \$T/bin/\$t; done
# x86-64 leftovers: host LLVM libraries, Python, musl, make, simpleperf
rm -rf \$T/lib/lib*.so* \$T/lib/python3* \$T/python3 \$T/musl \$T/libexec \$N/prebuilt/linux-x86_64 \$N/simpleperf
echo $major > \$N/.antigem-llvm
# CMake: the SDK package Gradle asks for, running Ubuntu's arm64 cmake and ninja
C=$SDK/cmake/$SDK_CMAKE/bin
for t in cmake ctest cpack ninja; do rm -f \$C/\$t; done
ln -s /usr/bin/cmake \$C/cmake; ln -s /usr/bin/ctest \$C/ctest; ln -s /usr/bin/cpack \$C/cpack; ln -s /usr/bin/ninja \$C/ninja
rm -rf $SDK/cmake/$SDK_CMAKE/share
echo $NDK_VERSION > $SDK/ndk-arm64.txt
echo \"NDK \$(basename \$N) → \$(\$T/bin/clang --version | head -1); cmake \$(cmake --version | head -1 | cut -d' ' -f3)\"
du -sh \$N
" || die "Could not set up the NDK with arm64 tools"
    ok "NDK $NDK_VERSION works on arm64 (Ubuntu LLVM $major). Gradle uses it for every C/C++ build."
}

step_flutter() {
    need_in /usr/bin/git base
    need_in "$SDK/cmdline-tools/latest/lib/sdkmanager-classpath.jar" sdk
    say "Installing Flutter (stable channel) in Ubuntu: about 1.5 GB with the Android engine files…"
    inside "
set -e
mkdir -p /root/tools
if [ ! -x /root/tools/flutter/bin/flutter ]; then
    rm -rf /root/tools/flutter.part
    git clone --depth 1 --branch stable https://github.com/flutter/flutter.git /root/tools/flutter.part
    mv /root/tools/flutter.part /root/tools/flutter
else
    cd /root/tools/flutter && git fetch --depth 1 origin stable && git reset --hard FETCH_HEAD
fi
git config --global --add safe.directory /root/tools/flutter
export FLUTTER_SUPPRESS_ANALYTICS=true
flutter --disable-analytics >/dev/null 2>&1 || true
dart --disable-analytics >/dev/null 2>&1 || true
flutter config --no-analytics --android-sdk $SDK --no-enable-web --no-enable-linux-desktop >/dev/null
flutter precache --android --no-ios --no-web --no-linux --no-windows --no-macos --no-fuchsia
yes | flutter doctor --android-licenses >/dev/null 2>&1 || true
flutter --version
" || die "Flutter install failed"
    write_flutter_wrapper
    # an update or precache brings fresh x86-64 gen_snapshot files: wrap them again
    [ -x "$P/bin/qemu-x86_64" ] && [ -d "$ROOTFS/usr/x86_64-linux-gnu" ] && wrap_gen_snapshot
    ok "Flutter installed in /root/tools/flutter"
}

# Flutter's release / profile compiler (gen_snapshot) exists only as an x86-64 Linux program (engine/<target>/linux-x64),
# while Flutter on an arm64 host looks for engine/<target>/linux-arm64/gen_snapshot. Those are small wrappers that
# run the x86-64 program with Termux's qemu-user (qemu-x86_64 11; Ubuntu 24.04's qemu 8.2 crashes under proot) and
# Ubuntu's x86-64 C library (libc6-amd64-cross). Flutter's files stay as they are.
wrap_gen_snapshot() {
    inside "
for x in /root/tools/flutter/bin/cache/artifacts/engine/*/linux-x64/gen_snapshot; do
    [ -f \"\$x\" ] || continue
    # an older setup renamed the binary: put it back
    if [ -f \"\$x.x86_64\" ]; then mv -f \"\$x.x86_64\" \"\$x\"; fi
    d=\"\$(dirname \"\$(dirname \"\$x\")\")/linux-arm64\"
    [ -e \"\$d/gen_snapshot\" ] && ! grep -q AntiGem \"\$d/gen_snapshot\" 2>/dev/null && continue   # a real arm64 build: keep it
    mkdir -p \"\$d\"
    printf '#!/bin/sh\\n# AntiGem (android-setup.sh flutter-release): the x86-64 gen_snapshot through qemu\\nexec $P/bin/qemu-x86_64 -L /usr/x86_64-linux-gnu %s \"\$@\"\\n' \"\$x\" > \"\$d/gen_snapshot\"
    chmod 755 \"\$d/gen_snapshot\"
    echo \"wrapped \${d#/root/tools/flutter/bin/cache/artifacts/engine/}/gen_snapshot\"
done
"
}

step_flutter_release() {
    need_in /root/tools/flutter/bin/cache/dart-sdk/bin/dart flutter
    say "Installing qemu (Termux) and the x86-64 C library (Ubuntu), for Flutter release and profile builds…"
    termux_install qemu-user-x86-64
    ubuntu_install libc6-amd64-cross
    wrap_gen_snapshot
    inside "/root/tools/flutter/bin/cache/artifacts/engine/android-arm64-release/linux-arm64/gen_snapshot --version 2>&1 | head -1" \
        || die "gen_snapshot does not run under qemu"
    ok "Flutter release builds work (gen_snapshot runs through qemu: a few minutes per build)"
}

# /root/tools/adev-bin/flutter: Flutter for this phone. 'flutter build apk|appbundle|aar' builds arm64 only
# (Flutter's default is arm, arm64 and x64: three Dart compiles); ADEV_ALL_ABIS=1 or an explicit
# --target-platform keeps Flutter's own choice.
write_flutter_wrapper() {
    inside "
mkdir -p /root/tools/adev-bin
cat > /root/tools/adev-bin/flutter <<'WRAP'
#!/bin/bash
# AntiGem (android-setup.sh flutter): Android builds on the phone are arm64-v8a only. ADEV_ALL_ABIS=1 turns it off.
real=/root/tools/flutter/bin/flutter
if [ \"\${ADEV_ALL_ABIS:-}\" != 1 ] && [ \"\${1:-}\" = build ]; then
    case \"\${2:-}\" in
        apk|appbundle|aar)
            case \" \$* \" in *' --target-platform'*) ;; *) exec \"\$real\" \"\$@\" --target-platform android-arm64 ;; esac ;;
    esac
fi
exec \"\$real\" \"\$@\"
WRAP
chmod 755 /root/tools/adev-bin/flutter
"
}

step_node() {
    need_in /usr/bin/curl base
    say "Installing Node.js $NODE_MAJOR with nvm $NVM_VERSION in Ubuntu (the same Node.js REA uses)…"
    inside "
set -e
export NVM_DIR=/root/.nvm
if [ ! -s \"\$NVM_DIR/nvm.sh\" ]; then
    curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/$NVM_VERSION/install.sh | PROFILE=/dev/null bash
fi
. \"\$NVM_DIR/nvm.sh\"
nvm install $NODE_MAJOR --no-progress
nvm alias default $NODE_MAJOR >/dev/null
mkdir -p /root/tools
ln -sfnr \"\$(dirname \"\$(dirname \"\$(nvm which $NODE_MAJOR)\")\")\" /root/tools/node
echo \"node \$(/root/tools/node/bin/node -v), npm \$(/root/tools/node/bin/npm -v)\"
" || die "Node.js install failed"
    # React Native release builds run the x86-64 hermesc through qemu (the Gradle init script wraps it)
    [ -x "$P/bin/qemu-x86_64" ] || termux_install qemu-user-x86-64
    ok "Node.js installed"
}

step_launcher() {
    say "Installing the adev and adev-new commands…"
    mkdir -p "$SHARE" || die "Cannot create $SHARE"
    if [ "$HERE" != "$SHARE" ]; then
        for f in $FILES; do [ -f "$HERE/$f" ] && cp -f "$HERE/$f" "$SHARE/$f"; done
    fi
    for f in adev adev-new; do [ -f "$SHARE/$f" ] || die "$SHARE/$f is missing (run this script from its own folder)"; done
    chmod 755 "$SHARE/adev" "$SHARE/adev-new" "$SHARE/android-setup.sh" 2>/dev/null
    ln -sf "$SHARE/adev" "$P/bin/adev"
    ln -sf "$SHARE/adev-new" "$P/bin/adev-new"
    ok "adev and adev-new installed in $P/bin"
}

step_adb() {
    say "Installing adb (Termux android-tools) to install and debug apps on this phone…"
    termux_install android-tools
    [ -d "$ROOTFS$SDK/platform-tools" ] && ln -sf "$P/bin/adb" "$ROOTFS$SDK/platform-tools/adb"
    ok "adb installed. Connect it to this phone in AntiGem Settings → ADB Connect."
}

step_doctor() {
    need_container
    inside "
echo \"java:      \$(java -version 2>&1 | head -1)\"
echo \"sdk:       \$(ls $SDK/platforms 2>/dev/null | tr '\n' ' ') · build-tools \$(ls $SDK/build-tools 2>/dev/null | tr '\n' ' ')\"
echo \"aapt2:     \$($AAPT2 version 2>&1 | head -1)\"
echo \"adb:       \$([ -x $SDK/platform-tools/adb ] && $SDK/platform-tools/adb version 2>/dev/null | head -1 || echo missing)\"
echo \"node:      \$(node -v 2>/dev/null || echo missing)\"
echo \"flutter:   \$(flutter --version 2>/dev/null | head -1 || echo missing)\"
echo \"cmake:     \$(cmake --version 2>/dev/null | head -1 || echo missing)\"
grep -E 'aapt2|jvmargs' /root/.gradle/gradle.properties 2>/dev/null
"
    return 0
}

# gradle-dist [project dir|version] [--mirror BASE_URL]: puts a project's Gradle distribution in the wrapper's cache.
# For when the wrapper's own download fails (GitHub, where services.gradle.org redirects, sometimes answers 5xx):
# curl retries with back-off, and a mirror can be given. The zip must match Gradle's official SHA-256 either way.
step_gradle_dist() {
    local arg="${1:-$PWD}" mirror="" props url version sum
    [ "${2:-}" = --mirror ] && mirror="${3:-}"
    [ "${1:-}" = --mirror ] && { mirror="${2:-}"; arg="$PWD"; }
    need_in /usr/bin/python3 base
    if [ -d "$arg" ]; then
        props="$arg/gradle/wrapper/gradle-wrapper.properties"
        [ -f "$props" ] || props="$arg/android/gradle/wrapper/gradle-wrapper.properties"
        [ -f "$props" ] || die "No gradle/wrapper/gradle-wrapper.properties in $arg"
        url=$(grep -E '^distributionUrl=' "$props" | cut -d= -f2- | sed 's/\\:/:/g; s/\\//g')
    else
        url="https://services.gradle.org/distributions/gradle-$arg-bin.zip"
    fi
    version=$(printf '%s' "$url" | grep -oE 'gradle-[0-9][0-9.a-z-]*-(bin|all)' | head -1)
    [ -n "$version" ] || die "Cannot read the Gradle version from $url"
    say "Gradle distribution $version ($url)"
    sum=$(curl -fsSL --retry 5 --retry-all-errors "https://services.gradle.org/distributions/$version.zip.sha256" 2>/dev/null)
    [ ${#sum} -eq 64 ] || die "Could not read Gradle's official checksum for $version (network?)"
    inside "
set -e
h=\$(python3 - '$url' <<'PY'
import hashlib, sys
n = int.from_bytes(hashlib.md5(sys.argv[1].encode()).digest(), 'big')
d = '0123456789abcdefghijklmnopqrstuvwxyz'; out = ''
while n: n, r = divmod(n, 36); out = d[r] + out
print(out or '0')
PY
)
dir=/root/.gradle/wrapper/dists/$version/\$h
mkdir -p \$dir
if [ -f \$dir/$version.zip.ok ]; then echo 'Already installed'; exit 0; fi
src='$url'
[ -n '$mirror' ] && src='${mirror%/}/$version.zip'
echo \"Downloading \$src\"
curl -fL --retry 8 --retry-all-errors --retry-delay 10 -sS -o \$dir/$version.zip.part \"\$src\"
echo '$sum  '\$dir/$version.zip.part | sha256sum -c --status || { rm -f \$dir/$version.zip.part; echo 'Checksum does not match Gradle official one'; exit 1; }
mv \$dir/$version.zip.part \$dir/$version.zip
echo \"Saved in \$dir (checksum OK)\"
" || die "Could not get $version"
    ok "$version is in the wrapper's cache: the next build uses it"
}

# test <compose|flutter|rn>: creates ~/AndroidProjects/hello-<kind> once and builds its debug APK
step_test() {
    local kind="${1:-}" dir apk
    [ -x "$P/bin/adev-new" ] || die "Needs the 'launcher' step first."
    dir="$H/AndroidProjects/hello-$kind"
    case "$kind" in
        compose) need_in "$SDK/cmdline-tools/latest/lib/sdkmanager-classpath.jar" sdk; apk="$dir/app/build/outputs/apk/debug/app-debug.apk" ;;
        flutter) need_in /root/tools/flutter/bin/cache/dart-sdk/bin/dart flutter; apk="$dir/build/app/outputs/flutter-apk/app-debug.apk" ;;
        rn) need_in /root/tools/node/bin/node node; need_in "$SDK/ndk-arm64.txt" ndk; apk="$dir/android/app/build/outputs/apk/debug/app-debug.apk" ;;
        *) die "test needs compose, flutter or rn" ;;
    esac
    mkdir -p "$H/AndroidProjects"
    if [ ! -e "$dir" ]; then
        "$P/bin/adev-new" "$kind" "$dir" || die "Could not create the $kind test project"
    fi
    # The wrapper downloads Gradle once, without retries in older wrappers: fetch it first, with retries
    (step_gradle_dist "$dir") || say "Could not fetch Gradle ahead; the build tries itself."
    say "Building $dir (the first build downloads Gradle and libraries: several minutes)…"
    case "$kind" in
        compose) (cd "$dir" && "$P/bin/adev" ./gradlew assembleDebug --console=plain) ;;
        flutter) (cd "$dir" && "$P/bin/adev" flutter build apk --debug) ;;
        rn) (cd "$dir/android" && "$P/bin/adev" ./gradlew assembleDebug --console=plain) ;;
    esac || die "The $kind test build failed (see above)"
    [ -f "$apk" ] || die "The build finished but $apk is missing"
    ok "Built $apk ($(du -h "$apk" | cut -f1))"
}

installed() { [ -e "$1" ] && echo yes || echo no; }
step_status() {
    echo "container=$(installed "$ROOTFS/usr/bin/apt-get")"
    echo "base=$( [ -e "$ROOTFS/usr/bin/git" ] && [ -e "$ROOTFS/usr/bin/zip" ] && echo yes || echo no)"
    echo "java=$(installed "$ROOTFS$JAVA_HOME_IN/bin/javac")"
    echo "sdk=$( [ -e "$ROOTFS$SDK/cmdline-tools/latest/lib/sdkmanager-classpath.jar" ] && ls -d "$ROOTFS$SDK"/platforms/android-* >/dev/null 2>&1 && [ -x "$AAPT2" ] && echo yes || echo no)"
    echo "launcher=$(installed "$P/bin/adev")"
    echo "flutter=$(installed "$ROOTFS/root/tools/flutter/bin/cache/dart-sdk/bin/dart")"
    echo "flutter-release=$( [ -e "$ROOTFS/root/tools/flutter/bin/cache/artifacts/engine/android-arm64-release/linux-arm64/gen_snapshot" ] && [ -x "$P/bin/qemu-x86_64" ] && echo yes || echo no)"
    echo "node=$(installed "$ROOTFS/root/tools/node/bin/node")"
    echo "ndk=$( [ -f "$ROOTFS$SDK/ndk-arm64.txt" ] && [ -x "$ROOTFS$SDK/ndk/$NDK_VERSION/toolchains/llvm/prebuilt/linux-x86_64/bin/clang" ] && echo yes || echo no)"
    echo "adb=$(installed "$P/bin/adb")"
}

step_uninstall_flutter() {
    say "Removing Flutter and its caches…"
    has_container && inside "rm -rf /root/tools/flutter /root/tools/adev-bin /root/.pub-cache /root/.flutter /root/.dart-tool /root/.config/flutter"
    ok "Flutter removed"
}

step_uninstall() {
    say "Removing the Android SDK, Flutter, the Gradle cache and the adev commands (the container, Java and Node.js stay)…"
    if has_container; then
        inside "rm -rf $SDK /root/tools/flutter /root/tools/adev-bin /root/.pub-cache /root/.flutter /root/.gradle /root/.android /etc/profile.d/antigem-android.sh; true"
    fi
    rm -f "$P/bin/adev" "$P/bin/adev-new"
    rm -rf "$SHARE"
    ok "Android development tools removed. Your projects are untouched. To delete the whole container: proot-distro remove $C"
}

step_clean_cache() {
    say "Deleting Gradle's caches and downloaded Gradle versions (they come back on the next build)…"
    has_container && inside "rm -rf /root/.gradle/caches /root/.gradle/wrapper/dists /root/.gradle/daemon /root/.gradle/native; du -sh /root/.gradle 2>/dev/null"
    ok "Gradle cache cleaned"
}

usage() {
    cat <<EOF
AntiGem Android development setup: tools run in the proot-distro container '$C' ($IMAGE), shared with REA.

Usage: bash android-setup.sh STEP [STEP...]

Groups of steps
  kotlin      container base java sdk launcher           Kotlin / Java / Jetpack Compose apps (start here)
  flutter-all kotlin + flutter flutter-release           Flutter apps
  rn          kotlin + node ndk                          React Native apps
  all         kotlin + flutter flutter-release node ndk adb

Steps (each can be rerun to repair or update)
  container   proot-distro and the Ubuntu 24.04 container
  base        curl, git, zip, unzip, xz, Python in Ubuntu
  java        OpenJDK 21 headless (Gradle, the Android SDK tools)
  sdk         Android command-line tools, $SDK_PLATFORMS, build-tools $SDK_BUILD_TOOLS, Termux's arm64 aapt2,
              Gradle settings for the phone (/root/.gradle/gradle.properties)
  launcher    the adev (run a command with the tools) and adev-new (new project) commands
  flutter     Flutter stable + its Android engine files
  flutter-release  Termux qemu-user + Ubuntu's x86-64 C library: Flutter release / profile builds (gen_snapshot is
              x86-64 only; it runs emulated, a few minutes per build)
  node        Node.js $NODE_MAJOR through nvm (React Native, Expo)
  ndk         NDK $NDK_VERSION + CMake for C/C++ code (React Native): Google's packages with their x86-64
              programs swapped for Ubuntu's arm64 LLVM, CMake and Ninja (≈1.5 GB)
  adb         adb in Termux, to install apps on this phone

Other
  gradle-dist [DIR|VERSION] [--mirror URL]   fetch a project's Gradle zip into the wrapper cache (when the
                   wrapper's download fails); a mirror's zip must match Gradle's official checksum
  test KIND        create ~/AndroidProjects/hello-KIND once and build it (KIND: compose, flutter, rn)
  doctor           versions of every tool
  status           what is installed (key=yes|no)
  clean-cache      delete Gradle's caches (frees space; the next build downloads again)
  uninstall-flutter  remove Flutter only
  uninstall        remove the SDK, Flutter, Gradle's files and adev (keeps the container, Java, Node.js)
EOF
}

run_step() {
    case "$1" in
        kotlin) for s in container base java sdk launcher; do run_step "$s" || return $?; done ;;
        flutter-all) for s in container base java sdk launcher flutter flutter-release; do run_step "$s" || return $?; done ;;
        rn) for s in container base java sdk launcher node ndk; do run_step "$s" || return $?; done ;;
        all) for s in container base java sdk launcher flutter flutter-release node ndk adb; do run_step "$s" || return $?; done ;;
        container|base|java|sdk|ndk|flutter|node|launcher|adb|doctor|status|uninstall) "step_$1" ;;
        flutter-release) step_flutter_release ;;
        clean-cache) step_clean_cache ;;
        uninstall-flutter) step_uninstall_flutter ;;
        help|-h|--help) usage ;;
        *) usage; die "Unknown step: $1" ;;
    esac
}

[ $# -gt 0 ] || { usage; exit 0; }
if [ "$1" = test ]; then step_test "${2:-}"; exit $?; fi
if [ "$1" = gradle-dist ]; then shift; step_gradle_dist "$@"; exit $?; fi
for step in "$@"; do run_step "$step" || exit $?; done

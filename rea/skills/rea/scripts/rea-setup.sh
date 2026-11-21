#!/data/data/com.termux/files/usr/bin/bash
# AntiGem · REA (Reverse Engineer Anything, github.com/morluto/rea) setup for Termux + proot-distro Ubuntu.
# AntiGem's Settings → REA runs these steps; you (or an agent) can run them in the terminal too.
#
#   bash rea-setup.sh help                 list the steps
#   bash rea-setup.sh android              everything needed to analyze APKs (recommended)
#   bash rea-setup.sh container base java  any steps, in the order given
#
# Source: antigem_plugins/rea/skills/rea/scripts/ (AntiGem downloads this folder into $PREFIX/share/antigem-rea/).
set -uo pipefail

say() { printf '==> %s\n' "$*"; }
ok() { printf '✓ %s\n' "$*"; }
die() { printf '✗ %s\n' "$*" >&2; exit 1; }

# Where REA runs. In AntiGem's terminal (Termux): a proot-distro Ubuntu container. In AntiGem's Ubuntu chroot (rooted
# phones): that Ubuntu itself, no container. There AntiGem runs this script inside the chroot as root with
# ANTIGEM_RUNTIME=chroot and ANTIGEM_USER=<the chroot's user>: the tools go to /opt/antigem (every user can run them),
# the launchers to /usr/local/bin and the tool groups to the user's ~/.config/antigem/rea.
RUNTIME="${ANTIGEM_RUNTIME:-termux}"
C="${REA_CONTAINER:-ubuntu}"
IMAGE="${REA_IMAGE:-ubuntu:24.04}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$RUNTIME" = chroot ]; then
    [ "$(id -u)" = 0 ] || die "In the Ubuntu chroot this script runs as root: sudo env ANTIGEM_RUNTIME=chroot bash $0 ${*:-help}"
    U="${ANTIGEM_USER:-${SUDO_USER:-}}"
    UH=""
    [ -n "$U" ] && UH=$(getent passwd "$U" | cut -d: -f6)
    [ -n "$UH" ] || { U=""; UH=/root; }
    export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin DEBIAN_FRONTEND=noninteractive
    ROOTFS=""
    T=/opt/antigem/tools
    NVM_HOME=/opt/antigem/nvm
    SHARE=/opt/antigem/share/antigem-rea
    BIN=/usr/local/bin
    CONF="$UH/.config/antigem/rea"
else
    P=/data/data/com.termux/files/usr
    H=/data/data/com.termux/files/home
    export PREFIX="$P" PATH="$P/bin:$PATH" TMPDIR="${TMPDIR:-$P/tmp}" DEBIAN_FRONTEND=noninteractive
    ROOTFS="$P/var/lib/proot-distro/containers/$C/rootfs"
    T=/root/tools
    NVM_HOME=/root/.nvm
    SHARE="$P/share/antigem-rea"
    BIN="$P/bin"
    CONF="$H/.config/antigem/rea"
fi
NODE_MAJOR=24
NVM_VERSION=v0.40.3
JADX_VERSION=0.7.1
JADX_JAR="jadx-headless-mcp-$JADX_VERSION-all.jar"
JADX_URL="https://github.com/1013503897/jadx-headless-mcp/releases/download/v$JADX_VERSION/$JADX_JAR"
APKTOOL_FALLBACK=3.0.3
KEEP="-o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold"
# Ubuntu's name for this CPU, in its JDK folder (java-21-openjdk-arm64 / -amd64)
case "$(uname -m)" in x86_64) DEB_ARCH=amd64 ;; *) DEB_ARCH=arm64 ;; esac
JAVA_BIN=/usr/lib/jvm/java-21-openjdk-$DEB_ARCH/bin/java   # real file: /usr/bin/java is an absolute symlink the Termux side cannot follow
IN_PATH=$T/node/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

has_container() { [ -x "$ROOTFS/usr/bin/apt-get" ]; }
need_container() { has_container || die "The '$C' Ubuntu container is not installed yet. Run the 'container' step first."; }
# Runs a bash script inside the container (in the chroot: right here, as root), with a clean environment (no Termux PATH)
inside() {
    if [ "$RUNTIME" = chroot ]; then
        /usr/bin/env -i HOME=/root TERM=dumb LANG=C.UTF-8 DEBIAN_FRONTEND=noninteractive "PATH=$IN_PATH" /bin/bash -c "$1"
        return
    fi
    proot-distro login "$C" --shared-tmp -b "$H:/data/user/0/com.termux/files/home" -- /usr/bin/env -i HOME=/root TERM=dumb LANG=C.UTF-8 \
        DEBIAN_FRONTEND=noninteractive "PATH=$IN_PATH" /bin/bash -c "$1"
}

# In the chroot: runs a command as the chroot's user (their HOME, files they own). In Termux: as is.
as_user() {
    if [ "$RUNTIME" = chroot ] && [ -n "$U" ]; then
        runuser -u "$U" -- /usr/bin/env HOME="$UH" LANG=C.UTF-8 "PATH=$PATH" "$@"
    else
        "$@"
    fi
}

TERMUX_UPDATED=""
termux_install() {
    [ "$RUNTIME" = chroot ] && die "Termux packages ($*) are not used in the Ubuntu chroot"
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
    # dpkg --configure -a: finishes an install that was stopped half way
    inside "dpkg --configure -a >/dev/null 2>&1; ${update}apt-get install -y -q --no-install-recommends $KEEP $*" || die "Could not install $* in Ubuntu"
    IN_UPDATED=1
}

need_in() { # need_in <path inside the container> <step that provides it>
    [ -e "$ROOTFS$1" ] || die "Needs the '$2' step first."
}

# ---------------- steps ----------------

step_container() {
    if [ "$RUNTIME" = chroot ]; then
        ok "REA installs straight into AntiGem's Ubuntu chroot: $(grep -m1 '^PRETTY_NAME=' /etc/os-release 2>/dev/null | cut -d'"' -f2)"
        return 0
    fi
    command -v proot-distro >/dev/null 2>&1 || termux_install proot-distro
    if has_container; then
        ok "Container '$C' is installed: $(grep -m1 '^PRETTY_NAME=' "$ROOTFS/etc/os-release" 2>/dev/null | cut -d'"' -f2)"
        return 0
    fi
    if [ -d "$P/var/lib/proot-distro/containers/$C" ]; then
        die "A container named '$C' exists but is not an apt-based distribution. Remove it (proot-distro remove $C) or set REA_CONTAINER to another name."
    fi
    say "Installing $IMAGE as container '$C' (about 30 MB download)…"
    if [ "$C" = ubuntu ]; then proot-distro install "$IMAGE"; else proot-distro install -n "$C" "$IMAGE"; fi
    has_container || die "proot-distro could not create the container"
    ok "Container '$C' installed"
}

step_base() {
    say "Installing base tools in Ubuntu (curl, Python, git, unzip, file, procps)…"
    ubuntu_install ca-certificates curl xz-utils procps file unzip python3 git
    ok "Base tools installed"
}

step_java() {
    say "Installing OpenJDK 21 (headless) in Ubuntu…"
    ubuntu_install openjdk-21-jdk-headless
    inside 'java -version 2>&1 | head -1'
    ok "Java installed"
}

step_node() {
    need_in /usr/bin/curl base
    say "Installing Node.js $NODE_MAJOR with nvm $NVM_VERSION in Ubuntu…"
    inside "
set -e
export NVM_DIR=$NVM_HOME
prev=\$(readlink -f $T/node 2>/dev/null || true)
if [ ! -s \"\$NVM_DIR/nvm.sh\" ]; then
    curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/$NVM_VERSION/install.sh | bash
fi
. \"\$NVM_DIR/nvm.sh\"
nvm install $NODE_MAJOR --no-progress
nvm alias default $NODE_MAJOR >/dev/null
mkdir -p $T
ln -sfnr \"\$(dirname \"\$(dirname \"\$(nvm which $NODE_MAJOR)\")\")\" $T/node
echo \"node \$($T/node/bin/node -v), npm \$($T/node/bin/npm -v)\"
# A newer Node has its own global packages: bring REA along
if [ -n \"\$prev\" ] && [ -d \"\$prev/lib/node_modules/rea-agents\" ] && [ ! -d $T/node/lib/node_modules/rea-agents ]; then
    echo 'Reinstalling REA for the new Node…'
    npm install -g rea-agents@latest --no-fund --no-audit
fi
" || die "Node.js install failed"
    ok "Node.js installed"
}

step_rea() {
    need_in $T/node/bin/node node
    say "Installing REA (npm rea-agents)…"
    inside "npm install -g rea-agents@latest --no-fund --no-audit && echo \"REA \$(rea --version)\"" || die "npm could not install rea-agents"
    ok "REA installed"
    [ -x "$BIN/rea-mcp" ] && { (step_tools) || say "Could not refresh the tool list now; Settings → REA → Refresh tool list retries."; }
    return 0
}

step_jadx() {
    need_in /usr/bin/curl base
    say "Downloading jadx-headless-mcp $JADX_VERSION (JADX bridge REA uses)…"
    inside "set -e; mkdir -p $T; curl -fL --retry 3 -o $T/$JADX_JAR.part '$JADX_URL'; mv $T/$JADX_JAR.part $T/$JADX_JAR; ls -la $T/$JADX_JAR" \
        || die "Could not download $JADX_URL"
    [ -e "$ROOTFS$JAVA_BIN" ] || say "Note: JADX also needs the 'java' step."
    ok "JADX bridge installed"
}

step_apktool() {
    need_in /usr/bin/curl base
    say "Downloading the latest apktool jar (official release, not Ubuntu's old 2.7)…"
    inside "
set -e
v=\$(curl -fsSL https://api.github.com/repos/iBotPeaches/Apktool/releases/latest 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"tag_name\"].lstrip(\"v\"))' 2>/dev/null || true)
[ -n \"\$v\" ] || v=$APKTOOL_FALLBACK
echo \"apktool \$v\"
mkdir -p $T
curl -fL --retry 3 -o $T/apktool.jar.part \"https://github.com/iBotPeaches/Apktool/releases/download/v\$v/apktool_\$v.jar\"
mv $T/apktool.jar.part $T/apktool.jar
printf '#!/bin/sh\nexec java -jar $T/apktool.jar \"\$@\"\n' > /usr/local/bin/apktool
chmod 755 /usr/local/bin/apktool
" || die "Could not install apktool"
    [ -e "$ROOTFS$JAVA_BIN" ] || say "Note: apktool also needs the 'java' step."
    ok "apktool installed"
}

# Ubuntu has no rizin package (24.04 has none): the rizin project builds its own Ubuntu packages on openSUSE's build
# service (home:RizinOrg, xUbuntu_<version>, arm64 and amd64). Adds that repository, signed with its key.
add_rizin_repo() {
    local ver repo
    ver=$(. /etc/os-release 2>/dev/null && echo "$VERSION_ID")
    repo="https://download.opensuse.org/repositories/home:/RizinOrg/xUbuntu_$ver"
    say "Ubuntu $ver has no rizin package: adding the rizin project's own repository ($repo)…"
    command -v curl >/dev/null 2>&1 || ubuntu_install ca-certificates curl
    mkdir -p /etc/apt/keyrings
    curl -fsSL --retry 3 "$repo/Release.key" -o /etc/apt/keyrings/rizin.asc.part \
        || die "The rizin project has no packages for Ubuntu $ver ($repo)"
    mv -f /etc/apt/keyrings/rizin.asc.part /etc/apt/keyrings/rizin.asc
    chmod 644 /etc/apt/keyrings/rizin.asc
    echo "deb [signed-by=/etc/apt/keyrings/rizin.asc] $repo/ /" > /etc/apt/sources.list.d/rizin.list
    IN_UPDATED=""   # the next install reads the new repository's package list
}

step_native() {
    if [ "$RUNTIME" = chroot ]; then
        say "Installing native code tools: objdump (binutils) and rizin…"
        ubuntu_install binutils
        if ! command -v rizin >/dev/null 2>&1; then
            apt-cache show rizin >/dev/null 2>&1 || add_rizin_repo
            ubuntu_install rizin
        fi
        rizin -v >/dev/null 2>&1 || die "rizin was installed but does not run"
        ok "objdump and rizin installed ($(rizin -v 2>/dev/null | head -1))"
        return 0
    fi
    say "Installing native code tools: objdump (Ubuntu binutils) and rizin (Termux)…"
    ubuntu_install binutils
    termux_install rizin
    ok "objdump and rizin installed"
}

step_adb() {
    if [ "$RUNTIME" = chroot ]; then
        say "Installing adb and fastboot (Ubuntu's packages)…"
        ubuntu_install adb fastboot
        ok "adb and fastboot installed. Connect adb to this phone in AntiGem Settings → ADB Connect."
        return 0
    fi
    say "Installing adb (Termux android-tools)…"
    termux_install android-tools
    ok "adb installed. Connect it to this phone in AntiGem Settings → ADB Connect."
}

step_hermes() {
    need_in /usr/bin/python3 base
    say "Installing hermes-dec (React Native Hermes bytecode decompiler) in a Python venv…"
    ubuntu_install python3-venv
    inside "
set -e
[ -x $T/hermes/bin/pip ] || python3 -m venv $T/hermes
$T/hermes/bin/pip install -q --upgrade hermes-dec
for f in $T/hermes/bin/hbc-*; do ln -sf \"\$f\" /usr/local/bin/; done
ls /usr/local/bin | grep hbc-
" || die "Could not install hermes-dec"
    ok "hermes-dec installed (hbc-decompiler, hbc-disassembler, hbc-file-parser)"
}

step_debug() {
    say "Installing gdb in Ubuntu…"
    ubuntu_install gdb
    ok "gdb installed"
}

step_firmware() {
    say "Installing binwalk in Ubuntu…"
    ubuntu_install binwalk
    ok "binwalk installed"
}

step_launcher() {
    say "Installing the rea-mcp launcher, rea-shell and the tool filter…"
    mkdir -p "$SHARE" || die "Cannot create $SHARE"
    as_user mkdir -p "$CONF" || die "Cannot create $CONF"
    if [ "$HERE" != "$SHARE" ]; then
        for f in files.json rea-setup.sh rea-mcp rea-shell rea-mcp-chroot rea-shell-chroot rea-filter.mjs groups.default.json; do
            [ -f "$HERE/$f" ] && cp -f "$HERE/$f" "$SHARE/$f"
        done
    fi
    if [ "$RUNTIME" = chroot ]; then
        # The chroot's own launchers: REA runs right here, no container
        for f in rea-mcp-chroot rea-shell-chroot rea-filter.mjs groups.default.json; do
            [ -f "$SHARE/$f" ] || die "$SHARE/$f is missing (get the setup files again)"
        done
        chmod 755 "$SHARE"
        chmod 644 "$SHARE"/*.json "$SHARE"/*.mjs 2>/dev/null
        install -m 755 "$SHARE/rea-mcp-chroot" "$BIN/rea-mcp" || die "Cannot write $BIN/rea-mcp"
        install -m 755 "$SHARE/rea-shell-chroot" "$BIN/rea-shell" || die "Cannot write $BIN/rea-shell"
    else
        for f in rea-mcp rea-shell rea-filter.mjs groups.default.json; do
            [ -f "$SHARE/$f" ] || die "$SHARE/$f is missing (run this script from its own folder)"
        done
        chmod 755 "$SHARE/rea-mcp" "$SHARE/rea-shell" "$SHARE/rea-setup.sh" 2>/dev/null
        ln -sf "$SHARE/rea-mcp" "$BIN/rea-mcp"
        ln -sf "$SHARE/rea-shell" "$BIN/rea-shell"
    fi
    if [ ! -f "$CONF/groups.json" ]; then
        as_user cp "$SHARE/groups.default.json" "$CONF/groups.json"
        ok "Default tool groups written to $CONF/groups.json"
    fi
    ok "rea-mcp and rea-shell installed in $BIN"
    [ -e "$ROOTFS$T/node/lib/node_modules/rea-agents" ] && { (step_tools) || say "Could not refresh the tool list now; Settings → REA → Refresh tool list retries."; }
    return 0
}

step_tools() {
    [ -x "$BIN/rea-mcp" ] || die "Needs the 'launcher' step first."
    need_in $T/node/lib/node_modules/rea-agents rea
    say "Reading REA's tool list…"
    as_user mkdir -p "$CONF"
    # in the chroot REA runs as the user, like the agents start it
    if as_user "$BIN/rea-mcp" --list-tools > "$CONF/tools.json.part"; then
        [ "$RUNTIME" = chroot ] && [ -n "$U" ] && chown "$U:$(id -gn "$U")" "$CONF/tools.json.part"
        mv "$CONF/tools.json.part" "$CONF/tools.json"
        ok "$(grep -c '"required":' "$CONF/tools.json") tools listed in $CONF/tools.json"
    else
        rm -f "$CONF/tools.json.part"
        die "Could not list REA's tools"
    fi
}

step_doctor() {
    [ -x "$BIN/rea-mcp" ] || die "Needs the 'launcher' step first."
    as_user "$BIN/rea-mcp" --doctor
    return 0
}

installed() { [ -e "$1" ] && echo yes || echo no; }
step_status() {
    echo "container=$(installed "$ROOTFS/usr/bin/apt-get")"
    echo "base=$(installed "$ROOTFS/usr/bin/curl")"
    echo "java=$(installed "$ROOTFS$JAVA_BIN")"
    echo "node=$(installed "$ROOTFS$T/node/bin/node")"
    echo "rea=$(installed "$ROOTFS$T/node/lib/node_modules/rea-agents/package.json")"
    echo "jadx=$(installed "$ROOTFS$T/$JADX_JAR")"
    echo "apktool=$(installed "$ROOTFS$T/apktool.jar")"
    echo "launcher=$(installed "$BIN/rea-mcp")"
    if [ "$RUNTIME" = chroot ]; then
        echo "native=$( [ -e /usr/bin/objdump ] && command -v rizin >/dev/null 2>&1 && echo yes || echo no)"
        echo "adb=$( [ -e /usr/bin/adb ] && [ -e /usr/bin/fastboot ] && echo yes || echo no)"
    else
        echo "native=$( [ -e "$ROOTFS/usr/bin/objdump" ] && [ -e "$P/bin/rizin" ] && echo yes || echo no)"
        echo "adb=$(installed "$P/bin/adb")"
    fi
    echo "hermes=$(installed "$ROOTFS$T/hermes/bin/hbc-decompiler")"
    echo "debug=$(installed "$ROOTFS/usr/bin/gdb")"
    echo "firmware=$(installed "$ROOTFS/usr/bin/binwalk")"
    # versions and where things are, for the app (it cannot read the chroot's files itself)
    echo "rea_version=$(sed -n 's/^ *"version": *"\([^"]*\)".*/\1/p' "$ROOTFS$T/node/lib/node_modules/rea-agents/package.json" 2>/dev/null | head -1)"
    echo "node_version=$(basename "$(readlink -f "$ROOTFS$T/node" 2>/dev/null)" 2>/dev/null | grep '^v' || true)"
    echo "os=$(grep -m1 '^PRETTY_NAME=' "$ROOTFS/etc/os-release" 2>/dev/null | cut -d'"' -f2)"
    echo "conf=$CONF"
}

step_uninstall() {
    say "Removing REA, its jars, hermes-dec and the launcher (the Ubuntu container, Java and Node stay)…"
    if has_container; then
        inside "[ -x $T/node/bin/npm ] && npm uninstall -g rea-agents; rm -rf $T/$JADX_JAR $T/apktool.jar /usr/local/bin/apktool $T/hermes /usr/local/bin/hbc-*; true"
    fi
    rm -f "$BIN/rea-mcp" "$BIN/rea-shell"
    rm -rf "$SHARE"
    if [ "$RUNTIME" = chroot ]; then
        ok "REA removed. Your tool groups stay in $CONF; Java and Node.js stay in the chroot ($T)."
    else
        ok "REA removed. Your tool groups stay in $CONF. To delete the whole container: proot-distro remove $C"
    fi
}

step_remove_container() {
    [ "$RUNTIME" = chroot ] && die "This is AntiGem's Ubuntu chroot, not a container: delete it in AntiGem Settings → Where agents run → Ubuntu chroot."
    say "Deleting the '$C' container and everything in it…"
    yes | proot-distro remove "$C" || die "proot-distro could not remove '$C'"
    rm -f "$BIN/rea-mcp" "$BIN/rea-shell"
    ok "Container '$C' deleted"
}

usage() {
    cat <<EOF
AntiGem REA setup. In AntiGem's terminal REA runs in the proot-distro container '$C' ($IMAGE); in AntiGem's
Ubuntu chroot it runs in the chroot itself (tools in /opt/antigem, launchers in /usr/local/bin).

Usage: bash rea-setup.sh STEP [STEP...]
       sudo env ANTIGEM_RUNTIME=chroot bash rea-setup.sh STEP [STEP...]   (in the Ubuntu chroot; AntiGem's Settings → REA
                                                                     does this for you)

Groups of steps
  android     container base java node rea jadx apktool native launcher (APK analysis, recommended)
  all         android + adb hermes debug firmware

Steps (each can be rerun to repair or update)
  container   proot-distro and the Ubuntu 24.04 container (in the Ubuntu chroot: nothing to install)
  base        curl, Python, git, unzip in Ubuntu (needed by node, jadx, apktool, hermes)
  java        OpenJDK 21 headless (JADX and apktool run on it)
  node        Node.js $NODE_MAJOR through nvm (REA runs on it)
  rea         REA itself (npm rea-agents); rerun to update
  jadx        jadx-headless-mcp $JADX_VERSION jar: Java/Kotlin decompiling of APKs
  apktool     latest apktool jar: manifest, resources and strings
  native      objdump (Ubuntu) and rizin (Termux's; in the chroot the rizin project's Ubuntu package) for .so libraries
  launcher    rea-mcp (the MCP server command), rea-shell and the tool filter
  adb         adb in Termux (in the chroot: Ubuntu's adb and fastboot), for REA's device tools
  hermes      hermes-dec for React Native Hermes bytecode
  debug       gdb
  firmware    binwalk

Other
  tools       refresh ~/.config/antigem/rea/tools.json (REA's tool list)
  doctor      rea doctor: which tools and engines are ready
  status      show what is installed
  uninstall   remove REA, its jars and the launcher (keeps the container)
  remove-container   delete the whole container (asks nothing: careful)
EOF
}

run_step() {
    case "$1" in
        android) for s in container base java node rea jadx apktool native launcher; do run_step "$s" || return $?; done ;;
        all) for s in container base java node rea jadx apktool native launcher adb hermes debug firmware; do run_step "$s" || return $?; done ;;
        container|base|java|node|rea|jadx|apktool|native|launcher|adb|hermes|debug|firmware|tools|doctor|status|uninstall)
            "step_$1" ;;
        remove-container) step_remove_container ;;
        help|-h|--help) usage ;;
        *) usage; die "Unknown step: $1" ;;
    esac
}

[ $# -gt 0 ] || { usage; exit 0; }
for step in "$@"; do run_step "$step" || exit $?; done

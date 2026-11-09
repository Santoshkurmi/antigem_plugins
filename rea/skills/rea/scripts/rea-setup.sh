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

P=/data/data/com.termux/files/usr
H=/data/data/com.termux/files/home
export PREFIX="$P" PATH="$P/bin:$PATH" TMPDIR="${TMPDIR:-$P/tmp}" DEBIAN_FRONTEND=noninteractive
C="${REA_CONTAINER:-ubuntu}"
IMAGE="${REA_IMAGE:-ubuntu:24.04}"
ROOTFS="$P/var/lib/proot-distro/containers/$C/rootfs"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARE="$P/share/antigem-rea"
CONF="$H/.config/antigem/rea"
NODE_MAJOR=24
NVM_VERSION=v0.40.3
JADX_VERSION=0.7.1
JADX_JAR="jadx-headless-mcp-$JADX_VERSION-all.jar"
JADX_URL="https://github.com/1013503897/jadx-headless-mcp/releases/download/v$JADX_VERSION/$JADX_JAR"
APKTOOL_FALLBACK=3.0.3
KEEP="-o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold"
JAVA_BIN=/usr/lib/jvm/java-21-openjdk-arm64/bin/java   # real file: /usr/bin/java is an absolute symlink the Termux side cannot follow
IN_PATH=/root/tools/node/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

say() { printf '==> %s\n' "$*"; }
ok() { printf '✓ %s\n' "$*"; }
die() { printf '✗ %s\n' "$*" >&2; exit 1; }

has_container() { [ -x "$ROOTFS/usr/bin/apt-get" ]; }
need_container() { has_container || die "The '$C' Ubuntu container is not installed yet. Run the 'container' step first."; }
# Runs a bash script inside the container, with a clean environment (no Termux PATH)
inside() {
    proot-distro login "$C" --shared-tmp -b "$H:/data/user/0/com.termux/files/home" -- /usr/bin/env -i HOME=/root TERM=dumb LANG=C.UTF-8 \
        DEBIAN_FRONTEND=noninteractive "PATH=$IN_PATH" /bin/bash -c "$1"
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
    # dpkg --configure -a: finishes an install that was stopped half way
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
export NVM_DIR=/root/.nvm
prev=\$(readlink -f /root/tools/node 2>/dev/null || true)
if [ ! -s \"\$NVM_DIR/nvm.sh\" ]; then
    curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/$NVM_VERSION/install.sh | bash
fi
. \"\$NVM_DIR/nvm.sh\"
nvm install $NODE_MAJOR --no-progress
nvm alias default $NODE_MAJOR >/dev/null
mkdir -p /root/tools
ln -sfnr \"\$(dirname \"\$(dirname \"\$(nvm which $NODE_MAJOR)\")\")\" /root/tools/node
echo \"node \$(/root/tools/node/bin/node -v), npm \$(/root/tools/node/bin/npm -v)\"
# A newer Node has its own global packages: bring REA along
if [ -n \"\$prev\" ] && [ -d \"\$prev/lib/node_modules/rea-agents\" ] && [ ! -d /root/tools/node/lib/node_modules/rea-agents ]; then
    echo 'Reinstalling REA for the new Node…'
    npm install -g rea-agents@latest --no-fund --no-audit
fi
" || die "Node.js install failed"
    ok "Node.js installed"
}

step_rea() {
    need_in /root/tools/node/bin/node node
    say "Installing REA (npm rea-agents)…"
    inside "npm install -g rea-agents@latest --no-fund --no-audit && echo \"REA \$(rea --version)\"" || die "npm could not install rea-agents"
    ok "REA installed"
    [ -x "$P/bin/rea-mcp" ] && { (step_tools) || say "Could not refresh the tool list now; Settings → REA → Refresh tool list retries."; }
    return 0
}

step_jadx() {
    need_in /usr/bin/curl base
    say "Downloading jadx-headless-mcp $JADX_VERSION (JADX bridge REA uses)…"
    inside "set -e; mkdir -p /root/tools; curl -fL --retry 3 -o /root/tools/$JADX_JAR.part '$JADX_URL'; mv /root/tools/$JADX_JAR.part /root/tools/$JADX_JAR; ls -la /root/tools/$JADX_JAR" \
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
mkdir -p /root/tools
curl -fL --retry 3 -o /root/tools/apktool.jar.part \"https://github.com/iBotPeaches/Apktool/releases/download/v\$v/apktool_\$v.jar\"
mv /root/tools/apktool.jar.part /root/tools/apktool.jar
printf '#!/bin/sh\nexec java -jar /root/tools/apktool.jar \"\$@\"\n' > /usr/local/bin/apktool
chmod 755 /usr/local/bin/apktool
" || die "Could not install apktool"
    [ -e "$ROOTFS$JAVA_BIN" ] || say "Note: apktool also needs the 'java' step."
    ok "apktool installed"
}

step_native() {
    say "Installing native code tools: objdump (Ubuntu binutils) and rizin (Termux)…"
    ubuntu_install binutils
    termux_install rizin
    ok "objdump and rizin installed"
}

step_adb() {
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
[ -x /root/tools/hermes/bin/pip ] || python3 -m venv /root/tools/hermes
/root/tools/hermes/bin/pip install -q --upgrade hermes-dec
for f in /root/tools/hermes/bin/hbc-*; do ln -sf \"\$f\" /usr/local/bin/; done
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
    mkdir -p "$SHARE" "$CONF" || die "Cannot create $SHARE"
    if [ "$HERE" != "$SHARE" ]; then
        for f in files.json rea-setup.sh rea-mcp rea-shell rea-filter.mjs groups.default.json; do
            [ -f "$HERE/$f" ] && cp -f "$HERE/$f" "$SHARE/$f"
        done
    fi
    for f in rea-mcp rea-shell rea-filter.mjs groups.default.json; do
        [ -f "$SHARE/$f" ] || die "$SHARE/$f is missing (run this script from its own folder)"
    done
    chmod 755 "$SHARE/rea-mcp" "$SHARE/rea-shell" "$SHARE/rea-setup.sh" 2>/dev/null
    ln -sf "$SHARE/rea-mcp" "$P/bin/rea-mcp"
    ln -sf "$SHARE/rea-shell" "$P/bin/rea-shell"
    if [ ! -f "$CONF/groups.json" ]; then
        cp "$SHARE/groups.default.json" "$CONF/groups.json"
        ok "Default tool groups written to $CONF/groups.json"
    fi
    ok "rea-mcp and rea-shell installed in $P/bin"
    [ -e "$ROOTFS/root/tools/node/lib/node_modules/rea-agents" ] && { (step_tools) || say "Could not refresh the tool list now; Settings → REA → Refresh tool list retries."; }
    return 0
}

step_tools() {
    [ -x "$P/bin/rea-mcp" ] || die "Needs the 'launcher' step first."
    need_in /root/tools/node/lib/node_modules/rea-agents rea
    say "Reading REA's tool list…"
    mkdir -p "$CONF"
    if "$P/bin/rea-mcp" --list-tools > "$CONF/tools.json.part"; then
        mv "$CONF/tools.json.part" "$CONF/tools.json"
        ok "$(grep -c '"required":' "$CONF/tools.json") tools listed in $CONF/tools.json"
    else
        rm -f "$CONF/tools.json.part"
        die "Could not list REA's tools"
    fi
}

step_doctor() {
    [ -x "$P/bin/rea-mcp" ] || die "Needs the 'launcher' step first."
    "$P/bin/rea-mcp" --doctor
    return 0
}

installed() { [ -e "$1" ] && echo yes || echo no; }
step_status() {
    echo "container=$(installed "$ROOTFS/usr/bin/apt-get")"
    echo "base=$(installed "$ROOTFS/usr/bin/curl")"
    echo "java=$(installed "$ROOTFS$JAVA_BIN")"
    echo "node=$(installed "$ROOTFS/root/tools/node/bin/node")"
    echo "rea=$(installed "$ROOTFS/root/tools/node/lib/node_modules/rea-agents/package.json")"
    echo "jadx=$(installed "$ROOTFS/root/tools/$JADX_JAR")"
    echo "apktool=$(installed "$ROOTFS/root/tools/apktool.jar")"
    echo "launcher=$(installed "$P/bin/rea-mcp")"
    echo "native=$( [ -e "$ROOTFS/usr/bin/objdump" ] && [ -e "$P/bin/rizin" ] && echo yes || echo no)"
    echo "adb=$(installed "$P/bin/adb")"
    echo "hermes=$(installed "$ROOTFS/root/tools/hermes/bin/hbc-decompiler")"
    echo "debug=$(installed "$ROOTFS/usr/bin/gdb")"
    echo "firmware=$(installed "$ROOTFS/usr/bin/binwalk")"
}

step_uninstall() {
    say "Removing REA, its jars, hermes-dec and the launcher (the Ubuntu container, Java and Node stay)…"
    if has_container; then
        inside "[ -x /root/tools/node/bin/npm ] && npm uninstall -g rea-agents; rm -rf /root/tools/$JADX_JAR /root/tools/apktool.jar /usr/local/bin/apktool /root/tools/hermes /usr/local/bin/hbc-*; true"
    fi
    rm -f "$P/bin/rea-mcp" "$P/bin/rea-shell"
    rm -rf "$SHARE"
    ok "REA removed. Your tool groups stay in $CONF. To delete the whole container: proot-distro remove $C"
}

step_remove_container() {
    say "Deleting the '$C' container and everything in it…"
    yes | proot-distro remove "$C" || die "proot-distro could not remove '$C'"
    rm -f "$P/bin/rea-mcp" "$P/bin/rea-shell"
    ok "Container '$C' deleted"
}

usage() {
    cat <<EOF
AntiGem REA setup: REA runs in the proot-distro container '$C' ($IMAGE).

Usage: bash rea-setup.sh STEP [STEP...]

Groups of steps
  android     container base java node rea jadx apktool native launcher (APK analysis, recommended)
  all         android + adb hermes debug firmware

Steps (each can be rerun to repair or update)
  container   proot-distro and the Ubuntu 24.04 container
  base        curl, Python, git, unzip in Ubuntu (needed by node, jadx, apktool, hermes)
  java        OpenJDK 21 headless (JADX and apktool run on it)
  node        Node.js $NODE_MAJOR through nvm (REA runs on it)
  rea         REA itself (npm rea-agents); rerun to update
  jadx        jadx-headless-mcp $JADX_VERSION jar: Java/Kotlin decompiling of APKs
  apktool     latest apktool jar: manifest, resources and strings
  native      objdump (Ubuntu) and rizin (Termux) for .so libraries
  launcher    rea-mcp (the MCP server command), rea-shell and the tool filter
  adb         adb in Termux, for REA's device tools
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

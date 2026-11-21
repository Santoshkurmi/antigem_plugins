# Setting up REA

REA runs in a proot-distro Ubuntu 24.04 container named `ubuntu` inside AntiGem's terminal (com.termux builds).
The easy way is **Settings → REA · Reverse Engineering** in the app: it installs the same steps below with
buttons, one part at a time or several together, and adds the MCP server. Suggest that first.

If the user prefers, install from the terminal. **Ask before installing**: the APK-analysis set needs about 1 GB
and takes 5–15 minutes depending on the network. Run long steps one at a time so a failure is easy to see.

## In AntiGem's Ubuntu chroot (rooted phones)

When the phone runs AntiGem's Ubuntu chroot, you are in a normal Ubuntu (no `$PREFIX`, no proot) and REA installs
right into it: no container. The same script runs as root with `ANTIGEM_RUNTIME=chroot`; Settings → REA does this
for the user, and copies the scripts to `/opt/antigem/share/antigem-rea`. From the terminal (it needs root, so ask
the user first):

```sh
sudo env ANTIGEM_RUNTIME=chroot bash /opt/antigem/share/antigem-rea/rea-setup.sh android
```

Where things are there: tools in `/opt/antigem/tools` (Node.js, the JADX and apktool jars, hermes-dec), the
commands `rea-mcp`, `rea-shell` and `apktool` in `/usr/local/bin`, the tool groups in the user's own
`~/.config/antigem/rea/groups.json`. The `container` step does nothing there; `native` installs objdump and rizin
(rizin from the rizin project's own Ubuntu repository: Ubuntu has no package), `adb` installs Ubuntu's adb and
fastboot (they work without sudo). The MCP server command is `/usr/local/bin/rea-mcp`. Everything below about
`$PREFIX` and proot-distro is for AntiGem's terminal (Termux) only.

## The setup script

The script ships with this skill: `scripts/rea-setup.sh` in this skill's detail folder (`get_skill` returns
`detail_dir`; the full path is `<detail_dir>/scripts/rea-setup.sh`). If that folder is not reachable from the
terminal, download the scripts:

```sh
mkdir -p $PREFIX/share/antigem-rea && cd $PREFIX/share/antigem-rea
for f in files.json rea-setup.sh rea-mcp rea-shell rea-filter.mjs groups.default.json; do
  curl -fsSLO https://raw.githubusercontent.com/Santoshkurmi/antigem_plugins/main/rea/skills/rea/scripts/$f
done
```

Then `bash <folder>/rea-setup.sh help` lists every step. Steps can be given together and each can be run again
to repair or update it.

| Step | Installs | Needed for |
| --- | --- | --- |
| `container` | proot-distro (Termux) and the Ubuntu 24.04 container (≈30 MB download) | everything |
| `base` | curl, Python, git, unzip, procps in Ubuntu | node, jadx, apktool, hermes |
| `java` | OpenJDK 21 headless | JADX, apktool |
| `node` | Node.js 24 through nvm (not Ubuntu's apt Node, which is too old) | REA |
| `rea` | REA (`npm i -g rea-agents`); rerun to update | everything |
| `jadx` | jadx-headless-mcp 0.7.1 jar | Java/Kotlin decompiling |
| `apktool` | latest official apktool jar (Ubuntu's 2.7 is old and has known bugs) | resources, manifest |
| `native` | objdump (Ubuntu binutils) + rizin (Termux) | .so libraries |
| `launcher` | `rea-mcp`, `rea-shell`, the tool filter, default tool groups | the MCP server |
| `adb` | Termux android-tools | REA's phone tools |
| `hermes` | hermes-dec in a Python venv (`hbc-decompiler`…) | React Native Hermes |
| `debug` | gdb | debugging |
| `firmware` | binwalk | firmware images |

Shortcuts: `android` = container base java node rea jadx apktool native launcher (recommended);
`all` = android + adb hermes debug firmware.

Recommended sequence (check each step's last line: `✓` is success, `✗` names the problem):

```sh
S=<folder with rea-setup.sh>
bash $S/rea-setup.sh container base
bash $S/rea-setup.sh java node
bash $S/rea-setup.sh rea jadx apktool native launcher
bash $S/rea-setup.sh status          # every needed line should say yes
rea-mcp --doctor                     # engines REA can use
```

Optional: `bash $S/rea-setup.sh hermes` for React Native apps, `adb` for the phone tools.

## After installing

The MCP server still has to be added to the agent: tell the user to use the **REA** preset in that agent's MCP
settings (Antigravity → MCP Servers, Claude Code → MCP, OpenCode → MCP servers); it asks for the mode and the tool
groups. By hand: `mcp.md`. A new chat (or refreshing the
server) is needed before the tools appear.

## Other commands

- `bash $S/rea-setup.sh rea`: update REA. `bash $S/rea-setup.sh tools`: refresh the tool list after an update.
- `rea-shell`: a shell inside the container with REA's tools on PATH; `rea-shell '<command>'` runs one command
  in the current folder (for example `rea-shell 'apktool d app.apk -o out'`).
- `bash $S/rea-setup.sh uninstall`: remove REA, its jars and the launcher (the container stays).
- `bash $S/rea-setup.sh remove-container`: delete the whole container. Only with the user's explicit OK: it
  removes everything else installed in it too.

## Notes

- The container is a normal proot-distro container: `proot-distro login ubuntu` opens it, and the user can
  install other software in it.
- Proot is slower than native Linux: JADX opens a large APK in 15–60 s, and the first call of a session is the
  slowest.
- If `apt` reports a lock, another install is running (maybe in the app). Wait for it; never delete lock files.

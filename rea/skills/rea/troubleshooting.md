# Troubleshooting REA

| Symptom | Cause and fix |
| --- | --- |
| No REA tools at all | Server not added or not started. Settings → REA → Add to Antigravity; restart the server; new chat. Check `command -v rea-mcp`. |
| Server shows Error / "Not started" | Run `rea-mcp --doctor` in the terminal and read its error. Common: REA or Node missing (install the `node` and `rea` parts), container missing (`container`). |
| `rea-mcp: the 'ubuntu' container is not installed` | Install the Ubuntu container part (Settings → REA) or `rea-setup.sh container`. |
| "not in this server's tool groups" / "not available on this server" | Tool hidden by groups: add its group to the server or the tool to a group (`mcp.md`), then restart the server. |
| "changes things: run it with rea_call_change" | On-demand server: that tool is marked ✎; call it with `rea_call_change` (and the reverse message for `rea_call`). |
| JADX: Java missing / "jdk.compiler" | Install the Java 21 part (`rea-setup.sh java`). |
| JADX: JAR not configured | Install the JADX part (`rea-setup.sh jadx`). |
| JADX slow or out of memory on a huge APK | Normal in proot for the first call (up to a minute). Analyze `base.apk` only; close other apps. |
| apktool decode fails | Reinstall the apktool part (latest jar). Split APKs: decode `base.apk`. |
| objdump / rizin "Could not launch" | Install the Native code tools part (`rea-setup.sh native`). |
| adb tools: no devices / unauthorized | `device.md`: install adb, pair in Settings → ADB Connect, tap Allow on the phone. |
| `hbc-decompiler: command not found` | Install React Native (hermes-dec) (`rea-setup.sh hermes`); run it through `rea-shell`. |
| A path "does not exist" | Use absolute Termux paths (`/data/data/com.termux/files/home/...`) or exact `/data/app/...` paths from `pm path`; `/sdcard` may need storage permission: copy files into the home. |
| `apt` lock / dpkg interrupted | Another install is running, or one was stopped. Wait; then rerun the same step (it finishes interrupted installs). |
| Tool list in Settings is old after an update | Settings → REA → Refresh tool list (or `rea-setup.sh tools`). |
| Answers are slow or the agent forgets things | Too many tools offered directly: switch the server to On demand, or choose fewer groups (the dialog shows the tokens each choice costs). |

Logs: run the failing step again in the terminal (`bash <setup>/rea-setup.sh <step>`), which prints every command
and error. `rea-mcp --doctor` shows REA's own view of every engine.

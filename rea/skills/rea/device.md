# REA's phone tools (adb, group `device`)

REA's adb tools work on this phone once the terminal's adb is connected to it:

1. `adb` installed: Settings → REA → adb (or `bash <setup>/rea-setup.sh adb`).
2. Connected: Settings → ADB Connect pairs the terminal's adb with this phone over Wireless debugging (once).
   Check with `adb devices`: a line like `127.0.0.1:<port>  device`. `unauthorized` means the user must tap
   Allow on the phone's USB-debugging prompt; `offline` or nothing means pair again in ADB Connect.

Without adb, installed apps are still readable: `pm path <package>` (see `android.md`).

## Tools

The device `serial` comes from `list_adb_devices` (for this phone usually `127.0.0.1:<port>`).

| Tool | Use |
| --- | --- |
| `list_adb_devices`, `inspect_adb_device` | devices and build identity |
| `resolve_adb_packages {serial, query}` | find a package by part of its name |
| `list_adb_packages {serial, scope}` | installed packages (`third_party`, `system`, `all`) with APK paths |
| `inspect_adb_package {serial, package}` | version, installer, flags (dumpsys) |
| `pull_adb_package {serial, package, output_directory}` | copy base + all splits into `<output_directory>/<package>/` (must not exist yet) |
| `read_adb_logcat {serial}` | recent logs (filter for the app's tag or process) |
| `capture_adb_screen {serial, output_directory}` | screenshot PNG |
| `list_adb_processes`, `start_adb_app`, `stop_adb_app`, `start_adb_activity` | processes; start/stop the app or an activity |
| `install_adb_package`, `uninstall_adb_package`, `push_adb_file` | change the phone: only when the user asks |

Use a folder in the Termux home as `output_directory` (for example `~/re/pulled`).

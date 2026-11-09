# The REA MCP server and tool groups

## How it is wired

Agents start `/data/data/com.termux/files/usr/bin/rea-mcp` (stdio). It logs into the `ubuntu` container with a
clean environment and runs `rea mcp` behind a small filter (`rea-filter.mjs`) that shows only the tools of the
chosen **tool groups**. Settings of the server, in its `env`:

| Variable | Meaning |
| --- | --- |
| `REA_MODE` | `lazy` (on demand): four gateway tools, ≈0.7k tokens per request whatever is allowed. `direct`: every allowed tool is an MCP tool |
| `REA_GROUPS` | Which tools the agent may use: comma separated group ids, e.g. `core,android,flutter,device,native`; `all` allows every tool |
| `REA_DIRECT_GROUPS` | With `REA_MODE=lazy`: groups whose tools are also offered directly (each adds its size) |
| `REA_MCP_OUTPUT_SCHEMA_PROFILE` | `off` (default) or `full`. Full output schemas make the tool list ~12× bigger |
| `REA_CONTAINER` | Container name, default `ubuntu` |

What it costs per request (REA 6.8.0, output schemas off):

| Setup | Context per request |
| --- | --- |
| On demand (`REA_MODE=lazy`), any groups | ≈0.7k tokens (+ ≈1.6k once when the agent calls `rea_tools`) |
| On demand + `core` offered directly | ≈9.6k |
| Directly, groups core,android,flutter,device,native (61 tools) | ≈24k |
| Directly, all 229 tools | ≈75k (≈900k with full output schemas) |

On demand is the default for servers added in AntiGem. Directly saves the lookup step for small sets.

## Tool groups

Stored in `~/.config/antigem/rea/groups.json` (edited in Settings → REA → Tool groups):

```json
{ "version": 1, "groups": [
  { "id": "android", "name": "Android apps", "description": "…", "builtin": true, "tools": ["inspect_android_package", "…"] }
] }
```

Built-in ids: `core` (basics, session status, evidence), `android` (JADX, apktool, signatures), `flutter`,
`device` (adb), `native` (objdump, rizin, ELF/exports), `javascript` (JS bundles), `unity` (IL2CPP),
`debug` (gdb, rizin debugger), `frida`, `firmware`, `network` (pcap), `apple` (iOS/macOS), `windows` (PE, .NET),
`decompiler` (needs Ghidra/IDA/Hopper/Kuna, which AntiGem does not install; leave it off).

`~/.config/antigem/rea/tools.json` lists every tool REA has, with a short description and its size.

When a call fails with "not in this server's tool groups" or "not available on this server", the tool is hidden. Tell the user to add its group to
the server (the REA preset in that agent's MCP settings), or the tool to a group (Settings → REA → Tool
groups). If the user asks you to do it, edit `groups.json` (keep valid JSON, ids unchanged) and ask them to
restart the server: changes apply on restart only.

## Adding the server

- **In AntiGem, for any agent**: the **REA** preset in that agent's MCP settings (Antigravity → MCP Servers,
  Claude Code → MCP, OpenCode → MCP servers). It asks for the mode and the tool groups and writes the agent's
  config; nothing has to be typed. The same agent can have several REA servers with different groups.
- **By hand** (any agent, or outside AntiGem): a stdio server with the command
  `/data/data/com.termux/files/usr/bin/rea-mcp` and the env above. Examples:
  - Antigravity (`~/.gemini/config/mcp_config.json`, under `mcpServers`):

    ```json
    "rea": { "command": "/data/data/com.termux/files/usr/bin/rea-mcp", "env": { "REA_MODE": "lazy", "REA_GROUPS": "all" } }
    ```

  - Claude Code (in the terminal):

    ```sh
    claude mcp add rea -e REA_MODE=lazy -e REA_GROUPS=all -- /data/data/com.termux/files/usr/bin/rea-mcp
    ```

  - OpenCode (`~/.config/opencode/opencode.json`):

    ```json
    { "mcp": { "rea": { "type": "local", "command": ["/data/data/com.termux/files/usr/bin/rea-mcp"],
        "environment": { "REA_MODE": "lazy", "REA_GROUPS": "all" }, "enabled": true } } }
    ```

After adding or changing the server, the agent needs a restart of the server or a new session to see the tools.

## Checking it by hand

```sh
command -v rea-mcp                 # the launcher is installed
rea-mcp --doctor                   # REA starts; which engines are ready
rea-mcp --list-tools | head -40    # REA's tools (all of them, ignoring groups)
cat ~/.config/antigem/rea/groups.json | head -40
```

`rea-mcp --doctor` reporting `unsupported_host` or `missing_analysis_engine` for Hopper, IDA, Ghidra or Kuna is
normal: those engines are not part of the setup.

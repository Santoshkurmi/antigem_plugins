#!/usr/bin/env node
// AntiGem · REA tool filter. Starts `rea mcp` and passes the MCP stdio through, limiting what the agent sees.
//
// Which tools the agent may use: REA_GROUPS, comma separated group ids from REA_GROUPS_FILE (edited in AntiGem's
// Settings → REA → Tool groups); empty or "all" allows every tool.
//
// How the agent sees them: REA_MODE
//   direct (default)  every allowed tool is advertised as itself. Fast, but every tool definition costs context on
//                     every request.
//   lazy              only four small gateway tools are advertised (rea_tools, rea_tool_info, rea_call,
//                     rea_call_change); the agent lists tools by name, reads the ones it needs and runs them
//                     through rea_call. REA_DIRECT_GROUPS names groups whose tools are also advertised directly.
//
//   node rea-filter.mjs               MCP server over stdio (what agents run, through rea-mcp)
//   node rea-filter.mjs --list-tools  print every REA tool (name, title, short description, required inputs, whether
//                                     it changes things, and the bytes its definition adds to the context) as JSON
//   node rea-filter.mjs --doctor      run `rea doctor`
//
// Source: antigem_plugins/rea/skills/rea/scripts/. AntiGem's Settings → REA downloads this folder into
// $PREFIX/share/antigem-rea/; the REA skill plugin carries the same files.
import { spawn } from "node:child_process";
import { readFileSync } from "node:fs";
import { createInterface } from "node:readline";

const GROUPS_FILE = process.env.REA_GROUPS_FILE || "/data/data/com.termux/files/home/.config/antigem/rea/groups.json";
const MODE = (process.env.REA_MODE || "direct").trim().toLowerCase() === "lazy" ? "lazy" : "direct";
const GATEWAYS = new Set(["rea_tools", "rea_tool_info", "rea_call", "rea_call_change"]);
const CHANGE_MARK = "✎";

// ---------------- groups ----------------

const idList = (value) => (value || "").split(",").map((s) => s.trim()).filter(Boolean);

function loadGroups() {
  try {
    return JSON.parse(readFileSync(GROUPS_FILE, "utf8")).groups ?? [];
  } catch (e) {
    process.stderr.write(`rea-filter: cannot read ${GROUPS_FILE} (${e.message})\n`);
    return [];
  }
}

/** Tool names of the given group ids (unknown ids are reported on stderr). */
function toolsOfGroups(groups, ids) {
  const names = new Set();
  for (const id of ids) {
    const group = groups.find((g) => g.id === id);
    if (!group) process.stderr.write(`rea-filter: unknown tool group "${id}"\n`);
    else for (const tool of group.tools ?? []) names.add(tool);
  }
  return names;
}

const changesThings = (tool) => tool.annotations?.destructiveHint === true;

// ---------------- gateway tools (lazy mode) ----------------

function gatewayDefinitions(groupIds) {
  const groups = groupIds.length > 0 ? ` Groups: ${groupIds.join(", ")}.` : "";
  const callSchema = {
    type: "object",
    properties: {
      name: { type: "string", description: "The REA tool's name, from rea_tools" },
      arguments: { type: "object", description: "The tool's arguments, as rea_tool_info describes them" }
    },
    required: ["name"]
  };
  return [
    {
      name: "rea_tools",
      title: "List REA tools",
      description:
        "Start here. Lists the REA reverse-engineering tools this server offers (Android APK decompiling with JADX, " +
        "resources with apktool, Flutter, React Native, native code with objdump/rizin, adb…), by group and by name " +
        `only, with REA's usage notes. Give a group to see its tools with one line each, or a query to search them.${groups} ` +
        "Then read a tool's arguments with rea_tool_info and run it with rea_call.",
      inputSchema: {
        type: "object",
        properties: {
          group: { type: "string", description: "A group id: its tools with a one-line description each" },
          query: { type: "string", description: "Words to find in tool names and descriptions, e.g. \"apk manifest\"" }
        }
      },
      annotations: { readOnlyHint: true, openWorldHint: false }
    },
    {
      name: "rea_tool_info",
      title: "Describe REA tools",
      description: "Full description and argument schema of up to 10 REA tools (names from rea_tools), and whether to run each with rea_call or rea_call_change.",
      inputSchema: {
        type: "object",
        properties: { names: { type: "array", items: { type: "string" }, minItems: 1, maxItems: 10, description: "Tool names" } },
        required: ["names"]
      },
      annotations: { readOnlyHint: true, openWorldHint: false }
    },
    {
      name: "rea_call",
      title: "Run an REA tool",
      description: `Run one REA tool that does not change anything (most of them: reading APKs, decompiling, listing). Tools marked ${CHANGE_MARK} in rea_tools change things: run those with rea_call_change.`,
      inputSchema: callSchema,
      annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: true }
    },
    {
      name: "rea_call_change",
      title: "Run an REA tool that changes things",
      description: `Run one REA tool marked ${CHANGE_MARK} in rea_tools: it changes the phone, a device or a session (installing or uninstalling apps, pushing files, debugger and Frida commands…). Same arguments as rea_call.`,
      inputSchema: callSchema,
      annotations: { readOnlyHint: false, destructiveHint: true, openWorldHint: true }
    }
  ];
}

const LAZY_INSTRUCTIONS =
  "REA's reverse-engineering tools are offered on demand: call rea_tools to list them (or rea_tools {query} to search), " +
  "rea_tool_info for a tool's arguments, then rea_call to run it (rea_call_change for tools marked " + CHANGE_MARK + "). " +
  "Prefer detail: \"summary\" where a tool offers it.";

/** First sentence (at most 300 characters) of a tool description. */
function shorten(text = "") {
  const flat = text.replace(/\s+/g, " ").trim();
  const sentence = flat.match(/^.{1,300}?[.!?](?=\s|$)/);
  return (sentence ? sentence[0] : flat.slice(0, 300)).trim();
}

const mark = (tool) => (changesThings(tool) ? `${tool.name} ${CHANGE_MARK}` : tool.name);
const oneLine = (tool) => {
  const needs = tool.inputSchema?.required?.length ? ` (needs ${tool.inputSchema.required.join(", ")})` : "";
  return `- ${mark(tool)}: ${shorten(tool.description)}${needs}`;
};

function listText(tools, groups, direct, reaInstructions, args) {
  const byName = new Map(tools.map((t) => [t.name, t]));
  const footer = `\n${CHANGE_MARK} = changes things: run with rea_call_change. Everything else: rea_call. Arguments: rea_tool_info {names: [...]}.`;
  const query = typeof args.query === "string" ? args.query.trim().toLowerCase() : "";
  if (query) {
    const words = query.split(/\s+/);
    const hits = tools.filter((t) => {
      const hay = `${t.name} ${t.title ?? ""} ${t.description ?? ""}`.toLowerCase().replace(/_/g, " ");
      return words.every((w) => hay.includes(w.replace(/_/g, " ")));
    });
    if (hits.length === 0) return `No REA tool on this server matches "${args.query}". Try other words, or rea_tools with no arguments.`;
    return `REA tools matching "${args.query}" (${hits.length}${hits.length > 40 ? ", first 40" : ""}):\n` + hits.slice(0, 40).map(oneLine).join("\n") + footer;
  }
  if (typeof args.group === "string" && args.group.trim()) {
    const group = groups.find((g) => g.id === args.group.trim());
    const members = group ? (group.tools ?? []).map((n) => byName.get(n)).filter(Boolean) : [];
    if (!group || members.length === 0) {
      const ids = groups.filter((g) => (g.tools ?? []).some((n) => byName.has(n))).map((g) => g.id);
      return `No group "${args.group}" on this server. Groups: ${ids.join(", ")}.`;
    }
    return `${group.name} (${group.id}, ${members.length} tools)${group.description ? `: ${group.description}` : ""}\n` + members.map(oneLine).join("\n") + footer;
  }
  const lines = [`${tools.length} REA tools on this server, by group (names only; rea_tools {group} or {query} for descriptions):`];
  const grouped = new Set();
  for (const group of groups) {
    const members = (group.tools ?? []).map((n) => byName.get(n)).filter(Boolean);
    if (members.length === 0) continue;
    members.forEach((t) => grouped.add(t.name));
    lines.push(`[${group.id}] ${group.name}: ${members.map(mark).join(", ")}`);
  }
  const rest = tools.filter((t) => !grouped.has(t.name));
  if (rest.length) lines.push(`[other] In no group: ${rest.map(mark).join(", ")}`);
  if (direct.size > 0) lines.push(`Also offered directly as their own tools: ${[...direct].filter((n) => byName.has(n)).join(", ")}.`);
  lines.push(footer.trim());
  if (reaInstructions) lines.push(`\nREA's usage notes:\n${reaInstructions}`);
  return lines.join("\n");
}

function infoText(tools, args) {
  const names = Array.isArray(args.names) ? args.names : typeof args.names === "string" ? [args.names] : [];
  if (names.length === 0) return "Give names: rea_tool_info {names: [\"inspect_android_package\"]}.";
  const byName = new Map(tools.map((t) => [t.name, t]));
  return names.slice(0, 10).map((name) => {
    const tool = byName.get(name);
    if (!tool) return `## ${name}\nNot available on this server (not in its tool groups, or no such REA tool). See rea_tools.`;
    return [
      `## ${tool.name}${tool.title ? ` (${tool.title})` : ""}`,
      `Run with: ${changesThings(tool) ? "rea_call_change" : "rea_call"} {name: "${tool.name}", arguments: {...}}`,
      (tool.description ?? "").trim(),
      `Arguments (JSON Schema): ${JSON.stringify(tool.inputSchema ?? { type: "object" })}`
    ].join("\n");
  }).join("\n\n");
}

// ---------------- server ----------------

function startRea(args) {
  const child = spawn("rea", args, { stdio: ["pipe", "pipe", "inherit"] });
  child.on("error", (e) => {
    process.stderr.write(`rea-filter: cannot start rea (${e.message}). Install REA in AntiGem Settings → REA.\n`);
    process.exit(127);
  });
  return child;
}

function serve() {
  const groups = loadGroups();
  const wanted = idList(process.env.REA_GROUPS);
  const scope = wanted.length === 0 || wanted.includes("all") ? null : toolsOfGroups(groups, wanted);
  const allowed = (name) => scope === null || scope.has(name);
  const direct = MODE === "lazy" ? new Set([...toolsOfGroups(groups, idList(process.env.REA_DIRECT_GROUPS))].filter(allowed)) : new Set();
  const label = process.env.REA_GROUPS || "all";
  const groupIds = groups.filter((g) => (g.tools ?? []).some(allowed)).map((g) => g.id);

  const child = startRea(["mcp"]);
  const toChild = (message) => child.stdin.write(JSON.stringify(message) + "\n");
  const toClient = (message) => process.stdout.write(JSON.stringify(message) + "\n");
  const toolError = (id, text) => toClient({ jsonrpc: "2.0", id, result: { content: [{ type: "text", text }], isError: true } });

  const pending = new Map(); // client request id → method whose response we change
  const internal = new Map(); // our own requests to REA
  let nextInternal = 1;
  let catalog = null; // Promise of REA's allowed tools
  let reaInstructions = "";

  const askRea = (method, params) => new Promise((resolve, reject) => {
    const id = `__rea_filter_${nextInternal++}`;
    internal.set(id, { resolve, reject });
    toChild({ jsonrpc: "2.0", id, method, params });
  });
  const loadCatalog = () => {
    if (!catalog) {
      catalog = (async () => {
        const tools = [];
        let cursor;
        do {
          const page = await askRea("tools/list", cursor ? { cursor } : {});
          tools.push(...(page.tools ?? []));
          cursor = page.nextCursor;
        } while (cursor);
        return tools.filter((t) => allowed(t.name));
      })();
      catalog.catch(() => { catalog = null; });
    }
    return catalog;
  };

  async function lazyList(message) {
    try {
      const tools = await loadCatalog();
      toClient({ jsonrpc: "2.0", id: message.id, result: { tools: [...gatewayDefinitions(groupIds), ...tools.filter((t) => direct.has(t.name))] } });
    } catch (e) {
      toClient({ jsonrpc: "2.0", id: message.id, error: { code: -32603, message: `REA did not list its tools: ${e.message}` } });
    }
  }

  async function gateway(message) {
    const name = message.params?.name;
    const args = message.params?.arguments ?? {};
    try {
      const tools = await loadCatalog();
      if (name === "rea_call" || name === "rea_call_change") {
        const target = args.name;
        if (typeof target !== "string" || !target) return toolError(message.id, `Give the REA tool's name: ${name} {name: "...", arguments: {...}}.`);
        const tool = tools.find((t) => t.name === target);
        if (!tool) {
          return toolError(message.id, `REA tool ${target} is not available on this server (${label}). ` +
            "It may be outside this server's tool groups: AntiGem Settings → REA → Tool groups, or choose more groups for the server. See rea_tools.");
        }
        if (name === "rea_call" && changesThings(tool)) return toolError(message.id, `${target} changes things: run it with rea_call_change.`);
        if (name === "rea_call_change" && !changesThings(tool)) return toolError(message.id, `${target} does not change anything: run it with rea_call.`);
        // Same request id: REA's answer goes straight back to the agent
        return toChild({ ...message, params: { ...message.params, name: target, arguments: args.arguments ?? {} } });
      }
      const text = name === "rea_tools" ? listText(tools, groups, direct, reaInstructions, args) : infoText(tools, args);
      toClient({ jsonrpc: "2.0", id: message.id, result: { content: [{ type: "text", text }] } });
    } catch (e) {
      toolError(message.id, `REA did not answer: ${e.message}`);
    }
  }

  createInterface({ input: process.stdin, crlfDelay: Infinity })
    .on("line", (line) => {
      let message = null;
      try { message = JSON.parse(line); } catch { /* not JSON: pass it on */ }
      if (!message || Array.isArray(message) || message.id === undefined || typeof message.method !== "string") {
        child.stdin.write(line + "\n");
        return;
      }
      if (message.method === "initialize") pending.set(message.id, "initialize");
      if (message.method === "tools/list") {
        if (MODE === "lazy") return void lazyList(message);
        if (scope !== null) pending.set(message.id, "tools/list");
      }
      if (message.method === "tools/call") {
        const name = message.params?.name;
        if (MODE === "lazy" && GATEWAYS.has(name)) return void gateway(message);
        if (!allowed(name)) {
          return toolError(message.id, `REA tool ${name} is not in this server's tool groups (${label}). ` +
            "Add it to a group in AntiGem Settings → REA → Tool groups, or choose more groups for this MCP server, then restart the server.");
        }
      }
      child.stdin.write(line + "\n");
    })
    .on("close", () => child.stdin.end());

  createInterface({ input: child.stdout, crlfDelay: Infinity }).on("line", (line) => {
    if (pending.size === 0 && internal.size === 0 && !line.includes("list_changed")) {
      process.stdout.write(line + "\n");
      return;
    }
    let message = null;
    try { message = JSON.parse(line); } catch { /* not JSON: pass it on */ }
    if (message && typeof message.id === "string" && internal.has(message.id)) {
      const waiter = internal.get(message.id);
      internal.delete(message.id);
      if (message.error) waiter.reject(new Error(message.error.message));
      else waiter.resolve(message.result ?? {});
      return;
    }
    if (message?.method === "notifications/tools/list_changed") catalog = null;
    if (message && pending.has(message.id)) {
      const kind = pending.get(message.id);
      pending.delete(message.id);
      if (kind === "initialize" && message.result) {
        reaInstructions = message.result.instructions ?? "";
        if (MODE === "lazy") message.result.instructions = LAZY_INSTRUCTIONS;
      }
      if (kind === "tools/list" && Array.isArray(message.result?.tools)) {
        message.result.tools = message.result.tools.filter((t) => allowed(t.name));
      }
      line = JSON.stringify(message);
    }
    process.stdout.write(line + "\n");
  });

  child.on("exit", (code, signal) => process.exit(code ?? (signal ? 1 : 0)));
  for (const signal of ["SIGTERM", "SIGINT", "SIGHUP"]) process.on(signal, () => child.kill(signal));
}

function doctor() {
  const child = spawn("rea", ["doctor", ...process.argv.slice(3)], { stdio: "inherit" });
  child.on("error", (e) => {
    process.stderr.write(`rea-filter: cannot start rea (${e.message})\n`);
    process.exit(127);
  });
  child.on("exit", (code) => process.exit(code ?? 1));
}

async function listTools() {
  const child = startRea(["mcp"]);
  const pending = new Map();
  let nextId = 1;
  createInterface({ input: child.stdout, crlfDelay: Infinity }).on("line", (line) => {
    let message;
    try { message = JSON.parse(line); } catch { return; }
    const waiter = pending.get(message.id);
    if (!waiter) return;
    pending.delete(message.id);
    if (message.error) waiter.reject(new Error(message.error.message));
    else waiter.resolve(message.result);
  });
  const call = (method, params) => new Promise((resolve, reject) => {
    const id = nextId++;
    pending.set(id, { resolve, reject });
    child.stdin.write(JSON.stringify({ jsonrpc: "2.0", id, method, params }) + "\n");
  });
  const fail = (message) => {
    process.stderr.write(`rea-filter: ${message}\n`);
    child.kill();
    process.exit(1);
  };
  const timer = setTimeout(() => fail("timed out listing REA's tools"), 180_000);
  try {
    const init = await call("initialize", {
      protocolVersion: "2025-06-18",
      capabilities: {},
      clientInfo: { name: "antigem-rea", version: "1" }
    });
    child.stdin.write(JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized" }) + "\n");
    const tools = [];
    let cursor;
    do {
      const page = await call("tools/list", cursor ? { cursor } : {});
      tools.push(...(page.tools ?? []));
      cursor = page.nextCursor;
    } while (cursor);
    const groupIds = loadGroups().map((g) => g.id);
    const output = {
      server: init.serverInfo ?? null,
      generated: new Date().toISOString(),
      // Context sizes in bytes (≈4 per token), with the output schema profile rea-mcp was started with
      instructions_bytes: (init.instructions ?? "").length,
      lazy_bytes: JSON.stringify(gatewayDefinitions(groupIds)).length + LAZY_INSTRUCTIONS.length,
      tools: tools
        .map((t) => ({
          name: t.name,
          title: t.title ?? "",
          description: shorten(t.description),
          required: t.inputSchema?.required ?? [],
          changes: changesThings(t),
          bytes: JSON.stringify(t).length
        }))
        .sort((a, b) => a.name.localeCompare(b.name))
    };
    clearTimeout(timer);
    process.stdout.write(JSON.stringify(output, null, 1) + "\n", () => {
      child.kill();
      process.exit(0);
    });
  } catch (e) {
    fail(`listing REA's tools failed: ${e.message}`);
  }
}

// Last, so every constant above is initialized before a mode starts
const mode = process.argv[2];
if (mode === "--doctor") doctor();
else if (mode === "--list-tools") listTools();
else serve();

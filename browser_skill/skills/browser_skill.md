---
name: Browser automation in AntiGem's browser
description: Do tasks on websites in AntiGem's built-in browser with the browser_mcp tools (browser_*). Lock the tab, find elements by ref, click, type and fill forms, search sites, read pages, and handle dialogs, popups, new tabs and errors quickly and reliably.
---

# Browser automation in AntiGem's browser

The `browser_*` tools (MCP server `browser_mcp`) drive AntiGem's built-in browser like a person would. They send
real taps and keystrokes, read the page, and take screenshots. **Follow this guide**: it is the fast, reliable way
to use them. Read a detail file when your task needs it.

Detail files (read with `get_skill_file`, name `browser_skill`):

| File | When |
| --- | --- |
| `workflows.md` | Recipes: searching, forms, logins, multi-page tasks, reading and extracting data, uploads, cookie banners, infinite scroll, iframes, desktop sites, debugging a web app |
| `troubleshooting.md` | A tool returned an error, or the page does not do what you expect: each message and what to do |

## 0. Check the tools

You need tools named `browser_open_url`, `browser_find`, `browser_computer`, `browser_lock`, and so on. If they are
missing, stop and tell the user how to add the **Browser Automation** MCP:

- Antigravity: AntiGem → Settings → MCP Servers & Tools → Quick Presets → "Browser Automation" → save.
- Claude Code / Codex / OpenCode: AntiGem → Settings → that agent's MCP page → "Browser Automation" preset.
- Then reload the tools or start a new chat.

## 1. The loop: lock → look → act → check → unlock

1. **Pick a tab.** Use `browser_open_url` with `new_tab=true` for your own work, so you don't replace the page the
   user has open. Use the user's current tab only when the task is about that page. Omitting `tab_id` means the
   active tab; keep the `tab_id` the tools return and pass it every time once you have several tabs.
2. **Lock** with `browser_lock` once (see section 2) for any task of more than one or two steps. The lock then
   follows you to every tab you use or open.
3. **Look** with the cheapest tool that answers your question (section 3). You get refs like `ref_12`.
4. **Act on refs** with `browser_computer` and `browser_form_input` (section 4). Chain steps you can predict in
   one `browser_batch` call (section 6).
5. **Check** each result. Tool outputs say when the page changed, a new tab opened or a dialog appeared; read the
   page again or take a screenshot when unsure (section 7).
6. **Unlock** with `browser_lock` `locked=false` (no `tab_id`) when you are done: it releases every locked tab.
   Always do this, also when you stop because of an error or to ask the user something.

## 2. Locking: keep the user's touches, the keyboard and zoom out of your way

- Every browser tool call already blocks the soft keyboard on that tab for about 3 seconds, so focusing a field
  never opens it. The user can still touch and zoom the page then.
- `browser_lock` (default `locked=true`) turns on the **agent lock** for your task, with no timeout:
  - the tab you call it on (`tab_id`, or the active tab) is locked at once;
  - every tab you use or open while the lock is on is locked too: `browser_open_url` with `new_tab=true`, and
    popups or new tabs opened by your clicks. Outputs show it (`[mobile view, locked]`, "locked like this one");
  - on locked tabs the user's touches are blocked and the keyboard and zoom stay put, so pages behave the same from
    step to step. The user sees an "AI controls this tab · Unlock" button, and an "AI" badge on the tab in the tab
    overview.

  **Lock once at the start of a multi-step task.** Don't lock again for each new tab.
- `browser_lock` `locked=false` **without** `tab_id` turns the lock off and releases every locked tab; its output
  lists them. Do this when you finish. With `tab_id` it releases only that tab, which then stays unlocked until
  you lock it again. The output says when a tab was not locked, and lists the tabs that still are.
- The user can tap Unlock on any tab. That tab then stays unlocked; the lock does not take it back by itself.
  Signs that it happened:
  - a tool output starts with "Note: the user unlocked this tab…";
  - `browser_list_tabs` no longer shows `"lockedByAgent": true` for the tab;
  - the page changed in ways your actions did not cause: another URL, scrolled, a menu opened or closed, fields
    filled.

  When you see this in the middle of a task: read the page again (`browser_find` / `browser_read_page`, or a
  screenshot), because your refs and coordinates may be stale. Then lock that tab again with `browser_lock`
  `tab_id=<it>` and continue. If the user unlocks a second time during the same task, they want control: stop and
  ask them how to go on.
- A tab that a browser extension (e.g. Google Flow) is automating refuses your input; use another tab.

## 3. Looking: the cheapest tool that answers the question

| You need | Use | Notes |
| --- | --- | --- |
| One element: a button, a field, a link, a price | `browser_find` with plain words: "search box", "Add to cart button", "email field", "price of the blue shirt" | Fastest. Up to 20 matches, best first, each with a ref. Words that name a control type (button, field, box, link, checkbox, dropdown, tab, image) also match by type. Hidden things (closed menus, collapsed sections) are not searched: open them first. |
| What you can do on the page | `browser_read_page` `filter="interactive"` | Every clickable or typeable control, with state (checked, expanded, disabled, focused, value) |
| The page's structure: headings, lists, forms, text near controls | `browser_read_page` (`filter="all"`, the default) | Short text blocks are one line each. Big page: use `max_chars`, or `ref_id` to read one part |
| Text to read: an article, results, messages, a table | `browser_get_page_text` | Plain text of the main content. It says when text is hidden (collapsed sections); `include_hidden=true` reads it too |
| How it looks: layout, images, charts, canvas or video, whether something worked | `browser_computer` `action=screenshot` | Its pixels are the coordinates for clicks. `scale=0.5` for a cheap check; `action=zoom` with a `region` to read small text |
| Data the page has but does not show | `browser_eval_js` | e.g. `[...document.querySelectorAll('table tr')].map(r => r.innerText)`; top-level `await` works |

Prefer `browser_find` over reading the whole page, and refs over screenshots: text costs far fewer tokens than
images and is exact. Take screenshots when the page is visual, or to confirm an important result.

## 4. Acting

| To | Use |
| --- | --- |
| Click a button or link | `browser_computer` `action=left_click`, `ref=…` (it scrolls the element into view first) |
| Fill a text field, number, date or time, or a `<select>`; tick a checkbox or radio; set a textarea or rich-text editor | `browser_form_input` `ref=…`, `value=…`. Fast and framework-safe (React and Vue see the change). A checkbox that is already in the wanted state is left alone. |
| Type the way a person does: search boxes with suggestions, chat inputs, editors that react to each key | `left_click` the field, then `action=type`. `\n` in the text presses Enter. `type` fails, typing nothing, when no text field has focus |
| Press keys | `action=key`, e.g. `"Enter"`, `"Tab"`, `"Escape"`, `"ArrowDown Enter"`, `"ctrl+a"`, `"shift+Tab"`; `repeat` for many presses |
| Open a hover menu or tooltip | `action=hover` on the ref |
| Bring something into view | `action=scroll_to` with its ref. Use `action=scroll` (returns a screenshot) to explore, or for inner scroll boxes |
| Right-click, double-click, select a paragraph | `right_click`, `double_click`, `triple_click` |
| Drag (sliders, maps, drag-and-drop) | `action=left_click_drag` with `start_coordinate` and `coordinate` from a screenshot |
| Upload files | `browser_upload_file` with the ref of the upload button or file input. **Never click file inputs**: that opens a picker you cannot use |
| Custom dropdowns (not `<select>`) | Click the dropdown, then `browser_find` the option and click it |

Rules:
- **Refs over coordinates.** Refs point at the element itself and survive scrolling. Use coordinates only for
  things without a ref (canvas, maps, images); they are pixels in your latest screenshot of that tab.
- Pass `action_summary` on actions: 2–5 words such as "Opening Filters menu" or "Searching for shoes". It is
  shown next to the cursor so the user can follow along. Never put passwords or other secrets in it.
- A ref stays valid while its element is on the page. If the page redraws it, the tools find the same element
  again when only one matches. After a navigation, read the page again.

## 5. Searching

- **On the web**: `browser_open_url` with words instead of a URL searches the web. When you know a site's search
  URL, open it directly; that is the fastest way. Examples: `https://www.google.com/search?q=…`,
  `https://www.youtube.com/results?search_query=…`, `https://en.wikipedia.org/w/index.php?search=…`,
  `https://github.com/search?q=…`, `https://www.amazon.com/s?k=…`.
- **In a site's own search box**: `browser_find` "search box" → `browser_form_input` the query → `action=key`
  `"Enter"`. If the site shows suggestions you need, or ignores the value, `left_click` the box and `type` the
  query instead. On mobile layouts the box is often behind a "Search" button: click it first, then type. Typing
  waits a moment for the box to get focus.
- **Within the page**: `browser_find` with words from what you are looking for. Use `browser_get_page_text` to read
  everything.

## 6. Batching: fewer round trips

`browser_batch` runs several calls in order and stops at the first error. Use it whenever you can predict the
next steps. Each item is `{"name": tool, "input": its arguments}`; `computer` is short for `browser_computer`, and
so on.

```json
{"actions": [
  {"name": "browser_form_input", "input": {"ref": "ref_8", "value": "running shoes", "action_summary": "Entering the search"}},
  {"name": "browser_computer", "input": {"action": "key", "text": "Enter"}},
  {"name": "browser_computer", "input": {"action": "wait", "duration": 1.5}},
  {"name": "browser_find", "input": {"query": "first product title"}}
]}
```

- Coordinates inside a batch refer to the screenshot taken before the batch.
- Do not put an action that depends on what you have not seen yet (a ref from a page that is still loading) into the
  same batch; end the batch with a `find`, `read_page` or `screenshot` and plan the next batch from it.

## 7. Checking results

- Read every action's output. It tells you what was clicked (`Clicked button "Search" [ref_7]`), whether the page
  changed (`The page changed to …`), whether a new tab opened (`This opened a new tab: <id>`), and whether
  something covered the target (`Note: … was covering it`).
- After a navigation or a big change, look again before acting: refs from the old page are gone.
- Confirm important outcomes (an order placed, a form sent, a setting saved) with `browser_find` for the success
  message, `browser_get_page_text`, or a screenshot.
- Use `browser_computer` `action=wait` (1–3 s) for pages that load content after a click, then look again.

## 8. Dialogs, popups and new tabs

- **JavaScript alert / confirm / prompt / "Leave this page?"**: while one is open, every page is paused and other
  tools tell you so. Answer it with `browser_handle_dialog` (`accept=true` for OK or Leave, `false` for Cancel or
  Stay; `prompt_text` for prompts). `browser_list_tabs` shows open dialogs.
- **Cookie banners and consent popups**: choose the most privacy-preserving option ("Reject all",
  "Only necessary"), unless the user said otherwise.
- **Newsletter and app-install popups**: close them (`browser_find` "close button", or `action=key` `"Escape"`).
- **Links that open a new tab**: the click output gives the new `tab_id`; pass it to the next tools. Close tabs
  you opened when you no longer need them, unless the user wants to see them.

## 9. Ask the user first

Ask in chat and wait for a clear yes before anything outward-facing or hard to undo: submitting forms, sending
messages, posting, buying, booking, deleting, changing account settings, accepting terms. Logins, passwords,
2FA codes and captchas are for the user: unlock the tab, ask them to do it in the browser, and continue when they
say they are done.

## 10. Speed tips

- `browser_find` before `browser_read_page`; `filter="interactive"` before the full tree.
- One `browser_batch` instead of several calls.
- `browser_form_input` instead of click + type when the field has no suggestions.
- A site's search URL instead of its search box.
- `scale=0.5` screenshots for quick visual checks; `action=zoom` instead of a full screenshot to read small text.
- Don't screenshot after every step; the action outputs already report page changes.

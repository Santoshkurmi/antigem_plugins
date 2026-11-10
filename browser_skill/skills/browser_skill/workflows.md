# Workflows

Recipes for common browser tasks. Each assumes you turned on the agent lock (`browser_lock`, once; it follows you to
new tabs) and will release it at the end (`browser_lock` `locked=false`, no `tab_id`).

## Search a site and open a result

```json
{"actions": [
  {"name": "browser_open_url", "input": {"url": "https://www.youtube.com/results?search_query=jetpack+compose+tutorial", "new_tab": true}},
  {"name": "browser_lock", "input": {"action_summary": "Searching YouTube"}},
  {"name": "browser_find", "input": {"query": "first video title"}}
]}
```

Then `left_click` the ref you want. When you don't know the site's search URL, use its search box:
`browser_find` "search box" → `browser_form_input` → `action=key` `"Enter"`. On mobile layouts the box may be behind
a "Search" button: click it first, then `type`.

## Fill and send a form

1. `browser_read_page` `filter="interactive"` to see every field with its state.
2. One batch of `browser_form_input` calls, one per field. Text, number, date (`YYYY-MM-DD`), time (`HH:MM`),
   `<select>` (option text or value), checkboxes and switches (`true` / `false`), radios (`true`).
3. `browser_read_page` `filter="interactive"` again to check the values. `form_input` already reports each field
   that refused a value.
4. Ask the user before pressing the submit button, unless they clearly asked you to send it.
5. Click submit, then check the result page (success message or validation errors).

Fields with autocomplete (addresses, cities, airports): `left_click` the field, `type` part of the text,
`action=wait` 1 s, `browser_find` the suggestion, click it.

## Logins and anything secret

Do not type passwords, card numbers or 2FA codes, and do not complete captchas. Release the tab
(`browser_lock` `locked=false` `tab_id=<it>`), switch the user to it (`browser_switch_tab`), and ask them to sign
in and tell you when they are done. Then lock it again (`browser_lock` `tab_id=<it>`) and continue. Google sign-in pages also turn off the browser's DevTools, so
automation there is limited anyway.

## Multi-page tasks (lists, pagination, comparisons)

- Read a list page with `browser_get_page_text` (fast) or `browser_find` (for refs).
- Open items in new tabs if you need to come back: `browser_open_url` with the item's `href` (from
  `browser_read_page`) and `new_tab=true`; the agent lock covers them. Keep track of the tab ids and close them
  afterwards.
- For "next page" use `browser_find` "next page"; check the URL in the click output to confirm the move.

## Read or extract data

- Articles and docs: `browser_get_page_text` (add `include_hidden=true` for collapsed sections, as on mobile
  Wikipedia).
- Tables and lists: `browser_eval_js`, e.g.
  `[...document.querySelectorAll('table tr')].map(r => [...r.cells].map(c => c.innerText.trim()))`.
- Data loaded by the page's API: `browser_read_network` `url_pattern="/api/"` shows the requests; fetch one with
  `browser_eval_js` `await fetch(url).then(r => r.json())`. The page's cookies are sent.

## Infinite scroll and lazy loading

`action=scroll` down (returns a screenshot; its output also says whether the page moved), or `action=key`
`"End"`. Then `action=wait` 1 s and `browser_get_page_text` / `browser_find`. Stop when the output says the page
did not move or nothing new appears.

## Cookie banners and popups

`browser_find` "reject cookies" or "only necessary". If there is no reject option, look for "settings" or
"customize" to turn the extras off before you accept. Close other popups with `browser_find` "close" or
`action=key` `"Escape"`. If a click's output says something "was covering it", a popup is in the way: close it,
then click again.

## Menus and hover content

`action=hover` on the menu's ref opens hover menus; then `browser_find` the item. Click-to-open menus: click, then
find the item. `browser_read_page` shows `(expanded)` / `(collapsed)` on menu buttons.

## Iframes and shadow DOM

`browser_read_page` and `browser_find` look inside same-origin iframes and open shadow roots, and their refs work
normally. A frame from another site shows as `iframe … (cross-origin frame: contents not readable)`: take a
screenshot and click it by coordinates. Typing into a focused field inside it still works.

## Desktop sites

Some sites only offer features on their desktop layout. Use `browser_open_url` with `mode="desktop"`, or
`browser_set_view_mode`. Screenshots then show the full desktop width, so text is small: use `action=zoom` on a
region to read it. Refs work the same as in mobile view.

## Uploading files

`browser_find` "upload" or "choose file" → `browser_upload_file` with that ref and the file paths (inside the
terminal home or /sdcard). Never click the file input itself. Check the page afterwards (file name shown, preview).

## Downloads

There is no download tool. Get the file's URL (`browser_read_page` gives `href`s) and download it in the terminal
(`curl -L -o file "<url>"`); for pages that need the user's login, ask the user.

## Debugging a web app you are building

- Open it: `browser_open_url` `http://localhost:5173` (any port).
- Errors: `browser_get_console_logs` `only_errors=true` (`pattern` to filter, `clear=true` before a retry).
- Requests: `browser_read_network` `only_failed=true`, or `url_pattern="/api/"`. Reload the page
  (`browser_open_url` `url="reload"`) to capture its first requests.
- State: `browser_eval_js` (`localStorage`, app globals, `document.querySelector(...)`).
- After code changes, reload and check again; compare screenshots before and after.

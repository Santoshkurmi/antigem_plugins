# Troubleshooting

What a tool's message means and what to do. The messages are quoted as the tools write them.

| Message | Meaning | Do |
| --- | --- | --- |
| "Note: the user unlocked this tab…" | The user tapped Unlock and may have used the page | Read the page again, then `browser_lock` again if your task is not finished (ask the user if it happens twice) |
| "No element ref_N … on the page any more" | The element was removed, or the page redrew it in a way that could not be matched | `browser_find` / `browser_read_page` for a fresh ref |
| "ref_N is not from this page…" | The page was reloaded or replaced, or the app restarted, since you read it | Read the page again |
| "…had been redrawn by the page; used the matching element" | The tool found the same element again by its role and name | Nothing; it worked |
| "No tab with id …: it was closed, or the app restarted" | Old tab id; the message lists the tabs open now | Use one of the listed ids, or open the page again |
| "Nothing was typed: no text field has keyboard focus" / "…which is not a text field" | `type` needs a focused text field | `left_click` the field first (by ref), or use `browser_form_input`. To press keys on the page itself use `action=key` |
| "…but its content did not change" | The page blocked the input or swapped the field | Screenshot to see why; try `browser_form_input`, or click the field again and type |
| "There is no screenshot of this tab yet" / "outside the latest screenshot" / "The visible page area changed" | Coordinates need a current screenshot | A fresh screenshot is attached to the error: use its pixels and retry. Better: use refs |
| "these coordinates come from a screenshot of …; the tab now shows …" | The page navigated since your screenshot | Take a new screenshot if the click was not meant for the old page |
| "A JavaScript alert/confirm/prompt is open…" / "That opened a page dialog" | A page dialog paused every page | `browser_handle_dialog` with `accept=true` or `false` (`prompt_text` for prompts) |
| "…opens a file picker, which cannot be used here" | You tried to click a file input | `browser_upload_file` with that ref |
| "This tab is being automated by a browser extension" | Google Flow (or another extension) owns the tab | Open your own tab with `new_tab=true` |
| "Nothing on the page matches …" | `browser_find` found nothing visible | Use words that appear on the page; open closed menus or sections first; `browser_read_page` `filter="interactive"`; scroll for lazy content |
| "…was covering it at that point" | Something (a popup, banner or sticky header) is over the target | Close the popup or scroll a little, then click again |
| "The page did not answer within 10 s" | The page is busy, frozen or still loading | `action=wait`, then a screenshot; reload (`browser_open_url` `url="reload"`) if it stays stuck |
| "Could not load the page helper" | The page is navigating, is not HTML (PDF, image), or blocks scripts | Wait and retry; use a screenshot and coordinates |
| "(cross-origin frame: contents not readable…)" | A frame from another site | Screenshot and click by coordinates |
| "Full request recording needs DevTools…" (`browser_read_network`) | DevTools is off on this page (Google sign-in pages) | Only failed requests are listed; that is expected there |
| "This tab has no earlier page in its history" | `url="back"` at the first page | Open the URL directly |

## The page does not react to a click

1. Check the click output: what did it hit (`Clicked … on <element>`)? Was something covering it?
2. The element may need a hover first (menus), or a double-click.
3. Single-page apps may update slowly: `action=wait` 1 s, then look again.
4. Click by ref instead of coordinates, or the reverse, using the screenshot's centre of the element.

## A field ignores the value

- `browser_form_input` reports when a field refused a value (e.g. a date must be `YYYY-MM-DD`).
- Some fields react only to typing: `left_click` the field, `ctrl+a` with `action=key` to select the old text,
  then `type`.
- Masked inputs (phone numbers, cards) may want digits only.

## Text or controls you know are there are not found

- They may be hidden: closed menus, collapsed sections, inactive tabs. Open them first.
  `browser_get_page_text` `include_hidden=true` reads hidden text.
- Content loaded on scroll: scroll down, wait, look again.
- Very large pages: `browser_read_page` stops early and says so; use `browser_find` or `ref_id`.

## Screenshots look wrong

- In desktop view the full page width is shown, so text is small: use `action=zoom` on a region.
- A screenshot shows only the visible area, not the whole page: scroll, or use `browser_get_page_text`.
- Overlays drawn by AntiGem (cursor, caption, lock button) never appear in screenshots.

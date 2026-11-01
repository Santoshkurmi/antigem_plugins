---
name: Product / app promo and ads
description: Short promos and ads for products, apps, services, events and launches — hero product shots, phone/browser mock-ups, feature callouts, price bursts, testimonials, logo reveal and call to action.
---

# Product promo / ad

Starting point: `$VS new DIR --example product_promo` (9:16, style `minimal`; `luxury` for premium goods, `neon` for
tech, `bold_explainer` for loud promos).

## 15–30 s structure
1. **Hook (0–2 s)**: the problem or the product hero shot, moving on frame 1.
2. **Product reveal**: cut-out product (`kit.sticker` without border or plain `image` + `shadow`) on a gradient,
   `zoom_in` + light sweep (recipe 10 in `make_video/docs/recipes.md`), or `kit.phone_frame` / `kit.browser_frame`
   with a screenshot for apps (`scroll` to show more).
3. **3 benefits**, one per 2–3 s: `kit.list_item` / `kit.checklist_item`, or `"layout": "focus"` with `kit.callout`s
   pointing at product parts.
4. **Proof**: `kit.stat_card` (users, rating), `kit.post_card` testimonial.
5. **Offer + CTA**: `kit.burst` ("−30%", "NEW"), price `counter`, then logo reveal (ring draw + logo `zoom_in` +
   `sfx:bass_drop` + sparks) and the URL/handle.

## Rules
- Brand colors via `"theme": {"accent": "#...", "accent2": "#..."}`; brand font in `fonts/` + `"theme": {"font_display": "BrandFont"}`.
- One message per shot; benefits not features ("Never miss a deadline", not "Push notifications").
- Fast but clean: `slide_left`/`zoom` transitions, entrances 0.3–0.5 s, nothing longer than 3 s without change.
- Only real claims the user supplies.

---
name: News recap & social media stories
description: News-style recaps and social-media-native formats — breaking news banners and tickers, post/tweet cards, viral comment reactions, phone notifications and text-message/chat stories.
---

# News & social formats

Starting point: `$VS new DIR --example news_social` (9:16, style `news`).

## Formats
- **Breaking recap**: background photo/clip dimmed (`filter.brightness 0.6`), `kit.breaking_news` (label, headline,
  ticker) near 78 % height, `kit.live_badge`, `kit.location_tag`. One story per scene, 4–6 s, `wipe_left` transitions.
- **"The internet reacts"**: `kit.post_card` (counting likes), `kit.comment_bubble`, `kit.notification` sliding down.
  Stack 2–3 cards with staggered `at` and slight `rotation`.
- **Chat story** (text-message drama): light background, `kit.chat_left` / `kit.chat_right` bubbles stacked every ~9 %
  of the height, each `at` a beat later (0.8–1.2 s); `sfx:blip8` / `sfx:pop` per message; punchline message +
  camera punch + a reacting `stickman`. Scroll long chats by putting bubbles in a `group` and animating its `y`.
- **Explainer news** ("what happened with X"): `kit.headline_box`, `kit.stat_card`, `kit.versus` for two sides,
  `kit.timeline_point` for how it unfolded.

## Rules
- Mock-ups are generic (no real brand logos or exact app designs); invent names/handles unless the user supplies real
  public posts they may quote.
- Keep text short in cards (fits `max_height`, the font shrinks otherwise).
- Captions `clean`. Sounds: `sfx:whoosh` on banners, `sfx:ding` on notifications.

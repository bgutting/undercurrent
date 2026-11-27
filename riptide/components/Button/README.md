# Button

Mono caps pills: the label is always `button-mono` (JetBrains Mono 12/600, 1.5px tracking, UPPERCASE), except the secondary, which drops to sentence-case sans.

- **Primary** — `.rt-btn-primary`: `cerulean` fill, `on-cerulean` text, `radius-feature`. One per view, for the thing the page is for (subscribe, sign in). Hover inverts to a `canvas` fill with a `cerulean` outline and `cerulean-ink` label.
- **Flare** — `.rt-btn-flare`: `flare` fill, `on-flare` text. Only for joining something happening now (watch live, follow the live blog). Never on the same view as a primary unless the live event IS the page.
- **Secondary** — `.rt-btn-secondary`: `surface-slate` fill, `ink-on-slate` text. Hover adds a `hairline`.
- **Outlined cerulean** — `.rt-btn-outline`: transparent, 1px `cerulean`, `radius-pill`, `cerulean-ink` label; fills on hover.
- **Outlined ultraviolet** — `.rt-btn-ultraviolet`: commerce and promo only (deals, events). 1px `ultraviolet-ink`, `radius-promo`.

Pressed: `surface-pressed`. Focus: 2px `focus-ring` at 2px offset. No shadows, no scale on hover. The consumer provides the `<button>` and its label; the classes come from `components/bundle.css`.

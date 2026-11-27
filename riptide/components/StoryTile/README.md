# StoryTile

The unit of the homepage: a rounded card (`radius-tile`, `space-6` padding) holding a mono kicker, a `heading-md` headline and a byline pinned to the bottom.

- **Outline** — `canvas` with a 1px `hairline`. The default; most of a grid should be these.
- **Cerulean** — the highlight tile, `on-cerulean` text. At most one or two per screen: the accent works because it is rationed.
- **Flare** — the live or breaking story, `on-flare` text. One per page, and only while it is live; it reverts to outline afterwards.
- **Ultraviolet** — alternates and commerce, `on-ultraviolet` text.

Hover changes the headline colour only (to `cerulean-ink` on outline tiles) — no lift, no scale, no shadow. Images inside sit at `radius-image` with a 1px `hairline-soft` frame. The consumer provides the link, kicker, headline and byline.

# FeedItem

One entry in the StoryStream feed: a 1px `ultraviolet-rule` rail on the left, a mono `timestamp` in `ink-muted`, then a card with a 1px `hairline-soft` border at `radius-tile`.

Headline in `heading-sm`; the blurb is the one place the serif (`serif-body`) appears in UI. Links inside are `cerulean-ink`, underlined. A live item (`.rt-feed-item-live`) swaps the rail to `flare` and the timestamp to `flare-ink`, prefixed "Live". Items stack `space-3` apart. The rail is decorative (1.7:1 on dark canvas); the timestamp carries the meaning.

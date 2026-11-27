# Riptide

A loud, editorial tech-tabloid system built on The Verge's 2022 redesign — near-black canvas, heavy condensed headlines, mono-caps labels, 1px white lines instead of shadows — re-tuned to a cooler palette: the acid Jelly Mint accent (`#3cffd0`) is replaced by **cerulean** (`#2fa8e8`), and a warm third accent, **flare** (`#ff7a45`), puts back the tension that the swap took out.

## The three accents

| Accent | Token | Means | Text on it |
|---|---|---|---|
| Cerulean | `cerulean` | The brand. Primary buttons, highlight tiles, active states. | `on-cerulean` (black) |
| Ultraviolet | `ultraviolet` | Commerce, promo, error. | `on-ultraviolet` (white) |
| Flare | `flare` | Live and breaking — something happening now. Nothing else. | `on-flare` (black) |

Flare is the scarcest of the three: at most one flare element per view (a LIVE tag, a breaking tile, a watch-live button), and it comes off when the event ends. Its rarity is what makes it read as urgent.

## What changed from the source, and why it rippled

Mint sits at 16:1 against black; that luminance is what made it feel like hazard paint. Cerulean sits at 7.9:1 — still unmistakably the accent, but it reads as a colour rather than a warning light. Knock-ons:

- **Focus.** The source's focus cyan (`#1eaedb`) would now be indistinguishable from the accent. `focus-ring` is white in dark and ultraviolet in light.
- **Link hover.** The source hovered links to a mid blue (`#3860be`), which now clashes with cerulean. Hover goes to `cerulean-ink` instead.
- **Accent pairing.** Mint and ultraviolet were opposite hues; cerulean and ultraviolet are neighbours, so on their own the palette went cool and quiet. Flare is cerulean's complement and restores the clash. Cerulean and ultraviolet stay apart by lightness (never set one on the other as text: 2.8:1). Cerulean and flare are the SAME lightness (1.1:1), so where they touch they vibrate — wanted on a cover, never as the only cue for meaning: a live tile is always labelled "Live".

## Voice

Confident, quick, a little irreverent. Headlines make a claim; kickers are one word in caps. No exclamation marks, no emoji, no "you won't believe".

## Visual foundations

- **Canvas first.** `canvas` is near-black (`#131313`), never pure black. Light theme is for long-read article pages.
- **Accents are rationed.** `cerulean` (primary), `ultraviolet` (commerce, error) and `flare` (live only) appear as solid fills — tiles, pills, buttons — never as washes, gradients or glows. One or two accent tiles per screen.
- **Lines, not shadows.** Depth comes from 1px `hairline` (full-strength white in dark) and `hairline-soft` around images. The only shadow token is `shadow-ring`.
- **Two radius worlds.** 2–4px for inputs and media (`radius-xs`, `radius-image`, `radius-sm`); 20–40px for tiles and buttons (`radius-tile` … `radius-pill`). Nothing in between.
- **Text on accents.** `on-cerulean` (black) on cerulean; `on-ultraviolet` (white) on ultraviolet. `on-flare` (black) on flare. An accent as *text* uses `cerulean-ink` / `ultraviolet-ink` / `flare-ink`.

## Type

Four voices, each with a job:

| Family | Token | Job |
|---|---|---|
| Display | `--font-display` | Headlines 60–107px, tight leading. One per section. |
| Sans | `--font-sans` | Headlines 20–34px, body, uppercase labels. |
| Mono | `--font-mono` | Every button label, timestamp and kicker — UPPERCASE, tracked. |
| Serif | `--font-serif` | Review decks and feed blurbs only. |

The Verge's own faces (Mānuka, PolySans, PolySans Mono, FK Roman Standard) are commercial and not included. This system uses Google Fonts stand-ins — **Anton, Space Grotesk, JetBrains Mono, Newsreader** — loaded by `components/bundle.css`. Each stack names the licensed original second, so a machine that has it installed will not pick it up ahead of the stand-in; swap the order if you hold the licenses. Anton has one weight, so display styles are 400 with leading raised from 0.80 to ~0.92.

## Iconography

No icon set ships with this system. If you add one: single-weight stroke icons, square caps, drawn in `ink`; on accent fills, `on-cerulean` / `on-ultraviolet` / `on-flare`.

## Gaps

The source names saturated yellow, pink, orange and electric-blue tile fills without values; flare covers the warm slot, the rest are not invented here. There is no logo — use the name set in `display-hero`.

## Sources

Built from third-party reconstructions of theverge.com's styles (the site itself could not be fetched), and Fonts In Use / Typeroom on the 2022 redesign typefaces. Values are as documented there, except the accent family above (cerulean and flare are this system's own).

# pianeer-app

The marketing, support and privacy site for **Pianeer**, an iPhone and iPad app
for piano practice driven by MIDI input. Published with GitHub Pages and linked
from Pianeer's App Store listing.

The app itself lives in a separate repository.

## What's here

| File | Purpose | App Store field |
| --- | --- | --- |
| `index.html` | Marketing landing page | **Marketing URL** |
| `support.html` | FAQ and contact details | **Support URL** |
| `privacy.html` | Privacy policy | **Privacy Policy URL** |
| `assets/css/style.css` | The entire stylesheet | — |
| `assets/img/screens/` | Web-optimised screenshots | — |
| `manual-shots/` | Original full-resolution captures (source of truth) | — |

## Stack

Static HTML and one hand-written CSS file. Deliberately no framework, no build
step, no package manager and **no web fonts** — the pages use the system font
stack, so they render in Apple's own typefaces on Apple devices and load with
zero blocking third-party requests. The only JavaScript on any page is a
one-liner that fills in the copyright year.

There is nothing to compile. Edit a file, commit, and GitHub Pages serves it.

- Fully responsive, down to small phones.
- **Light only**, matching the app, which is itself light-only
  (`UIUserInterfaceStyle: Light`). A complete dark palette, drawn from the app's
  falling-notes view, is written and working but switched off: it is gated
  behind `:root[data-theme="dark"]`, an attribute nothing sets. Search
  `DARK-THEME` in `assets/css/style.css` — the comment there says how to turn it
  back on, either following the reader's OS or behind an explicit toggle.
- Respects `prefers-reduced-motion`.
- `.nojekyll` is present so GitHub Pages serves the files as-is.

## Local preview

No server is strictly needed — `open index.html` works. To check it over HTTP:

```bash
make serve
```

Then visit <http://localhost:8000>.

## Checks

There is no compiler to catch a typo, so `tools/check.py` does it instead.
Standard library Python only — no Node, no npm, nothing to install:

```bash
make check
```

It verifies, across all three pages:

1. Tag balance and nesting, with a real HTML5-aware parser.
2. Every referenced stylesheet, script and image exists on disk.
3. Every internal link resolves to a file that exists.
4. Every `#anchor` resolves, including cross-page ones like `./#pricing`.
5. Every `<img>` has `alt` and explicit `width`/`height` (no layout shift).
6. Each page has exactly one `<h1>`, a `<title>` and a meta description.
7. The hand-duplicated nav and footer have not drifted apart.
8. The stylesheet and the markup agree: no class without a rule, no rule
   without a user.

`.github/workflows/check.yml` runs the same script on every push, so a broken
link cannot reach the App Store listing unnoticed.

### Browser support

The CSS deliberately stays on long-settled features — Grid, Flexbox, custom
properties, `clamp()`, `position: sticky`, `scroll-snap`, `prefers-color-scheme`
— none of them newer than about 2021. The only two newer things,
`loading="lazy"` and `fetchpriority`, are hints that do nothing at all on a
browser that lacks them. `backdrop-filter` has an `@supports` fallback to an
opaque nav bar.

The site has been checked in Chromium and in Mobile Safari on the iOS 18
simulator at 375pt, which is the narrowest phone worth worrying about and the
browser most visitors from the App Store listing will arrive in.

## Before the app goes live

Three things are placeholders until Pianeer is approved.

**1. The App Store links.** Search the HTML for `APPSTORE_URL`:

```bash
grep -rn "APPSTORE_URL" .
```

Each marked `<a>` currently points at `#pricing` or `#` and reads "Coming soon
to the App Store". Replace the `href` with the real listing URL
(`https://apps.apple.com/app/id<YOUR_APP_ID>`) and change the small line above
the button from "Coming soon to the" to "Download on the". Also update the
"Coming to the App Store" button in the nav bar of `index.html`.

**2. Apple's official badge.** The store buttons are plain, unbranded links
styled to look like a store button — they do *not* reproduce Apple's badge
artwork. Once the app is live, download the official "Download on the App Store"
badge from
[Apple's marketing resources](https://developer.apple.com/app-store/marketing/guidelines/)
and swap it into the `.appstore` element, which is sized for it. Apple requires
their own artwork rather than a lookalike.

**3. The canonical URL.** Each page has a `<link rel="canonical">` pointing at
`https://pianeer-app.github.io/`. If you set up a custom domain, update all
three (and add a `CNAME` file).

## Publishing

This is a GitHub Pages **organisation site**, which constrains the repo name:
it must be `<org>.github.io` exactly, so under the `pianeer-app` org the repo
has to be called **`pianeer-app.github.io`**. That is what puts the site at the
root of the domain rather than in a subdirectory.

```bash
git remote add origin git@github.com:pianeer-app/pianeer-app.github.io.git
git push -u origin main
```

Then Settings → Pages → *Source: Deploy from a branch* → branch `main`, folder
`/ (root)`. The site appears at `https://pianeer-app.github.io/` within a
minute or so.

The three App Store URLs are then:

| Field | URL |
| --- | --- |
| Marketing | `https://pianeer-app.github.io/` |
| Support | `https://pianeer-app.github.io/support.html` |
| Privacy Policy | `https://pianeer-app.github.io/privacy.html` |

## Updating the screenshots

`manual-shots/` holds the original captures straight off the simulator.
`assets/img/screens/` holds resized, compressed copies for the web — nothing on
the site points at the originals. To regenerate one after a new capture:

```bash
sips --resampleWidth 560 -s format jpeg -s formatOptions 88 manual-shots/iphone-6.9/NEW.png --out assets/img/screens/iphone-home.jpg
```

Use `--resampleWidth 560` for iPhone shots and `--resampleWidth 900` for iPad.

**Use `--resampleWidth`, not `-Z`.** `-Z` fits the *longest* side, so on a
portrait screenshot it sets the height and leaves the width about 45% of what
you asked for. That silently shipped 294px-wide phone shots that looked soft on
every retina screen.

The widths above are roughly 2.4x the largest size each image is displayed at,
which is what keeps them sharp on a retina display. Screenshots that are mostly
sheet music sometimes come out smaller as PNG than as JPEG — try both, keep the
smaller file, and update the `<img src>` extension to match.

Then update that `<img>`'s `width` and `height` to the new file's real pixel
size. They are what reserves the space before the image loads, so a stale pair
is a layout shift:

```bash
sips -g pixelWidth -g pixelHeight assets/img/screens/iphone-home.jpg
```


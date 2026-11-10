# samkp.com

Personal site for Sam Kaplan Pettus — political organizer, communicator & strategist.
Hand-written static HTML, published to GitHub Pages at **samkp.com**.

## Layout

```
index.html         Home — full-screen hero (logo + portrait), then "Check These Out" tiles
consulting.html    Two scroll-snap panels: Consulting (orange) + Work history (blue)
resume.html        Resume
precinct-map.html  Berkeley precinct map (embeds an external map app)
d1/                Berkeley District 1 ranked-choice count: index.html + updates.json
assets/site.css    The shared layer — every page links it. Change the brand here.
assets/            logo.webp, logo-wordmark.webp, portrait.webp, texture.jpg, og-image.png
scripts/           build-updates.sh — polls the county, appends to d1/updates.json
.github/           workflows/d1-updates.yml — runs that script on a schedule
CNAME              samkp.com (custom domain)
```

## How it deploys

GitHub Pages builds **directly from the `main` branch** (root). Push to `main` and the
site goes live — there is no build step and nothing generates the HTML. Edit by hand.

## Design system

`assets/site.css` is the single source: brand tokens, the reset, the orange field and
its texture, the nav and the footer. Every page links it and its own `<style>` holds
only what is true of that page. Change the brand once, there, and every page follows.

A page's `<style>` loads *after* the shared sheet, so a bare `nav{...}` or `body{...}`
rule in a page will beat the shared one. Scope such overrides (a media query, or a more
specific selector) rather than restating the bare element.

Two colour "recipes", driven by those variables:

| | Consulting (orange) | Work (blue) |
|---|---|---|
| field | `#C6572A` | `#3C69AC` |
| accent | `#1F3A2E` green | `#F2B417` gold |
| cards | `#EAE1C6` cream | `#EAE1C6` cream |

On `consulting.html` both recipes live on one page, scoped to `.panel-consult` and
`.panel-work`, so each section keeps its own look.

- **Wordmark:** `assets/logo-wordmark.webp` sits in the nav on `consulting`, `resume` and
  `/d1`. Not on the home page, whose hero already shows the full logo, and not on the
  precinct map, whose bar is the dark green `#1F3A2E` — the mark's green fill needs the
  orange behind it. Add it by putting `<a class="brand">` in the nav; the shared sheet
  does the rest, and `nav:has(.brand)` splits the row. A branded nav stays in flow on
  small screens instead of pinning to the top, because it is too tall to float.
- **Fonts:** Anton (headlines, uppercase), Lora (body serif), Poppins (nav/labels).
- **Texture:** kraft photo on `soft-light` over the orange; SVG grain on `multiply` over the blue.
- **Motion:** GSAP ScrollTrigger (scroll-reveal) and GSAP Flip (click-to-feature on the work
  cards). Scroll-snap is native CSS (`scroll-snap-type: y proximity`). All motion respects
  `prefers-reduced-motion`.

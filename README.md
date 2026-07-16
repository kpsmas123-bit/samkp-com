# samkp.com

Personal site for Sam Kaplan Pettus — political organizer, communicator & strategist.
Hand-written static HTML, published to GitHub Pages at **samkp.com**.

## Layout

```
index.html         Home — full-screen hero (logo + portrait), then "Latest Projects" tiles
consulting.html    Two scroll-snap panels: Consulting (orange) + Work history (blue)
assets/            logo.svg, portrait.png, texture.jpg
CNAME              samkp.com (custom domain)
```

## How it deploys

GitHub Pages builds **directly from the `main` branch** (root). Push to `main` and the
site goes live — there is no build step and nothing generates the HTML. Edit by hand.

## Design system

Two colour "recipes", driven by CSS variables:

| | Consulting (orange) | Work (blue) |
|---|---|---|
| field | `#C6572A` | `#3C69AC` |
| accent | `#1F3A2E` green | `#F2B417` gold |
| cards | `#EAE1C6` cream | `#EAE1C6` cream |

On `consulting.html` both recipes live on one page, scoped to `.panel-consult` and
`.panel-work`, so each section keeps its own look.

- **Fonts:** Anton (headlines, uppercase), Lora (body serif), Poppins (nav/labels).
- **Texture:** kraft photo on `soft-light` over the orange; SVG grain on `multiply` over the blue.
- **Motion:** GSAP ScrollTrigger (scroll-reveal) and GSAP Flip (click-to-feature on the work
  cards). Scroll-snap is native CSS (`scroll-snap-type: y proximity`). All motion respects
  `prefers-reduced-motion`.

## Filling asset slots

Placeholders are marked `▢` in the HTML. Drop real files into `assets/` and point the `▢`
element at them. Keep exports compressed — large images slow the page down.

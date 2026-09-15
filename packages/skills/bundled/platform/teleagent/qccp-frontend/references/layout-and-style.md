# Layout and Style Rules

## Project facts

| Item | Rule |
| --- | --- |
| Design width | 1920px desktop-first |
| Global header | 60px, rendered by `App.vue` |
| Content width | `.wrapper` is 1440px centered |
| Page background | `#f4f7fc` |
| Brand blue | `#1664ff` or `#1964fc` |
| Text colors | `#020814`, `#1e1e1e`, `#41464f` |
| Font | global `PingFang SC, Microsoft YaHei` |
| Unit handling | write design `px`; project `postcss-pxtorem` converts automatically |

Do not manually convert all sizes to `rem`; do not import `src/utils/rem.js`.

## Structure

Use a top-to-bottom page layout by default:

1. Algorithm application introduction box.
2. Hero/banner section.
3. Core value or overview section.
4. Capability/process/data sections.
5. Scenario/case/result sections.
6. Action section and optional `<Footer />`.

Avoid split-screen hero designs where text and media are equal left/right columns. If a two-column block is necessary, place it inside a later content section, not as the primary page structure.

## Algorithm introduction box

Every generated algorithm application page must start with a text description box for the algorithm application. Use the application description from the user request, backend contract, or `application_manifest.json`; do not leave placeholder copy.

- Place it as the first visible content block inside `<main>`, before the banner/header section.
- Use the project `.wrapper` or an equivalent page-local container so the box width is the 1440px page content width.
- Set `margin-top: 40px`.
- Set `background: #e9effc`.
- Set `padding: 20px`.
- Set text `font-size: 14px` and `color: #000`.
- Keep the description text in i18n keys, with complete zh/en entries in `INTEGRATE.md`.

## SCSS rules

- Use `<style lang="scss" scoped>`.
- Root class must include `pageKey`, for example `.quantum-security-page`.
- Page-local components must also have unique root classes.
- Use `:deep(...)` only for Element Plus internals.
- Do not style `body`, `html`, `#app`, `.header`, `.footer`, or other global selectors.
- Do not output unscoped global style blocks.
- Do not modify the global `.wrapper`; either use it as-is or create a page-specific container.

## Responsive requirements

- Must work at 1366px, 1440px, and 1920px desktop widths.
- No horizontal scrollbar.
- Do not depend on fixed Chinese character width. English can be longer.
- Buttons, tags, cards, tabs, and table headers must handle both zh and en text.
- Use wrapping, flexible grid tracks, and `minmax(0, 1fr)` where text overflow is possible.
- QCIS circuit display sections should be full-width within the content container, with a stable min-height and internal scrolling handled by the circuit component. The page itself must not gain a horizontal scrollbar.

## Visual discipline

- Prefer clean enterprise platform layout over decorative marketing composition.
- Do not use emoji.
- Do not use random network images or invented object storage URLs.
- If images are provided, place them in `src/assets/images/<pageKey>/` and import via `@/assets/images/<pageKey>/...`.
- If no images are provided, use CSS shapes, plain blocks, local SVGs, or Element Plus icons only when they can be delivered with the page.
- Public introduction, product, and solution landing pages should usually include `<Footer />`; workflow tools and modal-like pages usually should not.
- Treat circuit visualization as data display, not decoration. Do not add decorative gradients, random images, or extra animation around the QCIS graph.

# EgoVault — Brand Charter

> Pixel art meets personal knowledge. Sober greens, one warm accent, one mark.

---

## Identity

**Tagline.** *Long-term memory for you and your LLM.*

**What we are.** A local, deterministic knowledge vault. The LLM is an optional passenger, never the driver.

**Tone.** Direct, technical, low-drama. No marketing fluff. Sentences short. Claims backed by code.

---

## Logo

The mark is a **pixel-art bust with a gold key inserted through a keyhole in the temple**. The bust is the user; the key is the personal access they own; the keyhole is the vault — the moment of unlocking is the product.

### Variants

| File | When to use |
|---|---|
| `docs/assets/logo.svg` | Light backgrounds (linen, white). Pine silhouette, gold key, black keyhole and key outline. |
| `docs/assets/logo-dark.svg` | Dark backgrounds (pine). Spring silhouette, gold key with 1px pine outline, pine keyhole as cutout. |
| `docs/assets/logo-mono.svg` | Single-color stamp (favicons, embossed prints). Pine everywhere, keyhole as linen cutout. |

### Grid and proportions

- Pixel grid: **36×33**. Never scale non-integer. Always render with `shape-rendering: crispEdges`.
- Minimum display size: **32 px** on the short side. Below that, switch to `logo-mono.svg`.
- Clearspace: at least 2 pixel-grid units on every side — never crop the key ring.

### Don'ts

- Never recolor the mark outside the palette below.
- Never add shadows, gradients, or bevels. The mark is flat on purpose.
- Never use the gold fill for anything else. Gold is the key only — scarcity makes it mean something.
- The dark-variant key carries a 1px **pine** outline — required for contrast against the spring silhouette. Pine on pine background disappears, so the "pop" survives where it matters.

---

## Palette

| Name | Hex | Role |
|---|---|---|
| **Pine** | `#0B4527` | Silhouette, frames, body text, dark backgrounds. |
| **Forest** | `#3C8A5F` | Secondary green. Links, section titles, muted accents. |
| **Spring** | `#8FE0A0` | Light accent. Silhouette fill on dark backgrounds, taglines. |
| **Linen** | `#F5F9F4` | Light backgrounds, surfaces, text on pine. |
| **Gold** | `#E8B830` | The key. Highlights only, never structural. |

Accessibility: pine on linen is ~AAA; spring on pine is ~AA large-text. Never run pine text on forest or spring on linen — both fail contrast.

---

## Typography

| Use | Font | Weight |
|---|---|---|
| Wordmark (banner) | PressStart2P (embedded base64, woff2) | 400 |
| Wordmark (inline / fallback) | IBM Plex Mono | 800 |
| Headings, body text (digital) | system sans (-apple-system, Segoe UI, Roboto) | 400–600 |
| Code, CLI, filenames | IBM Plex Mono / SF Mono / Consolas | 400 |
| Print (Typst exports) | Times New Roman + DejaVu Serif fallback | regular |

The mono wordmark is non-negotiable. The body font is pragmatic — whatever renders fastest on the user's machine.

---

## Voice

- **Say**: "local", "deterministic", "vault", "long-term memory", "capture friction".
- **Don't say**: "AI-powered", "smart", "magical", "revolutionary", "unlock your potential". The product is about *your* thinking, not ours.
- **Tagline must pair with a verb or a context** when not standalone. Example: *"Long-term memory for you and your LLM — every source kept, every note findable."*

---

## Banner

`docs/assets/banner.svg` — 900×280, pine background. Used at the top of `README.md` and for social previews. Logo on the left (dark variant), wordmark and tagline on the right. Never embed the banner with a different aspect ratio — crop the background, don't stretch the mark.

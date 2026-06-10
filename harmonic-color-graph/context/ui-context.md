# UI Context

## Theme

Harmonic Color Graph should feel like a focused music
intelligence workbench: technical, musical, responsive, and
playable. The UI should prioritize chord input, analysis
results, recommendation comparison, graph exploration, and
audio playback over marketing copy.

The default visual language is dark, high-contrast, and
studio-like, with restrained surfaces and vivid accents for
interactive harmonic states. Avoid generic SaaS hero pages
and decorative gradients. The first useful screen should be
the tool itself.

## Colors

Define these as CSS custom properties before building
substantial UI. Components should use tokens rather than
hardcoded hex values.

| Role                 | CSS Variable          | Value     |
| -------------------- | --------------------- | --------- |
| Page background      | `--bg-base`           | `#08090b` |
| Raised surface       | `--bg-surface`        | `#111318` |
| Subtle surface       | `--bg-subtle`         | `#191d24` |
| Primary text         | `--text-primary`      | `#f4f1e8` |
| Secondary text       | `--text-secondary`    | `#b7bdc8` |
| Muted text           | `--text-muted`        | `#777f8f` |
| Primary accent       | `--accent-primary`    | `#42e8b4` |
| Secondary accent     | `--accent-secondary`  | `#7aa7ff` |
| Warm color accent    | `--accent-warm`       | `#f2c86b` |
| Tension accent       | `--accent-tension`    | `#f05d8e` |
| Border               | `--border-default`    | `#2a303a` |
| Strong border        | `--border-strong`     | `#3e4654` |
| Error                | `--state-error`       | `#ff6b6b` |
| Success              | `--state-success`     | `#53d18a` |
| Warning              | `--state-warning`     | `#f2c86b` |

Use accent colors semantically:

- Green for valid analysis, resolved paths, and primary
  actions.
- Blue for selected graph context, similarity, and inspection.
- Warm gold for brightness, warmth, or high confidence.
- Rose for tension, surprise, warnings, or parse problems.

## Typography

| Role      | Font       | Variable              |
| --------- | ---------- | --------------------- |
| UI text   | Geist Sans | `--font-geist-sans`   |
| Code/mono | Geist Mono | `--font-geist-mono`   |

Use compact, scannable type in tool panels. Reserve large
display type for the product name or major empty states only.
Chord symbols and Roman numerals should use mono or
tabular-like styling when alignment matters.

## Border Radius

| Context           | Class target |
| ----------------- | ------------ |
| Inline controls   | `rounded-md` |
| Cards / panels    | `rounded-lg` |
| Modals / overlays | `rounded-lg` |
| Graph nodes       | circular or pill only when semantically useful |

Keep cards and panels at 8px radius or less unless a future
component library defines a stricter scale.

## Component Library

shadcn/ui is installed and configured through
`components.json` with Radix primitives, Lucide icons, RSC
support, TypeScript, Tailwind CSS v4, and CSS variables.
Generated primitives live in `components/ui/`; treat them as
owned source code, but keep changes intentional and aligned
with the design system.

## Layout Patterns

- **Phase 1 analysis workbench**: one primary chord input row,
  analysis output, transition relationships, next-chord
  candidates, and parse warnings.
- **Progression builder**: left input/intent panel, center
  progression path and playback controls, right analysis and
  recommendation panel.
- **Graph explorer**: full-width graph canvas with compact
  filter toolbar for genre, section, emotion, and complexity.
- **Comparison mode**: original progression plus two or three
  recommended variants, each with play controls, Roman
  numerals, color scores, and explanation.
- **Error states**: show parse problems inline near the chord
  they affect and preserve the user's original input.

## Controls

- Use text inputs or tokenized chord chips for progression
  entry.
- Use segmented controls for mode, view, and recommendation
  type.
- Use sliders for intent axes such as darker/brighter,
  common/surprising, simple/complex, resolved/unresolved.
- Use icon buttons for playback, pause, loop, reset, expand,
  and graph focus.
- Use compact tables or lists for transition statistics.

## Icons

Use Lucide React when installed. Prefer familiar icons for
playback, graph navigation, search, filters, reset, copy, and
download. Icon buttons should include accessible labels and
tooltips when the icon is not self-evident.

## Accessibility and Responsiveness

- Chord input, playback, recommendation selection, and graph
  filters must be keyboard reachable.
- Text must not overlap controls on mobile or desktop.
- Color scores must not rely on color alone; include labels
  and numeric values.
- Audio playback controls must expose current state clearly.

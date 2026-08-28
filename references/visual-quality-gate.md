# Visual Quality Gate

Venue compliance constrains visual design; it does not guarantee a readable or
professional paper. Judge beauty as disciplined clarity within the official
template, not as decorative customization.

## Page rhythm and hierarchy

- The title, abstract, headings, body, captions, tables, and references should
  have an obvious hierarchy without local font inventions.
- Density should be stable across neighboring pages. A dense wall followed by
  an avoidable half-empty page usually signals float, block, or allocation
  problems.
- Paragraphs should not be stretched to fill pages, and logical units should
  not be separated by unexplained blank bands.
- In two-column papers, balance column bottoms when the venue style expects it,
  but accept natural final-page or section-ending whitespace.
- Inspect ordinary-page bottoms and final-page balance as separate checks.
  Reject unexplained internal white bands before trying to equalize the bottom;
  a visually level bottom is not a valid repair if it is achieved by stretching
  a heading, list, equation, or caption gap.

## Figures

- Prefer vector PDF/SVG-to-PDF for plots and diagrams. Use PNG for sharp raster
  content and JPEG only for photographic content.
- Crop empty margins in the asset rather than compensating with negative TeX
  spacing.
- At final printed size, axes, legends, node labels, and annotations must remain
  readable. Inspect the rendered PDF, not only the source image at full size.
- Reuse colors and visual encodings consistently. Do not use color as the only
  distinction; add line style, marker, texture, or direct labels.
- Match font family and weight to the paper where feasible. Avoid screenshots
  of plots, UI chrome, or blurry rasterized text.
- A main figure should communicate one argument. Move secondary diagnostics to
  a panel, appendix, or separate figure rather than shrinking everything.

## Tables

- One-column tables target `\columnwidth`; two-column tables target
  `\textwidth`. A deliberately narrow semantic table may be centered with a
  recorded reason.
- Use booktabs-style top, header, and bottom rules unless the venue specifies a
  different convention. Avoid vertical rules and grid-like repeated lines.
- Allocate width by information density. Prose columns need room; numeric
  columns should align consistently and may use decimal alignment.
- Use the document font family and a readable size. Simplify, abbreviate, split,
  or move a table before using extreme scaling.
- Captions state the dataset/protocol, metric direction, uncertainty, and
  comparison boundary needed to interpret the values.

## Equations and algorithms

- Define symbols before or immediately after use. Keep related equations in one
  coherent alignment environment.
- Avoid clipped equation numbers, oversized delimiters, and displays that force
  large holes.
- Algorithm line numbers, comments, and mathematical symbols must remain
  readable at print scale. Do not shrink an algorithm below the surrounding
  table/caption readability level merely to save a page.

## Captions, links, and references

- Caption style and position follow the kit. Captions are compact but
  self-contained enough to identify what is shown and under which protocol.
- Hyperlinks should render without garish boxes unless the official style uses
  them. Review mode must not contain identifying project URLs when anonymity
  forbids them.
- Bibliography entries must not overflow columns. Long URLs and identifiers
  should break using venue-supported packages, not manual character insertion.

## Accessibility and print checks

- Inspect grayscale or low-saturation rendering for figures with color-coded
  claims.
- Provide alt-text/accessibility metadata when the venue or publisher requires
  it and the template supports it.
- Verify fonts are embedded and reject Type 3 fonts when the venue does.
- Inspect at 100% scale and a high-DPI render. A zoomed screenshot can hide
  unreadable print-size labels and exaggerate rule-weight differences.

## Acceptance record

For the exact final PDF, record:

| Area | Evidence |
|---|---|
| Template identity | Venue profile, official sources, kit hashes |
| Build health | Command, dependency manifest, log summary |
| PDF mechanics | Page size/count, metadata, fonts, audit JSON |
| Visual coverage | All pages or explicit inspected-page list |
| Figures/tables | Page and crop evidence at print scale |
| Change containment | Before/after changed-page list |
| Remaining warnings | Manual disposition and reason |

No automated score proves that the paper is beautiful. A final visual pass is a
human-judgment gate over the rendered artifact.

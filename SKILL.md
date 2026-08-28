---
name: paper-compile-layout-qa
description: Compile, generate, convert, and visually validate LaTeX conference papers against the current official author kit for the exact venue, year, track, and review/final mode. Use when a paper PDF must be both submission-compliant and publication-quality; do not use for prose-only editing or citation-only audits.
metadata:
  version: "1.2.0"
  last_updated: "2026-08-28"
---

# Paper Compile and Layout QA

Produce a reproducible PDF that follows the exact conference contract and looks
like a serious paper in that venue. A successful TeX exit is necessary but is
never evidence of venue compliance or visual readiness by itself.

## Venue-first contract

Before changing source or compiling, identify the exact:

- venue, year, track or paper type, and `review`, `final`, or `preprint` mode;
- official author-instructions page, official template/author kit, and any
  separate track or camera-ready instructions;
- canonical source, main `.tex`, bibliography, figures, style/class files,
  generator, build command, and expected PDF;
- page-limit semantics, anonymity mode, required sections/checklists,
  supplementary rules, paper size, columns, and font requirements;
- authorization boundary for format-only edits versus content compression.

Use the current official venue website and author kit as the authority. Search
the web when the exact current instructions are not already pinned locally.
Third-party Overleaf templates, prior-year repositories, accepted papers, and
blog posts are useful diagnostics but cannot establish compliance.

Create a project-level `venue-profile.json` before claiming compliance. Start
from [assets/venue-profile.template.json](assets/venue-profile.template.json)
and follow [references/conference-format-workflow.md](references/conference-format-workflow.md).
Every material rule must identify the official source that supports it. Record
the SHA-256 of local official style/class files when practical. Unknown or
conflicting requirements remain explicit blockers; do not guess from the
conference family or last year's template.

## Inter-skill handoff

This skill owns the official format contract, reproducible compilation,
source/PDF audit, rendered inspection, and layout fixes. It does not own the
scientific story or peer-review verdict.

- `$paper-submission-orchestrator` creates or maps the venue profile during
  intake, references its page-budget assumptions in the approved story packet,
  and freezes `venue-profile.json`, `format-audit.json`, `BUILD_RECEIPT.md`, and
  the exact PDF at review and final QA gates.
- `$academic-paper-reviewer` reads the rendered candidate and may report venue
  or readability concerns, but remains read-only and never changes templates.
- `$toppdf`, when available and the user authorizes prose work, may improve
  paper structure, compression, captions, and overall visual rhythm. This skill
  remains the authority for the actual author-kit configuration and build.

Input contract: canonical manuscript source, target venue identity, official
sources or local kit, build root, and requested mode. Output contract:
`venue-profile.json`, exact build command, compiled PDF, machine-readable
`format-audit.json`, render evidence, changed-page footprint, and remaining
manual or external blockers.

## Select and preserve the official template

1. Download or reuse the exact official kit for the selected year and track.
2. Compare it with the current project before migration: class/style names,
   mode switches, bibliography style, required sections, and build engine.
3. Move manuscript content through the template's supported hooks. Do not
   transplant geometry, heading, caption, line-spacing, or font overrides from
   a generic template.
4. Keep review, final, and preprint settings distinct. Never expose author
   identity in review mode or leave review rulers/line numbers in final mode.
5. If Markdown or code generates TeX, edit the real source and generator so the
   next build preserves the official template.

Do not edit an official `.cls` or `.sty` file to make content fit. If a local
kit file differs from its pinned hash, stop and determine whether the change is
an intentional official revision or an unauthorized local modification.

## Compile from the real submission root

1. Prefer the repository's documented build script or Makefile.
2. Otherwise use `latexmk`; then the appropriate LaTeX/BibTeX or Biber cycles;
   use Tectonic only when it is the established project workflow.
3. Preserve stdout/stderr and judge success by the exit code plus the expected
   PDF. Record the engine, command, style files, dependency manifest, page
   count, and log counts.
4. Require zero missing files and undefined citations/references. Review every
   overfull box against the rendered page.
5. Do not overwrite the last known-good final PDF until the candidate passes.

Run the deterministic preflight after building:

```powershell
python scripts/conference_format_audit.py `
  --profile .paper-workflow/venue-profile.json `
  --project-root . `
  --tex path/to/main.tex `
  --pdf path/to/paper.pdf `
  --log path/to/main.log `
  --output .paper-workflow/format-audit.json
```

Use `--source-only` before the first successful build. Use `--strict` only for
the final gate, after warnings have been manually disposed. The audit checks
profile provenance, pinned template files, dangerous source overrides, required
patterns/sections, total-page rules when mechanically knowable, PDF page size,
metadata anonymity, font embedding, Type 3 fonts, TeX vertical-box/float log
signals, manual spacing/break interventions, and heuristic PDF blank-band and
column-bottom geometry. Geometry findings identify pages to inspect; they
cannot determine whether excluded references or appendices begin on the correct
page, prove visual beauty, or replace venue-provided checkers.

## Render before diagnosing

Render the baseline at a fixed DPI and inspect every page for final delivery.
At minimum during iteration inspect:

- first page, title/author/abstract block, and anonymity state;
- every page containing figures, tables, dense equations, or long algorithms;
- section boundaries, bibliography start, appendix start, checklist/disclosure
  pages, and the final page;
- both column bottoms and all changed pages after a fix.

Classify a defect before editing: official-template mismatch, page-building
glue, unbreakable block, float queue, asset crop, local heading/list/equation
spacing, table geometry, font problem, or genuine end-of-section whitespace.
Treat ordinary-page bottom alignment and final-page column balancing as
separate venue rules. A source blank line is not proof of a rendered blank
band, and a level column bottom is not proof that spacing is healthy.
Read [references/latex-spacing-playbook.md](references/latex-spacing-playbook.md)
only when layout repair is needed. Read
[references/visual-quality-gate.md](references/visual-quality-gate.md) for
publication-quality figure, table, typography, density, and accessibility QA.

## Make the smallest owning-layer fix

- Preserve official template defaults. Never change global margins, base font,
  line spacing, heading macros, or column geometry to recover page budget.
- Prefer content prioritization, appendix movement, float placement, asset crop,
  table redesign, and breakability over negative `\vspace` or forced breaks.
- Keep one-column tables within `\columnwidth` and two-column tables within
  `\textwidth`; use semantic three-line rules and readable document-matched
  fonts. Simplify columns before shrinking.
- Prefer vector plots, tight bounding boxes, legible labels, consistent color
  semantics, and grayscale-safe distinctions.
- Treat beauty as constrained clarity: consistent hierarchy, balanced density,
  aligned edges, readable graphics, stable caption rhythm, and no unexplained
  holes. Do not cosmetically diverge from the venue style.
- A content edit made only to fit pages must remain claim-neutral unless the
  user explicitly authorizes scientific rewriting.

## Rebuild and prove containment

After each meaningful change:

1. rebuild from the same root and rerun the audit;
2. compare page count, logs, hashes, and audit findings;
3. render before and after at the same DPI;
4. list every changed page using
   [scripts/pdf_render_diff.py](scripts/pdf_render_diff.py);
5. inspect the target page, every changed page, and the following page when
   pagination moved;
6. revert or narrow avoidable unrelated cascades.

Never accept a target-page improvement that makes a later table, figure,
formula, bibliography, appendix, checklist, or author block worse.

## Final gate

Require all applicable items on the exact candidate:

- official sources are current, recorded, and sufficient for every material
  profile rule;
- official template, year, track, and review/final mode are correct;
- local template hashes match the approved kit;
- page-limit boundaries, paper size, margins, columns, anonymity, numbering,
  bibliography style, and required sections/checklists are correct;
- build and venue-provided checker outputs pass;
- `conference_format_audit.py --strict` passes or every remaining warning has
  an explicit manual disposition supported by rendered evidence;
- all fonts are embedded, no Type 3 font remains when prohibited, and PDF
  metadata does not leak identity in anonymous mode;
- figures, tables, captions, equations, links, algorithms, and headings are
  readable, aligned, unclipped, and visually consistent;
- every page has been visually inspected after the last build;
- source, profile, audit JSON, build receipt, render evidence, and PDF hashes
  describe the same build.

Report the official sources consulted, exact files changed, build command,
audit status, rendered pages inspected, changed-page footprint, and remaining
blockers. Never report only “compiled successfully” or “format fixed.”

---
name: paper-compile-layout-qa
description: Compile LaTeX conference papers locally and diagnose or fix rendered PDF layout, especially uneven page or column bottoms, unexplained blank bands, heading/list/equation spacing, and figure/table placement. Use for camera-ready compilation and iterative layout QA; do not trigger for prose-only editing or citation-only audits.
---

# Paper Compile and Layout QA

Produce a reproducible PDF whose layout follows the venue template and whose fixes are supported by rendered before/after evidence. A successful TeX exit is necessary but never sufficient.

## Establish the contract

Before editing, identify:

- target venue, year, track, and review/final/preprint mode;
- source of truth, main `.tex`, bibliography, style/class files, figures, and repository build command;
- page limit and whether references, limitations, acknowledgments, and appendices count;
- whether the request authorizes layout edits, content edits, or both.

When venue compliance is requested, verify the current official author instructions or local official kit. Preserve the official style defaults. Do not change the title, abstract, claims, numbers, citations, or author metadata merely to make a page fit unless the user explicitly authorizes content changes.

If the LaTeX file is generated from Markdown or another source, edit the real source or generator. Do not make a one-off generated-TeX fix that the next build will erase unless the user explicitly wants that.

## Compile from the real submission root

1. Prefer the repository's documented build script or Makefile.
2. Otherwise try `latexmk`; then the appropriate `pdflatex`/`bibtex` cycles; use Tectonic when it is the established local workflow.
3. Preserve stderr and judge success by the process exit code plus the expected PDF, not by warning-like PowerShell rendering alone.
4. Record the command, output PDF, page count, and log counts for undefined citations/references, missing files, overfull boxes, and meaningful underfull boxes.

Do not overwrite the user's last known-good final artifact until the revised build passes the final gate. Archive the source and PDF before material layout edits when the user values rollback or asks for change records.

## Render before diagnosing

Render the baseline PDF at a fixed DPI. Inspect the page named by the user and also:

- first page and author/abstract block;
- every page with dense equations, figures, or tables;
- section boundaries, bibliography start, appendix start, and last page;
- both column bottoms on two-column pages.

Classify each defect before editing:

- real paragraph break or explicit vertical space;
- stretched flexible glue caused by `\flushbottom`;
- unbreakable block such as a minipage, table, list, or kept paragraph;
- pending float, forced float barrier, or forced column/page break;
- excess whitespace inside the figure's own bounding box;
- heading/list/equation/table-cell spacing owned by that local construct;
- unavoidable residual space at the end of a section or document.

Do not infer the cause from blank lines in the `.tex` alone. A source blank line creates a paragraph; a large rendered band often comes from page building, floats, or flexible glue instead.

## Fix the owning layer

Use the smallest structural fix that addresses the diagnosed layer. Preserve unrelated layout and official template behavior.

- Prefer natural page building, float placement, block breakability, and content movement over arbitrary `\vspace`.
- Keep narrative paragraphs and their contribution/list block visually continuous. If residual column space is unavoidable, place it at the column bottom after the logical block rather than between related paragraphs.
- In two-column final papers, retain venue `\flushbottom` unless there is strong rendered evidence and venue permission for a different global policy. Never introduce global `\raggedbottom` to fix one page.
- Use `\vfill\newpage` only as a local, verified column-ending tool when the intended consequence is to move residual space to the bottom. In two-column mode, confirm it advances only the intended column and does not cascade later pages.
- Use minipages or same-page blocks only for short content that genuinely should not split. Re-render immediately because an unbreakable block can create a larger upstream gap.
- Fix figure whitespace by tightening the source graphic or crop box before adding negative spacing around the float.
- Fix table header alignment with column types, struts, row height, or cell padding rather than blank rows.
- Keep equation spacing near official defaults. Use a small local group around exceptional displays rather than redefining global skips for the entire paper.
- Do not patch global section-heading macros to repair one heading. Diagnose the neighboring float, list, paragraph, or page builder first.

For the ordered fix ladder and LaTeX patterns, read [references/latex-spacing-playbook.md](references/latex-spacing-playbook.md) only when layout changes are needed.

## Rebuild and prove containment

After each meaningful change:

1. Recompile from the same root.
2. Confirm page count and log findings.
3. Render before and after at the same DPI.
4. Identify every changed rendered page. Use [scripts/pdf_render_diff.py](scripts/pdf_render_diff.py) when Poppler is available.
5. Inspect the target page, every changed page, and the following page when pagination moved.
6. If unrelated pages changed, determine whether the cascade is necessary; otherwise revert or narrow the fix.

Do not accept a fix because the target screenshot improved while a figure, table, formula, bibliography, or appendix moved into a worse state.

## Final gate

Before reporting completion, require all applicable items:

- official template and final/review mode are correct;
- page size, margins, columns, page/ruler settings, and page limit are correct;
- build has no missing files, undefined references/citations, or visible overfull content;
- all required fonts are embedded when the venue requires it;
- figures, tables, captions, equations, lists, and headings are readable and not clipped;
- no unexplained blank band remains inside a logical narrative block;
- page/column bottoms are as balanced as the template and content reasonably allow;
- unavoidable end-of-section or last-page whitespace is not disguised with filler text;
- every page was visually inspected after the final build, or the uninspected scope is stated explicitly;
- rollback archive and final artifacts are synchronized when requested.

Report the exact layer changed, pages affected, build result, and any remaining intentional whitespace. Never say only “compiled successfully” or “format fixed.”

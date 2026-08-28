# LaTeX spacing playbook

Use this reference after rendered evidence identifies a layout defect. Apply the first suitable structural option; later options are progressively more local or manual.

## 1. Uneven two-column bottoms and stretched gaps

First distinguish:

- a small natural difference at the final page or before a forced break;
- a large gap created because `\flushbottom` stretched one of the few available vertical glues;
- an upstream gap created by an unbreakable block that no longer fits;
- a float that reserved or consumed the remaining column space.

Also distinguish **ordinary-page flush bottoms** from **final-page column
balancing**. `\flushbottom` and `\raggedbottom` control how TeX uses vertical
glue on pages; they are not universal substitutes for a venue's final-page
balancing mechanism. `acmart`, IEEEtran, and other conference families can
have different final-page rules. Preserve the exact author kit and venue
profile instead of copying a fix from another family.

Preferred order:

1. Let a short paragraph, list, or float break naturally if the logical structure permits it.
2. Reduce an unnecessarily unbreakable block.
3. Correct float placement or an overly strong `\FloatBarrier`.
4. Keep a short logical unit together only when splitting it would be visibly worse.
5. If the logical unit must remain intact and the residual space is unavoidable, end the column locally after that unit so the space appears at the bottom.

Useful local pattern, only after rendering proves it is appropriate:

```tex
\end{minipage}
\vfill
\newpage

\section{Next Section}
```

In two-column mode, `\newpage` normally advances to the next column. Verify the next section remains at the intended right-column top and compare all rendered pages. Do not generalize this pattern across the paper.

Avoid:

- global `\raggedbottom` for a single problem page;
- filler sentences added only to consume space;
- repeated negative `\vspace` near page boundaries;
- manual line breaks whose only purpose is pagination;
- forcing both bottoms to match when doing so creates a large mid-column hole.

Treat `Underfull \vbox` in the build log as a lead: it often accompanies a
page that lacks enough acceptable stretch, but only the render shows which
heading, list, display, float, or paragraph gap absorbed the stretch. Do not
silence the warning before locating the visible owner.

## 2. Unexplained blank band between paragraphs

Inspect the source immediately before and after the gap and ask:

- Is there a paragraph break, `\vspace`, `\smallskip`, `\medskip`, `\bigskip`, `\vfill`, or forced break?
- Does a nearby list, minipage, `samepage`, table, equation, or heading refuse to split?
- Did `\flushbottom` stretch `\parskip`, list `topsep`, display math skips, or heading skips?
- Is a float or `\FloatBarrier` changing the page builder's choices?

If the gap migrates when one local space is removed, it is usually flexible-glue stretch rather than the literal blank line that was removed. Give TeX a better place for residual space instead of repeatedly deleting normal paragraph separation.

In ordinary LaTeX prose, one or several source blank lines both end the current
paragraph; they do not request a proportional stack of blank rendered lines.
An empty line before a list can still activate list separation such as
`\partopsep`, so inspect the owning environment rather than counting blank
source lines.

## 3. Contribution lists and compact enumerations

Keep the introduction-to-contribution transition continuous. A compact list may use local `enumitem` settings:

```tex
\begin{enumerate}[topsep=2pt,partopsep=0pt,itemsep=0pt,parsep=0pt]
  \item ...
\end{enumerate}
```

Use values as examples, not universal constants. Inspect the rendered heading-to-item gap and line leading. A minipage can prevent a heading from separating from item 1, but it also makes the whole block unbreakable; use it only when the full block comfortably fits.

## 4. Equations

Start with the official style defaults. Diagnose separately:

- inline math baseline or oversized symbols;
- space above a display;
- space below a display;
- multiple displays that should be one `aligned`, `gathered`, or `align` block;
- equation width or number collision;
- page-builder stretch around displays.

For a genuine local exception, group skip changes so they do not affect later equations:

```tex
{%
  \setlength{\abovedisplayskip}{5pt plus 1pt minus 2pt}%
  \setlength{\belowdisplayskip}{5pt plus 1pt minus 2pt}%
  \begin{equation}
    ...
  \end{equation}
}
```

Keep stretch and shrink components unless there is a reason not to. Avoid large negative values and verify the preceding/following baselines, equation number, and both column bottoms.

## 5. Section and subsection headings

Official venue styles own heading font and nominal skips. If one heading looks too far from or too close to body text:

1. check whether a float ends directly above it;
2. check whether the first body object is a list, table, minipage, or display;
3. check forced page/column breaks;
4. check flexible-glue stretch;
5. only then consider a tightly scoped local correction.

Do not redefine `\section` or `\subsection` globally for one page. Never add an empty paragraph between a heading and its body.

## 6. Figures

Differentiate float spacing from whitespace inside the image:

- Open or render the source image/PDF and inspect its bounding box.
- Crop actual internal whitespace in the asset or use a verified `trim=...,clip` setting.
- Use venue-normal float placement such as `[t]`, `[tbp]`, or a justified `[!t]` before forcing manual breaks.
- Prefer moving a secondary figure to the appendix over extreme shrinking or negative spacing.

After any figure change, inspect label/legend readability at print size and grayscale interpretability when relevant.

## 7. Tables

For horizontal fit:

- one-column table: target `\columnwidth`;
- two-column table: use `table*` and target `\textwidth`;
- simplify columns before shrinking below readable font sizes;
- use `adjustbox` with `max width`, not unconditional distortion.

For vertical alignment:

- use `m{<width>}` columns for vertically centered wrapped cells;
- use `p{<width>}` when top alignment is intended;
- add a strut or small `\extrarowheight` for header breathing room;
- tune `\arraystretch` locally;
- do not insert blank rows to simulate padding.

Inspect table rules, multirow cells, the first/last row padding, caption gap, and both side margins in the rendered PDF.

## 8. Floats, barriers, and forced breaks

`\FloatBarrier`, `\clearpage`, `\newpage`, and `[H]` can all create large holes. Use them only when their placement semantics are intended.

- `\FloatBarrier`: keep earlier floats from crossing a meaningful boundary; remove or relocate if it strands a large region.
- `\clearpage`: flush all pending floats and start a page; usually appropriate before appendices only when the venue/package structure needs it.
- `\newpage`: end the current page or column without flushing all floats.
- `[H]`: make a float non-floating; use sparingly because it can create upstream gaps.
- `table*` or `figure*` with `[h]`: standard two-column output routines may not
  honor here-placement for a full-width float, so the float can be deferred and
  leave a visually surprising region. Start from the exact kit's supported
  full-width placement, commonly top placement, and verify the following page.

## 9. Verification matrix

For every spacing fix, record:

| Check | Required evidence |
| --- | --- |
| Target defect | Before/after render at the same DPI |
| Containment | List of changed rendered pages |
| Pagination | Page count and section/float boundary check |
| TeX health | Undefined, missing, overfull, and relevant underfull findings |
| Neighbor safety | Target page plus following page inspected |
| Final readiness | All pages visually inspected after the last build |

Treat a large last-page blank area as acceptable when the document genuinely ends there. Do not spread that space into preceding pages merely to make the last page look fuller.

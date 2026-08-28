# Conference Format Workflow

Use this reference when creating or refreshing `venue-profile.json`. It is an
evidence contract, not a static catalog of conference page limits.

## 1. Resolve the exact publication target

Identify all four dimensions before selecting a template:

1. venue and year;
2. track or paper type;
3. review, rebuttal, final/camera-ready, or preprint mode;
4. source format and publication family.

Do not collapse tracks. Main, findings, industry, dataset/benchmark, position,
short-paper, demo, workshop, and journal-to-conference tracks can differ in page
limits, anonymity, required sections, and supplementary rules even when they
share a style file.

## 2. Apply source precedence

Use the first available source at each level and record every source in the
profile:

1. exact-year, exact-track official author or camera-ready instructions;
2. exact official author kit or template archive and its bundled instructions;
3. official publisher instructions explicitly incorporated by the venue;
4. official submission form or official venue checker;
5. prior-year official instructions only as a clearly labeled fallback.

An official general template does not override a venue's track-specific
instructions. A venue page can in turn defer typography details to the bundled
kit. When sources conflict, record the conflict, prefer the more specific and
more recently updated official source, and keep strict compliance blocked until
the choice is defensible.

For every `official_sources[]` entry, list the profile fields it supports. A URL
that merely names the conference does not support page-limit or mode rules.

## 3. Download and pin the kit

- Preserve the original archive or a clean official checkout when practical.
- Record the source URL, retrieval date, release/version/commit if available,
  and SHA-256 for every required local `.cls`, `.sty`, `.bst`, or template file.
- Keep official files separate from local macros. Do not edit the kit in place.
- If an existing project uses a prior-year kit, migrate through a source diff;
  do not rename the old style file and assume equivalence.
- Run the sample paper from the kit once. A sample that does not build indicates
  an environment or kit problem, not a manuscript-layout problem.

## 4. Fill the venue profile

Start from `assets/venue-profile.template.json`. Complete:

- identity: venue, year, track, mode, verification date;
- official sources and the rule fields each source supports;
- template family, required files/hashes, and source signatures for the mode;
- page policy: main-text limit and whether references, appendices, checklists,
  ethics, limitations, or acknowledgments count;
- PDF contract: paper size, columns, embedded fonts, and Type 3 policy;
- layout contract: ordinary-page bottom behavior, final-page column policy,
  manual-spacing/break policy, and any pages excluded from the geometry probe;
- anonymity and PDF metadata policy;
- required sections and any venue-provided checker command.

Use `total_pdf_limit` only when the entire submitted PDF is capped. If
references or appendices are excluded, leave it `null` and verify the boundary
manually from the rendered PDF. Automated total page count cannot infer the
venue's semantic page boundary.

`required_tex_patterns` and `forbidden_tex_patterns` are regular expressions
over the comment-stripped combined TeX source. Use them for kit-supported mode
switches, not for brittle sentence wording.

## 5. Separate blank space from bottom alignment

Do not treat every white region as an empty line, and do not treat every unequal
column bottom as a defect. Record the exact venue policy in `layout_rules`:

- `body_bottoms` concerns ordinary full pages. `flush` allows TeX to stretch
  vertical glue so columns reach a common bottom; `ragged` keeps natural block
  height; `template-controlled` leaves the official class/style in charge.
- `final_page_columns` is separate. `balanced` means the venue wants the final
  two columns coarsely equalized; `natural` permits the document to end in the
  left or a shorter right column; `template-controlled` preserves the kit.
- `manual_vertical_spacing`, `forced_page_breaks`, and `blank_bands` decide
  whether the audit allows, reports, or rejects those interventions/candidates.
- `ignore_pages` is not a suppression list for convenience. Add a page only
  after rendering proves that a legitimate full-width figure, references,
  appendix boundary, checklist, or genuine document ending confuses the
  heuristic probe.

The distinction matters in real venue families. LaTeX's `\flushbottom`
stretches available vertical space and can surface `Underfull \vbox` warnings;
`\raggedbottom` leaves natural bottoms. Current `acmart` has its own last-page
`balance` behavior, while IEEE guidance asks for coarse last-page equalization.
ACL instead requires authors to preserve the official style; do not infer an
ACM or IEEE balancing rule for an ACL-family paper.

Useful primary or package-authoritative references:

- LaTeX layout, floats, page breaks, and vertical space:
  <https://tug.ctan.org/info/latex2e-help-texinfo/latex2e.html>;
- current `acmart` class guide and its `balance`/`pbalance` options:
  <https://www.tug.org/docs/latex/acmart/acmguide.pdf>;
- IEEEtran last-page column equalization guidance:
  <https://www.ewh.ieee.org/conf/holm/res/IEEEtran_HOWTO.pdf>;
- ACL official style and formatting constraints:
  <https://github.com/acl-org/acl-style-files> and
  <https://acl-org.github.io/ACLPUB/formatting.html>;
- `flushend` and `pbalance` package behavior, only when the venue permits them:
  <https://ctan.org/pkg/flushend> and <https://ctan.org/pkg/pbalance>.

Multiple source blank lines normally express paragraph structure, not a fixed
rendered gap. A large rendered band more often comes from stretchable glue, an
unbreakable block, a float queue/barrier, a forced page/column break, or explicit
vertical space. Diagnose from the log plus the rendered page before editing.

## 6. Recognize families without assuming rules

These signatures help locate the correct instructions; they are not universal
mode settings:

| Family | Common source signature | Frequent failure |
|---|---|---|
| ACL/ARR | `acl.sty` and ACL anthology bibliography style | wrong long/short or review/final option; missing limitations/ethics handling |
| NeurIPS | year-specific `neurips_YYYY.sty` | missing checklist; wrong final/preprint option |
| ICML | year-specific `icmlYYYY.sty` | leaving review mode for camera-ready or exposing authors in review |
| ICLR | year-specific ICLR conference style | wrong review/final switch or stale page limit |
| CVF/CVPR | year-specific CVPR kit | wrong review/final switch, missing anonymization, old style files |
| ACM | `acmart` with a venue-chosen class option | assuming every ACM venue wants the same `sigconf`/`manuscript` options |
| AAAI | year-specific AAAI author kit | old author kit, unauthorized formatting changes, wrong appendix policy |
| IEEE | `IEEEtran` or venue-supplied IEEE kit | using a generic IEEE template instead of the event-specific instructions |

## 7. Current official examples that motivate the profile

The following official 2026 instructions were checked on 2026-08-28. Recheck
them for later years or changed tracks.

- ACL 2026 main papers defer to ARR and distinguish long/short review limits
  from the additional final-version content page:
  <https://2026.aclweb.org/calls/main_conference_papers/>.
- NeurIPS requires the official style and paper checklist, and its tracks can
  have different calls: <https://neurips.cc/Conferences/2026/CallForPapers> and
  <https://neurips.cc/public/guides/PaperChecklist>.
- ICLR 2026 allows 9 pages of main text at submission and 10 during discussion
  and camera-ready, with references excluded:
  <https://iclr.cc/Conferences/2026/AuthorGuide>.
- ICML 2026's official kit specifies US Letter geometry and switches the style
  to `accepted` for camera-ready:
  <https://media.icml.cc/Conferences/ICML2026/Styles/example_paper.pdf>.
- CVPR 2026 requires the official CVPR style, anonymous review submission, and
  limits the paper body while excluding reference-only pages:
  <https://cvpr.thecvf.com/Conferences/2026/AuthorGuidelines>.
- The Web Conference 2026 uses ACM formatting, but requirements vary by track;
  research relevance is also required on the first page:
  <https://www2026.thewebconf.org/calls/research-tracks.html>.
- AAAI-26 requires its year-specific two-column author kit:
  <https://aaai.org/conference/aaai/aaai-26/submission-instructions/>.

These examples must not be copied into a later profile without current official
verification.

## 8. Conversion and generation strategy

- Existing correct venue source: preserve it and work in place.
- Prior-year venue source: diff template interfaces, migrate content, rebuild
  with the new sample, and remove stale mode switches.
- Generic LaTeX: start from the official sample, move semantic content and
  macros selectively, then rebuild.
- Markdown/Pandoc: keep Markdown canonical, use a venue-specific template, and
  inspect generated TeX. Use raw LaTeX fragments only for constructs Pandoc
  cannot express reliably.
- Word-only source: use the official Word template when supported. Do not claim
  LaTeX source compliance after a lossy conversion.

The generated PDF must come from the canonical path that future revisions will
rebuild. A one-off TeX export is not a maintainable camera-ready workflow.

## 9. Evidence returned to the orchestrator

Return:

- `venue-profile.json` path and SHA-256;
- official source list and unresolved conflicts;
- exact template file paths and hashes;
- exact build command and dependency manifest;
- exact `.log` path/hash and vertical-box/float diagnostic counts;
- `format-audit.json` path, SHA-256, and status;
- PDF path, SHA-256, page count, and page-boundary disposition;
- per-page blank-band candidates, column-bottom deltas, and their rendered
  dispositions when `layout_rules` enables the geometry probe;
- venue-provided checker command/result when one exists;
- render location, pages inspected, changed pages, and manual warning
  dispositions.

The orchestrator may freeze these artifacts at `REVIEWABLE` and `RE_REVIEW`.
Any profile, source, template, audit, or PDF change invalidates the corresponding
package sign-off.

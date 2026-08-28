# Paper Compile & Layout QA

A Codex skill for venue-aware LaTeX conference-paper generation, reproducible
compilation, deterministic format auditing, and rendered-PDF visual QA. It
builds a sourced profile for the exact venue/year/track/mode, pins official
template files, and treats a successful TeX exit as necessary but not
sufficient.

## Installation

The recommended installation is the complete paper-submission plugin:

<https://github.com/bystander563/paper-submission-suite>

For standalone use, clone this repository as
`$CODEX_HOME/skills/paper-compile-layout-qa` (or under the default
`.codex/skills` directory in the user profile), then start a new Codex task.

## Runtime requirements

- A repository-native LaTeX build command, `latexmk`, or Tectonic.
- Poppler's `pdfinfo`, `pdffonts`, and `pdftoppm` on `PATH`, in the bundled
  Codex runtime, or supplied explicitly to the audit/render scripts. The format
  audit falls back to PyMuPDF for page, metadata, and font checks when Poppler's
  inspection tools are unavailable. PyMuPDF also powers the optional two-column
  blank-band and bottom-geometry probe.

## Venue-aware use

Copy and fill `assets/venue-profile.template.json` from current official author
instructions, then run:

```powershell
python scripts/conference_format_audit.py `
  --profile .paper-workflow/venue-profile.json `
  --project-root . --tex paper/main.tex --pdf paper/main.pdf --log paper/main.log `
  --output .paper-workflow/format-audit.json
```

The audit distinguishes ordinary-page bottom policy from final-page column
balancing, reports manual vertical spacing and forced breaks, reads vertical-box
and float warnings from the LaTeX log, and records heuristic blank-band/bottom
geometry. It remains intentionally conservative: semantic page boundaries,
the cause of a whitespace candidate, and visual beauty require rendered
inspection.

## Validation

```powershell
python scripts/pdf_render_diff.py --help
python scripts/conference_format_audit.py --help
python scripts/test_conference_format_audit.py
```

## License

MIT. See [`LICENSE`](LICENSE).

# Paper Compile & Layout QA

A Codex skill for reproducible LaTeX conference-paper compilation and
rendered-PDF layout diagnosis. It treats a successful TeX exit as necessary but
not sufficient, compares rendered pages, and keeps fixes at the layer that owns
the defect.

## Installation

The recommended installation is the complete paper-submission plugin:

<https://github.com/bystander563/paper-submission-suite>

For standalone use, clone this repository as
`$CODEX_HOME/skills/paper-compile-layout-qa` (or under the default
`.codex/skills` directory in the user profile), then start a new Codex task.

## Runtime requirements

- A repository-native LaTeX build command, `latexmk`, or Tectonic.
- Poppler's `pdftoppm` on `PATH`, in the bundled Codex runtime, or supplied via
  `--pdftoppm` to `scripts/pdf_render_diff.py`.

## Validation

```powershell
python scripts/pdf_render_diff.py --help
```

## License

MIT. See [`LICENSE`](LICENSE).

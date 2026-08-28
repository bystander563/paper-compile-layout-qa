#!/usr/bin/env python3
"""Render two PDFs with Poppler and report which page images changed."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path


def find_pdftoppm(explicit: str | None) -> Path:
    if explicit:
        candidate = Path(explicit).expanduser().resolve()
        if candidate.is_file():
            return candidate
        raise FileNotFoundError(f"pdftoppm not found at: {candidate}")

    on_path = shutil.which("pdftoppm")
    if on_path:
        return Path(on_path).resolve()

    bundled = (
        Path.home()
        / ".cache"
        / "codex-runtimes"
        / "codex-primary-runtime"
        / "dependencies"
        / "native"
        / "poppler"
        / "Library"
        / "bin"
        / "pdftoppm.exe"
    )
    if bundled.is_file():
        return bundled

    raise FileNotFoundError(
        "pdftoppm was not found on PATH or in the bundled Codex Poppler runtime. "
        "Pass --pdftoppm with its full path."
    )


def ensure_empty_output(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise FileExistsError(f"output directory is not empty: {path}")
    path.mkdir(parents=True, exist_ok=True)


def render(executable: Path, pdf: Path, output_dir: Path, dpi: int) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = output_dir / "page"
    subprocess.run(
        [str(executable), "-png", "-r", str(dpi), str(pdf), str(prefix)],
        check=True,
    )
    return sorted(output_dir.glob("page-*.png"))


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def page_number(path: Path) -> int:
    return int(path.stem.rsplit("-", 1)[1])


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render before/after PDFs at the same DPI and list changed pages."
    )
    parser.add_argument("before_pdf", type=Path)
    parser.add_argument("after_pdf", type=Path)
    parser.add_argument("--dpi", type=int, default=110)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--pdftoppm")
    args = parser.parse_args()

    before_pdf = args.before_pdf.expanduser().resolve()
    after_pdf = args.after_pdf.expanduser().resolve()
    for pdf in (before_pdf, after_pdf):
        if not pdf.is_file():
            parser.error(f"PDF not found: {pdf}")
    if args.dpi <= 0:
        parser.error("--dpi must be positive")

    executable = find_pdftoppm(args.pdftoppm)
    if args.output_dir:
        root = args.output_dir.expanduser().resolve()
        ensure_empty_output(root)
    else:
        root = Path(tempfile.mkdtemp(prefix="paper_pdf_diff_"))

    before_pages = render(executable, before_pdf, root / "before", args.dpi)
    after_pages = render(executable, after_pdf, root / "after", args.dpi)
    before_hashes = {page_number(p): digest(p) for p in before_pages}
    after_hashes = {page_number(p): digest(p) for p in after_pages}
    all_pages = sorted(set(before_hashes) | set(after_hashes))
    changed = [p for p in all_pages if before_hashes.get(p) != after_hashes.get(p)]

    print(f"pdftoppm={executable}")
    print(f"output_dir={root}")
    print(f"before_pages={len(before_pages)}")
    print(f"after_pages={len(after_pages)}")
    print("changed_pages=" + (",".join(map(str, changed)) if changed else "none"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

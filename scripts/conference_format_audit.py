#!/usr/bin/env python3
"""Audit a LaTeX/PDF candidate against a project venue profile.

The tool deliberately checks only mechanically defensible properties. It does
not infer semantic page boundaries or visual quality from source alone.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any


@dataclass
class Finding:
    level: str
    code: str
    message: str
    evidence: str = ""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def add(findings: list[Finding], level: str, code: str, message: str, evidence: str = "") -> None:
    findings.append(Finding(level, code, message, evidence))


def load_profile(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read venue profile: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("venue profile root must be a JSON object")
    return data


def validate_profile(profile: dict[str, Any], findings: list[Finding]) -> None:
    required = (
        "profile_version",
        "venue",
        "year",
        "track",
        "mode",
        "verified_at",
        "official_sources",
        "template",
        "page_policy",
        "pdf",
        "mode_rules",
        "content_rules",
        "venue_checker",
    )
    for key in required:
        if key not in profile:
            add(findings, "ERROR", "PROFILE_MISSING_FIELD", f"missing profile field: {key}")

    serialized = json.dumps(profile, ensure_ascii=False)
    if "REPLACE_WITH" in serialized or "YYYY-MM-DD" in serialized:
        add(findings, "ERROR", "PROFILE_PLACEHOLDER", "venue profile still contains template placeholders")

    if profile.get("profile_version") != 1:
        add(findings, "ERROR", "PROFILE_VERSION", "profile_version must be 1")
    if profile.get("mode") not in {"review", "rebuttal", "final", "preprint"}:
        add(findings, "ERROR", "PROFILE_MODE", "mode must be review, rebuttal, final, or preprint")
    if not isinstance(profile.get("year"), int) or profile.get("year", 0) < 2000:
        add(findings, "ERROR", "PROFILE_YEAR", "year must be an integer >= 2000")
    try:
        date.fromisoformat(str(profile.get("verified_at", "")))
    except ValueError:
        add(findings, "ERROR", "PROFILE_DATE", "verified_at must be an ISO date")

    sources = profile.get("official_sources")
    supported: set[str] = set()
    if not isinstance(sources, list) or not sources:
        add(findings, "ERROR", "PROFILE_SOURCES", "at least one official source is required")
    else:
        for index, source in enumerate(sources, 1):
            if not isinstance(source, dict):
                add(findings, "ERROR", "PROFILE_SOURCE", f"official source {index} must be an object")
                continue
            url = str(source.get("url", ""))
            title = str(source.get("title", "")).strip()
            supports = source.get("supports")
            if not title or not url.startswith("https://"):
                add(findings, "ERROR", "PROFILE_SOURCE", f"official source {index} needs a title and HTTPS URL")
            try:
                date.fromisoformat(str(source.get("accessed", "")))
            except ValueError:
                add(findings, "ERROR", "PROFILE_SOURCE_DATE", f"official source {index} has an invalid accessed date")
            if not isinstance(supports, list) or not supports:
                add(findings, "ERROR", "PROFILE_SOURCE_SUPPORT", f"official source {index} must identify supported rules")
            else:
                supported.update(str(item) for item in supports)

    for rule in ("template", "page_policy", "mode_rules", "pdf"):
        if rule not in supported:
            add(
                findings,
                "ERROR",
                "PROFILE_UNSOURCED_RULE",
                f"no official source declares support for {rule}",
            )

    layout_rules = profile.get("layout_rules")
    if layout_rules is not None:
        if "layout_rules" not in supported:
            add(
                findings,
                "ERROR",
                "PROFILE_UNSOURCED_RULE",
                "no official source declares support for layout_rules",
            )
        if not isinstance(layout_rules, dict):
            add(findings, "ERROR", "PROFILE_LAYOUT_RULES", "layout_rules must be an object")
        else:
            allowed = {
                "body_bottoms": {"template-controlled", "flush", "ragged"},
                "final_page_columns": {"template-controlled", "balanced", "natural"},
                "manual_vertical_spacing": {"review", "forbid", "allow"},
                "forced_page_breaks": {"review", "forbid", "allow"},
                "blank_bands": {"review", "forbid", "allow"},
            }
            for field, values in allowed.items():
                if layout_rules.get(field) not in values:
                    add(
                        findings,
                        "ERROR",
                        "PROFILE_LAYOUT_RULES",
                        f"layout_rules.{field} must be one of: {', '.join(sorted(values))}",
                    )
            for field in ("column_bottom_tolerance_pt", "blank_band_min_pt"):
                value = layout_rules.get(field)
                if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
                    add(
                        findings,
                        "ERROR",
                        "PROFILE_LAYOUT_RULES",
                        f"layout_rules.{field} must be a positive number",
                    )
            if not isinstance(layout_rules.get("log_required"), bool):
                add(
                    findings,
                    "ERROR",
                    "PROFILE_LAYOUT_RULES",
                    "layout_rules.log_required must be boolean",
                )
            ignore_pages = layout_rules.get("ignore_pages")
            if not isinstance(ignore_pages, list) or any(
                not isinstance(page, int) or isinstance(page, bool) or page < 1 for page in ignore_pages
            ):
                add(
                    findings,
                    "ERROR",
                    "PROFILE_LAYOUT_RULES",
                    "layout_rules.ignore_pages must contain positive page numbers",
                )

    template = profile.get("template")
    if not isinstance(template, dict):
        add(findings, "ERROR", "PROFILE_TEMPLATE", "template must be an object")
    else:
        files = template.get("files")
        if not isinstance(files, list) or not files:
            add(findings, "ERROR", "PROFILE_TEMPLATE_FILES", "template.files must list at least one kit file")
        for field in ("required_tex_patterns", "forbidden_tex_patterns"):
            if not isinstance(template.get(field), list):
                add(findings, "ERROR", "PROFILE_TEMPLATE_PATTERNS", f"template.{field} must be an array")

    checker = profile.get("venue_checker")
    if isinstance(checker, dict) and checker.get("required"):
        if not str(checker.get("command", "")).strip():
            add(findings, "ERROR", "VENUE_CHECKER_COMMAND", "required venue checker has no recorded command")
        result = checker.get("result", "NOT_RUN")
        if result != "PASS":
            add(findings, "ERROR", "VENUE_CHECKER_RESULT", f"required venue checker result is {result}")
        if not str(checker.get("evidence", "")).strip():
            add(findings, "ERROR", "VENUE_CHECKER_EVIDENCE", "required venue checker has no result evidence")


def safe_project_path(project_root: Path, relative: str) -> Path | None:
    candidate = (project_root / relative).resolve()
    try:
        candidate.relative_to(project_root)
    except ValueError:
        return None
    return candidate


def audit_template_files(
    profile: dict[str, Any], project_root: Path, findings: list[Finding]
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    template = profile.get("template")
    if not isinstance(template, dict):
        return records
    files = template.get("files")
    if not isinstance(files, list):
        return records
    for entry in files:
        if not isinstance(entry, dict):
            add(findings, "ERROR", "TEMPLATE_ENTRY", "template file entry must be an object")
            continue
        relative = str(entry.get("path", ""))
        expected = str(entry.get("sha256", "")).lower()
        required = bool(entry.get("required", True))
        path = safe_project_path(project_root, relative)
        record: dict[str, Any] = {"path": relative, "required": required, "exists": False}
        if path is None:
            add(findings, "ERROR", "TEMPLATE_PATH_ESCAPE", f"template path leaves project root: {relative}")
            records.append(record)
            continue
        if not path.is_file():
            level = "ERROR" if required else "WARNING"
            add(findings, level, "TEMPLATE_FILE_MISSING", f"template file not found: {relative}")
            records.append(record)
            continue
        actual = sha256(path)
        record.update({"exists": True, "sha256": actual})
        if expected:
            if not re.fullmatch(r"[0-9a-f]{64}", expected):
                add(findings, "ERROR", "TEMPLATE_HASH_FORMAT", f"invalid SHA-256 for {relative}")
            elif actual != expected:
                add(findings, "ERROR", "TEMPLATE_HASH_MISMATCH", f"template hash differs: {relative}", actual)
        else:
            add(findings, "WARNING", "TEMPLATE_HASH_UNPINNED", f"template file is not hash-pinned: {relative}", actual)
        records.append(record)
    return records


def strip_comments(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        match = re.search(r"(?<!\\)%", line)
        lines.append(line[: match.start()] if match else line)
    return "\n".join(lines)


def collect_tex(main_tex: Path, project_root: Path, findings: list[Finding]) -> tuple[str, list[Path]]:
    pending = [main_tex]
    seen: set[Path] = set()
    chunks: list[str] = []
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        seen.add(path)
        try:
            path.relative_to(project_root)
        except ValueError:
            add(findings, "ERROR", "TEX_PATH_ESCAPE", f"TeX input leaves project root: {path}")
            continue
        if not path.is_file():
            add(findings, "ERROR", "TEX_FILE_MISSING", f"TeX file not found: {path}")
            continue
        text = strip_comments(path.read_text(encoding="utf-8", errors="replace"))
        chunks.append(f"\n% FILE: {path.relative_to(project_root)}\n{text}")
        for raw in re.findall(r"\\(?:input|include)\s*\{([^}]+)\}", text):
            if "\\" in raw or "#" in raw:
                add(findings, "WARNING", "TEX_DYNAMIC_INPUT", f"dynamic TeX input needs manual review: {raw}")
                continue
            candidate = (path.parent / raw).resolve()
            if not candidate.suffix:
                candidate = candidate.with_suffix(".tex")
            pending.append(candidate)
    return "\n".join(chunks), sorted(seen)


DANGEROUS_OVERRIDES: tuple[tuple[str, str], ...] = (
    (r"\\usepackage\s*(?:\[[^]]*\])?\s*\{geometry\}", "geometry package"),
    (r"\\geometry\s*\{", "geometry override"),
    (r"\\setlength\s*\{\\(?:textwidth|textheight|oddsidemargin|evensidemargin|topmargin|columnsep|baselineskip|parskip)\}", "global length override"),
    (r"\\(?:linespread|fontsize)\s*\{", "global font or leading override"),
    (r"\\renewcommand\s*\{\\baselinestretch\}", "global baseline stretch override"),
    (r"\\(?:titleformat|titlespacing)\b", "heading-format override"),
    (r"\\enlargethispage\b", "manual page enlargement"),
)

MANUAL_VERTICAL_SPACE = (
    r"\\vspace\*?\s*\{",
    r"\\(?:smallskip|medskip|bigskip|vfill)\b",
)

FORCED_PAGE_BREAKS = (
    r"\\(?:newpage|clearpage|cleardoublepage|pagebreak)\b",
    r"\\FloatBarrier\b",
    r"\\begin\s*\{(?:figure|table)\*?\}\s*\[\s*(?-i:H)\s*\]",
)

BOTTOM_CONTROLS = (
    r"\\(?:flushbottom|raggedbottom|balance|flushend)\b",
    r"\\usepackage\s*(?:\[[^]]*\])?\s*\{(?:balance|flushend|pbalance)\}",
)


def policy_finding_level(value: str) -> str | None:
    return {"forbid": "ERROR", "review": "WARNING", "allow": None}.get(value, "WARNING")


def audit_tex(profile: dict[str, Any], combined: str, findings: list[Finding]) -> None:
    template = profile.get("template", {})
    for pattern in template.get("required_tex_patterns", []) if isinstance(template, dict) else []:
        try:
            matched = re.search(pattern, combined, re.IGNORECASE | re.MULTILINE) is not None
        except re.error as exc:
            add(findings, "ERROR", "PROFILE_REGEX", f"invalid required TeX regex: {pattern}", str(exc))
            continue
        if not matched:
            add(findings, "ERROR", "TEX_REQUIRED_PATTERN", f"required TeX pattern not found: {pattern}")
    for pattern in template.get("forbidden_tex_patterns", []) if isinstance(template, dict) else []:
        try:
            matched = re.search(pattern, combined, re.IGNORECASE | re.MULTILINE) is not None
        except re.error as exc:
            add(findings, "ERROR", "PROFILE_REGEX", f"invalid forbidden TeX regex: {pattern}", str(exc))
            continue
        if matched:
            add(findings, "ERROR", "TEX_FORBIDDEN_PATTERN", f"forbidden TeX pattern found: {pattern}")

    for pattern, label in DANGEROUS_OVERRIDES:
        count = len(re.findall(pattern, combined, re.IGNORECASE | re.MULTILINE))
        if count:
            add(findings, "WARNING", "TEX_DANGEROUS_OVERRIDE", f"{label} requires official-kit justification", f"count={count}")

    manual_vspace = len(re.findall(r"\\vspace\*?\s*\{\s*-", combined))
    if manual_vspace:
        add(findings, "WARNING", "TEX_NEGATIVE_VSPACE", "negative vspace requires rendered containment evidence", f"count={manual_vspace}")

    layout_rules = profile.get("layout_rules", {})
    if isinstance(layout_rules, dict) and layout_rules:
        vertical_count = sum(
            len(re.findall(pattern, combined, re.IGNORECASE | re.MULTILINE))
            for pattern in MANUAL_VERTICAL_SPACE
        )
        vertical_level = policy_finding_level(str(layout_rules.get("manual_vertical_spacing", "review")))
        if vertical_count and vertical_level:
            add(
                findings,
                vertical_level,
                "TEX_MANUAL_VERTICAL_SPACE",
                "manual vertical spacing requires rendered, page-local justification",
                f"count={vertical_count}",
            )

        break_count = sum(
            len(re.findall(pattern, combined, re.IGNORECASE | re.MULTILINE))
            for pattern in FORCED_PAGE_BREAKS
        )
        break_level = policy_finding_level(str(layout_rules.get("forced_page_breaks", "review")))
        if break_count and break_level:
            add(
                findings,
                break_level,
                "TEX_FORCED_PAGE_BREAK",
                "forced page, column, float, or barrier placement needs rendered justification",
                f"count={break_count}",
            )

        wide_here_count = len(
            re.findall(
                r"\\begin\s*\{(?:figure|table)\*\}\s*\[[^]]*h[^]]*\]",
                combined,
                re.IGNORECASE | re.MULTILINE,
            )
        )
        if wide_here_count:
            add(
                findings,
                "WARNING",
                "TEX_WIDE_FLOAT_HERE",
                "two-column-wide float requests here-placement; standard output routines may defer it and create blank regions",
                f"count={wide_here_count}",
            )

        bottom_count = sum(
            len(re.findall(pattern, combined, re.IGNORECASE | re.MULTILINE))
            for pattern in BOTTOM_CONTROLS
        )
        if bottom_count:
            level = (
                "WARNING"
                if layout_rules.get("body_bottoms") == "template-controlled"
                and layout_rules.get("final_page_columns") == "template-controlled"
                else "INFO"
            )
            add(
                findings,
                level,
                "TEX_BOTTOM_CONTROL",
                "document-level bottom or final-column control is present; verify it matches the exact venue mode",
                f"count={bottom_count}",
            )

    rules = profile.get("content_rules", {})
    required_sections = rules.get("required_sections", []) if isinstance(rules, dict) else []
    headings = re.findall(r"\\(?:section|section\*|subsection|subsection\*)\s*\{([^}]*)\}", combined, re.IGNORECASE)
    normalized = "\n".join(headings)
    for section in required_sections:
        if str(section).casefold() not in normalized.casefold():
            add(findings, "ERROR", "TEX_REQUIRED_SECTION", f"required section not found: {section}")
    for pattern in rules.get("required_section_patterns", []) if isinstance(rules, dict) else []:
        try:
            matched = re.search(pattern, normalized, re.IGNORECASE) is not None
        except re.error as exc:
            add(findings, "ERROR", "PROFILE_REGEX", f"invalid section regex: {pattern}", str(exc))
            continue
        if not matched:
            add(findings, "ERROR", "TEX_REQUIRED_SECTION_PATTERN", f"required section pattern not found: {pattern}")
    for item in rules.get("manual_checks", []) if isinstance(rules, dict) else []:
        add(findings, "INFO", "MANUAL_CHECK", str(item))


def find_poppler(name: str, explicit: str | None) -> Path | None:
    if explicit:
        candidate = Path(explicit).expanduser().resolve()
        return candidate if candidate.is_file() else None
    on_path = shutil.which(name)
    if on_path:
        return Path(on_path).resolve()
    exe = name + (".exe" if sys.platform.startswith("win") else "")
    candidate = (
        Path.home()
        / ".cache"
        / "codex-runtimes"
        / "codex-primary-runtime"
        / "dependencies"
        / "native"
        / "poppler"
        / "Library"
        / "bin"
        / exe
    )
    return candidate if candidate.is_file() else None


def run_tool(executable: Path, pdf: Path) -> str:
    completed = subprocess.run(
        [str(executable), str(pdf)],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return completed.stdout


def parse_pdfinfo(text: str) -> dict[str, Any]:
    info: dict[str, Any] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        info[key.strip().lower().replace(" ", "_")] = value.strip()
    if "pages" in info:
        try:
            info["pages"] = int(str(info["pages"]))
        except ValueError:
            pass
    match = re.search(r"Page size:\s*([0-9.]+)\s*x\s*([0-9.]+)\s*pts", text, re.IGNORECASE)
    if match:
        info["page_width_pt"] = float(match.group(1))
        info["page_height_pt"] = float(match.group(2))
    return info


def expected_page_size(name: str) -> tuple[float, float] | None:
    return {"letter": (612.0, 792.0), "a4": (595.28, 841.89)}.get(name.lower())


def audit_fonts(text: str, profile: dict[str, Any], findings: list[Finding]) -> dict[str, int]:
    fonts = 0
    unembedded = 0
    type3 = 0
    for line in text.splitlines():
        if not line.strip() or line.lower().startswith("name") or set(line.strip()) == {"-"}:
            continue
        match = re.search(r"\s+(yes|no)\s+(yes|no)\s+(yes|no)\s+\d+\s+\d+\s*$", line, re.IGNORECASE)
        if not match:
            continue
        fonts += 1
        if match.group(1).lower() != "yes":
            unembedded += 1
        if re.search(r"\bType\s*3\b", line, re.IGNORECASE):
            type3 += 1
    pdf_rules = profile.get("pdf", {})
    if pdf_rules.get("fonts_must_be_embedded") and unembedded:
        add(findings, "ERROR", "PDF_FONT_UNEMBEDDED", "PDF contains unembedded fonts", f"count={unembedded}")
    if not pdf_rules.get("type3_fonts_allowed", False) and type3:
        add(findings, "ERROR", "PDF_FONT_TYPE3", "PDF contains prohibited Type 3 fonts", f"count={type3}")
    if not fonts:
        add(findings, "WARNING", "PDF_FONT_PARSE", "pdffonts returned no parseable font rows")
    return {"fonts": fonts, "unembedded": unembedded, "type3": type3}


def pymupdf_pdf_info(pdf: Path) -> dict[str, Any]:
    import fitz  # type: ignore

    document = fitz.open(pdf)
    info: dict[str, Any] = {"pages": document.page_count}
    metadata = document.metadata or {}
    if metadata.get("author"):
        info["author"] = metadata["author"]
    if document.page_count:
        rectangle = document[0].rect
        info["page_width_pt"] = float(rectangle.width)
        info["page_height_pt"] = float(rectangle.height)
    document.close()
    return info


def audit_fonts_pymupdf(
    pdf: Path, profile: dict[str, Any], findings: list[Finding]
) -> dict[str, int]:
    import fitz  # type: ignore

    document = fitz.open(pdf)
    seen: set[int] = set()
    fonts = 0
    unembedded = 0
    type3 = 0
    for page in document:
        for row in page.get_fonts(full=True):
            xref = int(row[0])
            if xref in seen:
                continue
            seen.add(xref)
            fonts += 1
            font_type = str(row[2])
            extracted = document.extract_font(xref)
            content = extracted[3] if len(extracted) >= 4 else b""
            if not content:
                unembedded += 1
            if re.search(r"\bType\s*3\b", font_type, re.IGNORECASE):
                type3 += 1
    document.close()
    pdf_rules = profile.get("pdf", {})
    if pdf_rules.get("fonts_must_be_embedded") and unembedded:
        add(findings, "ERROR", "PDF_FONT_UNEMBEDDED", "PDF contains unembedded fonts", f"count={unembedded}")
    if not pdf_rules.get("type3_fonts_allowed", False) and type3:
        add(findings, "ERROR", "PDF_FONT_TYPE3", "PDF contains prohibited Type 3 fonts", f"count={type3}")
    if not fonts:
        add(findings, "WARNING", "PDF_FONT_PARSE", "PyMuPDF found no fonts in the PDF")
    return {"fonts": fonts, "unembedded": unembedded, "type3": type3}


def merge_intervals(intervals: list[tuple[float, float]], join_gap_pt: float = 6.0) -> list[tuple[float, float]]:
    if not intervals:
        return []
    merged: list[tuple[float, float]] = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1] + join_gap_pt:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def largest_internal_gap(intervals: list[tuple[float, float]]) -> tuple[float, float, float] | None:
    merged = merge_intervals(intervals)
    if len(merged) < 2:
        return None
    gaps = [(merged[index][1], merged[index + 1][0]) for index in range(len(merged) - 1)]
    start, end = max(gaps, key=lambda pair: pair[1] - pair[0])
    return start, end, end - start


def page_layout_metrics(page: Any, page_number: int) -> dict[str, Any]:
    """Return heuristic body-column geometry from words, images, and vector drawings.

    The probe deliberately ignores the outer margin, header, and footer. It is
    evidence for rendered review, not a substitute for venue-specific layout
    semantics.
    """

    width = float(page.rect.width)
    height = float(page.rect.height)
    top = height * 0.06
    bottom = height * 0.93
    center = width / 2.0
    gutter = width * 0.025
    columns = {
        "left": (width * 0.05, center - gutter),
        "right": (center + gutter, width * 0.95),
    }
    items: list[tuple[float, float, float, float, str]] = []
    for word in page.get_text("words"):
        x0, y0, x1, y1 = (float(value) for value in word[:4])
        items.append((x0, y0, x1, y1, "word"))
    try:
        for image in page.get_image_info():
            x0, y0, x1, y1 = (float(value) for value in image["bbox"])
            items.append((x0, y0, x1, y1, "image"))
    except (KeyError, RuntimeError, TypeError, ValueError):
        pass
    try:
        for drawing in page.get_drawings():
            rectangle = drawing.get("rect")
            if rectangle is not None:
                items.append(
                    (
                        float(rectangle.x0),
                        float(rectangle.y0),
                        float(rectangle.x1),
                        float(rectangle.y1),
                        "drawing",
                    )
                )
    except (RuntimeError, TypeError, ValueError):
        pass

    result: dict[str, Any] = {"page": page_number, "width_pt": width, "height_pt": height}
    for name, (x_min, x_max) in columns.items():
        intervals: list[tuple[float, float]] = []
        words = 0
        for x0, y0, x1, y1, kind in items:
            if y1 < top or y0 > bottom:
                continue
            overlap = min(x1, x_max) - max(x0, x_min)
            if overlap <= 0:
                continue
            if kind == "word":
                center_x = (x0 + x1) / 2.0
                if not (x_min <= center_x <= x_max):
                    continue
                words += 1
            intervals.append((max(y0, top), min(y1, bottom)))
        merged = merge_intervals(intervals)
        gap = largest_internal_gap(merged)
        result[name] = {
            "word_count": words,
            "content_bottom_pt": max((end for _, end in merged), default=None),
            "largest_internal_blank_band": (
                {"start_pt": gap[0], "end_pt": gap[1], "height_pt": gap[2]} if gap else None
            ),
        }

    left_bottom = result["left"]["content_bottom_pt"]
    right_bottom = result["right"]["content_bottom_pt"]
    result["column_bottom_delta_pt"] = (
        abs(float(left_bottom) - float(right_bottom))
        if left_bottom is not None and right_bottom is not None
        else None
    )
    return result


def evaluate_layout_metrics(
    layout_rules: dict[str, Any], metrics: list[dict[str, Any]], findings: list[Finding]
) -> None:
    if not metrics:
        return
    tolerance = float(layout_rules.get("column_bottom_tolerance_pt", 18.0))
    blank_min = float(layout_rules.get("blank_band_min_pt", 48.0))
    ignored = {int(page) for page in layout_rules.get("ignore_pages", [])}
    blank_level = policy_finding_level(str(layout_rules.get("blank_bands", "review")))
    final_page = metrics[-1]["page"]

    for page in metrics:
        number = int(page["page"])
        if number in ignored:
            continue
        for column in ("left", "right"):
            gap = page[column].get("largest_internal_blank_band")
            if gap and float(gap["height_pt"]) >= blank_min and blank_level:
                add(
                    findings,
                    blank_level,
                    "PDF_BLANK_BAND_CANDIDATE",
                    f"page {number} {column} column contains a large internal blank band",
                    f"{gap['start_pt']:.1f}-{gap['end_pt']:.1f} pt; height={gap['height_pt']:.1f} pt",
                )

        left_words = int(page["left"].get("word_count", 0))
        right_words = int(page["right"].get("word_count", 0))
        delta = page.get("column_bottom_delta_pt")
        if number != final_page and layout_rules.get("body_bottoms") == "flush":
            if left_words >= 10 and right_words >= 10 and isinstance(delta, (int, float)) and delta > tolerance:
                add(
                    findings,
                    "WARNING",
                    "PDF_COLUMN_BOTTOM_DELTA",
                    f"page {number} column bottoms differ under a flush-bottom venue policy",
                    f"delta={delta:.1f} pt; tolerance={tolerance:.1f} pt",
                )

    if layout_rules.get("final_page_columns") == "balanced" and final_page not in ignored:
        page = metrics[-1]
        left_words = int(page["left"].get("word_count", 0))
        right_words = int(page["right"].get("word_count", 0))
        delta = page.get("column_bottom_delta_pt")
        if left_words >= 10 and right_words < 10:
            add(
                findings,
                "WARNING",
                "PDF_FINAL_COLUMN_UNBALANCED",
                "final page has substantial left-column content but little or no right-column content",
                f"left_words={left_words}; right_words={right_words}",
            )
        elif left_words >= 10 and right_words >= 10 and isinstance(delta, (int, float)) and delta > tolerance:
            add(
                findings,
                "WARNING",
                "PDF_FINAL_COLUMN_UNBALANCED",
                "final-page columns exceed the venue-profile balance tolerance",
                f"delta={delta:.1f} pt; tolerance={tolerance:.1f} pt",
            )


def audit_pdf_layout(
    pdf: Path, profile: dict[str, Any], findings: list[Finding]
) -> dict[str, Any]:
    layout_rules = profile.get("layout_rules")
    if not isinstance(layout_rules, dict) or not layout_rules:
        return {}
    if profile.get("pdf", {}).get("columns") != 2:
        return {"engine": "not-run", "reason": "column geometry probe currently targets two-column PDFs"}
    try:
        import fitz  # type: ignore
    except ImportError:
        add(
            findings,
            "WARNING",
            "PDF_LAYOUT_PROBE_UNAVAILABLE",
            "PyMuPDF is unavailable; inspect blank bands and column bottoms manually",
        )
        return {"engine": "unavailable"}

    try:
        document = fitz.open(pdf)
        metrics = [page_layout_metrics(page, index + 1) for index, page in enumerate(document)]
        document.close()
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        add(findings, "WARNING", "PDF_LAYOUT_PROBE_FAILED", "PDF layout geometry probe failed", str(exc))
        return {"engine": "failed", "error": str(exc)}
    evaluate_layout_metrics(layout_rules, metrics, findings)
    add(
        findings,
        "INFO",
        "PDF_LAYOUT_PROBE",
        "recorded heuristic blank-band and column-bottom geometry; rendered inspection remains required",
        f"pages={len(metrics)}",
    )
    return {
        "engine": "PyMuPDF heuristic",
        "parameters": {
            "column_bottom_tolerance_pt": layout_rules.get("column_bottom_tolerance_pt"),
            "blank_band_min_pt": layout_rules.get("blank_band_min_pt"),
            "ignore_pages": layout_rules.get("ignore_pages", []),
        },
        "pages": metrics,
    }


def audit_log(log: Path, findings: list[Finding]) -> dict[str, int]:
    if not log.is_file():
        add(findings, "ERROR", "LOG_MISSING", f"LaTeX log not found: {log}")
        return {}
    text = log.read_text(encoding="utf-8", errors="replace")
    counts = {
        "underfull_vbox": len(re.findall(r"Underfull \\vbox", text, re.IGNORECASE)),
        "overfull_vbox": len(re.findall(r"Overfull \\vbox", text, re.IGNORECASE)),
        "underfull_hbox": len(re.findall(r"Underfull \\hbox", text, re.IGNORECASE)),
        "float_too_large": len(re.findall(r"Float too large", text, re.IGNORECASE)),
        "unprocessed_floats": len(re.findall(r"Too many unprocessed floats", text, re.IGNORECASE)),
    }
    if counts["underfull_vbox"]:
        add(
            findings,
            "WARNING",
            "LOG_UNDERFULL_VBOX",
            "LaTeX reported underfull vertical boxes; inspect stretched gaps and page bottoms",
            f"count={counts['underfull_vbox']}",
        )
    if counts["overfull_vbox"]:
        add(
            findings,
            "ERROR",
            "LOG_OVERFULL_VBOX",
            "LaTeX reported overfull vertical boxes",
            f"count={counts['overfull_vbox']}",
        )
    if counts["float_too_large"] or counts["unprocessed_floats"]:
        add(
            findings,
            "ERROR",
            "LOG_FLOAT_FAILURE",
            "LaTeX reported an oversized or unprocessed float",
            f"too_large={counts['float_too_large']}; unprocessed={counts['unprocessed_floats']}",
        )
    return counts


def audit_pdf(
    profile: dict[str, Any],
    pdf: Path,
    findings: list[Finding],
    pdfinfo_arg: str | None,
    pdffonts_arg: str | None,
) -> tuple[dict[str, Any], dict[str, int], dict[str, Any]]:
    if not pdf.is_file():
        add(findings, "ERROR", "PDF_MISSING", f"PDF not found: {pdf}")
        return {}, {}, {}
    pdfinfo_exe = find_poppler("pdfinfo", pdfinfo_arg)
    pdffonts_exe = find_poppler("pdffonts", pdffonts_arg)
    info: dict[str, Any] = {}
    font_info: dict[str, int] = {}
    if pdfinfo_exe is None:
        try:
            info = pymupdf_pdf_info(pdf)
            add(findings, "INFO", "PDFINFO_FALLBACK", "used PyMuPDF for page and metadata audit")
        except ImportError:
            add(findings, "ERROR", "PDFINFO_MISSING", "pdfinfo or PyMuPDF is required for page and metadata audit")
        except (OSError, RuntimeError, ValueError) as exc:
            add(findings, "ERROR", "PDFINFO_FAILED", "PyMuPDF page/metadata audit failed", str(exc))
    else:
        try:
            info = parse_pdfinfo(run_tool(pdfinfo_exe, pdf))
        except (OSError, subprocess.CalledProcessError) as exc:
            add(findings, "ERROR", "PDFINFO_FAILED", "pdfinfo failed", str(exc))

    pages = info.get("pages")
    total_limit = profile.get("page_policy", {}).get("total_pdf_limit")
    if isinstance(total_limit, int) and isinstance(pages, int) and pages > total_limit:
        add(findings, "ERROR", "PDF_TOTAL_PAGE_LIMIT", f"PDF has {pages} pages; total limit is {total_limit}")
    main_limit = profile.get("page_policy", {}).get("main_page_limit")
    if isinstance(main_limit, int) and total_limit is None:
        add(findings, "INFO", "MANUAL_MAIN_PAGE_BOUNDARY", f"verify main content ends by page {main_limit}; excluded material cannot be inferred automatically")

    pdf_rules = profile.get("pdf", {})
    expected = expected_page_size(str(pdf_rules.get("paper_size", "")))
    width = info.get("page_width_pt")
    height = info.get("page_height_pt")
    if expected and isinstance(width, float) and isinstance(height, float):
        direct = abs(width - expected[0]) <= 4 and abs(height - expected[1]) <= 4
        rotated = abs(width - expected[1]) <= 4 and abs(height - expected[0]) <= 4
        if not (direct or rotated):
            add(findings, "ERROR", "PDF_PAGE_SIZE", f"PDF page size is {width:.2f} x {height:.2f} pt; expected {pdf_rules.get('paper_size')}")

    mode_rules = profile.get("mode_rules", {})
    author = str(info.get("author", "")).strip()
    if mode_rules.get("pdf_author_metadata") == "empty" and author and author.casefold() not in {"anonymous", "anonymous authors"}:
        add(findings, "ERROR", "PDF_AUTHOR_METADATA", "anonymous-mode PDF contains author metadata", author)

    if pdffonts_exe is None:
        try:
            font_info = audit_fonts_pymupdf(pdf, profile, findings)
            add(findings, "INFO", "PDFFONTS_FALLBACK", "used PyMuPDF for font embedding and Type 3 audit")
        except ImportError:
            if pdf_rules.get("fonts_must_be_embedded") or not pdf_rules.get("type3_fonts_allowed", False):
                add(findings, "ERROR", "PDFFONTS_MISSING", "pdffonts or PyMuPDF is required for the configured font audit")
        except (OSError, RuntimeError, ValueError) as exc:
            add(findings, "ERROR", "PDFFONTS_FAILED", "PyMuPDF font audit failed", str(exc))
    else:
        try:
            font_info = audit_fonts(run_tool(pdffonts_exe, pdf), profile, findings)
        except (OSError, subprocess.CalledProcessError) as exc:
            add(findings, "ERROR", "PDFFONTS_FAILED", "pdffonts failed", str(exc))
    layout_info = audit_pdf_layout(pdf, profile, findings)
    return info, font_info, layout_info


def status_for(findings: list[Finding]) -> str:
    if any(item.level == "ERROR" for item in findings):
        return "FAIL"
    if any(item.level == "WARNING" for item in findings):
        return "PASS_WITH_WARNINGS"
    return "PASS"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit a conference paper against a sourced venue profile.")
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--tex", required=True, type=Path)
    parser.add_argument("--pdf", type=Path)
    parser.add_argument("--source-only", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Return nonzero when warnings remain")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--log", type=Path, help="LaTeX build log for vertical-box and float diagnostics")
    parser.add_argument("--pdfinfo")
    parser.add_argument("--pdffonts")
    args = parser.parse_args()

    project_root = args.project_root.expanduser().resolve()
    profile_path = args.profile.expanduser().resolve()
    tex_path = args.tex.expanduser().resolve()
    findings: list[Finding] = []
    try:
        profile = load_profile(profile_path)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    validate_profile(profile, findings)
    template_files = audit_template_files(profile, project_root, findings)
    combined_tex, tex_files = collect_tex(tex_path, project_root, findings)
    audit_tex(profile, combined_tex, findings)

    pdf_info: dict[str, Any] = {}
    font_info: dict[str, int] = {}
    layout_info: dict[str, Any] = {}
    log_info: dict[str, int] = {}
    log_path: Path | None = None
    pdf_path: Path | None = None
    if args.source_only:
        add(findings, "INFO", "SOURCE_ONLY", "PDF mechanics and visual inspection were not run")
    elif args.pdf is None:
        add(findings, "ERROR", "PDF_ARGUMENT", "--pdf is required unless --source-only is used")
    else:
        pdf_path = args.pdf.expanduser().resolve()
        pdf_info, font_info, layout_info = audit_pdf(
            profile, pdf_path, findings, args.pdfinfo, args.pdffonts
        )

    if args.log is not None:
        log_path = args.log.expanduser().resolve()
        log_info = audit_log(log_path, findings)
    elif isinstance(profile.get("layout_rules"), dict) and profile["layout_rules"].get("log_required"):
        add(findings, "ERROR", "LOG_REQUIRED", "venue profile requires the LaTeX log; pass --log")

    status = status_for(findings)
    result = {
        "schema_version": 1,
        "status": status,
        "profile": {
            "path": str(profile_path),
            "sha256": sha256(profile_path),
            "venue": profile.get("venue"),
            "year": profile.get("year"),
            "track": profile.get("track"),
            "mode": profile.get("mode"),
            "verified_at": profile.get("verified_at"),
        },
        "project_root": str(project_root),
        "tex": {
            "main": str(tex_path),
            "main_sha256": sha256(tex_path) if tex_path.is_file() else None,
            "files": [str(path.relative_to(project_root)) for path in tex_files if path.is_file()],
        },
        "template_files": template_files,
        "pdf": {
            "path": str(pdf_path) if pdf_path else None,
            "sha256": sha256(pdf_path) if pdf_path and pdf_path.is_file() else None,
            "info": pdf_info,
            "fonts": font_info,
            "layout": layout_info,
        },
        "log": {
            "path": str(log_path) if log_path else None,
            "sha256": sha256(log_path) if log_path and log_path.is_file() else None,
            "counts": log_info,
        },
        "findings": [asdict(item) for item in findings],
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(f"status={status}")
    for item in findings:
        suffix = f" ({item.evidence})" if item.evidence else ""
        print(f"{item.level} {item.code}: {item.message}{suffix}")
    if any(item.level == "ERROR" for item in findings):
        return 1
    if args.strict and any(item.level == "WARNING" for item in findings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

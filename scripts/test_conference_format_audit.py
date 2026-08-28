#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("conference_format_audit.py")
SPEC = importlib.util.spec_from_file_location("conference_format_audit", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ConferenceFormatAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.style = self.root / "venue.sty"
        self.style.write_text("% official test style\n", encoding="utf-8")
        self.tex = self.root / "main.tex"
        self.tex.write_text(
            "\\documentclass{article}\n"
            "\\usepackage{venue}\n"
            "\\begin{document}\n"
            "\\section{Introduction}Text.\n"
            "\\section{Limitations}Limits.\n"
            "\\end{document}\n",
            encoding="utf-8",
        )
        self.profile = {
            "profile_version": 1,
            "venue": "TestConf",
            "year": 2026,
            "track": "main",
            "mode": "review",
            "verified_at": "2026-08-28",
            "official_sources": [
                {
                    "title": "Official author guide",
                    "url": "https://example.org/official",
                    "accessed": "2026-08-28",
                    "supports": [
                        "template",
                        "page_policy",
                        "mode_rules",
                        "pdf",
                        "required_sections",
                        "layout_rules",
                    ],
                }
            ],
            "template": {
                "family": "test",
                "files": [{"path": "venue.sty", "required": True, "sha256": digest(self.style)}],
                "required_tex_patterns": [r"\\usepackage\{venue\}"],
                "forbidden_tex_patterns": [r"\\usepackage\{oldvenue\}"],
            },
            "page_policy": {
                "main_page_limit": 8,
                "references_count": False,
                "appendix_count": False,
                "total_pdf_limit": None,
                "notes": "References excluded.",
            },
            "pdf": {
                "paper_size": "letter",
                "columns": 2,
                "fonts_must_be_embedded": True,
                "type3_fonts_allowed": False,
            },
            "mode_rules": {
                "anonymous": True,
                "pdf_author_metadata": "empty",
                "line_numbers": "required",
                "page_numbers": "venue-controlled",
            },
            "content_rules": {
                "required_sections": ["Limitations"],
                "required_section_patterns": [],
                "manual_checks": [],
            },
            "layout_rules": {
                "body_bottoms": "template-controlled",
                "final_page_columns": "template-controlled",
                "manual_vertical_spacing": "review",
                "forced_page_breaks": "review",
                "blank_bands": "review",
                "column_bottom_tolerance_pt": 18,
                "blank_band_min_pt": 48,
                "log_required": False,
                "ignore_pages": [],
            },
            "venue_checker": {"command": "", "required": False, "result": "NOT_RUN", "evidence": ""},
        }
        self.profile_path = self.root / "venue-profile.json"
        self.profile_path.write_text(json.dumps(self.profile), encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_valid_profile_has_no_errors(self) -> None:
        findings = []
        MODULE.validate_profile(self.profile, findings)
        self.assertFalse([item for item in findings if item.level == "ERROR"])

    def test_unsourced_material_rule_is_error(self) -> None:
        self.profile["official_sources"][0]["supports"].remove("pdf")
        findings = []
        MODULE.validate_profile(self.profile, findings)
        self.assertIn("PROFILE_UNSOURCED_RULE", [item.code for item in findings])

    def test_unsourced_layout_rule_is_error(self) -> None:
        self.profile["official_sources"][0]["supports"].remove("layout_rules")
        findings = []
        MODULE.validate_profile(self.profile, findings)
        self.assertIn("PROFILE_UNSOURCED_RULE", [item.code for item in findings])

    def test_template_hash_mismatch_is_error(self) -> None:
        self.profile["template"]["files"][0]["sha256"] = "0" * 64
        findings = []
        MODULE.audit_template_files(self.profile, self.root.resolve(), findings)
        self.assertIn("TEMPLATE_HASH_MISMATCH", [item.code for item in findings])

    def test_required_section_and_dangerous_override(self) -> None:
        source = "\\usepackage{venue}\n\\usepackage{geometry}\n\\section{Introduction}"
        findings = []
        MODULE.audit_tex(self.profile, source, findings)
        codes = [item.code for item in findings]
        self.assertIn("TEX_REQUIRED_SECTION", codes)
        self.assertIn("TEX_DANGEROUS_OVERRIDE", codes)

    def test_spacing_break_and_bottom_controls_are_reported(self) -> None:
        source = (
            "\\usepackage{venue}\n"
            "\\vspace{4pt}\n"
            "\\newpage\n"
            "\\raggedbottom\n"
            "\\section{Limitations}Limits.\n"
        )
        findings = []
        MODULE.audit_tex(self.profile, source, findings)
        codes = [item.code for item in findings]
        self.assertIn("TEX_MANUAL_VERTICAL_SPACE", codes)
        self.assertIn("TEX_FORCED_PAGE_BREAK", codes)
        self.assertIn("TEX_BOTTOM_CONTROL", codes)

    def test_lowercase_here_is_not_forced_H_but_wide_here_is_reported(self) -> None:
        source = (
            "\\usepackage{venue}\n"
            "\\begin{table*}[h]x\\end{table*}\n"
            "\\section{Limitations}Limits.\n"
        )
        findings = []
        MODULE.audit_tex(self.profile, source, findings)
        codes = [item.code for item in findings]
        self.assertNotIn("TEX_FORCED_PAGE_BREAK", codes)
        self.assertIn("TEX_WIDE_FLOAT_HERE", codes)

    def test_layout_metric_flags_blank_band_and_unbalanced_final_page(self) -> None:
        self.profile["layout_rules"]["final_page_columns"] = "balanced"
        metrics = [
            {
                "page": 1,
                "left": {
                    "word_count": 100,
                    "largest_internal_blank_band": {
                        "start_pt": 300.0,
                        "end_pt": 370.0,
                        "height_pt": 70.0,
                    },
                },
                "right": {"word_count": 100, "largest_internal_blank_band": None},
                "column_bottom_delta_pt": 4.0,
            },
            {
                "page": 2,
                "left": {"word_count": 120, "largest_internal_blank_band": None},
                "right": {"word_count": 0, "largest_internal_blank_band": None},
                "column_bottom_delta_pt": None,
            },
        ]
        findings = []
        MODULE.evaluate_layout_metrics(self.profile["layout_rules"], metrics, findings)
        codes = [item.code for item in findings]
        self.assertIn("PDF_BLANK_BAND_CANDIDATE", codes)
        self.assertIn("PDF_FINAL_COLUMN_UNBALANCED", codes)

    def test_log_audit_reports_vertical_and_float_failures(self) -> None:
        log = self.root / "main.log"
        log.write_text(
            "Underfull \\vbox (badness 10000) has occurred while \\output is active\n"
            "LaTeX Warning: Float too large for page by 10.0pt\n",
            encoding="utf-8",
        )
        findings = []
        counts = MODULE.audit_log(log, findings)
        self.assertEqual(counts["underfull_vbox"], 1)
        codes = [item.code for item in findings]
        self.assertIn("LOG_UNDERFULL_VBOX", codes)
        self.assertIn("LOG_FLOAT_FAILURE", codes)

    def test_source_only_cli_writes_bound_audit(self) -> None:
        output = self.root / "format-audit.json"
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--profile",
                str(self.profile_path),
                "--project-root",
                str(self.root),
                "--tex",
                str(self.tex),
                "--source-only",
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        audit = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["profile"]["sha256"], digest(self.profile_path))
        self.assertEqual(audit["tex"]["main_sha256"], digest(self.tex))

    def test_strict_rejects_unpinned_template(self) -> None:
        self.profile["template"]["files"][0]["sha256"] = ""
        self.profile_path.write_text(json.dumps(self.profile), encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--profile",
                str(self.profile_path),
                "--project-root",
                str(self.root),
                "--tex",
                str(self.tex),
                "--source-only",
                "--strict",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("TEMPLATE_HASH_UNPINNED", result.stdout)


if __name__ == "__main__":
    unittest.main()

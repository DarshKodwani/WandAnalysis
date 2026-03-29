#!/usr/bin/env python3
"""validate_inputs.py - Lightweight pre-run validator for BIDS-style inputs.

Checks basic assumptions used by this repository:
1. Dataset root exists.
2. Subject directories (`sub-*`) are present.
3. For selected subjects, expected BOLD file exists for session/task.
4. Optional MRIQC TSV exists when requested.

Usage:
    python scripts/validate_inputs.py
    python scripts/validate_inputs.py --session ses-06 --task rest
    python scripts/validate_inputs.py --subjects sub-00395 sub-01187
    python scripts/validate_inputs.py --require-mriqc
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from utils import DATASET_ROOT, DEFAULT_SESSION, DEFAULT_TASK, MRIQC_ANALYSIS_DIR, bold_path


@dataclass
class ValidationReport:
    checked_subjects: int
    valid_subjects: int
    missing_bold: list[str]
    dataset_root_ok: bool
    mriqc_ok: bool | None


def discover_subjects(root: Path) -> list[str]:
    if not root.exists():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir() and p.name.startswith("sub-"))


def validate_subject_bold(subject: str, session: str, task: str) -> bool:
    return bold_path(subject, session, task).exists()


def run_validation(subjects: list[str], session: str, task: str, require_mriqc: bool) -> ValidationReport:
    dataset_root_ok = DATASET_ROOT.exists() and DATASET_ROOT.is_dir()

    missing_bold = []
    valid = 0
    for subject in subjects:
        if validate_subject_bold(subject, session, task):
            valid += 1
        else:
            missing_bold.append(subject)

    mriqc_ok = None
    if require_mriqc:
        mriqc_tsv = MRIQC_ANALYSIS_DIR / f"{session}_task-{task}_bold.tsv"
        mriqc_ok = mriqc_tsv.exists()

    return ValidationReport(
        checked_subjects=len(subjects),
        valid_subjects=valid,
        missing_bold=missing_bold,
        dataset_root_ok=dataset_root_ok,
        mriqc_ok=mriqc_ok,
    )


def print_report(report: ValidationReport, session: str, task: str, max_missing: int) -> None:
    print()
    print("Input Validation Report")
    print("-" * 72)
    print(f"Dataset root         : {DATASET_ROOT}")
    print(f"Dataset root exists  : {'YES' if report.dataset_root_ok else 'NO'}")
    print(f"Session/task checked : {session} / task-{task}")
    print(f"Subjects checked     : {report.checked_subjects}")
    print(f"Subjects with BOLD   : {report.valid_subjects}")
    print(f"Subjects missing BOLD: {len(report.missing_bold)}")

    if report.mriqc_ok is not None:
        print(f"MRIQC TSV present    : {'YES' if report.mriqc_ok else 'NO'}")

    if report.missing_bold:
        print("\nMissing BOLD examples:")
        for sub in report.missing_bold[:max_missing]:
            print(f"  - {sub}: {bold_path(sub, session, task)}")
        if len(report.missing_bold) > max_missing:
            remaining = len(report.missing_bold) - max_missing
            print(f"  ... and {remaining} more")

    print("-" * 72)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate dataset inputs before running QC/analysis scripts.")
    parser.add_argument("--session", default=DEFAULT_SESSION, help=f"Session label (default: {DEFAULT_SESSION})")
    parser.add_argument("--task", default=DEFAULT_TASK, help=f"Task label (default: {DEFAULT_TASK})")
    parser.add_argument("--subjects", nargs="*", help="Optional subject IDs to validate; defaults to all sub-* found.")
    parser.add_argument("--require-mriqc", action="store_true", help="Also require MRIQC TSV for selected session/task.")
    parser.add_argument(
        "--max-missing-print",
        type=int,
        default=10,
        help="Maximum number of missing-subject examples to print (default: 10)",
    )
    args = parser.parse_args()

    if args.subjects:
        subjects = args.subjects
    else:
        subjects = discover_subjects(DATASET_ROOT)

    if not subjects:
        print(f"ERROR: No subjects found under {DATASET_ROOT}")
        sys.exit(1)

    report = run_validation(subjects, args.session, args.task, args.require_mriqc)
    print_report(report, args.session, args.task, args.max_missing_print)

    ok = report.dataset_root_ok and len(report.missing_bold) == 0
    if report.mriqc_ok is not None:
        ok = ok and report.mriqc_ok

    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()

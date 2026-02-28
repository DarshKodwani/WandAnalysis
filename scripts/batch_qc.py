"""
batch_qc.py - Run QC pipeline for a list of subjects, sequentially.

For each subject:
  1. Checks per-analysis which outputs already exist — skips only the analyses done
  2. Downloads the BOLD data if at least one analysis is still needed
  3. Runs visualise_bold.py  (saves plots + mean_bold.nii.gz + std_bold.nii.gz)
  4. Runs slice_qc.py        (saves plots + slicemean.npy)
  5. Runs iqm.py             (saves iqm.json + tSNR/CoV maps + DVARS timeseries)
  6. Drops the raw BOLD files via git-annex only when all analyses complete
  7. Moves to the next subject

Usage:
    # Pass subjects directly
    python scripts/batch_qc.py sub-43766 sub-64927 sub-00395

    # Or pass a text file with one subject ID per line
    python scripts/batch_qc.py --file subjects.txt

    # Or run on every subject in the dataset that has ses-06/func/ data
    python scripts/batch_qc.py --all

If a subject fails at any step, the error is printed and the pipeline
continues with the next subject.
"""

import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
REPO_ROOT  = Path(__file__).resolve().parents[1]
WAND_ROOT  = REPO_ROOT / "data" / "WAND"
SESSION    = "ses-06"
CONDA_BIN  = Path.home() / "miniconda3" / "envs" / "wand" / "bin"
DEPLOY_KEY = Path.home() / ".ssh" / "wand_deploy_key"
LOGS_DIR   = REPO_ROOT / "logs"

# ── Colours & symbols ─────────────────────────────────────────────────────────
R   = "\033[0m"       # reset
B   = "\033[1m"       # bold
DIM = "\033[2m"
CYN = "\033[0;36m"    # cyan
GRN = "\033[0;32m"    # green
YLW = "\033[0;33m"    # yellow
RED = "\033[0;31m"    # red
MAG = "\033[0;35m"    # magenta
BLU = "\033[0;34m"    # blue

TICK  = f"{GRN}✔{R}"
CROSS = f"{RED}✘{R}"
SKIP  = f"{YLW}⊘{R}"
ARROW = f"{CYN}▶{R}"
TRASH = f"{MAG}⌫{R}"
CLOCK = f"{DIM}⏱{R}"

W = 64  # line width


def bar(char="─", colour=DIM):
    print(f"{colour}{char * W}{R}", flush=True)


def header_line(text, colour=B):
    pad = max(0, W - len(text) - 4)
    print(f"{colour}  {text}{'  ' + ' ' * pad}{R}", flush=True)


def step(symbol, label, detail="", indent=4):
    pad = " " * indent
    detail_str = f"  {DIM}{detail}{R}" if detail else ""
    print(f"{pad}{symbol}  {B}{label}{R}{detail_str}", flush=True)


def substep(msg, indent=8):
    print(f"{' ' * indent}{DIM}↳  {msg}{R}", flush=True)


def elapsed(start):
    secs = int(time.time() - start)
    return str(timedelta(seconds=secs))


# ── Core helpers ──────────────────────────────────────────────────────────────
def is_real_file(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 1024 * 1024


def visualise_bold_done(subject: str) -> bool:
    return (REPO_ROOT / "results" / subject / "visualise_bold" / "mean_bold.nii.gz").exists()


def slice_qc_done(subject: str) -> bool:
    return (REPO_ROOT / "results" / subject / "slice_qc" / "slicemean.npy").exists()


def iqm_done(subject: str) -> bool:
    return (REPO_ROOT / "results" / subject / "iqm" / "iqm.json").exists()


def all_done(subject: str) -> bool:
    return visualise_bold_done(subject) and slice_qc_done(subject) and iqm_done(subject)


def run_cmd(cmd: list, cwd: Path = REPO_ROOT, extra_env: dict = None):
    """Run a command. Returns (returncode, error_output_str)."""
    env = os.environ.copy()
    env["PATH"] = str(CONDA_BIN) + ":" + env.get("PATH", "")
    if extra_env:
        env.update(extra_env)
    result = subprocess.run(
        cmd, cwd=str(cwd), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    output = result.stdout.decode(errors="replace")
    if result.returncode != 0:
        print(output, flush=True)
    return result.returncode, output


# ── Pipeline steps ─────────────────────────────────────────────────────────────
def download(subject: str):
    """Returns (ok: bool, error: str)."""
    bold_path = WAND_ROOT / subject / SESSION / "func" / \
                f"{subject}_{SESSION}_task-rest_bold.nii.gz"

    if is_real_file(bold_path):
        step(SKIP, "Download", "BOLD already present — skipping")
        return True, ""

    step(ARROW, "Download", f"fetching {SESSION}/func from GIN ...")
    t = time.time()
    rc, err = run_cmd(["bash", "scripts/download.sh", subject, SESSION, "func"])
    if rc != 0:
        step(CROSS, "Download FAILED", f"exit code {rc}")
        return False, err
    step(TICK, "Download complete", elapsed(t))
    return True, ""


def run_visualise_bold(subject: str):
    """Returns (ok: bool, error: str)."""
    step(ARROW, "Spatial QC", "running visualise_bold.py ...")
    t = time.time()
    rc, err = run_cmd([str(CONDA_BIN / "python"), "scripts/visualise_bold.py", subject])
    if rc != 0:
        step(CROSS, "Spatial QC FAILED", f"exit code {rc}")
        return False, err
    substep(f"mean_bold.nii.gz  •  std_bold.nii.gz  •  4 plots saved")
    step(TICK, "Spatial QC complete", elapsed(t))
    return True, ""


def run_slice_qc(subject: str):
    """Returns (ok: bool, error: str)."""
    step(ARROW, "Slice QC", "running slice_qc.py ...")
    t = time.time()
    rc, err = run_cmd([str(CONDA_BIN / "python"), "scripts/slice_qc.py", subject])
    if rc != 0:
        step(CROSS, "Slice QC FAILED", f"exit code {rc}")
        return False, err
    substep("slicemean.npy  •  5 plots saved")
    step(TICK, "Slice QC complete", elapsed(t))
    return True, ""


def run_iqm(subject: str):
    """Returns (ok: bool, error: str)."""
    step(ARROW, "IQM", "running iqm.py ...")
    t = time.time()
    rc, err = run_cmd([str(CONDA_BIN / "python"), "scripts/iqm.py", subject])
    if rc != 0:
        step(CROSS, "IQM FAILED", f"exit code {rc}")
        return False, err
    substep("iqm.json  •  tsnr_map  •  cov_map  •  dvars.tsv  •  3 plots saved")
    step(TICK, "IQM complete", elapsed(t))
    return True, ""


def drop_bold(subject: str) -> bool:
    bold  = f"{subject}/{SESSION}/func/{subject}_{SESSION}_task-rest_bold.nii.gz"
    sbref = f"{subject}/{SESSION}/func/{subject}_{SESSION}_task-rest_sbref.nii.gz"

    to_drop = []
    if is_real_file(WAND_ROOT / bold):
        to_drop.append(bold)
    if is_real_file(WAND_ROOT / sbref):
        to_drop.append(sbref)

    if not to_drop:
        step(SKIP, "Cleanup", "no local BOLD content to drop")
        return True

    names = "  +  ".join(Path(f).name for f in to_drop)
    step(TRASH, "Cleanup", f"dropping via git-annex ...")
    substep(names)

    env = os.environ.copy()
    env["PATH"] = str(CONDA_BIN) + ":" + env.get("PATH", "")
    env["GIT_SSH_COMMAND"] = f"ssh -i {DEPLOY_KEY} -o IdentitiesOnly=yes"

    result = subprocess.run(
        ["git-annex", "drop"] + to_drop,
        cwd=str(WAND_ROOT), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    if result.returncode != 0:
        step(CROSS, "Cleanup FAILED", "git-annex drop error (analysis outputs are safe)")
        print(result.stdout.decode(errors="replace"), flush=True)
        return False

    substep("annex pointer preserved — re-fetchable at any time")
    step(TICK, "Raw BOLD removed", "")
    return True


def discover_subjects() -> list:
    """
    Find all sub-* directories in WAND_ROOT that contain a ses-06/func/ folder.
    Subjects without that structure are silently skipped — they don't have
    the expected 7T resting-state data for this session.
    """
    candidates = sorted(p.name for p in WAND_ROOT.iterdir()
                        if p.is_dir() and p.name.startswith("sub-"))
    valid = [s for s in candidates
             if (WAND_ROOT / s / SESSION / "func").is_dir()]
    return valid


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Batch BOLD QC pipeline — download, analyse, drop raw data."
    )
    parser.add_argument("subjects", nargs="*", metavar="subject",
                        help="Subject IDs e.g. sub-43766 sub-64927")
    parser.add_argument("--file", metavar="FILE",
                        help="Text file with one subject ID per line")
    parser.add_argument("--all", action="store_true",
                        help=f"Run on every subject in WAND that has a {SESSION}/func/ folder")
    args = parser.parse_args()

    if args.all:
        subjects = discover_subjects()
        if not subjects:
            parser.error(f"No subjects found with {SESSION}/func/ in {WAND_ROOT}")
    elif args.file:
        subjects = Path(args.file).read_text().splitlines()
        subjects = [s.strip() for s in subjects if s.strip() and not s.startswith("#")]
    else:
        subjects = args.subjects

    if not subjects:
        parser.error("No subjects provided. Pass subject IDs, use --file, or use --all.")

    n           = len(subjects)
    skipped     = []
    failed      = []
    completed   = []
    total_start = time.time()
    run_ts      = datetime.now()
    log_records = []          # one dict per subject, written to JSON at end

    # ── Banner ─────────────────────────────────────────────────────────────────
    print()
    bar("═", BLU)
    header_line(f"WAND  •  Batch QC Pipeline", BLU + B)
    header_line(f"Session: {SESSION}   •   Subjects: {n}", DIM)
    bar("═", BLU)
    print()

    for i, subject in enumerate(subjects, 1):
        sub_start = time.time()

        # ── Subject header ─────────────────────────────────────────────
        print()
        bar()
        pct = int((i - 1) / n * 100)
        filled = int(pct / 5)
        progress_bar = f"[{'█' * filled}{'░' * (20 - filled)}] {pct:3d}%"
        print(f"  {B}{CYN}Subject {i}/{n}{R}  {MAG}{B}{subject}{R}  {DIM}{progress_bar}{R}", flush=True)
        bar()
        print()

        # ── Per-analysis status ────────────────────────────────────────
        vb_done  = visualise_bold_done(subject)
        slc_done = slice_qc_done(subject)
        iq_done  = iqm_done(subject)

        log_rec = {
            "subject":  subject,
            "analyses": {
                "visualise_bold": "already_done" if vb_done  else "not_run",
                "slice_qc":       "already_done" if slc_done else "not_run",
                "iqm":            "already_done" if iq_done  else "not_run",
            },
        }

        # ── Already fully done? ────────────────────────────────────────
        if vb_done and slc_done and iq_done:
            step(SKIP, "Already complete", "all 3 analyses found — skipping")
            log_rec["status"]     = "skipped"
            log_rec["reason"]     = "all analyses already complete"
            log_rec["duration_s"] = 0
            log_records.append(log_rec)
            skipped.append(subject)
            print()
            continue

        # Report what is already done
        if vb_done:
            step(SKIP, "Spatial QC", "outputs already exist — skipping")
        if slc_done:
            step(SKIP, "Slice QC",   "outputs already exist — skipping")
        if iq_done:
            step(SKIP, "IQM",        "outputs already exist — skipping")
        if vb_done or slc_done or iq_done:
            print()

        # ── Download ───────────────────────────────────────────────────
        ok, err = download(subject)
        if not ok:
            log_rec["status"]     = "failed"
            log_rec["failed_at"]  = "download"
            log_rec["error"]      = err.strip()
            log_rec["duration_s"] = round(time.time() - sub_start)
            log_records.append(log_rec)
            failed.append(subject)
            print()
            continue
        print()

        # ── Spatial QC ─────────────────────────────────────────────────
        if not vb_done:
            ok, err = run_visualise_bold(subject)
            if not ok:
                log_rec["status"]     = "failed"
                log_rec["failed_at"]  = "visualise_bold"
                log_rec["error"]      = err.strip()
                log_rec["duration_s"] = round(time.time() - sub_start)
                log_records.append(log_rec)
                failed.append(subject)
                print()
                continue
            log_rec["analyses"]["visualise_bold"] = "ran"
            print()

        # ── Slice QC ───────────────────────────────────────────────────
        if not slc_done:
            ok, err = run_slice_qc(subject)
            if not ok:
                log_rec["status"]     = "failed"
                log_rec["failed_at"]  = "slice_qc"
                log_rec["error"]      = err.strip()
                log_rec["duration_s"] = round(time.time() - sub_start)
                log_records.append(log_rec)
                failed.append(subject)
                print()
                continue
            log_rec["analyses"]["slice_qc"] = "ran"
            print()

        # ── IQM ────────────────────────────────────────────────────────
        if not iq_done:
            ok, err = run_iqm(subject)
            if not ok:
                log_rec["status"]     = "failed"
                log_rec["failed_at"]  = "iqm"
                log_rec["error"]      = err.strip()
                log_rec["duration_s"] = round(time.time() - sub_start)
                log_records.append(log_rec)
                failed.append(subject)
                print()
                continue
            log_rec["analyses"]["iqm"] = "ran"
            print()

        # ── Drop raw BOLD (only when all analyses are now complete) ────
        drop_bold(subject)
        print()

        # ── Subject footer ─────────────────────────────────────────────
        log_rec["status"]     = "completed"
        log_rec["duration_s"] = round(time.time() - sub_start)
        log_records.append(log_rec)
        completed.append(subject)
        dur = elapsed(sub_start)
        print(f"  {TICK}  {GRN}{B}{subject}  —  done{R}  {DIM}({dur}){R}\n", flush=True)

    # ── Write log ──────────────────────────────────────────────────────────────
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    run_id   = run_ts.strftime("batch_qc_%Y-%m-%d_%H%M%S")
    log_path = LOGS_DIR / f"{run_id}.json"
    log = {
        "run_id":       run_id,
        "timestamp":    run_ts.isoformat(timespec="seconds"),
        "session":      SESSION,
        "summary": {
            "n_subjects":   n,
            "completed":    len(completed),
            "skipped":      len(skipped),
            "failed":       len(failed),
            "total_duration_s": round(time.time() - total_start),
        },
        "subjects": log_records,
    }
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)

    # ── Final summary ──────────────────────────────────────────────────────────
    total_dur = elapsed(total_start)
    print()
    bar("═", BLU)
    header_line("Summary", BLU + B)
    bar("─", DIM)
    print(f"  {TICK}  {GRN}{B}Completed{R}  {B}{len(completed)}{R} / {n}")
    print(f"  {SKIP}  {YLW}{B}Skipped  {R}  {B}{len(skipped)}{R}  {DIM}(already done){R}")
    print(f"  {CROSS}  {RED}{B}Failed   {R}  {B}{len(failed)}{R}")
    if failed:
        print()
        for s in failed:
            print(f"       {RED}•  {s}{R}")
    bar("─", DIM)
    print(f"  {CLOCK}  {DIM}Total time: {total_dur}{R}")
    print(f"  {DIM}Log saved → {log_path.relative_to(REPO_ROOT)}{R}")
    bar("═", BLU)
    print()


if __name__ == "__main__":
    main()


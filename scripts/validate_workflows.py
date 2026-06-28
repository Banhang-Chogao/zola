#!/usr/bin/env python3
"""
Validate GitHub Actions workflow YAML — a QA gate so an "Invalid workflow file"
can never silently ship again (vaccine V21).

Why this exists:
  `check-branch-ancestry.yml` shipped broken for a long time — GitHub flagged it
  as "Invalid workflow file" on every run, but that status does NOT block
  auto-merge (only qa-check gates). qa_check.py is stdlib-only and never parsed
  workflow YAML, so the breakage slipped straight to main and showed a red ✗ on
  every PR. This script closes that gap.

Checks per .github/workflows/*.yml|*.yaml:
  1. The file parses as valid YAML (catches the block-scalar / template-literal
     indentation break + plain-scalar `: ` ambiguity that broke V21).
  2. Each `actions/github-script` step's inline `script:` is valid JS (best-effort,
     only when Node is on PATH) — catches a malformed script body early.

PyYAML: used when importable (CI installs it via qa.yml). If it is missing the
script falls back to a focused structural lint that still catches the two failure
modes above, so it remains a real gate even without the dependency. It never
crashes CI on an unexpected internal error (prints + exits 0 in that case).

Exit code:
  0 — all workflows valid
  2 — at least one workflow is invalid (CI gate → red)

Usage:
  python3 scripts/validate_workflows.py
  python3 scripts/validate_workflows.py .github/workflows/foo.yml   # specific files
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"

try:
    import yaml  # type: ignore

    _HAVE_YAML = True
except Exception:  # pragma: no cover - depends on env
    _HAVE_YAML = False


def _structural_lint(path: Path) -> list[str]:
    """Pure-stdlib fallback. Catches the two YAML break modes that shipped broken:
      (a) a `|` block scalar whose continuation lines dedent to column 0 (a
          multi-line JS template literal forced to the left margin), and
      (b) a `run:`/plain scalar value containing `: ` outside quotes.
    Conservative — reports only high-confidence problems."""
    errors: list[str] = []
    lines = path.read_text(encoding="utf-8").splitlines()

    in_block = False
    block_indent = 0
    block_key_line = 0
    for i, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        indent = len(raw) - len(raw.lstrip(" "))

        if in_block:
            if not stripped:
                continue  # blank lines are allowed inside block scalars
            if indent < block_indent:
                # A non-blank line dedented out of the block scalar. If it is not a
                # plausible new YAML key/list item, the block was broken mid-content.
                looks_like_key = bool(
                    re.match(r"^[A-Za-z0-9_.\"'-]+\s*:(\s|$)", stripped)
                    or stripped.startswith("- ")
                )
                if not looks_like_key or indent == 0:
                    errors.append(
                        f"{path}:{i}: line dedented out of block scalar opened at "
                        f"line {block_key_line} (indent {indent} < {block_indent}); "
                        f"likely a multi-line string that broke the YAML"
                    )
                in_block = False
            else:
                continue

        if not in_block:
            # Detect a block scalar opener: `key: |` or `key: >` (with optional chomp).
            m = re.match(r"^(\s*)([^:#]+):\s*[|>][+-]?\s*$", raw)
            if m:
                in_block = True
                block_indent = len(m.group(1)) + 1  # content must be deeper than key
                block_key_line = i
                continue
            # Detect a `run:`/plain scalar value with an unquoted `: ` (YAML mapping
            # ambiguity → "mapping values are not allowed here").
            m2 = re.match(r"^\s*[\w-]+:\s+(?![|>'\"])(.*\S)\s*$", raw)
            if m2:
                val = m2.group(1)
                if re.search(r"\S: \S", val) and not (
                    val.startswith(("'", '"')) and val.rstrip().endswith(("'", '"'))
                ):
                    errors.append(
                        f"{path}:{i}: unquoted scalar contains ': ' — wrap the value "
                        f"in a block scalar (| ) or quotes"
                    )
    return errors


def _validate_yaml(path: Path) -> list[str]:
    if not _HAVE_YAML:
        return _structural_lint(path)
    try:
        yaml.safe_load(path.read_text(encoding="utf-8"))
        return []
    except yaml.YAMLError as exc:  # type: ignore
        return [f"{path}: invalid YAML — {str(exc).splitlines()[0]}"]


def _validate_github_script_js(path: Path) -> list[str]:
    """Best-effort: node --check each inline github-script `script:` body."""
    if not _HAVE_YAML or not shutil.which("node"):
        return []
    errors: list[str] = []
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))  # type: ignore
    except Exception:
        return []  # YAML error already reported by _validate_yaml
    if not isinstance(doc, dict):
        return []
    for job in (doc.get("jobs") or {}).values():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps") or []:
            if not isinstance(step, dict):
                continue
            uses = str(step.get("uses") or "")
            with_ = step.get("with") or {}
            if "github-script" in uses and isinstance(with_, dict) and with_.get("script"):
                script = with_["script"]
                # ${{ ... }} is GitHub Actions interpolation — valid in a
                # github-script body but not standalone JS. Replace each with a
                # placeholder so node --check validates the real JS, not Actions.
                script = re.sub(r"\$\{\{.*?\}\}", "0", script, flags=re.DOTALL)
                # actions/github-script@v7 wraps the script in an async function,
                # so top-level `await` is valid at runtime.  Wrap in an async IIFE
                # so `node --check` accepts top-level `await` too.
                script = "(async () => {\n" + script.lstrip("\n") + "\n})();"
                with tempfile.NamedTemporaryFile(
                    "w", suffix=".js", delete=False, encoding="utf-8"
                ) as fh:
                    fh.write(script)
                    tmp = fh.name
                try:
                    res = subprocess.run(
                        ["node", "--check", tmp], capture_output=True, text=True
                    )
                    if res.returncode != 0:
                        first = (res.stderr or res.stdout).strip().splitlines()
                        errors.append(
                            f"{path}: github-script step '{step.get('name', uses)}' "
                            f"has invalid JS — {first[0] if first else 'syntax error'}"
                        )
                finally:
                    Path(tmp).unlink(missing_ok=True)
    return errors


def main(argv: list[str]) -> int:
    if argv:
        files = [Path(a) for a in argv]
    else:
        if not WORKFLOW_DIR.is_dir():
            print("No .github/workflows directory — nothing to validate.")
            return 0
        files = sorted(WORKFLOW_DIR.glob("*.yml")) + sorted(WORKFLOW_DIR.glob("*.yaml"))

    all_errors: list[str] = []
    for f in files:
        if not f.is_file():
            continue
        all_errors.extend(_validate_yaml(f))
        all_errors.extend(_validate_github_script_js(f))

    mode = "PyYAML" if _HAVE_YAML else "stdlib structural lint (PyYAML absent)"
    print(f"[validate_workflows] scanned {len(files)} workflow file(s) — mode: {mode}")
    if all_errors:
        print("\n✗ Invalid workflow file(s):")
        for e in all_errors:
            print(f"  - {e}")
        return 2
    print("✓ All workflow YAML valid")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as exc:  # never crash CI on an internal bug
        print(f"[validate_workflows] internal error (non-blocking): {exc}")
        sys.exit(0)

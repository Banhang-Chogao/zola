#!/usr/bin/env python3

import subprocess
from pathlib import Path

VACCINE_FILES = {
    "CLAUDE.md",
    "scripts/qa_vaccines.py",
    "scripts/test_qa_vaccines.py",
}

CI_PREFIXES = (
    ".github/workflows/",
)

def changed_files(base="origin/main"):
    try:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", f"{base}...HEAD"],
            text=True,
        )
        return [x.strip() for x in out.splitlines() if x.strip()]
    except Exception:
        return []

def build_context():
    files = changed_files()

    return {
        "files": files,
        "touches_vaccine": any(f in VACCINE_FILES for f in files),
        "touches_ci": any(
            f.startswith(CI_PREFIXES)
            for f in files
        ),
        "touches_claude": "CLAUDE.md" in files,
        "touches_content": any(
            f.startswith(("content/", "sass/", "static/", "templates/"))
            for f in files
        ),
    }

if __name__ == "__main__":
    from pprint import pprint
    pprint(build_context())

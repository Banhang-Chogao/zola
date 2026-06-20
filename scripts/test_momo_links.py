"""Guard test: default MoMo paid-content link must be the current one.

Ensures the deprecated default MoMo link never reappears across the repo and
that the canonical default link is wired everywhere a paywall/donate fallback
lives. The 2 subscription links (VIPZone monthly / semiannual) are intentional
exceptions and are NOT rewritten — they are asserted to remain intact.

Run: python3 -m unittest scripts.test_momo_links -v
"""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Canonical default MoMo paid-content / donate link (current).
CURRENT_DEFAULT = "https://me.momo.vn/G5T1CDFRuJFWfBCDiK/y5eVvzz2nlXXeEP"

# Deprecated default link — must NOT appear anywhere anymore.
DEPRECATED_DEFAULT = "https://me.momo.vn/G5T1CDFRuJFWfBCDiK/YQdJ8k98OO4vaOG"

# Preserved subscription links (exceptions — not the default paid-content link).
SUBSCRIPTION_LINKS = (
    "https://me.momo.vn/G5T1CDFRuJFWfBCDiK/MvbmqW94lpp0bYA",   # monthly
    "https://me.momo.vn/G5T1CDFRuJFWfBCDiK/lNbWPA9NgD64dyg",   # semiannual
)

# Files that must wire the current default link.
DEFAULT_LINK_FILES = (
    "config.toml",
    "templates/macros/paywall.html",
    "templates/shortensea-upgrade.html",
    "backend/paywall_app.py",
    "services/shortensea/main.py",
    "docs/paywall.md",
)


def _git_grep(needle: str) -> list[str]:
    """Return tracked-file lines containing needle (fixed string)."""
    res = subprocess.run(
        ["git", "grep", "-n", "-F", needle],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    # git grep exits 1 when no match — that's fine.
    return [ln for ln in res.stdout.splitlines() if ln.strip()]


class MomoLinkGuardTest(unittest.TestCase):
    def test_no_deprecated_default_link_anywhere(self):
        hits = _git_grep(DEPRECATED_DEFAULT)
        self.assertEqual(
            hits, [],
            "Deprecated default MoMo link found — replace with "
            f"{CURRENT_DEFAULT}:\n" + "\n".join(hits),
        )

    def test_current_default_link_wired(self):
        for rel in DEFAULT_LINK_FILES:
            with self.subTest(file=rel):
                text = (ROOT / rel).read_text(encoding="utf-8")
                self.assertIn(
                    CURRENT_DEFAULT, text,
                    f"{rel} should reference the current default MoMo link",
                )

    def test_subscription_links_preserved(self):
        for link in SUBSCRIPTION_LINKS:
            with self.subTest(link=link):
                self.assertNotEqual(
                    [], _git_grep(link),
                    f"Subscription link missing (must be preserved): {link}",
                )


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Tests for the scheduled-forward-ref vaccine (V13) in qa-404-checker.py.

A link to a draft post whose [extra].publish_at is in the FUTURE must be treated
as a scheduled forward-reference (warning), never a broken link. Anything else
(no publish_at, a PAST publish_at, or a non-draft) stays strict 404.
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("qa404", ROOT / "qa-404-checker.py")
qa404 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(qa404)


def _write_post(folder: Path, name: str, draft: bool, publish_at: str | None) -> None:
    fm = ['+++', 'title = "T"', f"draft = {'true' if draft else 'false'}", "[extra]"]
    if publish_at:
        fm.append(f'publish_at = "{publish_at}"')
    fm += ["+++", "", "body"]
    (folder / f"{name}.md").write_text("\n".join(fm), encoding="utf-8")


class ScheduledForwardRefTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.croot = Path(self.tmp.name) / "content"
        self.baochi = self.croot / "baochi"
        self.baochi.mkdir(parents=True)
        self._orig = qa404.CONTENT
        qa404.CONTENT = self.croot
        self.addCleanup(setattr, qa404, "CONTENT", self._orig)

    def _targets(self) -> dict[str, str]:
        return qa404._scheduled_forward_targets(datetime.now(timezone.utc))

    def test_future_draft_is_forward_ref(self) -> None:
        _write_post(self.baochi, "future", True, "2099-01-01T20:00:00+07:00")
        self.assertIn("/baochi/future/", self._targets())

    def test_past_publish_at_is_strict(self) -> None:
        _write_post(self.baochi, "past", True, "2000-01-01T20:00:00+07:00")
        self.assertNotIn("/baochi/past/", self._targets())

    def test_draft_without_publish_at_is_strict(self) -> None:
        _write_post(self.baochi, "plain", True, None)
        self.assertNotIn("/baochi/plain/", self._targets())

    def test_published_post_is_not_forward_ref(self) -> None:
        _write_post(self.baochi, "live", False, None)
        self.assertNotIn("/baochi/live/", self._targets())

    def test_aliases_are_included(self) -> None:
        (self.baochi / "withalias.md").write_text(
            '+++\ntitle = "T"\ndraft = true\naliases = ["/old-url/"]\n'
            '[extra]\npublish_at = "2099-01-01T20:00:00+07:00"\n+++\n\nbody',
            encoding="utf-8",
        )
        targets = self._targets()
        self.assertIn("/baochi/withalias/", targets)
        self.assertIn("/old-url/", targets)

    def test_bad_frontmatter_degrades_to_strict(self) -> None:
        (self.baochi / "broken.md").write_text(
            "+++\nthis is : not = valid toml [[[\n+++\n\nbody", encoding="utf-8"
        )
        # Must not raise; unparseable frontmatter yields no forward-ref entry.
        self.assertEqual(self._targets(), {})


if __name__ == "__main__":
    unittest.main()

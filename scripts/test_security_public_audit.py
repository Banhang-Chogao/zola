#!/usr/bin/env python3
"""Unit tests for security_public_audit.py.

Two jobs:
  1. Every detector FIRES on a planted exposure (the gate is not a no-op).
  2. CALIBRATION holds — legitimate blog content (prose keywords, generic
     tutorial paths, documented placeholders) is NOT flagged, so `main`
     keeps passing with zero false positives.
"""

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "security_public_audit", Path(__file__).resolve().parent / "security_public_audit.py")
spa = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(spa)


def _mktree(root: Path, files: dict):
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


def _rules(findings, level=None):
    return {f.rule for f in findings if level is None or f.level == level}


class DetectorsFire(unittest.TestCase):
    def _audit(self, files, include_public=True):
        import tempfile
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        _mktree(root, files)
        return spa.audit_public_surface(root, include_public=include_public)

    def test_forbidden_extension(self):
        f = self._audit({"static/db.sqlite": "x", "content/_index.md": "+++\n+++\n"})
        self.assertIn("forbidden-ext", _rules(f, "error"))

    def test_forbidden_basename(self):
        f = self._audit({"content/CLAUDE.md": "secret doctrine"})
        self.assertIn("forbidden-file", _rules(f, "error"))

    def test_dotenv_variants(self):
        f = self._audit({"static/.env.production": "API_KEY=real"})
        self.assertIn("forbidden-file", _rules(f, "error"))

    def test_internal_ops_doc_in_static(self):
        f = self._audit({"static/vaccine-cheat-sheet.html": "<html>operator</html>"})
        self.assertIn("internal-doc", _rules(f, "error"))

    def test_real_secret_value_anywhere(self):
        f = self._audit({"static/js/leak.js": 'const t="ghp_' + "a" * 36 + '";'})
        self.assertIn("secret-value", _rules(f, "error"))

    def test_secret_value_even_in_content(self):
        # A real token must not appear even inside a tutorial code block.
        f = self._audit({"content/posting/p.md": "+++\n+++\nkey=AKIA" + "A" * 16})
        self.assertIn("secret-value", _rules(f, "error"))

    def test_secret_assignment_in_infra(self):
        f = self._audit({"static/js/cfg.js": 'var c={api_key:"Ab3Xz9Qw7Lp2Kd8h"};'})
        self.assertIn("secret-assign", _rules(f, "error"))

    def test_local_path_leak_in_static(self):
        f = self._audit({"static/js/p.js": 'var p="/Users/duynguyen/blog/secret";'})
        self.assertIn("local-path", _rules(f, "error"))

    def test_sitemap_exposes_private_url(self):
        f = self._audit({
            "public/sitemap.xml":
                "<urlset><url><loc>https://x.org/vaccine-cheat-sheet.html</loc></url></urlset>",
        })
        self.assertIn("sitemap-link", _rules(f, "error"))

    def test_menu_link_to_private_path(self):
        f = self._audit({
            "config.toml": '[extra]\nmenu = [ { name = "x", url = "/private_content/a" } ]\n',
        })
        self.assertIn("menu-link", _rules(f, "error"))


class CalibrationNoFalsePositives(unittest.TestCase):
    def _audit(self, files):
        import tempfile
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        _mktree(root, files)
        return spa.audit_public_surface(root, include_public=True)

    def test_prose_keywords_not_flagged(self):
        # Real blog tutorials legitimately mention these words.
        body = ("+++\ntitle=\"t\"\n+++\n"
                "Hướng dẫn dùng API_KEY, PASSWORD, TOKEN, SECRET và WEBHOOK an toàn. "
                "Đừng commit `gh auth` token của bạn.\n")
        f = self._audit({"content/posting/security-tutorial.md": body})
        self.assertEqual([x.render(False) for x in f if x.level == "error"], [])

    def test_generic_home_paths_allowed(self):
        f = self._audit({
            "static/data/doc.txt": "Run in /home/user/project or /home/runner/work; ~/ is generic.",
        })
        self.assertNotIn("local-path", _rules(f, "error"))

    def test_placeholder_assignments_allowed(self):
        f = self._audit({
            "static/js/example.js":
                'const cfg={api_key:"YOUR_API_KEY_HERE",token:"xxxxxxxx",secret:"<your-secret>"};',
        })
        self.assertNotIn("secret-assign", _rules(f, "error"))

    def test_sitemap_tag_and_content_slugs_allowed(self):
        # Real taxonomy/content URLs that merely *contain* a sensitive word are
        # legitimate pages, not exposed files.
        sm = ("<urlset>"
              "<url><loc>https://x.org/tags/claude-md/</loc></url>"
              "<url><loc>https://x.org/tags/claude/page/1/</loc></url>"
              "<url><loc>https://x.org/posting/javascript-operators/</loc></url>"
              "<url><loc>https://x.org/posting/admin-rules-cua-toi/</loc></url>"
              "</urlset>")
        f = self._audit({"public/sitemap.xml": sm})
        self.assertNotIn("sitemap-link", _rules(f, "error"))

    def test_rendered_html_tutorial_paths_allowed(self):
        # Built pages embed tutorial prose: ~/.ssh, /home/<name>, password=… are
        # CONTENT, not leaks. Only static/ infra files get the loose heuristics.
        html = ("<html><body>Copy <code>~/.ssh/id_ed25519.pub</code>; "
                "edit <code>/home/duy/project/config</code>; "
                "set <code>password = \"S3cretValue123\"</code> in your env."
                "</body></html>")
        f = self._audit({"public/posting/ssh-guide/index.html": html})
        errs = _rules(f, "error")
        self.assertNotIn("local-path", errs)
        self.assertNotIn("secret-assign", errs)
        self.assertEqual([x.render(False) for x in f if x.level == "error"], [])

    def test_public_safe_assets_pass(self):
        f = self._audit({
            "static/robots.txt": "User-agent: *\nAllow: /\n",
            "static/ads.txt": "google.com, pub-0, DIRECT, f08c\n",
            "content/posting/normal.md": "+++\ntitle=\"Bài viết\"\n+++\nNội dung bình thường.\n",
        })
        self.assertEqual([x.render(False) for x in f if x.level == "error"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

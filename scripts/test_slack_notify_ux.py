#!/usr/bin/env python3
"""Tests cho slack_notify_ux — đảm bảo payload hợp lệ & mobile-friendly (≤5 blocks)."""
import json
import unittest

from scripts.slack_notify_ux import HEADER_LIMIT, TEXT_LIMIT, build_payload


class TestBuildPayload(unittest.TestCase):
    def test_all_kinds_valid(self):
        for kind in ("success", "warning", "critical", "info"):
            p = build_payload(kind, title="X", message="hello")
            self.assertIn("blocks", p)
            self.assertIn("text", p)  # fallback bắt buộc
            self.assertEqual(p["blocks"][0]["type"], "header")
            self.assertLessEqual(len(p["blocks"]), 5, f"{kind} vượt 5 blocks")

    def test_invalid_kind(self):
        with self.assertRaises(ValueError):
            build_payload("nope", title="X", message="y")

    def test_header_carries_emoji(self):
        self.assertTrue(
            build_payload("critical", title="DOWN", message="m")["blocks"][0]["text"]["text"].startswith("🚨")
        )

    def test_user_personalization(self):
        p = build_payload("warning", title="t", message="check", user="Minh")
        self.assertIn("*@Minh*", p["blocks"][1]["text"]["text"])

    def test_no_double_mention(self):
        # message đã có @user → không nhân đôi
        p = build_payload("warning", title="t", message="hi @Minh", user="Minh")
        self.assertEqual(p["blocks"][1]["text"]["text"].count("Minh"), 1)

    def test_single_button_is_accessory(self):
        p = build_payload(
            "success", title="t", message="m", button_text="Go", button_url="https://x"
        )
        section = p["blocks"][1]
        self.assertIn("accessory", section)
        self.assertEqual(section["accessory"]["style"], "primary")

    def test_two_buttons_make_actions_block(self):
        p = build_payload(
            "critical",
            title="t",
            message="m",
            button_text="Fix",
            button_url="https://a",
            secondary_text="Escalate",
            secondary_url="https://b",
        )
        actions = [b for b in p["blocks"] if b["type"] == "actions"]
        self.assertEqual(len(actions), 1)
        self.assertEqual(len(actions[0]["elements"]), 2)

    def test_context_only_when_metadata(self):
        p_no = build_payload("warning", title="t", message="m")
        self.assertFalse(any(b["type"] == "context" for b in p_no["blocks"]))
        p_yes = build_payload("warning", title="t", message="m", host="web-01", time="14:30")
        self.assertTrue(any(b["type"] == "context" for b in p_yes["blocks"]))

    def test_info_kind_neutral(self):
        p = build_payload("info", title="Commit mới", message="m", host="main")
        self.assertTrue(p["blocks"][0]["text"]["text"].startswith("🔔"))
        # info trung tính → không divider gây "ồn"
        self.assertFalse(any(b["type"] == "divider" for b in p["blocks"]))

    def test_info_button_no_style(self):
        p = build_payload(
            "info", title="t", message="m", button_text="Xem", button_url="https://x"
        )
        self.assertNotIn("style", p["blocks"][1]["accessory"])

    def test_warning_has_divider(self):
        p = build_payload("warning", title="t", message="m", host="web-01")
        self.assertTrue(any(b["type"] == "divider" for b in p["blocks"]))

    def test_truncation_limits(self):
        p = build_payload("warning", title="T" * 500, message="M" * 5000)
        self.assertLessEqual(len(p["blocks"][0]["text"]["text"]), HEADER_LIMIT)
        self.assertLessEqual(len(p["blocks"][1]["text"]["text"]), TEXT_LIMIT)

    def test_fallback_title_when_empty(self):
        p = build_payload("success", title="   ", message="m")
        self.assertIn("Hoàn thành", p["blocks"][0]["text"]["text"])

    def test_json_serializable(self):
        p = build_payload("critical", title="t", message="m", user="A", host="h", metric="92%")
        json.dumps(p)  # không raise

    def test_max_five_blocks_with_everything(self):
        p = build_payload(
            "critical",
            title="t",
            message="m",
            user="A",
            host="h",
            metric="x",
            time="14:30",
            button_text="Fix",
            button_url="https://a",
            secondary_text="Esc",
            secondary_url="https://b",
        )
        self.assertLessEqual(len(p["blocks"]), 5)


if __name__ == "__main__":
    unittest.main()

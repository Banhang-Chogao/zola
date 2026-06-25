#!/usr/bin/env python3
"""
slack_notify_ux.py — Bộ sinh payload Slack Block Kit "đẹp + human" cho 3 tình huống.

Biến thông báo Slack khô khan thành Block Kit có phân cấp thông tin, giọng văn gần
gũi, emoji có chủ đích và nút hành động ngay trong message. Hệ thống chỉ cần truyền
biến (host, %, user…) → script tự dựng payload hợp lệ rồi bắn vào Incoming Webhook.

3 loại:
    success  — Tin vui (deploy OK, job xong…)
    warning  — Cảnh báo (CPU cao, ngưỡng gần chạm…)
    critical — Lỗi khẩn cấp (service down, 5xx…)

Thiết kế UX (xem chi tiết PR/commit):
    - Số liệu quan trọng nhất lên `header` → quét <1s.
    - Metadata phụ (host, thời gian, ngưỡng) gom vào `context` (chữ xám, không "ồn").
    - Nút hành động (`accessory`/`actions`) đặt cạnh vấn đề → 1 chạm là xử lý.
    - Tone theo ngữ cảnh: vui thì ăn mừng, cảnh báo thì trấn an, khẩn thì nhấn impact.
    - Mobile-friendly: tối đa 5 blocks, mỗi text element gọn (cap an toàn < limit 3000).

Dùng (CLI):
    # In payload JSON ra stdout (preview / pipe sang curl)
    python3 scripts/slack_notify_ux.py warning \
        --title "CPU đang căng: 92%" \
        --message "*@Minh* server \`web-01\` đang ở *92%* CPU. Nên ngó qua nhé 👀" \
        --user Minh --host web-01 --metric "92% (ngưỡng 85%)" \
        --button-text "Mở Grafana" --button-url https://grafana.internal/web-01

    # Gửi thẳng vào Slack (env SLACK_WEBHOOK_URL hoặc --webhook)
    python3 scripts/slack_notify_ux.py success --title "Deploy thành công!" \
        --message "Tuyệt vời @Minh! v2.4.1 đã live 👏" --send

Dùng (import):
    from scripts.slack_notify_ux import build_payload, send
    payload = build_payload("critical", title="Payment API DOWN", message="...", ...)
    send(payload)  # cần SLACK_WEBHOOK_URL

Env: SLACK_WEBHOOK_URL (Incoming Webhook). Exit 0 nếu OK, !=0 nếu lỗi.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

# Slack Block Kit: mỗi text element tối đa 3000 chars. Cap an toàn để chừa chỗ
# cho prefix/markdown escape (cùng lý do với V2 — slack-notify.yml truncate 2500).
TEXT_LIMIT = 2900
HEADER_LIMIT = 150  # header dùng plain_text, Slack cap 150 chars

# Cấu hình theo từng loại: emoji header, prefix mặc định cho message, style nút.
KINDS = {
    "success": {
        "emoji": "🎉",
        "fallback_title": "Hoàn thành!",
        "button_style": "primary",
        "lead": "",  # success không cần lead nhấn mạnh
    },
    "warning": {
        "emoji": "⚠️",
        "fallback_title": "Cảnh báo",
        "button_style": None,  # nút trung tính, tránh tạo hoảng loạn
        "lead": "",
    },
    "critical": {
        "emoji": "🚨",
        "fallback_title": "Sự cố khẩn cấp",
        "button_style": "danger",
        "lead": "",
    },
}


def _truncate(text: str, limit: int) -> str:
    """Cắt an toàn theo limit Slack, thêm dấu hiệu nếu bị cắt."""
    if text is None:
        return ""
    text = str(text)
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _context_line(host: str = "", metric: str = "", time: str = "", extra: str = "") -> str:
    """Gom metadata phụ thành 1 dòng context phân tách bằng `·` (chỉ phần có giá trị)."""
    parts = []
    if metric:
        parts.append(f"📈 {metric}")
    if host:
        parts.append(f"🖥️ {host}")
    if extra:
        parts.append(extra)
    if time:
        parts.append(f"🕒 {time}")
    return "  ·  ".join(parts)


def build_payload(
    kind: str,
    *,
    title: str,
    message: str,
    user: str = "",
    host: str = "",
    metric: str = "",
    time: str = "",
    context_extra: str = "",
    button_text: str = "",
    button_url: str = "",
    secondary_text: str = "",
    secondary_url: str = "",
    secondary_style: str = "danger",
) -> dict:
    """
    Dựng payload Slack Block Kit (≤5 blocks) cho 1 trong 3 loại notification.

    kind: "success" | "warning" | "critical"
    title: tiêu đề ngắn, đưa số liệu quan trọng nhất lên đây (→ header).
    message: nội dung chính, hỗ trợ mrkdwn (*@user*, `code`, *bold*).
    button_text/button_url: nút hành động chính (đặt cạnh section vấn đề).
    secondary_*: nút phụ — chỉ critical thường cần (vd Báo PagerDuty).

    Trả về dict payload sẵn sàng `json.dumps` → gửi webhook.
    """
    if kind not in KINDS:
        raise ValueError(f"kind không hợp lệ: {kind!r}. Chọn: {', '.join(KINDS)}")
    cfg = KINDS[kind]

    title = title.strip() or cfg["fallback_title"]
    header_text = _truncate(f"{cfg['emoji']} {title}", HEADER_LIMIT)

    # Gọi tên người dùng nếu có và message chưa tự nhắc → cá nhân hóa.
    body = message.strip()
    if user and f"@{user}" not in body and user not in body:
        body = f"*@{user}* {body}"
    body = _truncate(body, TEXT_LIMIT)

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": header_text, "emoji": True}},
    ]

    # Section chính. Nếu có nút đơn → gắn accessory để nút nằm cạnh nội dung.
    section = {"type": "section", "text": {"type": "mrkdwn", "text": body}}
    has_secondary = bool(secondary_text and secondary_url)
    if button_text and button_url and not has_secondary:
        accessory = {
            "type": "button",
            "text": {"type": "plain_text", "text": _truncate(button_text, 75), "emoji": True},
            "url": button_url,
        }
        if cfg["button_style"]:
            accessory["style"] = cfg["button_style"]
        section["accessory"] = accessory
    blocks.append(section)

    # Nhiều nút (thường critical: fix + escalate) → actions block riêng.
    if button_text and button_url and has_secondary:
        elements = [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": _truncate(button_text, 75), "emoji": True},
                "url": button_url,
            }
        ]
        if cfg["button_style"]:
            elements[0]["style"] = cfg["button_style"]
        sec_btn = {
            "type": "button",
            "text": {"type": "plain_text", "text": _truncate(secondary_text, 75), "emoji": True},
            "url": secondary_url,
        }
        if secondary_style:
            sec_btn["style"] = secondary_style
        elements.append(sec_btn)
        blocks.append({"type": "actions", "elements": elements})

    # Context: metadata phụ. Critical/warning thường có divider để tách "ồn" khỏi nội dung.
    ctx = _context_line(host=host, metric=metric, time=time, extra=context_extra)
    if ctx:
        if kind == "warning":
            blocks.append({"type": "divider"})
        blocks.append(
            {"type": "context", "elements": [{"type": "mrkdwn", "text": _truncate(ctx, TEXT_LIMIT)}]}
        )

    # Mobile-friendly guard: không bao giờ vượt 5 blocks.
    blocks = blocks[:5]

    # `text` fallback (notification preview + accessibility) — bắt buộc nên có.
    return {"text": _truncate(f"{cfg['emoji']} {title}", TEXT_LIMIT), "blocks": blocks}


def send(payload: dict, webhook: str = "") -> int:
    """Bắn payload vào Slack Incoming Webhook. Trả 0 nếu OK, !=0 nếu lỗi."""
    webhook = webhook or os.getenv("SLACK_WEBHOOK_URL", "")
    if not webhook:
        print("Thiếu webhook: đặt SLACK_WEBHOOK_URL hoặc --webhook", file=sys.stderr)
        return 2
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            ok = resp.read().decode("utf-8", "replace").strip()
            if ok != "ok":
                print(f"Slack trả về: {ok}", file=sys.stderr)
                return 1
            return 0
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"Lỗi mạng: {e.reason}", file=sys.stderr)
        return 1


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Sinh/gửi payload Slack Block Kit (3 tình huống).")
    ap.add_argument("kind", choices=list(KINDS), help="Loại thông báo")
    ap.add_argument("--title", required=True, help="Tiêu đề ngắn (số liệu quan trọng nhất)")
    ap.add_argument("--message", required=True, help="Nội dung chính (hỗ trợ mrkdwn)")
    ap.add_argument("--user", default="", help="Tên người nhận → gọi tên cá nhân hóa")
    ap.add_argument("--host", default="", help="Tên host/service (context)")
    ap.add_argument("--metric", default="", help="Số liệu (vd '92% (ngưỡng 85%)')")
    ap.add_argument("--time", default="", help="Thời gian (vd 14:30)")
    ap.add_argument("--context-extra", default="", help="Mảnh context thêm")
    ap.add_argument("--button-text", default="", help="Chữ trên nút hành động chính")
    ap.add_argument("--button-url", default="", help="URL nút hành động chính")
    ap.add_argument("--secondary-text", default="", help="Chữ nút phụ (vd Báo PagerDuty)")
    ap.add_argument("--secondary-url", default="", help="URL nút phụ")
    ap.add_argument("--webhook", default="", help="Webhook (mặc định env SLACK_WEBHOOK_URL)")
    ap.add_argument("--send", action="store_true", help="Gửi luôn vào Slack (mặc định chỉ in JSON)")
    args = ap.parse_args(argv)

    payload = build_payload(
        args.kind,
        title=args.title,
        message=args.message,
        user=args.user,
        host=args.host,
        metric=args.metric,
        time=args.time,
        context_extra=args.context_extra,
        button_text=args.button_text,
        button_url=args.button_url,
        secondary_text=args.secondary_text,
        secondary_url=args.secondary_url,
    )

    if args.send:
        return send(payload, args.webhook)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

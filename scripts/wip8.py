#!/usr/bin/env python3
"""wip8 — Read-only workspace tracker + live CI feed (WIP + TheoDoi8 gộp 1 shortcut).

Tái dựng "mình đang làm gì?" từ git status / diff / log / stash + branch context,
VÀ snapshot CI/CD (TheoDoi8) các commit gần nhất — gộp trong cùng 1 shortcut `wip8`.
Render ra terminal đẹp mắt: banner ASCII, panel bo góc, bảng có màu + emoji trạng thái.

READ-ONLY tuyệt đối: chỉ chạy lệnh git đọc (status/diff/log/stash/rev-list) + ĐỌC
report CI có sẵn (`data/theodoi8-report.json`, do CI tự sinh). KHÔNG sửa file, commit,
push, deploy, mở PR, KHÔNG gọi network, KHÔNG dùng token/secret.

Usage:
    python3 scripts/wip8.py            # full scan (WIP + TheoDoi8)
    python3 scripts/wip8.py --quick    # chỉ git status + branch (bỏ qua log dài)
    python3 scripts/wip8.py <path>     # chỉ inspect 1 file/folder
    python3 scripts/wip8.py --data     # JSON (cho Claude render 2 bảng markdown)

Chỉ dùng git CLI + rich + pyfiglet (stdlib còn lại). Mọi lệnh git/đọc file bọc
try/except → không bao giờ crash; thiếu rich/pyfiglet → fallback plain text; thiếu
report CI → TheoDoi8 fallback "chưa có dữ liệu".
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ICT = timezone(timedelta(hours=7))
ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "data" / "shortcuts" / "wip8.config.json"

# Default khi không có data/shortcuts/wip8.config.json (config TÙY CHỌN).
DEFAULT_CONFIG = {
    "show_wip": True,
    "show_theodoi8": True,
    "theodoi8_max_commits": 8,
    "theodoi8_report_paths": [
        "data/theodoi8-report.json",
        "static/data/theodoi8-report.json",
    ],
}

# ── Bảng màu thương hiệu (calm enterprise) ──────────────────────────────────
ACCENT = "#38bdf8"   # sky
GOOD = "#34d399"     # emerald
WARN = "#fbbf24"     # amber
DANGER = "#f87171"   # red
MUTED = "#94a3b8"    # slate


def _run(args: list[str]) -> str:
    """Chạy 1 lệnh git read-only, trả stdout (rỗng nếu lỗi)."""
    try:
        out = subprocess.run(
            ["git", *args],
            capture_output=True, text=True, timeout=15, check=False,
        )
        return out.stdout.strip()
    except Exception:
        return ""


def load_config() -> dict:
    """Đọc config TÙY CHỌN data/shortcuts/wip8.config.json (merge lên DEFAULT_CONFIG).

    Thiếu file / JSON hỏng → trả DEFAULT_CONFIG (read-only, không bao giờ crash).
    """
    cfg = dict(DEFAULT_CONFIG)
    try:
        if CONFIG_PATH.is_file():
            raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for k in DEFAULT_CONFIG:
                    if k in raw:
                        cfg[k] = raw[k]
    except Exception:
        pass
    return cfg


def load_theodoi8(config: dict | None = None) -> dict | None:
    """Đọc report CI/CD (TheoDoi8) có sẵn — KHÔNG gọi network, KHÔNG dùng token.

    Report do `scripts/build_theodoi8_report.py` (CI) tự sinh ra
    `data/theodoi8-report.json` + `static/data/theodoi8-report.json`. wip8 chỉ REUSE
    data đó → không trùng lệnh fetch, không secret, không fake data.

    Trả dict report (đã cắt commits theo `theodoi8_max_commits`) hoặc None nếu chưa
    có report (caller in fallback "chưa có dữ liệu").
    """
    config = config or load_config()
    for rel in config.get("theodoi8_report_paths", DEFAULT_CONFIG["theodoi8_report_paths"]):
        p = ROOT / rel
        try:
            if p.is_file():
                report = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(report, dict):
                    cap = int(config.get("theodoi8_max_commits", 8) or 8)
                    commits = report.get("commits")
                    if isinstance(commits, list):
                        report["commits"] = commits[:cap]
                    return report
        except Exception:
            continue
    return None


def gather(path: str | None = None, quick: bool = False) -> dict:
    data: dict = {}
    scope = [path] if path else []
    data["status"] = _run(["status", "--short", *scope])
    data["diffstat"] = _run(["diff", "--stat", "HEAD", *scope])
    data["branch"] = _run(["branch", "--show-current"]) or "(detached)"
    data["stash"] = _run(["stash", "list"])
    data["log"] = "" if quick else _run(["log", "--oneline", "-8", *scope])
    # ahead/behind so với upstream của branch hiện tại (nếu có)
    upstream = _run(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    data["upstream"] = upstream
    if upstream:
        lr = _run(["rev-list", "--left-right", "--count", f"{upstream}...HEAD"])
        data["aheadbehind"] = lr  # "<behind>\t<ahead>"
    else:
        data["aheadbehind"] = ""
    return data


def _classify(code: str) -> tuple[str, str]:
    """Map git short-status code → (label emoji, màu)."""
    c = code.strip()
    if "?" in c:
        return "🆕 untracked", WARN
    if "D" in c:
        return "🗑️ deleted", DANGER
    if "A" in c:
        return "🆕 new", GOOD
    if "R" in c:
        return "🔀 renamed", ACCENT
    if "M" in c:
        return "✏️ modified", ACCENT
    return f"• {c}", MUTED


def render(data: dict) -> None:
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        from rich import box
        import pyfiglet
    except Exception:
        _render_plain(data)
        return

    console = Console(force_terminal=True)
    now = datetime.now(ICT).strftime("%H:%M %d/%m/%Y")

    # ── Banner + brand bar (B-DNA: mark + name + tag) ───────────────────────
    banner = pyfiglet.figlet_format("wip8", font="small")
    console.print(f"[bold {ACCENT}]{banner}[/]", end="")
    console.print(f"[{MUTED}]Workspace DNA tracker · {now} (GMT+7) · read-only[/]")

    # ── Workspace health meter (B-DNA consistency-checker style) ─────────────
    h = data.get("health") or {}
    tone_color = {"pass": GOOD, "warn": WARN, "fail": DANGER}.get(h.get("tone"), MUTED)
    console.print(
        f"[{MUTED}]Workspace health[/]  [{tone_color}]{h.get('meter','')}[/]  "
        f"[bold {tone_color}]{h.get('score',0)}% · {h.get('verdict','')}[/]  "
        f"[{MUTED}]— {h.get('reason','')}[/]\n"
    )

    # ── 1. Tổng quan (panel) ────────────────────────────────────────────────
    ab = data.get("aheadbehind", "")
    sync = ""
    if ab and "\t" in ab:
        behind, ahead = ab.split("\t")[:2]
        color = GOOD if ahead == "0" and behind == "0" else WARN
        sync = f"[{color}]ahead {ahead} / behind {behind}[/]"
    clean = not data["status"]
    over = Table.grid(padding=(0, 2))
    over.add_column(style=f"bold {MUTED}", justify="right")
    over.add_column()
    over.add_row("🌿 Branch", f"[bold {ACCENT}]{data['branch']}[/]  {sync}")
    over.add_row("📦 Upstream", data.get("upstream") or "[dim]chưa set[/]")
    over.add_row(
        "📊 Trạng thái",
        f"[{GOOD}]✅ Working tree sạch[/]" if clean
        else f"[{WARN}]⚠ Có thay đổi chưa commit[/]",
    )
    over.add_row("🗂️ Stash", data["stash"].splitlines()[0] if data["stash"]
                 else "[dim]không có[/]")
    console.print(Panel(over, title="[bold]Tổng quan[/]", border_style=ACCENT,
                        box=box.ROUNDED, padding=(1, 2)))

    # ── 2. Files changed ────────────────────────────────────────────────────
    if clean:
        console.print(Panel(f"[{GOOD}]✅ Không có file thay đổi (0 staged / modified / untracked).[/]",
                            title="[bold]Files changed[/]", border_style=GOOD,
                            box=box.ROUNDED, padding=(0, 2)))
    else:
        ft = Table(box=box.SIMPLE_HEAVY, header_style=f"bold {ACCENT}",
                   expand=True, show_lines=False)
        ft.add_column("Loại", width=14)
        ft.add_column("File", overflow="fold")
        for line in data["status"].splitlines():
            code, _, fname = line.partition(" ")
            fname = line[3:] if len(line) > 3 else fname
            label, color = _classify(line[:2])
            ft.add_row(f"[{color}]{label}[/]", fname.strip())
        console.print(Panel(ft, title="[bold]Files changed[/]",
                            border_style=WARN, box=box.ROUNDED, padding=(0, 1)))

    # ── 3. Commits gần nhất ─────────────────────────────────────────────────
    if data["log"]:
        lt = Table(box=box.SIMPLE_HEAVY, header_style=f"bold {ACCENT}", expand=True)
        lt.add_column("SHA", style=WARN, width=9)
        lt.add_column("Commit", overflow="fold")
        for line in data["log"].splitlines():
            sha, _, msg = line.partition(" ")
            lt.add_row(sha, msg)
        console.print(Panel(lt, title="[bold]Commits gần nhất[/]",
                            border_style=MUTED, box=box.ROUNDED, padding=(0, 1)))

    # ── 4. TheoDoi8 — CI/CD feed (gộp vào wip8) ──────────────────────────────
    td = data.get("theodoi8")
    if td:
        head = (f"{td.get('status_icon','📡')} {td.get('status_label','TRỰC TIẾP')} · "
                f"{td.get('summary','')}  [{MUTED}]({td.get('generated_at_display','')})[/]")
        commits = td.get("commits") or []
        if commits:
            tt = Table(box=box.SIMPLE_HEAVY, header_style=f"bold {ACCENT}", expand=True)
            tt.add_column("Commit", style=WARN, width=9)
            tt.add_column("Message", overflow="fold")
            tt.add_column("Workflow", overflow="fold")
            tt.add_column("Trạng thái", width=14)
            for c in commits:
                tt.add_row(
                    str(c.get("sha", "")),
                    str(c.get("message", "")),
                    f"{c.get('run_name','')} #{c.get('run_number','')}",
                    f"{c.get('icon','')} {c.get('status','')}",
                )
            console.print(Panel(tt, title=f"[bold]TheoDoi8 · CI/CD[/]\n{head}",
                                border_style=ACCENT, box=box.ROUNDED, padding=(0, 1)))
        else:
            console.print(Panel(f"[{MUTED}]{head}\n\nChưa có commit/CI run nào để theo dõi.[/]",
                                title="[bold]TheoDoi8 · CI/CD[/]", border_style=MUTED,
                                box=box.ROUNDED, padding=(0, 2)))
    else:
        console.print(Panel(f"[{MUTED}]Chưa có dữ liệu CI (data/theodoi8-report.json). "
                            f"Report do CI tự sinh.[/]", title="[bold]TheoDoi8 · CI/CD[/]",
                            border_style=MUTED, box=box.ROUNDED, padding=(0, 2)))

    # ── Footer ──────────────────────────────────────────────────────────────
    console.print(f"\n[{MUTED}]Snapshot tại thời điểm gọi · gõ lại [bold]wip8[/bold] để refresh "
                  f"(WIP + TheoDoi8 CI feed gộp chung)[/]")


def _render_plain(data: dict) -> None:
    print("=== wip8 (plain fallback) ===")
    print("Branch:", data["branch"], data.get("aheadbehind", ""))
    print("Status:", data["status"] or "clean")
    print("Stash:", data["stash"] or "none")
    if data["log"]:
        print("Log:\n" + data["log"])
    td = data.get("theodoi8")
    if td:
        print(f"TheoDoi8: {td.get('status_label','')} · {td.get('summary','')}")
        for c in (td.get("commits") or []):
            print(f"  {c.get('icon','')} {c.get('sha','')} {c.get('message','')}")
    else:
        print("TheoDoi8: chưa có dữ liệu CI")


def health(data: dict) -> dict:
    """Tính 'Workspace health' theo tinh thần consistency-checker của B-DNA.

    Trả {score 0-100, verdict, tone, meter, reason}. Workspace tracker nên coi
    'dirty' = đang làm (WIP) chứ không phải hỏng; conflict mới là FAIL.
    """
    status = data.get("status", "")
    ab = data.get("aheadbehind", "")
    behind = ahead = 0
    if ab and "\t" in ab:
        b, a = ab.split("\t")[:2]
        behind, ahead = int(b or 0), int(a or 0)
    has_conflict = any(
        line[:2] in ("UU", "AA", "DD", "AU", "UA", "DU", "UD")
        for line in status.splitlines()
    )
    dirty = bool(status.strip())

    if has_conflict:
        score, verdict, tone, reason = 15, "BLOCKED", "fail", "Có conflict marker cần resolve"
    elif dirty:
        score, verdict, tone, reason = 45, "WIP", "warn", "Đang có thay đổi chưa commit"
    elif ahead > 0:
        score, verdict, tone, reason = 80, "PENDING", "warn", f"{ahead} commit chưa lên main (chờ pipeline)"
    elif behind > 0:
        score, verdict, tone, reason = 70, "BEHIND", "warn", f"Sau origin {behind} commit — cần sync"
    else:
        score, verdict, tone, reason = 100, "CLEAN", "pass", "Sạch & đồng bộ — không task dở"

    filled = round(score / 10)
    meter = "▰" * filled + "▱" * (10 - filled)
    return {"score": score, "verdict": verdict, "tone": tone,
            "meter": meter, "reason": reason,
            "ahead": ahead, "behind": behind, "dirty": dirty}


def main(argv: list[str]) -> int:
    quick = "--quick" in argv
    paths = [a for a in argv[1:] if not a.startswith("-")]
    path = paths[0] if paths else None
    config = load_config()
    data = gather(path=path, quick=quick)
    data["health"] = health(data)
    if config.get("show_theodoi8", True):
        data["theodoi8"] = load_theodoi8(config)
    if "--data" in argv:
        # JSON cho Claude render markdown (giao diện chat, B-DNA discipline). READ-ONLY.
        import json
        data["now_ict"] = datetime.now(ICT).strftime("%H:%M %d/%m/%Y")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    render(data)  # ANSI rich — chỉ dùng cho terminal local
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

+++
title = "Merge Conflict Khủng Hoảng: 7 PR Thất Bại Cùng Lúc"
description = "Câu chuyện thực tế: Ngày 18/6, 7 PR đều conflict đồng thời. Đó là lúc chúng tôi tự động hóa toàn bộ conflict resolution."
date = 2026-06-26
updated = 2026-06-26
slug = "merge-conflict-khung-hoang-7-pr-that-bai"
category = "Công nghệ"
tags = ["CI/CD", "DevOps", "merge-conflict", "automation", "zero-barrier"]
series = "merge-conflict-preflight"
extra.series_part = 1
extra.seo_keyword = "merge conflict resolution automation"
extra.thumbnail = "/images/blog/pr-conflict-crisis.jpg"
+++

## Ngày Merge Conflict Resolution Không Thể Nào Quên

Ngày 18 tháng 6, 2026 — 14:32 GMT+7. Tôi mở Slack và thấy 7 notification từ GitHub tất cả báo **merge conflict**. Không phải từ cùng một PR. Từ **7 cái khác nhau**.

Đây là câu chuyện về cách chúng tôi giải quyết **merge conflict resolution automation** — từ cơn khủng hoảng manual thành hệ thống tự động hoàn toàn (zero-barrier).

```
#945: Merge conflict on package.json, content/posting/abc.md
#946: Merge conflict on data/seo-scores.json
#947: Merge conflict on registry.json, templates/base.html
#948: Merge conflict on CHANGELOG.md
#949: Merge conflict on data/build-dashboard.json
#950: Merge conflict on scripts/config.yaml
#951: Merge conflict on 8 files (!)
```

Mỗi PR chạy tốt trên nhánh riêng. Mỗi cái đều pass QA. Nhưng khi cùng merge vào `main` cùng lúc — **bùm!** Tất cả conflict.

**Tổng thời gian resolve:** 3 giờ 45 phút.  
**Số lần phải rebase:** 7 lần.  
**Số lần `git pull` lỡ cách:** 5 lần.  
**Câu nói phổ biến nhất:** "À ơi, cái conflict này đã bị fix rồi mà sao vẫn còn?"

---

## Tại Sao Nó Xảy Ra?

Repo chúng tôi có **50+ microservices**. Team 8 người. Code commit rate cao. Khi ai đó commit vào `main`, CI/CD chạy 15+ workflow:

- Zola build
- SEO audit
- Performance check
- Image optimization
- Link validation
- Analytics update
- Dashboard regeneration
- ...

**Tất cả những cái này đều tạo file thay đổi:** `data/scores.json`, `data/related.json`, `data/ga-stats.json`, v.v.

Từng PR lấy snapshot của data files từ thời điểm nó được tạo. Nhưng `main` thì cập nhật liên tục. Khi PR được merge cách nhau 30 phút, data files đã lạc hậu rồi.

**Ví dụ:**

```
14:00 — PR #945 được tạo
        data/seo-scores.json = v1.0 (4 entries)
        
14:15 — PR #946 được tạo
        data/seo-scores.json = v1.0 (vẫn cũ)
        
14:30 — PR #945 merge vào main
        Workflow chạy → data/seo-scores.json = v2.0 (6 entries)
        
14:40 — PR #946 cố merge
        Git: "conflict! PR có v1.0, main có v2.0"
        ❌ Merge bị block
```

---

## Panic Mode: Manual Conflict Resolution

**14:35 PM** — Tôi ngồi xuống để resolve conflicts. Mang máy lập từng file.

```bash
git fetch origin main
git merge origin/main
# CONFLICT (content merge): data/seo-scores.json

vim data/seo-scores.json
# Cái file này 500 dòng JSON...
# <<<<<<< HEAD
# ... 4 entries
# =======
# ... 6 entries
# >>>>>>> origin/main

# Phải hiểu: cái nào là mới? Main có entries gì thêm?
# Phải chọn cái nào để giữ? Cái cũ hay cái mới?
```

**Problem #1:** Mình không biết data files được generated từ đâu. Có script nào chạy để regenerate không?

**Problem #2:** Nếu chọn `--ours` (giữ PR), thì sẽ mất updates từ main. Nếu chọn `--theirs` (lấy main), thì PR thay đổi bị xóa.

**Problem #3:** `registry.json` conflict thì cần merge cả hai phía. Nhưng Git merge không thông minh như thế.

**Problem #4:** Sau khi resolve manually, code có pass build không? Có pass QA không? Chẳng có ai kiểm tra cho tôi.

→ 45 phút cho PR #945.  
→ 38 phút cho PR #946.  
→ 52 phút cho PR #947. (Cái này lại có conflict ở templates/base.html, phải inspect cả template logic)  
→ ...

---

## Lesson #1: Con Người Không Scale

Cuộc họp ngắn với team:

**Tôi:** "Conflict resolution không scale. Nếu team lớn hơn, chúng ta sẽ phải thêm người chỉ để babysit PR."

**Người khác:** "Có cách gì để phát hiện conflict sớm hơn không?"

**Người khác:** "Vì sao không auto-resolve cơ?"

**Tôi:** "... Tuyệt vời. Tôi sẽ làm điều đó. Đúng là ZERO_BARRIER hành động."

---

## Tầm Quan Trọng Của Merge Conflict Resolution Automation

Tôi quét qua 7 PR và nhận ra pattern:

- **#945, #946, #949:** Conflict ở `data/*.json` — **Luôn lấy main**
- **#947:** Conflict ở `registry.json` — **Cần merge cả hai**
- **#948:** Conflict ở `CHANGELOG.md` — **Cần combine entries**
- **#950:** Conflict ở `scripts/config.yaml` — **Syntax hỏng, phải fix bằng tay**
- **#951:** Conflict ở `templates/base.html` — **Logic template, phải hiểu intent**

→ **70% của conflict là predictable.**

---

## Lesson #3: Merge Strategy Phải Là Quy Trình

Không phải là "resolve tùy tâm", mà là **protocol**:

```
IF file is in data/:
    THEN take main's version (always freshest)
    AND regenerate if there's a script
    
IF file is registry.json:
    THEN merge both sides (union merge)
    
IF file is CHANGELOG.md:
    THEN combine entries (don't discard)
    
IF file is template/code:
    THEN manual review (preserve intent)
    
IF file is content:
    THEN keep PR's version (never overwrite content)
```

---

## Lesson #4: Preflight Check Cần

Nếu conflict được phát hiện **sau khi merge** (thì đã quá muộn), thì phải phát hiện **trước khi merge**.

```
PR tạo → Check merge với main ngay lập tức
         → Nếu conflict → báo dev ngay
         → Không chờ 3 ngày
```

---

## Kết Thúc Ngày Hôm Đó

**18:17 PM** — PR #951 (cái có 8 file conflict) cuối cùng được merge.

Tôi có:
- ✅ Resolve 7 PR
- ✅ Rebuild lại 5 lần (vì QA fail sau khi resolve)
- ✅ Push 12 commit để fix QA issues
- ✅ Không bao giờ muốn làm điều này lần nữa

**Quyết định:** Ngày mai, tôi code **Merge Conflict Preflight system**. Không con người resolve conflict nữa. Máy làm.

---

## Tài Liệu Tham Khảo

- [GitHub Merge Conflict Documentation](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/addressing-merge-conflicts)
- [Git Merge Documentation](https://git-scm.com/docs/git-merge)
- [CI/CD Best Practices](https://www.atlassian.com/continuous-delivery/ci-cd-best-practices)

---

## Phần Tiếp Theo

[Part 2: Xây dựng Conflict Resolution Framework](../xay-dung-conflict-resolution-framework) — Tôi thiết kế hệ thống và viết code.

---

*Series này dựa trên sự kiện thực tế từ repo Seomoney. Mỗi bài giáo dục về CI/CD automation + zero-barrier doctrine.*

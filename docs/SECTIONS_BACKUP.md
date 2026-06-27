# Sections Backup & Restore — không mất chuyên mục khi đổi theme

> Mỗi "theme" trong repo này là **một branch full-repo riêng**. Một trang công cụ/
> tính năng (vd `content-direction`, `calendar`) được định nghĩa bởi 5+ file rải rác:
> `content/tools/<x>.md` + `templates/<x>.html` + `sass/_<x>.scss` (+ `@import` trong
> `sass/site.scss`) + `static/js/<x>/*` + 1 mục menu trong `config.toml` (+ đôi khi
> script generator + `data/*.json`). Đổi sang branch thiếu **bất kỳ** mảnh nào →
> chuyên mục im lặng biến mất. Bộ công cụ này gom tất cả mảnh đó lại để khôi phục.

## TL;DR

```bash
# TRƯỚC khi đổi/thử theme: chụp lại toàn bộ chuyên mục + bài viết
python3 scripts/backup_sections.py            # → sections-backup/ (commit cái này)

# SAU khi đổi theme, nếu mất chuyên mục: khôi phục những file còn thiếu
python3 scripts/restore_sections.py                       # khôi phục mọi mục còn thiếu
python3 scripts/restore_sections.py --only calendar       # chỉ 1 mục
python3 scripts/restore_sections.py --apply-menu          # +  chèn lại mục menu
```

## Backup — `scripts/backup_sections.py`

Quét toàn repo, sinh:

- `sections-backup/manifest.json` — **kiểm kê đầy đủ**: tất cả bài viết (`posts`),
  section (`_index.md`), feature page (template riêng) kèm dependency đã resolve
  (template, macro, scss partial, js, data, generator), `taxonomies`, khối `menu`
  thô và **thứ tự `@import` của `sass/site.scss`**.
- `sections-backup/files/` — bản sao thật của các file định nghĩa section/feature +
  snapshot `config.toml`, `categories.json`. File theme-core (reset, navbar,
  `base.html`, `page.html`…) **không** được copy — chúng có ở mọi theme, không bao
  giờ mất; chỉ file feature mới được gom → bundle gọn, restore an toàn.

| Flag | Ý nghĩa |
|------|---------|
| (mặc định) | Backup đầy đủ, **gồm** markdown bài viết |
| `--no-posts` | Bỏ copy markdown bài viết (vẫn kiểm kê trong manifest) → bundle nhẹ |
| `--print` | In thêm bảng tóm tắt feature page |

Dependency được resolve bằng **parse + quy ước**: template `foo.html` →
`sass/_foo.scss`; mọi `js/<dir>/*.js` trong template → copy js **và** kéo theo
`sass/_<dir>.scss` (nhờ vậy `_whiteboard.scss` đi cùng `calendar.html`);
`{% import %}`/`{% include %}` → macro/partial; `load_data(path=…)` → data file;
`scripts/<tên>.py` → generator.

## Restore — `scripts/restore_sections.py`

Hai nguồn:

1. **Bundle local (mặc định)** — đọc `sections-backup/manifest.json` + copy file từ
   `sections-backup/files/` về working tree.
2. **Từ một git ref** (`--from-ref <branch|sha>`) — khôi phục chuyên mục **thẳng từ
   branch theme khác**, kể cả branch chưa từng backup. Với mỗi mục yêu cầu, nó đọc
   content file + template từ ref, resolve dependency y như backup, rồi materialize
   bằng `git show`. Đây là đường để "đổi theme xong mất `content-direction`/`calendar`
   → kéo lại từ branch cũ".

```bash
# Kéo content-direction + calendar từ theme cũ về theme hiện tại
python3 scripts/restore_sections.py \
    --from-ref origin/claude/blog-theme-rollback-y16qfp \
    --only content-direction calendar --apply-menu
```

| Flag | Ý nghĩa |
|------|---------|
| `--list` | Liệt kê các mục có thể khôi phục rồi thoát |
| `--only <tên…>` | Chỉ khôi phục mục khớp tên (stem/title/alias) |
| `--from-ref <ref>` | Khôi phục từ git ref thay vì bundle local |
| `--overwrite` | Ghi đè cả file đã tồn tại (mặc định: chỉ điền file **thiếu**) |
| `--apply-menu` | Chèn mục menu `{ url, name }` còn thiếu vào nhóm "Tiện ích" |
| `--no-build` | Bỏ bước kiểm tra `zola build` |
| `--dry-run` | Hiện hành động, không ghi file |

**An toàn:** mặc định **fill-missing** — file đã có trong working tree thì giữ
nguyên, nên restore lên theme MỚI không bao giờ đè theme mới; chỉ điền lại mục
theme mới làm rớt. `@import` thiếu trong `sass/site.scss` được thêm lại (trước
marker `// site.scss imports end` nếu có).

## Quy trình khuyến nghị

1. Làm việc trên theme hiện tại → `python3 scripts/backup_sections.py` → commit
   `sections-backup/`.
2. Tạo branch theme mới từ branch này (bundle đi theo).
3. Đổi `templates/` + `sass/` thoải mái. Build thử.
4. Thiếu chuyên mục nào → `python3 scripts/restore_sections.py --only <tên> --apply-menu`.
5. `zola build` xanh → xong.

## Giới hạn đã biết

- Generator Python (vd `content_direction.py`) có thể `import` module nội bộ
  (`link_utils`, `related_engine`) — restore kéo generator nhưng **không** tự dò
  các import đó. Trang vẫn render nhờ `data/*.json` đã bundle; chạy lại generator
  cần các module đó có mặt.
- Chèn menu tự động chỉ nhắm nhóm **"Tiện ích"** (mục `{ url, name }` đơn). Mục
  mega-menu lồng nhau được **báo cáo** để chèn tay.
- Test: `python3 -m unittest scripts.test_sections_backup_restore -v`.

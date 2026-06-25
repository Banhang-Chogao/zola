# `ff.py` — Full-Fix AI-Agent

> Thay thế (local) shortcut `ff` Claude-driven bằng Python script gọi
> trực tiếp AI SDK. Mục đích: phát hiện + chẩn đoán lỗi `zola build`
> ngay trên máy dev, KHÔNG đụng vào source file.

## 1. Cài đặt 1 lần

```bash
# Cài dependencies (anthropic + loguru + ruff + mypy + pydantic + pre-commit)
pip install -r scripts/requirements-ff.txt

# Cài pre-commit hook (chạy ruff + mypy + check-toml trước mỗi commit)
pre-commit install

# Export API key (chọn 1)
# Claude chỉ khi heuristics confidence < 70%:
export AI_DIAGNOSE_USE_CLAUDE=1
export ANTHROPIC_API_KEY="sk-ant-..."
# hoặc:
export FF_AI_PROVIDER=openai
export OPENAI_API_KEY="sk-..."
```

## 2. Chạy ff.py

| Lệnh | Khi nào dùng |
|---|---|
| `python3 scripts/ff.py` | Build thường + auto-diagnose nếu fail |
| `python3 scripts/ff.py --file templates/zx.html` | Ép AI inspect file cụ thể |
| `python3 scripts/ff.py --dry-run` | Chỉ classify pattern, KHÔNG gọi AI (tiết kiệm token) |
| `python3 scripts/ff.py --teach "tera_var: typo trong key 'ga_stats._status'"` | Dạy lại AI khi đoán sai |

## 3. Log files (debug)

Tất cả ghi vào `.ff/` (đã gitignore):

| File | Dùng để |
|---|---|
| `.ff/ff.log` | Toàn bộ debug log (rotation 2MB, retain 10) — `tail -f .ff/ff.log` khi script đang chạy |
| `.ff/teach.jsonl` | Lịch sử feedback `--teach`. Mỗi lần build tiếp theo, ff.py inject 5 entry gần nhất vào prompt làm hint |

## 4. Workflow khi `ff.py` báo lỗi

1. **Đọc `=== STDERR EXCERPT ===`** đầu tiên — pattern thật từ Zola.
2. **Đọc `=== AI FIX SUGGESTION ===`** — gồm 3 phần:
   - Nguyên nhân gốc
   - Diff snippet
   - Cách verify
3. **Apply manually** vào file bằng editor (script KHÔNG tự sửa).
4. **Re-run** `python3 scripts/ff.py` để verify.
5. Nếu AI đoán sai → `python3 scripts/ff.py --teach "đúng pattern là X vì Y"`.
6. Nếu cùng lỗi lặp lại → mở `.ff/ff.log` xem prompt đã gửi → cải thiện
   `ERROR_PATTERNS` trong `scripts/ff.py` (thêm regex mới).

## 5. Bộ công cụ song hành

| Tool | Nhiệm vụ | Khi nào trigger |
|---|---|---|
| **Ruff** | Lint + format Python (.py) | Pre-commit hook + `ruff check scripts/` thủ công |
| **Mypy** | Type-check `scripts/`, `services/` | Pre-commit + `mypy scripts/` khi sửa script lớn |
| **Loguru** | Log file `.ff/ff.log` | Tự động bên trong `ff.py` |
| **Pydantic** | Validate config (vd: `data/*.json` schema cho GA stats) | Khi tạo model class mới — hiện chưa wire vào ff.py |
| **pre-commit** | Chạy Ruff + Mypy + check-toml/yaml trước commit | Tự động khi `git commit` |

## 6. Safety guarantees

- `ff.py` **KHÔNG** import `os.write`, không gọi `Path.write_text` ngoài
  `.ff/teach.jsonl` (file log riêng của chính nó).
- AI prompt **bắt buộc** trả về diff snippet, KHÔNG full rewrite.
- File `config.toml`, `templates/*`, `sass/*` được đọc qua `read_suspect()`
  với cap 12k chars để tránh leak token.
- `MAX_FILE_CHARS = 12_000` giới hạn payload gửi AI.

## 7. Tới đây vẫn chưa đủ?

- Pin sub-version model qua `FF_AI_MODEL` (vd: `claude-opus-4-7`).
- Plug Pydantic vào để validate `data/scores.json`, `data/ga-stats.json`
  schema trước build — bắt lỗi sớm hơn cả ff.py.
- Thêm `pre-commit` stage cho `qa_check.py` đã có sẵn.

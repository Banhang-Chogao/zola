# GitHub Actions — permissions & workflow approval

## Vì sao workflow từng bị chặn (action_required)

| Nguyên nhân | Triệu chứng | Fix trong repo |
|-------------|-------------|----------------|
| **GITHUB_TOKEN tạo PR** | PR `github-actions[bot]` → `pull_request` workflows không tự chạy; UI bắt "Approve workflows" | `workflow_run` relay trong `qa.yml` + `pr-policy.yml` |
| **`pr-approval.yml` (đã xóa)** | Check `PR Manual Approval / manual-approval` fail mọi PR | Đã remove — dùng branch protection + review thủ công khi cần |
| **Fork PR** | Workflow chờ approval maintainer | Giữ GitHub Setting (fork protection) — không bypass bằng code |
| **Deploy `environment: github-pages`** | Chỉ job deploy trên `push main` — không ảnh hưởng PR QA | Tách deploy production; QA/chore không dùng environment gate |

## GitHub repo Settings (admin — không commit được)

**Settings → Actions → General**

| Setting | Khuyến nghị |
|---------|-------------|
| Actions permissions | **Allow all actions** (hoặc allowlist org) |
| Workflow permissions | **Read and write** (cho bot merge, PR, pages) |
| Fork PR workflows | Bật; **Require approval for outside collaborators** (giữ cho fork) |
| Approval for running fork PR workflows | Chỉ fork — same-repo bot PR dùng relay |

**Settings → Environments → `github-pages`**

- Chỉ `deploy.yml` job `deploy` dùng environment này (production).
- Không gắn environment vào QA / chore / bot PR workflows.

**Settings → Branches → `main`**

- Required checks: `QA Gatekeeper`, `PR Policy`
- Required approvals: **0** (auto-merge policy)
- Không thêm check `manual-approval`

## Tùy chọn: `WORKFLOW_BOT_PAT` (secret)

Fine-grained hoặc classic PAT của repo admin (scope: `contents`, `pull_requests`).

Khi set secret `WORKFLOW_BOT_PAT`, `push_via_pr.sh` push + mở PR bằng PAT → `pull_request` workflows chạy trực tiếp (không cần relay).

Không bắt buộc nếu relay đã bật.

## Workflow relay (bot PR)

Các workflow tạo PR qua `push_via_pr.sh` kích relay sau khi hoàn tất:

- `qa.yml` (`QA Gatekeeper`) — checkout `workflow_run.head_sha`
- `pr-policy.yml` (`PR Policy`) — resolve PR qua API, chạy `pr_policy_checks.sh`

Danh sách nguồn: xem `workflow_run.workflows` trong `qa.yml` / `pr-policy.yml`.

## Rule an toàn (không đổi)

- Không push trực tiếp `main` (`main-guard.yml`)
- Không auto-merge PR nhạy cảm (label `no-auto-merge`)
- Deploy production qua `deploy.yml` + environment `github-pages`
- Fork/untrusted: giữ approval ở GitHub Settings
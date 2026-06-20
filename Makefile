# Makefile — shortcut targets cho dev tooling của blog.

.PHONY: preflight-conflict preflight-conflict-json install-preflight-hook

# Quét conflict với origin/main TRƯỚC commit/PR (read-only, không đụng working tree).
preflight-conflict:
	python3 scripts/preflight_conflict_check.py

# Bản JSON cho automation.
preflight-conflict-json:
	python3 scripts/preflight_conflict_check.py --json

# Cài git pre-commit hook chạy preflight checker (chặn khi risk HIGH).
install-preflight-hook:
	python3 scripts/install_precommit_conflict_hook.py

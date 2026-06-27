#!/bin/bash
# Preflight validation for critical workflows
# Catches configuration errors early before expensive steps run
# Exit codes:
#   0: All checks passed
#   1: Warning (non-critical)
#   2: Error (should block workflow)

set -u  # Error on undefined variables

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'  # No Color

WARNINGS=0
ERRORS=0

echo "🔍 Running preflight checks..."
echo ""

# Check 1: GITHUB_TOKEN exists
echo "Check 1: GitHub token availability"
if [ -z "${GITHUB_TOKEN:-}" ] && [ -z "${GH_TOKEN:-}" ]; then
  echo -e "${RED}❌ FAIL: GITHUB_TOKEN / GH_TOKEN not set${NC}"
  echo "   This step requires GitHub API access."
  ERRORS=$((ERRORS + 1))
else
  echo -e "${GREEN}✓ GitHub token available${NC}"
fi

# Check 2: gh CLI available
echo ""
echo "Check 2: GitHub CLI (gh) installation"
if ! command -v gh &> /dev/null; then
  echo -e "${YELLOW}⚠️  WARNING: gh CLI not found${NC}"
  echo "   Some features will be disabled (gh api calls)"
  WARNINGS=$((WARNINGS + 1))
else
  GH_VERSION=$(gh --version 2>/dev/null | head -1 || echo "unknown")
  echo -e "${GREEN}✓ gh CLI found: $GH_VERSION${NC}"
fi

# Check 3: Python available
echo ""
echo "Check 3: Python 3.x installation"
if ! command -v python3 &> /dev/null; then
  echo -e "${RED}❌ FAIL: python3 not found${NC}"
  ERRORS=$((ERRORS + 1))
else
  PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
  echo -e "${GREEN}✓ Python 3 found: $PYTHON_VERSION${NC}"
fi

# Check 4: Required Python packages
echo ""
echo "Check 4: Python dependencies"
REQUIRED_PACKAGES=("yaml" "urllib3" "json")
MISSING_PACKAGES=()

for pkg in "${REQUIRED_PACKAGES[@]}"; do
  if ! python3 -c "import $pkg" 2>/dev/null; then
    MISSING_PACKAGES+=("$pkg")
  fi
done

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
  echo -e "${YELLOW}⚠️  Missing Python packages: ${MISSING_PACKAGES[*]}${NC}"
  WARNINGS=$((WARNINGS + 1))
else
  echo -e "${GREEN}✓ All required Python packages available${NC}"
fi

# Check 5: Required scripts exist
echo ""
echo "Check 5: Required scripts and configs"
REQUIRED_FILES=(
  "scripts/qa_check.py"
  "scripts/build_references.py"
  "config.toml"
  ".github/workflows/deploy.yml"
)

MISSING_FILES=()
for file in "${REQUIRED_FILES[@]}"; do
  if [ ! -f "$REPO_ROOT/$file" ]; then
    MISSING_FILES+=("$file")
  fi
done

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
  echo -e "${RED}❌ Missing required files: ${MISSING_FILES[*]}${NC}"
  ERRORS=$((ERRORS + 1))
else
  echo -e "${GREEN}✓ All required files found${NC}"
fi

# Check 6: Git repository status
echo ""
echo "Check 6: Git repository"
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
  echo -e "${RED}❌ FAIL: Not inside a Git repository${NC}"
  ERRORS=$((ERRORS + 1))
else
  BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
  COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
  echo -e "${GREEN}✓ Git repository OK (branch: $BRANCH, commit: $COMMIT)${NC}"
fi

# Check 7: Network connectivity (optional, best-effort)
echo ""
echo "Check 7: External service connectivity (optional)"
echo "  Testing connectivity to GitHub API..."
if timeout 5 curl -s -I https://api.github.com > /dev/null 2>&1; then
  echo -e "  ${GREEN}✓ GitHub API reachable${NC}"
else
  echo -e "  ${YELLOW}⚠️  Cannot reach GitHub API (offline environment?)${NC}"
  WARNINGS=$((WARNINGS + 1))
fi

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
  echo -e "${GREEN}✅ All preflight checks passed${NC}"
  exit 0
elif [ $ERRORS -eq 0 ]; then
  echo -e "${YELLOW}⚠️  Preflight checks passed with $WARNINGS warning(s)${NC}"
  echo "   Some features may be degraded. Check logs above."
  exit 1
else
  echo -e "${RED}❌ Preflight checks FAILED with $ERRORS error(s)${NC}"
  echo ""
  echo "Remediation:"
  if [ -z "${GITHUB_TOKEN:-}" ] && [ -z "${GH_TOKEN:-}" ]; then
    echo "  1. Add GITHUB_TOKEN secret to GitHub Actions"
    echo "     Settings → Secrets and variables → Actions → New secret"
  fi
  if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    echo "  2. Verify repository is properly cloned"
    echo "     Missing: ${MISSING_FILES[*]}"
  fi
  exit 2
fi

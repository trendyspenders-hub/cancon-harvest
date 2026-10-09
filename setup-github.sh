#!/usr/bin/env bash
# One-time: turn this folder into the private GitHub repo "cancon-harvest"
# (the mailbox Kimi reads from). Needs `gh auth login` once.
set -euo pipefail
cd "$(dirname "$0")"
REPO=cancon-harvest

cat > .gitignore <<'IGN'
test.txt
batch*.txt
*.orig
__pycache__/
.DS_Store
IGN

[ -d .git ] || git init -q -b main
git add .gitignore CLAUDE.md README.md harvest_topic_local.py artists.txt \
        github-actions-workflow.yml setup-github.sh push-results.sh mcp relay
for f in tracks_local.jsonl harvest_done.jsonl; do [ -f "$f" ] && git add "$f"; done
git diff --cached --quiet || git commit -q -m "Harvest kit"

if git remote get-url origin >/dev/null 2>&1; then
  git push -u origin main
elif gh repo view "$REPO" >/dev/null 2>&1; then
  git remote add origin "$(gh repo view "$REPO" --json url -q .url).git"
  git push -u origin main
else
  gh repo create "$REPO" --private --source=. --remote=origin --push
fi

OWNER=$(gh api user -q .login)
echo
echo "Ready: github.com/$OWNER/$REPO (private)"
echo "Tell Kimi: sync the harvest from github:$OWNER/$REPO"

#!/usr/bin/env bash
# Publish the current commit to the Hugging Face Space (a free Docker Space).
#
#   bash scripts/deploy_space.sh             # builds the Space commit and pushes it (asks for your Hugging Face login)
#   bash scripts/deploy_space.sh --dry-run   # builds it and shows the Space README header, pushes nothing
#
# A Space reads its settings from a small header at the top of README.md. The GitHub README stays clean: this script
# adds the header to a copy of the tree and pushes that to the Space only. Needs a git remote named "hf":
#   git remote add hf https://huggingface.co/spaces/<user>/<space>
set -euo pipefail
cd "$(dirname "$0")/.."

tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
{
  printf -- '---\ntitle: AI Phishing Detector\nemoji: 🎣\ncolorFrom: blue\ncolorTo: red\nsdk: docker\napp_port: 8501\npinned: false\n'
  printf -- 'short_description: Paste an email, see if it looks like phishing and why.\n---\n\n'
  cat README.md
} > "$tmp/README.md"

export GIT_INDEX_FILE="$tmp/index"
git read-tree HEAD
git update-index --add --cacheinfo "100644,$(git hash-object -w "$tmp/README.md"),README.md"
tree="$(git write-tree)"
unset GIT_INDEX_FILE
commit="$(git commit-tree "$tree" -m "AI Phishing Detector: DistilBERT email classifier with a Streamlit app")"

echo "Space commit: $commit"
git show "$commit:README.md" | head -11
if [ "${1:-}" = "--dry-run" ]; then echo "(dry run: nothing pushed)"; exit 0; fi
git push --force hf "$commit:refs/heads/main"
echo "Pushed. The Space rebuilds for a few minutes, then is live."

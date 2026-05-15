#!/usr/bin/env bash
# Point the Hugging Face Space git remote at SSH and print the push command.
# Override defaults: HF_USER, HF_SPACE_SLUG, HUGGINGFACE_REMOTE
set -euo pipefail

REMOTE="${HUGGINGFACE_REMOTE:-huggingface}"
USER="${HF_USER:-habeneyasu}"
SLUG="${HF_SPACE_SLUG:-Agentic-AI-Fraud-Investigator}"
SSH_URL="git@hf.co:spaces/${USER}/${SLUG}"

if git remote get-url "${REMOTE}" &>/dev/null; then
  git remote set-url "${REMOTE}" "${SSH_URL}"
  echo "Updated remote '${REMOTE}' -> ${SSH_URL}"
else
  git remote add "${REMOTE}" "${SSH_URL}"
  echo "Added remote '${REMOTE}' -> ${SSH_URL}"
fi

echo ""
echo "Next:"
echo "  1. Ensure https://huggingface.co/settings/keys has your SSH public key."
echo "  2. Run:  ssh -T git@hf.co"
echo "  3. Push:  git push ${REMOTE} main:main"
echo ""
echo "If push is rejected, see deploy/HUGGINGFACE.md → Quick fix (merge or --force)."

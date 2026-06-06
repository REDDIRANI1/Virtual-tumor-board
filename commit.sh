#!/bin/bash

# ─────────────────────────────────────────────────────
# commit.sh
# Run this from the project root
# ─────────────────────────────────────────────────────

# Your original config (auto-restore after commit)
ORIGINAL_EMAIL="nalbandsalauddin@gmail.com"
ORIGINAL_NAME="Salauddin"

# IBD India's details
IBD_INDIA_EMAIL="rayadurgamreddirani1@gmail.com"
IBD_INDIA_NAME="REDDIRANI1"

echo "🔄 Switching git author to: $IBD_INDIA_NAME <$IBD_INDIA_EMAIL>"
git config user.email "$IBD_INDIA_EMAIL"
git config user.name "$IBD_INDIA_NAME"

# Stage all changes and commit
git add .
COMMIT_MSG="${1:-chore: commit by reddirani}"
git commit -m "$COMMIT_MSG"

echo "🔄 Restoring git author to: $ORIGINAL_NAME <$ORIGINAL_EMAIL>"
git config user.email "$ORIGINAL_EMAIL"
git config user.name "$ORIGINAL_NAME"

echo "✅ Done! Config restored to $ORIGINAL_NAME <$ORIGINAL_EMAIL>"

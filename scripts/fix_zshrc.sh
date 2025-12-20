#!/usr/bin/env bash
set -euo pipefail

# Safe script to patch ~/.zshrc:
# - Backup existing ~/.zshrc to ~/.zshrc.storyteller.bak.TIMESTAMP
# - Remove any existing storyteller block marked with "# storyteller: python3.11 + locale"
# - Append a safe block that exports PATH (only if python3.11 exists) and locale variables

ZSHRC="${ZSHRC:-$HOME/.zshrc}"
BACKUP="${ZSHRC}.storyteller.bak.$(date +%Y%m%d%H%M%S)"

echo "Backing up ${ZSHRC} -> ${BACKUP}"
cp "$ZSHRC" "$BACKUP"

MARK="# storyteller: python3.11 + locale"

echo "Removing any existing storyteller block from ${ZSHRC}"
awk -v mark="$MARK" '
  BEGIN { found=0 }
  $0 ~ mark { found=1; next }
  found && $0 ~ /^$/ { found=0; next }
  !found { print }
' "$BACKUP" > "${ZSHRC}.tmp"

mv "${ZSHRC}.tmp" "$ZSHRC"

echo "Appending safe storyteller block to ${ZSHRC}"
cat >> "$ZSHRC" <<'EOF'
# storyteller: python3.11 + locale
if command -v python3.11 >/dev/null 2>&1; then
  # Prefer Homebrew python3.11 if available
  if brew_prefix="$(brew --prefix python@3.11 2>/dev/null)"; then
    export PATH="${brew_prefix}/bin:$PATH"
  else
    # common Homebrew prefix on Apple Silicon
    export PATH="/opt/homebrew/bin:$PATH"
  fi
fi
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export PYTHONUTF8=1
EOF

echo "Patch applied. To activate now run:"
echo "  source \"$ZSHRC\""
echo "A backup was saved to: $BACKUP"



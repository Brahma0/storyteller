#!/usr/bin/env bash
set -euo pipefail

# Adds direnv hook to the user's shell rc file (idempotent).
# Supports: zsh (~/.zshrc), bash (~/.bashrc or ~/.bash_profile), fish (~/.config/fish/config.fish)
# Usage:
#   chmod +x scripts/add_direnv_hook.sh
#   ./scripts/add_direnv_hook.sh

detect_shell() {
  if [ -n "${SHELL:-}" ]; then
    basename "$SHELL"
    return
  fi
  # Fallback: try to detect from process tree
  ps -p "$$" -o comm= | awk -F/ '{print $NF}'
}

add_line_if_missing() {
  local file="$1"
  local line="$2"
  mkdir -p "$(dirname "$file")"
  if [ -f "$file" ]; then
    if grep -Fxq "$line" "$file"; then
      printf "Already present in %s\n" "$file"
      return 0
    fi
  fi
  printf "%s\n" "$line" >> "$file"
  printf "Appended hook to %s\n" "$file"
}

main() {
  sh="$(detect_shell)"
  echo "Detected shell: $sh"

  case "$sh" in
    zsh)
      rc="$HOME/.zshrc"
      hook='eval "$(direnv hook zsh)"'
      add_line_if_missing "$rc" "$hook"
      echo "To activate now: run 'source $rc' or open a new terminal."
      ;;
    bash)
      # prefer ~/.bashrc; on macOS ~/.bash_profile may be used
      if [ -f "$HOME/.bashrc" ]; then
        rc="$HOME/.bashrc"
      else
        rc="$HOME/.bash_profile"
      fi
      hook='eval "$(direnv hook bash)"'
      add_line_if_missing "$rc" "$hook"
      echo "To activate now: run 'source $rc' or open a new terminal."
      ;;
    fish)
      rc="$HOME/.config/fish/config.fish"
      hook='direnv hook fish | source'
      add_line_if_missing "$rc" "$hook"
      echo "To activate now: run 'source $rc' or open a new terminal."
      ;;
    *)
      echo "Unknown shell '$sh'."
      echo "You can manually add one of the following lines to your shell rc:"
      echo "  zsh:   eval \"\$(direnv hook zsh)\""
      echo "  bash:  eval \"\$(direnv hook bash)\""
      echo "  fish:  direnv hook fish | source"
      exit 1
      ;;
  esac

  echo "Done. If direnv is installed, run 'direnv allow' inside the project directory to approve .envrc."
}

main "$@"



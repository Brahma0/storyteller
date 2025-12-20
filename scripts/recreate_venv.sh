#!/usr/bin/env bash
set -euo pipefail

# Recreate .venv with --upgrade-deps and install project dependencies.
# Usage:
#   chmod +x scripts/recreate_venv.sh
#   ./scripts/recreate_venv.sh

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

# Prefer python3, fallback to python
PYTHON_BIN="$(command -v python3.11 || command -v python3 || command -v python || true)"
if [ -z "$PYTHON_BIN" ]; then
  echo "Error: python or python3 not found in PATH." >&2
  exit 1
fi

echo "Removing existing .venv if present..."
rm -rf .venv

echo "Creating virtual environment with --upgrade-deps using $PYTHON_BIN..."
"$PYTHON_BIN" -m venv --upgrade-deps .venv

echo "Activating .venv..."
# shellcheck source=/dev/null
source .venv/bin/activate

echo "Ensuring pip is available and up-to-date..."
python -m pip install --upgrade pip setuptools wheel

echo "Installing runtime requirements..."
if [ -f "requirements.txt" ]; then
  python -m pip install -r requirements.txt
else
  echo "requirements.txt not found; installing core deps from pyproject.toml is not implemented."
fi

echo "Optionally install voice extras (openai/elevenlabs). To install, run:"
echo "  .venv/bin/python -m pip install openai elevenlabs"

echo "Done. You can now run: direnv allow  (if not already allowed) and open a new shell to auto-activate."



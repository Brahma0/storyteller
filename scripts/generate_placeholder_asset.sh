#!/usr/bin/env bash
set -euo pipefail

# Generates a placeholder vertical video into assets/carousel/placeholder.mp4
# Requires ffmpeg be installed (ffmpeg -version)
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ASSETS_DIR="$ROOT_DIR/assets/carousel"
OUT="$ASSETS_DIR/placeholder.mp4"

mkdir -p "$ASSETS_DIR"

# Create a 6-second 1080x1920 MP4 with a solid background and silent audio.
# Color: dark gray, small text overlay for identification.
# Note: place all inputs before applying -vf; use standard anullsrc options.
ffmpeg -y \
  -f lavfi -i color=c=0x222222:s=1080x1920:d=6 \
  -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=44100 \
  -vf "drawtext=text='Placeholder':fontcolor=white:fontsize=72:x=(w-text_w)/2:y=(h-text_h)/2,format=yuv420p" \
  -c:v libx264 -preset veryfast -crf 23 -c:a aac -shortest "$OUT"

echo "Generated placeholder asset at: $OUT"



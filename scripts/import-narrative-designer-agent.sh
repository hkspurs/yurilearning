#!/usr/bin/env bash
set -euo pipefail

mkdir -p agents/game-development
curl -L \
  https://raw.githubusercontent.com/msitarzewski/agency-agents/main/game-development/narrative-designer.md \
  -o agents/game-development/narrative-designer.md

echo "Imported agents/game-development/narrative-designer.md"

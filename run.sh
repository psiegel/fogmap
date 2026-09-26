# !/bin/bash
cd "$(dirname "$BASH_SOURCE")" || exit
source .venv/bin/activate
fogmap &

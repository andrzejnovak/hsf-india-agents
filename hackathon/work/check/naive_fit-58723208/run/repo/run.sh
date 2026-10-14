#!/usr/bin/env bash
# run.sh <dataset_dir> <output_dir>  -- the entrypoint EVAL_CONTRACT.md asks for
set -euo pipefail
cd "$(dirname "$0")"
python3 fit.py "$1" "$2"

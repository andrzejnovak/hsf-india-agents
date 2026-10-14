#!/usr/bin/env bash
# new_team.sh <team-name>: make a team workspace ~/hack-<team-name> with the task files, the public dataset,
# opencode's NRP settings (from ~/opencode-exercise) and a submission/ folder started from the stub.
set -euo pipefail
[ $# -eq 1 ] || { echo "usage: bash new_team.sh <team-name>"; exit 1; }
HERE="$(cd "$(dirname "$0")" && pwd)"
W="$HOME/hack-$1"
[ -e "$W" ] && { echo "$W exists"; exit 1; }
mkdir -p "$W/submission"
cp "$HERE"/{PROMPT.md,DATASET.md,EVAL_CONTRACT.md} "$W/"
cp -r "$HERE/datasets" "$W/datasets"
cp "$HERE"/examples/stub_submission/run.sh "$W/submission/run.sh"
[ -f "$HOME/opencode-exercise/opencode.json" ] && cp "$HOME/opencode-exercise/opencode.json" "$W/" \
  || echo "note: no ~/opencode-exercise/opencode.json (notebook 3 writes it); opencode will not know NRP here"
printf 'datasets/\n.venv/\n' > "$W/.gitignore"
( cd "$W" && git init -q && git add -A && git commit -qm "team workspace: task files, public dataset, stub submission" )
cat <<EOF
workspace: $W
  PROMPT.md DATASET.md EVAL_CONTRACT.md   the task
  datasets/public/seed_000/              the public dataset
  submission/                            what you hand in: run.sh <dataset_dir> <output_dir> -> RESULT.json

next:
  cd $W && opencode          # paste the prompt from the README, or write submission/ yourself
  cd $HERE && python3 -m sbh check --task gauss_peak --submission $W/submission --dataset datasets/public/seed_000 --determinism
  cd $W && git add -A && git commit -m submission && git push   # to a public GitHub repository of yours
  cd $HERE && bash submit.sh $1 <git url>                        # the self-check, is it pushed, the line to post on the submissions issue
EOF

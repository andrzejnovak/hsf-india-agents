#!/usr/bin/env bash
# submit.sh <team-name> [submission_dir] [--no-check]
#   Runs the self-check on your submission, then copies it (code only) to the drop folder under your team name:
#   /data/hackathon/<team-name> (or $HACK_DROP). Submitting again replaces your earlier submission; the last
#   one before the deadline is the one that gets run.
#     bash submit.sh red                      # ~/hack-red/submission
#     bash submit.sh red path/to/submission
#   --no-check: submit even if the self-check cannot run here; the organisers run the same check before scoring.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
CHECK=1; ARGS=()
for a in "$@"; do case "$a" in --no-check) CHECK=0;; *) ARGS+=("$a");; esac; done
[ ${#ARGS[@]} -ge 1 ] || { sed -n 2,8p "$0" | sed 's/^# \{0,1\}//'; exit 1; }
TEAM="${ARGS[0]}"
case "$TEAM" in ""|.*|*[!A-Za-z0-9_-]*) echo "team name: letters, digits, - and _ only"; exit 1;; esac
SRC="${ARGS[1]:-$HOME/hack-$TEAM/submission}"
[ -f "$SRC/run.sh" ] || { echo "no run.sh in $SRC"; exit 1; }
SUB="$(cd "$SRC" && pwd)"
DROP="${HACK_DROP:-/data/hackathon}"; DEST="$DROP/$TEAM"
if [ "$CHECK" = 1 ]; then
  echo "== self-check: $SUB"
  ( cd "$HERE" && python3 -m sbh check --task gauss_peak --submission "$SUB" --dataset datasets/public/seed_000 --determinism ) \
    || { echo; echo "self-check FAILED: nothing submitted. Fix it, or submit anyway with --no-check (the organisers run the same check)."; exit 1; }
fi
mkdir -p "$DROP" || { echo "cannot create $DROP"; exit 1; }
STAGE="$(mktemp -d "$DROP/.$TEAM.XXXXXX")"
tar -C "$SUB" --exclude=.git --exclude=__pycache__ --exclude=.venv --exclude=node_modules --exclude=datasets --exclude=out \
    --exclude='*.npy' --exclude='*.npz' --exclude='*.root' --exclude='*.parquet' --exclude='*.h5' --exclude='*.pkl' \
    --exclude=RESULT.json -cf - . | tar -C "$STAGE" -xf -
N=$(find "$STAGE" -type f | wc -l); SZ=$(du -sh "$STAGE" | cut -f1)
SHA=$(cd "$STAGE" && find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum | cut -c1-12)
printf 'team: %s\nsubmitted: %s\nby: %s\nfrom: %s\nfiles: %s (%s)\nsha256: %s\nself-check: %s\n' \
  "$TEAM" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${USER:-$(id -un)}" "$SUB" "$N" "$SZ" "$SHA" \
  "$([ "$CHECK" = 1 ] && echo PASS || echo skipped)" > "$STAGE/SUBMITTED.txt"
if [ -e "$DEST" ]; then rm -rf "$DEST" || { echo "cannot replace $DEST (another user's?)"; rm -rf "$STAGE"; exit 1; }; fi
mv "$STAGE" "$DEST"; chmod -R a+rX "$DEST"
echo "== submitted: $DEST  ($N files, $SZ, sha $SHA, $(date -u +%H:%M) UTC)"
( cd "$DEST" && find . -type f | sort | sed 's|^\./|     |' )

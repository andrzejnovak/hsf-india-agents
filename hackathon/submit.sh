#!/usr/bin/env bash
# submit.sh <team-name> <git-url> [workspace] [--no-check]
#   Submit your team repository: the self-check on <workspace>/submission (default ~/hack-<team-name>), a check
#   that the committed state is pushed to <git-url>, then the one line to post as a comment on the submissions
#   issue, https://github.com/andrzejnovak/hsf-india-agents/issues/1 (posted for you when `gh` is logged in).
#     bash submit.sh red https://github.com/alice/hack-red
#   Submit as often as you like; a new comment replaces your earlier one. The last comment per team before the
#   deadline is the one that gets run.
#   --no-check: skip the self-check if it cannot run on your machine; the organisers run it anyway.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ISSUE_REPO="andrzejnovak/hsf-india-agents"; ISSUE=1
CHECK=1; ARGS=()
for a in "$@"; do case "$a" in --no-check) CHECK=0;; *) ARGS+=("$a");; esac; done
[ ${#ARGS[@]} -ge 2 ] || { sed -n 2,9p "$0" | sed 's/^# \{0,1\}//'; exit 1; }
TEAM="${ARGS[0]}"; URL="${ARGS[1]}"
case "$TEAM" in ""|.*|*[!A-Za-z0-9_-]*) echo "team name: letters, digits, - and _ only"; exit 1;; esac
W="${ARGS[2]:-$HOME/hack-$TEAM}"
[ -f "$W/submission/run.sh" ] || { echo "no submission/run.sh in $W (the layout new_team.sh makes)"; exit 1; }
[ -d "$W/.git" ] || { echo "$W is not a git repository: cd $W && git init && git add -A && git commit -m submission"; exit 1; }
if [ "$CHECK" = 1 ]; then
  echo "== self-check: $W/submission"
  ( cd "$HERE" && python3 -m sbh check --task gauss_peak --submission "$W/submission" --dataset datasets/public/seed_000 --determinism ) \
    || { echo; echo "self-check FAILED: nothing submitted. Fix it, or submit anyway with --no-check (the organisers run the same check)."; exit 1; }
fi
DIRTY="$(git -C "$W" status --porcelain -- submission)"
[ -z "$DIRTY" ] || { echo "uncommitted changes in $W/submission: commit them first (git -C $W add -A && git -C $W commit -m submission)"; echo "$DIRTY" | sed 's/^/   /'; exit 1; }
SHA="$(git -C "$W" rev-parse HEAD)"
echo "== pushed? $URL at $SHA"
REFS="$(git ls-remote "$URL" 2>&1)" || { echo "cannot read $URL: is it pushed and public (or shared with the organisers)?"; echo "$REFS" | tail -2; exit 1; }
echo "$REFS" | grep -q "^$SHA" || { echo "commit $SHA is not on $URL: push first (git -C $W push $URL HEAD)"; exit 1; }
LINE="$TEAM: $URL @ ${SHA:0:12}"
echo "== submission line:"; echo; echo "    $LINE"; echo
if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  gh issue comment "$ISSUE" --repo "$ISSUE_REPO" --body "$LINE" && echo "posted on https://github.com/$ISSUE_REPO/issues/$ISSUE" && exit 0
fi
echo "post it as a comment on https://github.com/$ISSUE_REPO/issues/$ISSUE (a new comment replaces your earlier one)"

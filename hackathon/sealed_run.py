#!/usr/bin/env python3
"""The sealed run, with the kit alone, anywhere with git, python3, numpy and scipy: build a sealed suite from a
secret seed, clone every submitted team repository at its submitted commit, run them all, write the leaderboard.

    python3 sealed_run.py [--seed <secret>] [--n 21] [--out ~/hack-sealed] [--issue 1 | --teams FILE]
                          [--team red --team blue] [--as nobody] [--publish README.md [--plots]]
                          [--no-check] [--timeout 600]

Without --seed the suite is drawn from a seed made up on the spot and never printed: the run is then
self-contained (CI: .github/workflows/sealed_run.yml runs it on every comment on the submissions issue and
commits the table into the README). With --as USER the submissions run as that user through sudo -n, with the
truths unreadable to it (<out> is 711, <out>/truths 700) and a scrubbed environment. --publish writes the
leaderboard table between the `<!-- leaderboard -->` markers of that README; --plots also copies each team's
recovery plot beside it (results/<team>.png) and links it: the plots show the planted values per dataset, so
publish them only once the deadline has passed.

Submissions are the comments on the submissions issue (--issue, default 1 of andrzejnovak/hsf-india-agents,
read through the public GitHub API with no token), one line each: `<team>: <git url> @ <commit>`; the last
comment per team wins. --teams FILE reads the same lines from a file instead (a hand-made list, or the issue
copied over). Each repository is cloned into <out>/submissions/<team>/ and checked out at that commit; the
submission is its submission/ directory (or its root when run.sh is there).

The suite goes under --out: seed_000 is the public truth and the rest are drawn from the task's priors with the
detector response on. The truths are moved out of the dataset directories into <out>/truths/ before anything
runs, and <out> is made private, so a submission that reads its dataset directory finds no answer key. A second
run with the same --seed and --out reuses the suite (and re-clones each team); without --seed a fresh suite
replaces it.

Per team: the self-check (hygiene, the contract, determinism on the public dataset; <out>/results/<team>/check.txt),
then score_suite.score on every sealed dataset (score.txt, score.json, recovery.png). Submissions run as you,
without a sandbox: run this in a throwaway session or a VM rather than on your own account; the private
harness's `sbh eval` on the clones is the sandboxed alternative (ORGANISER.md).

Levels, as the pitch defines them (change `level` below if the rule changes):
  0  self-check failed, fewer than 90 % of the datasets gave a valid RESULT.json, or no slope
  1  a measurement: the slope of reported vs planted mH is at least 0.8
  2  level 1 with honest error bars: pull widths within [0.7, 1.4] for mH and mu, and no false discovery
  3  is not the machine's to judge (how the pipeline was made); say so when the teams present
Order: level, then the distance |slope_mH - 1| + |slope_mu - 1| + |ln w_mH| + |ln w_mu|, smallest first.
Each sbh check run takes two runs of the submission and the scoring --n runs: budget about 2 minutes per team
with a pipeline like examples/naive_fit.
"""
import argparse
import json
import math
import os
import re
import shutil
import stat
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import score_suite as S  # noqa: E402
import toy_suite as T  # noqa: E402

PUBLIC = HERE / "datasets" / "public" / "seed_000"
ISSUE_REPO = "andrzejnovak/hsf-india-agents"
LINE = re.compile(r"^\s*`?([A-Za-z0-9_-]+)\s*:\s*(\S+?)\s*@\s*([0-9a-fA-F]{7,40})`?\s*$", re.M)


def build_suite(out: Path, seed, n: int, log):
    suite, truths = out / "suite", out / "truths"
    man = truths / "manifest.json"
    if seed is None:
        import secrets
        seed = secrets.randbelow(2 ** 31)
        if suite.exists() or truths.exists():
            shutil.rmtree(suite, ignore_errors=True); shutil.rmtree(truths, ignore_errors=True)
    elif suite.is_dir() and man.is_file():
        have = json.loads(man.read_text())["master_seed"]
        if have != seed:
            raise SystemExit(f"{suite} was built with another seed; pick another --out")
        log(f"suite: {suite} (built earlier with this seed, {len(list(suite.glob('seed_*')))} datasets)")
        return suite, truths
    if suite.exists():
        raise SystemExit(f"{suite} exists without {man}; remove it or pick another --out")
    out.mkdir(parents=True, exist_ok=True)
    os.chmod(out, 0o711)   # traversable, not listable: a submission running as another user reaches its dataset and nothing else
    log(f"building the sealed suite: {n} datasets, seed {'*' * 6}, response on")
    T.build(suite, n, seed, True, None, log=lambda s: None)
    truths.mkdir()
    os.chmod(truths, stat.S_IRWXU)
    for d in sorted(suite.glob("seed_*")):
        (d / "truth.json").rename(truths / f"{d.name}.json")
    (suite / "manifest.json").rename(man)
    left = [p for p in suite.rglob("*") if "truth" in p.name.lower() or p.name == "manifest.json"]
    assert not left, left
    log(f"suite: {suite}; truths in {truths} (private)")
    return suite, truths


def parse_lines(texts):
    """`<team>: <url> @ <commit>` lines, in order; the last line per team wins."""
    teams = {}
    for text, when in texts:
        for m in LINE.finditer(text):
            teams[m.group(1)] = {"team": m.group(1), "url": m.group(2), "commit": m.group(3).lower(), "submitted": when}
    return teams


def teams_from_issue(number: int):
    url = f"https://api.github.com/repos/{ISSUE_REPO}/issues/{number}/comments?per_page=100"
    texts, page = [], 1
    while True:
        req = urllib.request.Request(url + f"&page={page}", headers={"Accept": "application/vnd.github+json",
                                                                     "User-Agent": "hsf-india-hackathon"})
        with urllib.request.urlopen(req, timeout=30) as r:
            comments = json.loads(r.read().decode())
        texts += [(c["body"], f"{c.get('created_at', '')} by {c.get('user', {}).get('login', '?')}") for c in comments]
        if len(comments) < 100:
            break
        page += 1
    return parse_lines(texts)


def teams_from_file(path: Path):
    return parse_lines([(path.read_text(), f"from {path.name}")])


def fetch(entry, dest: Path, log):
    """Clone the team repository at the submitted commit into dest; returns the submission directory or None."""
    if dest.exists():
        shutil.rmtree(dest)
    try:
        subprocess.run(["git", "clone", "-q", entry["url"], str(dest)], check=True, capture_output=True, text=True, timeout=300)
        subprocess.run(["git", "-C", str(dest), "checkout", "-q", entry["commit"]], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        log(f"cannot fetch {entry['url']} @ {entry['commit']}: {(e.stderr or e.stdout).strip()[-200:]}")
        return None
    except subprocess.TimeoutExpired:
        log(f"cloning {entry['url']} timed out")
        return None
    for sub in (dest / "submission", dest):
        if (sub / "run.sh").is_file():
            for q in sub.rglob("*"):
                q.chmod(q.stat().st_mode | 0o044 | (0o011 if q.is_dir() else 0))
            sub.chmod(sub.stat().st_mode | 0o055)
            return sub
    log(f"no submission/run.sh (nor run.sh) in {entry['url']} @ {entry['commit']}")
    return None


def self_check(sub: Path, log_path: Path, timeout: float):
    cmd = [sys.executable, "-m", "sbh", "check", "--task", "gauss_peak", "--submission", str(sub),
           "--dataset", str(PUBLIC), "--determinism"]
    try:
        p = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True, timeout=timeout)
        out, rc = p.stdout + p.stderr, p.returncode
    except subprocess.TimeoutExpired:
        out, rc = "self-check timed out", 1
    log_path.write_text(out)
    return rc == 0, out


def level(agg, check_ok):
    mh, mu = agg["pois"].get("mH"), agg["pois"].get("mu")
    if not check_ok or agg["recovery"] < 0.9 or mh is None or mu is None or not math.isfinite(mh["slope"]):
        return 0
    if mh["slope"] < 0.8:
        return 0
    honest = all(S.WIDTH_OK[0] <= a["width"] <= S.WIDTH_OK[1] for a in (mh, mu)) and not agg["false_discoveries"]
    return 2 if honest else 1


def distance(agg):
    mh, mu = agg["pois"].get("mH"), agg["pois"].get("mu")
    if mh is None or mu is None:
        return float("inf")
    d = abs(mh["slope"] - 1) + abs(mu["slope"] - 1)
    for a in (mh, mu):
        d += abs(math.log(a["width"])) if a["width"] > 0 else 9.0
    return d if math.isfinite(d) else float("inf")


def fmt(x, f="{:.2f}"):
    return "–" if x is None or (isinstance(x, float) and not math.isfinite(x)) else f.format(x)


MARK = ("<!-- leaderboard -->", "<!-- /leaderboard -->")


def publish(entries, readme: Path, results: Path, plots: bool, log):
    """The table (and, with plots, each team's recovery plot) into the README between the markers."""
    text = readme.read_text()
    if MARK[0] not in text or MARK[1] not in text:
        raise SystemExit(f"{readme} has no {MARK[0]} ... {MARK[1]} markers")
    rows = [table_rows(entries)]
    when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body = [f"_Sealed run of {when}: {entries[0]['agg']['n']} datasets nobody has seen, every submission on the "
            f"[issue](https://github.com/{ISSUE_REPO}/issues/1) at its last comment. "
            + ("Recovery plots: reported against planted, per team." if plots else "Recovery plots follow after the deadline.") + "_", "",
            rows[0]]
    if plots:
        pdir = readme.parent / "results"; pdir.mkdir(exist_ok=True)
        for e in entries:
            src = results / e["team"] / "recovery.png"
            if src.is_file():
                shutil.copy(src, pdir / f"{e['team']}.png")
                body += ["", f"**{e['team']}** (level {e['level']})", "", f"![{e['team']}](results/{e['team']}.png)"]
    head, tail = text.split(MARK[0], 1)[0], text.split(MARK[1], 1)[1]
    readme.write_text(head + MARK[0] + "\n" + "\n".join(body) + "\n" + MARK[1] + tail)
    log(f"published into {readme}" + (f" with plots under {readme.parent / 'results'}" if plots else ""))


def table_rows(entries):
    entries.sort(key=lambda e: (-e["level"], e["distance"], e["team"]))
    head = ["#", "team", "level", "slope mH", "slope μ", "pull width mH", "pull width μ", "false disc.", "power",
            "recovery", "self-check", "submitted"]
    rows = []
    for i, e in enumerate(entries, 1):
        a = e["agg"]; mh, mu = a["pois"].get("mH"), a["pois"].get("mu")
        rows.append([str(i), e["team"], str(e["level"]),
                     fmt(mh and mh["slope"]), fmt(mu and mu["slope"]), fmt(mh and mh["width"]), fmt(mu and mu["width"]),
                     f"{a['false_discoveries']}/{a['n_null']}" if a["n_null"] else "–",
                     fmt(a["power"]), f"{a['n_ok']}/{a['n']}" if a["n"] else "–", "PASS" if e["check_ok"] else "FAIL",
                     e.get("submitted") or "–"])
    w = [max(len(h), *(len(r[j]) for r in rows)) if rows else len(h) for j, h in enumerate(head)]
    line = lambda cells: "| " + " | ".join(c.ljust(w[j]) for j, c in enumerate(cells)) + " |"
    md = [line(head), "|" + "|".join("-" * (x + 2) for x in w) + "|"] + [line(r) for r in rows]
    return "\n".join(md)


def leaderboard(entries, path_md: Path, path_json: Path, log):
    text = table_rows(entries)
    path_md.write_text(f"# Leaderboard\n\n{text}\n\nlevel 0: no measurement (self-check, recovery or slope); 1: follows the truth "
                       f"(slope of mH ≥ 0.8); 2: and honest error bars (pull widths in [{S.WIDTH_OK[0]}, {S.WIDTH_OK[1]}], no false discovery). "
                       f"Within a level, closest to slope 1 and width 1 first.\n")
    path_json.write_text(json.dumps([{k: v for k, v in e.items() if k != "rows"} for e in entries], indent=1, default=str))
    log("\n" + text)
    log(f"\nwritten: {path_md}, {path_json}; per team: {path_md.parent}/<team>/recovery.png, score.txt, check.txt")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, help="the secret master seed; default: made up for this run and never printed")
    ap.add_argument("--n", type=int, default=21, help="datasets in the sealed suite, public seed_000 included (default 21)")
    ap.add_argument("--issue", type=int, default=1, help=f"the submissions issue of {ISSUE_REPO} (default 1)")
    ap.add_argument("--teams", help="read the `<team>: <url> @ <commit>` lines from this file instead of the issue")
    ap.add_argument("--out", default="~/hack-sealed", help="private working directory: suite, truths, submissions, results (default ~/hack-sealed)")
    ap.add_argument("--team", action="append", help="only these teams (repeatable)")
    ap.add_argument("--as", dest="as_user", metavar="USER", help="run the submissions as this user through sudo -n (CI: nobody)")
    ap.add_argument("--publish", metavar="README", help="write the leaderboard between the markers of this README")
    ap.add_argument("--plots", action="store_true", help="with --publish: the recovery plots too (after the deadline only)")
    ap.add_argument("--no-check", action="store_true", help="skip the self-check (its verdict then reads FAIL)")
    ap.add_argument("--timeout", type=float, default=600, help="seconds per dataset, the contract's 600")
    a = ap.parse_args()
    out = Path(a.out).expanduser().resolve()
    log = print
    teams = teams_from_file(Path(a.teams)) if a.teams else teams_from_issue(a.issue)
    if a.team:
        missing = sorted(set(a.team) - set(teams))
        if missing:
            raise SystemExit(f"no submission line for {', '.join(missing)}")
        teams = {t: e for t, e in teams.items() if t in a.team}
    if not teams:
        raise SystemExit("no submissions: no `<team>: <url> @ <commit>` line " + (f"in {a.teams}" if a.teams else f"on issue {a.issue}"))
    log("submissions: " + ", ".join(f"{t} ({e['url']} @ {e['commit'][:7]})" for t, e in teams.items()))
    suite, truths = build_suite(out, a.seed, a.n, log)
    results = out / "results"; results.mkdir(exist_ok=True)
    entries = []
    for team, entry in teams.items():
        log(f"\n=== {team}")
        res = results / team; res.mkdir(exist_ok=True)
        submitted = f"{entry['commit'][:7]} ({entry['submitted']})"
        sub = fetch(entry, out / "submissions" / team, log)
        if sub is None:
            (res / "check.txt").write_text("not fetched\n")
            entries.append({"team": team, "check_ok": False, "submitted": submitted, "level": 0, "distance": float("inf"),
                            "agg": S.aggregate([]), "rows": [], "url": entry["url"], "commit": entry["commit"]})
            log("level 0 (not fetched)")
            continue
        if a.no_check:
            check_ok, note = False, "skipped (--no-check)"
        else:
            check_ok, text = self_check(sub, res / "check.txt", 2 * a.timeout + 60)
            note = "PASS" if check_ok else "FAIL: " + (text.strip().splitlines() or ["(no output)"])[-1][:120]
        log(f"self-check: {note}")
        lines = []
        r = S.score(sub, suite, a.timeout, truths, log=lambda s: (lines.append(s), print(s)), as_user=a.as_user)
        (res / "score.txt").write_text("\n".join(lines) + "\n")
        (res / "score.json").write_text(json.dumps(r, indent=1, default=str))
        if not S.plot(r["rows"], res / "recovery.png", title=f"{team} — sealed run"):
            log("no matplotlib here: no recovery.png (python3 -m pip install matplotlib, or plot score.json elsewhere)")
        e = {"team": team, "check_ok": check_ok, "submitted": submitted, "agg": r["agg"],
             "level": level(r["agg"], check_ok), "distance": distance(r["agg"]), "rows": r["rows"],
             "url": entry["url"], "commit": entry["commit"],
             "scored_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        entries.append(e)
        log(f"level {e['level']}  (distance {fmt(e['distance'])})")
    leaderboard(entries, results / "leaderboard.md", results / "leaderboard.json", log)
    if a.publish:
        publish(entries, Path(a.publish).resolve(), results, a.plots, log)


if __name__ == "__main__":
    main()

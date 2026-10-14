#!/usr/bin/env python3
"""The sealed run, with the kit alone: build a sealed suite from a secret seed, run every submission in the drop
folder on it, write the leaderboard.

    python3 sealed_run.py --seed <secret> [--n 21] [--drop /data/hackathon] [--out ~/hack-sealed]
                          [--team red --team blue] [--no-check] [--timeout 600]

The suite goes under --out (keep it in your own home, never under /data): seed_000 is the public truth and the
rest are drawn from the task's priors with the detector response on. The truths are moved out of the dataset
directories into <out>/truths/ before anything runs, and <out> is made private, so a submission that reads its
dataset directory finds no answer key. A second run with the same --seed and --out reuses the suite.

Per team (every <drop>/<team>/run.sh): the submission is copied to <out>/submissions/<team>/, the self-check
runs on it (hygiene, the contract, determinism on the public dataset; <out>/results/<team>/check.txt), then
score_suite.score runs it on every sealed dataset (score.txt, score.json, recovery.png). Submissions run as
you, without a sandbox: run this in a throwaway session (a Binder), not on your laptop; the private harness's
`sbh eval` is the sandboxed alternative (ORGANISER.md).

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
import shutil
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import score_suite as S  # noqa: E402
import toy_suite as T  # noqa: E402

PUBLIC = HERE / "datasets" / "public" / "seed_000"


def build_suite(out: Path, seed: int, n: int, log):
    suite, truths = out / "suite", out / "truths"
    man = truths / "manifest.json"
    if suite.is_dir() and man.is_file():
        have = json.loads(man.read_text())["master_seed"]
        if have != seed:
            raise SystemExit(f"{suite} was built with another seed; pick another --out")
        log(f"suite: {suite} (built earlier with this seed, {len(list(suite.glob('seed_*')))} datasets)")
        return suite, truths
    if suite.exists():
        raise SystemExit(f"{suite} exists without {man}; remove it or pick another --out")
    out.mkdir(parents=True, exist_ok=True)
    os.chmod(out, stat.S_IRWXU)
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


def teams_in(drop: Path, only):
    found = sorted(d for d in drop.iterdir() if d.is_dir() and not d.name.startswith(".") and (d / "run.sh").is_file())
    if only:
        missing = sorted(set(only) - {d.name for d in found})
        if missing:
            raise SystemExit(f"no submission for {', '.join(missing)} in {drop}")
        found = [d for d in found if d.name in only]
    return found


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


def leaderboard(entries, path_md: Path, path_json: Path, log):
    entries.sort(key=lambda e: (-e["level"], e["distance"], e["team"]))
    head = ["#", "team", "level", "slope mH", "slope μ", "pull width mH", "pull width μ", "false disc.", "power",
            "recovery", "self-check", "submitted"]
    rows = []
    for i, e in enumerate(entries, 1):
        a = e["agg"]; mh, mu = a["pois"].get("mH"), a["pois"].get("mu")
        rows.append([str(i), e["team"], str(e["level"]),
                     fmt(mh and mh["slope"]), fmt(mu and mu["slope"]), fmt(mh and mh["width"]), fmt(mu and mu["width"]),
                     f"{a['false_discoveries']}/{a['n_null']}" if a["n_null"] else "–",
                     fmt(a["power"]), f"{a['n_ok']}/{a['n']}", "PASS" if e["check_ok"] else "FAIL",
                     e.get("submitted") or "–"])
    w = [max(len(h), *(len(r[j]) for r in rows)) if rows else len(h) for j, h in enumerate(head)]
    line = lambda cells: "| " + " | ".join(c.ljust(w[j]) for j, c in enumerate(cells)) + " |"
    md = [line(head), "|" + "|".join("-" * (x + 2) for x in w) + "|"] + [line(r) for r in rows]
    text = "\n".join(md)
    path_md.write_text(f"# Leaderboard\n\n{text}\n\nlevel 0: no measurement (self-check, recovery or slope); 1: follows the truth "
                       f"(slope of mH ≥ 0.8); 2: and honest error bars (pull widths in [{S.WIDTH_OK[0]}, {S.WIDTH_OK[1]}], no false discovery). "
                       f"Within a level, closest to slope 1 and width 1 first.\n")
    path_json.write_text(json.dumps([{k: v for k, v in e.items() if k != "rows"} for e in entries], indent=1, default=str))
    log("\n" + text)
    log(f"\nwritten: {path_md}, {path_json}; per team: {path_md.parent}/<team>/recovery.png, score.txt, check.txt")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, required=True, help="the secret master seed (python3 -c 'import secrets; print(secrets.randbelow(2**31))')")
    ap.add_argument("--n", type=int, default=21, help="datasets in the sealed suite, public seed_000 included (default 21)")
    ap.add_argument("--drop", default=os.environ.get("HACK_DROP", "/data/hackathon"), help="where the teams submitted (default /data/hackathon or $HACK_DROP)")
    ap.add_argument("--out", default="~/hack-sealed", help="private working directory: suite, truths, submissions, results (default ~/hack-sealed)")
    ap.add_argument("--team", action="append", help="only these teams (repeatable); default every <drop>/<team>/run.sh")
    ap.add_argument("--no-check", action="store_true", help="skip the self-check (its verdict then reads FAIL)")
    ap.add_argument("--timeout", type=float, default=600, help="seconds per dataset, the contract's 600")
    a = ap.parse_args()
    out, drop = Path(a.out).expanduser().resolve(), Path(a.drop).expanduser().resolve()
    if not drop.is_dir():
        raise SystemExit(f"no drop folder {drop}")
    if drop in out.parents or out == drop:
        raise SystemExit("--out must not be inside the drop folder: the truths would be readable by everyone")
    log = print
    suite, truths = build_suite(out, a.seed, a.n, log)
    results = out / "results"; results.mkdir(exist_ok=True)
    entries = []
    for src in teams_in(drop, a.team):
        team = src.name
        log(f"\n=== {team}")
        sub = out / "submissions" / team
        if sub.exists():
            shutil.rmtree(sub)
        shutil.copytree(src, sub, ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv"))
        submitted = None
        if (sub / "SUBMITTED.txt").is_file():
            for ln in (sub / "SUBMITTED.txt").read_text().splitlines():
                if ln.startswith("submitted:"):
                    submitted = ln.split(":", 1)[1].strip()
        res = results / team; res.mkdir(exist_ok=True)
        if a.no_check:
            check_ok, note = False, "skipped (--no-check)"
        else:
            check_ok, text = self_check(sub, res / "check.txt", 2 * a.timeout + 60)
            note = "PASS" if check_ok else "FAIL: " + (text.strip().splitlines() or ["(no output)"])[-1][:120]
        log(f"self-check: {note}")
        lines = []
        r = S.score(sub, suite, a.timeout, truths, log=lambda s: (lines.append(s), print(s)))
        (res / "score.txt").write_text("\n".join(lines) + "\n")
        (res / "score.json").write_text(json.dumps(r, indent=1, default=str))
        if not S.plot(r["rows"], res / "recovery.png", title=f"{team} — sealed run"):
            log("no matplotlib here: no recovery.png (python3 -m pip install matplotlib, or plot score.json elsewhere)")
        e = {"team": team, "check_ok": check_ok, "submitted": submitted, "agg": r["agg"],
             "level": level(r["agg"], check_ok), "distance": distance(r["agg"]), "rows": r["rows"],
             "scored_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        entries.append(e)
        log(f"level {e['level']}  (distance {fmt(e['distance'])})")
    if not entries:
        raise SystemExit(f"no submissions in {drop}")
    leaderboard(entries, results / "leaderboard.md", results / "leaderboard.json", log)


if __name__ == "__main__":
    main()

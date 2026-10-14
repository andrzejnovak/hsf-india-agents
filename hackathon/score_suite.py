#!/usr/bin/env python3
"""Run a submission on a suite you made with toy_suite.py and score it the way the sealed evaluation does.

    python3 score_suite.py <submission_dir> <suite_dir> [--plot recovery.png] [--timeout 600] [--truths DIR]

Runs `run.sh <dataset> <out>` once per seed (no sandbox: the real evaluation has one), reads RESULT.json, and
compares with truth.json: a table of planted vs reported values with pulls, then the aggregates of
EVAL_CONTRACT.md section 3 -- sensitivity (slope of reported vs planted), bias (mean pull), calibration (pull
width), recovery, false-discovery rate and discovery power.  Pulls and slopes use the seeds whose injected
signal has expected local significance >= 5; null seeds count towards the false-discovery rate.  --truths reads
each seed's truth from DIR/<seed>.json instead of <seed>/truth.json (the sealed run keeps them apart).
"""
import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np

Z_APPLICABLE = 5.0


def run_seed(sub: Path, ds: Path, timeout: float, as_user: str = None):
    """One run of sub/run.sh on the dataset, with a scrubbed environment (PATH, a scratch HOME, LANG: nothing of
    yours) and, with as_user, as that user through sudo -n (the sealed run: the truths stay unreadable)."""
    out = Path(tempfile.mkdtemp(prefix="score_"))
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(out), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}
    cmd = ["bash", str(sub / "run.sh"), str(ds.resolve()), str(out)]
    if as_user:
        os.chmod(out, 0o1777)
        cmd = ["sudo", "-n", "-u", as_user, "--", "env", "-i"] + [f"{k}={v}" for k, v in env.items()] + cmd
    t = time.time()
    try:
        p = subprocess.run(cmd, cwd=sub, env=env, capture_output=True, text=True, timeout=timeout)
        status, log = p.returncode, (p.stdout + p.stderr)[-800:]
    except subprocess.TimeoutExpired:
        status, log = "timeout", ""
    res = None
    if status == 0 and (out / "RESULT.json").is_file():
        try:
            res = json.loads((out / "RESULT.json").read_text())
        except (json.JSONDecodeError, PermissionError) as e:
            status, log = "malformed", str(e)
    if as_user:
        subprocess.run(["sudo", "-n", "rm", "-rf", str(out)], capture_output=True)
    shutil.rmtree(out, ignore_errors=True)
    return status, res, time.time() - t, log


def poi(res, name):
    for p in res.get("pois", []):
        if p.get("name") == name:
            return float(p["value"]), float(p["total"])
    raise KeyError(name)



WIDTH_OK = (0.7, 1.4)


def load_truth(ds: Path, truths: Path = None):
    f = (truths / f"{ds.name}.json") if truths else (ds / "truth.json")
    return json.loads(f.read_text()) if f.is_file() else None


def score(sub: Path, suite: Path, timeout: float = 600, truths: Path = None, log=print, as_user: str = None):
    """Run sub/run.sh on every seed of the suite and compare with the truths; prints the per-seed table through
    log and returns {"rows": [...], "agg": aggregate(rows)}."""
    sub, suite = Path(sub).resolve(), Path(suite).resolve()
    if not (sub / "run.sh").is_file():
        raise SystemExit(f"no run.sh in {sub}")
    seeds = [d for d in sorted(suite.glob("seed_*")) if load_truth(d, truths)]
    if not seeds:
        raise SystemExit(f"no truths for seed_* under {suite}: make a suite with toy_suite.py")
    rows = []
    log(f"{'seed':9s} {'status':8s} {'wall':>6s}  {'mH planted':>10s} {'reported':>16s} {'pull':>6s}  "
        f"{'mu planted':>10s} {'reported':>14s} {'pull':>6s}  {'Z_exp':>5s} {'Z_obs':>5s} disc")
    for ds in seeds:
        truth = load_truth(ds, truths)
        status, res, wall, errlog = run_seed(sub, ds, timeout, as_user)
        row = {"seed": ds.name, "truth": truth, "ok": False, "status": str(status), "wall": wall}
        if res is not None:
            try:
                (mh, mh_e), (mu, mu_e) = poi(res, "mH"), poi(res, "mu")
                row.update(ok=True, mH=mh, mH_e=mh_e, mu=mu, mu_e=mu_e,
                           z=float(res.get("significance_obs", 0.0)), disc=bool(res.get("discovery", False)))
            except (KeyError, TypeError, ValueError) as e:
                status = f"bad:{type(e).__name__}"
                row["status"] = status
        zexp = truth.get("expected_significance", 0.0)
        if row["ok"]:
            pm, pu = (row["mH"] - truth["mH"]) / row["mH_e"], (row["mu"] - truth["mu"]) / row["mu_e"]
            row.update(pull_mH=pm, pull_mu=pu)
            log(f"{ds.name:9s} {'ok':8s} {wall:5.1f}s  {truth['mH']:10.2f} {row['mH']:8.2f} ± {row['mH_e']:5.2f} "
                f"{pm:6.2f}  {truth['mu']:10.2f} {row['mu']:7.2f} ± {row['mu_e']:4.2f} {pu:6.2f}  "
                f"{zexp:5.1f} {row['z']:5.1f} {'yes' if row['disc'] else 'no'}")
        else:
            log(f"{ds.name:9s} {str(status):8s} {wall:5.1f}s  {truth['mH']:10.2f} {'-':>16s} {'-':>6s}  "
                f"{truth['mu']:10.2f} {'-':>14s} {'-':>6s}  {zexp:5.1f}" + (f"\n    {errlog.strip()[-300:]}" if errlog.strip() else ""))
        rows.append(row)
    agg = aggregate(rows)
    report(agg, log)
    return {"rows": rows, "agg": agg}


def aggregate(rows):
    """The contract's aggregates from the per-seed rows: recovery, and per POI the sensitivity slope, bias and
    calibration width over the strong seeds; the false-discovery rate on null seeds, the discovery power on strong."""
    ok = [r for r in rows if r["ok"]]
    strong = [r for r in ok if r["truth"].get("expected_significance", 0) >= Z_APPLICABLE]
    null = [r for r in ok if r["truth"]["mu"] == 0]
    agg = {"n": len(rows), "n_ok": len(ok), "recovery": len(ok) / max(len(rows), 1),
           "n_strong": len(strong), "n_null": len(null), "pois": {}}
    for name in ("mH", "mu"):
        if len(strong) < 3:
            agg["pois"][name] = None
            continue
        x = np.array([r["truth"][name] for r in strong]); y = np.array([r[name] for r in strong])
        pulls = np.array([r[f"pull_{name}"] for r in strong])
        slope = float(np.polyfit(x, y, 1)[0]) if np.ptp(x) > 0 else float("nan")
        width = float(np.sqrt(np.mean(pulls ** 2)))
        verdict = ("OK" if WIDTH_OK[0] <= width <= WIDTH_OK[1] else
                   ("UNDER-covering: error bars too small" if width > WIDTH_OK[1] else "OVER-covering: error bars too large"))
        agg["pois"][name] = {"slope": slope, "bias": float(pulls.mean()), "width": width, "verdict": verdict}
    agg["false_discoveries"] = sum(r["disc"] for r in null)
    agg["fdr"] = agg["false_discoveries"] / len(null) if null else None
    agg["discoveries"] = sum(r["disc"] for r in strong)
    agg["power"] = agg["discoveries"] / len(strong) if strong else None
    return agg


def report(agg, log=print):
    log(f"\nrecovery: {agg['n_ok']}/{agg['n']} seeds completed with a valid RESULT.json")
    log(f"scored for mH and mu: {agg['n_strong']} seeds with expected significance >= {Z_APPLICABLE:g}; "
        f"{agg['n_null']} null seeds")
    for name in ("mH", "mu"):
        a = agg["pois"][name]
        if a is None:
            log(f"  {name}: fewer than 3 scorable seeds, no slope")
            continue
        log(f"  {name}: sensitivity slope {a['slope']:5.2f} (1 = faithful, 0 = constant) | bias (mean pull) {a['bias']:+5.2f} "
            f"| calibration (pull RMS) {a['width']:4.2f} -> {a['verdict']}")
    if agg["fdr"] is not None:
        log(f"  false-discovery rate: {agg['fdr']:.2f} ({agg['false_discoveries']} of {agg['n_null']} null seeds claimed)")
    if agg["power"] is not None:
        log(f"  discovery power: {agg['power']:.2f} ({agg['discoveries']} of {agg['n_strong']} strong seeds claimed)")


def plot(rows, path, title=None):
    """The recovery plot, reported vs planted for mH and mu; returns False without matplotlib."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    ok = [r for r in rows if r["ok"]]
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.2))
    for ax, name, unit in zip(axes, ("mH", "mu"), (" [GeV]", "")):
        for r in ok:
            s = r["truth"].get("expected_significance", 0) >= Z_APPLICABLE
            ax.errorbar(r["truth"][name], r[name], yerr=r[f"{name}_e"], fmt="o", ms=4, capsize=2,
                        color="C0" if s else "0.6", alpha=0.9 if s else 0.6)
        lo, hi = ax.get_xlim()
        ax.plot([lo, hi], [lo, hi], "k--", lw=1, label="reported = planted")
        ax.set_xlim(lo, hi)
        ax.set_xlabel(f"planted {name}{unit}"); ax.set_ylabel(f"reported {name}{unit}")
        ax.legend(loc="upper left", frameon=False)
    axes[0].set_title("blue: scored seeds (Z_exp ≥ 5), grey: weak or null", fontsize=9)
    if title:
        fig.suptitle(title, fontsize=11)
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("submission")
    ap.add_argument("suite")
    ap.add_argument("--plot", help="write the recovery plot (reported vs planted) to this PNG")
    ap.add_argument("--timeout", type=float, default=600)
    ap.add_argument("--truths", help="read truths from DIR/<seed>.json instead of <seed>/truth.json")
    a = ap.parse_args()
    r = score(Path(a.submission), Path(a.suite), a.timeout, Path(a.truths).resolve() if a.truths else None)
    if a.plot:
        if plot(r["rows"], a.plot):
            print(f"plot: {a.plot}")
        else:
            print("no matplotlib: skipping the plot")


if __name__ == "__main__":
    main()

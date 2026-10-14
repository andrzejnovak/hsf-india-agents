#!/usr/bin/env python3
"""Run a submission on a suite you made with toy_suite.py and score it the way the sealed evaluation does.

    python3 score_suite.py <submission_dir> <suite_dir> [--plot recovery.png] [--timeout 600]

Runs `run.sh <dataset> <out>` once per seed (no sandbox: the real evaluation has one), reads RESULT.json, and
compares with truth.json: a table of planted vs reported values with pulls, then the aggregates of
EVAL_CONTRACT.md section 3 -- sensitivity (slope of reported vs planted), bias (mean pull), calibration (pull
width), recovery, false-discovery rate and discovery power.  Pulls and slopes use the seeds whose injected
signal has expected local significance >= 5; null seeds count towards the false-discovery rate.
"""
import argparse
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np

Z_APPLICABLE = 5.0


def run_seed(sub: Path, ds: Path, timeout: float):
    out = Path(tempfile.mkdtemp(prefix="score_"))
    t = time.time()
    try:
        p = subprocess.run(["bash", str(sub / "run.sh"), str(ds.resolve()), str(out)], cwd=sub,
                           capture_output=True, text=True, timeout=timeout)
        status, log = p.returncode, (p.stdout + p.stderr)[-800:]
    except subprocess.TimeoutExpired:
        status, log = "timeout", ""
    res = None
    if status == 0 and (out / "RESULT.json").is_file():
        try:
            res = json.loads((out / "RESULT.json").read_text())
        except json.JSONDecodeError as e:
            status, log = "malformed", str(e)
    shutil.rmtree(out, ignore_errors=True)
    return status, res, time.time() - t, log


def poi(res, name):
    for p in res.get("pois", []):
        if p.get("name") == name:
            return float(p["value"]), float(p["total"])
    raise KeyError(name)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("submission")
    ap.add_argument("suite")
    ap.add_argument("--plot", help="write the recovery plot (reported vs planted) to this PNG")
    ap.add_argument("--timeout", type=float, default=600)
    a = ap.parse_args()
    sub, suite = Path(a.submission).resolve(), Path(a.suite).resolve()
    if not (sub / "run.sh").is_file():
        raise SystemExit(f"no run.sh in {sub}")
    seeds = sorted(d for d in suite.glob("seed_*") if (d / "truth.json").is_file())
    if not seeds:
        raise SystemExit(f"no seed_*/truth.json under {suite}: make a suite with toy_suite.py")
    rows = []
    print(f"{'seed':9s} {'status':8s} {'wall':>6s}  {'mH planted':>10s} {'reported':>16s} {'pull':>6s}  "
          f"{'mu planted':>10s} {'reported':>14s} {'pull':>6s}  {'Z_exp':>5s} {'Z_obs':>5s} disc")
    for ds in seeds:
        truth = json.loads((ds / "truth.json").read_text())
        status, res, wall, log = run_seed(sub, ds, a.timeout)
        row = {"seed": ds.name, "truth": truth, "ok": False}
        if res is not None:
            try:
                (mh, mh_e), (mu, mu_e) = poi(res, "mH"), poi(res, "mu")
                row.update(ok=True, mH=mh, mH_e=mh_e, mu=mu, mu_e=mu_e,
                           z=float(res.get("significance_obs", 0.0)), disc=bool(res.get("discovery", False)))
            except (KeyError, TypeError, ValueError) as e:
                status = f"bad:{type(e).__name__}"
        zexp = truth.get("expected_significance", 0.0)
        if row["ok"]:
            pm, pu = (row["mH"] - truth["mH"]) / row["mH_e"], (row["mu"] - truth["mu"]) / row["mu_e"]
            row.update(pull_mH=pm, pull_mu=pu)
            print(f"{ds.name:9s} {'ok':8s} {wall:5.1f}s  {truth['mH']:10.2f} {row['mH']:8.2f} ± {row['mH_e']:5.2f} "
                  f"{pm:6.2f}  {truth['mu']:10.2f} {row['mu']:7.2f} ± {row['mu_e']:4.2f} {pu:6.2f}  "
                  f"{zexp:5.1f} {row['z']:5.1f} {'yes' if row['disc'] else 'no'}")
        else:
            print(f"{ds.name:9s} {str(status):8s} {wall:5.1f}s  {truth['mH']:10.2f} {'-':>16s} {'-':>6s}  "
                  f"{truth['mu']:10.2f} {'-':>14s} {'-':>6s}  {zexp:5.1f}" + (f"\n    {log.strip()[-300:]}" if log.strip() else ""))
        rows.append(row)

    ok = [r for r in rows if r["ok"]]
    strong = [r for r in ok if r["truth"].get("expected_significance", 0) >= Z_APPLICABLE]
    null = [r for r in ok if r["truth"]["mu"] == 0]
    print(f"\nrecovery: {len(ok)}/{len(rows)} seeds completed with a valid RESULT.json")
    print(f"scored for mH and mu: {len(strong)} seeds with expected significance >= {Z_APPLICABLE:g}; "
          f"{len(null)} null seeds")
    for name in ("mH", "mu"):
        if len(strong) < 3:
            print(f"  {name}: fewer than 3 scorable seeds, no slope")
            continue
        x = np.array([r["truth"][name] for r in strong]); y = np.array([r[name] for r in strong])
        pulls = np.array([r[f"pull_{name}"] for r in strong])
        slope = np.polyfit(x, y, 1)[0] if np.ptp(x) > 0 else float("nan")
        width = float(np.sqrt(np.mean(pulls ** 2)))
        verdict = "OK" if 0.7 <= width <= 1.4 else ("UNDER-covering: error bars too small" if width > 1.4 else "OVER-covering: error bars too large")
        print(f"  {name}: sensitivity slope {slope:5.2f} (1 = faithful, 0 = constant) | bias (mean pull) {pulls.mean():+5.2f} "
              f"| calibration (pull RMS) {width:4.2f} -> {verdict}")
    if null:
        fdr = sum(r["disc"] for r in null) / len(null)
        print(f"  false-discovery rate: {fdr:.2f} ({sum(r['disc'] for r in null)} of {len(null)} null seeds claimed)")
    if strong:
        power = sum(r["disc"] for r in strong) / len(strong)
        print(f"  discovery power: {power:.2f} ({sum(r['disc'] for r in strong)} of {len(strong)} strong seeds claimed)")

    if a.plot:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            print("no matplotlib: skipping the plot")
            return
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
        fig.tight_layout(); fig.savefig(a.plot, dpi=130)
        print(f"plot: {a.plot}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Look at one dataset, and at what a pipeline said about it:

    python3 explore.py datasets/public/seed_000
    python3 explore.py suites/mine/seed_003 --result out/RESULT.json --out seed_003.png

Left: the data histogram with the MC background template (nominal normalisation) and, if known, the signal
template at the planted or reported mass. Right: the control sample against the nominal MC control template,
which shows the detector response (a shift of the peak = the mass scale, a wider peak = extra smearing).
Prints the counts, the truth if truth.json is beside the dataset, and the pulls if a RESULT.json is given.
"""
import argparse
import json
from pathlib import Path

import numpy as np


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dataset")
    ap.add_argument("--result", help="a RESULT.json your run.sh wrote for this dataset")
    ap.add_argument("--out", default="explore.png")
    a = ap.parse_args()
    d = Path(a.dataset)
    m = np.load(d / "data" / "events.npy"); ctrl = np.load(d / "control" / "events.npy")
    bkg = np.load(d / "mc" / "background.npy"); ctrl_mc = np.load(d / "mc" / "control_mc.npy")
    xs = json.loads((d / "mc" / "cross_sections.json").read_text())
    grid = {float(p.stem.split("mH")[1]): np.load(p) for p in sorted((d / "mc").glob("signal_mH*.npy"))}
    truth = json.loads((d / "truth.json").read_text()) if (d / "truth.json").is_file() else None
    res = json.loads(Path(a.result).read_text()) if a.result else None
    print(f"{d}: {m.size} data events in [100, 160), {ctrl.size} control events in [70, 110)")
    print(f"  mean control mass {ctrl.mean():.3f} GeV (nominal MC {ctrl_mc.mean():.3f}); "
          f"control RMS {ctrl[(ctrl > 85) & (ctrl < 97)].std():.3f} GeV (MC {ctrl_mc[(ctrl_mc > 85) & (ctrl_mc < 97)].std():.3f}) in 85–97")
    if truth:
        print(f"  truth: mH {truth['mH']:.2f}  mu {truth['mu']:.2f}  bkg_norm {truth['bkg_norm']:.3f}  scale {truth['scale']:.4f}  "
              f"smear {truth['smear']:.4f}  signal events {truth.get('n_signal_realized')}  Z_exp {truth.get('expected_significance')}")
    pois = {p["name"]: p for p in res.get("pois", [])} if res else {}
    if res:
        line = "  result:"
        for k in ("mH", "mu"):
            if k in pois:
                line += f" {k} {pois[k]['value']:.3f} ± {pois[k]['total']:.3f}"
                if truth:
                    line += f" (pull {(pois[k]['value'] - truth[k]) / pois[k]['total']:+.2f})"
        print(line + f"  Z {res.get('significance_obs', float('nan')):.2f}  discovery {res.get('discovery')}")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    ax = axes[0]; e = np.arange(100.0, 160.5, 1.0); c = 0.5 * (e[1:] + e[:-1])
    n, _ = np.histogram(m, e); ax.errorbar(c, n, yerr=np.sqrt(n), fmt="o", ms=3, color="k", label=f"data, {m.size} events")
    nb, _ = np.histogram(bkg, e); ax.step(e, np.append(nb * xs["background_expected"] / nb.sum(), 0), where="post", color="#2f6db5", label="MC background, nominal 2000")
    mark = (truth or {}).get("mH") if truth else (pois.get("mH") or {}).get("value")
    if mark is not None and grid:
        near = min(grid, key=lambda g: abs(g - mark)); ns, _ = np.histogram(grid[near] + (mark - near), e)
        ysm = float(np.interp(mark, [float(k) for k in xs["signal_expected_SM"]], list(xs["signal_expected_SM"].values())))
        mu = (truth or {}).get("mu", (pois.get("mu") or {}).get("value", 1.0))
        ax.step(e, np.append(ns * mu * ysm / max(ns.sum(), 1), 0), where="post", color="#b8322f", label=f"signal template moved to {mark:.1f} GeV, μ = {mu:.2f}")
    if truth: ax.axvline(truth["mH"], color="#b8322f", ls="--", lw=1, label="planted mass")
    if "mH" in pois: ax.axvspan(pois["mH"]["value"] - pois["mH"]["total"], pois["mH"]["value"] + pois["mH"]["total"], color="#d98a1e", alpha=0.3, label="reported mass ± error")
    ax.set_xlabel("mass [GeV]"); ax.set_ylabel("events / GeV"); ax.set_xlim(100, 160); ax.legend(frameon=False, fontsize=8)
    ax = axes[1]; e2 = np.arange(80.0, 100.5, 0.5); c2 = 0.5 * (e2[1:] + e2[:-1])
    n2, _ = np.histogram(ctrl, e2); ax.errorbar(c2, n2, yerr=np.sqrt(n2), fmt="o", ms=3, color="k", label="control data")
    n3, _ = np.histogram(ctrl_mc, e2); ax.step(e2, np.append(n3 * n2.sum() / max(n3.sum(), 1), 0), where="post", color="#2f6db5", label="nominal MC control, scaled to the data")
    ax.axvline(91.19, color="0.5", ls=":", lw=1, label="91.19 GeV")
    ax.set_xlabel("mass [GeV]"); ax.set_ylabel("events / 0.5 GeV"); ax.legend(frameon=False, fontsize=8)
    ax.set_title("a shifted peak = mass scale; a wider peak = extra smearing", fontsize=9)
    fig.suptitle(str(d), fontsize=10); fig.tight_layout(); fig.savefig(a.out, dpi=130)
    print("plot:", a.out)


if __name__ == "__main__":
    main()

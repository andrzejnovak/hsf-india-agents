#!/usr/bin/env python3
"""Make your own toy suites for the gauss_peak task, truth included, so you can score yourself before you submit.

    python3 toy_suite.py suites/mine --n 10 --seed 7            # seed_000 public, seed_001.. with hidden truths
    python3 toy_suite.py suites/easy --n 10 --seed 7 --no-response   # mass scale 1, no extra smearing
    python3 toy_suite.py suites/grid --design '[{"mH": 118, "mu": 2}, {"mH": 132, "mu": 0.5}, {"mu": 0}]'

Every dataset has exactly the layout of datasets/public/seed_000 (DATASET.md), plus a truth.json beside it.
The organisers' sealed suite is drawn from the same priors with a seed you do not have.
The generator is the task's own, copied here with nothing changed; the MC library is identical for every seed.
"""
import argparse
import json
from pathlib import Path

import numpy as np

M_LO, M_HI = 100.0, 160.0
BKG_DECAY = 30.0
SIG_RES = 2.0
N_BKG_EXP = 2000.0
Z_MASS, Z_WIDTH = 91.19, 2.5
C_LO, C_HI = 70.0, 110.0
CTRL_FLAT_FRAC = 0.05
N_CTRL_EXP = 200_000
SIG_GRID = [115.0, 120.0, 125.0, 130.0, 135.0]
N_MC_SIG, N_MC_BKG, N_MC_CTRL = 20_000, 200_000, 200_000
MC_SEED = 20260917          # the MC library is identical for every seed and suite
PRIORS = {"mH_range": [115.0, 135.0], "mu_range": [0.0, 3.0], "null_fraction": 0.2,
          "bkg_norm_range": [0.9, 1.1], "scale_range": [0.985, 1.015], "smear_range": [0.0, 0.015], "lumi_fb": 20.0}
PUBLIC_TRUTH = {"mH": 125.0, "mu": 1.0, "bkg_norm": 1.0, "scale": 1.0, "smear": 0.0, "lumi_fb": 20.0}


def n_sm(m):
    return 120.0 * np.exp(-(np.asarray(m, float) - 125.0) / 50.0)


def expected_significance(truth) -> float:
    """Asimov local significance of the injected signal in a +-2 sigma mass window."""
    mH, mu = float(truth["mH"]), float(truth["mu"])
    if mu <= 0:
        return 0.0
    width = float(np.sqrt(SIG_RES ** 2 + (float(truth.get("smear", 0.0)) * mH) ** 2))
    lo, hi = mH - 2 * width, mH + 2 * width
    norm = 1.0 - np.exp(-(M_HI - M_LO) / BKG_DECAY)
    cdf = lambda x: (1.0 - np.exp(-(x - M_LO) / BKG_DECAY)) / norm
    b = N_BKG_EXP * float(truth.get("bkg_norm", 1.0)) * (cdf(hi) - cdf(lo))
    s = 0.9545 * mu * float(n_sm(mH))
    return float(np.sqrt(2.0 * ((s + b) * np.log1p(s / b) - s)))


def trunc_exp(rng, n, lo, hi, decay):
    u = rng.random(n)
    return lo - decay * np.log1p(-u * (1.0 - np.exp(-(hi - lo) / decay)))


def trunc_norm(rng, n, mean, sigma, lo, hi):
    out = np.empty(0)
    while out.size < n:
        x = rng.normal(mean, sigma, int(1.3 * (n - out.size)) + 16)
        out = np.concatenate([out, x[(x >= lo) & (x < hi)]])
    return out[:n]


def control_sample(rng, n):
    nflat = int(rng.binomial(n, CTRL_FLAT_FRAC))
    z = trunc_norm(rng, n - nflat, Z_MASS, Z_WIDTH, C_LO, C_HI)
    return np.concatenate([z, rng.uniform(C_LO, C_HI, nflat)])


def distort(rng, m, scale, smear):
    return m * scale * (1.0 + smear * rng.normal(size=m.size))


def window(m, lo, hi):
    return m[(m >= lo) & (m < hi)]


_MC = None


def mc_library():
    global _MC
    if _MC is None:
        rng = np.random.default_rng(MC_SEED)
        sig = {m: trunc_norm(rng, N_MC_SIG, m, SIG_RES, M_LO, M_HI) for m in SIG_GRID}
        bkg = trunc_exp(rng, N_MC_BKG, M_LO, M_HI, BKG_DECAY)
        ctrl = control_sample(rng, N_MC_CTRL)
        _MC = (sig, bkg, ctrl)
    return _MC


def draw_truth(rng, priors, fixed=None):
    f = fixed or {}
    t = {"mH": float(f.get("mH", rng.uniform(*priors["mH_range"])))}
    if "mu" in f:
        t["mu"] = float(f["mu"])
    else:
        t["mu"] = 0.0 if rng.random() < priors["null_fraction"] else float(rng.uniform(*priors["mu_range"]))
    t["bkg_norm"] = float(f.get("bkg_norm", rng.uniform(*priors["bkg_norm_range"])))
    t["scale"] = float(f.get("scale", rng.uniform(*priors["scale_range"])))
    t["smear"] = float(f.get("smear", rng.uniform(*priors["smear_range"])))
    t["lumi_fb"] = float(priors["lumi_fb"])
    return t


def generate(truth, rng, d: Path):
    for sub in ("data", "control", "mc"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    s, r = truth["scale"], truth["smear"]
    n_sig = int(rng.poisson(truth["mu"] * float(n_sm(truth["mH"]))))
    n_bkg = int(rng.poisson(N_BKG_EXP * truth["bkg_norm"]))
    sig = trunc_norm(rng, n_sig, truth["mH"], SIG_RES, M_LO, M_HI) if n_sig else np.empty(0)
    bkg = trunc_exp(rng, n_bkg, M_LO, M_HI, BKG_DECAY)
    ev = window(distort(rng, np.concatenate([sig, bkg]), s, r), M_LO, M_HI)
    rng.shuffle(ev)
    np.save(d / "data" / "events.npy", ev.astype(np.float64))
    ctrl = window(distort(rng, control_sample(rng, int(rng.poisson(N_CTRL_EXP))), s, r), C_LO, C_HI)
    rng.shuffle(ctrl)
    np.save(d / "control" / "events.npy", ctrl.astype(np.float64))
    sig_mc, bkg_mc, ctrl_mc = mc_library()
    for m, arr in sig_mc.items():
        np.save(d / "mc" / f"signal_mH{int(m)}.npy", arr)
    np.save(d / "mc" / "background.npy", bkg_mc)
    np.save(d / "mc" / "control_mc.npy", ctrl_mc)
    xs = {
        "lumi_fb": truth["lumi_fb"],
        "signal_expected_SM": {f"{m:.1f}": float(n_sm(m)) for m in np.arange(105.0, 150.01, 1.0)},
        "signal_expected_SM_note": "expected signal events in the full dataset at mu = 1 as a function of the "
                                   "resonance mass; interpolate linearly between tabulated masses",
        "signal_mc_note": "mc/signal_mH<M>.npy are nominal (no detector response) templates at the grid masses",
        "background_expected": N_BKG_EXP,
        "background_note": "nominal expectation; the true normalisation differs by up to ~10% and must be "
                           "determined from the data",
        "control": {"expected_events": N_CTRL_EXP, "peak_mass": Z_MASS,
                    "flat_background_fraction": CTRL_FLAT_FRAC,
                    "note": "control/events.npy and data/events.npy carry the same detector response; "
                            "mc/control_mc.npy carries none"},
    }
    (d / "mc" / "cross_sections.json").write_text(json.dumps(xs, indent=1))
    (d / "lumi.json").write_text(json.dumps({"lumi_fb": truth["lumi_fb"]}))
    truth["n_signal_realized"], truth["n_background_realized"] = n_sig, n_bkg
    truth["expected_significance"] = round(expected_significance(truth), 3)
    (d / "truth.json").write_text(json.dumps(truth, indent=1))


def build(out: Path, n: int = 10, seed: int = 1, response: bool = True, design=None, log=print):
    """Write seed_000 (the public truth) and n - 1 drawn datasets under out/, truth.json beside each and a
    manifest.json listing them; returns the list of truths (seed name included)."""
    if out.exists():
        raise SystemExit(f"{out} exists; pick another name")
    priors = dict(PRIORS)
    if not response:
        priors["scale_range"], priors["smear_range"] = [1.0, 1.0], [0.0, 0.0]
    n = len(design) + 1 if design else n
    truths = []
    for i in range(n):
        rng = np.random.default_rng([seed, i])
        truth = dict(PUBLIC_TRUTH) if i == 0 else draw_truth(rng, priors, design[i - 1] if design else None)
        d = out / f"seed_{i:03d}"
        generate(truth, rng, d)
        truths.append({"seed": d.name, **truth})
        tag = "public" if i == 0 else f"Z_exp={truth['expected_significance']:.1f}"
        log(f"{d.name}  mH={truth['mH']:.2f}  mu={truth['mu']:.2f}  scale={truth['scale']:.4f}  "
            f"smear={truth['smear']:.4f}  {tag}")
    (out / "manifest.json").write_text(json.dumps({"task": "gauss_peak", "master_seed": seed,
                                                   "response": response, "seeds": truths}, indent=1))
    return truths


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out", help="suite directory to create")
    ap.add_argument("--n", type=int, default=10, help="datasets including the public seed_000 (default 10)")
    ap.add_argument("--seed", type=int, default=1, help="master seed; change it for another suite")
    ap.add_argument("--no-response", action="store_true", help="mass scale 1 and no extra smearing in every seed")
    ap.add_argument("--design", help="JSON list of truths to fix, one per sealed seed (unset keys are drawn)")
    a = ap.parse_args()
    out = Path(a.out)
    truths = build(out, a.n, a.seed, not a.no_response, json.loads(a.design) if a.design else None)
    print(f"wrote {len(truths)} datasets under {out}/ (truth.json beside each; seed_000 is at the public truth)")


if __name__ == "__main__":
    main()

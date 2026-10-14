"""A naive bump hunt: exponential background + Gaussian signal fitted to the data histogram.

It ignores the control sample on purpose, so it trusts the nominal detector response.  On a dataset with a mass
scale or extra smearing (DATASET.md), its mass comes out shifted and its error bar does not know: run it on a
suite from toy_suite.py and look at the mH pulls.  A starting point, not an answer.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

M_LO, M_HI, BIN = 100.0, 160.0, 0.5
SIG_RES = 2.0                          # the nominal resolution, from mc/signal_mH125.npy (ignoring any smearing)


def main(dataset: Path, out: Path):
    m = np.load(dataset / "data" / "events.npy")
    xs = json.loads((dataset / "mc" / "cross_sections.json").read_text())["signal_expected_SM"]
    grid = np.array(sorted(float(k) for k in xs)); n_sm = np.array([xs[f"{g:.1f}"] for g in grid])
    edges = np.arange(M_LO, M_HI + BIN / 2, BIN); c = 0.5 * (edges[1:] + edges[:-1])
    n, _ = np.histogram(m, edges)

    def expected(p):
        nb, tau, ns, mh = p
        bkg = np.exp(-(c - M_LO) / tau); bkg *= nb / bkg.sum()
        sig = np.exp(-0.5 * ((c - mh) / SIG_RES) ** 2); sig *= ns / max(sig.sum(), 1e-12)
        return bkg + sig

    def nll(p):
        if p[0] <= 0 or p[1] <= 1 or p[2] < 0 or not (M_LO + 5 < p[3] < M_HI - 5):
            return 1e12
        lam = np.clip(expected(p), 1e-9, None)
        return float(np.sum(lam - n * np.log(lam)))

    # a coarse mass scan picks the starting point, then a full minimisation
    best = None
    for mh0 in np.arange(110.0, 150.0, 0.5):
        r = minimize(nll, [n.sum(), 30.0, 20.0, mh0], method="Nelder-Mead", options={"xatol": 1e-3, "fatol": 1e-4, "maxiter": 4000})
        if best is None or r.fun < best.fun:
            best = r
    p = best.x
    # background-only fit for the significance
    bo = minimize(lambda q: nll([q[0], q[1], 0.0, 125.0]), [n.sum(), 30.0], method="Nelder-Mead")
    z = float(np.sqrt(max(0.0, 2.0 * (bo.fun - best.fun))))
    # statistical errors from a numerical Hessian of the NLL
    h = np.zeros((4, 4)); eps = np.array([max(1.0, 1e-3 * p[0]), 0.05, 0.5, 0.02])
    for i in range(4):
        for j in range(4):
            e_i, e_j = np.eye(4)[i] * eps[i], np.eye(4)[j] * eps[j]
            h[i, j] = (nll(p + e_i + e_j) - nll(p + e_i - e_j) - nll(p - e_i + e_j) + nll(p - e_i - e_j)) / (4 * eps[i] * eps[j])
    try:
        cov = np.linalg.inv(h)
        err = np.sqrt(np.clip(np.diag(cov), 0, None))
    except np.linalg.LinAlgError:
        err = np.array([np.nan, np.nan, np.sqrt(max(p[2], 1.0)), 1.0])
    ns, mh, ns_e, mh_e = p[2], p[3], err[2], err[3]
    mh_e = mh_e if np.isfinite(mh_e) and mh_e > 0 else 1.0
    ns_e = ns_e if np.isfinite(ns_e) and ns_e > 0 else np.sqrt(max(ns, 1.0))
    sm = float(np.interp(mh, grid, n_sm))
    mu, mu_e = ns / sm, ns_e / sm
    result = {
        "pois": [{"name": "mH", "value": float(mh), "stat": float(mh_e), "syst": 0.0, "total": float(mh_e)},
                 {"name": "mu", "value": float(mu), "stat": float(mu_e), "syst": 0.0, "total": float(mu_e)}],
        "significance_obs": z,
        "discovery": bool(z >= 5.0),
        "notes": "naive histogram fit, nominal response assumed (no in-situ calibration)",
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "RESULT.json").write_text(json.dumps(result, indent=1))
    print(f"mH = {mh:.2f} ± {mh_e:.2f}  mu = {mu:.2f} ± {mu_e:.2f}  Z = {z:.1f}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))

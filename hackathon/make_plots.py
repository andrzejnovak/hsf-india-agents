#!/usr/bin/env python3
"""The physics of the task in pictures, made from the toy itself:  python3 make_plots.py [--out figs] [--fast]

  data_public.png   the public dataset: a falling background and a bump at 125 GeV, with the MC templates
  fit.png           a fit, explained: the model's four knobs on the data, and the likelihood valley whose width is the error bar
  mu.png            the same mass with mu = 0, 1, 3: the signal strength
  moves.png         three datasets with the resonance planted at 117, 125, 133 GeV: the truth moves
  control.png       the detector response: the Z control peak shifted and smeared against the nominal MC,
                    and what the same response does to the signal peak
  pulls.png         the naive fit's pulls on 30 datasets, response off and on: what calibration means
  recovery.png      the naive fit's recovery plot on those 30 datasets, response on

The datasets are generated in a temporary folder with toy_suite.py's generator (same code as the task).
--fast skips the two naive-fit figures (about a minute of fitting).
"""
import argparse
import json
import shutil
import tempfile
from pathlib import Path

import numpy as np

import toy_suite as T

HERE = Path(__file__).resolve().parent
EDGES = np.arange(100.0, 160.0 + 0.25, 1.0)
C = 0.5 * (EDGES[1:] + EDGES[:-1])
BLUE, RED, GREY, ORANGE = "#2f6db5", "#b8322f", "#8a8a8a", "#d98a1e"


def make(truth, seed, root):
    rng = np.random.default_rng([seed, 1])
    d = root / f"s{seed}"
    t = dict(truth, lumi_fb=20.0)
    T.generate(t, rng, d)
    return d, t


def hist(ax, m, label, color, edges=EDGES, **kw):
    n, _ = np.histogram(m, edges)
    c = 0.5 * (edges[1:] + edges[:-1])
    ax.errorbar(c, n, yerr=np.sqrt(n), fmt="o", ms=3, color=color, label=label, lw=1, capsize=0, **kw)
    return n


def template(ax, arr, n_expected, label, color, edges=EDGES, ls="-"):
    n, _ = np.histogram(arr, edges)
    w = n_expected / max(n.sum(), 1)
    ax.step(edges, np.append(n * w, 0), where="post", color=color, lw=1.6, ls=ls, label=label)
    return n * w


def fig_data(root, out, plt):
    d, t = make(dict(T.PUBLIC_TRUTH), 11, root)
    m = np.load(d / "data" / "events.npy")
    sig = np.load(d / "mc" / "signal_mH125.npy"); bkg = np.load(d / "mc" / "background.npy")
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    hist(ax, m, f"the pseudo-data: {m.size} events, one mass each", "k")
    b = template(ax, bkg, T.N_BKG_EXP, "MC background template, scaled to the nominal 2000 events", BLUE)
    s = template(ax, sig, float(T.n_sm(125.0)), "MC signal template at 125 GeV, scaled to μ = 1 (120 events)", RED)
    ax.step(EDGES, np.append(b + s, 0), where="post", color=ORANGE, lw=1.6, label="background + signal")
    ax.annotate("a resonance: a bump 2 GeV wide\non a falling background", xy=(125, 1.05 * (b + s).max()), xytext=(137, 0.5 * (b + s).max()),
                arrowprops=dict(arrowstyle="->", color="0.3"), fontsize=10, color="0.2")
    ax.set_xlabel("reconstructed mass [GeV]"); ax.set_ylabel("events / GeV"); ax.set_xlim(100, 160); ax.set_ylim(0, None)
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("The public dataset: planted mass 125 GeV, μ = 1, nominal response", fontsize=11)
    fig.tight_layout(); fig.savefig(out / "data_public.png", dpi=140); plt.close(fig)


def fig_fit(root, out, plt):
    """a fit, explained: a model with four knobs turned until it matches the histogram; the valley's width is the error bar"""
    from scipy.optimize import minimize
    d, t = make(dict(T.PUBLIC_TRUTH), 11, root)
    m = np.load(d / "data" / "events.npy")
    edges = np.arange(100.0, 160.5, 1.0); c = 0.5 * (edges[1:] + edges[:-1]); n, _ = np.histogram(m, edges)
    def expected(p):
        nb, tau, ns, mh = p
        bkg = np.exp(-(c - 100.0) / tau); bkg *= nb / bkg.sum()
        sig = np.exp(-0.5 * ((c - mh) / T.SIG_RES) ** 2); sig *= ns / max(sig.sum(), 1e-12)
        return bkg, sig
    def nll(p):
        if p[0] <= 0 or p[1] <= 1 or p[2] < 0: return 1e12
        lam = np.clip(sum(expected(p)), 1e-9, None); return float(np.sum(lam - n * np.log(lam)))
    best = min((minimize(nll, [n.sum(), 30.0, 100.0, mh0], method="Nelder-Mead", options={"xatol": 1e-4, "fatol": 1e-5, "maxiter": 5000}) for mh0 in (120.0, 125.0, 130.0)), key=lambda r: r.fun)
    nb, tau, ns, mh = best.x
    scan = np.arange(122.0, 128.01, 0.1)
    prof = np.array([minimize(lambda q: nll([q[0], q[1], q[2], x]), best.x[:3], method="Nelder-Mead", options={"xatol": 1e-4, "fatol": 1e-5}).fun for x in scan]) - best.fun
    inside = scan[prof <= 0.5]; lo, hi = inside.min(), inside.max(); sig_m = 0.5 * (hi - lo)
    mu = ns / float(T.n_sm(mh))
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), gridspec_kw={"width_ratios": [1.35, 1]})
    ax = axes[0]
    ax.errorbar(c, n, yerr=np.sqrt(n), fmt="o", ms=3, color="k", label="the data: a histogram of the masses")
    bkg, sg = expected(best.x)
    ax.step(edges, np.append(bkg, 0), where="post", color=BLUE, lw=1.5, ls="--", label="background: N$_{bkg}$ · exp(−m / τ)")
    ax.step(edges, np.append(bkg + sg, 0), where="post", color=ORANGE, lw=2, label="background + signal: N$_{sig}$ · Gauss(m$_H$, 2 GeV)")
    ax.text(0.98, 0.72, f"the four knobs, turned until the curve\nmatches the points (maximum likelihood):\n"
            f"N$_{{bkg}}$ = {nb:.0f}   τ = {tau:.1f} GeV\nN$_{{sig}}$ = {ns:.0f} → μ = {mu:.2f}   m$_H$ = {mh:.2f} GeV",
            transform=ax.transAxes, ha="right", va="top", fontsize=9, bbox=dict(boxstyle="round", fc="white", ec="0.7"))
    ax.set_xlabel("reconstructed mass [GeV]"); ax.set_ylabel("events / GeV"); ax.set_xlim(100, 160); ax.set_ylim(0, None)
    ax.legend(frameon=False, fontsize=9, loc="upper left"); ax.set_title("A fit: a model with four knobs, matched to the data", fontsize=11)
    ax = axes[1]
    ax.plot(scan, prof, color=RED, lw=2)
    ax.axhline(0.5, color="0.5", ls=":", lw=1); ax.axvline(mh, color="0.5", ls=":", lw=1)
    ax.axvspan(lo, hi, color=ORANGE, alpha=0.25, label=f"where the valley is less than ½ unit deep:\nm$_H$ = {mh:.2f} ± {sig_m:.2f} GeV")
    ax.annotate("best fit = the bottom", xy=(mh, 0), xytext=(mh + 1.2, 1.6), arrowprops=dict(arrowstyle="->", color="0.3"), fontsize=9, color="0.2")
    ax.set_xlabel("m$_H$ tried [GeV]"); ax.set_ylabel("how much worse the match gets  (ΔNLL)"); ax.set_ylim(0, 6); ax.set_xlim(scan.min(), scan.max())
    ax.legend(frameon=False, fontsize=9, loc="upper right"); ax.set_title("The error bar: the width of the likelihood valley", fontsize=11)
    fig.tight_layout(); fig.savefig(out / "fit.png", dpi=140); plt.close(fig)


def fig_mu(root, out, plt):
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.9), sharey=True)
    for ax, mu in zip(axes, (0.0, 1.0, 3.0)):
        d, t = make({"mH": 125.0, "mu": mu, "bkg_norm": 1.0, "scale": 1.0, "smear": 0.0}, 20 + int(mu), root)
        m = np.load(d / "data" / "events.npy")
        hist(ax, m, "data", "k")
        b = template(ax, np.load(d / "mc" / "background.npy"), T.N_BKG_EXP, "background only", BLUE)
        ax.set_title(f"μ = {mu:g}: {t['n_signal_realized']} signal events on ~2000 background", fontsize=10)
        ax.set_xlabel("mass [GeV]"); ax.set_xlim(100, 160)
    axes[0].set_ylabel("events / GeV"); axes[0].legend(frameon=False, fontsize=9)
    fig.suptitle("Signal strength μ: how big the bump is, relative to the Standard Model expectation (μ = 1 is 120 events at 125 GeV)", fontsize=11)
    fig.tight_layout(); fig.savefig(out / "mu.png", dpi=140); plt.close(fig)


def fig_moves(root, out, plt):
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.9), sharey=True)
    for ax, mh in zip(axes, (117.0, 125.0, 133.0)):
        d, t = make({"mH": mh, "mu": 2.0, "bkg_norm": 1.0, "scale": 1.0, "smear": 0.0}, 30 + int(mh), root)
        m = np.load(d / "data" / "events.npy")
        hist(ax, m, "data", "k")
        template(ax, np.load(d / "mc" / "background.npy"), T.N_BKG_EXP, "background", BLUE)
        ax.axvline(mh, color=RED, ls="--", lw=1.2, label=f"planted mass {mh:g} GeV")
        ax.set_title(f"planted {mh:g} GeV, μ = 2", fontsize=10); ax.set_xlabel("mass [GeV]"); ax.set_xlim(100, 160)
    axes[0].set_ylabel("events / GeV"); axes[0].legend(frameon=False, fontsize=9)
    fig.suptitle("The truth moves between datasets: a pipeline that always answers 125 scores zero", fontsize=11)
    fig.tight_layout(); fig.savefig(out / "moves.png", dpi=140); plt.close(fig)


def fig_control(root, out, plt):
    t = {"mH": 125.0, "mu": 3.0, "bkg_norm": 1.0, "scale": 1.012, "smear": 0.012}
    d, t = make(t, 40, root)
    ctrl = np.load(d / "control" / "events.npy"); ctrl_mc = np.load(d / "mc" / "control_mc.npy")
    m = np.load(d / "data" / "events.npy"); sig = np.load(d / "mc" / "signal_mH125.npy"); bkg = np.load(d / "mc" / "background.npy")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    ax = axes[0]; e = np.arange(80.0, 100.5, 0.5)
    n = hist(ax, ctrl, "control data (same response as the data)", "k", edges=e)
    template(ax, ctrl_mc[(ctrl_mc >= 80) & (ctrl_mc < 100)], n.sum(), "nominal MC control template", BLUE, edges=e)
    ax.axvline(91.19, color=GREY, ls=":", lw=1, label="the Z mass, 91.19 GeV")
    ax.set_title(f"The Z control peak: scale {t['scale']:.3f}, smearing {100*t['smear']:.1f}% (hidden values)", fontsize=10)
    ax.set_xlabel("mass [GeV]"); ax.set_ylabel("events / 0.5 GeV"); ax.legend(frameon=False, fontsize=9)
    ax = axes[1]; e2 = np.arange(110.0, 140.5, 1.0)
    hist(ax, m, "data", "k", edges=e2)
    b = template(ax, bkg, T.N_BKG_EXP * (np.histogram(bkg, e2)[0].sum() / bkg.size), "background", BLUE, edges=e2)
    s = template(ax, sig, t["mu"] * float(T.n_sm(125.0)), "nominal signal template at 125 GeV, μ = 3", RED, edges=e2)
    ax.step(e2, np.append(b + s, 0), where="post", color=ORANGE, lw=1.4, label="background + nominal signal")
    ax.set_title("The same response on the signal: the data peak sits off the template", fontsize=10)
    ax.set_xlabel("mass [GeV]"); ax.legend(frameon=False, fontsize=9, loc="lower left")
    fig.suptitle("The detector response: measure it on the control peak, then apply it to your fit", fontsize=11)
    fig.tight_layout(); fig.savefig(out / "control.png", dpi=140); plt.close(fig)


def naive_on_suite(root, name, response, n, sub):
    import score_suite as S
    rows = []
    for i in range(n):
        rng = np.random.default_rng([1234 + (1 if response else 0), i])
        priors = dict(T.PRIORS)
        if not response:
            priors["scale_range"], priors["smear_range"] = [1.0, 1.0], [0.0, 0.0]
        truth = T.draw_truth(rng, priors, {"mu": float(rng.uniform(1.0, 3.0))})   # strong signals only: every seed is scored
        d = root / name / f"seed_{i:03d}"
        T.generate(truth, rng, d)
        status, res, wall, log = S.run_seed(sub, d, 600)
        if res is None:
            continue
        (mh, mh_e), (mu, mu_e) = S.poi(res, "mH"), S.poi(res, "mu")
        rows.append(dict(truth=truth, mH=mh, mH_e=mh_e, mu=mu, mu_e=mu_e))
    return rows


def fig_pulls(root, out, plt):
    sub = HERE / "examples" / "naive_fit"
    off = naive_on_suite(root, "off", False, 30, sub)
    on = naive_on_suite(root, "on", True, 30, sub)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.0), sharey=True)
    x = np.linspace(-5, 5, 200)
    for ax, rows, title in zip(axes, (off, on), ("response off: scale 1, no smearing", "response on: the sealed suite's priors")):
        pulls = np.array([(r["mH"] - r["truth"]["mH"]) / r["mH_e"] for r in rows])
        ax.hist(np.clip(pulls, -5, 5), bins=np.arange(-5, 5.5, 0.5), color=BLUE, alpha=0.75, label=f"mH pulls, {len(pulls)} datasets")
        ax.plot(x, len(pulls) * 0.5 * np.exp(-0.5 * x ** 2) / np.sqrt(2 * np.pi), color=RED, lw=1.5, label="width 1: a calibrated error bar")
        ax.set_title(f"{title}\nmean {pulls.mean():+.2f}, RMS {np.sqrt(np.mean(pulls**2)):.2f}", fontsize=10)
        ax.set_xlabel("pull = (reported − planted) / your error bar"); ax.legend(frameon=False, fontsize=9)
    axes[0].set_ylabel("datasets")
    fig.suptitle("The naive fit ignores the control sample: its error bars are honest without the response, and not with it", fontsize=11)
    fig.tight_layout(); fig.savefig(out / "pulls.png", dpi=140); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.2))
    for ax, name, unit in zip(axes, ("mH", "mu"), (" [GeV]", "")):
        for r in on:
            ax.errorbar(r["truth"][name], r[name], yerr=r[f"{name}_e"], fmt="o", ms=4, capsize=2, color=BLUE)
        lo, hi = ax.get_xlim(); ax.plot([lo, hi], [lo, hi], "k--", lw=1, label="reported = planted"); ax.set_xlim(lo, hi)
        ax.set_xlabel(f"planted {name}{unit}"); ax.set_ylabel(f"reported {name}{unit}"); ax.legend(loc="upper left", frameon=False)
    fig.suptitle("The naive fit on 30 datasets, response on: it follows the truth; the error bars are the problem", fontsize=11)
    fig.tight_layout(); fig.savefig(out / "recovery.png", dpi=140); plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="figs")
    ap.add_argument("--fast", action="store_true", help="skip the naive-fit figures (pulls.png, recovery.png)")
    a = ap.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="hack_figs_"))
    try:
        for f in (fig_data, fig_fit, fig_mu, fig_moves, fig_control) + (() if a.fast else (fig_pulls,)):
            f(root, out, plt); print("wrote", out / (f.__name__[4:] + ".png"))
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    main()

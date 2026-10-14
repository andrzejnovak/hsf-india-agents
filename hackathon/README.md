# Hackathon: plant a value, hide it, find it

One task, the toy version of the benchmark from Tuesday's talk: a narrow resonance of unknown mass and strength
in pseudo-data, with a detector response you must calibrate from a control sample. You build a pipeline on the
**one public dataset**; the organisers run it, unchanged, on **sealed datasets with hidden truths** and score
whether your answers move with the truth, with honest error bars.

Read, in this order: [`PROMPT.md`](PROMPT.md) (the task), [`DATASET.md`](DATASET.md) (the data),
[`EVAL_CONTRACT.md`](EVAL_CONTRACT.md) (what you deliver, how it is run and scored).

## Three levels

1. **A pipeline.** A `run.sh` that fits the four knobs (background amount and slope, signal amount and mass), passes
   the self-check and follows the truth on a suite you made (slope ≈ 1). The agent can write it from `PROMPT.md`;
   `examples/naive_fit` is one.
2. **Calibrated.** Measure the mass scale and the extra smearing on the Z control peak and apply them to the fit:
   pulls of width ≈ 1 with the response on, an honest significance, no false discoveries on the empty datasets.
3. **The agent does it.** A brief, a check it must pass, a reviewer, a second model: whatever gets `deepseek-v4-flash`
   or `glm-5` from the bare prompt to a level-2 pipeline on its own. How much context that takes is an open
   question; keep the prompts and the runs, they are the result.

The metric: **sensitivity** (the slope of reported vs planted; 1 is a measurement, 0 is a constant) while keeping
**calibration** (the width of your pulls with your own error bars; 1 is honest, 4 is the plain fit, 0.3 is padded).

## Setup (2 minutes, anywhere with git and Python 3)

Everything is in this repository, the public dataset included; the data is simulated, so nothing else is
needed. A Binder session from Tuesday works, and so does your laptop (`pip install numpy scipy matplotlib` if
they are missing: numpy and scipy are what submissions may use, matplotlib draws the pictures).

```bash
git clone https://github.com/andrzejnovak/hsf-india-agents.git   # or: cd ~/hsf-india-agents && git pull
cd hsf-india-agents/hackathon
python3 -m sbh check --task gauss_peak --submission examples/stub_submission --dataset datasets/public/seed_000 --determinism
```
The last line must say `determinism (second clean run): PASS`. Then make your team's workspace:

```bash
bash new_team.sh <team-name>        # -> ~/hack-<team-name>: task files, the public dataset, submission/ with the stub
```

## The loop

1. **Build** `~/hack-<team>/submission/`: a `run.sh <dataset_dir> <output_dir>` that writes `<output_dir>/RESULT.json`
   (format in EVAL_CONTRACT.md §2). Python 3 with **numpy and scipy only**. `examples/naive_fit/` is a working
   start that ignores the control sample on purpose: see what that does to its error bars before you copy it.
2. **With the agent:** `cd ~/hack-<team> && opencode`, then paste:
   > Read PROMPT.md, DATASET.md and EVAL_CONTRACT.md in this folder. Build the submission in `submission/`:
   > a `run.sh <dataset_dir> <output_dir>` that writes `<output_dir>/RESULT.json`. The public dataset is
   > `datasets/public/seed_000`. Python 3 with numpy and scipy only. Do not hard-code the public dataset's answer.
3. **Self-check** (hygiene, the contract, determinism), from this folder:
   ```bash
   python3 -m sbh check --task gauss_peak --submission ~/hack-<team>/submission --dataset datasets/public/seed_000 --determinism
   ```
4. **Score yourself** on suites you make, truth included, before the sealed one:
   ```bash
   python3 toy_suite.py suites/mine --n 10 --seed 7        # 1 public + 9 hidden-truth datasets; --no-response for the easy version
   python3 score_suite.py ~/hack-<team>/submission suites/mine --plot recovery.png
   ```
   Change `--seed` for a fresh suite. The sealed suite is drawn from the same priors with a seed you don't have.
5. **Submit**: your workspace is a git repository; push it to GitHub and post one line on the
   [submissions issue](https://github.com/andrzejnovak/hsf-india-agents/issues/1):
   ```bash
   cd ~/hack-<team> && git add -A && git commit -m "our submission" && git push    # a public repository of yours (git remote add origin <url> the first time)
   cd ~/hsf-india-agents/hackathon && bash submit.sh <team-name> <git url>          # the self-check, is it pushed, then the line to post
   ```
   The line is `<team-name>: <git url> @ <commit>`; `submit.sh` posts it for you when `gh` is logged in, else
   paste it as a comment. Submit as often as you like: a new comment replaces your earlier one, and the last
   comment per team before the deadline is the commit that gets run. A submission that fails the self-check
   is not submitted (`--no-check` if the check cannot run on your machine; the organisers run it anyway).
   Pushing from a Binder session needs a GitHub token as the password (github.com → Settings → Developer
   settings → Personal access tokens); from your laptop it is your usual push.

## The physics, in five pictures

`python3 make_plots.py` draws all of them from the toy (`figs/`; `--fast` skips the two that fit 60 datasets).

1. **[`figs/data_public.png`](figs/data_public.png) — the data.** Each event is one number, a reconstructed mass in
   GeV. Background falls off exponentially; a particle of mass m<sub>H</sub> shows as a Gaussian bump 2 GeV wide. The
   MC templates in `mc/` (a background shape, signal shapes at 115…135 GeV) are what you fit with.
2. **[`figs/fit.png`](figs/fit.png) — a fit.** A measurement is a model with a few knobs turned until it matches
   the histogram: here N<sub>bkg</sub> and τ for the falling background, N<sub>sig</sub> and m<sub>H</sub> for the
   bump (maximum likelihood: the knobs that make the observed counts most probable). Move m<sub>H</sub> away from
   the best value and the match gets worse; the width of that valley, where it is less than ½ unit worse, is the
   error bar. An honest error bar covers the truth about two times in three; that is what the sealed run tests.
3. **[`figs/mu.png`](figs/mu.png) — the signal strength μ.** How many signal events, relative to the Standard Model
   expectation at that mass (`mc/cross_sections.json`: 120 events at 125 GeV for μ = 1). μ = 0 is no signal, one
   dataset in five. The *significance* is how unlikely the bump is from background alone, in σ; `discovery: true`
   is a claim that it is real (Z ≥ 5), and claiming it on an empty dataset is a false discovery.
3. **[`figs/moves.png`](figs/moves.png) — the truth moves.** Every sealed dataset has its own planted mass between
   115 and 135 GeV, its own μ and background normalisation. Answer 125 every time and your slope is 0.
4. **[`figs/control.png`](figs/control.png) — the detector response.** The data's masses carry a hidden *scale*
   (every mass multiplied by a number within ±1.5 % of 1) and extra *smearing* (up to 1.5 % resolution). The control
   sample, a known peak (the Z boson at 91.19 GeV, 200k events), carries the same response; the MC templates carry
   none. Measure the shift and the widening there, then correct your fit: without it, the mass is biased by up to
   2 GeV with an error bar of a few hundred MeV.
5. **[`figs/pulls.png`](figs/pulls.png) and [`figs/recovery.png`](figs/recovery.png) — calibration.**
   pull = (reported − planted) / your error bar; a calibrated pipeline has pulls of width 1. The naive fit on 30
   datasets follows the truth (slope ≈ 1) with pulls of width 0.9 without the response and 4.0 with it: that is the
   under-coverage the sealed run fails you on. Quoting a huge error bar to be safe fails too.

## Debugging

```bash
bash ~/hack-<team>/submission/run.sh suites/mine/seed_003 out && cat out/RESULT.json    # one dataset by hand
python3 explore.py suites/mine/seed_003 --result out/RESULT.json --out seed_003.png     # the data, the truth, your answer, the control peak
```
`score_suite.py` prints a per-dataset table (status, pulls, and the last lines of `run.sh`'s output when it fails);
the self-check prints the traceback of a failed run. `seed_000` of any suite is the public truth, so a pipeline that
is right there and wrong elsewhere has hard-coded something.

## What gets scored (EVAL_CONTRACT.md §3, in one line each)

- **sensitivity**: slope of reported vs planted — 1 is a measurement, 0 is a memorised constant (the stub scores 0).
- **calibration**: width of your pulls `(reported − planted) / your total` — too small *and* too large both fail.
- **bias**, **precision** (vs the reference, only once calibration passes), **recovery** (fraction of datasets that run).
- **false-discovery rate** on datasets with no signal; **discovery power** on strong ones.

`score_suite.py` prints the same aggregates on your own suites. The organisers' leaderboard is the sealed run.

## Rules

- numpy + scipy; no other packages, no network at run time, ≤ 600 s per dataset, no data files inside `submission/`.
- `run.sh` must be deterministic (fix your random seeds) and read only `<dataset_dir>` and its own folder.
- Nothing from the public truth (mass 125, μ = 1, nominal response) may be hard-coded: the sealed datasets differ in all of it.
- Teams of three or so. Model variance is real: run the agent twice before you trust a design.
- The leaderboard: level 0, 1 or 2 as above (level 1: slope of m<sub>H</sub> ≥ 0.8 with the self-check passing and every
  dataset run; level 2: pull widths within [0.7, 1.4] for both and no false discovery), then closest to slope 1 and
  width 1 first. Level 3 is judged when you present: show the prompts and the runs.

## The day

1. Setup: the two commands above pass; teams and workspaces.
2. Build, self-check, score yourself; submit early and again whenever it gets better: every comment on the
   issue re-runs the sealed run (a GitHub Actions job, every submission on 20 fresh datasets nobody has seen)
   and updates the table below within a few minutes.
3. The deadline is announced in the room; the last comment per team on the issue before it counts.
4. The final sealed run: the table with recovery plots, one slide per team, then each team on how it got there
   (level 3 is judged there).

## Leaderboard

<!-- leaderboard -->
_Sealed run of 2026-10-14 05:31 UTC: 11 datasets nobody has seen, every submission on the [issue](https://github.com/andrzejnovak/hsf-india-agents/issues/1) at its last comment. Recovery plots follow after the deadline._

| # | team     | level | slope mH | slope μ | pull width mH | pull width μ | false disc. | power | recovery | self-check | submitted                                      |
|---|----------|-------|----------|---------|---------------|--------------|-------------|-------|----------|------------|------------------------------------------------|
| 1 | demo-red | 1     | 1.06     | 0.94    | 4.06          | 0.62         | 0/2         | 1.00  | 11/11    | PASS       | b178cea (2026-10-14T05:23:09Z by andrzejnovak) |
<!-- /leaderboard -->

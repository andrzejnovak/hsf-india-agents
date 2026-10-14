# Organiser notes

What is here: the participant bundle of `jfc-mit/slopbench_harness` for the `gauss_peak` task (`sbh pack` of a
throwaway suite, master seed 20261014 — its sealed seeds were discarded; only its public seed ships), plus
`toy_suite.py` (the task's generator, standalone, truth beside each dataset), `score_suite.py` (the contract's
aggregates on a home-made suite, no sandbox), `submit.sh` and `sealed_run.py` (below), `examples/naive_fit/` (a histogram fit without the in-situ
calibration: slope ≈ 1, under-covering on mH) and `new_team.sh`.

## Validate in 3 minutes (a Binder terminal)

```bash
cd ~/hsf-india-agents && git pull && cd hackathon
python3 -m sbh check --task gauss_peak --submission examples/stub_submission --dataset datasets/public/seed_000 --determinism   # PASS
python3 -m sbh check --task gauss_peak --submission examples/naive_fit --dataset datasets/public/seed_000 --determinism        # PASS, mH ≈ 125.2 ± 0.4
python3 toy_suite.py suites/t --n 6 --seed 3 && python3 score_suite.py examples/naive_fit suites/t --plot r.png              # slope ≈ 1, FDR 0
python3 explore.py suites/t/seed_001 --out e.png && python3 make_plots.py --fast --out /tmp/figs                              # the pictures regenerate
bash new_team.sh test && ls ~/hack-test                                                                                       # then rm -rf ~/hack-test
```
The slides' figures are `figs/*.png`, made by `make_plots.py` (the full run, with the two naive-fit figures, takes
about 90 s); the deck copies them as `assets/hack_*.png`.
Both `sbh check` runs need scipy in the Binder's `python3` (the kernel env), which the naive fit imports. The
self-check sandboxes the run with what the host allows (bwrap, else `setpriv` to `nobody` when root, else
`unshare -rn`, else none; `SBH_SANDBOX=none` forces the last); under `setpriv` the interpreter must be
world-readable (a conda env is).

## Before the start

```bash
python3 -c 'import secrets; print(secrets.randbelow(2**31))'   # the sealed seed: keep it to yourself until the leaderboard is up
```
Everything the students need is in this repository (the data is simulated, the public dataset is committed),
so they can work in a Binder session or on a laptop. They submit by pushing their team workspace (a git
repository `new_team.sh` makes) to GitHub and posting `<team>: <url> @ <commit>` as a comment on the
[submissions issue](https://github.com/andrzejnovak/hsf-india-agents/issues/1); `bash submit.sh <team> <url>`
runs the self-check, checks the commit is pushed and prints (or, with `gh`, posts) that line. The last comment
per team before the deadline counts. A team that cannot push hands you a tarball: unpack it as
`<out>/submissions/<team>/` and add a `<team>: file://<out>/submissions/<team> @ <commit>` line to a `--teams`
file (or any git URL you host it at).

## The sealed run in CI (the default)

`.github/workflows/sealed_run.yml` runs `sealed_run.py` on a GitHub-hosted runner on every comment on the
submissions issue and commits the table into `hackathon/README.md` (the `<!-- leaderboard -->` markers). The
suite is drawn from a seed made up in the job and never printed, so each run is self-contained and nothing
secret is stored anywhere; the submissions run as `nobody` with the truths unreadable (`--as nobody`) and a
scrubbed environment. After the deadline: Actions → "sealed run" → Run workflow with plots = true (and a
larger n if you like) for the final table with the recovery plots, committed under `hackathon/results/`;
the plots show the planted values per dataset, which is why they wait for the deadline. A fixed seed input
makes two runs comparable. The run takes a few minutes per team.

## The sealed run by hand (anywhere with git, python3, numpy, scipy)

```bash
cd hsf-india-agents/hackathon && git pull
python3 sealed_run.py --seed <secret>                        # reads issue 1, clones each team at its commit, ~/hack-sealed: 21 datasets (response on), truths kept apart; --as nobody where sudo allows it
cat ~/hack-sealed/results/leaderboard.md                     # per team: results/<team>/recovery.png, score.txt, check.txt
```
About 2 minutes per team with a pipeline like the naive fit (the self-check runs it twice, the suite 21 times;
`--team red` for one team, `--teams FILE` for a hand-made list, `--timeout` is the contract's 600 s per
dataset). The suite is reused on a second run with the same seed, so run it as submissions come in and once
more after the deadline. The levels and the order are in the script's docstring; `level()` is the one function
to change if the rule changes. The submissions run as you with no sandbox (only the self-check is sandboxed):
a throwaway session or a VM, not your own account, and `--out` somewhere private (the truths are there).

The private harness is the sandboxed alternative, on the clones `sealed_run.py` made (or your own):
```bash
python -m sbh build-suite --task gauss_peak --name hsf_sealed --n-seeds 21 --master-seed <secret>   # response on
python -m sbh closure --suite suites/hsf_sealed                                                      # sigma_ref for the precision term
SBH_BASE_ENV_ONLY=1 pixi run python -m sbh eval --suite suites/hsf_sealed --submission ~/hack-sealed/submissions/<team>/submission --label <team>
```
The submissions ship no pixi manifest, so `SBH_BASE_ENV_ONLY=1` runs them with the evaluator's interpreter:
check `pixi run python -c "import scipy"` first. The eval prints the aggregates per team.

## Two things found while packing

- `sbh pack` leaves `sbh/reaper.py` out of the bundle (`runner.py` reads it as a file, so the import-closure pruning
  drops it) and `sbh check` then fails with `FileNotFoundError: .../sbh/reaper.py`. Copied in by hand here; in the
  harness, add `"reaper.py"` to `PARTICIPANT_SBH` and to the closure roots in `finish_participant_bundle`.
- `sbh pack` imports every task module (`submission_dirs()`), so it needs `awkward` installed even for the toy.

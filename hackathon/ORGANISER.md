# Organiser notes

What is here: the participant bundle of `jfc-mit/slopbench_harness` for the `gauss_peak` task (`sbh pack` of a
throwaway suite, master seed 20261014 — its sealed seeds were discarded; only its public seed ships), plus
`toy_suite.py` (the task's generator, standalone, truth beside each dataset), `score_suite.py` (the contract's
aggregates on a home-made suite, no sandbox), `examples/naive_fit/` (a histogram fit without the in-situ
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
Both `sbh check` runs need scipy in the Binder's `python3` (the kernel env), which the naive fit imports; the
self-check runs the submission as user `nobody` under `setpriv`, so the interpreter must be world-readable (a
conda env is).

## The sealed run (your laptop, the private harness)

```bash
python -m sbh build-suite --task gauss_peak --name hsf_sealed --n-seeds 21 --master-seed <secret>   # response on
python -m sbh closure --suite suites/hsf_sealed                                                      # sigma_ref for the precision term
SBH_BASE_ENV_ONLY=1 pixi run python -m sbh eval --suite suites/hsf_sealed --submission /path/to/<team>/submission --label <team>
```
The submissions ship no pixi manifest, so `SBH_BASE_ENV_ONLY=1` runs them with the evaluator's interpreter:
check `pixi run python -c "import scipy"` first. The eval prints the aggregates per team; the leaderboard is
those lines in a table, the recovery plots come from the per-seed results in each run directory.

## Two things found while packing

- `sbh pack` leaves `sbh/reaper.py` out of the bundle (`runner.py` reads it as a file, so the import-closure pruning
  drops it) and `sbh check` then fails with `FileNotFoundError: .../sbh/reaper.py`. Copied in by hand here; in the
  harness, add `"reaper.py"` to `PARTICIPANT_SBH` and to the closure roots in `finish_participant_bundle`.
- `sbh pack` imports every task module (`submission_dirs()`), so it needs `awkward` installed even for the toy.

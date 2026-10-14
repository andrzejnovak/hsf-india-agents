# Hackathon: plant a value, hide it, find it

One task, the toy version of the benchmark from Tuesday's talk: a narrow resonance of unknown mass and strength
in pseudo-data, with a detector response you must calibrate from a control sample. You build a pipeline on the
**one public dataset**; the organisers run it, unchanged, on **sealed datasets with hidden truths** and score
whether your answers move with the truth, with honest error bars.

Read, in this order: [`PROMPT.md`](PROMPT.md) (the task), [`DATASET.md`](DATASET.md) (the data),
[`EVAL_CONTRACT.md`](EVAL_CONTRACT.md) (what you deliver, how it is run and scored).

## Setup (2 minutes, in a JupyterLab terminal)

```bash
cd ~/hsf-india-agents && git pull && cd hackathon
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
5. **Submit** by the deadline: copy `submission/` (code only, no data) to the shared folder:
   ```bash
   cp -r ~/hack-<team>/submission /data/hackathon/<team-name>
   ```

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

## Schedule

| when | what |
|---|---|
| start | setup, both commands above pass |
| start + 30 min | first self-check passes on your own pipeline (the stub does not count) |
| deadline | `submission/` in `/data/hackathon/<team-name>` |
| after | the sealed run: recovery plots and the leaderboard, one slide per team |

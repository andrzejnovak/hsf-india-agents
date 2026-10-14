# EVAL_CONTRACT v0.1-toy — submission contract for `gauss_peak`

This file is part of the input given to the analysis agent.  Everything below
is checked mechanically.

## 1. Submission form

A submission is a directory (ideally a git repository) whose root contains an
executable `run.sh`.  The harness freezes the directory into an immutable
snapshot and executes, from a clean unpack, for every sealed seed:

    ./run.sh <dataset_dir> <output_dir>

- `<dataset_dir>` has exactly the layout of the public seed (DATASET.md).
- `<output_dir>` exists and is empty; write `RESULT.json` there (GATE).
  Output files are read only as regular files: a symlink there is never
  followed, and a symlinked `RESULT.json` counts as malformed.
- Exit code 0 signals success.  Non-zero exit, timeout, or a malformed
  `RESULT.json` scores the seed as failed and counts against recovery.
- Repeated execution on the same dataset must reproduce `RESULT.json`
  (fix your random seeds).

Hygiene, checked before freezing: no data files (`.npy`, `.root`, `.parquet`,
…), no committed outputs or truth files, no symlinks, ≤ 5 MB per file,
≤ 50 MB total.
A `pylib/` directory of vendored packages is exempt from the two size caps
(own budget 4 GB); the data-file and truth-name rules apply inside it too,
except that a data file identical to the one the evaluation interpreter's
own packages install at the same path (e.g. numpy's bundled test data,
which `pip install --target` re-vendors) is recognized and allowed.

Runtime: Python 3.14 with `numpy` importable (no `scipy` in the base
environment — declare it in your own pixi manifest if needed); no network; the
pipeline may read only `<dataset_dir>` and its own directory.  Limits per
seed: 600 s wall clock, 6 GB memory (v0 defaults).

## 2. RESULT.json (result type `search`)

    {
      "pois": [
        {"name": "mH", "value": f, "stat": f, "syst": f, "total": f},
        {"name": "mu", "value": f, "stat": f, "syst": f, "total": f}
      ],
      "significance_obs": f,          # local, in sigma; 0 if no excess
      "discovery": bool,              # your discovery claim (e.g. Z >= 5)
      "nuisances": {                  # optional, scored as a calibration check
        "gauss_scale": {"value": f, "unc": f},
        "gauss_smear": {"value": f, "unc": f}
      }
    }

All values finite; `total` > 0 and consistent with `stat ⊕ syst`.  Nuisance
names follow the grammar of `sbh/hep/names.py`; this task's own are
`gauss_<label>`: `gauss_scale` (the data mass scale, 1 = nominal) and
`gauss_smear` (extra relative mass resolution).  Extra keys are allowed and
ignored.

## 3. How you are scored (aggregate metrics only)

Across the sealed suite, per POI:

- **sensitivity** — slope of recovered vs injected value (unit slope = faithful
  measurement; a constant output scores zero).  Gate.
- **bias** — mean pull `(value − truth) / total`.
- **calibration** — width of the pull distribution using YOUR quoted `total`;
  both under- and over-coverage fail.
- **precision** — `min(1, σ_ref / total)`, awarded only if calibration passes
  (σ_ref is the reference pipeline's uncertainty).
- **recovery** — fraction of seeds that complete with a valid result.
- **false-discovery rate** — fraction of no-signal seeds on which you claim
  discovery.

- **discovery power** — fraction of strong-signal seeds on which you claim
  discovery.

`S_phys = recovery × mean_POI(sensitivity_gate × calibration_gate × precision)`.
Pulls and slopes use only seeds whose injected signal has expected local
significance ≥ 5 (a truth-based rule, the same for every submission); null
seeds enter the false-discovery rate.  You receive these aggregates; never
per-seed truths or per-seed results.

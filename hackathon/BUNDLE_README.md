# gauss_peak — participant bundle

You are given ONE development dataset:

    datasets/public/seed_000/      (described in DATASET.md)

Read, in this order: `PROMPT.md` (the task), `DATASET.md` (what the data
is), `EVAL_CONTRACT.md` (what your submission must deliver and how it is
executed — the contract is the single source for that).

Develop however you like — internet included.  The evaluation run itself
is offline and reproducible from your submission alone (EVAL_CONTRACT.md).

## Self-check before submitting

    python3 -m sbh check --task gauss_peak --submission <your_dir> \
        --dataset datasets/public/seed_000 --determinism

`examples/stub_submission/` shows the minimal interface (it never reads the
data and scores zero -- do not copy its physics).

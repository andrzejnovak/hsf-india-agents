Search for and measure a narrow resonance in the pseudo-dataset described in
DATASET.md (a toy stand-in for a CMS H->ZZ*->4l analysis).

Deliver a reproducible analysis directory that conforms to EVAL_CONTRACT.md:
a `run.sh <dataset_dir> <output_dir>` entrypoint that writes
`<output_dir>/RESULT.json` with the measured mass `mH`, the signal strength
`mu` (= sigma/sigma_SM at that mass; report 0 +- unc if no signal), the
observed local significance, and a discovery flag.

Develop against the public seed only (generated at the disclosed public parameters).
Your frozen pipeline will then be executed unchanged on sealed datasets with
the same layout but different injected mass, signal strength, background
normalisation, and detector response (mass scale and extra smearing).  The
nominal MC does not carry that response; the control sample does.  Do not
hard-code any number from the public truth, from the MC grid masses, or from
"known" physics: what is scored is whether your pipeline tracks the injected
truth across seeds, with honest uncertainties.

Use Python with numpy and scipy only.  Keep the run under a few minutes per
dataset.  Use only files under <dataset_dir>; there is no network at run time.
Verify your submission with:

    python3 -m sbh check --task gauss_peak --submission <your_dir> --dataset datasets/public/seed_000 --determinism

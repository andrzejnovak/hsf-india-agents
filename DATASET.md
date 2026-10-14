# TASK CARD — `gauss_peak` (toy stand-in for the H→ZZ*→4ℓ sealed-truth task)

## Physics statement

A pseudo-dataset of reconstructed "four-lepton" masses may contain a narrow
resonance on top of a smoothly falling background.  Search for it, measure its
mass and signal strength, and report the observed local significance.

The detector response of the pseudo-data is **not** the nominal one used to
produce the simulation: every reconstructed mass in the data carries an
unknown multiplicative scale and an unknown extra resolution smearing.  A
high-statistics control sample (a "Z → ℓℓ" peak at 91.19 GeV) carries the
same response, so the corrections can be measured in situ and transferred.

## Dataset layout (identical for every seed)

    data/events.npy          reconstructed masses in [100, 160) GeV — the pseudo-data
    control/events.npy       control-sample masses in [70, 110) GeV — same response as the data
    mc/signal_mH115.npy … mc/signal_mH135.npy
                             nominal signal templates at 115, 120, 125, 130, 135 GeV
                             (20 000 events each, resolution as simulated, NO response)
    mc/background.npy        nominal background template (200 000 events)
    mc/control_mc.npy        nominal control-sample template (200 000 events)
    mc/cross_sections.json   expected SM signal yield vs mass at this luminosity (mu = 1),
                             nominal background expectation, control-sample description
    lumi.json                {"lumi_fb": 20.0}

The public development seed is generated at the stated public parameters
(the packed bundle ships no `truth.json`; sealed truths are never shipped).

## Sealed parameters (drawn per seed)

| parameter | meaning | prior (v0) |
|---|---|---|
| `mH` | resonance mass | uniform 115–135 GeV, or fixed by the suite design |
| `mu` | signal strength σ/σ_SM (0 = no signal) | uniform 0–3 with a 20 % null admixture |
| `bkg_norm` | background normalisation relative to nominal | uniform 0.9–1.1 |
| `scale` | multiplicative mass scale in data and control | uniform 0.985–1.015 |
| `smear` | extra relative resolution in data and control | uniform 0–1.5 % |

Suites can switch the response off (`scale = 1`, `smear = 0`).

## Result type: `search`

`RESULT.json` must report POIs `mH` and `mu`, plus `significance_obs` and
`discovery` (see EVAL_CONTRACT.md).  Optionally report the recovered response
under `nuisances` (`gauss_scale`, `gauss_smear`; see EVAL_CONTRACT.md); it is scored against the injected
values as a calibration check (not part of the physics score).

## How the suite is scored

Per-seed pulls and the sensitivity slopes of `mH` and `mu` use only seeds
whose injected signal has an expected local significance ≥ 5 (computed from
the injected truth, independent of any pipeline; the toy keeps this
original gate — the real `h4l` task uses Z ≥ 3).  Null seeds (`mu = 0`)
enter the false-discovery rate; weak-signal seeds enter recovery and
discovery power only.  This is the "measurement conditional on discovery"
rule of a search: a mass and signal strength are only meaningful once there
is a signal to measure.  See EVAL_CONTRACT.md.

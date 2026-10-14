"""The ``pois`` kind: RESULT.json parameters of interest with their uncertainties, scored directly."""
from __future__ import annotations

from ..base import Kind


class PoisKind(Kind):
    name = "pois"
    attack_families = {
        "constant": "never reads the data: one fixed answer for every dataset",
        "crasher": "fails on part of the datasets (recovery)",
        "inflator": "overstates every uncertainty (over-coverage)",
        "memorizer": "fixes a parameter at a remembered value and fits the rest",
        "nocalib": "skips the in-situ calibration and trusts the nominal simulation (bias)",
    }


KIND = PoisKind()

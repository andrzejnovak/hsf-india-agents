"""Output kinds: what a submission returns per dataset, and how the evaluator checks and scores it.

The core (runner, sandbox, sealed truth, scoring framework, packaging) knows only RESULT.json; a task
(tasks/<name>/) is the physics.  An output kind sits between them, shared by every task returning the same kind of
answer; a task names it in ``Task.kind``.

- ``pois``: RESULT.json parameters of interest with uncertainties, scored directly.
- ``binned_likelihood``: pois plus a declared pyhf model (MODEL.json) the evaluator refits, the mass grid
  (MODEL_GRID/), the event list (EVENTS.json), goodness of fit, truthfulness and claims.
- ``corrections``: correctionlib functions (corrections.json) answering a dataset's request, with uncertainties and
  the declared measurement (MEASUREMENT.json), scored at evaluation points.

See docs/ADDING_A_TASK.md for where a new task or kind goes.
"""
from __future__ import annotations

from importlib import import_module

# kind name -> module exposing KIND (a sbh.kinds.base.Kind)
KINDS = {"pois": "sbh.kinds.pois", "binned_likelihood": "sbh.kinds.binned_likelihood",
         "corrections": "sbh.kinds.corrections"}


def card_files():
    """Every kind's Kind.card_files, sorted (the card's staleness key reads them for any run)."""
    return sorted({n for k in KINDS for n in get_kind(k).card_files})


def page_files():
    """Every kind's Kind.page_files, sorted (a published run keeps them: sbh/runstore.py)."""
    return sorted({n for k in KINDS for n in get_kind(k).page_files})


def scoreboard_tables(summaries):
    """Every kind's scoreboard table (Kind.scoreboard_rows), in KINDS order."""
    return [line for k in KINDS for line in get_kind(k).scoreboard_rows(summaries)]


def get_kind(task_or_name):
    """The Kind of a task (its ``kind`` attribute) or of a kind name."""
    name = task_or_name if isinstance(task_or_name, str) else getattr(task_or_name, "kind", "pois")
    if name not in KINDS:
        raise ValueError(f"unknown output kind {name!r} (known: {', '.join(sorted(KINDS))})")
    if not isinstance(task_or_name, str) and getattr(task_or_name, "requires_model", False) \
            and name != "binned_likelihood":
        raise ValueError(f"{getattr(task_or_name, 'name', task_or_name)}: requires_model is the binned_likelihood "
                         f"kind's MODEL.json gate, but the task's kind is {name!r}")
    return import_module(KINDS[name]).KIND

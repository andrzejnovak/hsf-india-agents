"""RESULT.json contract checks (core part; sbh/kinds/ check each kind's outputs, sbh/hep/ the nuisance log).  Every
check is mechanical; a failure scores the seed as not completed, never interpreted charitably.

    {
      "pois": [ {"name": "mH", "value": f, "stat": f, "syst": f, "total": f}, ... ],
      "significance_obs": f,  "discovery": bool,          # search tasks
      "nuisances": { "<name>": {"value": f, "unc": f, "note": "..."}, ... }
    }

Nuisance names follow sbh/hep/names.py.  An exported MODEL.json must name every NP modifier by that grammar, log
each in RESULT.json, and describe every channel in `_meta.binning`.
"""
from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any, List, Optional, Tuple


POI_FIELDS = ("value", "stat", "syst", "total")


def _finite(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def open_output(path, dir_fd=None):
    """Open (binary) a file the SUBMISSION wrote, with read_output's guards, for streaming readers (MEASUREMENT.npz).
    Raises OSError or ValueError with a participant-readable reason."""
    import errno
    import os
    import stat
    name = os.path.basename(os.fspath(path))
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0),
                     dir_fd=dir_fd)
    except OSError as e:
        if e.errno == errno.ELOOP:
            raise ValueError(f"{name} is a symlink (not followed; write a regular file)") from None
        raise
    fh = os.fdopen(fd, "rb")
    try:
        st = os.fstat(fh.fileno())
        if not stat.S_ISREG(st.st_mode):
            raise ValueError(f"{name} is not a regular file")
        if st.st_nlink > 1:
            raise ValueError(f"{name} is hard-linked ({st.st_nlink} links; write a regular file)")
    except BaseException:
        fh.close()
        raise
    return fh


def read_output(path, dir_fd=None, max_bytes=None) -> bytes:
    """Bytes of a file the SUBMISSION wrote, read only if it is a regular, singly-linked file, never via a symlink.
    The TB grader runs as root over a submission running as nobody: a symlinked RESULT.json would make it read and
    record a root-only file such as the sealed answer key (confused deputy).  O_NONBLOCK: a FIFO cannot hang the
    grader.  `dir_fd`: `path` is a name inside that open directory, so no component is resolved twice.  `max_bytes`:
    size cap, refused before reading.  Raises OSError or ValueError with a participant-readable reason."""
    import os
    name = os.path.basename(os.fspath(path))
    with open_output(path, dir_fd=dir_fd) as fh:
        st = os.fstat(fh.fileno())
        if max_bytes is None:
            return fh.read()
        data = fh.read(max_bytes + 1)            # a file still growing is bounded too
        if max(st.st_size, len(data)) > max_bytes:
            raise ValueError(f"{name} is {max(st.st_size, len(data)) / 1e6:.1f} MB, above the "
                             f"{max_bytes / 1e6:.0f} MB cap")
        return data


def load_output_json(path, max_bytes=None) -> Any:
    """json.loads(read_output(path)): every evaluator read of a submission's JSON output goes through here."""
    import json
    return json.loads(read_output(path, max_bytes=max_bytes))


def contract_version(task) -> Optional[str]:
    """Contract version from the EVAL_CONTRACT.md title ("# EVAL_CONTRACT v0.8 — ..."), or None (no file / no
    version).  Stamped into RunRecord.contract so newer requirements apply only to runs made under them.  The title is
    the first line after leading HTML comments: the TB pack puts the canary comment on line 1."""
    import re
    try:
        text = (task.dir / "EVAL_CONTRACT.md").read_text(encoding="utf-8")
    except (AttributeError, OSError):
        return None
    body = re.sub(r"\A(?:\s*<!--.*?-->)*\s*", "", text, flags=re.S)
    first = body.splitlines()[0] if body else ""
    m = re.match(r"#\s*EVAL_CONTRACT\s+v(\d+(?:\.\d+)*)", first)
    return m.group(1) if m else None


def check_result(result: Any, task=None) -> List[str]:
    from .kinds import get_kind
    kind = get_kind(task if task is not None else "pois")
    if not kind.reports_pois:
        # a kind without POIs (corrections: answers live in its own outputs): only the kind's RESULT.json rules
        return kind.result_problems(result, task)
    errs: List[str] = []
    if not isinstance(result, dict):
        return ["RESULT.json is not a JSON object"]
    pois = result.get("pois")
    if not isinstance(pois, list) or not pois:
        return ["'pois' missing or not a non-empty list"]
    seen = {}
    for i, p in enumerate(pois):
        if not isinstance(p, dict) or "name" not in p:
            errs.append(f"pois[{i}] malformed")
            continue
        seen[p["name"]] = p
        for f in POI_FIELDS:
            if f not in p:
                errs.append(f"poi {p['name']}: missing '{f}'")
            elif not _finite(p[f]):
                errs.append(f"poi {p['name']}: '{f}' is not a finite number")
        if all(f in p and _finite(p[f]) for f in POI_FIELDS):
            if p["total"] <= 0:
                errs.append(f"poi {p['name']}: total uncertainty must be > 0")
            if p["stat"] < 0 or p["syst"] < 0:
                errs.append(f"poi {p['name']}: negative uncertainty")
            q = math.hypot(p["stat"], p["syst"])
            if abs(p["total"] - q) > 0.05 * max(p["total"], q):
                errs.append(f"poi {p['name']}: total inconsistent with stat (+) syst in quadrature")
    if task is not None:
        for name in task.pois:
            if name not in seen:
                errs.append(f"required POI '{name}' not reported")
        if task.result_type == "search":
            if not _finite(result.get("significance_obs")):
                errs.append("'significance_obs' missing or not finite")
            if not isinstance(result.get("discovery"), bool):
                errs.append("'discovery' missing or not a boolean")
    errs += kind.result_problems(result, task)
    return errs


# Prefix of problems that are contract failures (gates), as opposed to fit diagnostics.
CONTRACT_PREFIX = "contract: "


# ------------------------------------------------------------------------------------------- the contract text --
# EVAL_CONTRACT.md is rendered from a template (the unified tasks/EVAL_CONTRACT.in.md, or a task's own) and the
# parts files of core, hep and kinds.  Tokens: {{core:<part>}}, {{hep:<part>}}, {{kind:<part>}} (the task's kind),
# {{kind.<name>:<part>}}, {{value:<name>}} (Task.contract_values(), UNIFIED_VALUES overriding).  Then the task's
# pieces (contract_pieces) select the blocks `<!-- if: a|b -->...<!-- /if -->` (kept when the task has any listed
# piece), the kept `{{sec:<id>}}` headings are numbered in order and `{{ref:<id>}}` becomes "§<n>" (a reference
# to a dropped section is an error).  The rendered file is committed like a lock file; `render --check` (in smoke)
# fails when stale.  No template = hand-written contract.
TEMPLATE = "EVAL_CONTRACT.in.md"
UNIFIED_TEMPLATE = Path(__file__).resolve().parent.parent / "tasks" / TEMPLATE
# Names fixed by the unified contract for every task: signal-strength POI `mu`, analysis nuisances `ana_<label>`.
UNIFIED_VALUES = {"signal_poi": "mu", "nuisance_prefix": "ana"}
_PART_RE = re.compile(r"<!-- part: ([\w-]+) -->\n(.*?)<!-- /part -->", re.S)
_TOKEN_RE = re.compile(r"\{\{(core|hep|kind(?:\.\w+)?|value):([\w-]+)\}\}")
_IF_RE = re.compile(r"<!-- if: ([\w|]+) -->\n?(.*?)<!-- /if -->\n?", re.S)
_SEC_RE = re.compile(r"\{\{sec:([\w-]+)\}\}")
_REF_RE = re.compile(r"\{\{ref:([\w-]+)\}\}")


def contract_pieces(task) -> Tuple[str, ...]:
    """The unified contract's pieces the task receives: Task.contract_pieces, else its kind's."""
    from .kinds import get_kind
    own = getattr(task, "contract_pieces", None)
    return tuple(own) if own is not None else tuple(get_kind(task).contract_pieces)


def compose(text: str, pieces, where: str = "contract") -> str:
    """Keep the `if:` blocks of `pieces`, number the kept {{sec:}} headings, resolve the {{ref:}}s."""
    have = set(pieces)
    rest = _IF_RE.sub("", text)
    if "<!-- if:" in rest or "<!-- /if -->" in rest:
        raise ValueError(f"{where}: an unclosed or nested `<!-- if: -->` block")
    text = _IF_RE.sub(lambda m: m.group(2) if have & set(m.group(1).split("|")) else "", text)
    num = {}

    def sec(m):
        if m.group(1) in num:
            raise ValueError(f"{where}: section {m.group(1)!r} twice")
        num[m.group(1)] = len(num) + 1
        return str(num[m.group(1)])
    text = _SEC_RE.sub(sec, text)

    def ref(m):
        if m.group(1) not in num:
            raise KeyError(f"{where}: a reference to section {m.group(1)!r}, which pieces {sorted(have)} leave out "
                           f"(kept: {', '.join(num)})")
        return f"§{num[m.group(1)]}"
    return _REF_RE.sub(ref, text)


def contract_parts(path) -> dict:
    """{name: text} of a parts file (exact text between each part's markers)."""
    return dict(_PART_RE.findall(Path(path).read_text(encoding="utf-8")))


def template_of(task) -> Optional[Path]:
    """The task's own template, else the unified one if it uses it; None = hand-written contract."""
    own = Path(task.dir) / TEMPLATE
    if own.exists():
        return own
    return UNIFIED_TEMPLATE if getattr(task, "unified_contract", False) else None


def render_contract(task) -> str:
    """The text of a task's EVAL_CONTRACT.md: rendered template, or the hand-written file."""
    from . import ROOT
    from .kinds import get_kind
    tpl = template_of(task)
    if tpl is None:
        return (Path(task.dir) / "EVAL_CONTRACT.md").read_text(encoding="utf-8")
    homes = {"core": ROOT / "sbh" / "contract_parts.md", "hep": ROOT / "sbh" / "hep" / "contract_parts.md",
             "kind": get_kind(task).contract_parts_file()}
    parts = {layer: (contract_parts(path) if path is not None and Path(path).exists() else {})
             for layer, path in homes.items()}
    values = {**task.contract_values(), **(UNIFIED_VALUES if tpl == UNIFIED_TEMPLATE else {})}

    def fill(m):
        layer, name = m.group(1), m.group(2)
        if layer.startswith("kind.") and layer not in parts:
            path = get_kind(layer[len("kind."):]).contract_parts_file()
            parts[layer] = contract_parts(path) if path is not None else {}
        src = values if layer == "value" else parts[layer]
        if name not in src:
            raise KeyError(f"{tpl}: no {layer} {name!r} (known: {', '.join(sorted(src))})")
        return str(src[name])
    text = tpl.read_text(encoding="utf-8")
    for _ in range(3):                    # parts may carry value placeholders: fill until none is left
        text, n = _TOKEN_RE.subn(fill, text)
        if not n:
            break
    return compose(text, contract_pieces(task), where=str(tpl))


def main(argv=None) -> int:
    """`python -m sbh.contract render [--task NAME ...] [--check]`: write (or, with --check, compare) every
    templated task's EVAL_CONTRACT.md."""
    import argparse
    import sys
    from . import ROOT
    from .task import load_task
    ap = argparse.ArgumentParser(prog="python -m sbh.contract")
    sp = ap.add_subparsers(dest="cmd", required=True)
    r = sp.add_parser("render", help="render tasks/<task>/EVAL_CONTRACT.md from its template (the unified "
                                     "tasks/EVAL_CONTRACT.in.md or its own EVAL_CONTRACT.in.md) and the parts")
    r.add_argument("--task", action="append", help="a task name (default: every task with a template)")
    r.add_argument("--check", action="store_true", help="only compare: nonzero exit when a rendered file is stale")
    a = ap.parse_args(argv)
    tasks = [load_task(n) for n in (a.task or sorted(p.parent.name for p in (ROOT / "tasks").glob("*/__init__.py")))]
    stale = []
    for task in (t for t in tasks if template_of(t) is not None):
        name = task.name
        text = render_contract(task)
        out = Path(task.dir) / "EVAL_CONTRACT.md"
        if out.exists() and out.read_text(encoding="utf-8") == text:
            print(f"{name}: EVAL_CONTRACT.md current")
            continue
        if a.check:
            stale.append(name)
            print(f"{name}: EVAL_CONTRACT.md STALE (run `pixi run contracts`)", file=sys.stderr)
        else:
            out.write_text(text, encoding="utf-8")
            print(f"{name}: EVAL_CONTRACT.md rendered")
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())

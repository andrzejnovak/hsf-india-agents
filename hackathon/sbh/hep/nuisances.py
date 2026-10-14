"""The RESULT.json nuisance log (EVAL_CONTRACT section 4): entry format, names, and declared working points."""
from __future__ import annotations

from typing import Any, List, Optional

from ..contract import CONTRACT_PREFIX, _finite
from . import names as NN


def check_nuisance_log(result: dict, task=None) -> List[str]:
    """Gate: {"value": finite, "unc": finite >= 0, "note": str (optional)} entries under names that parse."""
    log = result.get("nuisances")
    if log is None:
        return []
    if not isinstance(log, dict):
        return ["'nuisances' must be an object"]
    errs = []
    prefix = getattr(task, "nuisance_prefix", "") if task is not None else ""
    for k, e in log.items():
        if not (isinstance(e, dict) and _finite(e.get("value")) and _finite(e.get("unc")) and e["unc"] >= 0
                and isinstance(e.get("note", ""), str)):
            errs.append(f"nuisances.{k}: needs finite 'value', non-negative 'unc' and an optional string 'note'")
    bad = NN.unparsed(log, prefix)
    if bad:
        errs.append(CONTRACT_PREFIX + "nuisance names outside the naming grammar: " + ", ".join(bad[:8])
                    + (" …" if len(bad) > 8 else ""))
    # a part (<name>__<label>) or an efficiency step needs its whole effect logged too
    wholes = set()
    for k in log:
        n = NN.parse(k, prefix)
        if n is not None:
            wholes |= {n.base, NN.effect(k, prefix)}
    whole = sorted(wholes - set(log))
    if whole:
        errs.append(CONTRACT_PREFIX + "nuisances logged in parts or steps without the whole effect: "
                    + ", ".join(whole[:8]) + (" …" if len(whole) > 8 else ""))
    return errs


def _wp_keys(name: str) -> set:
    """Accepted spellings of a working point: case and spaces ignored, collection prefix optional
    ("Muon_mediumId" matches "muon_mediumid" and "mediumId")."""
    k = "".join(str(name).split()).lower()
    return {k, k.split("_", 1)[1]} if "_" in k else {k}


def declared_working_points(log: Any, working_points: Optional[dict]) -> dict:
    """{object: accepted working point} from the "wp" field of each eff_<obj> entry, matched against
    ``working_points`` ({object: accepted names, default first}).  Absent/null "wp" gives the default; an unknown one
    gives None, which the scorer reads as not logged."""
    out = {}
    log = log if isinstance(log, dict) else {}
    for obj, names in (working_points or {}).items():
        names = tuple(names or ())
        if not names:
            continue
        entry = log.get(f"eff_{obj}")
        wp = entry.get("wp") if isinstance(entry, dict) else None
        if wp is None:
            out[obj] = names[0]
        elif isinstance(wp, str) and wp.strip():
            key = "".join(wp.split()).lower()
            out[obj] = next((n for n in names if key in _wp_keys(n)), None)
        else:
            out[obj] = None
    return out


def working_point_problems(result: Any, task=None) -> List[str]:
    """`sbh check` warning (not a gate): eff_<obj> entries whose "wp" the task does not accept."""
    wps = getattr(task, "working_points", None) if task is not None else None
    log = result.get("nuisances") if isinstance(result, dict) else None
    out = []
    for obj, wp in declared_working_points(log, wps).items():
        if wp is None:
            got = log[f"eff_{obj}"].get("wp")
            out.append(f"nuisances.eff_{obj}: \"wp\" {got!r} is not one of the identification working points accepted "
                       f"for this object ({', '.join(wps[obj])}; EVAL_CONTRACT section 4); the evaluation reads this "
                       "entry as not logged")
    return out

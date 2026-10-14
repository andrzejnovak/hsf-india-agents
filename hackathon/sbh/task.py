"""The task interface: the physics-specific part of a benchmark.

A task says how to draw a sealed truth from a prior, how to generate a dataset from it, which RESULT.json entries are
POIs, which logged nuisances it scores, and its participant-facing documents.  Freezing, execution, isolation,
scoring and packaging are shared.  Tasks live in tasks/<name>/__init__.py and expose a module-level ``TASK``.
"""
from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parent.parent


class Task:
    name: str = "base"
    # The output kind (sbh/kinds/): what a run returns per dataset and how it is checked and scored.
    kind: str = "pois"
    pois: List[str] = []                 # RESULT.json POI names == truth keys
    # The signal-strength POI (0 on a search's null datasets: discovery, FDR, model refits); None = none.
    signal_strength_poi: Optional[str] = None
    # Truth key whose datasets share a draw: the scorer's standard-error cluster; None = each dataset its own.
    cluster_key: Optional[str] = "profile"
    result_type: str = "search"          # "search" | "measurement"
    requires_model: bool = False         # MODEL.json must exist and build as a pyhf workspace (GATE)
    # Contract version from which EVENTS.json (events behind MODEL.json's observed counts) is required; None = never.
    event_list_from: Optional[str] = None
    run_timeout_s: int = 600             # per-run wall clock budget (single source; CLI --timeout overrides)
    run_memory_mb: int = 6144            # RLIMIT_AS per run; 0 = none
    worker_memory_mb: int = 0            # per-dataset RESIDENT memory cap [MB], enforced by the eval's cgroup;
                                         # the runner only measures against it.  0 = not stated.
    run_cpus: int = 0                    # CPUs per run (single source; TB resources must match); 0 = host's.
    # Analysis-specific nuisance names are <nuisance_prefix>_<label> (sbh/hep/names.py).
    nuisance_prefix: str = ""
    # Pixi environment for a submission that ships no pixi.toml: .pixi/envs/<name>.
    base_env: str = "agentbase"
    # True = render the unified tasks/EVAL_CONTRACT.in.md with contract_values; False = the task's own template or
    # hand-written EVAL_CONTRACT.md (sbh.contract.render_contract).
    unified_contract: bool = False
    # The unified contract's pieces this task receives (the template's `<!-- if: <piece> -->` blocks); None = its
    # kind's (Kind.contract_pieces).  A task that composes others lists them all.
    contract_pieces: Optional[Tuple[str, ...]] = None
    # Entries `sbh stress` runs without --only (None: all not naming another task); `sbh pack`'s stub example.
    stress_submissions: Optional[Tuple[str, ...]] = None
    example_submission: str = "attacker_constant"
    # Attackers generated from the reference at stress time (sbh/attackgen.py): {entry: (family, run.sh flags,
    # description)}, family one of the kind's attack_families (or a core one).  An entry outside stress_submissions
    # is a review case (review_note says why).
    attackers: Dict[str, Tuple[str, str, str]] = {}
    # Hand-written attackers (tasks/<t>/attackers/, or another task's): {entry: family}.
    hand_attackers: Dict[str, str] = {}
    # Families of the kind this task neither generates nor hand-writes: {family: why}.
    attack_waivers: Dict[str, str] = {}
    review_note: str = ""

    def report_page(self) -> Dict[str, Any]:
        """The results page's facts about this task (scripts/report/collect_report_data.py -> v1.page):
          title, heading, lede   page name (plain), h1 and the paragraph under it (HTML),
          briefing_note          note beside the participant texts' commit,
          profiles               {profile: {column: value}} the datasets tab's detector-profile table,
          cases                  {POI: {name, symbol (HTML), text, unit, digits, unscored}} the run pages' names of a
                                 POI, its unit, the decimals of a value (the response axes one fewer) and why a
                                 dataset's case may go unscored; a POI not listed shows its key, no unit, 2 decimals,
        and for a function-output task
          datasets, seeds_intro  scoreboard dataset line and datasets-tab intro (HTML),
          labels                 {key: display name} for case groups, roles, flavours, score terms, curve variables,
          glossary               {key: hover text} added to or replacing glossary entries,
          tiers                  {"p0", "p1", "p2": what each prompt tier hands over}."""
        return {"title": f"Slopbench {self.name}", "heading": f"Slopbench {self.name}", "lede": ""}

    def report_truth(self, truth: Dict[str, Any]) -> Dict[str, Any]:
        """Per-dataset truth fields shown on the (evaluator-only) results page: the POIs and the profile."""
        return {**{p: truth.get(p) for p in self.pois}, "profile": truth.get("profile")}

    def quick_checks(self) -> List[Tuple[str, bool, str]]:
        """Fast task consistency checks run in smoke (checks/task_checks.py): [(check, passed, detail)]."""
        return []

    # POI -> (center, width): ignorance forecast from PARTICIPANT knowledge only (prompt envelope / shipped priors,
    # never the sealed design).  Evaluator-side scoring input.
    fallback_forecast: Dict[str, tuple] = {}
    # Evaluator-side scoring inputs; empty = the term is off.
    calibration_scored: Dict[str, Dict[str, float]] = {}
    # The measurement's usual nuisances, each unit satisfied by any of its names.  Units the calibration term
    # value-scores are scored there; Delta_syst covers the rest (sbh.score.syst_units).
    completeness_units: List[Tuple[str, Tuple[str, ...]]] = []
    # Magnitude floors of the nuisance probes (sbh.score.nuisance_probes); an effect below its floor covers nothing.
    # "norm": relative yield change (normsys max|hi - 1|, |lo - 1|; histosys sum|x - nominal| / sum(nominal); lumi
    # its relative width), every effect but scale and resolution; "shape": total-variation distance of the
    # unit-normalised histosys shapes, for scale and resolution.  Parts on one sample add in quadrature.  Empty = none.
    nuisance_floors: Dict[str, float] = {}
    # Delta_cal aggregation over value-scored effects (sbh.score._cal_aggregate): "meanmax" ((mean + max) / 2,
    # scored), "mean" or "sum"; all three are reported.  None = sbh.score.CAL_AGGREGATE.
    cal_aggregate: Optional[str] = None
    # Standard background processes (sbh.score.background_processes; REPORT-ONLY flag, never a score input):
    # [(label, patterns)], each a regex searched in the sample name lower-cased to letters and digits.
    # _merged: [((labels, ...), patterns)] for a sample carrying several processes (tried only if no single match);
    # _signal: names never counted as background; _min_share: below this share of nominal background = missing.
    standard_backgrounds: List[Tuple[str, Tuple[str, ...]]] = []
    standard_background_merged: List[Tuple[Tuple[str, ...], Tuple[str, ...]]] = []
    standard_background_signal: Tuple[str, ...] = ()
    standard_background_min_share: float = 0.0

    # Working points a submission may name in an eff_<obj> log entry ("wp"): {object: names, default first}.
    # NAMES only (shipped in the participant stub); their truth meaning stays evaluator-side.
    working_points: Dict[str, Tuple[str, ...]] = {}

    def calibration_truth(self, truth: Dict[str, Any], log: Optional[dict] = None) -> Dict[str, float]:
        """Injected value of every effect, by logged nuisance name.  ``log``: the dataset's nuisance log, for a task
        whose truth follows declared working points; None = defaults."""
        return {k: float(truth[k]) for k in self.calibration_scored if k in truth}

    def calibration_spec(self, log: Optional[dict] = None) -> Dict[str, Dict[str, float]]:
        """Value-scored effects ({name: nominal, target, prior}) for one nuisance log; calibration_scored unless the
        truth follows a declared working point."""
        return self.calibration_scored

    # ---- calibration response and compute (diagnostics) --
    # Detector effects are drawn independently of the POIs, so each POI residual is regressed on what an
    # UNcalibrated analysis would show: {poi: {effect: f(truth) -> residual}}.  Leakage k = 0 calibrated, 1 not.
    def leakage_probes(self) -> Dict[str, Dict[str, Any]]:
        return {}

    # Calibration effect whose injected value should scale MODEL.json's signal yield at POI = 1 (None: not probed).
    yield_response_effect: Optional[str] = None

    def event_level_truth(self, truth: Dict[str, Any]) -> Dict[str, float]:
        """One number per effect for the event-level regressions; per-object effects are combined here."""
        return self.calibration_truth(truth)

    # Reference wall seconds per evaluation dataset on the task's worker shape: the compute yardstick.
    # Delta_compute rewards faster and charges slower, up to run_timeout_s.  None: compute reported, not charged.
    compute_reference_wall_s: Optional[float] = None
    # Opt-in: time the reference on the public dataset in every evaluation (sbh/yardstick.py) and use Y x k as the
    # reference wall, k = sealed/public wall ratio measured once.  A failed measurement leaves no compute term.
    compute_yardstick_k: Optional[float] = None
    # Compute bonus gate (sbh/score.py compute_gate): full speed reward while the rest of Delta_total <= rest0,
    # fading linearly to zero at rest0 + width; the slowness charge is never gated.  None = V3_COMP_GATE_REST0 (0),
    # V3_COMP_GATE_WIDTH (0.05).  The TB verifier sets both.
    compute_gate_rest0: Optional[float] = None
    compute_gate_width: Optional[float] = None
    # Opt-in: the headline's exponent (sbh/score.py score_gamma); None: the scorer's.
    score_gamma: Optional[float] = None
    # Set per evaluation by the TB verifier (sbh.tbgrade.tb_score), never by a task.
    compute_yardstick: Optional[Dict[str, Any]] = None
    compute_gate_source: Optional[str] = None
    grader_strict: bool = False

    # ---- binned_likelihood kind (sbh/kinds/binned_likelihood/) ---------------
    # Score-from-fit: {POI: "fit" | "grid"}: score the evaluator's refit of the declared model or the declared grid;
    # empty = score the reported values.
    model_poi_sources: Dict[str, str] = {}
    # Range a "grid" POI's interval is evaluated in (e.g. (110, 140) GeV); None = the grid's own span.
    mass_range: Optional[Tuple[float, float]] = None
    # Calibration credit withdrawn where the model shows it is not applied (sbh.score.calibration_gate):
    # {effect: (check, probe)}, check "leakage" with a probe name or "yield" with None.
    calibration_gates: Dict[str, Tuple[str, Optional[str]]] = {}
    # Opt-in: cap model verification per dataset at twice the reference's slowest (recorded in closure.json); a
    # dataset over the cap fails verification.  False: only the job's time limit.
    model_verify_cap: bool = False

    # ---- priors and truths -------------------------------------------------
    def default_priors(self) -> Dict[str, Any]:
        raise NotImplementedError

    def priors_without_response(self, priors: Dict[str, Any]) -> Dict[str, Any]:
        """Priors with optional dataset variations switched off."""
        return dict(priors)

    def public_truth(self, priors: Dict[str, Any]) -> Dict[str, Any]:
        """The disclosed truth of the public development seed (seed_000)."""
        raise NotImplementedError

    def draw_truth(self, rng: np.random.Generator, priors: Dict[str, Any],
                   fixed: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """One sealed truth drawn from the prior, ``fixed`` entries (e.g. {"mH": 120}) overriding."""
        raise NotImplementedError

    # ---- data --------------------------------------------------------------
    def generate(self, truth: Dict[str, Any], rng: np.random.Generator,
                 dataset_dir: Path) -> None:
        """Write a dataset directory for this truth: NO truth information, same layout for every seed."""
        raise NotImplementedError

    # ---- scoring hooks -----------------------------------------------------
    def poi_applicable(self, poi: str, truth: Dict[str, Any]) -> bool:
        """Whether a POI is scorable on this seed (e.g. no mass without injected signal)."""
        return True

    def poi_scored_v2(self, poi: str, truth: Dict[str, Any]) -> bool:
        """(seed, POI) cases in the v2 log-score; tasks may widen applicability (e.g. mu on null seeds)."""
        return self.poi_applicable(poi, truth)

    # ---- files -------------------------------------------------------------
    # A variant of another task names it here: the files this task's directory lacks (DATASET.md, PROMPT.md,
    # prompts/, RUNTIME.md, reference/) are that task's.
    shares: Optional[str] = None

    @property
    def dir(self) -> Path:
        return ROOT / "tasks" / self.name

    def path(self, rel: str) -> Path:
        """tasks/<task>/<rel>, else the shared task's copy (`shares`)."""
        own = self.dir / rel
        return ROOT / "tasks" / self.shares / rel if self.shares and not own.exists() else own

    @property
    def reference_submission(self) -> Path:
        return self.path("reference")

    # The run label of the reference when `sbh stress` or `sbh eval` scores it as a submission (the closure's run is
    # always `reference`); stored campaigns carry it.
    reference_label: str = "reference"

    # Further reference analyses (opt-in): {label: {"name": page name, "budget": {...}, "note": ...}},
    # tasks/<task>/alt_references/<label> evaluated like any run and shown beside the task's reference, which stays
    # the yardstick (sigma_ref).  "budget" (optional, OWN_BUDGET_KEYS): its own larger run limits; its compute term is
    # then neutral and shown scaled to the task's CPUs.  evaluator_budget_x scales the evaluator's per-dataset checking
    # budgets.  "note" (optional): what the results page says beside it.
    further_references: Dict[str, Dict[str, Any]] = {}
    OWN_BUDGET_KEYS = {"run_cpus": int, "worker_memory_mb": int, "run_timeout_s": int, "run_memory_mb": int,
                       "evaluator_budget_x": float}

    def further_reference_names(self) -> Dict[str, str]:
        """{label: page name} of the further references; ValueError names a malformed entry."""
        out = {}
        for label, entry in self.further_references.items():
            if not isinstance(entry, dict) or not isinstance(entry.get("name"), str) or not entry["name"]:
                raise ValueError(f"{self.name}: further reference {label!r} is not {{'name': <page name>, "
                                 f"'budget': {{...}} (optional), 'note': '...' (optional)}}: {entry!r}")
            unknown = set(entry) - {"name", "budget", "note"}
            if unknown:
                raise ValueError(f"{self.name}: further reference {label!r} has unknown keys {sorted(unknown)}")
            if not isinstance(entry.get("note", ""), str):
                raise ValueError(f"{self.name}: further reference {label!r}'s note is not a string")
            self.own_budget(label)
            out[label] = entry["name"]
        return out

    def own_budget(self, label: Optional[str]) -> Dict[str, Any]:
        """A further reference's own budget; empty for every other label (task budgets apply)."""
        entry = self.further_references.get(label) if label is not None else None
        if entry is not None and not isinstance(entry, dict):
            raise ValueError(f"{self.name}: further reference {label!r} is not a dict: {entry!r}")
        own = (entry or {}).get("budget") or {}
        unknown = set(own) - set(self.OWN_BUDGET_KEYS)
        if unknown:
            raise ValueError(f"{self.name}: the budget of further reference {label} names unknown limits "
                             f"{sorted(unknown)}")
        return {k: self.OWN_BUDGET_KEYS[k](v) for k, v in own.items()}

    def docs(self) -> List[Path]:
        names = ("DATASET.md", "EVAL_CONTRACT.md", "PROMPT.md")
        return [self.path(n) for n in names if self.path(n).exists()]

    def prompt(self) -> str:
        return self.path("PROMPT.md").read_text()

    def extra_terms(self, run_dir: Path, records: List[dict], truths: Dict[str, dict], inputs: dict) -> list:
        """Task-specific weighted S_v3 terms after its kind's: [(name, weight, {"delta", "se", ...} or None)]."""
        return []

    def contract_values(self) -> Dict[str, str]:
        """The {{value:<name>}} placeholders of the task's contract (sbh.contract.render_contract): budgets, nuisance
        prefix, signal POI, RUNTIME.md additions (one paragraph), observable, and optional kind-specific paragraphs
        (datasets_note, selfcheck_note, measurement_budget, correction_population, measurement_opening,
        model_verify_budget).  Tasks extend the dict."""
        import textwrap

        def gib(mb):
            return f"{mb / 1024:g}"

        def article(n: int) -> str:
            # "an" for numbers read with a vowel sound: 8.., 11 / 18 (and their thousands)
            s = str(int(n))
            return "an" if s.startswith("8") or (s[:2] in ("11", "18") and len(s) in (2, 4, 5)) else "a"
        extra = self.path("RUNTIME.md")
        runtime = extra.read_text(encoding="utf-8").strip() if extra.exists() else ""
        if "\n\n" in runtime:
            raise ValueError(f"{extra}: the runtime part sits inside one paragraph (no blank line)")
        # ends the binned_likelihood kind's "measured" contract part
        cap = ("The evaluator checks each dataset's declared model within a wall-clock budget of twice the longest "
               "time the same checks take on the reference analysis's own models: a model not checked within it "
               "counts as failed on that dataset.") if self.model_verify_cap else ""
        return {"cpus": str(self.run_cpus), "memory_gib": gib(self.worker_memory_mb), "wall_s": str(self.run_timeout_s),
                "wall_article": article(self.run_timeout_s), "nuisance_prefix": self.nuisance_prefix,
                "signal_poi": str(self.signal_strength_poi or ""), "runtime": f"  {runtime}" if runtime else "",
                "observable": "the observable", "datasets_note": "", "selfcheck_note": "", "measurement_budget": "",
                "correction_population": "",
                # required-declaration variant; CorrectionsTask overrides where optional
                "measurement_opening": "{{kind.corrections:measurement_required}}",
                "model_verify_budget": "\n" + textwrap.fill(cap, 75) + "\n" if cap else ""}

    def ship_fixup(self, root: Path) -> int:
        """Update the dataset copies under a pack's `root` to current shipping rules (suites built earlier); never
        the suite itself.  Returns the number of files changed; default none."""
        return 0




# Task names a suite manifest or run record may carry for a task that has another name now: {stored: current}.
# h4l_ntuple suites were built from the inputs h4l_tbs pins.
RENAMED_TASKS = {"h4l_ntuple": "h4l_tbs"}


def current_name(name: str) -> str:
    return RENAMED_TASKS.get(name, name)


def load_task(name: str) -> Task:
    mod = importlib.import_module(f"tasks.{current_name(name)}")
    return mod.TASK


def tbs_toml(task_name: str) -> Path:
    """tasks/<task>/tbs/tbs.toml: the task's Terminal-Bench-Science variant (may not exist)."""
    return ROOT / "tasks" / current_name(task_name) / "tbs" / "tbs.toml"


PARTICIPANT_TASK_STUB = '''"""Participant-side task metadata: exactly what `sbh check` needs.

The evaluator's full task module (generation, priors, injected-truth
machinery) is not part of the bundle.
"""
from sbh.task import Task


class _ParticipantTask(Task):
    name = {name!r}
    kind = {kind!r}
    pois = {pois!r}
    result_type = {result_type!r}
    requires_model = {requires_model!r}
    event_list_from = {event_list_from!r}
    nuisance_prefix = {nuisance_prefix!r}
    run_timeout_s = {run_timeout_s!r}
    run_memory_mb = {run_memory_mb!r}
    worker_memory_mb = {worker_memory_mb!r}
    run_cpus = {run_cpus!r}
    working_points = {working_points!r}
{extras}

TASK = _ParticipantTask()
'''


def write_participant_task_stub(task: Task, pkg_dir: Path, **limits) -> None:
    """Write a minimal tasks/<name>/ package for participant bundles: contract metadata only, never the
    generator, priors, yield constants or response profiles.  `limits` overrides run budgets where the evaluation
    differs from the task's (e.g. the TB verifier), so `sbh check` measures against what is actually applied."""
    unknown = set(limits) - {"run_memory_mb", "worker_memory_mb", "run_timeout_s"}
    if unknown:
        raise TypeError(f"write_participant_task_stub: unknown limit override(s) {sorted(unknown)}")
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "__init__.py").write_text(PARTICIPANT_TASK_STUB.format(
        name=task.name, kind=str(getattr(task, "kind", "pois")), pois=list(task.pois),
        result_type=task.result_type,
        requires_model=bool(getattr(task, "requires_model", False)),
        event_list_from=getattr(task, "event_list_from", None),
        nuisance_prefix=str(getattr(task, "nuisance_prefix", "")),
        run_timeout_s=int(limits.get("run_timeout_s", getattr(task, "run_timeout_s", 600))),
        run_memory_mb=int(limits.get("run_memory_mb", getattr(task, "run_memory_mb", 6144))),
        worker_memory_mb=int(limits.get("worker_memory_mb", getattr(task, "worker_memory_mb", 0))),
        run_cpus=int(getattr(task, "run_cpus", 0)),
        working_points={str(o): tuple(str(n) for n in ns) for o, ns in (getattr(task, "working_points", None)
                                                                         or {}).items()},
        extras=_stub_extras(task)))


def _stub_extras(task: Task) -> str:
    """Stub lines for non-default base_env and measurement_required (none for h4l/gauss_peak: stubs byte-identical)."""
    lines = []
    if getattr(task, "base_env", Task.base_env) != Task.base_env:
        lines.append(f"    base_env = {task.base_env!r}")
    if getattr(task, "measurement_required", True) is False:
        lines.append("    measurement_required = False")
    return "".join(line + "\n" for line in lines)

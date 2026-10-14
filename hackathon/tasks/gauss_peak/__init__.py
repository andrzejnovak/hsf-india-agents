"""Participant-side task metadata: exactly what `sbh check` needs.

The evaluator's full task module (generation, priors, injected-truth
machinery) is not part of the bundle.
"""
from sbh.task import Task


class _ParticipantTask(Task):
    name = 'gauss_peak'
    kind = 'pois'
    pois = ['mH', 'mu']
    result_type = 'search'
    requires_model = False
    event_list_from = None
    nuisance_prefix = 'gauss'
    run_timeout_s = 600
    run_memory_mb = 6144
    worker_memory_mb = 0
    run_cpus = 0
    working_points = {}


TASK = _ParticipantTask()

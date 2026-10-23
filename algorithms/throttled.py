"""
algorithms/throttled.py — Least-Loaded Dynamic Load Balancing Algorithm (Existing Variant).

Historical Context & Academic Note:
  In earlier versions of this project, this algorithm was labeled "Throttled (Dynamic)".
  Following an academic correctness audit, it is noted that this implementation does
  NOT implement the traditional availability-table, first-available Throttled algorithm
  (as originally formulated in CloudAnalyst / CloudSim by Wickremasinghe et al., 2010).

  Instead, this algorithm implements a greedy Least-Loaded (minimum current load)
  dynamic scheduling policy:
    - For each incoming task, the scheduler inspects the current workload/backlog across
      all available (non-failed) VMs at the task's arrival time.
    - It assigns the task to the available VM with the lowest pending completion timestamp:
        vm = min(available_vms, key=lambda v: (max(t_arr, vm_busy_until[v.vm_id]), v.current_load, v.vm_id))
    - When all tasks arrive at t=0 (batch arrival), this simplifies to:
        vm = min(available_vms, key=lambda v: (v.current_load, v.vm_id))
      which strictly preserves the original batch scheduling behavior.

  To maintain compatibility with existing tests and internal callers, the module
  and function names (`run_throttled`, `validate_throttled`) are preserved, while
  user-facing labels and descriptions identify it as:
  "Least-Loaded Dynamic (Existing Variant)".

Contrast with Round Robin (Static):
  - Round Robin uses  vm = vms[index % n]  — cyclic, no load inspection.
  - Least-Loaded uses minimum load/backlog inspection at each arrival decision.
"""

from typing import List, Dict, Any
from simulation.vm   import VM,   STATUS_BUSY, STATUS_FAILED
from simulation.task import Task, STATUS_COMPLETED


# ── Algorithm identifiers (Primary label & backward compatibility alias) ──────
ALGORITHM_NAME        = "Least-Loaded Dynamic (Existing Variant)"
LEGACY_ALGORITHM_NAME = "Throttled (Dynamic)"


def run_throttled(
    vms             : List[VM],
    tasks           : List[Task],
    processing_rate : float = 1.0,
) -> Dict[str, Any]:
    """
    Execute Least-Loaded dynamic load balancing under the shared discrete-event simulation contract.

    For every task at arrival time t_arr:
      1. Scan available (non-failed) VMs.
      2. Select the VM with the lowest pending workload / earliest completion time.
         Ties are broken by current_load and then VM ID for determinism.
      3. Assign the task to that VM.
      4. Update the VM's busy time, current_load, and task list immediately so the
         next task decision reflects the updated state.
      5. Mark the task as Completed with exact start, completion, wait, and turnaround times.

    Parameters
    ----------
    vms             : List[VM]   — All VMs in the cluster (from SimulationEngine.vms)
    tasks           : List[Task] — All tasks to process (from SimulationEngine.tasks)
    processing_rate : float      — Simulated processing units per time unit (default: 1.0).

    Returns
    -------
    dict with keys:
      "algorithm"            : str
      "legacy_algorithm"     : str
      "total_tasks"          : int
      "total_vms"            : int
      "assignment_log"       : list
      "vm_task_counts"       : dict
      "vm_total_loads"       : dict
      "makespan"             : float
      "average_waiting_time" : float
      "maximum_waiting_time" : float
      "average_response_time": float
      "maximum_response_time": float
      "queued_task_count"    : int
      "metrics"              : PerformanceMetrics

    Raises
    ------
    ValueError — if VM list is empty or all VMs are unavailable/failed
    """
    if not vms:
        raise ValueError("Throttled: VM list is empty — cannot assign tasks.")

    available_vms: List[VM] = [v for v in vms if v.available and v.status != STATUS_FAILED]
    if not available_vms:
        raise ValueError(
            "Throttled: No available VMs — all VMs are failed or marked unavailable."
        )

    assignment_log: List[Dict[str, Any]] = []

    # Track simulated completion timestamp per VM (local queue busy time)
    vm_busy_until: Dict[int, float] = {}
    for v in available_vms:
        prior_busy = float(v.current_load) / float(processing_rate) if v.current_load > 0 else 0.0
        vm_busy_until[v.vm_id] = prior_busy

    for task in tasks:
        t_arr = getattr(task, "arrival_time", 0.0) or 0.0
        service_time = max(0.1, float(task.processing_req) / float(processing_rate))

        # ── Re-read VM state table at each task ───────────────────────────────
        # When all tasks arrive at t=0, max(0, busy_until) is strictly proportional
        # to v.current_load, preserving exact greedy minimum load selection.
        target_vm: VM = min(
            available_vms,
            key=lambda v: (max(t_arr, vm_busy_until[v.vm_id]), v.current_load, v.vm_id)
        )

        load_snapshot = {v.name: v.current_load for v in available_vms}

        start_time = max(t_arr, vm_busy_until[target_vm.vm_id])
        comp_time = start_time + service_time
        waiting_time = max(0.0, start_time - t_arr)
        response_time = comp_time - t_arr

        # ── Update Task ───────────────────────────────────────────────────────
        task.assigned_vm_id = target_vm.vm_id
        task.status         = STATUS_COMPLETED
        task.arrival_time   = t_arr
        task.start_time     = start_time
        task.completion_time= comp_time
        task.waiting_time   = waiting_time
        task.response_time  = response_time

        # ── Update VM ─────────────────────────────────────────────────────────
        target_vm.task_ids.append(task.task_id)
        target_vm.current_load += task.processing_req
        target_vm.status = STATUS_BUSY
        vm_busy_until[target_vm.vm_id] = comp_time

        # ── Log entry ─────────────────────────────────────────────────────────
        assignment_log.append({
            "task_id"           : task.task_id,
            "task_name"         : task.name,
            "processing_req"    : task.processing_req,
            "vm_id"             : target_vm.vm_id,
            "vm_name"           : target_vm.name,
            "loads_before"      : load_snapshot,
            "chosen_load_before": load_snapshot[target_vm.name],
            "arrival_time"      : t_arr,
            "start_time"        : start_time,
            "completion_time"   : comp_time,
            "waiting_time"      : waiting_time,
            "response_time"     : response_time,
        })

    # ── Build summary dicts and metrics ───────────────────────────────────────
    vm_task_counts = {v.name: v.task_count   for v in available_vms}
    vm_total_loads = {v.name: v.current_load for v in available_vms}

    from simulation.metrics import compute_metrics
    metrics = compute_metrics(vms=available_vms, tasks=tasks, algorithm=ALGORITHM_NAME)

    return {
        "algorithm"            : ALGORITHM_NAME,
        "legacy_algorithm"     : LEGACY_ALGORITHM_NAME,
        "total_tasks"          : len(tasks),
        "total_vms"            : len(available_vms),
        "assignment_log"       : assignment_log,
        "vm_task_counts"       : vm_task_counts,
        "vm_total_loads"       : vm_total_loads,
        "makespan"             : metrics.makespan,
        "average_waiting_time" : metrics.average_waiting_time,
        "maximum_waiting_time" : metrics.maximum_waiting_time,
        "average_response_time": metrics.average_response_time,
        "maximum_response_time": metrics.maximum_response_time,
        "queued_task_count"    : metrics.queued_task_count,
        "metrics"              : metrics,
    }


def validate_throttled(vms: List[VM], tasks: List[Task]) -> List[str]:
    """
    Validate that Throttled was applied correctly.

    Checks:
      1. Every task has been assigned (no unassigned tasks).
      2. Total VM task counts equal total tasks.
      3. No failed/unavailable VM received a task.
      4. Timing consistency (start >= arrival, response == wait + service).

    Returns a list of error strings (empty list = all checks passed).
    """
    errors: List[str] = []

    # Check 1: all tasks assigned
    unassigned = [t for t in tasks if t.assigned_vm_id is None]
    if unassigned:
        errors.append(f"Check 1 FAIL: {len(unassigned)} tasks are unassigned.")

    # Check 2: VM task count sum equals total tasks
    total_counted = sum(v.task_count for v in vms)
    if total_counted != len(tasks):
        errors.append(
            f"Check 2 FAIL: VM task counts sum to {total_counted}, "
            f"expected {len(tasks)}."
        )

    # Check 3: no unavailable VM received a task
    unavailable_ids = {v.vm_id for v in vms if not v.available or v.status == STATUS_FAILED}
    bad_assignments = [
        t for t in tasks
        if t.assigned_vm_id in unavailable_ids
    ]
    if bad_assignments:
        errors.append(
            f"Check 3 FAIL: {len(bad_assignments)} tasks assigned to "
            f"unavailable/failed VMs."
        )

    # Check 4: timing consistency
    for t in tasks:
        if t.start_time is not None and t.completion_time is not None:
            if t.start_time < t.arrival_time:
                errors.append(
                    f"Check 4 FAIL: Task {t.name} start_time ({t.start_time}) < arrival_time ({t.arrival_time})."
                )
                break
            expected_resp = t.completion_time - t.arrival_time
            if abs(t.response_time - expected_resp) > 1e-4:
                errors.append(
                    f"Check 4 FAIL: Task {t.name} response_time ({t.response_time}) != "
                    f"completion - arrival ({expected_resp})."
                )
                break

    return errors

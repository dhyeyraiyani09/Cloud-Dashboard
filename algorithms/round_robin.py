"""
algorithms/round_robin.py — Static Round Robin Load Balancing Algorithm.

Round Robin (Static):
  Tasks are assigned to VMs in a fixed cyclic order regardless of the
  current load on each VM.  The scheduler simply keeps a pointer to the
  next VM and advances it modulo the VM count for every task.

  This is a STATIC algorithm because the assignment decision is made
  purely from the VM index and does not inspect workload at runtime.

  Assignment example (4 VMs, 8 tasks):
    T-1 → VM-1, T-2 → VM-2, T-3 → VM-3, T-4 → VM-4
    T-5 → VM-1, T-6 → VM-2, T-7 → VM-3, T-8 → VM-4

Shared Simulation Contract (Phase 12.1):
  - Models distributed per-VM FIFO queues.
  - When task arrivals are staggered, tasks wait in the assigned VM's local queue
    until that VM completes all preceding work.
  - Produces consistent timing records (start_time, completion_time, waiting_time, response_time)
    evaluated under the exact same metric definitions as dynamic algorithms.
"""

from typing import List, Dict, Any
from simulation.vm   import VM,   STATUS_BUSY, STATUS_FAILED
from simulation.task import Task, STATUS_COMPLETED


# ── Algorithm identifier (used by the engine dispatcher) ─────────────────────
ALGORITHM_NAME = "Round Robin (Static)"


def run_round_robin(
    vms             : List[VM],
    tasks           : List[Task],
    start_index     : int   = 0,
    processing_rate : float = 1.0,
) -> Dict[str, Any]:
    """
    Execute Round Robin load balancing under the shared discrete-event simulation contract.

    Assigns tasks to available VMs in strict cyclic order (distributed per-VM queues).
    Models waiting time when the selected VM has previously queued tasks still executing.
    Updates VM and Task objects in-place.

    Parameters
    ----------
    vms             : List[VM]   — Available VMs (from SimulationEngine.vms)
    tasks           : List[Task] — All pending tasks (from SimulationEngine.tasks)
    start_index     : int        — Global task counter offset for cycle continuity across failover.
    processing_rate : float      — Simulated processing units per time unit (default: 1.0).

    Returns
    -------
    dict with keys:
      "algorithm"            : str
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
    ValueError — if vms list is empty or no VMs are available
    """
    if not vms:
        raise ValueError("Round Robin: VM list is empty — cannot assign tasks.")

    available_vms = [v for v in vms if v.available and v.status != STATUS_FAILED]
    if not available_vms:
        raise ValueError("Round Robin: No available VMs — all VMs are marked unavailable.")

    n = len(available_vms)
    assignment_log: List[Dict[str, Any]] = []

    # Track simulated completion timestamp per VM (local queue busy time)
    vm_busy_until: Dict[int, float] = {}
    for v in available_vms:
        prior_busy = float(v.current_load) / float(processing_rate) if v.current_load > 0 else 0.0
        vm_busy_until[v.vm_id] = prior_busy

    for local_idx, task in enumerate(tasks):
        global_idx = start_index + local_idx
        target_vm: VM = available_vms[global_idx % n]

        t_arr = getattr(task, "arrival_time", 0.0) or 0.0
        service_time = max(0.1, float(task.processing_req) / float(processing_rate))
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
            "task_id"        : task.task_id,
            "task_name"      : task.name,
            "processing_req" : task.processing_req,
            "vm_id"          : target_vm.vm_id,
            "vm_name"        : target_vm.name,
            "vm_index_used"  : global_idx % n,
            "arrival_time"   : t_arr,
            "start_time"     : start_time,
            "completion_time": comp_time,
            "waiting_time"   : waiting_time,
            "response_time"  : response_time,
        })

    # ── Build summary dicts and metrics ───────────────────────────────────────
    vm_task_counts = {v.name: v.task_count   for v in available_vms}
    vm_total_loads = {v.name: v.current_load for v in available_vms}

    from simulation.metrics import compute_metrics
    metrics = compute_metrics(vms=available_vms, tasks=tasks, algorithm=ALGORITHM_NAME)

    return {
        "algorithm"            : ALGORITHM_NAME,
        "total_tasks"          : len(tasks),
        "total_vms"            : n,
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


def validate_round_robin(vms: List[VM], tasks: List[Task]) -> List[str]:
    """
    Validate that Round Robin was applied correctly.

    Checks:
      1. Every task has been assigned to a VM.
      2. Total tasks assigned across all VMs equals total tasks.
      3. Cyclic order is respected (by arrival_order).
      4. Timing consistency (start >= arrival, response == wait + service).

    Returns a list of error strings (empty list = all checks passed).
    """
    errors: List[str] = []

    # Check 1: every task is assigned
    unassigned = [t for t in tasks if t.assigned_vm_id is None]
    if unassigned:
        errors.append(f"Check 1 FAIL: {len(unassigned)} tasks have no VM assignment.")

    # Check 2: sum of VM task counts == total tasks
    total_assigned = sum(v.task_count for v in vms if v.available)
    if total_assigned != len(tasks):
        errors.append(
            f"Check 2 FAIL: VM task counts sum to {total_assigned}, "
            f"expected {len(tasks)}."
        )

    # Check 3: cyclic order
    available_vms = [v for v in vms if v.available]
    n = len(available_vms)
    if n > 0:
        sorted_tasks = sorted(tasks, key=lambda t: t.arrival_order)
        for i, task in enumerate(sorted_tasks):
            expected_vm_id = available_vms[i % n].vm_id
            if task.assigned_vm_id != expected_vm_id:
                errors.append(
                    f"Check 3 FAIL: Task {task.name} (arrival #{task.arrival_order}) "
                    f"should go to VM-{expected_vm_id} but got VM-{task.assigned_vm_id}."
                )
                break  # report only the first violation

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

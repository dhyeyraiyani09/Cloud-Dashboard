"""
algorithms/throttled.py — Least-Loaded Dynamic Load Balancing Algorithm (Existing Variant).

Historical Context & Academic Note:
  In earlier versions of this project, this algorithm was labeled "Throttled (Dynamic)".
  Following an academic correctness audit, it is noted that this implementation does
  NOT implement the traditional availability-table, first-available Throttled algorithm
  (as originally formulated in CloudAnalyst / CloudSim by Wickremasinghe et al., 2010).

  Instead, this algorithm implements a greedy Least-Loaded (minimum current load)
  dynamic scheduling policy:
    - For each incoming task, the scheduler inspects the current cumulative workload
      (current_load) across all available (non-failed) VMs.
    - It assigns the task to the available VM with the lowest current_load:
        vm = min(available_vms, key=lambda v: (v.current_load, v.vm_id))
    - It does not maintain a binary availability table or throttle/queue
      tasks when VMs are busy.

  To maintain compatibility with existing tests and internal callers, the module
  and function names (`run_throttled`, `validate_throttled`) are preserved, while
  user-facing labels and descriptions identify it as:
  "Least-Loaded Dynamic (Existing Variant)".

Contrast with Round Robin (Static):
  - Round Robin uses  vm = vms[index % n]  — cyclic, no load inspection.
  - Least-Loaded uses vm = min(available_vms, key=lambda v: (v.current_load, v.vm_id))

Usage (called by SimulationEngine.run_algorithm()):
  from algorithms.throttled import run_throttled
  result = run_throttled(engine.vms, engine.tasks)

The function operates in-place on the shared VM and Task objects in the
engine, so all changes are immediately reflected in the dashboard.
"""

from typing import List, Dict, Any
from simulation.vm   import VM,   STATUS_BUSY, STATUS_FAILED
from simulation.task import Task, STATUS_COMPLETED


# ── Algorithm identifiers (Primary label & backward compatibility alias) ──────
ALGORITHM_NAME        = "Least-Loaded Dynamic (Existing Variant)"
LEGACY_ALGORITHM_NAME = "Throttled (Dynamic)"


def run_throttled(vms: List[VM], tasks: List[Task]) -> Dict[str, Any]:
    """
    Execute Throttled (least-load) dynamic load balancing.

    For every task:
      1. Scan the VM state table for available (non-failed) VMs.
      2. Select the VM with the lowest current_load.
         Ties are broken by VM ID (lower ID wins) for determinism.
      3. Assign the task to that VM.
      4. Update the VM's current_load and task list immediately so the
         next task decision reflects the updated state.
      5. Mark the task as Completed (instantaneous simulation).

    Parameters
    ----------
    vms   : List[VM]   — All VMs in the cluster (from SimulationEngine.vms)
    tasks : List[Task] — All tasks to process (from SimulationEngine.tasks)

    Returns
    -------
    dict with keys:
      "algorithm"      : str  — Algorithm name
      "total_tasks"    : int  — Number of tasks processed
      "total_vms"      : int  — Number of available VMs used
      "assignment_log" : list — Per-task records showing the dynamic decision
      "vm_task_counts" : dict — {vm_name: task_count}
      "vm_total_loads" : dict — {vm_name: cumulative processing units assigned}

    Each assignment_log entry also records the VM loads at decision time,
    making it possible to verify that decisions were truly dynamic.

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

    for task in tasks:
        # ── Re-read VM state table at each task ───────────────────────────────
        # This is what makes the algorithm dynamic: we inspect current_load
        # for every single task, not just once at the start.
        # Ties broken by vm_id (lowest ID first) for reproducibility.
        target_vm: VM = min(
            available_vms,
            key=lambda v: (v.current_load, v.vm_id)
        )

        # Snapshot loads before assignment (for log / comparison visibility)
        load_snapshot = {v.name: v.current_load for v in available_vms}

        # ── Update Task ───────────────────────────────────────────────────────
        task.assigned_vm_id = target_vm.vm_id
        task.status         = STATUS_COMPLETED   # instantaneous simulation

        # ── Update VM (immediately, so next iteration sees the new state) ─────
        target_vm.task_ids.append(task.task_id)
        target_vm.current_load += task.processing_req
        target_vm.status = STATUS_BUSY

        # ── Log entry — includes pre-assignment state for transparency ────────
        assignment_log.append({
            "task_id"           : task.task_id,
            "task_name"         : task.name,
            "processing_req"    : task.processing_req,
            "vm_id"             : target_vm.vm_id,
            "vm_name"           : target_vm.name,
            "loads_before"      : load_snapshot,     # shows dynamic decision
            "chosen_load_before": load_snapshot[target_vm.name],
        })

    # ── Build summary dicts ───────────────────────────────────────────────────
    vm_task_counts = {v.name: v.task_count   for v in available_vms}
    vm_total_loads = {v.name: v.current_load for v in available_vms}

    return {
        "algorithm"        : ALGORITHM_NAME,
        "legacy_algorithm" : LEGACY_ALGORITHM_NAME,
        "total_tasks"      : len(tasks),
        "total_vms"        : len(available_vms),
        "assignment_log"   : assignment_log,
        "vm_task_counts"   : vm_task_counts,
        "vm_total_loads"   : vm_total_loads,
    }


def validate_throttled(vms: List[VM], tasks: List[Task]) -> List[str]:
    """
    Validate that Throttled was applied correctly.

    Checks:
      1. Every task has been assigned (no unassigned tasks).
      2. Total VM task counts equal total tasks.
      3. No failed/unavailable VM received a task.

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

    return errors

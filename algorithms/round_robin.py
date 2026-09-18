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

Usage (called by SimulationEngine.run_algorithm()):
  from algorithms.round_robin import run_round_robin
  result = run_round_robin(engine.vms, engine.tasks)

The function operates directly on the shared VM and Task objects stored
in the engine, so all changes are immediately reflected in the dashboard.

Phase 4 will add: algorithms/throttled.py (Dynamic Throttled algorithm)
"""

from typing import List, Dict, Any
from simulation.vm   import VM,   STATUS_BUSY
from simulation.task import Task, STATUS_COMPLETED


# ── Algorithm identifier (used by the engine dispatcher) ─────────────────────
ALGORITHM_NAME = "Round Robin (Static)"


def run_round_robin(
    vms         : List[VM],
    tasks       : List[Task],
    start_index : int = 0,
) -> Dict[str, Any]:
    """
    Execute Round Robin load balancing.

    Assigns every task to the VMs in strict cyclic order.
    Updates VM and Task objects in-place.
    All tasks are marked Completed after assignment (instantaneous simulation).

    Parameters
    ----------
    vms         : List[VM]   — Available VMs (from SimulationEngine.vms)
    tasks       : List[Task] — All pending tasks (from SimulationEngine.tasks)
    start_index : int        — Global task counter offset for cycle continuity.
                               Defaults to 0 (normal behavior).
                               Pass the number of tasks already assigned to
                               preserve the Round Robin position across a
                               Phase 8 VM failure (failover continuity).

    Returns
    -------
    dict with keys:
      "algorithm"        : str  — Algorithm name
      "total_tasks"      : int  — Total tasks processed
      "total_vms"        : int  — Number of VMs used
      "assignment_log"   : list — Per-task assignment records (for debugging)
      "vm_task_counts"   : dict — {vm_name: task_count}
      "vm_total_loads"   : dict — {vm_name: total processing units assigned}

    Raises
    ------
    ValueError — if vms list is empty or no VMs are available
    """
    if not vms:
        raise ValueError("Round Robin: VM list is empty — cannot assign tasks.")

    # Filter to available (non-failed) VMs only
    available_vms = [v for v in vms if v.available]
    if not available_vms:
        raise ValueError("Round Robin: No available VMs — all VMs are marked unavailable.")

    n = len(available_vms)
    assignment_log: List[Dict[str, Any]] = []

    for local_idx, task in enumerate(tasks):
        # Global index preserves the cyclic position across phase boundaries.
        # For a normal (no-failover) run, start_index=0 so global_idx == local_idx.
        global_idx = start_index + local_idx
        target_vm: VM = available_vms[global_idx % n]

        # ── Update Task ───────────────────────────────────────────────────────
        task.assigned_vm_id = target_vm.vm_id
        task.status         = STATUS_COMPLETED   # instantaneous simulation

        # ── Update VM ─────────────────────────────────────────────────────────
        target_vm.task_ids.append(task.task_id)
        target_vm.current_load += task.processing_req
        target_vm.status = STATUS_BUSY

        # ── Log entry ─────────────────────────────────────────────────────────
        assignment_log.append({
            "task_id"        : task.task_id,
            "task_name"      : task.name,
            "processing_req" : task.processing_req,
            "vm_id"          : target_vm.vm_id,
            "vm_name"        : target_vm.name,
            "vm_index_used"  : global_idx % n,   # slot in the cycle (global)
        })

    # ── Build summary dicts ────────────────────────────────────────────────────
    vm_task_counts  = {v.name: v.task_count   for v in available_vms}
    vm_total_loads  = {v.name: v.current_load for v in available_vms}

    return {
        "algorithm"      : ALGORITHM_NAME,
        "total_tasks"    : len(tasks),
        "total_vms"      : n,
        "assignment_log" : assignment_log,
        "vm_task_counts" : vm_task_counts,
        "vm_total_loads" : vm_total_loads,
    }


def validate_round_robin(vms: List[VM], tasks: List[Task]) -> List[str]:
    """
    Validate that Round Robin was applied correctly.

    Checks:
      1. Every task has been assigned to a VM.
      2. Total tasks assigned across all VMs equals total tasks.
      3. Cyclic order is respected (by arrival_order).

    Returns a list of error strings (empty list = all checks passed).
    """
    errors: List[str] = []

    # Check 1: every task is assigned
    unassigned = [t for t in tasks if t.assigned_vm_id is None]
    if unassigned:
        errors.append(f"Check 1 FAIL: {len(unassigned)} tasks have no VM assignment.")

    # Check 2: sum of VM task counts == total tasks
    total_assigned = sum(v.task_count for v in vms)
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

    return errors

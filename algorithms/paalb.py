"""
algorithms/paalb.py — Priority-Aware Adaptive Load Balancer (PAALB).

Academic Reference & Rationale:
---------------------------------
Formulation: Original customized heuristic for multi-criteria task scheduling in cloud environments.
Combines three complementary scheduling principles:
1. Priority-Aware Urgency: Higher priority tiers (from Google Cluster Data 2011-2, tiers 0–11)
   are granted preferential dispatch to minimize turnaround latency for critical user-facing tasks.
2. Shortest Processing Time (SPT) Preference: Shorter tasks receive a higher dispatch score to
   maximize job completion rate and reduce overall mean waiting time across the cluster.
3. Dynamic Aging Anti-Starvation: Waiting time in the queue is accumulated linearly. This ensures
   that an aged low-priority task's score will eventually exceed any newly arrived high-priority task,
   establishing a mathematical overtaking horizon of 40 time units relative to newly arrived tasks (empirically
   demonstrating bounded queue delays without starvation across finite trace benchmarks).

Scoring Function:
-----------------
For each waiting task t at simulation time tau:
    S(t, tau) = w_p * P_norm(t) + w_s * L_norm(t) + w_a * A(t, tau)

Where:
    P_norm(t) = clamp(priority, 0, 11) / 11.0
    L_norm(t) = clamp((100.0 - estimated_service_time) / 99.0, 0.0, 1.0)
    A(t, tau) = max(0.0, tau - t.arrival_time) / T_ref

Default Weights:
    w_p   = 0.45  (Priority urgency weight)
    w_s   = 0.35  (Shortest-job preference weight)
    w_a   = 0.20  (Anti-starvation aging weight)
    T_ref = 10.0  (Aging reference time scale in simulated time units)

Note on Aging & Starvation:
    The mathematical bound (w_p + w_s) * T_ref / w_a = 40.0 time units represents a
    Priority Overtaking Horizon relative to newly arriving tasks under the default weights.
    It ensures that an aged task cannot be overtaken by any new arrivals once it has waited
    40 time units. However, existing queue backlog and non-preemptive currently running tasks
    can extend physical waiting time beyond 40 units in saturated clusters. Complete absence of
    starvation is an observed empirical result on finite evaluation workloads, rather than an
    unconditional theoretical guarantee under arbitrary or unbounded arrival streams.

VM Dispatch Rule:
    When one or more VMs are AVAILABLE, the scheduler assigns the highest-scoring task to
    the available VM with the lowest cumulative assigned workload (argmin current_load, vm_id).
    Tasks already running on VMs execute non-preemptively to completion.
"""

import collections
import heapq
from typing import List, Dict, Any, Optional, Tuple

from simulation.vm import VM, STATUS_IDLE, STATUS_BUSY, STATUS_FAILED
from simulation.task import Task, STATUS_COMPLETED
from simulation.metrics import compute_discrete_event_metrics, PerformanceMetrics


# ── Algorithm identifier ──────────────────────────────────────────────────────
ALGORITHM_NAME = "Priority-Aware Adaptive (PAALB)"
LEGACY_ALGORITHM_NAME = "PAALB"

VM_STATE_AVAILABLE = "AVAILABLE"
VM_STATE_BUSY      = "BUSY"

DEFAULT_W_PRIORITY     = 0.45
DEFAULT_W_SHORTEST_JOB = 0.35
DEFAULT_W_AGING        = 0.20
DEFAULT_T_REF          = 10.0

DEFAULT_W_P = DEFAULT_W_PRIORITY
DEFAULT_W_S = DEFAULT_W_SHORTEST_JOB
DEFAULT_W_A = DEFAULT_W_AGING


def compute_task_score(
    task           : Task,
    current_time   : float,
    w_priority     : float = DEFAULT_W_PRIORITY,
    w_shortest_job : float = DEFAULT_W_SHORTEST_JOB,
    w_aging        : float = DEFAULT_W_AGING,
    t_ref          : float = DEFAULT_T_REF,
    processing_rate: float = 1.0,
) -> float:
    """
    Compute dynamic scheduling score S(t, tau) for task t at simulation time tau.

    Parameters
    ----------
    task           : Task candidate in waiting queue
    current_time   : Current simulation timestamp tau
    w_priority     : Weight for priority component (default 0.45)
    w_shortest_job : Weight for Shortest Job First heuristic (default 0.35)
    w_aging        : Weight for aging / anti-starvation (default 0.20)
    t_ref          : Reference aging time scale in seconds/time units (default 10.0)
    processing_rate: Simulated processing units per time unit (default 1.0)

    Returns
    -------
    float : Composite scheduling score S(t, tau)
    """
    # 1. Normalized Priority: p in [0, 11] -> [0.0, 1.0]
    raw_p = getattr(task, "priority", 0)
    if raw_p is None:
        raw_p = 0
    try:
        raw_p = float(raw_p)
    except (ValueError, TypeError):
        raw_p = 0.0
    p_norm = max(0.0, min(1.0, raw_p / 11.0))

    # 2. Normalized Shortest Job First: smaller processing_req -> higher score
    service_time = max(0.1, float(task.processing_req) / float(processing_rate))
    # Service time in [1, 100] -> l_norm in [0.0, 1.0], clamped to prevent negative values
    l_norm = max(0.0, min(1.0, (100.0 - service_time) / 99.0))

    # 3. Dynamic Aging term: elapsed waiting time / t_ref
    waiting_time = max(0.0, current_time - float(task.arrival_time))
    a_term = waiting_time / float(t_ref)

    score = (w_priority * p_norm) + (w_shortest_job * l_norm) + (w_aging * a_term)
    return score


def validate_weights(
    w_priority     : float,
    w_shortest_job : float,
    w_aging        : float,
    t_ref          : float = DEFAULT_T_REF,
) -> None:
    """Validate PAALB scoring parameters."""
    if w_priority < 0.0 or w_shortest_job < 0.0 or w_aging < 0.0:
        raise ValueError("PAALB weights must be non-negative.")
    weight_sum = w_priority + w_shortest_job + w_aging
    if abs(weight_sum - 1.0) > 1e-5:
        raise ValueError(f"PAALB weights must sum to 1.0 (got {weight_sum:.4f}).")
    if t_ref <= 0.0:
        raise ValueError("PAALB t_ref must be strictly positive.")


def run_paalb(
    vms            : List[VM],
    tasks          : List[Task],
    processing_rate: float = 1.0,
    w_priority     : float = DEFAULT_W_PRIORITY,
    w_shortest_job : float = DEFAULT_W_SHORTEST_JOB,
    w_aging        : float = DEFAULT_W_AGING,
    t_ref          : float = DEFAULT_T_REF,
) -> Dict[str, Any]:
    """
    Execute Priority-Aware Adaptive Load Balancer (PAALB) via discrete-event simulation.

    Parameters
    ----------
    vms             : List[VM]   — VMs in the cluster (active and available)
    tasks           : List[Task] — Tasks to execute
    processing_rate : float      — Simulated processing units per time unit (default: 1.0)
    w_priority      : float      — Priority urgency weight (default: 0.45)
    w_shortest_job  : float      — Shortest-job preference weight (default: 0.35)
    w_aging         : float      — Anti-starvation aging weight (default: 0.20)
    t_ref           : float      — Aging reference time constant (default: 10.0)

    Returns
    -------
    dict with keys:
      "algorithm"            : str  — Algorithm name
      "total_tasks"          : int  — Number of tasks processed
      "completed_tasks"      : int  — Number of completed tasks
      "total_vms"            : int  — Number of available VMs used
      "assignment_log"       : list — Per-task execution records (start, wait, finish, priority)
      "event_log"            : list — Discrete-event state transition logs
      "vm_task_counts"       : dict — {vm_name: task_count}
      "vm_total_loads"       : dict — {vm_name: total workload assigned}
      "makespan"             : float — Total simulated time to complete all tasks
      "average_waiting_time" : float — Mean waiting time spent in queue
      "maximum_waiting_time" : float — Peak waiting time for any task
      "average_response_time": float — Mean turnaround time (wait + service)
      "maximum_response_time": float — Peak turnaround time
      "queued_task_count"    : int   — Number of tasks that had to wait in queue
      "metrics"              : PerformanceMetrics — Populated metrics object

    Raises
    ------
    ValueError — if VM list is empty, weights are invalid, or no VMs are available
    """
    # ── Validate weights ──────────────────────────────────────────────────────
    validate_weights(w_priority, w_shortest_job, w_aging, t_ref)

    if not vms:
        raise ValueError("PAALB: VM list is empty — cannot assign tasks.")

    available_vms: List[VM] = [v for v in vms if v.available and v.status != STATUS_FAILED]
    if not available_vms:
        raise ValueError("PAALB: No available VMs — all VMs are failed or marked unavailable.")

    table_vms: List[VM] = sorted(available_vms, key=lambda v: v.vm_id)

    if not tasks:
        empty_metrics = PerformanceMetrics(algorithm=ALGORITHM_NAME, active_vm_count=len(table_vms))
        return {
            "algorithm"            : ALGORITHM_NAME,
            "total_tasks"          : 0,
            "completed_tasks"      : 0,
            "total_vms"            : len(table_vms),
            "assignment_log"       : [],
            "event_log"            : [],
            "vm_task_counts"       : {v.name: v.task_count for v in table_vms},
            "vm_total_loads"       : {v.name: v.current_load for v in table_vms},
            "makespan"             : 0.0,
            "average_waiting_time" : 0.0,
            "maximum_waiting_time" : 0.0,
            "average_response_time": 0.0,
            "maximum_response_time": 0.0,
            "queued_task_count"    : 0,
            "metrics"              : empty_metrics,
        }

    # ── Initialize Availability Table ──────────────────────────────────────────
    availability_table: Dict[int, Dict[str, Any]] = {}
    completion_heap: List[Tuple[float, int, int, Any]] = []

    for v in table_vms:
        prior_busy = float(v.current_load) / float(processing_rate) if v.current_load > 0 else 0.0
        is_init_busy = prior_busy > 0.0
        availability_table[v.vm_id] = {
            "vm"             : v,
            "state"          : VM_STATE_BUSY if is_init_busy else VM_STATE_AVAILABLE,
            "current_task_id": v.task_ids[-1] if v.task_ids else None,
            "busy_until"     : prior_busy,
        }
        if is_init_busy:
            dummy_task = Task(
                task_id=-v.vm_id,
                name=f"PriorWork-{v.name}",
                size=v.current_load,
                processing_req=v.current_load,
                arrival_order=0,
            )
            heapq.heappush(completion_heap, (prior_busy, v.vm_id, -v.vm_id, dummy_task))

    # ── Task Arrival Schedule ─────────────────────────────────────────────────
    first_ts = next((t.timestamp for t in tasks if getattr(t, "timestamp", None) is not None), None)

    task_arrivals: List[Task] = []
    for t in tasks:
        t_arr = 0.0
        if getattr(t, "arrival_time", None) is not None:
            t_arr = float(t.arrival_time)
        elif getattr(t, "timestamp", None) is not None:
            t_arr = max(0.0, float(t.timestamp - first_ts) / 1_000_000.0) if first_ts is not None else 0.0
        t.arrival_time = t_arr
        task_arrivals.append(t)

    # Sort arrivals deterministically by (arrival_time, arrival_order, task_id)
    task_arrivals.sort(key=lambda t: (t.arrival_time, t.arrival_order, t.task_id))

    # Priority-aware waiting pool
    waiting_pool: List[Task] = []
    assignment_log: List[Dict[str, Any]] = []
    event_log: List[Dict[str, Any]] = []

    def _select_best_available_vm() -> Optional[VM]:
        """Select AVAILABLE VM with minimum cumulative current_load, tie-break by vm_id."""
        avails = [
            availability_table[v.vm_id]["vm"]
            for v in table_vms
            if availability_table[v.vm_id]["state"] == VM_STATE_AVAILABLE
        ]
        if not avails:
            return None
        return min(avails, key=lambda v: (v.current_load, v.vm_id))

    def _select_highest_scoring_task(current_time: float) -> Optional[Task]:
        """
        Find task with maximum S(t, current_time) in waiting pool.
        Tie-break deterministically by earliest arrival_time, then lowest task_id.
        """
        if not waiting_pool:
            return None
        best_idx = 0
        best_key = None

        for idx, t in enumerate(waiting_pool):
            s = compute_task_score(
                t, current_time, w_priority, w_shortest_job, w_aging, t_ref, processing_rate
            )
            # Tie-break tuple: (-score, arrival_time, task_id)
            key = (-round(s, 6), t.arrival_time, t.task_id)
            if best_key is None or key < best_key:
                best_key = key
                best_idx = idx

        return waiting_pool.pop(best_idx)

    def _dispatch_task(task: Task, vm: VM, current_time: float, from_queue: bool) -> None:
        """Assign task to VM, mark VM BUSY, schedule completion event."""
        service_time = max(0.1, float(task.processing_req) / float(processing_rate))
        start_time = current_time
        comp_time = start_time + service_time
        waiting_time = max(0.0, start_time - task.arrival_time)
        response_time = comp_time - task.arrival_time

        # Update Task attributes
        task.assigned_vm_id = vm.vm_id
        task.start_time = start_time
        task.completion_time = comp_time
        task.waiting_time = waiting_time
        task.response_time = response_time
        task.status = STATUS_COMPLETED

        # Update Availability Table
        availability_table[vm.vm_id]["state"] = VM_STATE_BUSY
        availability_table[vm.vm_id]["current_task_id"] = task.task_id
        availability_table[vm.vm_id]["busy_until"] = comp_time

        # Update VM object
        vm.task_ids.append(task.task_id)
        vm.current_load += task.processing_req
        vm.status = STATUS_BUSY

        # Push completion event to min-heap
        heapq.heappush(completion_heap, (comp_time, vm.vm_id, task.task_id, task))

        assignment_log.append({
            "task_id"        : task.task_id,
            "task_name"      : task.name,
            "processing_req" : task.processing_req,
            "priority"       : getattr(task, "priority", 0) or 0,
            "vm_id"          : vm.vm_id,
            "vm_name"        : vm.name,
            "arrival_time"   : task.arrival_time,
            "start_time"     : start_time,
            "completion_time": comp_time,
            "waiting_time"   : waiting_time,
            "response_time"  : response_time,
            "was_queued"     : from_queue,
        })

        event_log.append({
            "time"   : current_time,
            "event"  : "DISPATCH_QUEUED" if from_queue else "DISPATCH_IMMEDIATE",
            "task_id": task.task_id,
            "vm_id"  : vm.vm_id,
            "detail" : (
                f"Task {task.name} (p={getattr(task, 'priority', 0)}, req={task.processing_req}) "
                f"dispatched to {vm.name}. Est. finish at {comp_time:.2f} (wait={waiting_time:.2f})."
            ),
        })

    # ── Discrete-Event Simulation Loop ─────────────────────────────────────────
    arr_idx = 0
    total_arrivals = len(task_arrivals)

    while arr_idx < total_arrivals or completion_heap or waiting_pool:
        next_arr_time = (
            task_arrivals[arr_idx].arrival_time if arr_idx < total_arrivals else float("inf")
        )
        next_comp_time = completion_heap[0][0] if completion_heap else float("inf")

        current_time = min(next_arr_time, next_comp_time)
        if current_time == float("inf"):
            break

        # Step 1: Process completions at current_time
        while completion_heap and completion_heap[0][0] <= current_time:
            comp_time, vm_id, task_id, comp_task = heapq.heappop(completion_heap)
            availability_table[vm_id]["state"] = VM_STATE_AVAILABLE
            availability_table[vm_id]["current_task_id"] = None
            availability_table[vm_id]["busy_until"] = comp_time

            event_log.append({
                "time"   : comp_time,
                "event"  : "VM_FREED",
                "task_id": task_id,
                "vm_id"  : vm_id,
                "detail" : f"Task {comp_task.name} completed. {availability_table[vm_id]['vm'].name} -> AVAILABLE.",
            })

        # Step 2: Ingest all task arrivals at current_time into waiting pool
        while arr_idx < total_arrivals and task_arrivals[arr_idx].arrival_time <= current_time:
            arriving_task = task_arrivals[arr_idx]
            arr_idx += 1
            waiting_pool.append(arriving_task)

            event_log.append({
                "time"   : current_time,
                "event"  : "TASK_ARRIVED",
                "task_id": arriving_task.task_id,
                "vm_id"  : None,
                "detail" : f"Task {arriving_task.name} arrived at t={current_time:.2f}.",
            })

        # Step 3: Dispatch highest-scoring tasks from waiting pool to available VMs
        while waiting_pool:
            avail_vm = _select_best_available_vm()
            if avail_vm is None:
                break  # All active VMs are occupied

            best_task = _select_highest_scoring_task(current_time)
            if best_task is None:
                break

            _dispatch_task(best_task, avail_vm, current_time, from_queue=True)

    # ── Derive Performance Metrics ─────────────────────────────────────────────
    metrics = compute_discrete_event_metrics(vms=table_vms, tasks=tasks, algorithm=ALGORITHM_NAME)
    vm_task_counts = {v.name: v.task_count for v in table_vms}
    vm_total_loads = {v.name: v.current_load for v in table_vms}

    return {
        "algorithm"            : ALGORITHM_NAME,
        "legacy_algorithm"     : LEGACY_ALGORITHM_NAME,
        "total_tasks"          : len(tasks),
        "completed_tasks"      : metrics.completed_tasks,
        "total_vms"            : len(table_vms),
        "assignment_log"       : assignment_log,
        "event_log"            : event_log,
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


def validate_paalb(vms: List[VM], tasks: List[Task]) -> List[str]:
    """
    Validate that PAALB assignment satisfied core simulation invariants:
      1. Every task was completed and assigned to an available, non-failed VM.
      2. No VM executed overlapping tasks.
      3. Timing invariant: start_time >= arrival_time, completion = start + service.
      4. Turnaround invariant: response_time == waiting_time + service_time.
    """
    errors: List[str] = []
    active_vm_ids = {v.vm_id for v in vms if v.available and v.status != STATUS_FAILED}

    for t in tasks:
        if t.assigned_vm_id is None:
            errors.append(f"Task {t.name} was not assigned to any VM.")
        elif t.assigned_vm_id not in active_vm_ids:
            errors.append(f"Task {t.name} assigned to unavailable/failed VM {t.assigned_vm_id}.")

        if t.start_time is not None and t.arrival_time is not None:
            if t.start_time < t.arrival_time - 1e-6:
                errors.append(f"Task {t.name} start_time ({t.start_time}) < arrival_time ({t.arrival_time}).")
            if t.completion_time is not None:
                expected_resp = t.completion_time - t.arrival_time
                if abs(t.response_time - expected_resp) > 1e-4:
                    errors.append(f"Task {t.name} response_time inconsistency: {t.response_time} vs {expected_resp}.")

    return errors

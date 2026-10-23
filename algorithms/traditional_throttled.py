"""
algorithms/traditional_throttled.py — Traditional Throttled Load Balancing Algorithm.

Academic Reference & Attribution:
---------------------------------
Formulation: CloudAnalyst: A CloudSim-based Tool for Modelling and Analysis of Large
             Scale Cloud Computing Environments (Wickremasinghe, Calheiros, & Buyya, 2010).
             Proceedings of the 24th IEEE AINA 2010, Perth, Australia.

Core Mechanism:
---------------
1. Availability Table:
   Maintains an index table of all Virtual Machines mapping each VM ID to its current
   operational state: AVAILABLE or BUSY.
2. First-Available Allocation (First-Fit):
   When a task arrives, the load balancer scans the availability table from top to bottom
   (lowest VM ID first) and selects the FIRST VM marked AVAILABLE.
3. State Transition:
   The chosen VM's status in the table is immediately set to BUSY while it executes the task.
4. Throttled Ingress & FIFO Queuing:
   If all active VMs are currently BUSY, the task cannot be dispatched immediately. It is
   placed into a FIFO waiting queue (throttling workload intake to cluster capacity).
5. Completion & Queue Dispatch:
   When a VM completes a task, its state reverts to AVAILABLE. If there are tasks in the
   FIFO waiting queue, the head task is dispatched immediately to the newly available VM.
6. Execution-Time & Service-Time Model:
   - Tasks execute sequentially on their assigned VM.
   - Service-time estimate is derived deterministically from normalized processing units:
         estimated_service_time = task.processing_req / processing_rate
   - Explicit Distinction: This estimated duration is a simulated execution time
     representing computational workload in the simulator; it is NOT the actual runtime
     of the Google production task in Google data centers.
7. Deterministic Event Handling:
   Simultaneous completion events occurring at the exact same simulation time are processed
   deterministically (tie-broken by VM ID) before queued tasks are dispatched.
"""

import collections
import heapq
from typing import List, Dict, Any, Optional, Tuple

from simulation.vm import VM, STATUS_IDLE, STATUS_BUSY, STATUS_FAILED
from simulation.task import Task, STATUS_COMPLETED
from simulation.metrics import compute_discrete_event_metrics, PerformanceMetrics


# ── Algorithm identifier ──────────────────────────────────────────────────────
ALGORITHM_NAME = "Traditional Throttled"

VM_STATE_AVAILABLE = "AVAILABLE"
VM_STATE_BUSY      = "BUSY"


def run_traditional_throttled(
    vms            : List[VM],
    tasks          : List[Task],
    processing_rate: float = 1.0,
) -> Dict[str, Any]:
    """
    Execute the Traditional Throttled load balancing algorithm via discrete-event simulation.

    Parameters
    ----------
    vms             : List[VM]   — VMs in the cluster (active and available)
    tasks           : List[Task] — Tasks to execute
    processing_rate : float      — Simulated processing units per time unit (default: 1.0)

    Returns
    -------
    dict with keys:
      "algorithm"            : str  — Algorithm name
      "total_tasks"          : int  — Number of tasks processed
      "completed_tasks"      : int  — Number of completed tasks
      "total_vms"            : int  — Number of available VMs used
      "assignment_log"       : list — Per-task execution records (start, wait, finish)
      "event_log"            : list — Discrete-event state transition logs
      "vm_task_counts"       : dict — {vm_name: task_count}
      "vm_total_loads"       : dict — {vm_name: total workload assigned}
      "makespan"             : float — Total simulated time to complete all tasks
      "average_waiting_time" : float — Mean waiting time spent in FIFO queue
      "maximum_waiting_time" : float — Peak waiting time for any task
      "average_response_time": float — Mean turnaround time (wait + service)
      "maximum_response_time": float — Peak turnaround time
      "queued_task_count"    : int   — Number of tasks that had to wait in queue
      "metrics"              : PerformanceMetrics — Populated metrics object

    Raises
    ------
    ValueError — if VM list is empty or no VMs are available
    """
    if not vms:
        raise ValueError("Traditional Throttled: VM list is empty — cannot assign tasks.")

    available_vms: List[VM] = [
        v for v in vms if v.available and v.status != STATUS_FAILED
    ]
    if not available_vms:
        raise ValueError(
            "Traditional Throttled: No available VMs — all VMs are failed or marked unavailable."
        )

    # Documented table order: sorted by vm_id ascending (VM-1, VM-2, ...)
    table_vms: List[VM] = sorted(available_vms, key=lambda v: v.vm_id)

    if not tasks:
        # Safe handling of empty task input
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
    # If a VM already holds load (e.g. during failover Phase B continuity), its
    # busy state reflects its prior assigned execution time.
    availability_table: Dict[int, Dict[str, Any]] = {}
    completion_heap: List[Tuple[float, int, int, Any]] = []

    for v in table_vms:
        prior_busy = float(v.current_load) / float(processing_rate) if v.current_load > 0 else 0.0
        is_init_busy = prior_busy > 0.0
        availability_table[v.vm_id] = {
            "vm"              : v,
            "state"           : VM_STATE_BUSY if is_init_busy else VM_STATE_AVAILABLE,
            "current_task_id" : v.task_ids[-1] if v.task_ids else None,
            "busy_until"      : prior_busy,
        }
        if is_init_busy:
            # Schedule completion for prior work so VM becomes AVAILABLE at prior_busy
            dummy_task = Task(task_id=-v.vm_id, name=f"PriorWork-{v.name}", size=v.current_load, processing_req=v.current_load, arrival_order=0)
            heapq.heappush(completion_heap, (prior_busy, v.vm_id, -v.vm_id, dummy_task))

    # ── Task Arrival Schedule ─────────────────────────────────────────────────
    # Determine arrival times:
    # 1. task.arrival_time if set (relative simulation seconds)
    # 2. relative timestamp (timestamp - first_ts) / 1e6 if Google trace microseconds present
    # 3. 0.0 default (batch arrival)
    first_ts = next((t.timestamp for t in tasks if getattr(t, "timestamp", None) is not None), None)

    task_arrivals: List[Task] = []
    for t in tasks:
        t_arr = 0.0
        if getattr(t, "arrival_time", None) is not None:
            t_arr = float(t.arrival_time)
        elif getattr(t, "timestamp", None) is not None:
            if first_ts is not None:
                t_arr = max(0.0, float(t.timestamp - first_ts) / 1_000_000.0)
            else:
                t_arr = 0.0
        t.arrival_time = t_arr
        task_arrivals.append(t)

    # Sort arrivals deterministically by (arrival_time, arrival_order, task_id)
    task_arrivals.sort(key=lambda t: (t.arrival_time, t.arrival_order, t.task_id))

    # FIFO waiting queue for tasks arriving when all VMs are BUSY
    fifo_queue: collections.deque[Task] = collections.deque()

    assignment_log: List[Dict[str, Any]] = []
    event_log: List[Dict[str, Any]] = []

    def _find_first_available_vm() -> Optional[VM]:
        """Scan availability table sequentially in documented table order."""
        for v in table_vms:
            if availability_table[v.vm_id]["state"] == VM_STATE_AVAILABLE:
                return v
        return None

    def _dispatch_task(task: Task, vm: VM, current_time: float, from_queue: bool) -> None:
        """Assign task to VM, mark VM BUSY, schedule completion event."""
        # Simulated service-time estimate derived from normalized processing units
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
                f"Task {task.name} ({task.processing_req} units) dispatched to {vm.name}. "
                f"Est. completion at {comp_time:.2f} (wait={waiting_time:.2f})."
            ),
        })

    # ── Discrete-Event Simulation Loop ─────────────────────────────────────────
    arr_idx = 0
    total_arrivals = len(task_arrivals)

    while arr_idx < total_arrivals or completion_heap or fifo_queue:
        # Determine the next simulation event timestamp
        next_arr_time = (
            task_arrivals[arr_idx].arrival_time if arr_idx < total_arrivals else float("inf")
        )
        next_comp_time = completion_heap[0][0] if completion_heap else float("inf")

        current_time = min(next_arr_time, next_comp_time)
        if current_time == float("inf"):
            break

        # ── Step 1: Process ALL completions at current_time ────────────────────
        # Deterministic tie-breaking: completion_heap entries sorted by (comp_time, vm_id)
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
                "detail" : f"Task {comp_task.name} completed. {availability_table[vm_id]['vm'].name} state -> AVAILABLE.",
            })

        # ── Step 2: Dispatch from FIFO queue to any newly AVAILABLE VMs ────────
        while fifo_queue:
            avail_vm = _find_first_available_vm()
            if avail_vm is None:
                break  # All VMs occupied
            q_task = fifo_queue.popleft()
            _dispatch_task(q_task, avail_vm, current_time, from_queue=True)

        # ── Step 3: Process ALL task arrivals at current_time ──────────────────
        while arr_idx < total_arrivals and task_arrivals[arr_idx].arrival_time <= current_time:
            arriving_task = task_arrivals[arr_idx]
            arr_idx += 1

            event_log.append({
                "time"   : current_time,
                "event"  : "TASK_ARRIVED",
                "task_id": arriving_task.task_id,
                "vm_id"  : None,
                "detail" : f"Task {arriving_task.name} arrived at t={current_time:.2f}.",
            })

            # If queue is empty, attempt immediate allocation to first available VM
            if not fifo_queue:
                avail_vm = _find_first_available_vm()
                if avail_vm is not None:
                    _dispatch_task(arriving_task, avail_vm, current_time, from_queue=False)
                    continue

            # Otherwise, all VMs are BUSY or queue already has waiting tasks: ENQUEUE
            fifo_queue.append(arriving_task)
            event_log.append({
                "time"   : current_time,
                "event"  : "TASK_QUEUED",
                "task_id": arriving_task.task_id,
                "vm_id"  : None,
                "detail" : (
                    f"All VMs BUSY. Task {arriving_task.name} placed into FIFO queue "
                    f"(queue depth: {len(fifo_queue)})."
                ),
            })

    # ── Derive Performance Metrics ─────────────────────────────────────────────
    metrics = compute_discrete_event_metrics(vms=table_vms, tasks=tasks, algorithm=ALGORITHM_NAME)

    vm_task_counts = {v.name: v.task_count for v in table_vms}
    vm_total_loads = {v.name: v.current_load for v in table_vms}

    return {
        "algorithm"            : ALGORITHM_NAME,
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


def validate_traditional_throttled(vms: List[VM], tasks: List[Task]) -> List[str]:
    """
    Validate that Traditional Throttled execution followed availability and timing rules.

    Checks:
      1. Every task has been assigned to an available VM.
      2. Sum of VM task counts equals total tasks.
      3. No unavailable or failed VM received a task.
      4. Task start times, completion times, and response times are consistent.
      5. Response time equals waiting time plus service duration.

    Returns a list of error strings (empty list = all checks passed).
    """
    errors: List[str] = []

    unassigned = [t for t in tasks if t.assigned_vm_id is None]
    if unassigned:
        errors.append(f"Check 1 FAIL: {len(unassigned)} tasks have no assigned VM.")

    total_counted = sum(v.task_count for v in vms if v.available and v.status != STATUS_FAILED)
    if total_counted != len(tasks):
        errors.append(
            f"Check 2 FAIL: VM task counts sum to {total_counted}, expected {len(tasks)}."
        )

    unavailable_ids = {v.vm_id for v in vms if not v.available or v.status == STATUS_FAILED}
    bad_assignments = [t for t in tasks if t.assigned_vm_id in unavailable_ids]
    if bad_assignments:
        errors.append(
            f"Check 3 FAIL: {len(bad_assignments)} tasks assigned to unavailable/failed VMs."
        )

    for t in tasks:
        if t.start_time is None or t.completion_time is None:
            errors.append(f"Check 4 FAIL: Task {t.name} missing start_time or completion_time.")
            break
        if t.start_time < t.arrival_time:
            errors.append(
                f"Check 4 FAIL: Task {t.name} start_time ({t.start_time}) < arrival_time ({t.arrival_time})."
            )
            break
        if t.completion_time < t.start_time:
            errors.append(
                f"Check 4 FAIL: Task {t.name} completion_time ({t.completion_time}) < start_time ({t.start_time})."
            )
            break
        expected_resp = t.completion_time - t.arrival_time
        if abs(t.response_time - expected_resp) > 1e-4:
            errors.append(
                f"Check 5 FAIL: Task {t.name} response_time ({t.response_time}) != "
                f"completion_time - arrival_time ({expected_resp})."
            )
            break

    return errors

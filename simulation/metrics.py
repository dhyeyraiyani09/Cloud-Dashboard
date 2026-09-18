"""
simulation/metrics.py — Phase 6 Performance Metrics.

Provides:
  - PerformanceMetrics dataclass  — holds all computed metrics for one
                                     algorithm run.
  - compute_metrics()             — derives metrics from VM/task state
                                     after algorithm assignment.

Simulated Execution Time Model
-------------------------------
Tasks execute sequentially on each VM.
Processing rate = 1 processing unit per simulated time unit.

For each VM, completion times are calculated in task-assignment order
(the order tasks appear in vm.task_ids):

  cumulative_0 = task_0.processing_req
  cumulative_1 = task_0.processing_req + task_1.processing_req
  ...

The VM's total simulated work = its final cumulative value = vm.current_load.

Metrics Derived
---------------
  makespan          = max(vm.current_load for active VMs)
  avg_response_time = mean(completion_time per task)   [arrival = 0]
  max_response_time = max(completion_time per task)
  throughput        = completed_tasks / makespan
  cluster_util      = total_workload / (active_vms × makespan) × 100
  load_imbalance    = max_vm_workload − min_vm_workload
  norm_imbalance    = load_imbalance / avg_vm_workload × 100
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class PerformanceMetrics:
    """
    Holds all Phase 6 performance metrics for a single algorithm run.

    All time units are simulated (not wall-clock seconds).

    Attributes
    ----------
    algorithm              : Name of the algorithm (e.g. "Round Robin (Static)")
    total_tasks            : Total number of tasks in the workload
    completed_tasks        : Tasks that were successfully assigned
    active_vm_count        : Number of active (available, non-failed) VMs
    total_workload         : Sum of processing_req across all tasks

    makespan               : Max cumulative workload among active VMs
                             (= simulated total execution time)
    average_response_time  : Mean task completion time (arrival=0)
    maximum_response_time  : Worst-case task completion time
    throughput             : completed_tasks / makespan
    cluster_utilization    : total_workload / (active_vms × makespan) × 100

    max_vm_workload        : Highest cumulative assigned workload on any VM
    min_vm_workload        : Lowest cumulative assigned workload on any active VM
    avg_vm_workload        : Mean cumulative workload across active VMs
    load_imbalance         : max_vm_workload − min_vm_workload
    normalized_imbalance   : load_imbalance / avg_vm_workload × 100
    """
    algorithm             : str   = ""
    total_tasks           : int   = 0
    completed_tasks       : int   = 0
    active_vm_count       : int   = 0
    total_workload        : int   = 0

    makespan              : float = 0.0
    average_response_time : float = 0.0
    maximum_response_time : float = 0.0
    throughput            : float = 0.0
    cluster_utilization   : float = 0.0

    max_vm_workload       : int   = 0
    min_vm_workload       : int   = 0
    avg_vm_workload       : float = 0.0
    load_imbalance        : int   = 0
    normalized_imbalance  : float = 0.0

    def to_dict(self) -> Dict:
        """Flat dict for DataFrames / JSON serialisation."""
        return {
            "Algorithm"             : self.algorithm,
            "Tasks"                 : self.total_tasks,
            "Active VMs"            : self.active_vm_count,
            "Total Workload (units)": self.total_workload,
            "Makespan (time units)" : self.makespan,
            "Avg Response Time"     : round(self.average_response_time, 2),
            "Max Response Time"     : round(self.maximum_response_time, 2),
            "Throughput (tasks/tu)" : round(self.throughput, 4),
            "Cluster Utilization %" : round(self.cluster_utilization, 2),
            "Max VM Workload"       : self.max_vm_workload,
            "Min VM Workload"       : self.min_vm_workload,
            "Load Imbalance (units)": self.load_imbalance,
            "Norm. Imbalance %"     : round(self.normalized_imbalance, 2),
        }


def compute_metrics(vms, tasks, algorithm: str = "") -> PerformanceMetrics:
    """
    Compute PerformanceMetrics from post-assignment VM and task state.

    Parameters
    ----------
    vms       : List[VM]   — All VMs (including scaled-down/failed ones)
    tasks     : List[Task] — All tasks (all should be STATUS_COMPLETED)
    algorithm : str        — Algorithm name for the metrics label

    Returns
    -------
    PerformanceMetrics — Fully populated metrics object

    Notes
    -----
    The function builds a task_id → Task lookup map and then, for each
    active VM, walks vm.task_ids in assignment order to compute per-task
    sequential completion times.  This implements the model:

        completion_time(task_k_on_VM_i) =
            sum(processing_req for task_j assigned to VM_i where j <= k)
    """
    from simulation.vm import STATUS_FAILED

    # ── Active VMs (available, not failed) ────────────────────────────────────
    active_vms = [v for v in vms if v.available and v.status != STATUS_FAILED]
    n_active   = len(active_vms)

    if n_active == 0 or not tasks:
        return PerformanceMetrics(algorithm=algorithm)

    # ── Task lookup map ────────────────────────────────────────────────────────
    task_map = {t.task_id: t for t in tasks}

    # ── Total workload ─────────────────────────────────────────────────────────
    total_workload = sum(t.processing_req for t in tasks)

    # ── VM workloads (cumulative assigned load) ────────────────────────────────
    vm_workloads = [v.current_load for v in active_vms]

    max_vm_workload = max(vm_workloads) if vm_workloads else 0
    min_vm_workload = min(vm_workloads) if vm_workloads else 0
    avg_vm_workload = (sum(vm_workloads) / n_active) if n_active > 0 else 0.0

    # ── Makespan ───────────────────────────────────────────────────────────────
    # Sequential processing model: each VM executes its tasks one after another.
    # A VM's total simulated execution time = its cumulative assigned workload.
    makespan = float(max_vm_workload)

    # ── Response times (sequential completion model) ──────────────────────────
    # For each VM, walk task_ids in assignment order and accumulate.
    # completion_time(task) = sum of processing_req of all tasks on this VM
    # that were assigned before (and including) this task.
    response_times: List[float] = []
    for vm in active_vms:
        cumulative = 0
        for tid in vm.task_ids:
            task = task_map.get(tid)
            if task is None:
                continue
            cumulative += task.processing_req
            response_times.append(float(cumulative))  # arrival = 0

    n_rt = len(response_times)
    avg_rt = (sum(response_times) / n_rt) if n_rt > 0 else 0.0
    max_rt = max(response_times) if response_times else 0.0

    # ── Throughput ─────────────────────────────────────────────────────────────
    completed_tasks = len([t for t in tasks if task_map.get(t.task_id)])
    # Count tasks that were actually assigned (have an assigned VM)
    assigned_count = sum(1 for v in active_vms for _ in v.task_ids)
    throughput = (assigned_count / makespan) if makespan > 0 else 0.0

    # ── Cluster Utilization ────────────────────────────────────────────────────
    # How much of the available simulated processing capacity was actually used.
    # cluster_capacity = active_vms × makespan
    cluster_capacity = n_active * makespan
    cluster_util = ((total_workload / cluster_capacity) * 100) if cluster_capacity > 0 else 0.0

    # ── Load Imbalance ─────────────────────────────────────────────────────────
    load_imbalance = max_vm_workload - min_vm_workload
    norm_imbalance = (
        (load_imbalance / avg_vm_workload) * 100
    ) if avg_vm_workload > 0 else 0.0

    return PerformanceMetrics(
        algorithm             = algorithm,
        total_tasks           = len(tasks),
        completed_tasks       = assigned_count,
        active_vm_count       = n_active,
        total_workload        = total_workload,
        makespan              = makespan,
        average_response_time = round(avg_rt, 2),
        maximum_response_time = round(max_rt, 2),
        throughput            = round(throughput, 4),
        cluster_utilization   = round(cluster_util, 2),
        max_vm_workload       = max_vm_workload,
        min_vm_workload       = min_vm_workload,
        avg_vm_workload       = round(avg_vm_workload, 2),
        load_imbalance        = load_imbalance,
        normalized_imbalance  = round(norm_imbalance, 2),
    )

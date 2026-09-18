"""
simulation/failover.py — Phase 8: VM Failure & Failover.

FailoverManager orchestrates a simulated mid-run VM failure and records
all failover events.

Architecture
------------
    Tasks 0..failure_after_task-1 <- assigned using full available VM pool
                                         |
                              VM failure triggered
                                         |
    Tasks failure_after_task..end  <- assigned excluding the failed VM

Failure model
-------------
  Deterministic: failure is triggered after a configurable task count.
  vm.fail() sets:
      vm.status    = STATUS_FAILED
      vm.available = False

  Neither algorithm selects a VM where available=False or
  status==STATUS_FAILED — failover is automatic once fail() is called.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any

from simulation.vm import VM, STATUS_FAILED


@dataclass
class FailoverEvent:
    """
    Records a single failover-related event.

    Attributes
    ----------
    event_type  : "VM Failure" | "Failover Active" | "Task Redirected" | "No VMs Available"
    vm_name     : VM name involved
    vm_id       : VM numeric ID
    task_index  : Task index at which the event occurred (0-based)
    detail      : Human-readable description
    timestamp   : Wall-clock time string
    """
    event_type  : str
    vm_name     : str
    vm_id       : int
    task_index  : int
    detail      : str
    timestamp   : str = field(
        default_factory=lambda: datetime.now().strftime("%H:%M:%S")
    )


class FailoverManager:
    """
    Manages deterministic VM failure and failover during a simulation run.

    Parameters
    ----------
    fail_vm_id          : int  -- vm_id of the VM to fail (1-based)
    failure_after_tasks : int  -- fail the VM after this many tasks assigned
                                  (0 = fail before any task is assigned)
    """

    def __init__(self, fail_vm_id: int, failure_after_tasks: int) -> None:
        self.fail_vm_id           = fail_vm_id
        self.failure_after_tasks  = failure_after_tasks

        self.events               : List[FailoverEvent] = []
        self.failed_vm_name       : str  = ""
        self.failure_triggered    : bool = False
        self.tasks_before_failure : int  = 0
        self.tasks_after_failure  : int  = 0
        self.final_active_vms     : int  = 0
        self.tasks_skipped        : int  = 0

    def run_with_failover(
        self,
        vms     : List[VM],
        tasks   : list,
        algo_fn,
    ) -> Dict[str, Any]:
        """
        Run a load-balancing algorithm with a mid-run VM failure.

        Phase A: tasks[0..failure_after_tasks-1]  -> full VM pool
        Failure: target VM marked STATUS_FAILED / available=False
        Phase B: tasks[failure_after_tasks..]     -> remaining available VMs

        Round Robin continuity (Fix 1)
        --------------------------------
        For Round Robin, Phase B is called with start_index=fail_at so the
        scheduler continues from its current cyclic position rather than
        restarting at index 0.  Throttled is unaffected (it inspects load
        per task, not a positional index).

        Graceful all-VMs-failed handling (Fix 2)
        -----------------------------------------
        If no VMs remain after failure, Phase B is skipped entirely and a
        "No VMs Available" event is recorded.  No exception is raised.
        Phase A is also guarded: if the initial VM pool is already exhausted
        the result dict is populated with safe defaults.

        Returns the combined result dict (same schema as algo_fn).
        """
        from algorithms.round_robin import ALGORITHM_NAME as RR_NAME

        # Locate target VM
        target_vm: Optional[VM] = None
        for v in vms:
            if v.vm_id == self.fail_vm_id:
                target_vm = v
                break

        if target_vm is None or not target_vm.available or target_vm.status == STATUS_FAILED:
            # VM not found / already failed -> run normally (no failover path)
            try:
                result = algo_fn(vms, tasks)
            except ValueError:
                result = {
                    "algorithm": "", "total_tasks": len(tasks),
                    "total_vms": 0, "assignment_log": [],
                    "vm_task_counts": {}, "vm_total_loads": {},
                }
            self.final_active_vms = sum(
                1 for v in vms if v.available and v.status != STATUS_FAILED
            )
            return result

        self.failed_vm_name = target_vm.name
        n_tasks   = len(tasks)
        fail_at   = min(self.failure_after_tasks, n_tasks)

        tasks_a = tasks[:fail_at]
        tasks_b = tasks[fail_at:]

        combined_log    : List[Dict] = []
        combined_result : Dict[str, Any] = {
            "algorithm": "", "total_tasks": n_tasks,
            "total_vms": 0, "assignment_log": [],
            "vm_task_counts": {}, "vm_total_loads": {},
        }

        # Detect whether algo_fn is Round Robin so we can pass start_index
        is_rr = getattr(algo_fn, "__name__", "") == "run_round_robin"

        # -- Phase A: before failure --
        if tasks_a:
            try:
                res_a = algo_fn(vms, tasks_a)
                combined_log.extend(res_a.get("assignment_log", []))
                combined_result.update(res_a)
            except ValueError:
                # No available VMs even before failure — record and skip
                self.tasks_skipped += len(tasks_a)

        self.tasks_before_failure = fail_at

        # -- Trigger failure --
        target_vm.fail()
        self.failure_triggered = True

        self.events.append(FailoverEvent(
            event_type="VM Failure",
            vm_name=target_vm.name,
            vm_id=target_vm.vm_id,
            task_index=fail_at,
            detail=(
                f"{target_vm.name} marked FAILED after task {fail_at}. "
                "Removed from scheduler pool."
            ),
        ))
        self.events.append(FailoverEvent(
            event_type="Failover Active",
            vm_name=target_vm.name,
            vm_id=target_vm.vm_id,
            task_index=fail_at,
            detail=(
                "Failover triggered. All subsequent tasks redirected "
                "to remaining available VMs."
            ),
        ))

        # -- Phase B: after failure --
        remaining_vms = [v for v in vms if v.available and v.status != STATUS_FAILED]

        if tasks_b and not remaining_vms:
            # No healthy VMs left — record skipped tasks gracefully (Fix 2)
            self.tasks_skipped += len(tasks_b)
            self.events.append(FailoverEvent(
                event_type="No VMs Available",
                vm_name="—",
                vm_id=-1,
                task_index=fail_at,
                detail=(
                    f"No available VMs for failover. "
                    f"{len(tasks_b)} task(s) could not be assigned."
                ),
            ))
        elif tasks_b:
            try:
                # For Round Robin: pass start_index=fail_at to continue the cycle
                # from where Phase A stopped (Fix 1).
                # For Throttled: call normally (algo inspects load each task).
                if is_rr:
                    res_b = algo_fn(vms, tasks_b, start_index=fail_at)
                else:
                    res_b = algo_fn(vms, tasks_b)

                combined_log.extend(res_b.get("assignment_log", []))
                combined_result.update(res_b)

                self.events.append(FailoverEvent(
                    event_type="Task Redirected",
                    vm_name=target_vm.name,
                    vm_id=target_vm.vm_id,
                    task_index=fail_at,
                    detail=(
                        f"{len(tasks_b)} task(s) successfully redirected to "
                        f"{len(remaining_vms)} remaining VM(s)."
                    ),
                ))
            except ValueError as exc:
                # Unexpected — record gracefully, do not crash (Fix 2)
                self.tasks_skipped += len(tasks_b)
                self.events.append(FailoverEvent(
                    event_type="No VMs Available",
                    vm_name="—",
                    vm_id=-1,
                    task_index=fail_at,
                    detail=f"Scheduler error during failover: {exc}",
                ))

        self.tasks_after_failure = len(tasks_b)
        self.final_active_vms    = sum(
            1 for v in vms if v.available and v.status != STATUS_FAILED
        )

        combined_result["total_tasks"]    = n_tasks
        combined_result["assignment_log"] = combined_log
        return combined_result

    @property
    def failover_summary(self) -> Dict[str, Any]:
        """Plain-dict summary for dashboard Failover Summary card."""
        return {
            "failure_triggered"   : self.failure_triggered,
            "failed_vm_name"      : self.failed_vm_name,
            "fail_vm_id"          : self.fail_vm_id,
            "failure_after_tasks" : self.tasks_before_failure,
            "tasks_after_failure" : self.tasks_after_failure,
            "tasks_skipped"       : self.tasks_skipped,
            "final_active_vms"    : self.final_active_vms,
            "event_count"         : len(self.events),
        }

    def reset(self) -> None:
        """Clear all state (called by engine.reset())."""
        self.events               = []
        self.failed_vm_name       = ""
        self.failure_triggered    = False
        self.tasks_before_failure = 0
        self.tasks_after_failure  = 0
        self.final_active_vms     = 0
        self.tasks_skipped        = 0

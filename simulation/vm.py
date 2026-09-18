"""
simulation/vm.py — Virtual Machine model.

Defines the VM dataclass used throughout the simulation.
This model is algorithm-agnostic and will be used by:
  - Phase 3: Round Robin
  - Phase 4: Throttled
  - Phase 5: Automated Scaling Listener
  - Phase 8: VM Failure & Failover
"""

from dataclasses import dataclass, field
from typing import List

# ── VM Status constants ────────────────────────────────────────────────────────
STATUS_IDLE   = "Idle"
STATUS_BUSY   = "Busy"
STATUS_FAILED = "Failed"


@dataclass
class VM:
    """
    Represents a single Virtual Machine in the cloud cluster.

    Attributes
    ----------
    vm_id       : int   — Unique numeric identifier (1-based)
    name        : str   — Human-readable name, e.g. "VM-1"
    capacity    : int   — Maximum processing units this VM can handle
    current_load: int   — Sum of processing units of currently assigned tasks
    task_ids    : list  — IDs of tasks currently assigned to this VM
    status      : str   — One of: Idle | Busy | Failed
    available   : bool  — True if the VM can accept new tasks
    """
    vm_id       : int
    name        : str
    capacity    : int        = 100   # processing units
    current_load: int        = 0
    task_ids    : List[int]  = field(default_factory=list)
    status      : str        = STATUS_IDLE
    available   : bool       = True

    # ── Computed properties ────────────────────────────────────────────────────

    @property
    def task_count(self) -> int:
        """Number of tasks currently assigned to this VM."""
        return len(self.task_ids)

    @property
    def load_percent(self) -> float:
        """Assigned workload as % of capacity (can exceed 100% — cumulative model)."""
        if self.capacity == 0:
            return 0.0
        return round((self.current_load / self.capacity) * 100, 1)

    @property
    def display_status(self) -> str:
        """
        Human-readable status for the dashboard.

        In this project's instantaneous simulation model, tasks are marked
        Completed as soon as they are assigned — so a VM that has processed
        tasks will have STATUS_BUSY (it holds assigned workload records) but
        there are no actively running tasks.

        Mapping:
          Idle   → 'Idle'
          Busy   → 'Assigned / Loaded'  (workload records kept; tasks completed)
          Failed → 'Failed'
        """
        if self.status == STATUS_BUSY:
            return "Assigned / Loaded"
        if self.status == STATUS_FAILED:
            return "Failed"
        return "Idle"

    # ── State mutation helpers (used by algorithms in later phases) ────────────

    def assign_task(self, task_id: int, processing_req: int) -> None:
        """
        Assign a task to this VM. Updates load and status.
        Called by load-balancing algorithms (Phase 3+).
        """
        self.task_ids.append(task_id)
        self.current_load += processing_req
        self.status = STATUS_BUSY

    def complete_task(self, task_id: int, processing_req: int) -> None:
        """
        Mark a task as completed on this VM. Updates load and status.
        Called by the simulation engine (Phase 3+).
        """
        if task_id in self.task_ids:
            self.task_ids.remove(task_id)
            self.current_load = max(0, self.current_load - processing_req)
        if self.current_load == 0 and self.task_ids == []:
            self.status = STATUS_IDLE

    def fail(self) -> None:
        """Mark this VM as failed (Phase 8 — Failover)."""
        self.status = STATUS_FAILED
        self.available = False

    def recover(self) -> None:
        """Restore a failed VM to Idle state (Phase 8 — Failover)."""
        self.status = STATUS_IDLE
        self.available = True
        self.current_load = 0
        self.task_ids = []

    def reset(self) -> None:
        """Reset VM to initial state (used by Reset Simulation)."""
        self.current_load = 0
        self.task_ids = []
        self.status = STATUS_IDLE
        self.available = True

    def to_dict(self) -> dict:
        """Serialise VM to a plain dictionary (useful for display tables)."""
        return {
            "VM ID"       : self.vm_id,
            "Name"        : self.name,
            "Status"      : self.status,
            "Capacity"    : self.capacity,
            "Current Load": self.current_load,
            "Load %"      : f"{self.load_percent}%",
            "Tasks Assigned": self.task_count,
            "Available"   : "Yes" if self.available else "No",
        }


def create_vms(num_vms: int, base_capacity: int = 100) -> List[VM]:
    """
    Factory function — creates a list of fresh VMs.

    Parameters
    ----------
    num_vms       : int — How many VMs to create
    base_capacity : int — Processing capacity per VM (default 100 units)

    Returns
    -------
    List[VM] — Ready-to-use VM objects, all Idle
    """
    return [
        VM(vm_id=i + 1, name=f"VM-{i + 1}", capacity=base_capacity)
        for i in range(num_vms)
    ]

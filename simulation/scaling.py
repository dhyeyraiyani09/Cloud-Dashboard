"""
simulation/scaling.py — Automated Scaling Listener.

The AutoScalingListener monitors simulated workload demand against the active
cluster capacity and automatically scales the VM pool up or down before the
load-balancing algorithm makes its task assignments.

Architecture
------------
    Incoming Workload
          ↓
    Automated Scaling Listener   ← (this module)
          ↓
    Load Balancer (Round Robin / Throttled)
          ↓
    Active VM Cluster

Scaling is WORKLOAD-BASED, not real CPU-based:
    Workload Pressure % = total_processing_req ÷ (active_vms × vm_capacity) × 100

  Scale Up   when pressure > scale_up_threshold  (default 70%)
  Scale Down when pressure < scale_down_threshold (default 30%)

Limits:
  min_vms  (default 2) — never scale below this
  max_vms  (default 10)— never scale above this

The listener operates on the shared VM list stored in the engine, so all
scaling changes are immediately visible to both the load balancer and the
Streamlit dashboard.

Phase 8 will add VM failure/failover (separate concern).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from simulation.vm import VM, STATUS_FAILED


# ── Scaling event record ──────────────────────────────────────────────────────

@dataclass
class ScalingEvent:
    """
    Records a single scale-up or scale-down action taken by the listener.

    Attributes
    ----------
    event_type        : "Scale Up" or "Scale Down"
    vm_name           : Name of the VM added or removed (e.g. "VM-5")
    vm_id             : Numeric VM ID
    pressure_before   : Workload pressure (%) before the scaling action
    pressure_after    : Workload pressure (%) after the scaling action
    reason            : Human-readable explanation
    timestamp         : Wall-clock time of the event (HH:MM:SS)
    """
    event_type      : str
    vm_name         : str
    vm_id           : int
    pressure_before : float
    pressure_after  : float
    reason          : str
    timestamp       : str = field(
        default_factory=lambda: datetime.now().strftime("%H:%M:%S")
    )


# ── Automated Scaling Listener ────────────────────────────────────────────────

class AutoScalingListener:
    """
    Evaluates workload pressure and adjusts the VM cluster automatically.

    Parameters
    ----------
    scale_up_threshold   : float — Scale up  when pressure > this % (default 70)
    scale_down_threshold : float — Scale down when pressure < this % (default 30)
    min_vms              : int   — Never go below this VM count (default 2)
    max_vms              : int   — Never go above this VM count (default 10)
    vm_capacity          : int   — Processing units per VM (mirrors engine config)

    After calling evaluate_and_scale(), inspect:
        .events           — list of ScalingEvent (all actions taken)
        .vms_added        — count of VMs added
        .vms_removed      — count of VMs removed
        .initial_pressure — workload pressure before any scaling
        .final_pressure   — workload pressure after scaling completes
        .initial_vm_count — available VM count before scaling
        .final_vm_count   — available VM count after scaling
    """

    def __init__(
        self,
        scale_up_threshold   : float = 70.0,
        scale_down_threshold : float = 30.0,
        min_vms              : int   = 2,
        max_vms              : int   = 10,
        vm_capacity          : int   = 100,
    ) -> None:
        self.scale_up_threshold   = scale_up_threshold
        self.scale_down_threshold = scale_down_threshold
        self.min_vms              = min_vms
        self.max_vms              = max_vms
        self.vm_capacity          = vm_capacity

        # Statistics populated by evaluate_and_scale()
        self.events           : List[ScalingEvent] = []
        self.vms_added        : int   = 0
        self.vms_removed      : int   = 0
        self.initial_vm_count : int   = 0
        self.final_vm_count   : int   = 0
        self.initial_pressure : float = 0.0
        self.final_pressure   : float = 0.0

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _available(self, vms: List[VM]) -> List[VM]:
        """Return VMs that can accept tasks (not failed, not deactivated)."""
        return [v for v in vms if v.available and v.status != STATUS_FAILED]

    def _pressure(self, vms: List[VM], total_demand: int) -> float:
        """
        Workload pressure as a percentage (uncapped — can exceed 100%).

        pressure = (total_processing_req ÷ (active_vms × vm_capacity)) × 100
        """
        avail = self._available(vms)
        if not avail:
            return 0.0
        capacity = len(avail) * self.vm_capacity
        if capacity == 0:
            return 0.0
        return round((total_demand / capacity) * 100, 1)

    def _next_vm_id(self, vms: List[VM]) -> int:
        """Return the next unique VM ID (max existing + 1)."""
        return max(v.vm_id for v in vms) + 1

    # ── Main interface ────────────────────────────────────────────────────────

    def evaluate_and_scale(self, vms: List[VM], tasks) -> List[VM]:
        """
        Evaluate workload vs cluster capacity and scale VMs accordingly.

        Modifies *vms* in-place:
          - Scale Up:   appends new VM objects to the list
          - Scale Down: marks VMs as unavailable (available=False)

        The method runs scaling in two phases:
          1. Scale Up  — add VMs until pressure ≤ threshold or max_vms reached
          2. Scale Down — remove idle VMs until pressure ≥ threshold or min_vms reached

        Scale-up runs first, so the cluster is never left under-provisioned.

        Parameters
        ----------
        vms   : List[VM]   — The engine's VM list (modified in-place)
        tasks : iterable   — Tasks whose processing_req drives the demand calc

        Returns
        -------
        List[VM] — The same list (with additions/deactivations applied)
        """
        total_demand = sum(t.processing_req for t in tasks)

        self.initial_vm_count = len(self._available(vms))
        self.initial_pressure = self._pressure(vms, total_demand)

        # ── Phase 1: Scale Up ─────────────────────────────────────────────────
        while True:
            avail_count = len(self._available(vms))
            pressure    = self._pressure(vms, total_demand)

            if pressure <= self.scale_up_threshold or avail_count >= self.max_vms:
                break  # no scale-up needed / at max

            new_id  = self._next_vm_id(vms)
            new_vm  = VM(vm_id=new_id, name=f"VM-{new_id}", capacity=self.vm_capacity)
            vms.append(new_vm)
            self.vms_added += 1

            new_pressure = self._pressure(vms, total_demand)
            self.events.append(ScalingEvent(
                event_type      = "Scale Up",
                vm_name         = new_vm.name,
                vm_id           = new_id,
                pressure_before = pressure,
                pressure_after  = new_pressure,
                reason          = (
                    f"Workload pressure {pressure}% exceeded "
                    f"scale-up threshold ({self.scale_up_threshold}%)"
                ),
            ))

        # ── Phase 2: Scale Down ───────────────────────────────────────────────
        # Only consider idle VMs (no tasks, zero load) to avoid disrupting
        # VMs that already have work assigned.  Prefer removing the
        # highest-numbered VM (most recently added by scale-up, or the
        # last one in the initial pool).
        while True:
            avail_count = len(self._available(vms))
            pressure    = self._pressure(vms, total_demand)

            if pressure >= self.scale_down_threshold or avail_count <= self.min_vms:
                break  # no scale-down needed / at min

            # Find eligible idle VMs
            idle_candidates = [
                v for v in self._available(vms)
                if v.task_count == 0 and v.current_load == 0
            ]
            if not idle_candidates:
                break  # no eligible VMs to remove

            # Remove highest-ID idle VM first (LIFO — last-added, first-removed)
            vm_to_remove = max(idle_candidates, key=lambda v: v.vm_id)
            vm_to_remove.available = False   # deactivate (not deleted from list)
            self.vms_removed += 1

            new_pressure = self._pressure(vms, total_demand)
            self.events.append(ScalingEvent(
                event_type      = "Scale Down",
                vm_name         = vm_to_remove.name,
                vm_id           = vm_to_remove.vm_id,
                pressure_before = pressure,
                pressure_after  = new_pressure,
                reason          = (
                    f"Workload pressure {pressure}% was below "
                    f"scale-down threshold ({self.scale_down_threshold}%)"
                ),
            ))

        self.final_vm_count = len(self._available(vms))
        self.final_pressure = self._pressure(vms, total_demand)
        return vms

    # ── Reset (called by engine.reset()) ─────────────────────────────────────

    def reset(self) -> None:
        """Clear all accumulated state (used when the engine resets)."""
        self.events           = []
        self.vms_added        = 0
        self.vms_removed      = 0
        self.initial_vm_count = 0
        self.final_vm_count   = 0
        self.initial_pressure = 0.0
        self.final_pressure   = 0.0

    # ── Convenience properties for the dashboard ──────────────────────────────

    @property
    def scale_up_events(self) -> List[ScalingEvent]:
        return [e for e in self.events if e.event_type == "Scale Up"]

    @property
    def scale_down_events(self) -> List[ScalingEvent]:
        return [e for e in self.events if e.event_type == "Scale Down"]

    @property
    def last_scale_up(self) -> Optional[ScalingEvent]:
        evs = self.scale_up_events
        return evs[-1] if evs else None

    @property
    def last_scale_down(self) -> Optional[ScalingEvent]:
        evs = self.scale_down_events
        return evs[-1] if evs else None

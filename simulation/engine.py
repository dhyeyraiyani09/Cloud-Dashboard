"""
simulation/engine.py — Central Simulation State Engine.

SimulationEngine is the single source of truth for the simulation.
It stores all VMs, tasks, and overall status.

Design principles:
  - Algorithm-agnostic: the engine's run_algorithm() method dispatches
    to the correct algorithm module.  Adding a new algorithm only
    requires a new elif branch and a new module file.
  - Streamlit-friendly: stored in st.session_state so data survives
    UI interactions without being recreated unnecessarily.
  - Extensible: scaling (Phase 5), metrics (Phase 6), scalability (Phase 7),
    failover (Phase 8).

Lifecycle (Phase 7)
--------------------
  not_started  →  (initialize)           →  ready
  ready        →  [run_scaling]          →  ready   (optional Phase 5)
  ready        →  (run_algorithm)        →  completed
  completed    →  [compute_metrics]      →  completed  (auto in run_algorithm)
  completed    →  [run_comparison]       →  completed  (optional Phase 6)
  completed    →  [run_scalability_test] →  completed  (optional Phase 7)
  any          →  (reset)               →  not_started
"""

from typing import List, Optional, Dict, Any
from simulation.vm   import VM,   create_vms
from simulation.task import Task, STATUS_PENDING, STATUS_RUNNING, STATUS_COMPLETED
from simulation.workload import generate_tasks, calculate_total_workload

# ── Simulation status constants ───────────────────────────────────────────────
SIM_NOT_STARTED = "not_started"
SIM_READY       = "ready"
SIM_RUNNING     = "running"
SIM_COMPLETED   = "completed"


class SimulationEngine:
    """
    Central simulation state container and coordinator.

    Attributes
    ----------
    vms                  : List[VM]                  — All VMs in the cluster
    tasks                : List[Task]                — All tasks in the workload
    status               : str                       — Lifecycle state
    num_vms              : int                       — Configured VM count (initial)
    num_tasks            : int                       — Configured task count
    algorithm            : str                       — Selected algorithm name
    vm_capacity          : int                       — Processing capacity per VM
    algorithm_result     : dict | None               — Result from the last algorithm run
    scaling_listener     : AutoScalingListener | None — Scaling state (Phase 5)
    current_metrics      : PerformanceMetrics | None  — Metrics for current run (Phase 6)
    comparison_results   : dict | None               — {algo_name: PerformanceMetrics} (Phase 6)
    scalability_results  : list | None               — Phase 7 multi-workload results
    failover_manager     : FailoverManager | None     — Phase 8 failover state
    """

    def __init__(self) -> None:
        self.vms               : List[VM]       = []
        self.tasks             : List[Task]     = []
        self.status            : str            = SIM_NOT_STARTED
        self.num_vms           : int            = 0
        self.num_tasks         : int            = 0
        self.algorithm         : str            = ""
        self.vm_capacity       : int            = 100
        self.algorithm_result  : Optional[dict] = None
        self.scaling_listener                   = None  # AutoScalingListener | None
        self.current_metrics                    = None  # PerformanceMetrics | None
        self.comparison_results: Optional[Dict] = None  # Phase 6
        self.scalability_results: Optional[List]= None  # Phase 7
        self.failover_manager                   = None  # FailoverManager | None  (Phase 8)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def initialize(self, num_vms: int, num_tasks: int, algorithm: str,
                   vm_capacity: int = 100, seed: int = 42) -> None:
        self.num_vms          = num_vms
        self.num_tasks        = num_tasks
        self.algorithm        = algorithm
        self.vm_capacity      = vm_capacity
        self.algorithm_result = None
        self.scaling_listener = None
        self.current_metrics  = None
        self.comparison_results = None

        self.vms   = create_vms(num_vms, base_capacity=vm_capacity)
        self.tasks = generate_tasks(num_tasks, seed=seed)
        self.status = SIM_READY

    def run_scaling(
        self,
        scale_up_threshold   : float = 70.0,
        scale_down_threshold : float = 30.0,
        min_vms              : int   = 2,
        max_vms              : int   = 10,
    ):
        """Phase 5 — Run the Automated Scaling Listener before the algorithm."""
        from simulation.scaling import AutoScalingListener
        listener = AutoScalingListener(
            scale_up_threshold   = scale_up_threshold,
            scale_down_threshold = scale_down_threshold,
            min_vms              = min_vms,
            max_vms              = max_vms,
            vm_capacity          = self.vm_capacity,
        )
        listener.evaluate_and_scale(self.vms, self.tasks)
        self.scaling_listener = listener
        return listener

    def run_algorithm(self) -> Dict[str, Any]:
        """
        Execute the selected load balancing algorithm and compute metrics.

        After assignment, automatically calls compute_current_metrics() so
        the Performance Metrics section always has fresh data.
        """
        if self.status not in (SIM_READY, SIM_COMPLETED):
            raise ValueError(
                f"Cannot run algorithm: simulation is in state '{self.status}'. "
                "Call initialize() first."
            )

        algo = self.algorithm.lower()
        if "round robin" in algo:
            from algorithms.round_robin import run_round_robin
            result = run_round_robin(self.vms, self.tasks)
        elif "throttled" in algo:
            from algorithms.throttled import run_throttled
            result = run_throttled(self.vms, self.tasks)
        else:
            raise ValueError(f"Unknown algorithm: '{self.algorithm}'")

        self.algorithm_result = result
        self.status = SIM_COMPLETED

        # Phase 6 — auto-compute metrics after every run
        self.current_metrics = self._compute_metrics_from_state(
            self.vms, self.tasks, self.algorithm
        )
        return result

    def compute_current_metrics(self):
        """Explicitly (re-)compute metrics from current state."""
        self.current_metrics = self._compute_metrics_from_state(
            self.vms, self.tasks, self.algorithm
        )
        return self.current_metrics

    def run_comparison(
        self,
        num_vms              : int   = 4,
        num_tasks            : int   = 100,
        vm_capacity          : int   = 100,
        seed                 : int   = 42,
        scaling_enabled      : bool  = True,
        scale_up_threshold   : float = 70.0,
        scale_down_threshold : float = 30.0,
        min_vms              : int   = 2,
        max_vms              : int   = 10,
    ) -> Dict:
        """
        Phase 6 — Run both algorithms on an IDENTICAL workload and compare.

        Both algorithms receive:
          - Same canonical task list (deep copied from seed-deterministic generation)
          - Same initial VM count
          - Same scaling thresholds (when scaling_enabled=True)
          - Same VM capacity

        Results are stored in self.comparison_results as:
            { "Round Robin (Static)": PerformanceMetrics,
              "Throttled (Dynamic)":  PerformanceMetrics }

        This method does NOT touch self.vms, self.tasks, or self.status —
        it runs on temporary copies so the main dashboard state is preserved.
        """
        import copy
        from algorithms.round_robin import run_round_robin
        from algorithms.throttled   import run_throttled
        from simulation.scaling     import AutoScalingListener

        ALGO_RR = "Round Robin (Static)"
        ALGO_TH = "Throttled (Dynamic)"

        # ── Generate ONE canonical task list ───────────────────────────────────
        canonical_tasks = generate_tasks(num_tasks, seed=seed)

        scaling_kwargs = dict(
            scale_up_threshold   = scale_up_threshold,
            scale_down_threshold = scale_down_threshold,
            min_vms              = min_vms,
            max_vms              = max_vms,
            vm_capacity          = vm_capacity,
        )

        comparison: Dict = {}

        for algo_name, algo_fn in [(ALGO_RR, run_round_robin), (ALGO_TH, run_throttled)]:
            # Fresh VMs and a deep copy of the canonical tasks
            tmp_vms   = create_vms(num_vms, base_capacity=vm_capacity)
            tmp_tasks = copy.deepcopy(canonical_tasks)

            # Apply scaling (deterministic — same workload → same result)
            if scaling_enabled:
                listener = AutoScalingListener(**scaling_kwargs)
                listener.evaluate_and_scale(tmp_vms, tmp_tasks)

            # Run the algorithm
            algo_fn(tmp_vms, tmp_tasks)

            # Compute metrics
            m = self._compute_metrics_from_state(tmp_vms, tmp_tasks, algo_name)
            comparison[algo_name] = m

        self.comparison_results = comparison
        return comparison

    # ── Internal metric computation ───────────────────────────────────────────

    @staticmethod
    def _compute_metrics_from_state(vms, tasks, algorithm: str):
        """Delegate to simulation.metrics.compute_metrics()."""
        from simulation.metrics import compute_metrics
        return compute_metrics(vms, tasks, algorithm)

    def run_scalability_test(
        self,
        task_counts          : List[int] = None,
        num_vms              : int       = 4,
        vm_capacity          : int       = 100,
        seed                 : int       = 42,
        scaling_enabled      : bool      = True,
        scale_up_threshold   : float     = 70.0,
        scale_down_threshold : float     = 30.0,
        min_vms              : int       = 2,
        max_vms              : int       = 10,
    ) -> List[Dict]:
        """
        Phase 7 — Workload & Scalability Testing.

        Runs both algorithms across multiple workload sizes on IDENTICAL
        canonical task lists.  For each workload size:
          1. Generate ONE canonical task list (deterministic seed).
          2. Deep-copy for Round Robin and for Throttled.
          3. Create fresh VM pools for each.
          4. Apply identical scaling (deterministic — workload-driven).
          5. Run Round Robin / Throttled independently.
          6. Compute metrics using Phase 6 compute_metrics().

        Parameters
        ----------
        task_counts          : Workload sizes, default [10, 50, 100, 500]
        num_vms              : Initial VM count for every scenario
        vm_capacity          : Processing capacity per VM (default 100)
        seed                 : Deterministic seed for workload generation
        scaling_enabled      : Whether to run the Automated Scaling Listener
        scale_up_threshold   : Pressure % threshold to add a VM
        scale_down_threshold : Pressure % threshold to remove a VM
        min_vms              : Minimum VMs the listener will scale to
        max_vms              : Maximum VMs the listener will scale to

        Returns
        -------
        List[Dict] — One dict per (task_count, algorithm) pair, containing
                     the PerformanceMetrics plus scaling metadata.
                     Stored in self.scalability_results.

        Notes
        -----
        Does NOT touch self.vms, self.tasks, or self.status — runs entirely
        on temporary objects so the main dashboard state is preserved.
        """
        import copy
        from algorithms.round_robin import run_round_robin
        from algorithms.throttled   import run_throttled
        from simulation.scaling     import AutoScalingListener

        if task_counts is None:
            task_counts = [10, 50, 100, 500]

        ALGO_RR = "Round Robin (Static)"
        ALGO_TH = "Throttled (Dynamic)"

        scaling_kwargs = dict(
            scale_up_threshold   = scale_up_threshold,
            scale_down_threshold = scale_down_threshold,
            min_vms              = min_vms,
            max_vms              = max_vms,
            vm_capacity          = vm_capacity,
        )

        results: List[Dict] = []

        for n_tasks in task_counts:
            # ── Generate ONE canonical task list for this workload size ────────
            canonical_tasks = generate_tasks(n_tasks, seed=seed)

            for algo_name, algo_fn in [(ALGO_RR, run_round_robin), (ALGO_TH, run_throttled)]:
                tmp_vms   = create_vms(num_vms, base_capacity=vm_capacity)
                tmp_tasks = copy.deepcopy(canonical_tasks)

                vms_added   = 0
                vms_removed = 0
                initial_pressure = 0.0
                final_pressure   = 0.0

                if scaling_enabled:
                    listener = AutoScalingListener(**scaling_kwargs)
                    listener.evaluate_and_scale(tmp_vms, tmp_tasks)
                    vms_added        = listener.vms_added
                    vms_removed      = listener.vms_removed
                    initial_pressure = listener.initial_pressure
                    final_pressure   = listener.final_pressure

                # Run load balancing algorithm
                algo_fn(tmp_vms, tmp_tasks)

                # Compute metrics via Phase 6 function (unchanged)
                m = self._compute_metrics_from_state(tmp_vms, tmp_tasks, algo_name)

                results.append({
                    "tasks"             : n_tasks,
                    "algorithm"         : algo_name,
                    "seed"              : seed,
                    "initial_vms"       : num_vms,
                    "final_vms"         : m.active_vm_count,
                    "vms_added"         : vms_added,
                    "vms_removed"       : vms_removed,
                    "scaling_enabled"   : scaling_enabled,
                    "initial_pressure"  : round(initial_pressure, 1),
                    "final_pressure"    : round(final_pressure, 1),
                    "metrics"           : m,        # full PerformanceMetrics object
                    # Flat copies of key fields for table/chart convenience
                    "total_workload"    : m.total_workload,
                    "makespan"          : m.makespan,
                    "avg_response_time" : m.average_response_time,
                    "max_response_time" : m.maximum_response_time,
                    "throughput"        : m.throughput,
                    "cluster_util"      : m.cluster_utilization,
                    "load_imbalance"    : m.load_imbalance,
                    "norm_imbalance"    : m.normalized_imbalance,
                })

        self.scalability_results = results
        return results

    def run_algorithm_with_failover(
        self,
        fail_vm_id          : int,
        failure_after_tasks : int,
    ) -> Dict[str, Any]:
        """
        Phase 8 — Run the selected algorithm with a mid-run VM failure.

        Wraps the existing algorithm (run_round_robin / run_throttled) via
        FailoverManager.run_with_failover(), which splits the task list at
        the failure point, calls vm.fail() on the target VM, then continues
        scheduling on remaining available VMs using the same algorithm.

        Neither algorithm is modified — they already skip unavailable VMs.

        Parameters
        ----------
        fail_vm_id          : VM ID to fail (1-based integer, e.g. 2 for VM-2)
        failure_after_tasks : Fail after this many tasks (0 = before any task)

        Side effects
        ------------
        - engine.vms            — target VM has available=False, status=FAILED
        - engine.failover_manager — populated with events and summary
        - engine.current_metrics  — computed from post-failover VM/task state
        - engine.algorithm_result — result dict from the combined run
        - engine.status           — set to SIM_COMPLETED
        """
        if self.status not in (SIM_READY, SIM_COMPLETED):
            raise ValueError(
                f"Cannot run with failover: simulation is in state '{self.status}'. "
                "Call initialize() first."
            )

        from simulation.failover import FailoverManager

        algo = self.algorithm.lower()
        if "round robin" in algo:
            from algorithms.round_robin import run_round_robin
            algo_fn = run_round_robin
        elif "throttled" in algo:
            from algorithms.throttled import run_throttled
            algo_fn = run_throttled
        else:
            raise ValueError(f"Unknown algorithm: '{self.algorithm}'")

        fm = FailoverManager(
            fail_vm_id          = fail_vm_id,
            failure_after_tasks = failure_after_tasks,
        )

        result = fm.run_with_failover(self.vms, self.tasks, algo_fn)

        self.failover_manager = fm
        self.algorithm_result = result
        self.status           = SIM_COMPLETED

        # Phase 6 metrics — computed after failover (failed VM excluded automatically)
        self.current_metrics = self._compute_metrics_from_state(
            self.vms, self.tasks, self.algorithm
        )
        return result

    def reset(self) -> None:
        """Clear all simulation and metrics state (Phases 1–8)."""
        self.vms                = []
        self.tasks              = []
        self.status             = SIM_NOT_STARTED
        self.num_vms            = 0
        self.num_tasks          = 0
        self.algorithm          = ""
        self.algorithm_result   = None
        self.scaling_listener   = None
        self.current_metrics    = None    # Phase 6
        self.comparison_results = None    # Phase 6
        self.scalability_results = None   # Phase 7
        self.failover_manager   = None    # Phase 8


    # ── Metrics (computed from current state) ─────────────────────────────────

    @property
    def total_tasks(self) -> int:
        return len(self.tasks)

    @property
    def pending_tasks(self) -> int:
        return sum(1 for t in self.tasks if t.status == STATUS_PENDING)

    @property
    def running_tasks(self) -> int:
        return sum(1 for t in self.tasks if t.status == STATUS_RUNNING)

    @property
    def completed_tasks(self) -> int:
        return sum(1 for t in self.tasks if t.status == STATUS_COMPLETED)

    @property
    def active_vm_count(self) -> int:
        """VMs that are available and not in Failed state (accounts for scaling)."""
        from simulation.vm import STATUS_FAILED
        return sum(1 for v in self.vms if v.available and v.status != STATUS_FAILED)

    @property
    def workload_percent(self) -> float:
        """
        Simulated workload pressure as a percentage (uncapped).

        Formula:
            Pressure % = (total processing units of all tasks)
                         ÷ (active VMs × VM capacity)
                         × 100

        Uses the actual active VM count (accounts for scaling).
        Values above 100% are expected when cumulative task demand exceeds
        a single VM's capacity — this reflects assigned workload demand vs
        cluster capacity, NOT real CPU utilization.

        Consistent with AutoScalingListener._pressure().
        """
        if not self.vms:
            return 0.0
        total_demand   = calculate_total_workload(self.tasks)
        active_count   = self.active_vm_count
        total_capacity = active_count * self.vm_capacity
        if total_capacity == 0:
            return 0.0
        return round((total_demand / total_capacity) * 100, 1)

    # ── Data accessors (used by the dashboard) ────────────────────────────────

    def get_vm_dicts(self) -> List[Dict[str, Any]]:
        """Return all VMs as list of dicts (for display tables)."""
        return [v.to_dict() for v in self.vms]

    def get_task_dicts(self, max_rows: int = 200) -> List[Dict[str, Any]]:
        """
        Return tasks as list of dicts (for display tables).
        Limits rows for readability when task count is large.
        """
        return [t.to_dict() for t in self.tasks[:max_rows]]

    def get_vm_by_id(self, vm_id: int) -> Optional[VM]:
        """Look up a VM by its numeric ID."""
        for v in self.vms:
            if v.vm_id == vm_id:
                return v
        return None

    def get_summary(self) -> Dict[str, Any]:
        """Return a high-level summary dict for the dashboard header metrics."""
        return {
            "status"          : self.status,
            "num_vms"         : self.num_vms,
            "active_vms"      : self.active_vm_count,
            "total_tasks"     : self.total_tasks,
            "pending_tasks"   : self.pending_tasks,
            "running_tasks"   : self.running_tasks,
            "completed_tasks" : self.completed_tasks,
            "workload_percent": self.workload_percent,
            "algorithm"       : self.algorithm,
        }

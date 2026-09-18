"""
app.py — Load Balancing Simulation Dashboard.

Phase 10: Final UI Polish & Submission Readiness
  - Reordered sections for logical presentation flow
  - Enhanced contrast for section titles and empty states
  - Streamlined empty state visuals across metrics and comparisons
  - Polished Algorithm Comparison descriptions
  - Final visual check for college project presentation

Previous phases:
  Phase 1 — Project structure & dashboard UI
  Phase 2 — VM model, Task model, Workload generator, Simulation engine
  Phase 3 — Round Robin Static Load Balancing
  Phase 4 — Throttled Dynamic Load Balancing
  Phase 5 — Automated Scaling Listener
  Phase 5.1 — Consistency & Terminology Cleanup
  Phase 6 — Performance Metrics & Quantitative Comparison
  Phase 6.1 — Final UI Cleanup
  Phase 7 — Workload & Scalability Testing
  Phase 8 — VM Failure & Failover
"""

import math
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go

# ── Simulation engine ─────────────────────────────────────────────────────────
from simulation.engine import (
    SimulationEngine, SIM_NOT_STARTED, SIM_READY, SIM_COMPLETED
)
from simulation.vm import STATUS_IDLE, STATUS_BUSY, STATUS_FAILED

# ── Algorithm identifier ──────────────────────────────────────────────────────
ALGO_RR        = "Round Robin (Static)"
ALGO_THROTTLED = "Throttled (Dynamic)"

# ─────────────────────────────────────────────────────────────────────────────
# Page configuration — must be the first Streamlit call
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Load Balancing Simulation",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Custom CSS — Phase 1 style preserved + Phase 3 additions
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
body { font-family: 'Segoe UI', sans-serif; }

/* Header banner */
.header-banner {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    padding: 2rem 2.5rem; border-radius: 12px;
    margin-bottom: 1.5rem; border-left: 5px solid #e94560;
}
.header-banner h1 { color:#fff; font-size:2rem; font-weight:700; margin:0 0 0.3rem 0; }
.header-banner p  { color:#a8b2d8; font-size:1rem; margin:0; }
.phase-badge {
    display:inline-block; background:#e94560; color:white;
    font-size:0.75rem; font-weight:600; padding:0.2rem 0.7rem;
    border-radius:20px; margin-top:0.6rem; letter-spacing:0.05em;
}

/* Section headings */
.section-title {
    font-size:1.05rem; font-weight:700; color:#e2e8f0;
    border-bottom:2px solid #e94560; padding-bottom:0.3rem;
    margin:1.5rem 0 1rem 0;
}

/* Metric cards */
.metric-card {
    background:#f8f9fb; border:1px solid #e0e4ef;
    border-radius:10px; padding:1rem 1.2rem; text-align:center;
}
.metric-card .metric-label {
    font-size:0.78rem; color:#6b7280; text-transform:uppercase;
    letter-spacing:0.06em; margin-bottom:0.4rem;
}
.metric-card .metric-value { font-size:1.4rem; font-weight:700; color:#1f2937; }
.metric-card .metric-sub   { font-size:0.75rem; color:#9ca3af; font-style:italic; margin-top:0.2rem; }

/* VM status cards */
.vm-card { border-radius:10px; padding:0.9rem 1rem; text-align:center; margin-bottom:0.5rem; }
.vm-card-idle   { background:#f0f4ff; border:1px solid #c7d2fe; color:#374151; }
.vm-card-busy   { background:#f0fdf4; border:1px solid #86efac; color:#374151; }
.vm-card-failed { background:#fff1f2; border:1px solid #fda4af; color:#374151; }
.vm-card .vm-name   { font-weight:700; font-size:0.95rem; }
.vm-card-idle   .vm-name { color:#3730a3; }
.vm-card-busy   .vm-name { color:#166534; }
.vm-card-failed .vm-name { color:#9f1239; }
.vm-card .vm-status { font-size:0.78rem; margin-top:0.2rem; }
.vm-card .vm-meta   { font-size:0.72rem; color:#4b5563; margin-top:0.3rem; }
.vm-card .vm-load-bar-wrap {
    background:#e5e7eb; border-radius:4px; height:6px; margin-top:0.4rem; overflow:hidden;
}
.vm-card .vm-load-bar { height:100%; border-radius:4px; background:#22c55e; }

/* Placeholder boxes */
.placeholder-box {
    border:1px dashed #64748b; border-radius:8px; padding:2rem;
    color:#94a3b8; font-size:0.9rem; text-align:center;
}

/* Algorithm info banner (Phase 3) */
.algo-info-banner {
    border-radius:10px; padding:0.9rem 1.2rem;
    margin-bottom:0.5rem; display:flex; align-items:flex-start; gap:0.8rem;
}
.algo-info-rr       { background:#eff6ff; border:1px solid #bfdbfe; }
.algo-info-throttled{ background:#fff7ed; border:1px solid #fed7aa; }
.algo-info-banner .ai-icon { font-size:1.4rem; }
.algo-info-banner .ai-title { font-weight:700; font-size:0.9rem; margin-bottom:0.15rem; }
.algo-info-rr        .ai-title { color:#1e40af; }
.algo-info-throttled .ai-title { color:#9a3412; }
.algo-info-banner .ai-desc { font-size:0.8rem; color:#4b5563; }

/* Scaling & failover */
.feature-card {
    background:#fff7ed; border:1px solid #fed7aa;
    border-radius:10px; padding:1rem 1.2rem; text-align:center;
}
.feature-card .feature-title { font-weight:700; color:#9a3412; font-size:0.85rem; }
.feature-card .feature-note  { color:#c2410c; font-size:0.75rem; margin-top:0.2rem; font-style:italic; }

/* Empty states */
.empty-state-box {
    border:1px dashed #64748b; border-radius:8px; padding:1rem;
    color:#94a3b8; font-size:0.9rem; text-align:center;
}
.empty-state-box strong { color:#cbd5e1; }

/* Algorithm comparison cards */
.algo-card { background:#f0fdf4; border:1px solid #bbf7d0; border-radius:10px; padding:1.2rem; }
.algo-card.dynamic { background:#fdf4ff; border-color:#e9d5ff; }
.algo-card .algo-title { font-size:1rem; font-weight:700; color:#166534; margin-bottom:0.4rem; }
.algo-card.dynamic .algo-title { color:#6b21a8; }
.algo-card .algo-type {
    font-size:0.75rem; font-weight:600; text-transform:uppercase;
    letter-spacing:0.08em; color:#4ade80; margin-bottom:0.6rem;
}
.algo-card.dynamic .algo-type { color:#c084fc; }
.algo-card ul { color:#374151; font-size:0.82rem; padding-left:1.2rem; margin:0.4rem 0 0.6rem 0; }
.algo-card .algo-placeholder { font-size:0.75rem; color:#9ca3af; font-style:italic; }
/* Scaling event cards (Phase 5) */
.scaling-event-card {
    border-radius:8px; padding:0.6rem 0.9rem; margin-bottom:0.4rem;
    font-size:0.82rem; border-left:4px solid;
}
.scaling-event-up   { background:#f0fdf4; border-color:#22c55e; color:#166534; }
.scaling-event-down { background:#fef9c3; border-color:#ca8a04; color:#713f12; }
.scaling-event-card .event-time { color:#9ca3af; font-size:0.75rem; margin-right:0.4rem; }
.scaling-event-card .event-type { font-weight:700; margin-right:0.3rem; }
.scaling-event-card .event-vm   { font-weight:700; }
.scaling-event-card .event-reason { font-size:0.75rem; color:#6b7280; margin-top:0.2rem; }

/* Active feature cards (Phase 5) */
.feature-card-active {
    background:#f0fdf4 !important; border:1px solid #86efac !important;
}
.feature-card-active .feature-title { color:#166534 !important; }
.feature-stat { font-size:0.85rem; font-weight:700; margin:0.3rem 0 0.1rem 0; }
.feature-detail { font-size:0.72rem; color:#374151; margin-top:0.2rem; line-height:1.5; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Session State — initialise simulation engine once per session
# ─────────────────────────────────────────────────────────────────────────────
if "engine" not in st.session_state:
    st.session_state.engine = SimulationEngine()

engine: SimulationEngine = st.session_state.engine


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar — Configuration Panel
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Simulation Configuration")
    st.markdown("---")

    st.markdown("**Load Balancing Algorithm**")
    algorithm = st.radio(
        label="Algorithm",
        options=[ALGO_RR, ALGO_THROTTLED],
        index=0,
        help="Round Robin (Static) vs Throttled (Dynamic).",
        label_visibility="collapsed",
    )

    st.markdown("---")

    num_vms = st.slider(
        "Number of VMs",  min_value=2, max_value=10, value=4, step=1,
        help="Initial number of VMs. The Scaling Listener may add or remove VMs before task assignment.",
    )
    num_tasks = st.slider(
        "Number of Tasks", min_value=10, max_value=500, value=100, step=10,
        help="Total number of tasks to distribute across VMs.",
    )

    st.markdown("---")

    # ── Scaling Configuration (Phase 5) ──────────────────────────────────────
    st.markdown("**⚡ Automated Scaling Listener**")
    scaling_enabled = st.toggle(
        "Enable Auto-Scaling",
        value=True,
        help="When ON, the listener evaluates workload before task assignment and adjusts the VM pool.",
    )

    if scaling_enabled:
        with st.expander("⚙️ Scaling Thresholds", expanded=False):
            scale_up_pct = st.slider(
                "Scale-Up Threshold (%)", min_value=50, max_value=95, value=70, step=5,
                help="Add a VM when workload pressure exceeds this % of cluster capacity.",
            )
            scale_down_pct = st.slider(
                "Scale-Down Threshold (%)", min_value=5, max_value=49, value=30, step=5,
                help="Remove an idle VM when workload pressure drops below this %.",
            )
            min_vms_cfg = st.slider(
                "Minimum VMs", min_value=2, max_value=5, value=2,
                help="The listener will never scale below this VM count.",
            )
            max_vms_cfg = st.slider(
                "Maximum VMs", min_value=5, max_value=10, value=10,
                help="The listener will never scale above this VM count.",
            )
    else:
        scale_up_pct   = 70
        scale_down_pct = 30
        min_vms_cfg    = 2
        max_vms_cfg    = 10

    st.markdown("---")

    # ── Phase 8 — VM Failure & Failover Controls ─────────────────────────────
    st.markdown("**🛡️ VM Failure & Failover**")
    failure_enabled = st.toggle(
        "Simulate VM Failure",
        value=False,
        help=(
            "When ON, one VM will be failed mid-simulation after a configurable "
            "number of tasks. Failover routes remaining tasks to healthy VMs. "
            "Demonstrates fault tolerance in a cloud cluster."
        ),
    )
    if failure_enabled:
        fail_vm_id = st.selectbox(
            "VM to Fail",
            options=list(range(1, num_vms + 1)),
            format_func=lambda x: f"VM-{x}",
            help="Which VM will fail. Must be within the configured VM count.",
        )
        max_fail_after = max(1, num_tasks - 1)
        failure_after = st.slider(
            "Fail After (tasks)",
            min_value=0,
            max_value=max_fail_after,
            value=min(num_tasks // 2, max_fail_after),
            step=1,
            help=(
                "VM fails after this many tasks are assigned. "
                "Tasks after this point are redirected to healthy VMs."
            ),
        )
        st.caption(
            f"VM-{fail_vm_id} will fail after task {failure_after}. "
            f"Tasks {failure_after + 1}–{num_tasks} will be redirected."
        )
    else:
        fail_vm_id    = 1
        failure_after = 0

    st.markdown("---")
    st.markdown("**🎮 Actions**")

    start_btn = st.button(
        "▶  Start Simulation",
        use_container_width=True,
        type="primary",
        help="Initialises VMs/tasks, optionally scales the cluster, then runs the load balancer.",
    )

    if start_btn:
        try:
            engine.initialize(
                num_vms=num_vms,
                num_tasks=num_tasks,
                algorithm=algorithm,
            )
            # Phase 5 — run scaling listener BEFORE the load balancer
            if scaling_enabled:
                engine.run_scaling(
                    scale_up_threshold   = float(scale_up_pct),
                    scale_down_threshold = float(scale_down_pct),
                    min_vms              = min_vms_cfg,
                    max_vms              = max_vms_cfg,
                )

            # Phase 8 — run with failover OR normal run
            if failure_enabled:
                engine.run_algorithm_with_failover(
                    fail_vm_id          = fail_vm_id,
                    failure_after_tasks = failure_after,
                )
                fm = engine.failover_manager
                st.success(
                    f"✅ Simulation with Failover complete!  \n"
                    f"**{engine.active_vm_count} active VM(s)** · "
                    f"**{num_tasks} tasks** total  \n"
                    f"🔴 **{fm.failed_vm_name}** failed after task {fm.tasks_before_failure} · "
                    f"{fm.tasks_after_failure} task(s) redirected."
                )
            else:
                engine.run_algorithm()
                algo_short = "Round Robin" if "round robin" in algorithm.lower() else "Throttled"
                sl = engine.scaling_listener
                scale_note = ""
                if sl and (sl.vms_added or sl.vms_removed):
                    scale_note = (
                        f"  \n🔼 +{sl.vms_added} VM(s) added · 🔽 -{sl.vms_removed} VM(s) removed"
                    )
                st.success(
                    f"✅ {algo_short} complete!  \n"
                    f"**{engine.active_vm_count} active VMs** · **{num_tasks} Tasks** assigned."
                    + scale_note
                )
        except Exception as exc:
            st.error(f"Simulation error: {exc}")

    # ── Reset Simulation ──────────────────────────────────────────────────────
    reset_btn = st.button(
        "🔄  Reset Simulation",
        use_container_width=True,
        type="secondary",
        help="Clears all VMs, tasks, scaling state, metrics, comparison, and failover.",
    )
    if reset_btn:
        engine.reset()
        st.info("Simulation has been reset.", icon="🔄")

    st.markdown("---")

    # ── Run Comparison (Phase 6) ───────────────────────────────────────────────
    st.markdown("**⚖️ Algorithm Comparison**")
    cmp_tasks = st.slider(
        "Comparison Tasks",
        min_value=10, max_value=500, value=100, step=10,
        help="Number of tasks for the fair comparison run (seed=42).",
    )
    cmp_vms = st.slider(
        "Comparison VMs",
        min_value=2, max_value=10, value=num_vms,
        help="Initial VM count for the comparison run.",
    )
    compare_btn = st.button(
        "📊  Run Comparison",
        use_container_width=True,
        type="primary",
        help=(
            "Runs Round Robin AND Throttled on the SAME generated workload "
            "(seed=42) with the same VMs and scaling settings."
        ),
    )
    if compare_btn:
        try:
            engine.run_comparison(
                num_vms              = cmp_vms,
                num_tasks            = cmp_tasks,
                vm_capacity          = 100,
                seed                 = 42,
                scaling_enabled      = scaling_enabled,
                scale_up_threshold   = float(scale_up_pct),
                scale_down_threshold = float(scale_down_pct),
                min_vms              = min_vms_cfg,
                max_vms              = max_vms_cfg,
            )
            st.success(
                f"✅ Comparison complete! ({cmp_vms} VMs, {cmp_tasks} tasks, seed=42, "
                f"scaling={'ON' if scaling_enabled else 'OFF'})"
            )
        except Exception as exc:
            st.error(f"Comparison error: {exc}")

    st.markdown("---")

    # Status indicator
    status_labels = {
        SIM_NOT_STARTED : "⬜ Not started",
        SIM_READY       : "🟡 Ready (pending run)",
        SIM_COMPLETED   : "🟢 Completed",
    }
    st.caption(f"**Status:** {status_labels.get(engine.status, engine.status)}")
    if engine.status == SIM_COMPLETED:
        st.caption(f"**Algorithm:** {engine.algorithm}")
    has_cmp  = engine.comparison_results  is not None
    has_scal = engine.scalability_results is not None
    has_fo   = engine.failover_manager    is not None and getattr(engine.failover_manager, "failure_triggered", False)
    st.caption(
        "Round Robin & Throttled ✅  \n"
        "Auto-Scaling ✅  \n"
        f"Performance Metrics ✅ {'· Comparison ✅' if has_cmp else ''}  \n"
        f"Scalability Testing {'✅' if has_scal else '(use Run Scalability)'}  \n"
        f"VM Failure & Failover {'✅' if has_fo else '(enable above)'}"
    )

    st.markdown("---")

    # ── Phase 7 — Scalability Test Controls ─────────────────────────────────
    st.markdown("**📈 Workload & Scalability Testing**")

    _WORKLOAD_SCENARIOS = {
        "Low    (10 tasks)"     : [10],
        "Medium (50 tasks)"     : [50],
        "High   (100 tasks)"    : [100],
        "Extreme (500 tasks)"   : [500],
        "Full progression (all)": [10, 50, 100, 500],
    }
    scal_scenario = st.selectbox(
        "Workload Scenario",
        options=list(_WORKLOAD_SCENARIOS.keys()),
        index=4,  # default: Full progression
        help="Choose a single workload level or run the full 10/50/100/500 progression.",
    )
    scal_vms = st.slider(
        "Initial VMs (scalability)",
        min_value=2, max_value=10, value=num_vms,
        help="Starting VM count for the scalability test. Scaling Listener may adjust.",
    )

    scal_btn = st.button(
        "📈  Run Scalability Test",
        use_container_width=True,
        type="primary",
        help=(
            "Runs both Round Robin AND Throttled across the selected workload(s) "
            "using identical task lists (seed=42). Does NOT affect main simulation state."
        ),
    )
    if scal_btn:
        task_counts = _WORKLOAD_SCENARIOS[scal_scenario]
        try:
            engine.run_scalability_test(
                task_counts          = task_counts,
                num_vms              = scal_vms,
                vm_capacity          = 100,
                seed                 = 42,
                scaling_enabled      = scaling_enabled,
                scale_up_threshold   = float(scale_up_pct),
                scale_down_threshold = float(scale_down_pct),
                min_vms              = min_vms_cfg,
                max_vms              = max_vms_cfg,
            )
            n_runs = len(engine.scalability_results)
            st.success(
                f"✅ Scalability test complete! ({n_runs // 2} workload sizes × 2 algorithms, "
                f"seed=42, scaling={'ON' if scaling_enabled else 'OFF'})"
            )
        except Exception as exc:
            st.error(f"Scalability test error: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
sim_active = engine.status in (SIM_READY, SIM_COMPLETED)
sim_done   = engine.status == SIM_COMPLETED


def _vm_card_class(status: str) -> str:
    m = {STATUS_IDLE: "idle", STATUS_BUSY: "busy", STATUS_FAILED: "failed"}
    return f"vm-card vm-card-{m.get(status, 'idle')}"


def _status_icon(status: str) -> str:
    return {STATUS_IDLE: "⬜", STATUS_BUSY: "🟢", STATUS_FAILED: "🔴"}.get(status, "⬜")


# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="header-banner">
    <h1>⚖️ Static vs Dynamic Load Balancing Algorithms</h1>
    <p>Interactive Cloud Load Balancing Simulation & Performance Analysis</p>
</div>
""", unsafe_allow_html=True)

# ── Algorithm info banner ─────────────────────────────────────────────────────
if algorithm == ALGO_RR:
    st.markdown("""
    <div class="algo-info-banner algo-info-rr">
        <div class="ai-icon">🔄</div>
        <div>
            <div class="ai-title">Round Robin — Static Load Balancing</div>
            <div class="ai-desc">
                Tasks are assigned sequentially to VMs in a fixed cyclic order
                <em>without considering current VM workload</em>.
                Simple and deterministic — VM-1 → VM-2 → … → VM-N → VM-1 → …
            </div>
        </div>
    </div>""", unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="algo-info-banner algo-info-throttled">
        <div class="ai-icon">⚡</div>
        <div>
            <div class="ai-title">Throttled Load Balancing — Dynamic Algorithm</div>
            <div class="ai-desc">
                Tasks are assigned to the <em>least-loaded available VM</em> based on
                current accumulated workload. Unlike Round Robin, the algorithm
                re-inspects the VM state table before every assignment decision,
                adapting dynamically to heterogeneous task sizes.
            </div>
        </div>
    </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Section 1 — Cloud Resources
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<p class="section-title">☁️  Cloud Resources</p>', unsafe_allow_html=True)

col1, col2, col3, col4, col5 = st.columns(5)

if sim_active:
    summary = engine.get_summary()
    workload_val  = summary['workload_percent']
    workload_str  = f"{workload_val}%"
    workload_sub  = "Cumulative workload demand ÷ cluster capacity (can exceed 100%)"
    # Show scaling delta in the Active VMs sub-label when scaling ran
    sl = engine.scaling_listener
    if sl and (sl.vms_added or sl.vms_removed):
        delta = sl.vms_added - sl.vms_removed
        delta_str = f"+{delta}" if delta > 0 else str(delta)
        active_sub = (
            f"of {summary['num_vms']} initial · scaled {delta_str} "
            f"({sl.vms_added}↑ {sl.vms_removed}↓)"
        )
    else:
        active_sub = f"of {summary['num_vms']} configured"
    if sim_done:
        tasks_sub = f"{summary['completed_tasks']} completed · {summary['pending_tasks']} pending"
    else:
        tasks_sub = f"{summary['pending_tasks']} pending · awaiting algorithm"
    # Phase 8 — failed VMs
    failed_count = sum(1 for v in engine.vms if v.status == STATUS_FAILED)
    total_created = len(engine.vms)
    failed_sub = (
        f"{engine.failover_manager.failed_vm_name} — failover active"
        if failed_count > 0 and engine.failover_manager and engine.failover_manager.failure_triggered
        else "No VM failures in this run"
    )
    vm_capacity_val = engine.vm_capacity if engine.vms else 100
else:
    summary       = {"active_vms": num_vms, "total_tasks": num_tasks}
    workload_str  = "—"
    workload_sub  = "Start simulation to calculate"
    active_sub    = "Not yet started"
    tasks_sub     = "Not yet started"
    failed_count  = 0
    total_created = num_vms
    failed_sub    = "Simulate VM Failure to test"
    vm_capacity_val = 100

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Active VMs</div>
        <div class="metric-value">{summary['active_vms']}</div>
        <div class="metric-sub">{active_sub}</div>
    </div>""", unsafe_allow_html=True)

with col2:
    failed_color = "color:#e94560;" if failed_count > 0 else ""
    failed_val = failed_count if sim_active else "—"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Failed VMs</div>
        <div class="metric-value" style="{failed_color}">{failed_val}</div>
        <div class="metric-sub">{failed_sub}</div>
    </div>""", unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total Tasks</div>
        <div class="metric-value">{summary['total_tasks']}</div>
        <div class="metric-sub">{tasks_sub}</div>
    </div>""", unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Cluster Workload Pressure</div>
        <div class="metric-value">{workload_str}</div>
        <div class="metric-sub">{workload_sub}</div>
    </div>""", unsafe_allow_html=True)

with col5:
    total_val = total_created if sim_active else num_vms
    cap_sub = f"VM capacity: {vm_capacity_val} units each"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total VMs Created</div>
        <div class="metric-value">{total_val}</div>
        <div class="metric-sub">{cap_sub}</div>
    </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Section 1b — Resource Cluster Visualization
# Uses st.components.v1.html() — see Phase 2 bug-fix notes.
# Phase 3: VM nodes now show task count + load after algorithm runs.
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<p class="section-title">🗺️  Resource Cluster Visualization</p>', unsafe_allow_html=True)

_CLUSTER_CSS = """
<style>
  body { margin:0; padding:0.2rem; font-family:'Segoe UI',sans-serif; background:transparent; }
  .cluster-box {
    background:#f8f9fb; border:1px solid #e0e4ef;
    border-radius:12px; padding:1.2rem 1rem; text-align:center;
  }
  .cluster-label {
    display:inline-block; background:#0f3460; color:#fff;
    padding:0.3rem 1.2rem; border-radius:6px;
    font-size:0.85rem; font-weight:600; margin:0.15rem 0;
  }
  .cluster-lb {
    display:inline-block; background:#e94560; color:#fff;
    padding:0.3rem 1.4rem; border-radius:6px;
    font-size:0.85rem; font-weight:700; margin:0.15rem 0;
  }
  .cluster-arrow { font-size:1.3rem; color:#0f3460; margin:0.1rem 0; line-height:1.4; }
  .vm-nodes { display:flex; flex-wrap:wrap; justify-content:center; gap:8px; margin:0.5rem 0; }
  .vm-node {
    display:inline-flex; flex-direction:column; align-items:center;
    background:#1a1a2e; border:2px solid #6366f1; border-radius:8px;
    padding:0.55rem 0.9rem; font-size:0.78rem; font-weight:600;
    min-width:90px; line-height:1.6;
  }
  .vm-node-idle   { border-color:#6366f1; color:#c7d2fe; }
  .vm-node-busy   { border-color:#22c55e; color:#bbf7d0; }
  .vm-node-failed { border-color:#ef4444; color:#fda4af; }
  .vm-node .vm-tasks-badge {
    margin-top:4px; background:rgba(255,255,255,0.12);
    border-radius:4px; padding:1px 6px; font-size:0.68rem;
    font-weight:700; letter-spacing:0.03em;
  }
  .vm-node .vm-load-text { font-size:0.62rem; opacity:0.75; margin-top:2px; }
  .load-bar-wrap {
    width:100%; background:rgba(255,255,255,0.15);
    border-radius:3px; height:5px; margin-top:4px; overflow:hidden;
  }
  .load-bar { height:100%; border-radius:3px; background:#22c55e; }
  .legend { font-size:0.68rem; color:#9ca3af; margin-top:0.5rem; }
  .sub    { font-size:0.72rem; color:#6b7280; margin-bottom:0.3rem; }
</style>
"""

def _build_vm_node_html(vm) -> str:
    """Build HTML for a single VM node in the cluster diagram."""
    if vm.status == STATUS_IDLE:
        node_cls = "vm-node vm-node-idle"
    elif vm.status == STATUS_BUSY:
        node_cls = "vm-node vm-node-busy"
    else:
        node_cls = "vm-node vm-node-failed"

    icon = _status_icon(vm.status)
    load_pct = vm.load_percent

    # Load bar width capped at 100%
    bar_w = min(load_pct, 100)
    bar_color = "#22c55e" if load_pct < 70 else "#f59e0b" if load_pct < 90 else "#ef4444"

    tasks_label = f"{vm.task_count} task{'s' if vm.task_count != 1 else ''}"

    return (
        f'<div class="{node_cls}">'
        f'{icon} {vm.name}'
        f'<span class="vm-tasks-badge">{tasks_label}</span>'
        f'<span class="vm-load-text">Wkld: {vm.current_load} ({load_pct}%)</span>'
        f'<div class="load-bar-wrap">'
        f'<div class="load-bar" style="width:{bar_w}%;background:{bar_color};"></div>'
        f'</div>'
        f'</div>'
    )


if sim_active and engine.vms:
    algo_label    = engine.algorithm if sim_done else "awaiting run"
    actual_vm_cnt = engine.active_vm_count
    failed_vm_cnt = sum(1 for v in engine.vms if v.status == STATUS_FAILED)
    sl            = engine.scaling_listener
    sub_parts = [
        f"Simulated Cloud Cluster &mdash; {engine.num_tasks} tasks &rarr; {actual_vm_cnt} active VM(s)"
    ]
    if failed_vm_cnt > 0:
        sub_parts.append(f"&nbsp;&mdash;&nbsp;<span style='color:#ef4444;font-weight:700'>&#128308; {failed_vm_cnt} FAILED</span>")
    if sim_done:
        sub_parts.append(f"&mdash; {engine.completed_tasks} tasks completed")
    sub_text = "".join(sub_parts)

    # Phase 9: Show ALL VMs (including FAILED) so the cluster is complete
    visible_vms   = engine.vms   # all VMs — failed ones shown in red
    vm_nodes_html = "".join(_build_vm_node_html(vm) for vm in visible_vms)

    # Scaling listener node (shown when scaling ran)
    if sl:
        sl_detail = (
            f"↑ Threshold: {sl.scale_up_threshold}% &nbsp;|&nbsp; "
            f"↓ Threshold: {sl.scale_down_threshold}%"
        )
        if sl.vms_added or sl.vms_removed:
            sl_detail += (
                f"<br>+{sl.vms_added} VM(s) added &nbsp;·&nbsp; "
                f"-{sl.vms_removed} VM(s) removed"
            )
        listener_html = (
            f'<div><span class="cluster-lb" style="background:#166534;">'
            f'&#9889; Scaling Listener &nbsp;({sl_detail})</span></div>'
            f'<div class="cluster-arrow">&#8595;</div>'
        )
    else:
        listener_html = ""

    total_visible = len(visible_vms)
    html_body = f"""{_CLUSTER_CSS}
<div class="cluster-box">
  <div class="sub">{sub_text}</div>
  <div><span class="cluster-label">&#128229; Incoming Tasks ({engine.num_tasks})</span></div>
  <div class="cluster-arrow">&#8595;</div>
  {listener_html}
  <div><span class="cluster-lb">&#9878; Load Balancer &nbsp;({algo_label})</span></div>
  <div class="cluster-arrow">&#8595;</div>
  <div class="sub">Resource Cluster ({actual_vm_cnt} active · {failed_vm_cnt} failed)</div>
  <div class="vm-nodes">{vm_nodes_html}</div>
  <div class="legend">
    &#11036; Idle &nbsp;|&nbsp; &#128994; Assigned / Loaded &nbsp;|&nbsp; &#128308; Failed
    &nbsp;&mdash;&nbsp;
    {"Task counts &amp; loads reflect " + engine.algorithm + " assignment" if sim_done else "Run simulation to see assignments"}
  </div>
</div>"""

    rows = math.ceil(total_visible / 4)
    # Extra height if scaling listener node is shown
    extra_h = 55 if sl else 0
    components.html(html_body, height=255 + rows * 85 + extra_h, scrolling=False)

else:
    # Pre-simulation static preview
    vm_nodes_preview = "".join(
        f'<div class="vm-node vm-node-idle">'
        f'&#11036; VM-{i+1}'
        f'<span class="vm-tasks-badge">0 tasks</span>'
        f'<span class="vm-load-text">Load: 0 (0%)</span>'
        f'<div class="load-bar-wrap"><div class="load-bar" style="width:0%;"></div></div>'
        f'</div>'
        for i in range(num_vms)
    )
    html_body = f"""{_CLUSTER_CSS}
<div class="cluster-box">
  <div class="sub">Press &#9654; Start Simulation to initialise the cluster</div>
  <div><span class="cluster-label">&#128229; Incoming Tasks ({num_tasks})</span></div>
  <div class="cluster-arrow">&#8595;</div>
  <div><span class="cluster-lb">&#9878; Load Balancer</span></div>
  <div class="cluster-arrow">&#8595;</div>
  <div class="sub">Resource Cluster (preview &mdash; {num_vms} VMs)</div>
  <div class="vm-nodes">{vm_nodes_preview}</div>
  <div class="legend">&#11036; Idle &nbsp;|&nbsp; &#128994; Assigned / Loaded &nbsp;|&nbsp; &#128308; Failed</div>
</div>"""

    rows = math.ceil(num_vms / 4)
    components.html(html_body, height=255 + rows * 85, scrolling=False)


# ─────────────────────────────────────────────────────────────────────────────
# Section 3 — VM Status
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<p class="section-title">🖥️  VM Status</p>', unsafe_allow_html=True)

if sim_active and engine.vms:
    # Phase 9: Show ALL VMs including FAILED — so teachers can see the full cluster state
    all_vms_list = engine.vms
    cols_per_row = min(len(all_vms_list), 4)
    vm_cols = st.columns(max(cols_per_row, 1))
    for idx, vm in enumerate(all_vms_list):
        with vm_cols[idx % cols_per_row]:
            icon    = _status_icon(vm.status)
            css     = _vm_card_class(vm.status)
            bar_pct = min(vm.load_percent, 100)
            bar_col = (
                "#22c55e" if bar_pct < 70 else
                "#f59e0b" if bar_pct < 90 else "#ef4444"
            )
            fm = engine.failover_manager
            is_failed_vm = (
                vm.status == STATUS_FAILED and
                fm and fm.failure_triggered and vm.vm_id == fm.fail_vm_id
            )
            extra_note = (
                '<br><span style="color:#9f1239;font-weight:700">New Tasks After Failure: 0</span>'
                if is_failed_vm else ""
            )
            st.markdown(f"""
            <div class="{css}">
                <div class="vm-name">{icon} {vm.name}</div>
                <div class="vm-status">{vm.display_status}</div>
                <div class="vm-meta">
                    Capacity: {vm.capacity} units<br>
                    Assigned Workload: {vm.current_load} units ({vm.load_percent}% of capacity)<br>
                    Tasks Assigned: {vm.task_count}{extra_note}
                </div>
                <div class="vm-load-bar-wrap">
                    <div class="vm-load-bar"
                         style="width:{bar_pct}%;background:{bar_col};"></div>
                </div>
            </div>""", unsafe_allow_html=True)
            st.write("")
    # Legend
    st.caption("⬜ Idle  |  🟢 Assigned / Loaded  |  🔴 Failed  — bar shows % of capacity used (capped at 100% for display)")
else:
    vm_cols = st.columns(min(num_vms, 4))
    for i in range(num_vms):
        with vm_cols[i % len(vm_cols)]:
            st.markdown(f"""
            <div class="vm-card vm-card-idle">
                <div class="vm-name">⬜ VM-{i + 1}</div>
                <div class="vm-status">Not initialised — press ▶ Start Simulation</div>
            </div>""", unsafe_allow_html=True)
            st.write("")


# ─────────────────────────────────────────────────────────────────────────────
# Section 4 — Task Distribution
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<p class="section-title">📦  Task Distribution</p>', unsafe_allow_html=True)

if sim_active and engine.tasks:
    task_dicts = engine.get_task_dicts(max_rows=200)
    df_tasks   = pd.DataFrame(task_dicts)

    total   = engine.total_tasks
    shown   = len(task_dicts)

    if sim_done:
        info_msg = (
            f"Showing {shown} of {total} tasks · "
            f"{engine.completed_tasks} completed via {engine.algorithm}"
        )
    else:
        info_msg = f"Showing {shown} of {total} tasks · awaiting algorithm"
    st.caption(info_msg)

    # Size distribution summary
    sizes  = [t.size for t in engine.tasks]
    small  = sum(1 for s in sizes if s <= 30)
    medium = sum(1 for s in sizes if 31 <= s <= 70)
    large  = sum(1 for s in sizes if s > 70)

    dc1, dc2, dc3 = st.columns(3)
    with dc1: st.metric("🔵 Small Tasks (≤30 units)",    small,  help="Lightweight")
    with dc2: st.metric("🟡 Medium Tasks (31–70 units)", medium, help="Normal requests")
    with dc3: st.metric("🔴 Large Tasks (>70 units)",    large,  help="Heavy compute")

    st.dataframe(
        df_tasks,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Task"        : st.column_config.TextColumn("Task",        width="small"),
            "Size"        : st.column_config.NumberColumn("Size",      width="small"),
            "Proc. Units" : st.column_config.NumberColumn("Proc. Units", width="small"),
            "Arrival #"   : st.column_config.NumberColumn("Arrival #", width="small"),
            "Status"      : st.column_config.TextColumn("Status",      width="small"),
            "Assigned VM" : st.column_config.TextColumn("Assigned VM", width="small"),
        },
    )
    if total > 200:
        st.caption(f"ℹ️ Displaying first 200 of {total} tasks.")
else:
    st.markdown("""
    <div class="placeholder-box">
        📋  Task table will appear here after pressing ▶ Start Simulation.<br>
        <small>Shows: Task ID · Size · Processing Units · Status · Assigned VM</small>
    </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Section 4b — Assignment Summary (shown after algorithm run)
# Shared display logic; caption adapts to the algorithm used.
# ─────────────────────────────────────────────────────────────────────────────
if sim_done and engine.algorithm_result:
    is_rr        = "round robin" in engine.algorithm.lower()
    is_throttled = "throttled"   in engine.algorithm.lower()

    if is_rr:
        section_title = "📈  Round Robin Assignment Summary"
        caption_note  = (
            "💡 Round Robin distributes tasks cyclically but **does not** account for task "
            "size, so VMs may have different total loads even if task counts are equal."
        )
    else:
        section_title = "⚡  Throttled Assignment Summary"
        caption_note  = (
            "💡 Throttled assigns each task to the **least-loaded VM** at that moment, "
            "so total loads tend to be more balanced than Round Robin — "
            "though task count per VM may be unequal."
        )

    st.markdown(f'<p class="section-title">{section_title}</p>', unsafe_allow_html=True)

    summary_rows = []
    for vm in engine.vms:
        if not vm.available:
            continue   # skip deactivated (scaled-down) VMs
        summary_rows.append({
            "VM"                        : vm.name,
            "Tasks Assigned"            : vm.task_count,
            "Assigned Workload (units)" : vm.current_load,
            "Workload vs Capacity"      : f"{vm.load_percent}%",
            "Capacity (units)"          : vm.capacity,
            "Status"                    : vm.display_status,
        })

    df_summary = pd.DataFrame(summary_rows)
    st.dataframe(df_summary, use_container_width=True, hide_index=True)

    active_loads = [vm.current_load for vm in engine.vms if vm.available]
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        st.metric("Max VM Workload", f"{max(active_loads)} units",
                  help="Highest cumulative assigned workload on any active VM")
    with sc2:
        st.metric("Min VM Workload", f"{min(active_loads)} units",
                  help="Lowest cumulative assigned workload on any active VM")
    with sc3:
        diff = max(active_loads) - min(active_loads)
        st.metric("Workload Imbalance (Max−Min)", f"{diff} units",
                  help="Smaller difference = more balanced distribution across VMs")

    st.caption(caption_note)


# ─────────────────────────────────────────────────────────────────────────────
# Section 2 — Performance Metrics (Phase 6 — real metrics)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<p class="section-title">📊  Performance Metrics</p>', unsafe_allow_html=True)

pm = engine.current_metrics  # PerformanceMetrics | None

pm_cols = st.columns(4)

with pm_cols[0]:
    if pm:
        val_str = f"{pm.cluster_utilization}%"
        sub_str = f"Total workload ÷ (active VMs × makespan) × 100"
    else:
        val_str, sub_str = "—", "Run simulation to calculate"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Cluster Utilization</div>
        <div class="metric-value">{val_str}</div>
        <div class="metric-sub">{sub_str}</div>
    </div>""", unsafe_allow_html=True)

with pm_cols[1]:
    if pm:
        val_str = f"{pm.average_response_time} tu"
        sub_str = f"Max: {pm.maximum_response_time} tu · time units (simulated)"
    else:
        val_str, sub_str = "—", "Run simulation to calculate"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Avg Response Time</div>
        <div class="metric-value">{val_str}</div>
        <div class="metric-sub">{sub_str}</div>
    </div>""", unsafe_allow_html=True)

with pm_cols[2]:
    if pm:
        val_str = f"{pm.throughput} tasks/tu"
        sub_str = f"Makespan: {pm.makespan:.0f} tu"
    else:
        val_str, sub_str = "—", "Run simulation to calculate"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Throughput</div>
        <div class="metric-value">{val_str}</div>
        <div class="metric-sub">{sub_str}</div>
    </div>""", unsafe_allow_html=True)

with pm_cols[3]:
    if pm:
        val_str = f"{pm.load_imbalance} units"
        sub_str = f"Normalized: {pm.normalized_imbalance}%"
    else:
        val_str, sub_str = "—", "Run simulation to calculate"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Load Imbalance</div>
        <div class="metric-value">{val_str}</div>
        <div class="metric-sub">{sub_str}</div>
    </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Section 6 — Algorithm Comparison (Phase 6 — quantitative)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<p class="section-title">⚖️  Algorithm Comparison</p>', unsafe_allow_html=True)

# Explanation of algorithms
st.markdown("""
<div style="display:flex; gap:1rem; margin-bottom:1rem;">
    <div style="flex:1; background:#1e293b; padding:1rem; border-radius:8px; border-left:4px solid #3b82f6;">
        <strong style="color:#60a5fa;">🔵 ROUND ROBIN — STATIC</strong><br>
        <span style="font-size:0.85rem; color:#cbd5e1;">
        • Uses fixed cyclic assignment.<br>
        • Does not consider current VM workload.<br>
        • Simple and deterministic.</span>
    </div>
    <div style="flex:1; background:#1e293b; padding:1rem; border-radius:8px; border-left:4px solid #f97316;">
        <strong style="color:#fb923c;">🟠 THROTTLED — DYNAMIC</strong><br>
        <span style="font-size:0.85rem; color:#cbd5e1;">
        • Considers current VM workload.<br>
        • Selects the least-loaded available VM.<br>
        • Dynamically reacts to workload distribution.</span>
    </div>
</div>
""", unsafe_allow_html=True)

cmp = engine.comparison_results  # {algo_name: PerformanceMetrics} | None
ALGO_RR = "Round Robin (Static)"
ALGO_TH = "Throttled (Dynamic)"

if not cmp:
    st.markdown("""
    <div class="empty-state-box">
        ⚖️ Click <strong>Run Comparison</strong> in the sidebar to generate a fair, side-by-side comparison of Round Robin vs Throttled using the same workload (seed=42).
    </div>
    """, unsafe_allow_html=True)
else:

    rr = cmp.get(ALGO_RR)
    th = cmp.get(ALGO_TH)

    if rr and th:
        # ── Comparison table ──────────────────────────────────────────────────
        st.markdown("#### 📋 Metrics Summary")
        cmp_df_data = {
            "Metric"              : [
                "Tasks",
                "Active VMs",
                "Total Workload (units)",
                "Makespan (time units)",
                "Avg Response Time (tu)",
                "Max Response Time (tu)",
                "Throughput (tasks/tu)",
                "Cluster Utilization (%)",
                "Load Imbalance (units)",
                "Normalized Imbalance (%)",
                "Max VM Workload (units)",
                "Min VM Workload (units)",
            ],
            "Round Robin (Static)": [
                rr.total_tasks,
                rr.active_vm_count,
                rr.total_workload,
                f"{rr.makespan:.0f}",
                f"{rr.average_response_time:.2f}",
                f"{rr.maximum_response_time:.2f}",
                f"{rr.throughput:.4f}",
                f"{rr.cluster_utilization:.2f}%",
                rr.load_imbalance,
                f"{rr.normalized_imbalance:.2f}%",
                rr.max_vm_workload,
                rr.min_vm_workload,
            ],
            "Throttled (Dynamic)": [
                th.total_tasks,
                th.active_vm_count,
                th.total_workload,
                f"{th.makespan:.0f}",
                f"{th.average_response_time:.2f}",
                f"{th.maximum_response_time:.2f}",
                f"{th.throughput:.4f}",
                f"{th.cluster_utilization:.2f}%",
                th.load_imbalance,
                f"{th.normalized_imbalance:.2f}%",
                th.max_vm_workload,
                th.min_vm_workload,
            ],
            "Lower is Better": [
                "—", "—", "—",
                "✅", "✅", "✅",
                "❌ Higher", "❌ Higher",
                "✅", "✅",
                "—", "—",
            ],
        }
        st.dataframe(
            pd.DataFrame(cmp_df_data),
            use_container_width=True,
            hide_index=True,
        )

        # ── Interpretation ────────────────────────────────────────────────────
        st.markdown("#### 🔍 Interpretation")
        notes = []
        if rr.load_imbalance < th.load_imbalance:
            notes.append(
                f"🔵 **Round Robin** achieved lower load imbalance ({rr.load_imbalance} units) "
                f"than Throttled ({th.load_imbalance} units) for this workload."
            )
        elif th.load_imbalance < rr.load_imbalance:
            notes.append(
                f"🟠 **Throttled** achieved lower load imbalance ({th.load_imbalance} units) "
                f"than Round Robin ({rr.load_imbalance} units) for this workload."
            )
        else:
            notes.append("➖ Both algorithms produced identical load imbalance for this workload.")

        if rr.average_response_time < th.average_response_time:
            notes.append(
                f"🔵 **Round Robin** had a lower average response time "
                f"({rr.average_response_time:.2f} vs {th.average_response_time:.2f} tu)."
            )
        elif th.average_response_time < rr.average_response_time:
            notes.append(
                f"🟠 **Throttled** had a lower average response time "
                f"({th.average_response_time:.2f} vs {rr.average_response_time:.2f} tu)."
            )
        else:
            notes.append("➖ Both algorithms had equal average response time.")

        if rr.makespan < th.makespan:
            notes.append(
                f"🔵 **Round Robin** had a shorter makespan "
                f"({rr.makespan:.0f} vs {th.makespan:.0f} tu)."
            )
        elif th.makespan < rr.makespan:
            notes.append(
                f"🟠 **Throttled** had a shorter makespan "
                f"({th.makespan:.0f} vs {rr.makespan:.0f} tu)."
            )
        else:
            notes.append("➖ Both algorithms produced the same makespan.")

        for note in notes:
            st.markdown(note)

        st.caption(
            "ℹ️ Metrics use a sequential simulated execution model: "
            "processing rate = 1 unit/time unit per VM. "
            "All results are deterministic for seed=42 workload."
        )

        # ── Plotly Charts ─────────────────────────────────────────────────────
        _CHART_COLORS = {"rr": "#3b82f6", "th": "#f97316"}  # blue, orange
        _ALGO_LABELS  = ["Round Robin", "Throttled"]

        with st.expander("📊  View Performance Charts", expanded=True):
            ch_col1, ch_col2 = st.columns(2)

            # Chart 1: Average Response Time
            with ch_col1:
                fig1 = go.Figure(go.Bar(
                    x=_ALGO_LABELS,
                    y=[rr.average_response_time, th.average_response_time],
                    marker_color=[_CHART_COLORS["rr"], _CHART_COLORS["th"]],
                    text=[f"{rr.average_response_time:.2f}", f"{th.average_response_time:.2f}"],
                    textposition="outside",
                ))
                fig1.update_layout(
                    title="Avg Response Time (tu) — Lower is better",
                    yaxis_title="Simulated time units",
                    plot_bgcolor="#1e293b",
                    paper_bgcolor="#1e293b",
                    font=dict(color="#e2e8f0"),
                    margin=dict(l=20, r=20, t=50, b=20),
                )
                st.plotly_chart(fig1, use_container_width=True)

            # Chart 2: Throughput
            with ch_col2:
                fig2 = go.Figure(go.Bar(
                    x=_ALGO_LABELS,
                    y=[rr.throughput, th.throughput],
                    marker_color=[_CHART_COLORS["rr"], _CHART_COLORS["th"]],
                    text=[f"{rr.throughput:.4f}", f"{th.throughput:.4f}"],
                    textposition="outside",
                ))
                fig2.update_layout(
                    title="Throughput (tasks/tu) — Higher is better",
                    yaxis_title="Tasks per time unit",
                    plot_bgcolor="#1e293b",
                    paper_bgcolor="#1e293b",
                    font=dict(color="#e2e8f0"),
                    margin=dict(l=20, r=20, t=50, b=20),
                )
                st.plotly_chart(fig2, use_container_width=True)

            ch_col3, ch_col4 = st.columns(2)

            # Chart 3: Cluster Utilization
            with ch_col3:
                fig3 = go.Figure(go.Bar(
                    x=_ALGO_LABELS,
                    y=[rr.cluster_utilization, th.cluster_utilization],
                    marker_color=[_CHART_COLORS["rr"], _CHART_COLORS["th"]],
                    text=[f"{rr.cluster_utilization:.2f}%", f"{th.cluster_utilization:.2f}%"],
                    textposition="outside",
                ))
                fig3.update_layout(
                    title="Cluster Utilization (%) — Higher is better",
                    yaxis_title="% of capacity used during makespan",
                    plot_bgcolor="#1e293b",
                    paper_bgcolor="#1e293b",
                    font=dict(color="#e2e8f0"),
                    margin=dict(l=20, r=20, t=50, b=20),
                )
                st.plotly_chart(fig3, use_container_width=True)

            # Chart 4: Load Imbalance
            with ch_col4:
                fig4 = go.Figure(go.Bar(
                    x=_ALGO_LABELS,
                    y=[rr.load_imbalance, th.load_imbalance],
                    marker_color=[_CHART_COLORS["rr"], _CHART_COLORS["th"]],
                    text=[f"{rr.load_imbalance} units", f"{th.load_imbalance} units"],
                    textposition="outside",
                ))
                fig4.update_layout(
                    title="Load Imbalance (units) — Lower is better",
                    yaxis_title="Max VM workload − Min VM workload",
                    plot_bgcolor="#1e293b",
                    paper_bgcolor="#1e293b",
                    font=dict(color="#e2e8f0"),
                    margin=dict(l=20, r=20, t=50, b=20),
                )
                st.plotly_chart(fig4, use_container_width=True)



# ─────────────────────────────────────────────────────────────────────────────
# Section 5 — Automated Scaling (Phase 5)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<p class="section-title">🔄  Automated Scaling</p>', unsafe_allow_html=True)

scaling_ran = sim_done and engine.scaling_listener is not None
sl          = engine.scaling_listener if scaling_ran else None

sf_cols = st.columns(3)

# ── Card 1: Automated Scaling Listener ───────────────────────────────────────
with sf_cols[0]:
    if scaling_ran:
        # Determine if max-VM limit was reached while pressure was still high
        at_max      = sl.final_vm_count >= sl.max_vms
        still_high  = sl.final_pressure > sl.scale_up_threshold
        cap_note    = ""
        if at_max and still_high:
            cap_note = (
                f'<div class="feature-detail" style="color:#b45309;">'
                f'⚠️ High pressure ({sl.final_pressure}%) — max cap reached'
                f'</div>'
            )
        st.markdown(f"""
        <div class="feature-card feature-card-active">
            <div class="feature-title">🔍 Automated Scaling Listener</div>
            <div class="feature-note">Monitoring complete</div>
            <div class="feature-stat">Final Pressure: {sl.final_pressure}%</div>
            {cap_note}
        </div>""", unsafe_allow_html=True)
    elif sim_done:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-title">🔍 Automated Scaling Listener</div>
            <div class="feature-note">Monitoring disabled</div>
            <br><small style="color:#9ca3af;font-style:italic;">Enable in sidebar to activate</small>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-title">🔍 Automated Scaling Listener</div>
            <div class="feature-note">Monitors workload and triggers scale events</div>
            <br><small style="color:#9ca3af;font-style:italic;">Run simulation to activate</small>
        </div>""", unsafe_allow_html=True)
    st.write("")

# ── Card 2: Scale Up ─────────────────────────────────────────────────────────
with sf_cols[1]:
    if scaling_ran:
        has_up   = sl.vms_added > 0
        last_up  = sl.last_scale_up
        at_max   = sl.final_vm_count >= sl.max_vms
        still_hi = sl.final_pressure > sl.scale_up_threshold
        card_cls = "feature-card feature-card-active" if has_up else "feature-card"
        if last_up:
            last_line = f'<div class="feature-stat">Last: {last_up.vm_name} added</div>'
        else:
            last_line = '<div class="feature-stat" style="color:#9ca3af;">No scale-up triggered</div>'
        # Show max-cap note when relevant
        cap_line = ""
        if at_max and still_hi:
            cap_line = (
                f'<div class="feature-detail" style="color:#b45309;">'
                f'⚠️ Max VM limit ({sl.max_vms}) reached'
                f'</div>'
            )
        st.markdown(f"""
        <div class="{card_cls}">
            <div class="feature-title">🔼 Scale Up</div>
            <div class="feature-note">VMs added: <strong>{sl.vms_added}</strong></div>
            {last_line}
            {cap_line}
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-title">⬆️ Scale Up</div>
            <div class="feature-note">Add a VM when pressure &gt; threshold</div>
            <br><small style="color:#9ca3af;font-style:italic;">Triggered automatically</small>
        </div>""", unsafe_allow_html=True)
    st.write("")

# ── Card 3: Scale Down ───────────────────────────────────────────────────────
with sf_cols[2]:
    if scaling_ran:
        has_dn   = sl.vms_removed > 0
        last_dn  = sl.last_scale_down
        card_cls = "feature-card feature-card-active" if has_dn else "feature-card"
        last_line = (
            f'<div class="feature-stat">Last: {last_dn.vm_name} removed</div>'
            if last_dn else
            '<div class="feature-stat" style="color:#9ca3af;">No scale-down triggered</div>'
        )
        st.markdown(f"""
        <div class="{card_cls}">
            <div class="feature-title">🔽 Scale Down</div>
            <div class="feature-note">VMs removed: <strong>{sl.vms_removed}</strong></div>
            {last_line}
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-title">⬇️ Scale Down</div>
            <div class="feature-note">Remove idle VM when pressure &lt; threshold</div>
            <br><small style="color:#9ca3af;font-style:italic;">Triggered automatically</small>
        </div>""", unsafe_allow_html=True)
    st.write("")

# ── Scaling event log ─────────────────────────────────────────────────────────
if scaling_ran and sl.events:
    st.markdown('<p class="section-title">📋  Scaling Event Log</p>', unsafe_allow_html=True)
    for ev in sl.events:
        icon     = "🔼" if ev.event_type == "Scale Up" else "🔽"
        ev_cls   = "scaling-event-up" if ev.event_type == "Scale Up" else "scaling-event-down"
        action   = "added" if ev.event_type == "Scale Up" else "removed"
        st.markdown(f"""
        <div class="scaling-event-card {ev_cls}">
            <span class="event-time">[{ev.timestamp}]</span>
            <span class="event-type">{icon} {ev.event_type}</span> —
            <span class="event-vm">{ev.vm_name}</span> {action}
            &nbsp;(pressure: {ev.pressure_before}% → {ev.pressure_after}%)
            <div class="event-reason">Reason: {ev.reason}</div>
        </div>""", unsafe_allow_html=True)
elif scaling_ran:
    st.info(
        "ℹ️ No scaling events triggered — workload was within the normal range "
        f"({sl.scale_down_threshold}% – {sl.scale_up_threshold}%).",
        icon="ℹ️",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Section 8 — VM Failure & Failover (Phase 8)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<p class="section-title">🛡️  VM Failure & Failover</p>', unsafe_allow_html=True)

fm = engine.failover_manager   # FailoverManager | None

if fm is None or not fm.failure_triggered:
    st.markdown("""
    <div class="empty-state-box">
        🛡️ Enable <strong>Simulate VM Failure</strong> in the sidebar and run the simulation to demonstrate fault tolerance and failover.
    </div>
    """, unsafe_allow_html=True)
else:
    fs = fm.failover_summary  # plain dict

    # ── Failover Summary cards ────────────────────────────────────────────────
    st.markdown("#### 🛡️ Failover Summary")
    f_c1, f_c2, f_c3, f_c4 = st.columns(4)

    with f_c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Failed VM</div>
            <div class="metric-value" style="color:#e94560">{fs['failed_vm_name']}</div>
            <div class="metric-sub">Permanently removed from scheduler</div>
        </div>""", unsafe_allow_html=True)

    with f_c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Failure After Task</div>
            <div class="metric-value">{fs['failure_after_tasks']}</div>
            <div class="metric-sub">Tasks assigned before failure</div>
        </div>""", unsafe_allow_html=True)

    with f_c3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Tasks Redirected</div>
            <div class="metric-value" style="color:#22c55e">{fs['tasks_after_failure']}</div>
            <div class="metric-sub">Protected by failover</div>
        </div>""", unsafe_allow_html=True)

    with f_c4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Remaining Active VMs</div>
            <div class="metric-value">{fs['final_active_vms']}</div>
            <div class="metric-sub">Healthy VMs after failure</div>
        </div>""", unsafe_allow_html=True)

    if fs["tasks_skipped"] > 0:
        st.warning(
            f"⚠️ **{fs['tasks_skipped']} task(s) could not be assigned** — "
            "no available VMs remained after failure. "
            "Increase VM count or fail a later task to allow full failover.",
            icon="⚠️",
        )
    else:
        st.success(
            f"✅ Failover successful — all {fs['tasks_after_failure']} remaining task(s) "
            f"were redirected to {fs['final_active_vms']} healthy VM(s). "
            f"{fs['failed_vm_name']} received 0 new tasks after failure.",
            icon="🛡️",
        )

    # ── VM Status After Failover ──────────────────────────────────────────────
    if engine.vms:
        st.markdown("#### 💻 VM Status After Failover")
        vm_cols = st.columns(min(len(engine.vms), 5))
        for i, vm in enumerate(engine.vms):
            with vm_cols[i % len(vm_cols)]:
                if vm.status == STATUS_FAILED:
                    icon_char   = "🔴"
                    card_color  = "#fff1f2"
                    border_color= "#fda4af"
                    name_color  = "#9f1239"
                    status_text = "FAILED"
                elif vm.status == STATUS_BUSY:
                    icon_char   = "🟢"
                    card_color  = "#f0fdf4"
                    border_color= "#86efac"
                    name_color  = "#166534"
                    status_text = "Assigned / Loaded"
                else:
                    icon_char   = "⬜"
                    card_color  = "#f0f4ff"
                    border_color= "#c7d2fe"
                    name_color  = "#3730a3"
                    status_text = "Idle"

                new_tasks_after = 0
                if fm and fm.failure_triggered and vm.vm_id == fm.fail_vm_id:
                    new_tasks_label = "New Tasks After Failure: **0** (blocked)"
                else:
                    new_tasks_label = f"Tasks: **{vm.task_count}**"

                st.markdown(f"""
                <div style="background:{card_color};border:1px solid {border_color};
                    border-radius:10px;padding:0.8rem;text-align:center;margin-bottom:0.5rem;">
                    <div style="font-weight:700;color:{name_color}">{icon_char} {vm.name}</div>
                    <div style="font-size:0.78rem;margin-top:0.2rem">{status_text}</div>
                    <div style="font-size:0.72rem;color:#6b7280;margin-top:0.3rem">
                        Cap: {vm.capacity} | Load: {vm.current_load}
                    </div>
                    <div style="font-size:0.72rem;color:#6b7280">
                        {new_tasks_label}
                    </div>
                </div>""", unsafe_allow_html=True)

    # ── Failover Event Log ────────────────────────────────────────────────────
    st.markdown("#### 📋 Failover Event Log")
    if fm.events:
        ev_data = []
        for ev in fm.events:
            ev_icon = {
                "VM Failure"      : "🔴",
                "Failover Active" : "🟡",
                "Task Redirected" : "🟢",
                "No VMs Available": "⛔",
            }.get(ev.event_type, "ℹ️")
            ev_data.append({
                "Time"       : ev.timestamp,
                "Event"      : f"{ev_icon} {ev.event_type}",
                "VM"         : ev.vm_name,
                "Task Index" : ev.task_index,
                "Detail"     : ev.detail,
            })
        st.dataframe(
            pd.DataFrame(ev_data),
            use_container_width=True,
            hide_index=True,
        )

    # ── Fault Tolerance Note ──────────────────────────────────────────────────
    algo_name = engine.algorithm
    if "round robin" in algo_name.lower():
        algo_desc = (
            "**Round Robin failover:** After the failure, the scheduler "
            "continued cycling through the remaining available VMs only — "
            f"{fs['failed_vm_name']} was excluded from the rotation."
        )
    else:
        algo_desc = (
            "**Throttled failover:** After the failure, the least-load "
            "selector excluded the failed VM from all subsequent decisions — "
            f"all new tasks were directed to the {fs['final_active_vms']} "
            "remaining available VMs."
        )
    st.info(algo_desc, icon="ℹ️")
    st.caption(
        "ℹ️ Tasks assigned to the failed VM *before* failure are preserved in simulation history. "
        "Only *new* tasks after the failure point are redirected (failover semantics)."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Section 7 — Workload & Scalability Testing (Phase 7)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<p class="section-title">📈  Workload & Scalability Testing</p>', unsafe_allow_html=True)

scal = engine.scalability_results  # List[Dict] | None
_RR  = "Round Robin (Static)"
_TH  = "Throttled (Dynamic)"
_C_RR = "#3b82f6"   # blue
_C_TH = "#f97316"   # orange

if not scal:
    st.markdown("""
    <div class="empty-state-box">
        📈 Click <strong>Run Scalability Test</strong> in the sidebar to test both algorithms across multiple workload sizes (10 / 50 / 100 / 500 tasks).
    </div>
    """, unsafe_allow_html=True)
else:
    # ── Derive per-algorithm series ───────────────────────────────────────────
    rr_rows = [r for r in scal if r["algorithm"] == _RR]
    th_rows = [r for r in scal if r["algorithm"] == _TH]
    task_labels_rr = [str(r["tasks"]) for r in rr_rows]
    task_labels_th = [str(r["tasks"]) for r in th_rows]
    # Use the union of tested task counts as x-axis labels
    all_tasks = sorted(set(r["tasks"] for r in scal))

    # Scaling metadata
    scal_on   = rr_rows[0]["scaling_enabled"] if rr_rows else False
    seed_used = rr_rows[0]["seed"]            if rr_rows else 42

    st.caption(
        f"📊 Scalability test — seed={seed_used} · "
        f"{'Auto-Scaling ON' if scal_on else 'Auto-Scaling OFF'} · "
        f"{len(all_tasks)} workload size(s): {', '.join(str(t) for t in all_tasks)} tasks"
    )

    # ── Results Table ─────────────────────────────────────────────────────────
    st.markdown("#### 📋 Scalability Results Table")
    tbl_rows = []
    for r in scal:
        tbl_rows.append({
            "Tasks"          : r["tasks"],
            "Algorithm"      : r["algorithm"],
            "Init. VMs"      : r["initial_vms"],
            "Final VMs"      : r["final_vms"],
            "VMs Added"      : r["vms_added"],
            "VMs Removed"    : r["vms_removed"],
            "Total Workload" : r["total_workload"],
            "Makespan (tu)"  : f"{r['makespan']:.0f}",
            "Avg RT (tu)"    : f"{r['avg_response_time']:.2f}",
            "Max RT (tu)"    : f"{r['max_response_time']:.2f}",
            "Throughput"     : f"{r['throughput']:.4f}",
            "Util. %"        : f"{r['cluster_util']:.2f}%",
            "Imbalance"      : r["load_imbalance"],
            "Norm. Imb. %"   : f"{r['norm_imbalance']:.2f}%",
        })
    st.dataframe(
        pd.DataFrame(tbl_rows),
        use_container_width=True,
        hide_index=True,
    )

    # ── Charts ────────────────────────────────────────────────────────────────
    def _make_line_chart(rr_y, th_y, x_labels, title, yaxis_title):
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x_labels, y=rr_y, mode="lines+markers",
            name="Round Robin", line=dict(color=_C_RR, width=2),
            marker=dict(size=8),
        ))
        fig.add_trace(go.Scatter(
            x=x_labels, y=th_y, mode="lines+markers",
            name="Throttled", line=dict(color=_C_TH, width=2),
            marker=dict(size=8),
        ))
        fig.update_layout(
            title=title,
            xaxis_title="Number of Tasks",
            yaxis_title=yaxis_title,
            plot_bgcolor="#1e293b",
            paper_bgcolor="#1e293b",
            font=dict(color="#e2e8f0"),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
            margin=dict(l=20, r=20, t=50, b=20),
        )
        return fig

    with st.expander("📊  View Scalability Charts", expanded=True):
        sc_col1, sc_col2 = st.columns(2)

        rr_rt  = [r["avg_response_time"] for r in rr_rows]
        th_rt  = [r["avg_response_time"] for r in th_rows]
        rr_tp  = [r["throughput"]        for r in rr_rows]
        th_tp  = [r["throughput"]        for r in th_rows]
        rr_imb = [r["load_imbalance"]    for r in rr_rows]
        th_imb = [r["load_imbalance"]    for r in th_rows]
        rr_vm  = [r["final_vms"]         for r in rr_rows]
        th_vm  = [r["final_vms"]         for r in th_rows]
        rr_util= [r["cluster_util"]      for r in rr_rows]
        th_util= [r["cluster_util"]      for r in th_rows]

        with sc_col1:
            st.plotly_chart(
                _make_line_chart(
                    rr_rt, th_rt, task_labels_rr,
                    "Avg Response Time vs Workload — Lower is better",
                    "Simulated time units",
                ),
                use_container_width=True,
            )
        with sc_col2:
            st.plotly_chart(
                _make_line_chart(
                    rr_tp, th_tp, task_labels_rr,
                    "Throughput vs Workload — Higher is better",
                    "Tasks / time unit",
                ),
                use_container_width=True,
            )

        sc_col3, sc_col4 = st.columns(2)
        with sc_col3:
            st.plotly_chart(
                _make_line_chart(
                    rr_imb, th_imb, task_labels_rr,
                    "Load Imbalance vs Workload — Lower is better",
                    "Max − Min VM workload (units)",
                ),
                use_container_width=True,
            )
        with sc_col4:
            st.plotly_chart(
                _make_line_chart(
                    rr_vm, th_vm, task_labels_rr,
                    "Active VMs vs Workload",
                    "Active VM count",
                ),
                use_container_width=True,
            )

        # Cluster utilization chart in a full-width row
        st.plotly_chart(
            _make_line_chart(
                rr_util, th_util, task_labels_rr,
                "Cluster Utilization vs Workload — Higher is better",
                "Utilization %",
            ),
            use_container_width=True,
        )

    # ── Data-driven Interpretation ────────────────────────────────────────────
    st.markdown("#### 🔍 Scalability Interpretation")
    interp = []

    # Response time trend across workloads
    if len(rr_rows) >= 2:
        rr_rt_delta = rr_rows[-1]["avg_response_time"] - rr_rows[0]["avg_response_time"]
        th_rt_delta = th_rows[-1]["avg_response_time"] - th_rows[0]["avg_response_time"]
        if abs(rr_rt_delta) > 0 or abs(th_rt_delta) > 0:
            interp.append(
                f"📈 As workload grew from {rr_rows[0]['tasks']} to {rr_rows[-1]['tasks']} tasks: "
                f"Round Robin avg response time changed by **{rr_rt_delta:+.0f} tu**, "
                f"Throttled by **{th_rt_delta:+.0f} tu**."
            )

    # Per-level imbalance comparison
    for rr_r, th_r in zip(rr_rows, th_rows):
        t = rr_r["tasks"]
        if rr_r["load_imbalance"] > th_r["load_imbalance"]:
            interp.append(
                f"🟠 At **{t} tasks**, Throttled had lower load imbalance "
                f"({th_r['load_imbalance']} vs {rr_r['load_imbalance']} units)."
            )
        elif th_r["load_imbalance"] > rr_r["load_imbalance"]:
            interp.append(
                f"🔵 At **{t} tasks**, Round Robin had lower load imbalance "
                f"({rr_r['load_imbalance']} vs {th_r['load_imbalance']} units)."
            )
        else:
            interp.append(f"➖ At **{t} tasks**, both algorithms had equal load imbalance.")

    # Scaling summary
    if scal_on and rr_rows:
        for rr_r in rr_rows:
            t = rr_r["tasks"]
            if rr_r["vms_added"] > 0:
                interp.append(
                    f"⚡ At **{t} tasks**, the Scaling Listener added **{rr_r['vms_added']} VM(s)** "
                    f"(pressure: {rr_r['initial_pressure']}% → {rr_r['final_pressure']}%)."
                )

    if not interp:
        interp.append("Run the full progression (10/50/100/500 tasks) for richer interpretation.")

    for note in interp:
        st.markdown(note)

    st.caption(
        "ℹ️ All scalability metrics use the sequential simulated execution model. "
        "Both algorithms received identical task lists for each workload size (seed=42)."
    )



# ─────────────────────────────────────────────────────────────────────────────
# About / Project Information
# ─────────────────────────────────────────────────────────────────────────────
with st.expander("ℹ️  About This Project", expanded=False):
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
**Project:** Static vs Dynamic Load Balancing Algorithms

**Course:** Cloud Computing

**Algorithms:**
- 🔄 **Round Robin (Static)** — Assigns tasks cyclically without considering VM workload.
- ⚡ **Throttled (Dynamic)** — Assigns each task to the least-loaded available VM.

**Supporting Features:**
- ⚡ Automated Scaling Listener — adjusts VM count based on workload pressure
- 📊 Performance Metrics — makespan, response time, throughput, utilization
- 📈 Workload & Scalability Testing — 10 / 50 / 100 / 500 task progressions
- 🛡️ VM Failure & Failover — deterministic fault tolerance simulation
""")
    with col_b:
        st.markdown("""
**Key Concepts Demonstrated:**
- Static vs dynamic scheduling trade-offs
- Cluster utilization and load imbalance measurement
- Elastic scaling (scale-up / scale-down)
- Fault tolerance via failover (no failed VM receives new tasks)
- Cyclic Round Robin index continuity across VM failure

**Terminology:**
- *Assigned Workload* — cumulative processing units assigned (not real CPU%)
- *Cluster Workload Pressure* — total_req ÷ (active_vms × capacity) × 100 (uncapped)
- *Makespan* — time from start of first task to end of last task on any VM
- *Throughput* — tasks per simulated time unit
""")

# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("🎓 Cloud Computing Project · Static vs Dynamic Load Balancing")

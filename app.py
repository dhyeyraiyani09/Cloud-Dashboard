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

# ── Simulation engine & workload sources ──────────────────────────────────────
from simulation.engine import (
    SimulationEngine, SIM_NOT_STARTED, SIM_READY, SIM_COMPLETED
)
from simulation.vm import STATUS_IDLE, STATUS_BUSY, STATUS_FAILED
from simulation.google_trace import (
    load_bundled_google_trace, parse_google_trace, TraceParseResult
)

# ── Algorithm identifiers ─────────────────────────────────────────────────────
ALGO_RR             = "Round Robin (Static)"
ALGO_LEAST_LOADED   = "Least-Loaded Dynamic (Existing Variant)"
ALGO_TRAD_THROTTLED = "Traditional Throttled"
ALGO_PAALB          = "Priority-Aware Adaptive (PAALB)"
ALGO_THROTTLED      = ALGO_LEAST_LOADED  # backward compatibility alias

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
        options=[ALGO_RR, ALGO_LEAST_LOADED, ALGO_TRAD_THROTTLED, ALGO_PAALB],
        index=0,
        help="Round Robin (Static) vs Least-Loaded Dynamic (Existing Variant) vs Traditional Throttled (Baseline) vs Priority-Aware Adaptive (PAALB).",
        label_visibility="collapsed",
    )

    st.markdown("---")

    st.markdown("**Workload Source**")
    workload_source = st.radio(
        label="Workload Source",
        options=["Synthetic Workload", "Google Cluster Trace"],
        index=0,
        help="Synthetic mixed distribution vs genuine Google Cluster Data 2011-2.",
        label_visibility="collapsed",
    )

    trace_parse_result = None
    trace_tasks = None

    if workload_source == "Google Cluster Trace":
        trace_mode = st.radio(
            "Trace Source",
            options=[
                "Bundled Staggered Trace (2011-2, varied timestamps)",
                "Bundled Snapshot Trace (2011-2, t=0 batch)",
                "Upload Custom Trace CSV",
            ],
            index=0,
            horizontal=False,
            help="Choose between genuine time-distributed arrivals, baseline t=0 batch snapshot, or custom CSV.",
        )
        if trace_mode == "Bundled Staggered Trace (2011-2, varied timestamps)":
            try:
                trace_parse_result = load_bundled_google_trace(sample_type="staggered")
                trace_tasks = trace_parse_result.tasks
            except Exception as e:
                st.error(f"Failed to load staggered trace: {e}")
        elif trace_mode == "Bundled Snapshot Trace (2011-2, t=0 batch)":
            try:
                trace_parse_result = load_bundled_google_trace(sample_type="snapshot")
                trace_tasks = trace_parse_result.tasks
            except Exception as e:
                st.error(f"Failed to load snapshot trace: {e}")
        else:
            st.caption(
                "Upload a Google Cluster Trace CSV (`task_events`) or CSV with a `cpu_request` column."
            )
            uploaded_trace = st.file_uploader(
                "Choose Trace CSV",
                type=["csv", "gz"],
                help="Accepts official 13-column schema or CSV with cpu_request column.",
            )
            if uploaded_trace is not None:
                try:
                    trace_parse_result = parse_google_trace(uploaded_trace)
                    trace_tasks = trace_parse_result.tasks
                except Exception as e:
                    st.error(f"Failed to parse uploaded trace: {e}")
            else:
                st.info("Upload a trace file to run simulation on custom trace.")

        if trace_parse_result and trace_tasks:
            with st.expander("ℹ️ Google Cluster Trace Info", expanded=False):
                st.markdown(
                    "**Dataset:** Google Cluster Data 2011-2 (v2.1)  \n"
                    "**Source:** [github.com/google/cluster-data](https://github.com/google/cluster-data)  \n"
                    "**License:** Creative Commons CC-BY 4.0  \n"
                    f"**Usable Records:** {trace_parse_result.records_accepted} (Read: {trace_parse_result.records_read})  \n"
                    f"**CPU Request Range:** {trace_parse_result.min_raw_cpu:.5f} – {trace_parse_result.max_raw_cpu:.5f} (Mean: {trace_parse_result.avg_raw_cpu:.5f})  \n"
                    "**Normalization:** `Units = clamp(round(CPU_Request * 100), 1, 100)`  \n"
                    "**Semantics:** Trace-informed workload replay evaluating static Round Robin vs. least-loaded dynamic scheduling."
                )

    st.markdown("---")

    num_vms = st.slider(
        "Number of VMs",  min_value=2, max_value=10, value=4, step=1,
        help="Initial number of VMs. The Scaling Listener may add or remove VMs before task assignment.",
    )
    if workload_source == "Google Cluster Trace":
        max_avail = len(trace_tasks) if trace_tasks else 500
        default_val = min(100, max_avail)
        num_tasks = st.slider(
            "Number of Tasks", min_value=10, max_value=max(10, max_avail), value=default_val, step=10,
            help=f"Total number of trace tasks to distribute across VMs (up to {max_avail}).",
        )
    else:
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
        if workload_source == "Google Cluster Trace" and not trace_tasks:
            st.error("Cannot start simulation: No valid Google Cluster Trace loaded.")
        else:
            try:
                engine.initialize(
                    num_vms=num_vms,
                    num_tasks=num_tasks,
                    algorithm=algorithm,
                    custom_tasks=trace_tasks if workload_source == "Google Cluster Trace" else None,
                    workload_source="google_trace" if workload_source == "Google Cluster Trace" else "synthetic",
                )
                if trace_parse_result:
                    engine.trace_parse_result = trace_parse_result

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
                    if "round robin" in algorithm.lower():
                        algo_short = "Round Robin"
                    elif "traditional" in algorithm.lower():
                        algo_short = "Traditional Throttled"
                    elif "paalb" in algorithm.lower() or "priority" in algorithm.lower():
                        algo_short = "Priority-Aware Adaptive (PAALB)"
                    else:
                        algo_short = "Least-Loaded Dynamic"
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
    max_cmp_tasks = len(trace_tasks) if (workload_source == "Google Cluster Trace" and trace_tasks) else 500
    cmp_tasks = st.slider(
        "Comparison Tasks",
        min_value=10, max_value=max(10, max_cmp_tasks), value=min(100, max_cmp_tasks), step=10,
        help="Number of tasks for the fair comparison run.",
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
            "Runs Round Robin, Least-Loaded Dynamic, Traditional Throttled, and PAALB on the SAME workload "
            "with the same VMs and scaling settings."
        ),
    )
    if compare_btn:
        if workload_source == "Google Cluster Trace" and not trace_tasks:
            st.error("Cannot run comparison: No valid Google Cluster Trace loaded.")
        else:
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
                    custom_tasks         = trace_tasks if workload_source == "Google Cluster Trace" else None,
                )
                src_note = "Google Cluster Trace" if workload_source == "Google Cluster Trace" else "seed=42"
                st.success(
                    f"✅ Comparison complete! ({cmp_vms} VMs, {cmp_tasks} tasks, {src_note}, "
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
        src_label = "Google Cluster Trace" if getattr(engine, "workload_source", "synthetic") == "google_trace" else "Synthetic Workload"
        st.caption(f"**Workload:** {src_label}")
    has_cmp  = engine.comparison_results  is not None
    has_scal = engine.scalability_results is not None
    has_fo   = engine.failover_manager    is not None and getattr(engine.failover_manager, "failure_triggered", False)
    st.caption(
        "Round Robin & Least-Loaded Dynamic ✅  \n"
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

    include_trad_scal = st.checkbox(
        "Include Traditional Throttled Baseline",
        value=False,
        help="Also benchmark the Traditional Throttled algorithm across the workload progression.",
    )
    include_paalb_scal = st.checkbox(
        "Include PAALB (Proposed)",
        value=False,
        help="Also benchmark the Priority-Aware Adaptive Load Balancer across the workload progression.",
    )

    scal_btn = st.button(
        "📈  Run Scalability Test",
        use_container_width=True,
        type="primary",
        help=(
            "Runs algorithms across the selected workload(s) "
            "using identical task lists. Does NOT affect main simulation state."
        ),
    )
    if scal_btn:
        if workload_source == "Google Cluster Trace" and not trace_tasks:
            st.error("Cannot run scalability test: No valid Google Cluster Trace loaded.")
        else:
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
                    custom_tasks         = trace_tasks if workload_source == "Google Cluster Trace" else None,
                    include_traditional  = include_trad_scal,
                    include_paalb        = include_paalb_scal,
                )
                n_runs = len(engine.scalability_results)
                n_algos = 2 + (1 if include_trad_scal else 0) + (1 if include_paalb_scal else 0)
                src_note = "Google Cluster Trace" if workload_source == "Google Cluster Trace" else "seed=42"
                st.success(
                    f"✅ Scalability test complete! ({n_runs // n_algos} workload sizes × {n_algos} algorithms, "
                    f"{src_note}, scaling={'ON' if scaling_enabled else 'OFF'})"
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
elif algorithm == ALGO_TRAD_THROTTLED:
    st.markdown("""
    <div class="algo-info-banner algo-info-throttled">
        <div class="ai-icon">⏳</div>
        <div>
            <div class="ai-title">Traditional Throttled — Baseline Dynamic Load Balancing</div>
            <div class="ai-desc">
                Follows the canonical availability-table approach (Wickremasinghe et al., 2010): Maintains an AVAILABLE/BUSY state
                table for each VM. Incoming tasks are dispatched to the <em>first available VM</em> in table order.
                If all VMs are BUSY, tasks are throttled into a <strong>FIFO waiting queue</strong>. When a VM completes a task,
                it reverts to AVAILABLE and immediately pulls the next waiting task from the queue.
                <br><em>Simulated service durations are deterministically derived from normalized processing units to model queueing delays and turnaround time.</em>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)
elif algorithm == ALGO_PAALB:
    st.markdown("""
    <div class="algo-info-banner algo-info-throttled" style="border-left-color: #8b5cf6;">
        <div class="ai-icon">🎯</div>
        <div>
            <div class="ai-title">Priority-Aware Adaptive Load Balancer (PAALB) — Proposed Heuristic</div>
            <div class="ai-desc">
                Dynamically prioritizes waiting tasks using a multi-criteria scoring function:
                <strong>S(t, &tau;) = w<sub>p</sub> &middot; P<sub>norm</sub>(t) + w<sub>s</sub> &middot; L<sub>norm</sub>(t) + w<sub>a</sub> &middot; A(t, &tau;)</strong>
                (defaults: <em>w<sub>p</sub> = 0.45, w<sub>s</sub> = 0.35, w<sub>a</sub> = 0.20, T<sub>ref</sub> = 10.0</em>).
                When a VM completes execution, the scheduler evaluates all pending tasks, selects the highest-scoring task,
                and dispatches it to the available VM with minimum cumulative load.
                Includes a dynamic aging mechanism allowing lower-priority tasks to advance in score over time
                (40-unit overtaking horizon relative to newly arriving tasks; empirically demonstrating bounded queue delays across finite trace workloads).
            </div>
        </div>
    </div>""", unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="algo-info-banner algo-info-throttled">
        <div class="ai-icon">⚡</div>
        <div>
            <div class="ai-title">Least-Loaded Dynamic (Existing Variant)</div>
            <div class="ai-desc">
                Tasks are assigned to the <em>least-loaded available VM</em> based on
                current accumulated workload (minimum cumulative processing units). Unlike static Round Robin, the algorithm
                re-inspects VM loads before every assignment decision, adapting dynamically to heterogeneous task sizes.
                <br><em>Note: Previously labeled in this project as "Throttled (Dynamic)". Following an academic audit, it is documented as a least-loaded dynamic variant rather than the traditional availability-table first-available Throttled algorithm.</em>
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
    if getattr(engine, "workload_source", "synthetic") == "google_trace":
        st.info(
            "📊 **Workload Source:** Google Cluster Trace (clusterdata-2011-2, v2.1) · "
            "Replaying genuine cluster task requests normalized via `clamp(round(CPU_Request * 100), 1, 100)`.",
            icon="ℹ️"
        )

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
            "Job ID"      : st.column_config.NumberColumn("Job ID",    width="small"),
            "Raw CPU"     : st.column_config.TextColumn("Raw CPU (norm)", width="small"),
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
    is_throttled = "throttled" in engine.algorithm.lower() or "least" in engine.algorithm.lower()

    if is_rr:
        section_title = "📈  Round Robin Assignment Summary"
        caption_note  = (
            "💡 Round Robin distributes tasks cyclically but **does not** account for task "
            "size, so VMs may have different total loads even if task counts are equal."
        )
    elif "traditional" in engine.algorithm.lower():
        section_title = "⏳  Traditional Throttled Assignment Summary"
        caption_note  = (
            "💡 Traditional Throttled allocates tasks to the **first available VM** in the availability table. "
            "When all VMs are BUSY, incoming tasks enter a **FIFO waiting queue**. "
            "Task response time comprises both waiting time and simulated service time."
        )
    elif "paalb" in engine.algorithm.lower() or "priority" in engine.algorithm.lower():
        section_title = "🎯  PAALB Assignment Summary"
        caption_note  = (
            "💡 PAALB evaluates pending tasks dynamically when a VM is ready, prioritizing higher-priority and "
            "shorter tasks while advancing aged tasks (40-unit overtaking horizon relative to new arrivals). "
            "Tasks are dispatched to the available VM with lowest cumulative workload."
        )
    else:
        section_title = "⚡  Least-Loaded Dynamic Assignment Summary"
        caption_note  = (
            "💡 Assigns each task to the **least-loaded available VM** (minimum current load) at that moment, "
            "so total loads tend to be more balanced than Round Robin — "
            "though task count per VM may be unequal. (Previously labeled Throttled)."
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

if pm and (pm.queued_task_count > 0 or pm.average_waiting_time > 0 or "traditional" in engine.algorithm.lower() or "paalb" in engine.algorithm.lower() or "priority" in engine.algorithm.lower()):
    q_cols = st.columns(3)
    with q_cols[0]:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Avg Queue Waiting Time</div>
            <div class="metric-value">{pm.average_waiting_time:.2f} tu</div>
            <div class="metric-sub">Max: {pm.maximum_waiting_time:.2f} tu · FIFO delay</div>
        </div>""", unsafe_allow_html=True)
    with q_cols[1]:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Queued Tasks Count</div>
            <div class="metric-value">{pm.queued_task_count} / {pm.total_tasks}</div>
            <div class="metric-sub">Tasks held in FIFO queue while all VMs BUSY</div>
        </div>""", unsafe_allow_html=True)
    with q_cols[2]:
        avg_svc = max(0.0, pm.average_response_time - pm.average_waiting_time)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Mean Service Duration</div>
            <div class="metric-value">{avg_svc:.2f} tu</div>
            <div class="metric-sub">Turnaround ({pm.average_response_time:.2f}) = Wait + Service</div>
        </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Section 6 — Algorithm Comparison (Phase 6 — quantitative)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<p class="section-title">⚖️  Algorithm Comparison</p>', unsafe_allow_html=True)

# Explanation of algorithms
st.markdown("""
<div style="display:flex; gap:1rem; margin-bottom:1rem; flex-wrap:wrap;">
    <div style="flex:1; min-width:220px; background:#1e293b; padding:1rem; border-radius:8px; border-left:4px solid #3b82f6;">
        <strong style="color:#60a5fa;">🔵 ROUND ROBIN — STATIC</strong><br>
        <span style="font-size:0.85rem; color:#cbd5e1;">
        • Uses fixed cyclic assignment.<br>
        • Does not consider current VM workload.<br>
        • Simple and deterministic.</span>
    </div>
    <div style="flex:1; min-width:220px; background:#1e293b; padding:1rem; border-radius:8px; border-left:4px solid #f97316;">
        <strong style="color:#fb923c;">🟠 LEAST-LOADED DYNAMIC (EXISTING VARIANT)</strong><br>
        <span style="font-size:0.85rem; color:#cbd5e1;">
        • Considers current cumulative VM workload.<br>
        • Selects least-loaded available VM.<br>
        • Adapts to heterogeneous task sizes.<br>
        • <em>Note: Previously labeled Throttled.</em></span>
    </div>
    <div style="flex:1; min-width:220px; background:#1e293b; padding:1rem; border-radius:8px; border-left:4px solid #10b981;">
        <strong style="color:#34d399;">🟢 TRADITIONAL THROTTLED — BASELINE</strong><br>
        <span style="font-size:0.85rem; color:#cbd5e1;">
        • Availability table (AVAILABLE / BUSY).<br>
        • First-available allocation.<br>
        • FIFO waiting queue when all VMs BUSY.<br>
        • Canonical CloudAnalyst model.</span>
    </div>
    <div style="flex:1; min-width:220px; background:#1e293b; padding:1rem; border-radius:8px; border-left:4px solid #8b5cf6;">
        <strong style="color:#a78bfa;">🟣 PRIORITY-AWARE ADAPTIVE (PAALB)</strong><br>
        <span style="font-size:0.85rem; color:#cbd5e1;">
        • Dynamic priority & length scoring.<br>
        • Dynamic aging (overtaking horizon: 40 tu).<br>
        • Dispatches to min-load available VM.<br>
        • SLA optimization for Production Tier.</span>
    </div>
</div>
""", unsafe_allow_html=True)

cmp = engine.comparison_results  # {algo_name: PerformanceMetrics} | None
ALGO_RR           = "Round Robin (Static)"
ALGO_LEAST_LOADED = "Least-Loaded Dynamic (Existing Variant)"
ALGO_TT           = "Traditional Throttled"
ALGO_PAALB        = "Priority-Aware Adaptive (PAALB)"
ALGO_TH           = ALGO_LEAST_LOADED

if not cmp:
    st.markdown("""
    <div class="empty-state-box">
        ⚖️ Click <strong>Run Comparison</strong> in the sidebar to generate a fair, side-by-side comparison across algorithms using the same workload.
    </div>
    """, unsafe_allow_html=True)
else:

    rr = cmp.get(ALGO_RR)
    th = cmp.get(ALGO_LEAST_LOADED) or cmp.get("Throttled (Dynamic)")
    tt = cmp.get(ALGO_TT)
    pa = cmp.get(ALGO_PAALB) or cmp.get("PAALB")

    if rr and th:
        # ── Comparison table ──────────────────────────────────────────────────
        st.markdown("#### 📋 Metrics Summary")
        src_label = "Google Cluster Trace (clusterdata-2011-2)" if getattr(engine, "workload_source", "synthetic") == "google_trace" else "Synthetic Workload (seed=42)"
        st.caption(f"**Workload Evaluated:** {src_label} — all algorithms received identical task records and ordering. *(Note: Least-Loaded Dynamic was previously labeled Throttled in this project).*")

        metrics_list = [
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
        ]
        def _get_metric_col(m):
            return [
                str(m.total_tasks),
                str(m.active_vm_count),
                str(m.total_workload),
                f"{m.makespan:.2f}",
                f"{m.average_response_time:.2f}",
                f"{m.maximum_response_time:.2f}",
                f"{m.throughput:.4f}",
                f"{m.cluster_utilization:.2f}%",
                str(m.load_imbalance),
                f"{m.normalized_imbalance:.2f}%",
                str(m.max_vm_workload),
                str(m.min_vm_workload),
            ]

        rr_vals = _get_metric_col(rr)
        th_vals = _get_metric_col(th)
        lower_better = [
            "—", "—", "—",
            "✅", "✅", "✅",
            "❌ Higher", "❌ Higher",
            "✅", "✅",
            "—", "—",
        ]

        cmp_df_data = {
            "Metric"                                 : list(metrics_list),
            "Round Robin (Static)"                   : list(rr_vals),
            "Least-Loaded Dynamic (Existing Variant)": list(th_vals),
        }

        all_present = [m for m in [rr, th, tt, pa] if m]
        has_queue_metrics = any((m.average_waiting_time > 0 or m.queued_task_count > 0) for m in all_present)

        if tt:
            cmp_df_data["Traditional Throttled (Baseline)"] = _get_metric_col(tt)
        if pa:
            cmp_df_data["Priority-Aware Adaptive (PAALB)"] = _get_metric_col(pa)

        if has_queue_metrics:
            cmp_df_data["Metric"].extend([
                "Avg Queue Waiting Time (tu)",
                "Queued Tasks Count",
            ])
            cmp_df_data["Round Robin (Static)"].extend([
                f"{rr.average_waiting_time:.2f}",
                f"{rr.queued_task_count} of {rr.total_tasks}",
            ])
            cmp_df_data["Least-Loaded Dynamic (Existing Variant)"].extend([
                f"{th.average_waiting_time:.2f}",
                f"{th.queued_task_count} of {th.total_tasks}",
            ])
            if tt:
                cmp_df_data["Traditional Throttled (Baseline)"].extend([
                    f"{tt.average_waiting_time:.2f}",
                    f"{tt.queued_task_count} of {tt.total_tasks}",
                ])
            if pa:
                cmp_df_data["Priority-Aware Adaptive (PAALB)"].extend([
                    f"{pa.average_waiting_time:.2f}",
                    f"{pa.queued_task_count} of {pa.total_tasks}",
                ])
            lower_better.extend(["✅", "✅"])

        cmp_df_data["Lower is Better"] = lower_better

        st.dataframe(
            pd.DataFrame(cmp_df_data),
            use_container_width=True,
            hide_index=True,
        )

        # ── Priority-Tier Performance Comparison (Phase 14.1) ─────────────────
        pt_rows = engine.get_priority_tier_comparison()
        if pt_rows and tt and pa:
            st.markdown("#### 🎯 Priority-Tier Performance Comparison (Traditional Throttled vs PAALB)")
            has_trace_priorities = any(r["Task Count"] > 0 for r in pt_rows)
            if has_trace_priorities:
                st.caption(
                    "Dynamic turnaround comparison evaluated directly from task execution records across official Google Cluster Trace priority tiers. "
                    "Reductions in response time reflect SLA improvements; increases reflect trade-offs on batch workloads."
                )
            else:
                st.caption(
                    "ℹ️ Priority tiers require workload priority metadata (available with Google Cluster Trace). "
                    "Synthetic tasks lack priority tiers and display as N/A."
                )
            st.dataframe(
                pd.DataFrame(pt_rows),
                use_container_width=True,
                hide_index=True,
            )

        # ── Interpretation ────────────────────────────────────────────────────
        st.markdown("#### 🔍 Interpretation")
        notes = []
        if rr.load_imbalance < th.load_imbalance:
            notes.append(
                f"🔵 **Round Robin** achieved lower load imbalance ({rr.load_imbalance} units) "
                f"than Least-Loaded Dynamic ({th.load_imbalance} units) for this workload."
            )
        elif th.load_imbalance < rr.load_imbalance:
            notes.append(
                f"🟠 **Least-Loaded Dynamic** achieved lower load imbalance ({th.load_imbalance} units) "
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
                f"🟠 **Least-Loaded Dynamic** had a lower average response time "
                f"({th.average_response_time:.2f} vs {rr.average_response_time:.2f} tu)."
            )
        else:
            notes.append("➖ Both algorithms had equal average response time.")

        if tt:
            notes.append(
                f"🟢 **Traditional Throttled Baseline** operated with discrete-event queueing: "
                f"makespan = {tt.makespan:.2f} tu, avg response time = {tt.average_response_time:.2f} tu "
                f"(including avg queue wait = {tt.average_waiting_time:.2f} tu across {tt.queued_task_count} queued tasks)."
            )

        if pa:
            pa_note = (
                f"🟣 **Priority-Aware Adaptive (PAALB)**: makespan = {pa.makespan:.2f} tu, "
                f"avg response time = {pa.average_response_time:.2f} tu "
                f"(avg queue wait = {pa.average_waiting_time:.2f} tu across {pa.queued_task_count} queued tasks)."
            )
            if pt_rows and pt_rows[0]["Task Count"] > 0:
                prod_row = pt_rows[0]
                exp_row  = pt_rows[1]
                low_row  = pt_rows[2]
                pa_note += (
                    f" For the **Official Production Tier (priorities 9–11, {prod_row['Task Count']} tasks)**, "
                    f"PAALB reduced turnaround time from {prod_row['Traditional Throttled Avg RT (tu)']} tu to "
                    f"{prod_row['PAALB Avg RT (tu)']} tu ({prod_row['Percentage Change']}). "
                    f"For the **High-Priority Experimental Group (priorities 8–11, {exp_row['Task Count']} tasks)**, "
                    f"turnaround time was reduced from {exp_row['Traditional Throttled Avg RT (tu)']} tu to "
                    f"{exp_row['PAALB Avg RT (tu)']} tu ({exp_row['Percentage Change']}). "
                    f"For the **Low-Priority Group ({low_row['Task Count']} tasks)**, response time changed from "
                    f"{low_row['Traditional Throttled Avg RT (tu)']} tu to {low_row['PAALB Avg RT (tu)']} tu ({low_row['Percentage Change']}), "
                    f"with dynamic aging bounding overtaking to 40 time units relative to newly arriving tasks."
                )
            else:
                pa_note += (
                    " PAALB uses multi-criteria scoring to prioritize latency-sensitive workloads while dynamic aging "
                    "establishes a 40-unit overtaking horizon relative to newly arriving tasks."
                )
            notes.append(pa_note)

        for note in notes:
            st.markdown(note)

        st.caption(
            "ℹ️ Metrics use a consistent discrete-event timing and execution model: "
            "processing rate = 1 unit/time unit per VM. "
            "Round Robin models distributed per-VM FIFO queues; Least-Loaded Dynamic dispatches to the VM with lowest pending completion time; Traditional Throttled throttles intake via availability table and a central FIFO queue; PAALB prioritizes tasks via multi-criteria scoring and dynamic aging."
        )

        # ── Plotly Charts ─────────────────────────────────────────────────────
        chart_series = [
            ("Round Robin", rr, "#3b82f6"),
            ("Least-Loaded Dynamic", th, "#f97316"),
        ]
        if tt:
            chart_series.append(("Traditional Throttled", tt, "#10b981"))
        if pa:
            chart_series.append(("PAALB (Proposed)", pa, "#8b5cf6"))

        _ALGO_LABELS = [item[0] for item in chart_series]
        _COLORS      = [item[2] for item in chart_series]
        _ART_VALS    = [item[1].average_response_time for item in chart_series]
        _ART_TEXT    = [f"{item[1].average_response_time:.2f}" for item in chart_series]
        _TP_VALS     = [item[1].throughput for item in chart_series]
        _TP_TEXT     = [f"{item[1].throughput:.4f}" for item in chart_series]
        _CU_VALS     = [item[1].cluster_utilization for item in chart_series]
        _CU_TEXT     = [f"{item[1].cluster_utilization:.2f}%" for item in chart_series]
        _LI_VALS     = [item[1].load_imbalance for item in chart_series]
        _LI_TEXT     = [f"{item[1].load_imbalance} units" for item in chart_series]

        with st.expander("📊  View Performance Charts", expanded=True):
            ch_col1, ch_col2 = st.columns(2)

            # Chart 1: Average Response Time
            with ch_col1:
                fig1 = go.Figure(go.Bar(
                    x=_ALGO_LABELS,
                    y=_ART_VALS,
                    marker_color=_COLORS,
                    text=_ART_TEXT,
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
                    y=_TP_VALS,
                    marker_color=_COLORS,
                    text=_TP_TEXT,
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
                    y=_CU_VALS,
                    marker_color=_COLORS,
                    text=_CU_TEXT,
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
                    y=_LI_VALS,
                    marker_color=_COLORS,
                    text=_LI_TEXT,
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
    elif "traditional" in algo_name.lower():
        algo_desc = (
            "**Traditional Throttled failover:** After the failure, the failed VM was "
            f"removed from the availability table. Subsequent tasks were dispatched "
            f"to the {fs['final_active_vms']} remaining available VMs or queued if busy."
        )
    elif "paalb" in algo_name.lower() or "priority" in algo_name.lower():
        algo_desc = (
            "**PAALB failover:** After the failure, the failed VM was removed from the active "
            "pool. Subsequent tasks were evaluated via multi-criteria scoring and dispatched to "
            f"the {fs['final_active_vms']} remaining healthy VMs (min-load selection)."
        )
    else:
        algo_desc = (
            "**Least-Loaded Dynamic failover:** After the failure, the least-load "
            "selector excluded the failed VM from all subsequent decisions — "
            f"all new tasks were directed to the {fs['final_active_vms']} "
            "remaining available VMs. (Previously labeled Throttled failover)."
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
_LL  = "Least-Loaded Dynamic (Existing Variant)"
_TT  = "Traditional Throttled"
_PA  = "Priority-Aware Adaptive (PAALB)"
_TH  = _LL
_C_RR = "#3b82f6"   # blue
_C_TH = "#f97316"   # orange
_C_TT = "#10b981"   # emerald green
_C_PA = "#8b5cf6"   # purple

if not scal:
    st.markdown("""
    <div class="empty-state-box">
        📈 Click <strong>Run Scalability Test</strong> in the sidebar to benchmark algorithms across multiple workload sizes (10 / 50 / 100 / 500 tasks).
    </div>
    """, unsafe_allow_html=True)
else:
    # ── Derive per-algorithm series ───────────────────────────────────────────
    rr_rows = [r for r in scal if r["algorithm"] == _RR]
    th_rows = [r for r in scal if r["algorithm"] in (_LL, "Throttled (Dynamic)")]
    tt_rows = [r for r in scal if r["algorithm"] == _TT]
    pa_rows = [r for r in scal if r["algorithm"] in (_PA, "PAALB")]
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
    def _make_line_chart(rr_y, th_y, x_labels, title, yaxis_title, tt_y=None, pa_y=None):
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x_labels, y=rr_y, mode="lines+markers",
            name="Round Robin", line=dict(color=_C_RR, width=2),
            marker=dict(size=8),
        ))
        fig.add_trace(go.Scatter(
            x=x_labels, y=th_y, mode="lines+markers",
            name="Least-Loaded Dynamic", line=dict(color=_C_TH, width=2),
            marker=dict(size=8),
        ))
        if tt_y:
            fig.add_trace(go.Scatter(
                x=x_labels, y=tt_y, mode="lines+markers",
                name="Traditional Throttled", line=dict(color=_C_TT, width=2),
                marker=dict(size=8),
            ))
        if pa_y:
            fig.add_trace(go.Scatter(
                x=x_labels, y=pa_y, mode="lines+markers",
                name="PAALB (Proposed)", line=dict(color=_C_PA, width=2),
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

        rr_rt   = [r["avg_response_time"] for r in rr_rows]
        th_rt   = [r["avg_response_time"] for r in th_rows]
        tt_rt   = [r["avg_response_time"] for r in tt_rows] if tt_rows else None
        pa_rt   = [r["avg_response_time"] for r in pa_rows] if pa_rows else None
        rr_tp   = [r["throughput"]        for r in rr_rows]
        th_tp   = [r["throughput"]        for r in th_rows]
        tt_tp   = [r["throughput"]        for r in tt_rows] if tt_rows else None
        pa_tp   = [r["throughput"]        for r in pa_rows] if pa_rows else None
        rr_imb  = [r["load_imbalance"]    for r in rr_rows]
        th_imb  = [r["load_imbalance"]    for r in th_rows]
        tt_imb  = [r["load_imbalance"]    for r in tt_rows] if tt_rows else None
        pa_imb  = [r["load_imbalance"]    for r in pa_rows] if pa_rows else None
        rr_vm   = [r["final_vms"]         for r in rr_rows]
        th_vm   = [r["final_vms"]         for r in th_rows]
        tt_vm   = [r["final_vms"]         for r in tt_rows] if tt_rows else None
        pa_vm   = [r["final_vms"]         for r in pa_rows] if pa_rows else None
        rr_util = [r["cluster_util"]      for r in rr_rows]
        th_util = [r["cluster_util"]      for r in th_rows]
        tt_util = [r["cluster_util"]      for r in tt_rows] if tt_rows else None
        pa_util = [r["cluster_util"]      for r in pa_rows] if pa_rows else None

        with sc_col1:
            st.plotly_chart(
                _make_line_chart(
                    rr_rt, th_rt, task_labels_rr,
                    "Avg Response Time vs Workload — Lower is better",
                    "Simulated time units",
                    tt_y=tt_rt,
                    pa_y=pa_rt,
                ),
                use_container_width=True,
            )
        with sc_col2:
            st.plotly_chart(
                _make_line_chart(
                    rr_tp, th_tp, task_labels_rr,
                    "Throughput vs Workload — Higher is better",
                    "Tasks / time unit",
                    tt_y=tt_tp,
                    pa_y=pa_tp,
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
                    tt_y=tt_imb,
                    pa_y=pa_imb,
                ),
                use_container_width=True,
            )
        with sc_col4:
            st.plotly_chart(
                _make_line_chart(
                    rr_vm, th_vm, task_labels_rr,
                    "Active VMs vs Workload",
                    "Active VM count",
                    tt_y=tt_vm,
                    pa_y=pa_vm,
                ),
                use_container_width=True,
            )

        # Cluster utilization chart in a full-width row
        st.plotly_chart(
            _make_line_chart(
                rr_util, th_util, task_labels_rr,
                "Cluster Utilization vs Workload — Higher is better",
                "Utilization %",
                tt_y=tt_util,
                pa_y=pa_util,
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
                f"Least-Loaded Dynamic by **{th_rt_delta:+.0f} tu**."
            )

    # Per-level imbalance comparison
    for rr_r, th_r in zip(rr_rows, th_rows):
        t = rr_r["tasks"]
        if rr_r["load_imbalance"] > th_r["load_imbalance"]:
            interp.append(
                f"🟠 At **{t} tasks**, Least-Loaded Dynamic had lower load imbalance "
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
- ⚡ **Least-Loaded Dynamic (Existing Variant)** — Assigns each task to the available VM with minimum cumulative workload (previously labeled Throttled).
- ⏳ **Traditional Throttled (Baseline)** — Canonical availability-table baseline (Wickremasinghe et al., 2010) with first-available dispatch, busy state tracking, and FIFO waiting queue.
- 🎯 **Priority-Aware Adaptive (PAALB)** — Proposed multi-criteria heuristic scoring tasks by normalized priority (0.45), task length (0.35), and dynamic aging (0.20 with $T_{\text{ref}}=10.0$), dispatching to the minimum-load available VM. Features a 40-unit overtaking horizon relative to newly arriving tasks, yielding a 65.4% turnaround reduction for the official Production Tier (priorities 9–11) and 60.4% for the High-Priority Experimental Group (8–11), with empirically demonstrated bounded queue delays across finite trace workloads.

**Supporting Features:**
- ⚡ Automated Scaling Listener — adjusts VM count based on workload pressure
- 📊 Performance Metrics — makespan, response time, throughput, utilization, and queue waiting time
- 📈 Workload & Scalability Testing — 10 / 50 / 100 / 500 task progressions
- 🛡️ VM Failure & Failover — deterministic fault tolerance simulation
- 🌐 Google Cluster Trace Integration — evaluation on real Google cluster workload data (CC-BY 4.0)
""")
    with col_b:
        st.markdown("""
**Key Concepts Demonstrated:**
- Static vs dynamic scheduling trade-offs
- Cluster utilization and load imbalance measurement
- Elastic scaling (scale-up / scale-down)
- Fault tolerance via failover (no failed VM receives new tasks)
- Cyclic Round Robin index continuity across VM failure
- Trace-informed workload replay on empirical cloud demand distributions

**Workload Sources & Terminology:**
- *Synthetic Workload* — Configurable mixed distribution (~50% small, 30% medium, 20% large)
- *Google Cluster Trace* — Empirical task submissions from Google Cluster Data 2011-2 (v2.1). Supports both genuine time-staggered arrivals (500 records spanning 125.19s) and initial cell snapshot ($t=0$ batch). Normalized via `clamp(round(CPU_Request * 100), 1, 100)` into simulator processing units
- *Discrete-Event Execution Model* — Evaluates all algorithms under a unified execution timeline. Round Robin models distributed per-VM FIFO queues; Least-Loaded Dynamic dispatches to the VM with lowest pending completion time; Traditional Throttled throttles intake via availability table and a central FIFO queue
- *Assigned Workload* — cumulative processing units assigned (not real CPU%)
- *Cluster Workload Pressure* — total_req ÷ (active_vms × capacity) × 100 (uncapped)
- *Makespan* — total duration from simulation start to completion of the final task across all VMs
- *Throughput* — tasks completed per simulated time unit
""")

# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("🎓 Cloud Computing Project · Static vs Dynamic Load Balancing")

# Static vs Dynamic Load Balancing Algorithms
### Cloud Computing — Load Balancing Simulation and Performance Analysis

A college Cloud Computing project that simulates and compares **static** and **dynamic** load balancing algorithms with an **Automated Scaling Listener** in a cloud environment.

---

## 🗂️ Project Structure

```
Cloud Project/
│
├── app.py                  # Main Streamlit dashboard (entry point)
│
├── algorithms/             # Load balancing algorithm implementations
│   ├── __init__.py
│   ├── round_robin.py      # [Phase 3] Static Round Robin
│   ├── throttled.py        # [Phase 4] Least-Loaded Dynamic (previously labeled Throttled)
│   ├── traditional_throttled.py # [Phase 12] Traditional Throttled baseline (CloudAnalyst)
│   └── paalb.py            # [Phase 14] Priority-Aware Adaptive Load Balancer (PAALB)
│
├── simulation/             # Simulation engine and helpers
│   ├── __init__.py
│   ├── engine.py           # Central simulation state + lifecycle
│   ├── vm.py               # VM dataclass + create_vms()
│   ├── task.py             # Task dataclass
│   ├── workload.py         # Task/workload generation
│   ├── scaling.py          # [Phase 5] Automated Scaling Listener
│   ├── metrics.py          # [Phase 6 & 12] Performance & queueing metrics
│   └── google_trace.py     # [Phase 11] Google Cluster Trace adapter
│
├── utils/                  # Utility helpers (future phases)
│   └── __init__.py
│
├── data/                   # Simulation output logs & trace samples
│   ├── .gitkeep
│   ├── google_cluster_trace_sample.csv    # Genuine 500-record staggered Google 2011-2 trace (varied arrival timestamps)
│   └── google_cluster_trace_snapshot.csv  # 500-record initial cell snapshot (t=0 batch baseline)
│
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

---

## ⚙️ Setup & Installation

```bash
pip3 install -r requirements.txt
```

---

## ▶️ Running the Application

```bash
streamlit run app.py
```

Opens at **http://localhost:8501**

---

## 🚦 Development Phases

| Phase | Status | Description |
|-------|--------|-------------|
| **Phase 1** | ✅ Complete | Project foundation & dashboard UI |
| **Phase 2** | ✅ Complete | VM model, Task model, Workload generator, Simulation engine |
| **Phase 3** | ✅ Complete | Round Robin Static Load Balancing |
| **Phase 4** | ✅ Complete | Least-Loaded Dynamic (Existing Variant; previously labeled Throttled) |
| **Phase 5** | ✅ Complete | Automated Scaling Listener (scale-up & scale-down) |
| **Phase 6** | ✅ Complete | Performance metrics & algorithm comparison charts |
| **Phase 7** | ✅ Complete | Workload/scalability simulation |
| **Phase 8** | ✅ Complete | VM failure & failover |
| **Phase 9** | ✅ Complete | Resource cluster visualization & polish |
| **Phase 10** | ✅ Complete | Submission readiness |
| **Phase 11** | ✅ Complete | Google Cluster Trace workload integration |
| **Phase 12** | ✅ Complete | Traditional Throttled baseline (CloudAnalyst availability table & FIFO queue) |
| **Phase 12.1** | ✅ Complete | Trace timing alignment (staggered arrivals) & fair algorithm comparisons |
| **Phase 13 / 13.1** | ✅ Complete | PAALB algorithm design, scratch prototype & rigorous arithmetic audit |
| **Phase 14** | ✅ Complete | Proposed Priority-Aware Adaptive Load Balancer (PAALB) full integration |

---

## 📚 Algorithms

### Static — Round Robin (Phase 3)
Tasks assigned in fixed cyclic order: `VM-1 → VM-2 → … → VM-N → VM-1 → …`
No consideration of current VM load.

### Dynamic — Least-Loaded Dynamic (Existing Variant) (Phase 4)
*Academic Note:* Previously labeled in this project as "Throttled (Dynamic)". Following an academic correctness audit, this algorithm is documented as a greedy least-loaded policy rather than the traditional availability-table first-available Throttled algorithm (Wickremasinghe et al., 2010).

For every task, assigns it to the **least-loaded available VM** (minimum cumulative processing units) at that moment.
Re-inspects VM state after every assignment → truly dynamic.

### Dynamic — Traditional Throttled Baseline (Phase 12)
*Academic Reference:* CloudAnalyst: A CloudSim-based Tool for Modelling and Analysis of Large Scale Cloud Computing Environments (*Wickremasinghe, Calheiros, & Buyya, 2010*).

Implements the canonical availability-table baseline:
1. **Availability Table:** Tracks each VM's state as `AVAILABLE` or `BUSY`.
2. **First-Available Dispatch:** Scans the table from top to bottom (VM ID order) and assigns the task to the first available VM.
3. **State Transition:** The selected VM transitions to `BUSY`.
4. **Throttled FIFO Queue:** If all VMs are `BUSY`, the task enters a FIFO waiting queue.
5. **Freed VM Queue Dispatch:** Upon task completion, the VM transitions back to `AVAILABLE` and immediately pulls the next waiting task from the FIFO queue.
6. **Discrete-Event Service Model:** Simulated execution durations are deterministically derived from normalized processing units ($\text{service\_time} = \text{processing\_req} / \text{processing\_rate}$) to accurately model queueing delays, waiting times, and turnaround times ($\text{Response Time} = \text{Waiting Time} + \text{Service Time}$). Deterministic tie-breaking by VM ID handles simultaneous completions.

### Dynamic — Priority-Aware Adaptive Load Balancer (PAALB) (Phase 14)
*Academic & Design Description:* An original proposed heuristic designed for multi-tenant, heterogeneous cloud workloads with service-level priority tiers (such as Google Cluster Data). While Traditional Throttled treats all queued requests identically in a First-In, First-Out (FIFO) queue, PAALB dynamically re-scores waiting tasks using a composite utility function.

1. **Multi-Criteria Scoring Formula:**
   $$S(t, \tau) = w_p \cdot P_{\text{norm}}(t) + w_s \cdot L_{\text{norm}}(t) + w_a \cdot A(t, \tau)$$
   where:
   - **$P_{\text{norm}}(t) = \text{clamp}(p, 0, 11) / 11$**: Normalized task priority (from Google Cluster Trace priority tiers 0–11).
   - **$L_{\text{norm}}(t) = \text{clamp}\left(\frac{100 - s}{99}, 0, 1\right)$**: Normalized inverse service length (rewards shorter tasks to improve system turnaround time, inspired by Shortest Job First).
   - **$A(t, \tau) = \frac{\max(0, \tau - t_{\text{arr}})}{T_{\text{ref}}}$**: Normalized queue waiting time relative to a reference horizon ($T_{\text{ref}} = 10.0$ tu).
   - **Default Calibrated Weights**: $w_p = 0.45$ (priority weight), $w_s = 0.35$ (task length weight), $w_a = 0.20$ (aging weight), with $w_p + w_s + w_a = 1.0$.

2. **Least-Loaded VM Selection:**
   When a VM completes execution or when an idle VM is available at time $\tau$, all pending tasks are scored. The task with highest score $S(t, \tau)$ is selected (with deterministic tie-breaking: earliest arrival, then lowest `task_id`). The selected task is dispatched to the available VM with minimum cumulative workload: $\arg\min_{v \in \text{Avail}} (v.\text{current\_load}, v.\text{vm\_id})$.

3. **Dynamic Aging & Priority Overtaking Horizon:**
   To mitigate prolonged queuing of lower-priority tasks when high-priority streams arrive, the aging term increases monotonically with queue waiting time. An aged lowest-priority task ($p=0$) overtakes a newly arriving highest-priority task ($p=11$) once its waiting time reaches:
   $$\Delta t_{\text{overtake}} = \frac{w_p + w_s}{w_a} \cdot T_{\text{ref}} = \frac{0.45 + 0.35}{0.20} \times 10.0 = 40.0 \text{ time units}$$
   *Academic Scoping Note:* This 40-unit threshold mathematically functions as an **overtaking horizon relative to newly arriving tasks** in the candidate pool, rather than an unconditional mathematical guarantee against queue delay in saturated clusters. Complete absence of starvation (bounded queue delay) is an **observed empirical result on the finite trace workload**, not an unconditional theoretical guarantee under arbitrary or unbounded arrival streams.

4. **Non-Preemptive Execution:**
   Once scheduled to an available VM, tasks execute to full completion without preemption.

5. **Empirical Performance on Google Trace (500 tasks, 4 VMs):**
   - **Makespan:** $383.00$ tu (identical to Traditional Throttled and Least-Loaded Dynamic; cluster utilization $99.74\%$).
   - **Official Production Tier (Priorities 9–11, 52 tasks):** Mean response time reduced from **145.73 tu** (Traditional Throttled) to **50.43 tu** (**65.4% reduction**).
   - **High-Priority Experimental Group (Priorities 8–11, 55 tasks):** Mean response time reduced from **151.77 tu** (Traditional Throttled) to **60.12 tu** (**60.4% reduction**).
   - **Low-Priority Group (Priorities 0–2, 445 tasks):** Mean response time remains stable at **174.82 tu** (vs **172.12 tu** in Traditional Throttled, a modest $+1.57\%$ trade-off) with observed bounded queue delay (maximum wait $263.55$ tu vs $262.05$ tu in Traditional Throttled).
   - **Overall Cluster Avg Response Time:** Reduced from $169.88$ tu to $162.20$ tu (a $4.5\%$ cluster-wide improvement).

---

## ⚡ Automated Scaling Listener (Phase 5)

The Automated Scaling Listener monitors simulated workload demand against cluster
capacity and automatically adjusts the VM pool **before** the load balancer runs.

### Architecture

```
Incoming Workload
      ↓
Automated Scaling Listener   ← evaluates demand vs capacity
      ↓  (adjusts VM pool)
Load Balancer (Round Robin / Least-Loaded Dynamic)
      ↓
Active VM Cluster
```

### Workload Pressure Formula

```
Pressure % = (total task processing units) / (active VMs × VM capacity) × 100
```

This is a simulation metric (workload demand vs cluster capacity), NOT real CPU utilization.

### Scaling Thresholds (configurable in sidebar)

| Parameter            | Default | Description |
|----------------------|---------|-------------|
| Scale-Up Threshold   | **70%** | Add a VM when pressure exceeds this % |
| Scale-Down Threshold | **30%** | Remove an idle VM when pressure falls below this % |
| Minimum VMs          | **2**   | Never scale below this count |
| Maximum VMs          | **10**  | Never scale above this count |

### Scale-Up
When pressure > 70%: add VMs one at a time (recalculating after each) until
pressure ≤ threshold OR max_vms reached. Records a ScalingEvent per VM added.

### Scale-Down
When pressure < 30%: deactivate the highest-ID idle VM (LIFO order) until
pressure ≥ threshold OR min_vms reached. Records a ScalingEvent per VM removed.

### Integration with Load Balancers
After scaling, both **Round Robin** and **Least-Loaded Dynamic** operate on the adjusted
active VM pool — scaling changes actually affect task assignment.

---

## 🌐 Google Cluster Trace Integration (Phase 11)

The simulator supports real-world empirical workload evaluation using genuine trace data from Google data centers.

### Dataset Attribution & License
- **Dataset:** Google Cluster Data 2011-2 (trace version 2.1)
- **Authors:** John Wilkes and Charles Reiss (Google LLC)
- **Source:** [google/cluster-data on GitHub](https://github.com/google/cluster-data)
- **License:** Creative Commons Attribution 4.0 International ([CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/))
- **Attribution Notice:** Users of this dataset agree to cite Wilkes & Reiss, Google LLC.

### Schema & Fields Used
From the official 13-field `task_events` table:
- `timestamp`: Event time in microseconds (trace start snapshot is 0).
- `job_id`: Canonical job identifier preserved on the Task object.
- `task_index`: Task index within the job.
- `event_type`: Filtered for `0` (`SUBMIT`) events.
- `priority`: Scheduling priority (0–11).
- `cpu_request`: Normalized fraction of machine CPU capacity ($0.0 \le c \le 1.0$).
- `memory_request`: Normalized fraction of machine RAM capacity.

### Normalization Formula
Google normalizes `cpu_request` so that 1.0 represents the maximum capacity of a physical cluster machine. In our simulator, each VM has a default capacity of 100 processing units.
The fractional core demand maps directly into simulator processing units via:

$$\text{Processing Units} = \max\left(1, \min\left(100, \text{round}(\text{cpu\_request} \times 100)\right)\right)$$

Original measurements (`raw_cpu_request`, `raw_mem_request`, `job_id`, `timestamp`) are preserved separately on each `Task` and displayed in the dashboard.

### Workload Replay Semantics & Limitations
- **Trace-Informed Workload Replay:** The simulation replays the empirical resource-demand distribution and job structure from Google's trace to evaluate static vs. dynamic load balancing on real-world request sizes.
- **Scope & Limitations:** This experiment does not claim to simulate Google's multi-cell Borg scheduling decisions, production eviction behaviors, or physical hardware latency.

---

## ⏱️ Trace Timing Alignment & Fair Comparison Contract (Phase 12.1)

Phase 12.1 addresses discrete-event timing comparability across all three algorithms when evaluating both batch and time-staggered trace workloads.

### 1. Improved Google Trace Workload Samples
- **Staggered Trace (`data/google_cluster_trace_sample.csv`):** 500 genuine task submission records (`SUBMIT`, `event_type == 0`) from `part-00001-of-00500.csv.gz` with 500 distinct timestamps ($t \in [5612587446, 5737776861]$ μs, spanning 125.19s). Microsecond timestamps are anchored at $t_0$ and converted to relative simulation arrival times in seconds: $\text{arrival\_time} = (t - t_0) / 10^6$.
- **Snapshot Trace (`data/google_cluster_trace_snapshot.csv`):** Preserved backup of the initial 500-record cell state snapshot ($t = 0$ batch submission) ensuring 100% numerical backwards compatibility with Phase 11/12 benchmarks.

### 2. Unified Simulation Contract
All algorithms operate under the exact same inputs and time contract:
- **Identical Inputs:** Canonical tasks generated in identical order with identical `task_id`, `arrival_time`, and `processing_req`.
- **Deterministic Service Model:** $\text{service\_time} = \max(0.1, \text{round}(\text{processing\_req} / \text{processing\_rate}, 4))$. Under unit rate ($1.0$), service duration equals normalized processing units.
- **Queueing Architectures Evaluated:**
  - **Round Robin (Static):** Models distributed per-VM FIFO queues. Incoming tasks are assigned cyclically at arrival $t_{\text{arr}}$ and begin execution once previous tasks on that VM finish: $\text{start\_time} = \max(t_{\text{arr}}, \text{vm\_busy\_until})$.
  - **Least-Loaded Dynamic (Existing Variant):** Immediately dispatches incoming tasks at $t_{\text{arr}}$ to the available VM with lowest pending completion time $\arg\min_v (\max(t_{\text{arr}}, \text{busy\_until}[v]), v.\text{current\_load}, v.\text{vm\_id})$.
  - **Traditional Throttled (Baseline):** Centralized FIFO waiting queue governed by an availability table (`AVAILABLE` / `BUSY`). Tasks wait until a VM completes execution and becomes available.
- **Standardized Metric Definitions:**
  - $\text{Makespan} = \max_{t \in \text{tasks}} (\text{completion\_time}_t)$
  - $\text{Turnaround (Response Time)} = \text{completion\_time} - \text{arrival\_time} = \text{Waiting Time} + \text{Service Time}$
  - $\text{Queue Waiting Time} = \text{start\_time} - \text{arrival\_time}$
  - $\text{Throughput} = \frac{\text{Completed Tasks}}{\text{Makespan}}$
  - $\text{Cluster Utilization} = \frac{\text{Total Workload Units}}{\text{Active VMs} \times \text{Makespan}} \times 100$

### 3. Mathematical Backward Compatibility on Batch Workloads
When all tasks arrive simultaneously at $t_{\text{arr}} = 0$, the discrete-event timing model produces results mathematically identical to the cumulative sequential model:
- Tasks execute back-to-back without idle gaps.
- Makespan equals $\max(\text{vm.current\_load})$.
- Turnaround time equals cumulative processing workload.
- Regression tests from Phase 4, 6, and 12 remain 100% satisfied.

---

---

## 🛠️ Tech Stack

- **Python 3.10+**
- **Streamlit** — Dashboard UI
- **Plotly** — Charts (Phase 6+)
- **Pandas** — Data handling

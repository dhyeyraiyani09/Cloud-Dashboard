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
│   └── throttled.py        # [Phase 4] Least-Loaded Dynamic (previously labeled Throttled)
│
├── simulation/             # Simulation engine and helpers
│   ├── __init__.py
│   ├── engine.py           # Central simulation state + lifecycle
│   ├── vm.py               # VM dataclass + create_vms()
│   ├── task.py             # Task dataclass
│   ├── workload.py         # Task/workload generation
│   ├── scaling.py          # [Phase 5] Automated Scaling Listener
│   └── google_trace.py     # [Phase 11] Google Cluster Trace adapter
│
├── utils/                  # Utility helpers (future phases)
│   └── __init__.py
│
├── data/                   # Simulation output logs & trace samples
│   ├── .gitkeep
│   └── google_cluster_trace_sample.csv  # Genuine 500-record Google 2011-2 trace sample
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
| **Phase 6** | 🔜 Planned | Performance metrics & algorithm comparison charts |
| **Phase 7** | 🔜 Planned | Workload/scalability simulation |
| **Phase 8** | 🔜 Planned | VM failure & failover |

---

## 📚 Algorithms

### Static — Round Robin (Phase 3)
Tasks assigned in fixed cyclic order: `VM-1 → VM-2 → … → VM-N → VM-1 → …`
No consideration of current VM load.

### Dynamic — Least-Loaded Dynamic (Existing Variant) (Phase 4)
*Academic Note:* Previously labeled in this project as "Throttled (Dynamic)". Following an academic correctness audit, this algorithm is documented as a greedy least-loaded policy rather than the traditional availability-table first-available Throttled algorithm (Wickremasinghe et al., 2010).

For every task, assigns it to the **least-loaded available VM** (minimum cumulative processing units) at that moment.
Re-inspects VM state after every assignment → truly dynamic.

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

## 🛠️ Tech Stack

- **Python 3.10+**
- **Streamlit** — Dashboard UI
- **Plotly** — Charts (Phase 6+)
- **Pandas** — Data handling

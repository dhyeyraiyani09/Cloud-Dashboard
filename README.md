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
│   └── throttled.py        # [Phase 4] Dynamic Throttled
│
├── simulation/             # Simulation engine and helpers
│   ├── __init__.py
│   ├── engine.py           # Central simulation state + lifecycle
│   ├── vm.py               # VM dataclass + create_vms()
│   ├── task.py             # Task dataclass
│   ├── workload.py         # Task/workload generation
│   └── scaling.py          # [Phase 5] Automated Scaling Listener
│
├── utils/                  # Utility helpers (future phases)
│   └── __init__.py
│
├── data/                   # Simulation output logs
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
| **Phase 4** | ✅ Complete | Throttled Dynamic Load Balancing |
| **Phase 5** | ✅ Complete | Automated Scaling Listener (scale-up & scale-down) |
| **Phase 6** | 🔜 Planned | Performance metrics & algorithm comparison charts |
| **Phase 7** | 🔜 Planned | Workload/scalability simulation |
| **Phase 8** | 🔜 Planned | VM failure & failover |

---

## 📚 Algorithms

### Static — Round Robin (Phase 3)
Tasks assigned in fixed cyclic order: `VM-1 → VM-2 → … → VM-N → VM-1 → …`
No consideration of current VM load.

### Dynamic — Throttled Load Balancing (Phase 4)
For every task, assigns it to the **least-loaded available VM** at that moment.
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
Load Balancer (Round Robin / Throttled)
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
After scaling, both **Round Robin** and **Throttled** operate on the adjusted
active VM pool — scaling changes actually affect task assignment.

---

## 🛠️ Tech Stack

- **Python 3.10+**
- **Streamlit** — Dashboard UI
- **Plotly** — Charts (Phase 6+)
- **Pandas** — Data handling

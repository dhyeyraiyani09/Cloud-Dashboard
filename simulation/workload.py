"""
simulation/workload.py — Workload (task) generator.

Generates a configurable list of Tasks with varied sizes so that
later phases can meaningfully demonstrate the difference between
static (Round Robin) and dynamic (Throttled) algorithms.

Task sizes follow a realistic mixed distribution:
  - 50% small tasks   (size 10–30)
  - 30% medium tasks  (size 31–70)
  - 20% large tasks   (size 71–100)

This distribution is intentional: static algorithms like Round Robin
will not account for the size difference and may overload some VMs,
while dynamic algorithms like Throttled will handle it better.
"""

import random
from typing import List
from simulation.task import Task


# Seed can be fixed for reproducibility during testing, or None for random runs.
_DEFAULT_SEED = 42


def generate_tasks(num_tasks: int, seed: int = _DEFAULT_SEED) -> List[Task]:
    """
    Generate a list of Task objects with mixed workload sizes.

    Parameters
    ----------
    num_tasks : int — Number of tasks to generate (from the dashboard slider)
    seed      : int — Random seed for reproducibility (default 42)

    Returns
    -------
    List[Task] — Tasks in arrival order, all in Pending state

    Task size distribution
    ----------------------
    Small  (10–30)  : ~50% of tasks — lightweight operations
    Medium (31–70)  : ~30% of tasks — normal cloud requests
    Large  (71–100) : ~20% of tasks — heavy compute jobs
    """
    rng = random.Random(seed)
    tasks: List[Task] = []

    for i in range(num_tasks):
        # Determine size category based on probability
        roll = rng.random()
        if roll < 0.50:
            size = rng.randint(10, 30)    # small
        elif roll < 0.80:
            size = rng.randint(31, 70)    # medium
        else:
            size = rng.randint(71, 100)   # large

        task = Task(
            task_id        = i + 1,
            name           = f"T-{i + 1}",
            size           = size,
            processing_req = size,         # 1 size unit = 1 processing unit
            arrival_order  = i + 1,
        )
        tasks.append(task)

    return tasks


def calculate_total_workload(tasks: List[Task]) -> int:
    """
    Calculate the total processing units across all tasks.

    Used to compute the Workload % metric on the dashboard:
        Workload % = (total_processing_req / (num_vms * vm_capacity)) * 100

    This is a simulation metric, not real CPU utilization.
    """
    return sum(t.processing_req for t in tasks)

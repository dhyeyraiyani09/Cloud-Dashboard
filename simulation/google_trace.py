"""
simulation/google_trace.py — Google Cluster Trace Adapter.

This module provides a dedicated adapter for loading, validating, and converting
real Google Cluster Workload Traces (specifically the official Google Cluster Data
2011-2 / v2.1 trace format) into the simulator's Task representation.

Attribution & License:
----------------------
Dataset: Google Cluster Data (clusterdata-2011-2 / trace version 2.1)
Authors: John Wilkes and Charles Reiss (Google LLC)
Repository: https://github.com/google/cluster-data
License: Creative Commons Attribution 4.0 International (CC-BY 4.0)
Terms: https://creativecommons.org/licenses/by/4.0/

Official Schema (task_events table, 13 fields):
----------------------------------------------
1. timestamp                      : int   — time in microseconds since trace start
2. missing_info                   : int   — reason code if record synthesized (empty if normal)
3. job_id                         : int   — canonical job identifier
4. task_index                     : int   — task index within the job (0-based)
5. machine_id                     : int   — machine ID (empty if unassigned)
6. event_type                     : int   — 0=SUBMIT, 1=QUEUE, 2=ENABLE, 3=SCHEDULE,
                                            4=EVICT, 5=FAIL, 6=FINISH, 7=KILL, 8=LOST
7. user_name                      : str   — hashed anonymized user identity
8. scheduling_class               : int   — latency sensitivity (0=batch, 3=high priority)
9. priority                       : int   — priority tier (0-11)
10. cpu_request                   : float — normalized fraction of machine CPU capacity (0.0–1.0)
11. memory_request                : float — normalized fraction of machine RAM capacity (0.0–1.0)
12. disk_request                  : float — normalized fraction of local disk space (0.0–1.0)
13. different_machine_constraint  : int   — 0 or 1

Workload Transformation & Normalization Model:
----------------------------------------------
1. Selection:
   Filters for task submission events (event_type == 0: SUBMIT) with positive CPU requests.
   Snapshot events with missing or zero CPU requests are recorded as skipped.

2. Normalization Formula:
   Google normalizes cpu_request such that 1.0 represents the capacity of the largest
   machine in the cell. In our simulator, a VM has a default capacity of 100 units.
   We map the fractional machine request directly into simulator processing units:

       processing_units = max(1, min(100, int(round(cpu_request * 100))))
       task.size        = processing_units
       task.processing_req = processing_units

   This deterministic mapping preserves the empirical workload distribution while keeping
   original measurements (raw_cpu_request, raw_mem_request, job_id, timestamp) accessible
   on each Task object without silently conflating them with simulator units.

3. Timing Semantics (Trace-Informed Workload Replay):
   Timestamps from Google Cluster Data represent event time in microseconds. The simulator
   operates as a trace-informed workload replay evaluating static Round Robin vs. dynamic
   Throttled load balancing on real workload size distributions; it does not simulate
   Google's internal multi-cell Borg scheduling decisions.
"""

import csv
import gzip
import io
import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Union, Tuple, Any

from simulation.task import Task


DEFAULT_TRACE_SAMPLE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "google_cluster_trace_sample.csv"
)

TRACE_VERSION = "Google Cluster Data 2011-2 (v2.1)"
TRACE_LICENSE = "Creative Commons Attribution 4.0 International (CC-BY 4.0)"
TRACE_SOURCE_URL = "https://github.com/google/cluster-data"


@dataclass
class TraceParseResult:
    """
    Holds the output of a trace parsing operation including converted tasks,
    reproducibility metadata, and parsing statistics.
    """
    tasks              : List[Task]
    records_read       : int
    records_accepted   : int
    records_skipped    : int
    skip_reasons       : Dict[str, int]
    trace_version      : str           = TRACE_VERSION
    normalization_rule : str           = "processing_units = clamp(round(cpu_request * 100), 1, 100)"
    min_raw_cpu        : float         = 0.0
    max_raw_cpu        : float         = 0.0
    avg_raw_cpu        : float         = 0.0
    total_proc_units   : int           = 0

    def summary(self) -> Dict[str, Any]:
        """Return a summary dictionary suitable for dashboard presentation."""
        return {
            "Trace Version"       : self.trace_version,
            "Records Read"        : self.records_read,
            "Records Accepted"    : self.records_accepted,
            "Records Skipped"     : self.records_skipped,
            "Skip Reasons"        : self.skip_reasons,
            "Normalization"       : self.normalization_rule,
            "Min CPU Request"     : f"{self.min_raw_cpu:.5f}" if self.records_accepted else "N/A",
            "Max CPU Request"     : f"{self.max_raw_cpu:.5f}" if self.records_accepted else "N/A",
            "Mean CPU Request"    : f"{self.avg_raw_cpu:.5f}" if self.records_accepted else "N/A",
            "Total Proc. Units"   : self.total_proc_units,
        }


def parse_google_trace(
    source: Union[str, bytes, io.IOBase],
    max_tasks: Optional[int] = None,
) -> TraceParseResult:
    """
    Parse a Google Cluster Trace file or stream and convert records into Tasks.

    Parameters
    ----------
    source    : Path to file (str), raw bytes (e.g. from file uploader),
                or an open text/binary file-like object.
    max_tasks : Optional maximum number of accepted tasks to return.

    Returns
    -------
    TraceParseResult containing the accepted Task objects and parsing metrics.

    Raises
    ------
    ValueError : If source is empty, missing required data, or cannot be parsed.
    """
    # ── Normalize input stream ────────────────────────────────────────────────
    text_stream, should_close = _open_source_stream(source)

    try:
        reader = csv.reader(text_stream)

        # ── Detect Header vs Headerless ─────────────────────────────────────────
        first_row = None
        for row in reader:
            if row and any(cell.strip() for cell in row):
                first_row = row
                break

        if first_row is None:
            raise ValueError("Google Cluster Trace file is empty or contains no data.")

        has_header, col_map = _detect_columns(first_row)

        records_read = 0
        records_accepted = 0
        records_skipped = 0
        skip_reasons: Dict[str, int] = {}

        tasks: List[Task] = []
        raw_cpus: List[float] = []

        def _record_skip(reason: str):
            nonlocal records_skipped
            records_skipped += 1
            skip_reasons[reason] = skip_reasons.get(reason, 0) + 1

        rows_to_process = []
        if not has_header:
            rows_to_process.append(first_row)

        for row in reader:
            if row and any(cell.strip() for cell in row):
                rows_to_process.append(row)

        for row in rows_to_process:
            records_read += 1

            if len(row) < 10:
                _record_skip("malformed_row_too_few_columns")
                continue

            # Extract fields via col_map or positional indexing
            try:
                cpu_str = _get_field(row, col_map, "cpu_request", default_idx=9)
                if not cpu_str or not cpu_str.strip():
                    _record_skip("missing_cpu_request")
                    continue

                raw_cpu = float(cpu_str.strip())
                if raw_cpu <= 0.0:
                    _record_skip("zero_or_negative_cpu_request")
                    continue

                # Filter by event_type if available (0 = SUBMIT)
                event_type_str = _get_field(row, col_map, "event_type", default_idx=5)
                if event_type_str and event_type_str.strip():
                    try:
                        event_type = int(event_type_str.strip())
                        if event_type != 0:
                            _record_skip(f"non_submit_event_type_{event_type}")
                            continue
                    except ValueError:
                        pass  # If not an integer event type, continue parsing

                # Optional metadata extraction
                job_id = _parse_int(_get_field(row, col_map, "job_id", default_idx=2))
                task_index = _parse_int(_get_field(row, col_map, "task_index", default_idx=3))
                timestamp = _parse_int(_get_field(row, col_map, "timestamp", default_idx=0))
                priority = _parse_int(_get_field(row, col_map, "priority", default_idx=8))
                raw_mem = _parse_float(_get_field(row, col_map, "memory_request", default_idx=10))

            except (ValueError, TypeError):
                _record_skip("invalid_numeric_field")
                continue

            # ── Normalization Transformation ──────────────────────────────────
            # Map fractional machine CPU [0.0, 1.0] to simulated VM capacity [1, 100]
            proc_units = max(1, min(100, int(round(raw_cpu * 100))))

            idx = len(tasks) + 1
            task = Task(
                task_id         = idx,
                name            = f"T-{idx}",
                size            = proc_units,
                processing_req  = proc_units,
                arrival_order   = idx,
                source          = "google_trace",
                job_id          = job_id,
                task_index      = task_index,
                timestamp       = timestamp,
                raw_cpu_request = raw_cpu,
                raw_mem_request = raw_mem,
                priority        = priority,
            )

            tasks.append(task)
            raw_cpus.append(raw_cpu)
            records_accepted += 1

            if max_tasks is not None and len(tasks) >= max_tasks:
                break

        if records_accepted == 0:
            raise ValueError(
                f"No usable task submission records found in trace. "
                f"Read {records_read} records, all were skipped: {skip_reasons}"
            )

        min_cpu = min(raw_cpus) if raw_cpus else 0.0
        max_cpu = max(raw_cpus) if raw_cpus else 0.0
        avg_cpu = (sum(raw_cpus) / len(raw_cpus)) if raw_cpus else 0.0
        total_units = sum(t.processing_req for t in tasks)

        return TraceParseResult(
            tasks              = tasks,
            records_read       = records_read,
            records_accepted   = records_accepted,
            records_skipped    = records_skipped,
            skip_reasons       = skip_reasons,
            min_raw_cpu        = min_cpu,
            max_raw_cpu        = max_cpu,
            avg_raw_cpu        = avg_cpu,
            total_proc_units   = total_units,
        )

    finally:
        if should_close:
            text_stream.close()


def load_bundled_google_trace(max_tasks: Optional[int] = None) -> TraceParseResult:
    """
    Load the genuine bundled Google Cluster Trace 2011-2 sample from data/.

    Parameters
    ----------
    max_tasks : Optional maximum number of tasks to load.

    Returns
    -------
    TraceParseResult containing the verified tasks.
    """
    if not os.path.exists(DEFAULT_TRACE_SAMPLE_PATH):
        raise FileNotFoundError(
            f"Bundled Google Cluster Trace sample not found at: {DEFAULT_TRACE_SAMPLE_PATH}"
        )
    return parse_google_trace(DEFAULT_TRACE_SAMPLE_PATH, max_tasks=max_tasks)


# ── Helper parsing utilities ──────────────────────────────────────────────────

def _open_source_stream(source: Any) -> Tuple[io.TextIOBase, bool]:
    """Return a readable text stream and a boolean indicating if it should be closed."""
    if isinstance(source, str):
        if not os.path.exists(source):
            raise FileNotFoundError(f"Trace file not found: {source}")
        if source.endswith(".gz"):
            return io.TextIOWrapper(gzip.open(source, "rb"), encoding="utf-8"), True
        return open(source, "r", encoding="utf-8", errors="replace"), True

    if isinstance(source, bytes):
        # Check for gzip magic header (0x1f 0x8b)
        if len(source) >= 2 and source[:2] == b"\x1f\x8b":
            return io.TextIOWrapper(gzip.GzipFile(fileobj=io.BytesIO(source)), encoding="utf-8"), True
        return io.StringIO(source.decode("utf-8", errors="replace")), True

    if hasattr(source, "read"):
        # Handle Streamlit UploadedFile or file-like object
        first_bytes = source.read(2)
        source.seek(0)
        if first_bytes == b"\x1f\x8b":
            return io.TextIOWrapper(gzip.GzipFile(fileobj=source), encoding="utf-8"), False
        if isinstance(source, io.TextIOBase):
            return source, False
        return io.TextIOWrapper(source, encoding="utf-8", errors="replace"), False

    raise TypeError(f"Unsupported trace source type: {type(source)}")


def _detect_columns(first_row: List[str]) -> Tuple[bool, Dict[str, int]]:
    """
    Detect whether the first row is a header, and build a column name -> index mapping.
    """
    clean_row = [col.strip().lower() for col in first_row]

    # Check for header names
    header_keywords = {"cpu_request", "cpu", "timestamp", "job_id", "event_type"}
    is_header = any(keyword in col for col in clean_row for keyword in header_keywords)

    col_map: Dict[str, int] = {}
    if is_header:
        for idx, col in enumerate(clean_row):
            if "cpu" in col:
                col_map["cpu_request"] = idx
            elif "job" in col:
                col_map["job_id"] = idx
            elif "task" in col and "index" in col:
                col_map["task_index"] = idx
            elif "event" in col:
                col_map["event_type"] = idx
            elif "time" in col:
                col_map["timestamp"] = idx
            elif "mem" in col:
                col_map["memory_request"] = idx
            elif "priority" in col:
                col_map["priority"] = idx
    else:
        # Default Google 13-column positional schema
        col_map = {
            "timestamp"      : 0,
            "missing_info"   : 1,
            "job_id"         : 2,
            "task_index"     : 3,
            "machine_id"     : 4,
            "event_type"     : 5,
            "user_name"      : 6,
            "sched_class"    : 7,
            "priority"       : 8,
            "cpu_request"    : 9,
            "memory_request" : 10,
            "disk_request"   : 11,
            "constraint"     : 12,
        }

    return is_header, col_map


def _get_field(row: List[str], col_map: Dict[str, int], field_name: str, default_idx: int) -> Optional[str]:
    """Retrieve field from row by mapped column index or fallback index."""
    idx = col_map.get(field_name, default_idx)
    if idx < len(row):
        return row[idx]
    return None


def _parse_int(val: Optional[str]) -> Optional[int]:
    if val is None or not val.strip():
        return None
    try:
        return int(val.strip())
    except ValueError:
        return None


def _parse_float(val: Optional[str]) -> Optional[float]:
    if val is None or not val.strip():
        return None
    try:
        return float(val.strip())
    except ValueError:
        return None

"""
Tests for Workload Evaluated label in Metrics Summary section.

Verifies:
1. When comparison uses Synthetic Workload, label is 'Synthetic Workload (seed=42)'.
2. When comparison uses Google Cluster Trace (Staggered), label is 'Google Cluster Trace (clusterdata-2011-2, Staggered Trace)'.
3. When comparison uses Google Cluster Trace (Snapshot), label is 'Google Cluster Trace (clusterdata-2011-2, Snapshot Trace)'.
4. Label is derived from saved comparison results, persisting across sidebar option changes until a new comparison runs.
"""

import os
import unittest
from streamlit.testing.v1 import AppTest
from simulation.engine import SimulationEngine
from simulation.google_trace import load_bundled_google_trace

APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))


class TestWorkloadEvaluatedLabel(unittest.TestCase):

    def test_engine_label_generation_direct(self):
        engine = SimulationEngine()
        self.assertIsNone(engine.get_comparison_workload_label())

        # 1. Synthetic
        engine.run_comparison(num_vms=4, num_tasks=20, seed=42)
        self.assertEqual(engine.get_comparison_workload_label(), "Synthetic Workload (seed=42)")

        # 2. Google Trace Staggered
        staggered = load_bundled_google_trace(sample_type="staggered")
        engine.run_comparison(num_vms=4, num_tasks=50, custom_tasks=staggered.tasks)
        self.assertEqual(
            engine.get_comparison_workload_label(),
            "Google Cluster Trace (clusterdata-2011-2, Staggered Trace)"
        )

        # 3. Google Trace Snapshot
        snapshot = load_bundled_google_trace(sample_type="snapshot")
        engine.run_comparison(num_vms=4, num_tasks=50, custom_tasks=snapshot.tasks)
        self.assertEqual(
            engine.get_comparison_workload_label(),
            "Google Cluster Trace (clusterdata-2011-2, Snapshot Trace)"
        )

        # 4. Reset clears label
        engine.reset()
        self.assertIsNone(engine.get_comparison_workload_label())

    def test_apptest_synthetic_comparison_label(self):
        at = AppTest.from_file(APP_PATH)
        at.run()
        self.assertFalse(at.exception)

        for btn in at.button:
            if "Comparison" in btn.label:
                btn.click()
                break
        at.run()
        self.assertFalse(at.exception)

        captions = [c.value for c in at.caption if "Workload Evaluated" in c.value]
        self.assertEqual(len(captions), 1)
        self.assertIn("Synthetic Workload (seed=42)", captions[0])

    def test_apptest_google_trace_staggered_comparison_label(self):
        at = AppTest.from_file(APP_PATH)
        at.run()
        self.assertFalse(at.exception)

        for r in at.radio:
            if hasattr(r, "options") and "Google Cluster Trace" in r.options:
                r.set_value("Google Cluster Trace")
                break
        at.run()
        self.assertFalse(at.exception)

        for r in at.radio:
            if hasattr(r, "options") and any("Staggered" in opt for opt in r.options):
                r.set_value([opt for opt in r.options if "Staggered" in opt][0])
                break
        at.run()
        self.assertFalse(at.exception)

        for btn in at.button:
            if "Comparison" in btn.label:
                btn.click()
                break
        at.run()
        self.assertFalse(at.exception)

        captions = [c.value for c in at.caption if "Workload Evaluated" in c.value]
        self.assertEqual(len(captions), 1)
        self.assertIn("Google Cluster Trace (clusterdata-2011-2, Staggered Trace)", captions[0])

    def test_apptest_google_trace_snapshot_comparison_label(self):
        at = AppTest.from_file(APP_PATH)
        at.run()
        self.assertFalse(at.exception)

        for r in at.radio:
            if hasattr(r, "options") and "Google Cluster Trace" in r.options:
                r.set_value("Google Cluster Trace")
                break
        at.run()
        self.assertFalse(at.exception)

        for r in at.radio:
            if hasattr(r, "options") and any("Snapshot" in opt for opt in r.options):
                r.set_value([opt for opt in r.options if "Snapshot" in opt][0])
                break
        at.run()
        self.assertFalse(at.exception)

        for btn in at.button:
            if "Comparison" in btn.label:
                btn.click()
                break
        at.run()
        self.assertFalse(at.exception)

        captions = [c.value for c in at.caption if "Workload Evaluated" in c.value]
        self.assertEqual(len(captions), 1)
        self.assertIn("Google Cluster Trace (clusterdata-2011-2, Snapshot Trace)", captions[0])

    def test_apptest_label_derives_from_saved_results_not_sidebar_selection(self):
        # 1. Run comparison with Google Cluster Trace Staggered
        at = AppTest.from_file(APP_PATH)
        at.run()

        for r in at.radio:
            if hasattr(r, "options") and "Google Cluster Trace" in r.options:
                r.set_value("Google Cluster Trace")
                break
        at.run()

        for btn in at.button:
            if "Comparison" in btn.label:
                btn.click()
                break
        at.run()

        captions = [c.value for c in at.caption if "Workload Evaluated" in c.value]
        self.assertIn("Google Cluster Trace (clusterdata-2011-2, Staggered Trace)", captions[0])

        # 2. Change sidebar radio to Synthetic Workload without clicking Comparison
        for r in at.radio:
            if hasattr(r, "options") and "Synthetic Workload" in r.options:
                r.set_value("Synthetic Workload")
                break
        at.run()

        # Label must still reflect saved results!
        captions_after_toggle = [c.value for c in at.caption if "Workload Evaluated" in c.value]
        self.assertIn("Google Cluster Trace (clusterdata-2011-2, Staggered Trace)", captions_after_toggle[0])

        # 3. Click Comparison to run on Synthetic Workload
        for btn in at.button:
            if "Comparison" in btn.label:
                btn.click()
                break
        at.run()

        # Now label updates
        captions_after_rerun = [c.value for c in at.caption if "Workload Evaluated" in c.value]
        self.assertIn("Synthetic Workload (seed=42)", captions_after_rerun[0])


if __name__ == "__main__":
    unittest.main()

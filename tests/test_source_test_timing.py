from __future__ import annotations

import copy
import sys
import tempfile
import time
import unittest
import types
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from source_test_timing import hints, observation, timed_suite, collect, report_hints
from check_source_unit_tests import test_shards


class SourceTimingTests(unittest.TestCase):
    def fixture(self, root):
        (root / "tools").mkdir()
        (root / "tools/check_source_unit_tests.py").write_text("runner")
        (root / "tests").mkdir()
        (root / "tests/test_demo.py").write_text("test")

    def test_hints_require_current_content_and_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            value = observation(root, {"tests/test_demo.py": 0.2})
            self.assertEqual(hints(value, root), {"tests/test_demo.py": 0.2})
            for bad in (None, [], {}, True, -1, 0, float("inf"), "0.2", 10 ** 1000):
                mutant = copy.deepcopy(value)
                mutant["files"]["tests/test_demo.py"]["seconds"] = bad
                self.assertEqual(hints(mutant, root), {})
            mutant = copy.deepcopy(value)
            mutant["identity"]["runtime"] = "different"
            self.assertEqual(hints(mutant, root), {})
            (root / "tests/test_demo.py").write_text("changed")
            self.assertEqual(hints(value, root), {})

    def test_timing_preserves_execution_failures_skips_and_cleanup(self):
        events = []
        class Demo(unittest.TestCase):
            @classmethod
            def setUpClass(cls): events.append("setup")
            @classmethod
            def tearDownClass(cls): events.append("cleanup")
            def test_a(self): events.append("a")
            def test_b(self): self.fail("expected failure")
            @unittest.skip("expected skip")
            def test_c(self): pass
        def run(timed):
            suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(Demo)])
            durations = {}
            if timed:
                suite = timed_suite(suite, durations, ROOT)
            result = unittest.TestResult()
            suite.run(result)
            return (result.testsRun, len(result.failures), len(result.skipped)), durations
        baseline, _ = run(False)
        before = events[:]
        events.clear()
        observed, durations = run(True)
        self.assertEqual(observed, baseline)
        self.assertEqual(events, before)
        self.assertGreater(durations["tests/test_source_test_timing.py"], 0)

    def test_module_setup_cleanup_and_final_teardown_are_charged_to_their_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tests").mkdir()
            now, events, modules, cases = [0.0], [], {}, []
            def spend(label, seconds):
                events.append(label)
                now[0] += seconds
            for number in (1, 2):
                name = f"timing_fixture_{number}"
                module = types.ModuleType(name)
                module.__file__ = str(root / "tests" / f"test_fixture_{number}.py")
                Path(module.__file__).write_text("fixture")
                def setup(name=name):
                    spend(name + " setup", 2)
                    unittest.addModuleCleanup(lambda: spend(name + " cleanup", 5))
                module.setUpModule = setup
                module.tearDownModule = lambda name=name: spend(name + " teardown", 10)
                def run_test(self, number=number):
                    spend("test", 1)
                    if number == 2: self.fail("retained failure")
                case = type("Demo", (unittest.TestCase,), {"__module__": name, "runTest": run_test,
                    "setUpClass": classmethod(lambda cls: spend("class setup", 3)),
                    "tearDownClass": classmethod(lambda cls: spend("class teardown", 4))})
                modules[name], cases = module, [*cases, case]
            def run(timed):
                now[0], events[:] = 0.0, []
                suite = unittest.TestSuite([unittest.TestSuite([case()]) for case in cases])
                durations = {}
                if timed: suite = timed_suite(suite, durations, root, clock=lambda: now[0])
                result = unittest.TestResult()
                suite.run(result)
                return list(events), result, durations
            with patch.dict(sys.modules, modules):
                baseline, expected_result, _ = run(False)
                actual, result, durations = run(True)
            self.assertEqual(actual, baseline)
            self.assertEqual(result.testsRun, expected_result.testsRun)
            self.assertEqual(len(result.failures), 1)
            self.assertEqual(durations, {"tests/test_fixture_1.py": 25, "tests/test_fixture_2.py": 25})
            self.assertEqual(sum(durations.values()), now[0])

    def test_custom_load_tests_suite_is_not_rewritten(self):
        class Custom(unittest.TestSuite): pass
        module = types.ModuleType("custom_timing")
        class Demo(unittest.TestCase):
            def runTest(self): pass
        module.load_tests = lambda loader, tests, pattern: Custom([Demo()])
        suite = unittest.defaultTestLoader.loadTestsFromModule(module)
        durations = {}
        self.assertIs(timed_suite(suite, durations, ROOT), suite)
        result = unittest.TestResult()
        suite.run(result)
        self.assertEqual(result.testsRun, 1)
        self.assertEqual(durations, {})

    def test_malformed_report_and_observations_cannot_abort(self):
        for value in (None, [], True, {"timing": []}, {"timing": {"unit_test_durations": []}}):
            self.assertEqual(report_hints(value, ROOT), {})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            value = observation(root, {"tests/test_demo.py": 1})
            value["files"]["tests/test_demo.py"]["seconds"] = 10 ** 1000
            (root / "unit-timing-large.json").write_text(__import__("json").dumps(value))
            self.assertEqual(collect(root, root)["files"], {})

    def test_partial_hints_do_not_mix_seconds_with_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / name for name in ("one.py", "two.py", "three.py")]
            for path in paths:
                path.write_text("x" * 10000)
            shards = test_shards(paths, 2, duration_hints={paths[0].as_posix(): 0.5})
            self.assertCountEqual([p for shard in shards for p in shard], paths)

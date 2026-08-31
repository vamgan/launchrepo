import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import facts


class TestFact(unittest.TestCase):
    def test_a_fact_carries_a_value_and_a_source(self):
        f = facts.Fact(11, "scripts/platforms.py count")
        self.assertEqual(f.value, 11)
        self.assertEqual(f.source, "scripts/platforms.py count")

    def test_a_fact_without_a_source_is_rejected(self):
        with self.assertRaises(ValueError):
            facts.Fact(11, "")
        with self.assertRaises(ValueError):
            facts.Fact(11, None)


class TestProfile(unittest.TestCase):
    def test_records_and_returns_a_fact(self):
        p = facts.Profile()
        p.record("tests", 153, "python -m unittest discover")
        self.assertEqual(p.value("tests"), 153)

    def test_an_absent_fact_is_none_not_an_error(self):
        self.assertIsNone(facts.Profile().value("nothing"))

    def test_unavailable_is_recorded_with_a_reason_and_no_value(self):
        p = facts.Profile()
        p.unavailable("tests", "command exited 1")
        self.assertIsNone(p.value("tests"))
        self.assertEqual(p.reasons()["tests"], "command exited 1")

    def test_recording_never_stores_none_as_a_value(self):
        p = facts.Profile()
        p.record("tests", None, "somewhere")
        self.assertIsNone(p.value("tests"))
        self.assertIn("tests", p.reasons())

    def test_serialises_facts_and_reasons_separately(self):
        p = facts.Profile()
        p.record("name", "declutter", "git remote")
        p.unavailable("tests", "no test command declared")
        out = p.as_dict()
        self.assertEqual(out["facts"]["name"], {"value": "declutter", "source": "git remote"})
        self.assertEqual(out["unavailable"]["tests"], "no test command declared")


if __name__ == "__main__":
    unittest.main()

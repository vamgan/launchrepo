import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import facts


class TestFact(unittest.TestCase):
    def test_a_fact_carries_a_value_and_a_source(self):
        f = facts.Fact(11, "scripts/platforms.py count")
        self.assertEqual(f.value, 11)
        self.assertEqual(f.source, "scripts/platforms.py count")


if __name__ == "__main__":
    unittest.main()

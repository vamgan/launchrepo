import os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import distribute


class TestPostures(unittest.TestCase):
    def test_the_three_postures_exist(self):
        self.assertEqual(set(distribute.POSTURES), {"auto", "confirm", "prepare"})

    def test_every_registered_adapter_declares_a_valid_posture(self):
        for name, adapter in distribute.registry().items():
            self.assertIn(adapter.posture, distribute.POSTURES, name)

    def test_unknown_posture_raises_at_construction(self):
        with self.assertRaises(ValueError):
            distribute.Adapter("bogus", "yolo")

    def test_prepare_adapters_have_no_send_method(self):
        for name, adapter in distribute.registry().items():
            if adapter.posture == "prepare":
                self.assertFalse(hasattr(adapter, "send"), name)


if __name__ == "__main__":
    unittest.main()

import os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import distribute


PROFILE = {"facts": {
    "tests":              {"value": 153, "source": "unittest"},
    "browsers_supported": {"value": 11,  "source": "platforms.py"}},
    "unavailable": {}}


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


class TestVerificationGate(unittest.TestCase):
    def test_contradicted_copy_cannot_be_dispatched(self):
        with self.assertRaises(SystemExit) as cm:
            distribute.dispatch(
                "hackernews", "Ten browsers, one markdown file.", PROFILE
            )
        self.assertIn("browsers_supported", str(cm.exception))

    def test_unprovable_copy_is_allowed(self):
        # No adapter named "noop" exists, but the copy itself has
        # nothing wrong with it (an unrelated number is unprovable, not
        # a failure), so the gate must let it through -- any further
        # error has to come from adapter lookup, not verification.
        with self.assertRaises(SystemExit) as cm:
            distribute.dispatch("noop", "It takes 47 seconds to run.", PROFILE)
        self.assertNotIn("47", str(cm.exception))
        self.assertIn("noop", str(cm.exception))

    def test_contradicted_copy_to_unknown_adapter_fails_on_the_copy(self):
        with self.assertRaises(SystemExit) as cm:
            distribute.dispatch(
                "not-a-real-adapter", "Ten browsers, one markdown file.", PROFILE
            )
        self.assertIn("browsers_supported", str(cm.exception))
        self.assertNotIn("not-a-real-adapter", str(cm.exception))


if __name__ == "__main__":
    unittest.main()

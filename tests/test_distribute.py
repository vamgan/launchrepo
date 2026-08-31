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


CLEAN_COPY = "Launchrepo ships with 153 tests.\nRead the release notes for details."


class TestHackerNewsAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = distribute.registry()["hackernews"]

    def test_posture_is_prepare(self):
        self.assertEqual(self.adapter.posture, "prepare")

    def test_plan_builds_an_encoded_submission_url(self):
        plan = self.adapter.plan(
            "Launchrepo: verify before you ship\nBody text here.",
            url="https://example.com/launchrepo?ref=hn",
        )
        self.assertEqual(
            plan["submission_url"],
            "https://news.ycombinator.com/submitlink?"
            "u=https%3A%2F%2Fexample.com%2Flaunchrepo%3Fref%3Dhn"
            "&t=Launchrepo%3A+verify+before+you+ship",
        )

    def test_plan_states_a_human_must_submit(self):
        plan = self.adapter.plan(CLEAN_COPY, url="https://example.com")
        self.assertIn("human", plan["note"].lower())

    def test_title_over_80_characters_is_refused(self):
        title = "x" * 81
        with self.assertRaises(SystemExit):
            self.adapter.plan(f"{title}\nbody", url="https://example.com")

    def test_title_of_exactly_80_characters_is_allowed(self):
        title = "x" * 80
        plan = self.adapter.plan(f"{title}\nbody", url="https://example.com")
        self.assertIn("t=" + "x" * 80, plan["submission_url"])

    def test_send_mode_is_refused(self):
        with self.assertRaises(SystemExit) as cm:
            distribute.dispatch(
                "hackernews", CLEAN_COPY, PROFILE, mode="send", url="https://example.com"
            )
        message = str(cm.exception).lower()
        self.assertIn("prepare", message)
        self.assertIn("human", message)


class TestProductHuntAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = distribute.registry()["producthunt"]

    def test_posture_is_prepare(self):
        self.assertEqual(self.adapter.posture, "prepare")

    def test_plan_carries_submission_url_and_copy_to_paste(self):
        plan = self.adapter.plan(CLEAN_COPY)
        self.assertEqual(plan["submission_url"], "https://www.producthunt.com/posts/new")
        self.assertIn(CLEAN_COPY, plan["copy"])

    def test_plan_notes_the_pacific_launch_window(self):
        plan = self.adapter.plan(CLEAN_COPY)
        note = plan["note"].lower()
        self.assertIn("12:01", note)
        self.assertIn("11:59", note)
        self.assertIn("pacific", note)

    def test_send_mode_is_refused(self):
        with self.assertRaises(SystemExit) as cm:
            distribute.dispatch("producthunt", CLEAN_COPY, PROFILE, mode="send")
        message = str(cm.exception).lower()
        self.assertIn("prepare", message)
        self.assertIn("human", message)


if __name__ == "__main__":
    unittest.main()

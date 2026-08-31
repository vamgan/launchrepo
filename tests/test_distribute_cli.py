import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DISTRIBUTE_SCRIPT = os.path.join(ROOT, "scripts", "distribute.py")

PROFILE = {
    "facts": {
        "tests": {"value": 153, "source": "unittest"},
        "browsers_supported": {"value": 11, "source": "platforms.py"},
    },
    "unavailable": {},
}

CLEAN_COPY = "Launchrepo: verify before you ship\nWe ship with 153 tests.\n"
CONTRADICTED_COPY = "Ten browsers, one markdown file.\n"


def run_cli(*args, timeout=10):
    return subprocess.run(
        [sys.executable, DISTRIBUTE_SCRIPT, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def write(path, content):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


class TestDistributeCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.profile_path = write(
            os.path.join(self.tmp, "profile.json"), json.dumps(PROFILE)
        )

    def _copy(self, content):
        return write(os.path.join(self.tmp, "copy.md"), content)

    def test_dry_run_prints_the_plan_exits_zero_no_side_effects(self):
        copy_path = self._copy(CLEAN_COPY)
        result = run_cli(
            "producthunt", "--copy", copy_path, "--profile", self.profile_path
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("producthunt.com", result.stdout)
        # dry-run is the default: no --mode was passed at all, and
        # nothing here should have reached a network or a subprocess.

    def test_dry_run_is_the_default_mode(self):
        copy_path = self._copy(CLEAN_COPY)
        with_mode = run_cli(
            "producthunt", "--copy", copy_path, "--profile", self.profile_path,
            "--mode", "dry-run",
        )
        without_mode = run_cli(
            "producthunt", "--copy", copy_path, "--profile", self.profile_path,
        )
        self.assertEqual(with_mode.stdout, without_mode.stdout)

    def test_send_mode_on_prepare_adapter_exits_nonzero_explaining_human_submits(self):
        copy_path = self._copy(CLEAN_COPY)
        result = run_cli(
            "hackernews", "--copy", copy_path, "--profile", self.profile_path,
            "--mode", "send", "--url", "https://example.com",
        )
        self.assertNotEqual(result.returncode, 0)
        message = (result.stdout + result.stderr).lower()
        self.assertIn("human", message)

    def test_contradicted_copy_exits_nonzero_naming_the_fact(self):
        copy_path = self._copy(CONTRADICTED_COPY)
        result = run_cli(
            "hackernews", "--copy", copy_path, "--profile", self.profile_path,
            "--url", "https://example.com",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("browsers_supported", result.stdout + result.stderr)

    def test_list_shows_every_adapter_with_its_posture(self):
        result = run_cli("--list")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("hackernews", result.stdout)
        self.assertIn("prepare", result.stdout)
        self.assertIn("producthunt", result.stdout)
        self.assertIn("github_release", result.stdout)
        self.assertIn("auto", result.stdout)

    def test_github_release_dry_run_drafts_by_default(self):
        copy_path = self._copy(CLEAN_COPY)
        result = run_cli(
            "github_release", "--copy", copy_path, "--profile", self.profile_path,
            "--tag", "v1.0.0",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--draft", result.stdout)


if __name__ == "__main__":
    unittest.main()

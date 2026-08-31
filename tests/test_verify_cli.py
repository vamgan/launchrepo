import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFY_SCRIPT = os.path.join(ROOT, "scripts", "verify.py")

PROFILE = {
    "facts": {
        "tests": {"value": 153, "source": "unittest"},
        "browsers_supported": {"value": 11, "source": "platforms.py"},
    },
    "unavailable": {},
}


def write(path, content):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def run_cli(*args, timeout=10):
    return subprocess.run(
        [sys.executable, VERIFY_SCRIPT, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


class TestVerifyCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.profile_path = os.path.join(self.tmp, "profile.json")
        write(self.profile_path, json.dumps(PROFILE))

    def _copy(self, content):
        path = os.path.join(self.tmp, "copy.md")
        write(path, content)
        return path

    def test_clean_copy_exits_zero(self):
        copy_path = self._copy("We ship with 153 tests.\n")
        result = run_cli(copy_path, "--profile", self.profile_path)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_contradicted_copy_exits_non_zero(self):
        copy_path = self._copy("Ten browsers, one markdown file.\n")
        result = run_cli(copy_path, "--profile", self.profile_path)
        self.assertNotEqual(result.returncode, 0)

    def test_unprovable_copy_still_exits_zero(self):
        copy_path = self._copy("It takes 47 seconds to run.\n")
        result = run_cli(copy_path, "--profile", self.profile_path)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_human_readable_report_names_the_conflicting_fact_and_source(self):
        copy_path = self._copy("Ten browsers, one markdown file.\n")
        result = run_cli(copy_path, "--profile", self.profile_path)
        self.assertIn("browsers_supported", result.stdout)
        self.assertIn("platforms.py", result.stdout)

    def test_json_flag_produces_machine_readable_output(self):
        copy_path = self._copy("Ten browsers, one markdown file.\n")
        result = run_cli(copy_path, "--profile", self.profile_path, "--json")
        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])

    def test_profile_flag_is_required(self):
        copy_path = self._copy("We ship with 153 tests.\n")
        result = run_cli(copy_path)
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()

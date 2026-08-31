import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fixtures import make_repo

PROFILE_SCRIPT = os.path.join(ROOT, "scripts", "profile.py")


def run_cli(*args, timeout=10):
    return subprocess.run(
        [sys.executable, PROFILE_SCRIPT, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


class TestProfileCLI(unittest.TestCase):
    def test_prints_json_with_facts_and_unavailable(self):
        repo = make_repo()
        result = run_cli(repo)
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertIn("facts", payload)
        self.assertIn("unavailable", payload)
        self.assertEqual(payload["facts"]["name"]["value"], os.path.basename(repo))

    def test_out_flag_writes_to_a_file(self):
        repo = make_repo()
        with tempfile.TemporaryDirectory() as tmp:
            out_path = os.path.join(tmp, "profile.json")
            result = run_cli(repo, "--out", out_path)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout.strip(), "")
            with open(out_path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            self.assertIn("facts", payload)
            self.assertIn("unavailable", payload)

    def test_non_git_directory_exits_non_zero(self):
        non_repo = os.path.dirname(make_repo())
        result = run_cli(non_repo)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not a git repository", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()

import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENDER_SCRIPT = os.path.join(ROOT, "scripts", "render.py")

PROFILE = {
    "facts": {"name": {"value": "declutter", "source": "git remote"}},
    "unavailable": {"tagline": "not declared"},
}

BOGUS_CHROME = "/nonexistent/path/to/chrome"


def run_cli(*args, timeout=15):
    return subprocess.run(
        [sys.executable, RENDER_SCRIPT, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


class TestRenderCLI(unittest.TestCase):
    def _write(self, path, content):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return path

    def test_missing_chrome_exits_nonzero_mentioning_chrome(self):
        with tempfile.TemporaryDirectory() as tmp:
            template = self._write(
                os.path.join(tmp, "t.html"), "<html><body>{{name}}</body></html>"
            )
            profile_path = self._write(
                os.path.join(tmp, "p.json"), json.dumps(PROFILE)
            )
            out_path = os.path.join(tmp, "out.png")
            result = run_cli(
                template,
                "--profile", profile_path,
                "--out", out_path,
                "--width", "100",
                "--height", "50",
                "--chrome", BOGUS_CHROME,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("chrome", (result.stdout + result.stderr).lower())

    def test_set_supplies_missing_value_so_failure_is_chrome_not_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp:
            template = self._write(
                os.path.join(tmp, "t.html"), "<html><body>{{tagline}}</body></html>"
            )
            profile_path = self._write(
                os.path.join(tmp, "p.json"), json.dumps(PROFILE)
            )
            out_path = os.path.join(tmp, "out.png")
            result = run_cli(
                template,
                "--profile", profile_path,
                "--out", out_path,
                "--width", "100",
                "--height", "50",
                "--chrome", BOGUS_CHROME,
                "--set", "tagline=a fine tagline",
            )
            self.assertNotEqual(result.returncode, 0)
            combined = (result.stdout + result.stderr).lower()
            self.assertIn("chrome", combined)
            self.assertNotIn("unavailable", combined)

    def test_unprovable_placeholder_exits_nonzero_and_names_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            template = self._write(
                os.path.join(tmp, "t.html"), "<html><body>{{tagline}}</body></html>"
            )
            profile_path = self._write(
                os.path.join(tmp, "p.json"), json.dumps(PROFILE)
            )
            out_path = os.path.join(tmp, "out.png")
            result = run_cli(
                template,
                "--profile", profile_path,
                "--out", out_path,
                "--width", "100",
                "--height", "50",
            )
            self.assertNotEqual(result.returncode, 0)
            combined = result.stdout + result.stderr
            self.assertIn("tagline", combined)

    def test_malformed_set_exits_with_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            template = self._write(
                os.path.join(tmp, "t.html"), "<html><body>{{name}}</body></html>"
            )
            profile_path = self._write(
                os.path.join(tmp, "p.json"), json.dumps(PROFILE)
            )
            out_path = os.path.join(tmp, "out.png")
            result = run_cli(
                template,
                "--profile", profile_path,
                "--out", out_path,
                "--width", "100",
                "--height", "50",
                "--set", "no-equals-sign",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue((result.stdout + result.stderr).strip())


if __name__ == "__main__":
    unittest.main()

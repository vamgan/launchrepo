import os, sys, unittest
import re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import profile as profile_mod
from fixtures import make_repo


class TestName(unittest.TestCase):
    def test_name_comes_from_remote_slug(self):
        repo = make_repo(remote="https://github.com/vamgan/declutter.git")
        p = profile_mod.extract(repo)
        self.assertEqual(p.value("name"), "declutter")
        self.assertIn("remote", p.source("name"))

    def test_name_falls_back_to_directory_basename_without_remote(self):
        repo = make_repo()
        p = profile_mod.extract(repo)
        self.assertEqual(p.value("name"), os.path.basename(repo))

    def test_extract_raises_systemexit_for_non_git_directory(self):
        non_repo = os.path.dirname(make_repo())  # parent of a repo is not itself a repo
        with self.assertRaises(SystemExit):
            profile_mod.extract(non_repo)


MIT_TEXT = """MIT License

Copyright (c) 2024 Test

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to
deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
sell copies of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
"""

APACHE_TEXT = """
                                 Apache License
                           Version 2.0, January 2004
                        https://www.apache.org/licenses/

TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION
"""


class TestLicence(unittest.TestCase):
    def test_mit_licence_is_detected(self):
        repo = make_repo(files={"README.md": "# t\n", "LICENSE": MIT_TEXT})
        p = profile_mod.extract(repo)
        self.assertEqual(p.value("licence"), "MIT")

    def test_apache_licence_is_detected(self):
        repo = make_repo(files={"README.md": "# t\n", "LICENSE": APACHE_TEXT})
        p = profile_mod.extract(repo)
        self.assertEqual(p.value("licence"), "Apache-2.0")

    def test_unrecognised_licence_body_is_unavailable(self):
        repo = make_repo(files={"README.md": "# t\n", "LICENSE": "do whatever you want\n"})
        p = profile_mod.extract(repo)
        self.assertIsNone(p.value("licence"))
        self.assertIn("licence", p.reasons())

    def test_missing_licence_file_is_unavailable(self):
        repo = make_repo()
        p = profile_mod.extract(repo)
        self.assertIsNone(p.value("licence"))
        self.assertIn("licence", p.reasons())


class TestLanguage(unittest.TestCase):
    def test_most_common_source_extension_wins(self):
        repo = make_repo(files={
            "README.md": "# t\n",
            "a.py": "print(1)\n",
            "b.py": "print(2)\n",
            "c.js": "console.log(1)\n",
        })
        p = profile_mod.extract(repo)
        self.assertEqual(p.value("language"), "Python")

    def test_docs_and_config_files_are_ignored(self):
        repo = make_repo(files={
            "README.md": "# t\n",
            "package.json": "{}\n",
            "a.go": "package main\n",
        })
        p = profile_mod.extract(repo)
        self.assertEqual(p.value("language"), "Go")

    def test_no_source_files_means_no_language(self):
        repo = make_repo(files={"README.md": "# t\n", "notes.txt": "hi\n"})
        p = profile_mod.extract(repo)
        self.assertIsNone(p.value("language"))
        self.assertIn("language", p.reasons())


class TestHistory(unittest.TestCase):
    def test_commit_count(self):
        repo = make_repo(commits=4)
        p = profile_mod.extract(repo)
        self.assertEqual(p.value("commit_count"), 4)
        self.assertIn("git", p.source("commit_count"))

    def test_first_commit_date_is_iso_format(self):
        repo = make_repo(commits=2)
        p = profile_mod.extract(repo)
        self.assertRegex(p.value("first_commit_date"), r"^\d{4}-\d{2}-\d{2}$")
        self.assertIn("git", p.source("first_commit_date"))

    def test_contributor_count_is_unique_author_emails(self):
        repo = make_repo(commits=3)
        p = profile_mod.extract(repo)
        self.assertEqual(p.value("contributor_count"), 1)
        self.assertIn("git", p.source("contributor_count"))


MATRIX_WORKFLOW = """
name: CI
on: [push]
jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - run: echo hi
"""

PLAIN_WORKFLOW = """
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: echo hi
"""

WEIRD_WORKFLOW = """
name: CI
on: [push]
jobs:
  test:
    strategy:
      matrix:
        os: !!weird
    runs-on: ${{ matrix.os }}
    steps:
      - run: echo hi
"""


class TestCIPlatforms(unittest.TestCase):
    def test_reads_os_matrix_list(self):
        repo = make_repo(files={
            "README.md": "# t\n",
            ".github/workflows/ci.yml": MATRIX_WORKFLOW,
        })
        p = profile_mod.extract(repo)
        self.assertEqual(
            p.value("ci_platforms"),
            ["ubuntu-latest", "macos-latest", "windows-latest"],
        )
        self.assertIn("ci.yml", p.source("ci_platforms"))

    def test_reads_plain_runs_on_as_single_item_list(self):
        repo = make_repo(files={
            "README.md": "# t\n",
            ".github/workflows/ci.yml": PLAIN_WORKFLOW,
        })
        p = profile_mod.extract(repo)
        self.assertEqual(p.value("ci_platforms"), ["ubuntu-latest"])

    def test_no_workflow_files_is_unavailable(self):
        repo = make_repo()
        p = profile_mod.extract(repo)
        self.assertIsNone(p.value("ci_platforms"))
        self.assertIn("ci_platforms", p.reasons())

    def test_matrix_in_one_file_wins_over_plain_runs_on_in_another(self):
        # "pages.yml" sorts before "test.yml" alphabetically; the real
        # three-platform matrix lives in the file that sorts second, and
        # must not be eclipsed by the single-job workflow that sorts first.
        repo = make_repo(files={
            "README.md": "# t\n",
            ".github/workflows/pages.yml": PLAIN_WORKFLOW,
            ".github/workflows/test.yml": MATRIX_WORKFLOW,
        })
        p = profile_mod.extract(repo)
        self.assertEqual(
            p.value("ci_platforms"),
            ["ubuntu-latest", "macos-latest", "windows-latest"],
        )
        self.assertIn("test.yml", p.source("ci_platforms"))

    def test_unparsable_matrix_line_is_unavailable_not_partial(self):
        repo = make_repo(files={
            "README.md": "# t\n",
            ".github/workflows/ci.yml": WEIRD_WORKFLOW,
        })
        p = profile_mod.extract(repo)
        self.assertIsNone(p.value("ci_platforms"))
        self.assertIn("ci_platforms", p.reasons())


class TestDeclaredFacts(unittest.TestCase):
    def test_declared_command_output_is_recorded(self):
        repo = make_repo(files={
            "README.md": "# t\n",
            "launchrepo.toml": (
                '[facts.greeting]\n'
                'command = "echo hello"\n'
                'description = "a greeting"\n'
            ),
        })
        p = profile_mod.extract(repo)
        self.assertEqual(p.value("greeting"), "hello")
        self.assertIn("echo hello", p.source("greeting"))

    def test_numeric_output_becomes_int(self):
        repo = make_repo(files={
            "README.md": "# t\n",
            "launchrepo.toml": (
                '[facts.browsers_supported]\n'
                'command = "echo 11"\n'
                'description = "browsers this project supports"\n'
            ),
        })
        p = profile_mod.extract(repo)
        self.assertEqual(p.value("browsers_supported"), 11)
        self.assertIsInstance(p.value("browsers_supported"), int)

    def test_nonzero_exit_is_unavailable_with_exit_code_in_reason(self):
        repo = make_repo(files={
            "README.md": "# t\n",
            "launchrepo.toml": (
                '[facts.broken]\n'
                'command = "exit 3"\n'
                'description = "always fails"\n'
            ),
        })
        p = profile_mod.extract(repo)
        self.assertIsNone(p.value("broken"))
        self.assertIn("3", p.reasons()["broken"])

    def test_missing_launchrepo_toml_is_not_an_error(self):
        repo = make_repo()
        p = profile_mod.extract(repo)  # should not raise
        self.assertIsNone(p.value("greeting"))


if __name__ == "__main__":
    unittest.main()

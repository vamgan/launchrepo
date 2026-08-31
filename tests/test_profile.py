import os, sys, unittest
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


if __name__ == "__main__":
    unittest.main()

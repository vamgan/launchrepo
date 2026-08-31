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


if __name__ == "__main__":
    unittest.main()

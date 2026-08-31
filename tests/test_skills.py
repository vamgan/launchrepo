"""Structural tests for the copy skills.

Whether a skill produces good copy is not checkable, and a green tick claiming
otherwise would be false comfort. What is checkable is that each skill points at
the profile, runs verification, and does not hardcode a fact of its own, which is
the failure this whole tool exists to prevent.
"""
import glob, json, os, re, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = sorted(glob.glob(os.path.join(ROOT, "skills", "*", "SKILL.md")))


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def frontmatter(path):
    text = read(path)
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        return None, text
    meta, key = {}, None
    for line in match.group(1).splitlines():
        if re.match(r"^\s+", line) and key:
            meta[key] += " " + line.strip()
        elif ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            meta[key] = value.strip()
    return meta, text[match.end():]


class TestSkillsExist(unittest.TestCase):
    def test_all_three_skills_are_present(self):
        names = {os.path.basename(os.path.dirname(p)) for p in SKILLS}
        self.assertEqual(names, {"writing-a-readme", "writing-a-landing-page",
                                 "writing-launch-posts"})


class TestFrontmatter(unittest.TestCase):
    def test_frontmatter_parses(self):
        for path in SKILLS:
            with self.subTest(skill=path):
                meta, _ = frontmatter(path)
                self.assertIsNotNone(meta, "missing or malformed frontmatter")

    def test_name_matches_the_directory(self):
        for path in SKILLS:
            meta, _ = frontmatter(path)
            with self.subTest(skill=path):
                self.assertEqual(meta.get("name"),
                                 os.path.basename(os.path.dirname(path)))

    def test_description_says_when_to_use_it(self):
        for path in SKILLS:
            meta, _ = frontmatter(path)
            with self.subTest(skill=meta.get("name")):
                self.assertIn("use when", meta.get("description", "").lower())

    def test_description_lists_trigger_phrases(self):
        # The description is how the model decides to reach for a skill. Without
        # phrases a person would actually type, it never fires.
        for path in SKILLS:
            meta, _ = frontmatter(path)
            with self.subTest(skill=meta.get("name")):
                self.assertIn("triggers on", meta.get("description", "").lower())

    def test_names_are_unique(self):
        names = [frontmatter(p)[0]["name"] for p in SKILLS]
        self.assertEqual(len(names), len(set(names)))


class TestSkillsUseTheProfile(unittest.TestCase):
    """The point of the tool is that copy is checked. A skill that never reads a
    profile or runs verification produces exactly the drift it exists to stop."""

    def test_every_skill_reads_the_profile(self):
        for path in SKILLS:
            meta, body = frontmatter(path)
            with self.subTest(skill=meta["name"]):
                self.assertIn("profile.py", body)

    def test_every_skill_runs_verification(self):
        for path in SKILLS:
            meta, body = frontmatter(path)
            with self.subTest(skill=meta["name"]):
                self.assertIn("verify.py", body)

    def test_every_skill_forbids_hand_written_numbers(self):
        for path in SKILLS:
            meta, body = frontmatter(path)
            with self.subTest(skill=meta["name"]):
                self.assertRegex(body.lower(), r"(number|count).{0,80}profile",
                                 "no instruction tying numbers to the profile")

    def test_every_skill_has_a_never_section(self):
        for path in SKILLS:
            meta, body = frontmatter(path)
            with self.subTest(skill=meta["name"]):
                self.assertIn("## Never", body)


class TestNoHardcodedFacts(unittest.TestCase):
    """A skill that states a fact of its own is a second place for it to go stale."""

    def test_no_skill_claims_a_supported_platform_count(self):
        pattern = re.compile(r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|"
                             r"ten|eleven|twelve)\s+(?:supported\s+)?"
                             r"(?:browsers|platforms|apps|skills)\b", re.I)
        for path in SKILLS:
            meta, body = frontmatter(path)
            # strip fenced examples: illustrative copy is allowed to contain numbers
            prose = re.sub(r"```.*?```", "", body, flags=re.S)
            prose = re.sub(r'"[^"]{0,120}"', "", prose)
            with self.subTest(skill=meta["name"]):
                self.assertIsNone(pattern.search(prose),
                                  f"hardcoded count: {pattern.search(prose)}")


class TestPluginManifest(unittest.TestCase):
    def setUp(self):
        self.manifest = json.load(
            open(os.path.join(ROOT, ".claude-plugin", "plugin.json"), encoding="utf-8"))

    def test_has_the_required_fields(self):
        for field in ("name", "description", "version", "license"):
            self.assertIn(field, self.manifest)

    def test_name_matches_the_repository(self):
        self.assertEqual(self.manifest["name"], "launchrepo")


if __name__ == "__main__":
    unittest.main()

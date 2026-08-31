import os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import verify


class TestFindClaims(unittest.TestCase):
    def test_finds_digit_numbers(self):
        claims = verify.find_claims("There are 153 tests.")
        self.assertEqual([c.value for c in claims], [153])

    def test_finds_number_words(self):
        claims = verify.find_claims("Eleven browsers are supported.")
        self.assertEqual([c.value for c in claims], [11])

    def test_number_words_are_case_insensitive(self):
        claims = verify.find_claims("eleven browsers, ELEVEN times.")
        self.assertEqual([c.value for c in claims], [11, 11])

    def test_strips_thousands_separators(self):
        claims = verify.find_claims("3,412 bookmarks exported.")
        self.assertEqual([c.value for c in claims], [3412])

    def test_finds_several_in_one_line(self):
        claims = verify.find_claims("Fixes 3 bugs and adds two features.")
        self.assertEqual([c.value for c in claims], [3, 2])

    def test_ignores_version_strings(self):
        claims = verify.find_claims("Python 3.10 and 3.13 are supported.")
        self.assertEqual(claims, [])

    def test_ignores_bare_years(self):
        claims = verify.find_claims("Actively maintained since 2019.")
        self.assertEqual(claims, [])

    def test_records_the_sentence_as_context(self):
        claims = verify.find_claims("Intro. There are 153 tests today. Outro.")
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].context, "There are 153 tests today.")

    def test_claim_exposes_kind(self):
        claims = verify.find_claims("There are 153 tests.")
        self.assertEqual(claims[0].kind, "number")


PROFILE = {"facts": {
    "tests":              {"value": 153, "source": "unittest"},
    "browsers_supported": {"value": 11,  "source": "platforms.py"},
    "ci_platforms":       {"value": ["ubuntu-latest", "macos-latest", "windows-latest"],
                           "source": "test.yml"}}, "unavailable": {}}


class TestCheck(unittest.TestCase):
    def test_matching_number_is_proven(self):
        report = verify.check("We ship with 153 tests.", PROFILE)
        self.assertTrue(report.ok)
        self.assertEqual(len(report.proven), 1)
        self.assertEqual(report.proven[0].value, 153)

    def test_matching_number_word_is_proven(self):
        report = verify.check("Supports eleven browsers.", PROFILE)
        self.assertTrue(report.ok)
        self.assertEqual(len(report.proven), 1)
        self.assertEqual(report.proven[0].value, 11)

    def test_ten_browsers_one_markdown_file_is_contradicted(self):
        # The exact line that shipped to a live site while the coverage
        # table two sections below said eleven.
        report = verify.check("Ten browsers, one markdown file.", PROFILE)
        self.assertFalse(report.ok)
        self.assertEqual(len(report.contradicted), 1)
        finding = report.contradicted[0]
        self.assertEqual(finding.value, 10)
        self.assertEqual(finding.conflicts_with, "browsers_supported")
        self.assertEqual(finding.fact_value, 11)
        self.assertEqual(finding.source, "platforms.py")

    def test_unrelated_number_is_unprovable_and_does_not_fail(self):
        report = verify.check("It takes 47 seconds to run.", PROFILE)
        self.assertTrue(report.ok)
        self.assertEqual(len(report.unprovable), 1)
        self.assertEqual(report.unprovable[0].value, 47)

    def test_number_equal_to_list_length_is_proven(self):
        report = verify.check("Runs on three platforms.", PROFILE)
        self.assertTrue(report.ok)
        self.assertEqual(len(report.proven), 1)
        self.assertEqual(report.proven[0].value, 3)

    def test_a_number_sharing_a_sentence_with_an_unrelated_fact_is_left_alone(self):
        # "one markdown file" must not be judged against browsers_supported
        # just because "browsers" appears earlier in the same sentence.
        report = verify.check("Ten browsers, one markdown file.", PROFILE)
        one_findings = [f for f in report.contradicted + report.unprovable if f.value == 1]
        self.assertEqual(len(one_findings), 1)
        self.assertIn(one_findings[0], report.unprovable)


if __name__ == "__main__":
    unittest.main()

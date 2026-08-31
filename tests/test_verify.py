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


if __name__ == "__main__":
    unittest.main()

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

    def test_a_coincidental_value_match_without_subject_overlap_is_unprovable(self):
        # "one markdown file" happening to equal an unrelated fact's value
        # (here, a contributor count of 1) is not evidence of anything. A
        # false "proven" is worse than an unprovable: unprovable prompts a
        # human to look, proven tells them it's already checked.
        profile = {"facts": {
            "contributor_count": {"value": 1, "source": "git log --format=%ae"},
        }, "unavailable": {}}
        report = verify.check("Ten browsers, one markdown file.", profile)
        self.assertTrue(report.ok)
        one_findings = [f for f in report.proven + report.unprovable if f.value == 1]
        self.assertEqual(len(one_findings), 1)
        self.assertIn(one_findings[0], report.unprovable)


class TestEntityLists(unittest.TestCase):
    def test_a_complete_list_is_fine(self):
        report = verify.check(
            "Tested on ubuntu-latest, macos-latest, and windows-latest.", PROFILE
        )
        self.assertTrue(report.ok)
        self.assertTrue(any(
            set(f.value) == {"ubuntu-latest", "macos-latest", "windows-latest"}
            for f in report.proven
        ))

    def test_an_incomplete_list_is_contradicted(self):
        report = verify.check("Tested on ubuntu-latest and macos-latest.", PROFILE)
        self.assertFalse(report.ok)
        self.assertEqual(len(report.contradicted), 1)
        self.assertEqual(report.contradicted[0].conflicts_with, "ci_platforms")

    def test_the_report_names_what_was_left_out(self):
        report = verify.check("Tested on ubuntu-latest and macos-latest.", PROFILE)
        finding = report.contradicted[0]
        missing = set(finding.fact_value) - set(finding.value)
        self.assertEqual(missing, {"windows-latest"})

    def test_unrelated_names_are_not_a_claim_about_any_fact(self):
        report = verify.check("Thanks to Alice, Bob and Carol.", PROFILE)
        self.assertEqual(report.proven, [])
        self.assertEqual(report.contradicted, [])
        self.assertEqual(report.unprovable, [])

    def test_a_single_mention_is_a_reference_and_is_left_alone(self):
        report = verify.check("Built and tested on ubuntu-latest.", PROFILE)
        self.assertEqual(report.contradicted, [])
        self.assertEqual(report.proven, [])


class TestPluralSubjectMatching(unittest.TestCase):
    """Subject-overlap detection must treat a trailing 's' as optional, so
    a claim's plural wording ("commits") still overlaps a fact keyed with
    the singular ("commit_count"), and vice versa.
    """

    def test_plural_claim_word_matches_singular_fact_key_word(self):
        profile = {"facts": {
            "commit_count": {"value": 27, "source": "git log"},
        }, "unavailable": {}}
        report = verify.check("This project has 27 commits.", profile)
        self.assertTrue(report.ok)
        self.assertEqual(len(report.proven), 1)
        self.assertEqual(report.proven[0].value, 27)

    def test_plural_claim_word_still_matches_already_plural_fact_key_word(self):
        # Guards against a fix that only handles singular-fact/plural-claim
        # and breaks the case both sides already share.
        report = verify.check("Runs on three platforms.", PROFILE)
        self.assertTrue(report.ok)
        self.assertEqual(len(report.proven), 1)
        self.assertEqual(report.proven[0].value, 3)

    def test_word_sharing_a_prefix_does_not_falsely_match(self):
        # "commitment" starts with the same letters as "commit" but is a
        # different word entirely -- trailing-s normalisation must not
        # degrade into a prefix match.
        profile = {"facts": {
            "commit_count": {"value": 5, "source": "git log"},
        }, "unavailable": {}}
        report = verify.check("Real commitment gets you five results.", profile)
        self.assertTrue(report.ok)
        self.assertEqual(len(report.proven), 0)
        self.assertEqual(len(report.contradicted), 0)
        self.assertEqual(len(report.unprovable), 1)
        self.assertEqual(report.unprovable[0].value, 5)


class TestAgreementBeatsDisagreement(unittest.TestCase):
    """When a clause's words overlap more than one fact's subject, an
    agreeing fact must win over a disagreeing one -- a claim is only
    contradicted when *no* overlapping fact agrees with it.
    """

    PROFILE = {"facts": {
        "commit_count": {"value": 27, "source": "git log"},
        "ci_platforms": {"value": ["ubuntu-latest", "macos-latest", "windows-latest"],
                          "source": "test.yml"},
    }, "unavailable": {}}

    def test_true_claims_about_two_different_facts_in_one_sentence_are_both_proven(self):
        # The exact sentence from the bug report: every claim in it is
        # true, so nothing may be reported as contradicted.
        report = verify.check(
            "launchrepo runs on three platforms and has 27 commits.", self.PROFILE
        )
        self.assertTrue(report.ok)
        self.assertEqual(len(report.proven), 2)
        self.assertEqual(len(report.contradicted), 0)
        self.assertEqual({f.value for f in report.proven}, {3, 27})

    def test_a_genuinely_stale_claim_still_contradicts_alongside_a_true_one(self):
        report = verify.check(
            "launchrepo runs on two platforms and has 27 commits.", self.PROFILE
        )
        self.assertFalse(report.ok)
        self.assertEqual(len(report.proven), 1)
        self.assertEqual(report.proven[0].value, 27)
        self.assertEqual(len(report.contradicted), 1)
        self.assertEqual(report.contradicted[0].value, 2)
        self.assertEqual(report.contradicted[0].conflicts_with, "ci_platforms")


class TestSuperlatives(unittest.TestCase):
    def test_never_is_surfaced_as_unprovable(self):
        report = verify.check("It never crashes.", PROFILE)
        self.assertTrue(report.ok)
        self.assertTrue(any(f.value == "superlative" for f in report.unprovable))

    def test_always_is_surfaced_as_unprovable(self):
        report = verify.check("It always works.", PROFILE)
        self.assertTrue(report.ok)
        self.assertTrue(any(f.value == "superlative" for f in report.unprovable))

    def test_the_only_is_surfaced_as_unprovable(self):
        report = verify.check("The only tool you need.", PROFILE)
        self.assertTrue(report.ok)
        self.assertTrue(any(f.value == "superlative" for f in report.unprovable))

    def test_a_superlative_does_not_fail_the_build(self):
        report = verify.check("It is always the only choice and never breaks.", PROFILE)
        self.assertTrue(report.ok)

    def test_ordinary_prose_produces_no_superlative_finding(self):
        report = verify.check("It runs quickly and reliably.", PROFILE)
        self.assertFalse(any(f.value == "superlative" for f in report.unprovable))


if __name__ == "__main__":
    unittest.main()

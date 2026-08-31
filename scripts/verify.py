"""verify.py: check generated marketing copy against a repository's fact profile.

`profile.py` extracts what can be proven about a repository; this module
checks what was *said* about it. It reads a Profile's JSON (as a plain
dict) and a file of generated copy, and classifies every claim in that
copy into exactly one of three outcomes: proven (matches a fact),
contradicted (disagrees with a fact -- always wrong, fails the build),
or unprovable (no fact speaks to it -- not an error). This module does
not import profile.py; the two communicate only through that JSON shape.
"""

import re

# Number words this module recognises as quantity claims, one through
# twenty. Anything larger is written with digits in practice, and this
# keeps the word list small and unambiguous.
NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
}

# A version string like "3.10" or "3.13.1" is not a claim about a
# quantity -- it is masked out (replaced with spaces of the same length,
# so later match positions still line up with the original sentence)
# before any number is looked for.
_VERSION_RE = re.compile(r"\d+\.\d+(?:\.\d+)*")

# A date preposition immediately before a bare four-digit number turns
# that number into a year, not a quantity claim -- "since 2019" is not a
# claim that there are 2019 of anything.
_TEMPORAL_WORDS = {
    "since", "in", "from", "until", "by", "founded", "established",
    "circa", "est", "around", "dated",
}

# One token: either a thousands-grouped or plain integer, or a spelled
# number word. The grouped-number alternative comes first so "3,412" is
# consumed whole rather than as "3" followed by a stray ",412".
_CLAIM_TOKEN_RE = re.compile(
    r"\d{1,3}(?:,\d{3})+|\d+|\b(?:" + "|".join(NUMBER_WORDS) + r")\b",
    re.IGNORECASE,
)

# Sentences are split on a sentence-ending punctuation mark followed by
# whitespace. A decimal point inside a number (e.g. "3.10") is followed
# by a digit, not whitespace, so it is never mistaken for a boundary.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


class Claim:
    """One quantity mentioned in the copy: what it says, and where.

    `span` is the claim's (start, end) character offset within
    `context`, kept so later processing (contradiction detection) can
    tell which part of a multi-clause sentence a number belongs to,
    without needing every caller to re-parse the sentence.
    """

    __slots__ = ("kind", "value", "context", "span")

    def __init__(self, kind, value, context, span=None):
        self.kind = kind
        self.value = value
        self.context = context
        self.span = span

    def __repr__(self):
        return f"Claim(kind={self.kind!r}, value={self.value!r}, context={self.context!r})"


def _split_sentences(text):
    sentences = []
    for raw in _SENTENCE_SPLIT_RE.split(text.strip()):
        sentence = raw.strip()
        if sentence:
            sentences.append(sentence)
    return sentences


def _mask_versions(sentence):
    return _VERSION_RE.sub(lambda m: " " * len(m.group(0)), sentence)


def _is_bare_year(sentence, start, token):
    if len(token) != 4 or not token.isdigit():
        return False
    year = int(token)
    if not (1000 <= year <= 2099):
        return False
    preceding = re.search(r"([A-Za-z]+)\.?\s*$", sentence[:start])
    return preceding is not None and preceding.group(1).lower() in _TEMPORAL_WORDS


def _find_numeric_claims(sentence):
    claims = []
    scan_text = _mask_versions(sentence)
    for match in _CLAIM_TOKEN_RE.finditer(scan_text):
        token = match.group(0)
        if token[0].isdigit():
            if _is_bare_year(sentence, match.start(), token):
                continue
            value = int(token.replace(",", ""))
        else:
            value = NUMBER_WORDS[token.lower()]
        claims.append(Claim("number", value, sentence, span=match.span()))
    return claims


def find_claims(text):
    """Return every quantity claim in `text`, in order of appearance."""
    claims = []
    for sentence in _split_sentences(text):
        claims.extend(_find_numeric_claims(sentence))
    return claims


class Finding:
    """One classified claim: what was said, where, and (if wrong) why."""

    __slots__ = ("value", "context", "conflicts_with", "fact_value", "source")

    def __init__(self, value, context, conflicts_with=None, fact_value=None, source=None):
        self.value = value
        self.context = context
        self.conflicts_with = conflicts_with
        self.fact_value = fact_value
        self.source = source

    def as_dict(self):
        result = {"value": self.value, "context": self.context}
        if self.conflicts_with is not None:
            result["conflicts_with"] = self.conflicts_with
            result["fact_value"] = self.fact_value
            result["source"] = self.source
        return result


class Report:
    """The outcome of checking copy against a profile.

    `ok` is false only when something is contradicted -- an unprovable
    claim is not a failure, it is simply a claim the profile cannot
    speak to.
    """

    def __init__(self):
        self.proven = []
        self.contradicted = []
        self.unprovable = []

    @property
    def ok(self):
        return not self.contradicted

    def as_dict(self):
        return {
            "ok": self.ok,
            "proven": [f.as_dict() for f in self.proven],
            "contradicted": [f.as_dict() for f in self.contradicted],
            "unprovable": [f.as_dict() for f in self.unprovable],
        }


def _clause_at(sentence, span):
    """The comma/semicolon-delimited clause of `sentence` containing `span`.

    "Ten browsers, one markdown file." is two independent claims joined
    by a comma. Scoping subject-overlap detection to the claim's own
    clause -- rather than the whole sentence -- keeps "one" from being
    judged against the browsers fact just because "browsers" appears
    earlier in the same sentence.
    """
    if span is None:
        return sentence
    start = span[0]
    bounds = [0] + [m.end() for m in re.finditer(r"[,;]", sentence)] + [len(sentence) + 1]
    for lo, hi in zip(bounds, bounds[1:]):
        if lo <= start < hi:
            return sentence[lo:hi]
    return sentence


def _expected_value(fact_value):
    """What a number would have to equal to match this fact, or None."""
    if isinstance(fact_value, bool):
        return None
    if isinstance(fact_value, int):
        return fact_value
    if isinstance(fact_value, list):
        return len(fact_value)
    return None


def _find_conflicting_fact(claim, facts):
    """A fact whose subject this claim's clause is about, but disagrees with.

    Subject overlap is detected by splitting the fact's key on
    underscores: if any of those words appears in the claim's clause
    while the claim's value differs from that fact, the claim is
    contradicted. A coincidental value match to some unrelated fact
    never overrides a genuine, disagreeing subject match -- callers
    should check this before falling back to a bare value-membership
    test for "proven".
    """
    clause_words = set(re.findall(r"[a-z0-9]+", _clause_at(claim.context, claim.span).lower()))
    for key, fact in facts.items():
        expected = _expected_value(fact["value"])
        if expected is None:
            continue
        fact_words = set(key.lower().split("_"))
        if fact_words & clause_words and claim.value != expected:
            return key, fact
    return None


def check(text, profile):
    """Classify every claim in `text` against `profile`'s facts."""
    facts = profile.get("facts", {})
    report = Report()

    match_values = {
        _expected_value(fact["value"])
        for fact in facts.values()
        if _expected_value(fact["value"]) is not None
    }

    for claim in find_claims(text):
        conflict = _find_conflicting_fact(claim, facts)
        if conflict is not None:
            key, fact = conflict
            report.contradicted.append(
                Finding(
                    claim.value, claim.context,
                    conflicts_with=key, fact_value=fact["value"], source=fact["source"],
                )
            )
        elif claim.value in match_values:
            report.proven.append(Finding(claim.value, claim.context))
        else:
            report.unprovable.append(Finding(claim.value, claim.context))

    return report

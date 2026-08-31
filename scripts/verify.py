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

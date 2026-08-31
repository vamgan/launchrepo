"""Fact and Profile: the shape every extracted claim about a repository takes.

A fact without a source is not a fact. Marketing copy for a repository is
checked against a profile built from this module, and every value in that
profile must be traceable back to the command or file that produced it —
otherwise a reader (or a later automated check) has no way to tell a real
measurement from a guess. So `Fact` refuses to exist without a `source`,
and `Profile` refuses to let a missing value masquerade as a real one: an
extraction that fails is recorded as unavailable, with a reason, rather
than silently becoming zero, an empty string, or None hiding in place of
a value. Copy generated from a Profile may state what was verified and
nothing else.
"""


class Fact:
    """An extracted value paired with where it came from."""

    __slots__ = ("value", "source")

    def __init__(self, value, source):
        self.value = value
        self.source = source

    def as_dict(self):
        return {"value": self.value, "source": self.source}

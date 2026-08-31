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
        if not source:
            raise ValueError("a Fact requires a non-empty source")
        self.value = value
        self.source = source

    def as_dict(self):
        return {"value": self.value, "source": self.source}


class Profile:
    """A collection of Facts about one repository, keyed by name.

    Every key is either a recorded Fact or an unavailable reason —
    never both, and never neither with a value silently missing.
    Recording None is not a value: it is routed to `unavailable` so
    a caller can never mistake "we didn't check" for "the answer is
    nothing."
    """

    def __init__(self):
        self._facts = {}
        self._unavailable = {}

    def record(self, key, value, source):
        if value is None:
            self.unavailable(key, f"no value produced by {source}")
            return
        self._unavailable.pop(key, None)
        self._facts[key] = Fact(value, source)

    def unavailable(self, key, reason):
        self._facts.pop(key, None)
        self._unavailable[key] = reason

    def value(self, key):
        fact = self._facts.get(key)
        return fact.value if fact is not None else None

    def source(self, key):
        fact = self._facts.get(key)
        return fact.source if fact is not None else None

    def keys(self):
        return set(self._facts) | set(self._unavailable)

    def reasons(self):
        return dict(self._unavailable)

    def as_dict(self):
        return {
            "facts": {key: fact.as_dict() for key, fact in self._facts.items()},
            "unavailable": dict(self._unavailable),
        }

"""distribute.py: post generated copy to distribution platforms.

The intent is to post automatically. The obstacle is that the platforms
with the most reach forbid exactly that: Hacker News and Product Hunt
treat automated submission as bannable and expect the author present in
the comments, Reddit's self-promotion limits are enforced by humans, and
even GitHub releases -- an owned surface with a real API -- notify every
watcher the moment they're published, which cannot be undone.

So a single global "post automatically" switch is wrong. Autonomy is a
property of the platform, not of the run: each adapter below declares
its own `posture`, and the dispatcher enforces what that posture allows
rather than trusting a caller's flag.
"""

import argparse

import verify

POSTURES = ("auto", "confirm", "prepare")


class Adapter:
    """Base class for a distribution platform adapter.

    `posture` is one of `POSTURES` and is validated at construction --
    a typo in a posture string is a bug in this module, not something
    that should surface later as unexpected autonomy.

    This base class deliberately does not define a `send` method. A
    method that exists can be reached by a future caller who means
    well; a method that does not exist cannot. Adapters whose posture
    is "auto" or "confirm" define their own `send`. Adapters whose
    posture is "prepare" must never define one -- not behind a flag,
    not through configuration -- since a `prepare` adapter's whole job
    is producing something a human still has to act on.
    """

    def __init__(self, name, posture):
        if posture not in POSTURES:
            raise ValueError(
                f"unknown posture {posture!r} for adapter {name!r}: "
                f"must be one of {POSTURES}"
            )
        self.name = name
        self.posture = posture

    def plan(self, copy, **options):
        raise NotImplementedError


def registry():
    """Every known adapter, keyed by name."""
    adapters = ()
    return {adapter.name: adapter for adapter in adapters}


def _describe_contradictions(report):
    parts = []
    for finding in report.contradicted:
        parts.append(
            f"{finding.context!r} says {finding.value!r}, but "
            f"{finding.conflicts_with} = {finding.fact_value!r} ({finding.source})"
        )
    return "; ".join(parts)


def dispatch(name, copy, profile, mode="dry-run", **options):
    """Verify `copy` against `profile`, then hand it to adapter `name`.

    Verification runs first, before the adapter is even looked up.
    Distributing copy that contradicts the repository is the exact
    failure this tool exists to prevent, and the moment before it
    becomes public is the last place to catch it -- so contradicted
    copy must fail here even if `name` is misspelled or doesn't exist,
    rather than surfacing an "unknown adapter" error that would let the
    real problem go unnoticed. Unprovable copy passes through: plenty
    of true statements are unprovable, and blocking them would make the
    tool unusable.
    """
    report = verify.check(copy, profile)
    if not report.ok:
        raise SystemExit(
            f"copy contradicts the repository: {_describe_contradictions(report)}"
        )

    adapters = registry()
    if name not in adapters:
        raise SystemExit(
            f"unknown adapter {name!r}: choices are {', '.join(sorted(adapters)) or '(none registered)'}"
        )
    adapter = adapters[name]

    plan = adapter.plan(copy, **options)

    if mode == "send":
        if not hasattr(adapter, "send"):
            raise SystemExit(
                f"{name}'s posture is '{adapter.posture}': a human must submit "
                "this by hand, this tool cannot send it"
            )
        return adapter.send(plan, **options)

    return plan


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Distribute generated marketing copy to a platform."
    )
    args = parser.parse_args(argv)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

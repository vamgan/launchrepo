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


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Distribute generated marketing copy to a platform."
    )
    args = parser.parse_args(argv)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

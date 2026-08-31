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
import json
import shutil
import subprocess
import sys
import urllib.parse

import verify

POSTURES = ("auto", "confirm", "prepare")

# Hacker News truncates a submitted title past this length, silently,
# in the listing the author never gets to review before it's public.
_HN_TITLE_LIMIT = 80


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


def _split_title(copy):
    """The copy's first line as its title, the rest as its body.

    Generated copy is authored the way a post is: a headline line
    followed by the body. Adapters that need a title (Hacker News,
    a release's subject) read it from here instead of requiring a
    separate CLI flag that could drift out of sync with the copy file.
    """
    lines = copy.strip().splitlines()
    title = lines[0].strip() if lines else ""
    body = "\n".join(lines[1:]).strip()
    return title, body


class HackerNewsAdapter(Adapter):
    """Produces a pre-filled Hacker News submission link.

    Hacker News treats automated submission as bannable and expects
    the author present in the comments, so this adapter's posture is
    "prepare": it can only hand a human a link to click, never submit
    on its own -- see the base class for why that isn't even a `send`
    method that refuses, but no `send` method at all.
    """

    def __init__(self):
        super().__init__("hackernews", "prepare")

    def plan(self, copy, url=None, **_options):
        if not url:
            raise SystemExit(f"{self.name}: --url is required")
        title, _body = _split_title(copy)
        if len(title) > _HN_TITLE_LIMIT:
            raise SystemExit(
                f"{self.name}: title is {len(title)} characters, over the "
                f"{_HN_TITLE_LIMIT}-character limit Hacker News truncates to -- "
                "the author would never see it happen"
            )
        query = urllib.parse.urlencode({"u": url, "t": title})
        return {
            "adapter": self.name,
            "posture": self.posture,
            "submission_url": f"https://news.ycombinator.com/submitlink?{query}",
            "note": "a human must submit this and stay present in the comments; "
                    "automated submission is bannable on Hacker News",
        }


class ProductHuntAdapter(Adapter):
    """Produces a submission plan for Product Hunt.

    Product Hunt has no query-string prefill, so there is no link to
    hand over the way Hacker News gets one -- the plan instead carries
    the submission URL, the copy to paste by hand, and a note that
    launches run 12:01am to 11:59pm Pacific and rank across the whole
    day, so the hour a human chooses to submit matters. Posture is
    "prepare" for the same reason as Hacker News: automated submission
    is bannable and the author is expected present.
    """

    def __init__(self):
        super().__init__("producthunt", "prepare")

    def plan(self, copy, **_options):
        return {
            "adapter": self.name,
            "posture": self.posture,
            "submission_url": "https://www.producthunt.com/posts/new",
            "copy": copy,
            "note": "a human must submit this; Product Hunt launches run "
                    "12:01am to 11:59pm Pacific and rank across the whole day, "
                    "so the hour of submission matters",
        }


class GitHubReleaseAdapter(Adapter):
    """Creates (or plans) a GitHub release via the `gh` CLI.

    GitHub is an owned surface with a real API, so automation is
    appropriate -- posture "auto". But a release notifies every
    watcher the moment it's published and that notification cannot be
    unsent, so this adapter creates a draft unless explicitly told
    otherwise: `publish=True` must be passed on purpose, there is no
    posture-level way to make publishing the default.
    """

    def __init__(self):
        super().__init__("github_release", "auto")

    def plan(self, copy, tag=None, publish=False, **_options):
        if not tag:
            raise SystemExit(f"{self.name}: --tag is required")
        draft = not publish
        command = ["gh", "release", "create", tag, "--notes-file", "-"]
        if draft:
            command.append("--draft")
        return {
            "adapter": self.name,
            "posture": self.posture,
            "command": command,
            "draft": draft,
            "copy": copy,
        }

    def send(self, plan, **_options):
        """Run the planned `gh` command, feeding `copy` in as notes.

        A missing `gh` binary is an environment fact, not a bug in this
        module -- it comes back as `{"ok": False, "reason": ...}` the
        same way `render.render()` reports a missing Chrome, rather
        than raising.
        """
        gh = shutil.which("gh")
        if not gh:
            return {
                "ok": False,
                "reason": "gh binary not found on PATH: install the GitHub CLI "
                          "or add it to PATH",
            }
        command = [gh, *plan["command"][1:]]
        try:
            result = subprocess.run(
                command,
                input=plan["copy"],
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            return {"ok": False, "reason": f"gh could not be run: {exc}"}

        ok = result.returncode == 0
        return {
            "ok": ok,
            "reason": None if ok else result.stderr.strip(),
            "stdout": result.stdout,
        }


def registry():
    """Every known adapter, keyed by name."""
    adapters = (HackerNewsAdapter(), ProductHuntAdapter(), GitHubReleaseAdapter())
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
    parser.add_argument("adapter", nargs="?", help="adapter name, e.g. hackernews")
    parser.add_argument("--copy", metavar="PATH", help="path to the generated copy file")
    parser.add_argument("--profile", metavar="PATH", help="path to a profile JSON file")
    parser.add_argument(
        "--mode",
        choices=("dry-run", "send"),
        default="dry-run",
        help="dry-run (default) plans without acting; send performs the action "
             "an adapter's posture allows",
    )
    parser.add_argument("--url", help="the URL being announced (hackernews)")
    parser.add_argument("--tag", help="the release tag (github_release)")
    parser.add_argument(
        "--publish",
        action="store_true",
        help="publish rather than draft (github_release only; drafts by default)",
    )
    parser.add_argument(
        "--list", action="store_true", help="list every adapter and its posture"
    )
    args = parser.parse_args(argv)

    if args.list:
        for name, adapter in sorted(registry().items()):
            print(f"{name}\t{adapter.posture}")
        return 0

    if not args.adapter:
        parser.error("an adapter name is required unless --list is given")
    if not args.copy or not args.profile:
        parser.error("--copy and --profile are required")

    with open(args.copy, "r", encoding="utf-8") as fh:
        copy = fh.read()
    with open(args.profile, "r", encoding="utf-8") as fh:
        profile = json.load(fh)

    result = dispatch(
        args.adapter,
        copy,
        profile,
        mode=args.mode,
        url=args.url,
        tag=args.tag,
        publish=args.publish,
    )

    output = json.dumps(result, indent=2, sort_keys=True)
    if isinstance(result, dict) and result.get("ok") is False:
        print(output, file=sys.stderr)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())

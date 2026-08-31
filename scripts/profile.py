"""profile.py: walk a git repository and build a Profile of provable facts.

Every extractor in this module either records a value together with the
exact command or file that produced it, or records why it could not.
Nothing here is ever guessed, defaulted, or rounded: an unrecognised
licence body, an unparsable CI matrix, or a failed git command all become
`unavailable` entries rather than a best-effort value, because a wrong
fact stated as true in generated marketing copy is the failure this tool
exists to prevent.
"""

import os
import subprocess

from facts import Profile

GIT_TIMEOUT = 5


def _git(repo, *args, timeout=GIT_TIMEOUT):
    """Run git in `repo` and return stripped stdout, or None on any failure.

    A non-zero exit, a timeout, or git being missing are all the same
    kind of "we don't know" to a caller here -- none of them should ever
    raise out of an extractor and abort the whole profile.
    """
    try:
        result = subprocess.run(
            ["git", "-C", repo, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _remote_slug(remote_url):
    """Extract a repo slug from a git remote URL, e.g.

    https://github.com/vamgan/declutter.git -> declutter
    git@github.com:vamgan/declutter.git     -> declutter
    """
    slug = remote_url.rstrip("/")
    if slug.endswith(".git"):
        slug = slug[: -len(".git")]
    slug = slug.rstrip("/")
    if not slug:
        return None
    return slug.rsplit("/", 1)[-1]


def _extract_name(repo, profile):
    remote = _git(repo, "remote", "get-url", "origin")
    if remote:
        slug = _remote_slug(remote)
        if slug:
            profile.record("name", slug, f"git remote origin ({remote})")
            return
    basename = os.path.basename(os.path.abspath(repo).rstrip(os.sep))
    profile.record("name", basename, "directory name (no git remote configured)")


def extract(repo):
    if not os.path.isdir(os.path.join(repo, ".git")):
        raise SystemExit(f"not a git repository: {repo}")

    profile = Profile()
    _extract_name(repo, profile)
    return profile

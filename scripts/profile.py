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
import re
import subprocess

from facts import Profile

GIT_TIMEOUT = 5

LICENSE_FILENAMES = (
    "LICENSE",
    "LICENSE.md",
    "LICENSE.txt",
    "LICENCE",
    "LICENCE.md",
    "LICENCE.txt",
    "COPYING",
    "COPYING.txt",
)

# Each licence is recognised only by phrases distinctive enough that no
# other common licence body contains them. All phrases in a tuple must
# match (case-insensitively) before that name is used -- a partial match
# is not a match, it's a guess, and guesses are exactly what this file
# must never produce.
LICENSE_SIGNATURES = (
    ("MIT", (
        "permission is hereby granted, free of charge, to any person obtaining a copy",
    )),
    ("Apache-2.0", (
        "apache license",
        "version 2.0",
    )),
    ("GPL-3.0", (
        "gnu general public license",
        "version 3",
    )),
    ("BSD-3-Clause", (
        "redistribution and use in source and binary forms",
        "neither the name of",
    )),
    ("ISC", (
        "permission to use, copy, modify, and/or distribute this software",
    )),
)

LANGUAGE_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".java": "Java",
    ".c": "C",
    ".cpp": "C++",
    ".swift": "Swift",
    ".sh": "Shell",
}

SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    "vendor",
    ".venv",
    "venv",
}


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


def _detect_licence_text(text):
    lowered = text.lower()
    for name, signatures in LICENSE_SIGNATURES:
        if all(signature in lowered for signature in signatures):
            return name
    return None


def _extract_licence(repo, profile):
    for filename in LICENSE_FILENAMES:
        path = os.path.join(repo, filename)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
        except OSError:
            continue
        licence = _detect_licence_text(text)
        if licence:
            profile.record("licence", licence, filename)
        else:
            profile.unavailable(
                "licence", f"{filename} present but its text matched no known licence"
            )
        return
    profile.unavailable("licence", "no LICENSE file found")


def _extract_language(repo, profile):
    counts = {}
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for filename in filenames:
            ext = os.path.splitext(filename)[1]
            if ext in LANGUAGE_EXTENSIONS:
                counts[ext] = counts.get(ext, 0) + 1

    if not counts:
        profile.unavailable("language", "no recognised source files found")
        return

    best_ext = max(counts, key=lambda ext: counts[ext])
    count = counts[best_ext]
    profile.record(
        "language", LANGUAGE_EXTENSIONS[best_ext], f"{count} {best_ext} file(s)"
    )


_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _extract_history(repo, profile):
    count = _git(repo, "rev-list", "--count", "HEAD")
    if count is not None and count.isdigit():
        profile.record("commit_count", int(count), "git rev-list --count HEAD")
    else:
        profile.unavailable("commit_count", "git rev-list --count HEAD failed")

    log = _git(repo, "log", "--reverse", "--format=%ad", "--date=short")
    first_date = log.splitlines()[0] if log else None
    if first_date and _ISO_DATE_RE.match(first_date):
        profile.record(
            "first_commit_date",
            first_date,
            "git log --reverse --format=%ad --date=short",
        )
    else:
        profile.unavailable(
            "first_commit_date",
            "git log --reverse --format=%ad --date=short produced no usable date",
        )

    authors = _git(repo, "log", "--format=%ae")
    unique_authors = {line for line in authors.splitlines() if line} if authors is not None else set()
    if unique_authors:
        profile.record(
            "contributor_count", len(unique_authors), "git log --format=%ae"
        )
    else:
        profile.unavailable(
            "contributor_count", "git log --format=%ae produced no author emails"
        )


def extract(repo):
    if not os.path.isdir(os.path.join(repo, ".git")):
        raise SystemExit(f"not a git repository: {repo}")

    profile = Profile()
    _extract_name(repo, profile)
    _extract_licence(repo, profile)
    _extract_language(repo, profile)
    _extract_history(repo, profile)
    return profile

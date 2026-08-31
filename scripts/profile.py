"""profile.py: walk a git repository and build a Profile of provable facts.

Every extractor in this module either records a value together with the
exact command or file that produced it, or records why it could not.
Nothing here is ever guessed, defaulted, or rounded: an unrecognised
license body, an unparsable CI matrix, or a failed git command all become
`unavailable` entries rather than a best-effort value, because a wrong
fact stated as true in generated marketing copy is the failure this tool
exists to prevent.
"""

import argparse
import json
import os
import re
import subprocess

from facts import Profile

GIT_TIMEOUT = 5
DECLARED_FACT_TIMEOUT = 30

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

# Each license is recognised only by phrases distinctive enough that no
# other common license body contains them. All phrases in a tuple must
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


def _detect_license_text(text):
    lowered = text.lower()
    for name, signatures in LICENSE_SIGNATURES:
        if all(signature in lowered for signature in signatures):
            return name
    return None


def _extract_license(repo, profile):
    for filename in LICENSE_FILENAMES:
        path = os.path.join(repo, filename)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
        except OSError:
            continue
        license = _detect_license_text(text)
        if license:
            profile.record("license", license, filename)
        else:
            profile.unavailable(
                "license", f"{filename} present but its text matched no known license"
            )
        return
    profile.unavailable("license", "no LICENSE file found")


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

# A bare scalar we're willing to treat as a platform name/expression --
# letters, digits, dot, hyphen, underscore. Anything else (YAML tags like
# `!!weird`, anchors, nested structures) is a shape we do not attempt to
# parse: recording nothing is safer than a partial or wrong read.
_YAML_SCALAR_RE = re.compile(r"^[A-Za-z0-9_.\-]+$")


def _parse_yaml_flow_list(inner):
    """Parse the inside of a `[a, b, c]` flow list of bare/quoted scalars.

    Returns the list of items, or None if any item isn't a plain scalar
    we're confident about -- never a partial list.
    """
    items = []
    for raw_item in inner.split(","):
        item = raw_item.strip()
        if not item:
            continue
        if len(item) >= 2 and item[0] == item[-1] and item[0] in "\"'":
            item = item[1:-1]
        if not _YAML_SCALAR_RE.match(item):
            return None
        items.append(item)
    return items if items else None


def _scan_os_matrix(path):
    """Look for a `strategy: matrix: os:` line in one workflow file.

    Returns (items, reason). `items` is a parsed list only when an `os:`
    line was found and confidently parsed. `reason` is set only when an
    `os:` line was present but NOT confidently parsable -- distinct from
    no `os:` line being present at all, so the caller can tell "there is
    no matrix here" from "there is a matrix here we can't trust."
    """
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
    except OSError:
        return None, None

    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("os:"):
            continue
        value = stripped[len("os:"):].strip()
        if value.startswith("[") and value.endswith("]"):
            items = _parse_yaml_flow_list(value[1:-1])
            if items:
                return items, None
        return None, f"could not confidently parse `{stripped}`"
    return None, None


def _scan_runs_on(path):
    """Look for a plain `runs-on: value` line in one workflow file.

    A `${{ ... }}` value is a reference to a matrix variable, not a
    literal platform, so it is skipped rather than treated as a hit.
    """
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
    except OSError:
        return None, None

    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("runs-on:"):
            continue
        value = stripped[len("runs-on:"):].strip()
        if value.startswith("${{"):
            continue
        if _YAML_SCALAR_RE.match(value):
            return [value], None
        return None, f"could not confidently parse `{stripped}`"
    return None, None


def _extract_ci_platforms(repo, profile):
    workflows_dir = os.path.join(repo, ".github", "workflows")
    if not os.path.isdir(workflows_dir):
        profile.unavailable("ci_platforms", "no .github/workflows directory found")
        return

    workflow_files = sorted(
        f for f in os.listdir(workflows_dir) if f.endswith((".yml", ".yaml"))
    )
    if not workflow_files:
        profile.unavailable(
            "ci_platforms", "no workflow files found in .github/workflows"
        )
        return

    # An explicit `os:` matrix is checked across every file before any
    # bare `runs-on:` is considered, so a single-job `runs-on:
    # ubuntu-latest` in one file (e.g. a docs-deploy workflow that
    # happens to sort first) can never eclipse a real multi-platform
    # matrix declared in another file.
    matrix_failure = None
    for filename in workflow_files:
        items, reason = _scan_os_matrix(os.path.join(workflows_dir, filename))
        if items:
            profile.record("ci_platforms", items, f".github/workflows/{filename}")
            return
        if reason and matrix_failure is None:
            matrix_failure = f"{filename}: {reason}"

    if matrix_failure:
        # A matrix was declared somewhere but couldn't be trusted -- stay
        # unavailable rather than quietly falling back to a weaker signal.
        profile.unavailable("ci_platforms", matrix_failure)
        return

    for filename in workflow_files:
        items, reason = _scan_runs_on(os.path.join(workflows_dir, filename))
        if items:
            profile.record("ci_platforms", items, f".github/workflows/{filename}")
            return

    profile.unavailable(
        "ci_platforms", "no os matrix or runs-on found in workflow files"
    )


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


# A tiny, deliberately narrow reader for launchrepo.toml. tomllib only
# ships in Python 3.11+ and this must run on 3.10, and general TOML has
# far more shape than we need -- we only ever expect `[facts.NAME]`
# tables containing `key = "quoted string"` lines, so that's all this
# parses. Anything outside that shape (nested tables, arrays, bare
# numbers/booleans, multi-line strings) is simply not recognised.
_FACT_TABLE_RE = re.compile(r"^\[facts\.([A-Za-z0-9_\-]+)\]$")
_FACT_KV_RE = re.compile(r'^([A-Za-z0-9_\-]+)\s*=\s*"((?:[^"\\]|\\.)*)"$')


def _parse_launchrepo_toml(text):
    declared = {}
    current = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        table_match = _FACT_TABLE_RE.match(line)
        if table_match:
            current = table_match.group(1)
            declared.setdefault(current, {})
            continue
        kv_match = _FACT_KV_RE.match(line)
        if kv_match and current is not None:
            key, raw_value = kv_match.groups()
            declared[current][key] = raw_value.replace('\\"', '"').replace("\\\\", "\\")
    return declared


_INT_RE = re.compile(r"^-?\d+$")


def _coerce_declared_value(output):
    if _INT_RE.match(output):
        return int(output)
    return output


def _extract_declared_facts(repo, profile):
    toml_path = os.path.join(repo, "launchrepo.toml")
    if not os.path.isfile(toml_path):
        return

    try:
        with open(toml_path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return

    for name, table in _parse_launchrepo_toml(text).items():
        command = table.get("command")
        if not command:
            profile.unavailable(name, f"launchrepo.toml [facts.{name}] has no command")
            continue

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=repo,
                capture_output=True,
                text=True,
                timeout=DECLARED_FACT_TIMEOUT,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            profile.unavailable(name, f"command `{command}` could not be run: {exc}")
            continue

        if result.returncode != 0:
            profile.unavailable(
                name, f"command `{command}` exited {result.returncode}"
            )
            continue

        profile.record(
            name,
            _coerce_declared_value(result.stdout.strip()),
            f"launchrepo.toml [facts.{name}] command `{command}`",
        )


def extract(repo):
    if not os.path.isdir(os.path.join(repo, ".git")):
        raise SystemExit(f"not a git repository: {repo}")

    profile = Profile()
    _extract_name(repo, profile)
    _extract_license(repo, profile)
    _extract_language(repo, profile)
    _extract_history(repo, profile)
    _extract_ci_platforms(repo, profile)
    # Declared facts run last so a repository's own launchrepo.toml can
    # override anything generic extraction produced above.
    _extract_declared_facts(repo, profile)
    return profile


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Extract a fact profile from a git repository."
    )
    parser.add_argument("repo", nargs="?", default=".", help="path to the repository")
    parser.add_argument(
        "--out", metavar="PATH", help="write JSON to this path instead of stdout"
    )
    args = parser.parse_args(argv)

    profile = extract(args.repo)
    output = json.dumps(profile.as_dict(), indent=2, sort_keys=True)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(output + "\n")
    else:
        print(output)


if __name__ == "__main__":
    main()

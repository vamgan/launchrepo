"""render.py: turn a fact profile into marketing images via headless Chrome.

Copy is authored as HTML templates with `{{key}}` placeholders. Those
placeholders are substituted with values from a profile (facts proven
about the repository) and from `extras` (values the profile cannot
prove, such as a hand-written tagline). Substitution happens before
Chrome is ever launched: an unprovable placeholder is a hard error, and
paying for a browser start before finding that out would be wasted
work. A missing or unreadable Chrome binary is not an error at this
layer either -- `render()` reports it in the result it returns, because
copy generation (and thus `fill()`) has to keep working on machines
that have no browser at all.
"""

import html
import os
import re
import shutil

_PLACEHOLDER_RE = re.compile(r"\{\{(\w+)\}\}")

# Candidates covering the common install locations for Chrome/Chromium
# across platforms. Bare names (no path separator) are resolved with
# `shutil.which` against $PATH; entries containing a path separator are
# checked directly with os.access, since `which` only ever resolves
# names on $PATH. Order matters: the macOS app bundle path comes first
# because it's the most common source on a developer's own machine.
_DEFAULT_CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
)


def fill(template, profile, extras=None):
    """Substitute `{{key}}` placeholders in `template`.

    `extras` is checked before the profile's facts, so a caller-supplied
    value always wins. Every substituted value is HTML-escaped -- these
    templates are HTML, and a fact or extra is untrusted text as far as
    the page is concerned. A placeholder naming a key that is neither in
    `extras` nor among the profile's facts is a hard error: an unknown
    or unprovable placeholder must never render as a blank space, since
    a blank space looks like a finished asset instead of a broken one.
    """
    extras = extras or {}
    facts = profile.get("facts", {})
    unavailable = profile.get("unavailable", {})

    def replace(match):
        key = match.group(1)
        if key in extras:
            value = extras[key]
        elif key in facts:
            value = facts[key]["value"]
        elif key in unavailable:
            raise SystemExit(
                f"placeholder {{{{{key}}}}} is unavailable: {unavailable[key]}"
            )
        else:
            raise SystemExit(f"placeholder {{{{{key}}}}} has no value in profile or extras")
        return html.escape(str(value))

    return _PLACEHOLDER_RE.sub(replace, template)


def find_chrome(explicit=None, candidates=None):
    """Locate a Chrome/Chromium binary to drive headlessly.

    Precedence: an explicit path always wins (the caller knows best),
    then `$CHROME` (the conventional escape hatch for CI and unusual
    installs), then the first working entry from `candidates` (default:
    `_DEFAULT_CANDIDATES`). Returns None -- never raises -- when nothing
    is found, so callers can degrade instead of crashing.
    """
    if explicit:
        return explicit

    env_chrome = os.environ.get("CHROME")
    if env_chrome:
        return env_chrome

    if candidates is None:
        candidates = _DEFAULT_CANDIDATES

    for candidate in candidates:
        if os.sep in candidate or (os.altsep and os.altsep in candidate):
            if os.access(candidate, os.X_OK):
                return candidate
            continue
        found = shutil.which(candidate)
        if found:
            return found

    return None

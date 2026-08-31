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
import re

_PLACEHOLDER_RE = re.compile(r"\{\{(\w+)\}\}")


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

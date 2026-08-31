---
name: writing-a-readme
description: Use when writing or rewriting a README for a repository, or when a README is stale, thin, or reads like a category rather than a product. Triggers on "write a readme", "improve my readme", "my readme is bad", "what should my readme say".
---

# Writing a README

A README is the landing page for most people who ever see the project. Treat it as the
argument for why someone should spend the next ten minutes, not as documentation.

## Start from facts, not from a blank page

```bash
python3 scripts/profile.py <repo> --out profile.json
```

Read the profile before writing a word. **Every number you write must come from it.**
If the profile cannot prove something, either leave it out or get the repository to
declare it in `launchrepo.toml`. Do not write a number you have not checked, and do not
carry a number over from an older draft.

When you are done:

```bash
python3 scripts/verify.py README.md --profile profile.json
```

Fix contradictions. Read the unprovable list and decide, for each, whether to cut it or
give it a source.

## Structure that works

1. **Name, one-line description, badges.** The description says what it is, not what
   category it belongs to.
2. **The problem, in the reader's own words.** Describe the mess they recognise on
   their own machine. Not the mechanism.
3. **What it looks like.** A transcript, a screenshot, or a short before and after. This
   is the thing people scroll to.
4. **Install.** Exact commands, in a code block, near the top. Not at the bottom.
5. **What it does**, as a table if there is more than one piece.
6. **Honest status.** What is tested, what is not, which platforms have actually been
   used rather than merely built.
7. **Contributing**, with the smallest true statement of what it costs.
8. **Licence.**

## The failure that matters most

**Do not assume the reader knows your vocabulary.**

Real examples of copy that failed this test:

- "Adding Vivaldi was one line in a table." Most readers do not know Vivaldi is a
  browser, so the sentence carries no information for them.
- "Finds byte-identical duplicates, orphans, and tag sprawl, without breaking your
  `[[wikilinks]]`." Every one of those terms assumes the reader already lives in that
  world.
- "oss-launchkit". An abbreviation an insider reads instantly and nobody else does.

Rewrite each as the thing the reader would recognise:

- "Every browser above was added the same way."
- "Notes you started and never finished. Two versions of the same list. Half a dozen
  tags that all mean the same thing."

The test: **could someone outside this field read the sentence and know what it means?**
If not, it is describing the mechanism when it should describe the mess.

## Honest status beats implied completeness

A README that implies something works when it does not converts once and burns the
reader permanently. Say plainly which platforms have been used and which have only been
built. Mark unfinished things as unfinished. "Implemented, CI-tested, but nobody has run
a full pass on it" is a sentence worth writing.

## Never

- Write a number you have not read out of the profile
- Describe the category instead of the product in the first line
- Bury the install command
- Imply coverage that does not exist
- Assume the reader knows an abbreviation, a product name, or a term of art

---
name: writing-launch-posts
description: Use when writing launch announcements for a repository — a Show HN post, a Product Hunt launch, a Reddit or X post, or a Dev.to article. Triggers on "write a show hn", "launch post", "post about my project", "announce my repo", "product hunt launch".
---

# Writing Launch Posts

Same facts, different argument. A post that works on Hacker News fails on Product Hunt
and the reverse, and the difference is not tone. It is which question the audience is
asking.

## Before writing

```bash
python3 scripts/profile.py <repo> --out profile.json
```

Read it. Every number in every post comes from there. After writing each post:

```bash
python3 scripts/verify.py post.md --profile profile.json
```

A contradiction is a hard stop. Fix it before the post exists anywhere.

## Hacker News

**The question the audience is asking: is this interesting, and is the author honest?**

Title: `Show HN: Name – what it does` and it must fit in 80 characters. An en-dash is
the convention there.

Lead with the **most interesting engineering decision**, not the benefit. The reader
can infer the benefit; what they cannot get elsewhere is why you built it that way and
what you learned. If a design choice was forced by a constraint, say what the constraint
was.

**Be candid about limitations before anyone asks.** The comments will find them. A post
that says "only tested on macOS, Linux and Windows are CI-only" reads as trustworthy;
the same post without that line reads as trustworthy until someone checks, and then it
reads as a sales pitch.

**Admitting a mistake is worth more than a clean story.** If a claim you published was
wrong and you fixed it, say so. That is the single most credible thing a Show HN can
contain.

Get ahead of the obvious objection. If the project touches something the audience is
protective of, their files, their data, their money, address it in the post rather than
in a reply.

Show HN rules that get posts killed: you must be present in the thread, the thing must
be usable by the reader, and automated or coordinated voting is a permanent ban. Never
submit programmatically.

## Product Hunt

**The question: what does this do for me, and is it real?**

- Tagline, 60 characters, benefit not category
- Description, 260 characters, plain language
- A maker's first comment that sounds like a person

**No jargon at all.** Not "stdlib", not "EXIF", not the name of a file format. If a
sentence would need a footnote for a non-engineer, cut it.

Launches run 12:01am to 11:59pm Pacific and ranking depends on the whole day, so a
random hour wastes it. The gallery needs real images. The maker being present in the
comments is part of how it ranks.

## X

Automation is expected and sanctioned here, unlike the others. Lead with the single most
surprising true sentence. Threads work when each post stands alone.

## Reddit

Rules vary per subreddit and most relevant ones remove posts that look automated.
Self-promotion limits are real and enforced by humans. Read the sidebar of the specific
subreddit before writing, and never post the same text to several.

## Dev.to and Hashnode

Real publishing APIs, no rule against automation. Long form works. This is the safest
place to be fully automatic.

## The opening line

Almost every weak launch post fails in the first two sentences, by describing the
category instead of the problem.

Weak: "An open-source toolkit for repository management workflows."

Strong: name the mess in numbers the reader recognises. Real measurements from your own
machine are worth more than any adjective, and they are checkable, which is the point.

## Never

- Use a number you did not read out of the profile
- Claim something about the author's own setup that you have not verified
- Reuse the Hacker News text on Product Hunt, or the reverse
- Submit to Hacker News, Reddit or Product Hunt automatically
- Imply the project does something it does not yet do

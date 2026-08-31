---
name: writing-a-landing-page
description: Use when building or improving a landing page for a repository, or a GitHub Pages site for a project. Triggers on "build a landing page", "make a website for my project", "improve my project site", "github pages site".
---

# Writing a Landing Page

One self-contained HTML file. No build step, no framework, no dependency that has to be
installed before someone can see it. It deploys from a repository directory to GitHub
Pages with a workflow and nothing else.

## Before writing

```bash
python3 scripts/profile.py <repo> --out profile.json
```

Every number on the page comes from the profile. Never type one from memory or
carry one across from an older draft. Afterwards:

```bash
python3 scripts/verify.py site/index.html --profile profile.json
```

## Structure

Install belongs high, not at the bottom. The reader who is convinced in the first ten
seconds should not have to hunt.

1. Navigation, one line, under 80px tall
2. Hero: headline of at most two lines, subtext of at most 20 words, the install
   command, and one primary action
3. A visual that shows the actual concept, not a simulated screenshot
4. Install, in full, with every supported method
5. What it does
6. How to extend it
7. Whatever the reader has to trust, stated plainly

## Rules learned the hard way

**Derive every published number.** A count that appears in three places will be wrong in
at least one of them within a week. Generate them from the profile, and add a test that
fails when a published number stops matching the code. This is not hypothetical: a page
once said "Ten browsers" in a pill while a table two sections below said eleven, because
the number was hand-written in three places and only one was updated.

**A simulated product screenshot built from styled boxes is a tell.** If you need to
show the product, show the real thing, generate a real image, or show the concept
instead. A fake terminal is the most common version of this mistake.

**Content must degrade without JavaScript.** If a scroll-reveal effect starts elements
at zero opacity, a script failure leaves a blank page. Hide only after confirming the
script runs, and add a timeout that reveals everything regardless.

**Every translucent surface needs an opaque fallback.** Under `prefers-reduced-transparency`
a translucent white panel with the blur stripped is invisible on a light page, and the
navigation and buttons float with no edges. Cover every glass surface, not the ones that
existed when the fallback was written.

**Check contrast against the composited background**, not the base colour. Translucency
tints what sits behind text, and a colour that passes on white can fail on glass.

**Test at mobile width before shipping.** A pill navigation that fits on a laptop will
overflow a 375px viewport and take the whole page's horizontal scroll with it.

## Assets

```bash
python3 scripts/render.py templates/banner.html --profile profile.json \
  --out site/assets/banner.png --width 1600 --height 400 --set tagline="..."
```

The social card is a different composition from the banner, not a resize. Link previews
are 2:1 and crop toward the centre, so the wordmark stays left of centre. Open Graph
tags need an absolute image URL; scrapers ignore relative paths.

## Never

- Hand-write a number that appears anywhere else
- Build a fake screenshot out of styled boxes
- Hide content behind JavaScript with no fallback
- Ship a glass surface with no opaque alternative
- Leave install below the fold

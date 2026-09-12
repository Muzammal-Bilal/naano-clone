# Walkthrough script

Target runtime **4:45**. The brief allows five minutes maximum, so this is
written with fifteen seconds of margin rather than to the limit.

Camera on throughout. Record the live URL, never localhost.

**Live:** https://muzammalbilal.pythonanywhere.com
**Demo accounts:** `brand / demo1234` and `creator / demo1234`

---

## Before you hit record

- Open two browser tabs: the live homepage, and the login page.
- Sign in as `brand` in one tab beforehand so you are not typing a password on camera.
- Have the campaign form half filled in, so that section does not run silent.
- Close notifications, and anything on screen you would not want a reviewer to see.
- Do one throwaway take to warm up. It is always better than the first real one.

---

## 0:00 - 0:25 — Open (camera only, no screen share yet)

> Hi, I'm Muzammal Bilal. For the 8x assignment I picked the Naano brief, the
> B2B LinkedIn creator marketplace, and rebuilt it in Python and Django over one
> day.
>
> Naano is two-sided, and you cannot build both sides properly in a day, so I
> picked the spine that makes it a business instead of a directory: find
> creators, brief them, book them, and track what came back.
>
> Let me show you the live site.

## 0:25 - 1:05 — Landing page, signed out

*Share screen. Scroll the homepage slowly while talking.*

> This is the public front door, and it is the real deployed site, not
> localhost. I built the landing page first, because a reviewer who is not
> signed in still has to land on something that looks like a product.
>
> One deliberate detail: these creator cards do not show a match score, because
> you are signed out and there is nothing to match you against. That score only
> appears once a brand has an ideal customer profile. I would rather show
> nothing than show a number that means nothing.

*Hover the Resources dropdown, then click into Free Tools.*

> The nav matches the real site, with separate pages for creators and agencies,
> and a Resources menu that opens on hover. This budget calculator is live, the
> maths runs in the browser.

## 1:05 - 2:00 — Sign in as a brand, Discover

> I will sign in as a brand. The demo credentials are printed on the login page,
> so you do not need to sign up to see either side.

*Filter by a topic, then drag the price slider.*

> This is the marketplace. Filter by topic, country, price, audience size.
> Nothing reloads, that is HTMX swapping just the results.
>
> And now you can see the match score, because this brand has an ICP. It weighs
> topic overlap against that profile, so a two-thousand-follower voice speaking
> to your exact buyer outranks a two-hundred-thousand-follower generalist. That
> ranking is the actual product opinion here.

## 2:00 - 2:45 — Campaign brief builder

*Campaigns, then create one.*

> I give it an objective and describe the product, and it writes the structured
> brief: key messages, guidelines, the do's and don'ts.
>
> That is template-driven, not an LLM call. No API key, no latency, no spend,
> and it cannot fail mid-demo. If you wanted a model behind it, it is one
> function in `services.py`.

## 2:45 - 3:25 — Book a creator, then the creator side

*Back to Discover, open a creator, book them onto the campaign.*

> Book them onto that campaign at their price. Now the interesting part, because
> the other side of the marketplace actually exists.

*Sign out, sign in as `creator`, open the deal.*

> Signing in as that creator, the deal is in their inbox. They can accept or
> decline, and write the post.
>
> This is where writing tests found two real bugs. A declined deal could be
> pulled back into the pipeline by posting a draft to it, and an empty draft was
> accepted as a submission. Both are fixed, and there are twenty-two tests
> covering access control and this lifecycle.

## 3:25 - 4:05 — Pipeline and analytics

*Back on the brand side.*

> The booking moves through invited, accepted, draft ready, scheduled, live.
>
> And analytics: impressions, clicks, click-through rate, leads and attributed
> pipeline, charted daily and split per campaign. The seeded metrics decay
> geometrically after publishing, which is what makes this read as real data
> rather than noise.

## 4:05 - 4:45 — What you cut, and close

*Camera full screen if you can.*

> What I left out was deliberate, and it is all in the README.
>
> No LinkedIn OAuth, that needs a partner app and days of review for zero
> visible product. No Stripe: the wallet is a ledger that records movement
> without moving money. No real click tracking, because attribution is a product
> in itself. And the landing page has no video testimonial, because I do not
> have a video, and a play button that does nothing is worse than not having
> one.
>
> Everything the agent did is in `.agent-logs` in the repo, committed as I went.
> The repo link and the live link are in the submission. Thanks for watching.

---

## If a take runs long

Compress the analytics section first. Protect the closing cut list: "what you
built first, what you left out" is stated in the brief as a scoring criterion,
so it is the most valuable forty seconds in the video.

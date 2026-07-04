# How to write the blog for this repo

A reusable playbook so we never re-derive this. It's tuned for **Vendor vs Valor**, but it holds for any project blog where the goal is "make a smart outsider care," not "teach an engineer to rebuild it."

---

## 0. The one decision that governs everything

**The README explains *how it works*. The blog explains *why it should exist and who it's for*.**

Those are different jobs. The repo, the README, and `interview.md` already carry the technical weight — contracts, schemas, the hash guard, the API surface. The blog does not repeat them. It earns a click from someone who will *never read the README*: a founder, an operator, an investor, a curious friend. If they finish the blog and can explain the project to *someone else* in two sentences, it worked.

Technical decisions still appear — but as **ideas with stakes**, never as implementation notes. "The engine isn't allowed to trust its own quotes; a separate pass re-reads the source and grades it" is an idea anyone gets. "`verify()` resolves a char-span locator against cached bytes" is a README line. Use the first kind. Link to the repo for the second.

---

## 1. Know who's reading (and write down the answer first)

Before a word: name the reader and the takeaway in one line each.

- **Reader:** a technically-literate-but-not-engineer decision-maker. Reads on a phone, half-distracted, billions of other tabs open.
- **Takeaway:** "Build-vs-buy decisions are capital decisions in disguise, and most teams make them on a gut and a vendor demo. This is a machine that does the research, cites everything, argues with itself, and hands a human the call."

If you can't write those two lines, you're not ready to write the post.

**Why before how.** Non-technical readers move on *benefits*, not *features* — start with the outcome and the stakes, let the curious opt into depth later. ([Stanford Online](https://online.stanford.edu/10-tips-communicating-technical-ideas-non-technical-people), [Technical Leaders](https://www.technical-leaders.com/post/technical-vs-non-technical-audiences-communication-strategies))

---

## 2. The shape: a story spine, not a feature list

A feature list is a brochure. A story is a memory. Use the **story spine** — the same six beats Pixar uses — bent onto this project. ([Anvil](https://www.useanvil.com/blog/engineering/writing-technical-blog-posts-with-the-story-spine/))

| Beat | The job | For Vendor vs Valor |
|---|---|---|
| **Once upon a time** | Set the normal world | A platform team modernizing a portfolio of companies. |
| **Every day** | The recurring routine | The same question, over and over: build this, or buy it? |
| **One day** | The problem shows up | The call gets made on a demo, a gut, a spreadsheet that fakes precision. Capital walks out the door. |
| **Because of that** | The pain compounds | Duplicated effort, lock-in nobody priced, a "cheap" SaaS that's a trap. |
| **Because of that** | The search for a fix | Why not a consultant? A checklist? A generic research bot? (None compound, none cite, none know the decision's shape.) |
| **Until finally** | The resolution | The engine: intake → research both sides → verify every claim → reason over four paths → argue against itself → hand a human the decision. |

You don't need to label the beats. You need the reader to feel the hole get dug before you show them the ladder out.

---

## 3. A working section skeleton

Roughly 800–1,400 words. Five-to-eight-minute read. Each header should make sense even if the body underneath vanished — that's the skim test. ([refactoringenglish.com](https://refactoringenglish.com/chapters/write-blog-posts-developers-read/))

1. **Title + first three sentences.** State who it's for and the payoff, fast. No throat-clearing, no "in today's fast-paced world." The first three sentences must answer: *is this for me, and what do I get?* ([refactoringenglish.com](https://refactoringenglish.com/chapters/write-blog-posts-developers-read/))
2. **The expensive little question.** "Build or buy?" framed as a capital decision wearing engineering clothes. This is the hook — make the reader feel the cost.
3. **Why the usual answers fail.** Consultant, checklist, gut, generic AI bot — each in a line. Earns the existence of the thing.
4. **What it actually does.** The pipeline as a plain-English journey, not a diagram dump. Intake, research, verify, synthesize, challenge, report.
5. **The two or three ideas worth stealing.** The genuinely interesting decisions, told as concepts (see §5). This is where a technical reader leans in and a non-technical reader still nods.
6. **What it deliberately doesn't do.** The honesty section. No scores. No "acquire" path. Doesn't make the call. Knowing the edge of your competence is a feature — say so.
7. **Where it goes / try it.** Use cases, the GitHub link, one line on what's next (portfolio memory).

---

## 4. Voice: crisp, dry, human — not quippy

The target is *a sharp colleague explaining something at a whiteboard*, not a LinkedIn motivational post. The difference matters, because "be witty" fails loudly when it tries too hard.

**Do**
- **Short sentences carry the weight. Longer ones connect.** Vary the rhythm on purpose — uniform sentence length is the single biggest "a machine wrote this" tell. ([Grammarly](https://www.grammarly.com/blog/ai/how-to-avoid-ai-detection/))
- **Use contractions, "you," and a real opinion.** Have a point of view. A machine has no beliefs; the reader wants yours. ([Grammarly](https://www.grammarly.com/blog/ai/how-to-avoid-ai-detection/))
- **Be concrete.** "A cheap SaaS with brutal switching costs becomes a trap nobody priced" beats "vendor lock-in is a risk."
- **Read it aloud.** If you wouldn't say it to a person, cut it. ([Grammarly](https://www.grammarly.com/blog/ai/how-to-avoid-ai-detection/))
- **Let dry wit do the work.** Understatement lands; punchlines strain. "It knows the edge of its own competence — which is more than you can say for most spreadsheets" is enough.

**Don't**
- No AI throat-clearing or filler: *"In the rapidly evolving landscape," "It's worth noting that," "Let's dive in," "At the end of the day."*
- No em-dash-and-tricolon pattern on every line. No paragraph that's three sentences of identical length.
- No exclamation marks doing the job a strong sentence should do.
- No emoji unless the whole piece has earned a playful register.
- Don't perform enthusiasm. Show the thing being interesting; trust the reader to feel it.

---

## 5. Metaphors: a few, load-bearing, then stop

Analogy is how you smuggle a technical idea past a non-technical reader's defenses — it borrows something they already know to explain something they don't. ([explainability.dev](https://explainability.dev/article/How_to_Use_Analogies_to_Explain_Technical_Concepts_to_NonTechnical_Audiences.html)) But more than one per idea, or three in a paragraph, and it turns to mud. Save them for the parts that actually need the lift. ([clickhelp](https://clickhelp.com/clickhelp-technical-writing-blog/metaphor-in-technical-writing/))

Candidate metaphors for the hard-to-explain ideas (pick the best two or three, don't use all):

- **`grounded_claim` / verification** → *"The reporter doesn't get to grade their own story. A separate fact-checker re-reads the source and decides if it holds up."* The single most important idea in the project; spend your best metaphor here.
- **Source cache = closed evidence pool** → *"Everything's locked in an evidence room. You can't cite a document that isn't already on the table."*
- **Four paths as lenses over two evidence pools** → *"Two piles of research, four ways of looking at them — like the same photo through four different filters."*
- **The challenger pass** → *"Before it commits, the engine plays devil's advocate against itself — a built-in second opinion that has to argue with receipts."*
- **No scores** → *"It refuses to turn a judgment call into a fake 4.1 out of 5. False precision is just confidence cosplay."*

Anchor in the familiar, then add the twist ("the Airbnb for X" works because it does both). ([Stanford Online](https://online.stanford.edu/10-tips-communicating-technical-ideas-non-technical-people))

---

## 6. Lead with use cases, because that's what a reader can hold

Features are abstract; uses are pictures. Give two or three concrete "someone has a problem" scenes — the real run in `interview.md` (the Indian market-data startup choosing buy-then-extend under a 4-week regulatory deadline) is gold because it shows a *real tension*, not a happy path. One good worked example beats a paragraph of capability claims.

Frame each use case as a person in a bind, not a feature being exercised:
- A startup deciding whether to license market data or scrape it (and the regulator that makes that choice expensive).
- A platform team about to let six companies each buy the same vector database six times.
- Anyone who's ever picked a vendor off a demo and a gut feeling, then paid for it for three years.

---

## 7. Technical decisions — include them, as ideas

The reader doesn't need to read the code, but the *taste* behind the decisions is the most interesting part of the project. Surface the choices as one-line ideas with a stake. A few that translate well:

- **The model can't bless its own claims** — trust is enforced by code, not by asking the AI to be careful. (The deepest idea in the repo.)
- **It cites everything against a frozen copy of the source** — so it can't quietly change its story, and the whole run replays offline.
- **It argues against itself before it commits** — earned confidence, not manufactured confidence.
- **It refuses to score** — no weighted 1–5 theater; it names the two or three factors that actually drove the call.
- **It won't pretend it can value an acquisition** — that's M&A diligence, not web research, so it stays out. Knowing your limits is the feature.
- **The decision stays human** — the machine does the research; a person makes the call. That's the right posture for spending money.

Each of these is a *value*, legible to anyone. The README has the mechanism; the blog has the meaning.

---

## 8. Cut list (run this before publishing)

- Any sentence that survives deletion without the post getting worse. Cut it. ([freeCodeCamp](https://www.freecodecamp.org/news/how-to-write-a-great-technical-blog-post-414c414b67f6/))
- The meandering intro. Get to the expensive question fast.
- Detail that's "related but not load-bearing." Relatedness is not a reason to keep something.
- Anything that's really a README line in disguise (schemas, signatures, file paths) — link instead.
- Jargon a smart outsider would stumble on, unless you spend one sentence defining it. One swapped word can multiply the audience. ([refactoringenglish.com](https://refactoringenglish.com/chapters/write-blog-posts-developers-read/))
- Every third metaphor.

---

## 9. Pre-publish checklist

- [ ] First three sentences answer "is this for me?" and "what do I get?"
- [ ] A non-technical friend could explain the project to someone else after reading.
- [ ] Headers alone tell the story (the skim test).
- [ ] Sentence lengths vary; nothing reads like a uniform machine cadence.
- [ ] Two or three metaphors, each pulling real weight — not more.
- [ ] At least one concrete worked example / use case with a real tension.
- [ ] An honesty section: what it deliberately doesn't do.
- [ ] No AI-tell filler ("dive in," "in today's landscape," "it's worth noting").
- [ ] A clear link to the repo for anyone who wants the how.
- [ ] Read aloud start to finish; every line is something a human would actually say.

---

## Sources

- [refactoringenglish.com — Write blog posts developers read](https://refactoringenglish.com/chapters/write-blog-posts-developers-read/)
- [Anvil — Writing technical blog posts with the story spine](https://www.useanvil.com/blog/engineering/writing-technical-blog-posts-with-the-story-spine/)
- [freeCodeCamp — How to write a great technical blog post](https://www.freecodecamp.org/news/how-to-write-a-great-technical-blog-post-414c414b67f6/)
- [Stanford Online — 10 tips for communicating technical ideas to non-technical people](https://online.stanford.edu/10-tips-communicating-technical-ideas-non-technical-people)
- [Technical Leaders — Technical vs non-technical audiences](https://www.technical-leaders.com/post/technical-vs-non-technical-audiences-communication-strategies)
- [explainability.dev — Using analogies to explain technical concepts](https://explainability.dev/article/How_to_Use_Analogies_to_Explain_Technical_Concepts_to_NonTechnical_Audiences.html)
- [clickhelp — Metaphor in technical writing](https://clickhelp.com/clickhelp-technical-writing-blog/metaphor-in-technical-writing/)
- [Grammarly — How to avoid AI detection (write more human)](https://www.grammarly.com/blog/ai/how-to-avoid-ai-detection/)

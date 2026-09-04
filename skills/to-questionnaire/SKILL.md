---
name: to-questionnaire
description: Turn a decision you cannot settle alone into a Markdown discovery questionnaire for one named person to fill in async (or walk through in a meeting). User-invoked only - type /to-questionnaire when a follow-up is really a list of questions for someone else.
disable-model-invocation: true
---

# /to-questionnaire

Turn something the user cannot answer alone into a **questionnaire**: a
Markdown document they hand to one person to fill in async, or fill out
together over a meeting. The recipient holds knowledge the user lacks; the
questionnaire pulls it out of them.

Adapted from `to-questionnaire` in [mattpocock/skills](https://github.com/mattpocock/skills)
(MIT, see `NOTICE.md` next to this file). Output is a file in the repo, never
a chat message: the user asked for this document explicitly, and sending it
is their act. The skill itself writes nothing but that one file.

## Usage

```
/to-questionnaire                       # from the open questions in the conversation
/to-questionnaire <follow-up id>        # from an entry in your follow-ups registry
/to-questionnaire "<topic>" --to "<role/name>"
```

## Grill the send, not the subject

Interview the user only about the _send_, which they can always answer. Never
interview them about the subject - that is what the recipient is for.

1. **Who is it going to?** One exchange: the recipient's role, expertise, and
   relationship to the user (another PO, a team lead, a backend owner, the
   owner of a design task, compliance). This fixes the tone and how much
   context the document must carry. Skip the exchange if the user named the
   recipient or the follow-up entry already says who you wait on. Done when
   you know what the recipient knows that the user does not.
2. **What do you need back?** One exchange: the specific decisions or facts
   the user must walk away able to act on. Pull candidates from the
   conversation and from your follow-ups registry entries naming that person,
   and let the user prune. Done when you have a concrete list.
3. **Write the questionnaire.** Draft questions aimed at the gap from steps
   1-2, using the template below. Facts you can look up yourself (repo,
   knowledge base, tracker, code) are NOT questions - look them up and put
   them in Context, each with its source and date, because the recipient is
   often the only person who can tell you a repo fact is stale. Write to
   `docs/planning/questionnaire-<recipient-slug>-<topic-slug>-<YYYY-MM-DD>.md`
   (or wherever your project routes planning docs) and report the path. Done
   when the file exists and every item from step 2 is covered by exactly one
   question.

Constraints on the text: your team's process vocabulary only; ASCII if the
document will be pasted into a tracker or wiki; every figure carries its
source and date, and a figure without one is removed rather than kept; no
PII beyond the recipient's name and role - the file is git-tracked. If your
project path-scopes a scope checklist to planning docs, state market,
account-type and platform scope in Context or ask for them.

## Document structure

Frame it as a **discovery questionnaire**: the user lacks context, the
recipient holds it. Most-important-first, since async means you may get only
one pass. Group under `##` headings by theme once there are more than a
handful of questions.

<questionnaire-template>

# <Questionnaire title>

**Purpose:** why this questionnaire exists and the decision riding on it.

**From:** <the user>, **To:** <the recipient>, **How your answers will be used:** <where they go - ticket, ADR, roadmap decision>

## Context

One paragraph orienting a recipient who was not in the user's head. Enough to
answer well, not a page. Link the ticket / doc the decision lives in. Every
fact here names its source and date; close with: "Correct anything here that
is out of date - that is as useful as any answer below."

## How to answer

Deadline and rough effort. Partial answers and "I don't know" are useful: flag
anything you are unsure of rather than skipping it.

## <Theme heading>

One `##` section per theme. Under each, its questions, most-important-first.
Every question is one idea, never compound, with an answer stub directly
beneath, and a one-line _why this matters_ only where the question could be
misread or invite a throwaway answer.

<question-example>
### Which account types will see the new screen at launch?

_Why this matters: business accounts have a different visibility gate and would double the QA matrix._

>
</question-example>

## Anything else?

A closing catch-all: anything we did not ask that we should know?

</questionnaire-template>

## After writing

Propose (do not apply) one follow-up entry for the recipient so the wait is
tracked and the ping is never sent twice - whatever shape your registry
takes, with the questionnaire path as the source. If an entry for this wait
already exists, say so and propose nothing. The registry is never edited by
hand.

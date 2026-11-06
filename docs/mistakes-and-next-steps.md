# Mistakes, next steps, mood and time, spot the mistake

How SYNiq turns mistakes into the way into a topic and always shows the learner the next step. Code: `backend/app/engine/patterns.py` (pure rules), `backend/app/learning.py` (database glue), `frontend/app/learn/page.tsx`.

## Mistake patterns

- A **sighting** is a wrong answer that matches a known mistake: a misconception written with the question (`misconceptions:` in the packs) or a slip spotted in a sum (counting slip, tens slip, added instead of multiplied and so on).
- A mistake made **twice or more**, in any topic, is a **pattern**. It counts as **fixed** once the learner meets the same trap again and gets it right 3 times after the last time they fell into it. Falling in again reopens it.
- While a pattern is open, practice picks questions that carry that trap first (within one level of the target difficulty), so the mistake gets fixed instead of avoided. The question shows "Careful: this one has a trap you've met before" and never the answer.
- When the learner falls into an open pattern again, the response says so kindly ("You have met this trap before. Noticing it is the first step to beating it.").
- The learner sees **Mistakes I'm fixing** in My space; parents see it per child; teachers see **Mistakes that keep coming back** for the class, most common first, with who is still working on each. Words only: no counts or scores are shown to children.

## Mistakes explained the learner's way

The response to a wrong answer (`count_it_out` picture, `step_by_step`, `real_life` story, `try_similar`) used to follow a fixed order. Now:

1. SYNiq records whether the next answer on that topic was right after each kind of response, and reorders the list by what has helped this learner (needs 2 answers after a response before its record counts).
2. Until then, the way of explaining that helps them most (`engine/methods.py`) gets a nudge: pictures → `count_it_out`, step by step → `step_by_step`, real-life → `real_life`.
3. Each further wrong answer in a row still gets a different way. When the first response was chosen because of the learner, it says "This is the way that has helped you most after a mistake."

## The next step

Every answer returns `next_step`: either "N more right answers and you've got <topic>" (worked out from the mastery model) or "You've got <topic>! Next: <topic>". The Learn home shows **Your next step**: revision that is due, or the chapter to carry on with.

## Mood and time

The check-in before a chapter also asks "How much time do you have?" (5, 10, 20 minutes or no rush). If the learner says they feel low or frustrated, the first 3 questions are at the easiest level (logged as `gentle_start` in the decision). When their time is up, they see what they practised, the topics they secured and their next step, and can keep going. Mood is stored only if the parent allowed mood check-ins; the gentle start works either way.

## Spot the mistake

Every 5 answers, if the topic has written mistakes, a puzzle shows a friend's wrong answer and asks what it should be. Finding it earns a star (at most 20 a day) and the explanation of that mistake. Stars are a thank-you: they unlock nothing, are never compared between learners, and don't change the mastery estimate.

## Not built from the deck

- **IQ tracking**: left out on purpose, as decided earlier. SYNiq describes how a learner learns, never a score.
- **Voice answers**: browsers allow the microphone only on https, which the lab-computer setup doesn't have. Read-aloud works everywhere.

---
name: grill-me
license: MIT
description: Stress-test a plan, decision, or design through dependency-ordered questions and recommended answers. Use when the user asks to be grilled or wants assumptions challenged before implementation.
---

Stress-test consequential decisions until the material uncertainties are resolved. Map them as a **design tree**: each decision may unlock decisions that depend on it. Skip routine implementation choices and answers already established.

Work the tree in **rounds**. The **frontier** contains decisions whose prerequisites are already settled: questions you can ask without guessing at answers you haven't heard yet. In a normal round, ask at most three high-impact, independent questions from that frontier, with a recommended answer for each. Leave lower-impact questions for later; do not dump the whole tree into a questionnaire. Then wait for the user's answers before dependent questions.

Honor a requested pace: **short** focuses on the few decisions that could change the outcome; **thorough** explores more consequential branches and can use larger rounds when the user wants them. Do not add a mode-selection question unless the preference matters and is unclear. Plain numbered questions work on any host; a particular question UI is not required.

Format a round like so:

```
❓ **Q1** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>

---

❓ **Q2** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>
```

Word each question so "yes" accepts its recommended answer. Allow the user to accept all recommendations in the current round together, or answer by question number. Treat only an explicit answer as a decision; unanswered questions stay open or deferred. Accepting design recommendations does not authorize actions beyond the user's existing scope.

Each round the user answers reshapes the tree: settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.

Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, tools, etc.), look it up directly, or use a fresh-context subagent when available and permitted; don't ask the user for anything you could look up yourself. If an exploration is still running, treat it as an unsettled prerequisite and ask only independent questions until the result arrives. The _decisions_ are the user's: put each to them and wait.

Focus on decisions that could change scope, correctness, cost, or reversibility. Stop when material branches are resolved or explicitly deferred, the user asks to stop, or further questions would not change the next safe step. Summarize resolved decisions, deferred questions, their consequences, and the next step. For a longer discussion, keep that concise summary current in an existing decision/plan artifact or a session scratch note when useful; do not create documentation for a short exchange or overwrite authoritative decisions without agreement.

Implement only when requested; honor implementation authorization already given instead of asking for it again. Carry unresolved blockers into the next step rather than silently deciding them.

---
name: grill-me
license: MIT
description: Stress-test a plan, decision, or design through dependency-ordered questions and recommended answers. Use when the user asks to be grilled or wants assumptions challenged before implementation.
---

Interview the user relentlessly until you reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Ask the whole frontier in one round: number each question and give your recommended answer. Then wait for the user's answers before the next round.

Format a round like so:

```
❓ **Q1** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>

---

❓ **Q2** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>
```

Word each question so "yes" accepts your recommended answer.

Each round the user answers reshapes the tree: settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.

Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, tools, etc.), look it up directly, or use a fresh-context subagent when available and permitted; don't ask the user for anything you could look up yourself. If an exploration is still running, treat it as an unsettled prerequisite and ask only independent questions until the result arrives. The _decisions_ are the user's: put each to them and wait.

Focus on decisions that could change scope, correctness, cost, or reversibility; skip trivia and already settled answers. Stop when material branches are resolved or the user asks to stop. Summarize decisions and remaining uncertainties. Implement only when requested; honor implementation authorization already given instead of asking for it again.

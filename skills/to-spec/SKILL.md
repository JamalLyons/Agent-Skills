---
name: to-spec
license: MIT
description: "Turn an existing conversation into an implementation spec without another interview. Publish to the project issue tracker when requested, or save a local draft."
---

This skill takes the current conversation context and codebase understanding and produces a spec. Do NOT interview the user; just synthesize what you already know.

Discover the issue tracker and labels from repository guidance, remotes, and available integrations. Draft the spec locally when publishing is not requested or the destination is unknown. Publish only when the user has authorized it and a destination is established; use existing labels when appropriate rather than requiring a particular label or setup skill.

## Process

1. Explore the repo to understand the current state of the codebase, if you haven't already. Use the project's domain glossary vocabulary throughout the spec, and respect any ADRs in the area you're touching.

2. Extract checkable acceptance criteria from the agreed scope. Preserve existing requirement IDs and meanings; otherwise assign stable IDs such as `C1`, `C2`. Describe an observable result and its relevant preconditions, including failure or edge cases only when agreed or established by the existing contract. Do not infer new requirements merely to make coverage look complete. Separate proposed criteria and unresolved blockers from accepted criteria.

Read [acceptance and evidence](references/acceptance-evidence.md) for the compact contract used when requirements pass into tasks, implementation, verification, and review. Keep the source ID when splitting a criterion across tasks; record an explicit mapping if a destination uses different IDs.

3. Sketch out the seams at which you're going to test the feature. Prefer existing seams and the highest useful interface that can observe the agreed behavior. If a new seam materially affects scope, record it as a proposal rather than an accepted decision.

Use test seams already agreed in the conversation. Record a proposed seam as an open question if it materially affects scope; do not turn synthesis into another interview.

4. Write the spec using the template below, matching the project's spec location and conventions. If authorized, publish it to the established issue tracker and return the issue link. Otherwise return the draft path. Distinguish agreed decisions from proposals and unresolved questions; do not invent requirements to fill the template. Omit inapplicable sections instead of filling them with speculation.

<spec-template>

## Problem Statement

The problem that the user is facing, from the user's perspective.

## Solution

The solution to the problem, from the user's perspective.

## User Stories

A numbered list of user stories covering the agreed scope. Each user story should be in the format of:

1. As an <actor>, I want a <feature>, so that <benefit>

<user-story-example>
1. As a mobile bank customer, I want to see balance on my accounts, so that I can make better informed decisions about my spending
</user-story-example>

Cover the feature's agreed behavior and meaningful edge cases without adding speculative scope.

## Acceptance Criteria

List the agreed, observable conditions for completion, with stable IDs and a source reference when their origin would otherwise be ambiguous. Reuse IDs already present in the conversation, spec, or issue; do not renumber them when tasks are added or reordered.

For each criterion, record the relevant input or precondition and expected outcome. Include agreed failure behavior, compatibility, rollout, or migration conditions only when they belong to the scope. Link the planned verification in Testing Decisions by ID. A verification plan is not a passing result.

If the available context does not establish checkable criteria, say what remains unresolved below; do not manufacture acceptance to fill this section.

## Implementation Decisions

A list of implementation decisions that were made. This can include:

- The modules that will be built/modified
- The interfaces of those modules that will be modified
- Technical clarifications from the developer
- Architectural decisions
- Schema changes
- API contracts
- Specific interactions

Do NOT include specific file paths or code snippets. They may end up being outdated very quickly.

Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it within the relevant decision and note briefly that it came from a prototype. Trim to the decision-rich parts, not a working demo, just the important bits.

## Testing Decisions

A list of testing decisions that were made. Include:

- A description of what makes a good test (only test external behavior, not implementation details)
- Which modules will be tested
- Prior art for the tests (i.e. similar types of tests in the codebase)
- Which acceptance IDs each planned check covers and what it cannot establish; distinguish checks to run from evidence already observed

## Proposals and Unresolved Questions

Keep suggested behavior, proposed acceptance criteria, and unresolved decisions separate from agreed requirements. For each material blocker, state the affected acceptance IDs (if any) and what decision or evidence is needed. Do not resolve missing product decisions by guessing, and do not start another interview. A blocked criterion retains its ID and remains incomplete.

## Out of Scope

A description of the things that are out of scope for this spec.

## Further Notes

Any further notes about the feature.

</spec-template>

---
name: retrospective-process-hardening
description: Use when a completed feature, bugfix, or refactor needs lessons learned distilled into reusable workflow rules, SOP updates, or skill changes.
---

# Retrospective Process Hardening

## Overview

Convert one completed delivery cycle into durable process improvements.

This skill exists to prevent two common failures:
- overfitting lessons to the domain of the just-finished change
- dumping every observation into SOPs instead of classifying what should become a rule, a skill update, a new skill, or nothing

**Baseline failure this skill is designed to catch:** after a complex change, the first draft of "lessons learned" often mirrors the current module or protocol instead of extracting reusable engineering practice.

## When to Use

Use this skill only when a human explicitly asks to:
- summarize lessons learned
- update workflow norms or SOPs based on completed work
- decide whether to create or update a skill from recent delivery experience

Do not use this skill:
- before implementation is materially complete
- for ordinary progress updates
- for domain design writeups that are not intended to become process guidance

## Core Rule

Retrospective output must be classified before it is codified.

Every candidate lesson must end in exactly one bucket:
1. `update-sop`
2. `update-existing-skill`
3. `create-new-skill`
4. `do-not-codify`

If a lesson cannot survive that classification, it is not ready to become process guidance.

## Process

### 1. Gather evidence

Build the retrospective from concrete evidence, not impression:
- change scope
- review findings
- rework or rollback points
- design corrections
- verification gaps
- documentation drift

Prefer repository evidence over memory:
- diff scope
- review comments
- docs/spec updates
- tests added or corrected

### 2. Extract candidate lessons

Write short candidate lessons in neutral language.

<Good>
- Structural changes need an explicit scope freeze before implementation.
- Public API unions should be normalized at the boundary instead of propagating inward.
</Good>

<Bad>
- Rich-media messages should not use `Task.description`.
- Approval payloads should be `select`.
</Bad>

The bad examples may be true for the specific change, but they are domain decisions, not reusable process rules.

### 3. Abstract before classifying

For each candidate lesson, ask:
- Is this still true outside the current domain?
- Does it guide future decisions rather than restate this implementation?
- Would this help on unrelated features?

If the answer is no, move it to `do-not-codify`.

## Classification rules

### `update-sop`

Use when the lesson is:
- generally applicable across feature work
- a mandatory workflow or governance rule
- something contributors should follow even without special prompting

Typical examples:
- scope freeze before structural change
- entry-inventory requirement before schema/protocol changes
- global sweep before declaring completion

### `update-existing-skill`

Use when the lesson:
- fits the responsibility of an existing skill
- improves an existing skill's trigger, guardrails, or output contract
- does not justify a standalone reusable workflow

Typical examples:
- refine `development-workflow` to mention a closing checkpoint
- strengthen `documentation-management` archive rules

### `create-new-skill`

Use when the lesson describes a reusable decision workflow that:
- is too detailed for SOP prose
- benefits from classification steps, examples, or anti-patterns
- should only run under explicit triggering conditions

Typical examples:
- a dedicated retrospective-to-process-hardening workflow
- a cross-cutting debugging discipline with repeatable pressure cases

### `do-not-codify`

Use when the lesson is:
- domain-specific
- a one-off repository cleanup detail
- already implied by an existing rule
- better enforced by code or CI than by prose

## Output contract

Produce four sections in order:

1. `Evidence`
- concise list of the specific completed work and review signals used

2. `Candidate Lessons`
- short neutral statements

3. `Classification`
- one line per lesson with exactly one bucket:
  - `update-sop`
  - `update-existing-skill`
  - `create-new-skill`
  - `do-not-codify`

4. `Codified Changes`
- the actual file updates required
- keep only the highest-value general rules

## Codification guardrails

- SOPs should contain triggers, mandatory gates, and durable process rules
- skills should contain the detailed method and classification logic
- do not duplicate the same detailed workflow in both places
- if the detailed reasoning belongs in a skill, keep the SOP reference short
- prefer changing an existing skill before creating a new one

## Common mistakes

### Turning implementation details into workflow law

If the lesson names a current module, payload, adapter, or schema, it is probably not abstract enough yet.

### Codifying everything

A good retrospective is selective. Most observations should never become process rules.

### Using the skill without explicit human request

This skill is opt-in. It should not run automatically after every change.

### Updating SOP first and figuring out the method later

If the lesson needs a decision workflow, create or update the skill first, then reference it from SOP.

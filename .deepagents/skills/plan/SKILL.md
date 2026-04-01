---
name: plan
description: Decompose complex goals into ordered, actionable sub-tasks before executing
---

# Plan Skill

## When to Use
Call the `plan` tool whenever the user's goal requires:
- More than two sequential steps
- Coordination across multiple tools (search + think + report)
- A research or analysis workflow
- Anything that could fail midway and needs checkpoints

## How to Plan

1. **Understand the goal** — identify what success looks like
2. **Break it down** — list all sub-tasks needed to achieve it
3. **Order them** — determine dependencies between tasks
4. **Assign tools** — note which skill/tool handles each step
5. **Set checkpoints** — identify where to validate progress

## Output Format

```
## Plan: <goal title>

**Goal:** <one-sentence description of what we are achieving>

### Steps
1. [ ] <action> — using: <tool/skill>
2. [ ] <action> — using: <tool/skill>
3. [ ] <action> — using: <tool/skill>
...

**Success criteria:** <how we know we are done>
```

## Rules
- Always plan before starting multi-step tasks
- Keep each step atomic (one action per step)
- Re-plan if you discover the original plan is wrong
- Mark steps complete as you execute them

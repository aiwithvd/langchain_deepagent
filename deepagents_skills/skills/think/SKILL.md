---
name: think
description: Use structured chain-of-thought reasoning before acting on complex or ambiguous problems
---

# Think Skill

## When to Use
Call the `think` tool whenever you face:
- A question with multiple valid interpretations
- A task requiring trade-off analysis
- Any situation where rushing to an answer could cause errors
- Before deciding which other tool to use

## How to Think

Structure your reasoning as follows:

1. **Restate** the question or problem in your own words
2. **Identify** what you already know vs. what you need to find out
3. **Reason** step-by-step through the problem
4. **Consider** alternative approaches or edge cases
5. **Conclude** with a clear answer or next action

## Output Format

```
[Question]
<restate the question>

[Reasoning]
Step 1: ...
Step 2: ...
Step 3: ...

[Conclusion]
<clear answer or decided next action>
```

## Rules
- Never skip the thinking step for complex tasks
- If your conclusion changes mid-reasoning, note why
- Keep reasoning concise but complete

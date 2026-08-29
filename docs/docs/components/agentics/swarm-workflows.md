---
title: Swarm Workflows — Assembly Line & Think Tank
slug: /components/agentics/swarm-workflows
---

# Swarm Workflows — Assembly Line & Think Tank

Orchestrate a team of agents with two workflow patterns built into `lfx.agentics`:

- **Assembly Line** (`SequentialWorkflowComponent`) — work passes from one teammate to the next. Perfect for **Research → Write → Review**.
- **Think Tank** (`ConcurrentWorkflowComponent`) — everyone works on the same task at the same time, then you compare the combined answers. Great for brainstorming or voting.

Both take a list of **Team Members** (any `Agent` component) and one shared instruction, then return a single **Final Result** message.

## Which one do I use?

| Need | Pattern | How it runs |
|------|---------|-------------|
| A pipeline that builds on itself (research, then write, then edit) | **Assembly Line** | One agent at a time; the output of step 1 becomes the input of step 2 |
| Many perspectives on one question (brainstorm, taglines, vote) | **Think Tank** | All agents at once on the same task; answers joined for comparison |

Assembly Line chains results (`final_result`), so ordering your team matters — put the Researcher first, Writer second, Reviewer last. Think Tank fan-outs in parallel, so ordering does not affect each answer; you compare them afterward.

## Inputs

Both components expose the same inputs:

| Name | Type | Description |
|------|------|-------------|
| Your Team (drag Team Members here, in order) | `HandleInput` (`is_list=True`) | Drag 1+ (Assembly Line) or 2+ (Think Tank) Team Members. `input_types=["Agent"]`, required. |
| What should the team do? | `MessageTextInput` | One clear instruction for the whole team. Required. |
| Max loops | `IntInput`, `advanced=True` | How many times to run. Default `1`. Hidden on the canvas until "Show advanced" is toggled. |

## Output

| Name | Display | Method |
|------|---------|--------|
| `final_result` | Final Result | `build_workflow` |

The outputs of every agent run are normalized to `Message` and joined with `\n---\n`, so the final result reads as a clearly separated list of each teammate's contribution.

## How agent output is normalized

Both workflows use the same `_to_message` helper to normalize whatever an agent returns into a `Message`:

```python
def _to_message(value):
    # Message -> pass through
    if isinstance(value, Message):
        return value
    # dict -> json.dumps (preserves structure, avoids str(dict) single-quotes)
    if isinstance(value, dict):
        return Message(text=json.dumps(value, ensure_ascii=False, indent=2))
    # list -> json.dumps if items are dicts, else str join
    if isinstance(value, list):
        try:
            return Message(text=json.dumps(value, ensure_ascii=False, indent=2))
        except (TypeError, ValueError):
            return Message(text="\n".join(str(v) for v in value))
    # anything else -> string
    return Message(text=str(value))
```

`Message` output passes through untouched; `dict` and structured `list` outputs are pretty-printed as JSON (not single-quoted Python `str()`), so keys and nesting survive; anything else is stringified.

## Example flows

### Assembly Line — a 2-agent research chain

1. Drag **2 Team Members** into **Your Team** in order: Researcher, then Writer.
2. Set **What should the team do?** to something like:
   `Research the top 3 AI hiring trends and write a short LinkedIn post with sources.`
3. Run.

The Researcher produces a summary, which chains into the Writer on loop 2. Output is both results joined by `---`.

### Think Tank — a 3-agent brainstorm fan-out

1. Drag **3 Team Members** into **Your Team**.
2. Set **What should the team do?** to:
   `Brainstorm 3 different taglines for a local-first AI team product.`
3. Run.

All 3 agents run at once on the same task (via a `ThreadPoolExecutor`), then the 3 answers are joined by `---` for comparison.

## Choosing a model

Team Members are standard `Agent` components, so they work with any configured model — including free options such as **Big Pickle free**. No paid provider or API key is required to try these workflows.

## Registration

The native lfx components are registered under the `lfx.agentics` namespace:

- `lfx.components.agentics.SequentialWorkflowComponent` (display name **Assembly Line**, name `SequentialWorkflow`)
- `lfx.components.agentics.ConcurrentWorkflowComponent` (display name **Think Tank**, name `ConcurrentWorkflow`)

There is also a **bundle** variant (`lfx-swarms`, `lfx_swarms.components.swarms`) that uses the same display names but wraps the external `swarms` Python package (`uv pip install swarms`) and is registered as `SwarmsSequentialWorkflow` / `SwarmsConcurrentWorkflow`. The lfx-native `agentics` components replicate the pattern standalone — no external dependency, and they run against your configured Team Members regardless of provider.

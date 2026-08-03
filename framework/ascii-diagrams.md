# Portable ASCII Diagrams

ASCII is the baseline diagram presentation for Alatyr discussions. It works in
chat, terminals, logs, code review, and plain Markdown without client-specific
rendering or external tools.

This document defines presentation syntax, not project facts. Diagram content
still comes from target source-of-truth owners and remains subject to the
diagram status, approval, security, and revision rules.

## Output Contract

Every discussion diagram should include one fenced `text` block that:

- uses only printable 7-bit ASCII characters, spaces, and line feeds
- contains no tabs, ANSI color codes, or Unicode box-drawing characters
- prefers at most 88 columns and never exceeds 100 columns
- uses a consistent left-to-right or top-to-bottom reading direction
- keeps node labels concise and moves explanations below the diagram
- includes a legend when two or more connector meanings are used
- avoids crossing connectors; split one dense view into focused views instead
- preserves meaning when copied without Markdown styling

Use multiple diagrams when one view would contain more than seven primary
nodes, more than three connector kinds, mixed architecture levels, or labels
that cannot fit within the width limit.

## Building Blocks

Use stable, simple forms:

```text
[Component]       ordinary node or state
(Actor)           person or external actor
<External>        external system or boundary
+------------+    multi-line node or boundary
| Component  |
+------------+

-->               control, call, or dependency direction
==>               data, event, or message movement
<->               explicitly bidirectional relationship
..>               asynchronous, optional, or deferred path
```

Label a connector next to the line when its meaning is not obvious. Do not use
spacing alone to imply ownership, direction, or containment.

## Architecture And Flow

Prefer top-to-bottom layout for long labels and left-to-right layout for short
pipelines.

```text
(User)
  |
  | request
  v
+-------------+      query      +------------+
| API         | --------------> | Data Store |
+-------------+                 +------------+
  |
  | publish
  v
<Event Bus>
```

Show a boundary with an outer ASCII box only when containment is part of the
fact being explained. Otherwise use a short boundary label to avoid visual
noise.

## Sequence

Keep participants in fixed columns. Time moves downward.

```text
User          API          Store
 |             |             |
 | request     |             |
 |------------>|             |
 |             | query       |
 |             |------------>|
 |             | result      |
 |             |<------------|
 | response    |             |
 |<------------|             |
```

For retries, failures, or branches, show only the relevant branch and state the
omitted path below the diagram.

## Hierarchy And Ownership

Use `+-`, a backtick followed by `-`, and `|` consistently. Put the canonical
owner above derived surfaces.

```text
Project
+- API
|  +- Authentication
|  `- Orders
`- Worker
   `- Event handler
```

## State And Relationship Graphs

Use one line for a small state path and a vertical layout for branches.

```text
[Draft] --approve--> [Approved] --publish--> [Live]
   |
   `--reject-----> [Rejected]
```

When a graph is not a simple path, assign short stable node IDs and list any
edges that cannot be drawn without crossings below the main view.

## Quantitative Graphs

ASCII charts must use observed or explicitly supplied values. Always name the
metric, unit, direction of improvement, and scale. Do not imply precision that
the evidence does not support.

Use proportional bars for category comparison:

```text
Build time (seconds, lower is better; 1 # = 5 seconds)

before | #################### 100
after  | ########              40
```

Use a bounded point plot only when both axes and intervals are explicit:

```text
Errors
  8 | *
  6 |   *
  4 |      *
  2 |          *
  0 +----------------
      1  2  3  4  5   Day
```

If exact scaling would make the chart misleading or unreadable, show a compact
value list instead of decorative bars.

## Presentation Notes

After the ASCII block, report:

- diagram title, type, status, ID, and draft revision
- connector legend when needed
- assumptions, unresolved facts, and omitted detail
- fact owners and revision evidence
- whether a native inline view or artifact was also provided
- validation and stale-view risk

The ASCII view is presentation evidence, not automatically editable source or
project source of truth. A target may persist it as source only when the target
diagram policy explicitly owns ASCII diagrams.

## Rejection Criteria

Reject or revise an ASCII diagram that:

- exceeds 100 columns or depends on horizontal scrolling for its main path
- uses non-ASCII symbols, tabs, color, or font-specific alignment
- has crossing or unlabeled ambiguous connectors
- mixes unrelated architecture levels or quantitative scales
- truncates identifiers so different project facts look identical
- invents values, relationships, states, owners, or boundaries
- claims an ASCII block was natively rendered or generated by target tooling
- presents a draft view as accepted project truth

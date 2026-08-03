# ASCII Diagram Presentation

Use this target template for the mandatory portable view of a discussion
diagram. Replace placeholders from target evidence before returning a result.

## Layout

- Diagram kind: `{ARCHITECTURE_FLOW_SEQUENCE_HIERARCHY_STATE_GRAPH_OR_CHART}`
- Reading direction: `{LEFT_TO_RIGHT_OR_TOP_TO_BOTTOM}`
- Preferred width: `88`
- Hard maximum width: `100`
- Character set: `printable 7-bit ASCII plus line feeds`
- Connector meanings: `{CONNECTOR_LEGEND_OR_SINGLE_OBVIOUS_CONNECTOR}`

```text
{ASCII_DIAGRAM}
```

## Readability Check

- Pure ASCII, no tabs or ANSI codes: `{PASS_OR_REVISE}`
- Longest line at most 100 columns: `{PASS_OR_REVISE}`
- Direction and connector labels are unambiguous: `{PASS_OR_REVISE}`
- No crossing connectors: `{PASS_OR_SPLIT_INTO_FOCUSED_VIEWS}`
- Values, units, and scale are explicit for charts: `{PASS_NOT_APPLICABLE_OR_REVISE}`
- Stable target names are preserved: `{PASS_OR_REVISE}`

## Evidence

- Fact owners: `{FACT_IDS_AND_CANONICAL_OWNERS_OR_MISSING}`
- Assumptions: `{ASSUMPTIONS_OR_NONE}`
- Unresolved facts: `{UNRESOLVED_FACTS_OR_NONE}`
- Omitted detail: `{OMITTED_DETAIL_OR_NONE}`
- Validation: `{TARGET_REVIEW_OR_NOT_RUN}`

This ASCII view is presentation evidence. It is not accepted project source of
truth unless the target source-of-truth registry explicitly assigns ownership.

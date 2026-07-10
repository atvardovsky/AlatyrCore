---
alatyr_doc:
  id: framework.bridge-capability-matrix
  type: framework-rule-owner
  owns_rules:
    - ALATYR-BRIDGE-001
  depends_on:
    - ALATYR-ADAPTER-001
  applies_to:
    - ai-infrastructure
    - framework-upgrade
---
# Bridge Capability Matrix

A bridge capability matrix records how each supported assistant surface loads
instructions and what limitations apply.

Thin bridge files are still required, but thinness alone does not prove
equivalent behavior across assistants. The matrix makes differences explicit.

## Matrix Contract

For each supported assistant, record:

- assistant surface ID and display label
- bridge file path
- auto-load behavior
- instruction priority or known precedence
- supported Markdown, prompt, rule, or skill surfaces
- tool permission model
- whether operation help aliases are routed
- whether AI infrastructure inventory and adaptation aliases are routed
- known limitations
- conformance check or manual review

The target adapter owns exact assistant behavior. The framework only requires
the behavior to be discoverable and kept consistent with canonical target
files.

## Baseline Template Surfaces

The target bridge capability matrix template should include baseline entries
for the assistant surfaces tracked by the source conformance surface list:

- generic
- agents
- codex
- claude
- gemini
- github-copilot
- cursor
- devin-cascade
- windsurf

Targets may mark a surface unsupported or not applicable, but a missing row
should be treated as a bridge capability gap when that assistant is expected
to work.

## Conformance Expectations

Each bridge should:

- point to the canonical root entry point
- point to operation help and operation routing
- route `alatyr-ai-inventory`, `alatyr-adaptation`, and `alatyr-add-ai` when
  those aliases are supported by the target
- avoid duplicating full framework, project, or adapter policy
- avoid becoming a source of truth for project facts
- state assistant-specific limitations only when target evidence supports
  them

If an assistant surface cannot auto-load a bridge, record the manual loading
step or unsupported status.

## Upgrade Use

During framework update or adapter recheck:

1. Read the matrix.
2. Check every listed bridge file still exists.
3. Check each bridge points to the same canonical entry points.
4. Check operation aliases still route to the canonical flows.
5. Report bridge-specific limitations and residual risk.

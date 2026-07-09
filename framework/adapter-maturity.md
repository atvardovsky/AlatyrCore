# AI Framework Adapter Maturity

This file helps an assistant judge whether a project adapter is ready to
support reliable AI work.

It is not a scorecard for project quality. It is a readiness model for the
framework.

## Levels

### Incomplete

The adapter is incomplete when it lacks one or more of:

- canonical assistant entry point
- project, framework, and repository adapter contour separation
- project source-of-truth docs
- validation plan or explicit unresolved validation
- final evidence expectations

Assistant behavior is high-risk. The assistant should avoid broad changes and
report missing adapter facts.

### Minimal

The adapter is minimal when it defines:

- entry point and contours
- basic project facts
- basic validation commands or manual checks
- documentation-sync rule
- basic source-of-truth or blueprint-equivalent owner
- bridge files for the assistants in use

The assistant can handle small tasks, but should report missing tests,
diagrams, security, maturity, or checker coverage when relevant.

### Usable

The adapter is usable when it also defines:

- architecture/source-of-truth docs
- use cases or equivalent workflows when applicable
- test strategy and validation gates
- security and live-service boundaries
- diagram policy when diagrams exist
- approval triggers
- logical integrity review path
- blueprint-driven change or equivalent product-change workflow
- installed-operation request and adapter-recheck path for post-install work
- operation help or routing path for ambiguous requests
- skill adaptation and provenance rules when skills or third-party assistant
  infrastructure exist

The assistant can perform ordinary implementation and documentation tasks with
focused validation.

### Mature

The adapter is mature when it also defines:

- context packs or navigation aids for broad work
- module ownership, data dictionary, glossary, and decision log
- deterministic consistency checks for maintainable invariants
- generated-artifact drift checks or manual-review policy
- framework upgrade/lifecycle notes
- post-install operation, blueprint repair, and framework-update recheck notes
- maintained help menu and post-install/update chat-message templates
- skill/wrapper compatibility notes for supported assistants
- improvement advice path for reducing future friction

The assistant can handle larger tasks with phased context loading and stronger
evidence.

## Adapter Audit Questions

Ask:

- Can an assistant find the mandatory context without user explanation?
- Are framework rules, project facts, and adapter rules separated?
- Are local commands and generated artifacts clearly adapter-owned?
- Are tests and validation discoverable?
- Are security and live external side effects bounded?
- Are approval-required changes named?
- Are docs, diagrams, prompts, skills, bridges, and checker rules synchronized?
- Can the adapter be rechecked after installation or framework update without
  relying on user memory?
- Can an assistant show useful Alatyr help when the user's requested operation
  is unclear?
- Are imported or custom skills adapted from target evidence with provenance
  and safety review?
- Is there a way to report missing or unresolved adapter facts?

## Rejection Criteria

Reject maturity claims that:

- ignore missing validation or source-of-truth docs
- treat scripts as a substitute for assistant reasoning
- count bridge files as canonical policy
- copy another project's adapter facts instead of writing target facts
- hide unknowns instead of reporting residual risk

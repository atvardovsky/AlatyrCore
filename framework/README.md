# Alatyr Core Framework

This directory defines the portable Alatyr Core assistant framework.

It is the reusable source that an assistant can adapt into a target project.
It is separate from any target project's product facts and from any target
repository's local AI adapter.

The framework exists to make assistants work predictably on a project by
forcing context discovery, ownership separation, approval gates, documentation
sync, logical integrity review, and final evidence.

## Owns

- framework contour and portability rules
- guarantees the framework provides to a project
- project-adapter contract
- context-discovery and source-of-truth decision rules
- change-risk classification and approval trigger model
- first-class logical integrity review
- blueprint-driven product-change workflow
- portable security, safety, and live-service reasoning rules
- diagram reasoning and source/visual synchronization guidance
- skill, prompt, and third-party assistant infrastructure adaptation guidance
- reusable assistant workflow categories
- reusable approval, documentation-sync, logical integrity, and evidence
  concepts
- stack-aware testing analysis guidance
- supported-assistant bridge pattern
- adapter maturity and framework lifecycle guidance

## Does Not Own

- target project business logic, data model, architecture, diagrams, or
  runtime flows
- local commands, CI job names, generated files, hooks, or checker scripts
- project-specific skills, prompts, gates, or bridge wording
- target project facts during installation into another repository

Those belong to a project contour or repository adapter.

## Files

- `.ai/framework/README.md`: index for portable framework core files and
  ownership.
- `.ai/framework/contour.md`: boundary for portable framework core.
- `.ai/framework/guarantees.md`: what the framework guarantees and what it
  cannot guarantee without a project adapter.
- `.ai/framework/project-adapter-contract.md`: what a project must provide so
  the framework can work on that project.
- `.ai/framework/portability.md`: rules for separating framework core from
  repository adapter details.
- `.ai/framework/testing-guidance.md`: portable reasoning guidance for choosing
  test levels and structure from the target stack and risk profile.
- `.ai/framework/context-discovery.md`: portable process for finding required
  context, owners, missing facts, and source-of-truth conflicts.
- `.ai/framework/change-risk-model.md`: portable risk classes used to decide
  approvals, tests, docs, diagrams, and final evidence.
- `.ai/framework/logical-integrity.md`: portable semantic/logical review for
  changed facts, source-of-truth decisions, repair sets, and evidence.
- `.ai/framework/blueprint-driven-change.md`: portable product-change workflow
  from intent through source-of-truth, implementation, sync, and evidence.
- `.ai/framework/security-safety-guidance.md`: portable security and safety
  expectations for secrets, live services, dependencies, and destructive work.
- `.ai/framework/diagram-guidance.md`: portable diagram reasoning and
  source/visual split rules.
- `.ai/framework/skill-adaptation.md`: portable guidance for adapting skills,
  prompts, wrappers, and third-party assistant infrastructure.
- `.ai/framework/adapter-maturity.md`: readiness model for judging whether a
  project adapter can support reliable assistant work.
- `.ai/framework/lifecycle.md`: framework versioning, upgrade, deprecation,
  and migration guidance.

## Target Repository Adapter

In a target repository, `.ai/assistant` is normally the repository adapter. It
applies Alatyr Core to that project through local flows, gates, prompts,
skills, bridge files, consistency manifests, and local validation commands or
manual checks.

Portable framework files may point to adapter concepts, but must not require
Alatyr Core's source repository commands or any source project facts.

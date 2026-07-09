# AI Framework Testing Guidance

This file explains how an assistant should reason about tests when applying the
framework to any project. It is portable guidance, not a source of concrete
commands for this repository or any target repository.

The goal is not to force one testing pyramid on every project. The goal is to
make the assistant analyze the target stack, risk, architecture, and existing
test surface before proposing or changing tests.

## Inputs To Inspect

Before advising on test structure or writing tests, inspect the target project
adapter for:

- language, framework, package manager, and build files
- existing test directories, naming conventions, fixtures, and helpers
- CI jobs, local validation commands, static analysis, and coverage policy
- architecture boundaries, module ownership, and dependency direction
- business-critical rules, external side effects, persistence, queues, UI, or
  API boundaries
- existing mocks, fakes, containers, factories, test data builders, and
  contract fixtures
- known constraints such as no live external calls, deterministic clocks,
  secrets handling, or transaction isolation

If the target project does not define test commands or conventions, report that
as a missing project-adapter fact. Do not invent commands.

## Analytical Test Selection

Choose test levels by the changed behavior and risk:

- Pure business rules: favor fast unit tests around domain objects, value
  objects, pure functions, policies, and edge cases.
- Application orchestration: use application/service tests with fakes for
  ports, repositories, clocks, queues, and external clients.
- Persistence and migrations: use integration tests for mappings, constraints,
  transactions, indexes, query behavior, and repository contracts.
- External APIs: use contract tests with recorded or hand-written fixtures,
  schema validation, idempotency checks, retry behavior, and error cases. Do
  not call live services unless the project explicitly owns a separate live
  smoke-test policy.
- UI or user workflow: use component, interaction, accessibility, visual, or
  end-to-end tests according to the stack and risk. Avoid using broad end-to-end
  tests as the only proof for business rules.
- Async, queue, or event behavior: test message shape, handler idempotency,
  retry/failure transitions, and ordering assumptions with deterministic
  clocks and fakes.
- Security or permission behavior: test allowed and denied paths, secret
  redaction, authorization boundaries, input validation, and audit output.
- Cross-module contracts: test public interfaces, DTO/message schemas, and
  compatibility boundaries rather than private implementation details.

Prefer the smallest test level that proves the changed contract. Add broader
tests only when behavior crosses process, persistence, network, UI, or
integration boundaries.

## Stack-Aware Structure Advice

Adapt structure to the target stack instead of copying another project:

- service or backend projects often separate pure unit tests, application tests
  with fakes, framework/container tests, persistence tests, message/command
  tests, and external-client contract tests.
- web application projects often separate pure unit tests, component tests,
  API/route tests, browser interaction tests, accessibility checks, visual
  checks, and external-service contract tests.
- data or batch projects often separate transformation unit tests, fixture
  tests, pipeline tests, storage integration tests, and end-to-end replay or
  smoke tests.
- package or library projects often keep fast module/package tests close to
  source and place compatibility, integration, or external-boundary tests
  behind explicit adapter-defined gates.
- mobile or desktop projects often separate model tests, UI/component tests,
  platform integration tests, permission tests, and release smoke tests.

These examples are patterns to consider, not requirements. The project adapter
must name the actual test folders, tools, commands, and CI gates.

## Test Design Rules

Good assistant-generated tests should:

- assert observable behavior and contracts, not private implementation details
- cover happy path, negative path, boundary values, and important edge cases
- use clear fixtures or builders that make business meaning visible
- isolate external services with fakes, mocks, local emulators, or fixtures
- avoid sleeps, random data without seeds, real wall-clock assumptions, and
  network access unless the adapter explicitly allows them
- keep unit tests fast and deterministic
- prove error handling and idempotency for side-effecting code
- verify documentation-relevant behavior when docs, diagrams, or blueprints
  describe a rule, flow, state, relation, or external contract
- update or add adapter validation when a new test level becomes required

## Rejection Criteria

Reject or revise test proposals that:

- only test implementation details while leaving the business contract unproven
- replace focused lower-level tests with broad, brittle end-to-end tests
- hit live external services without an explicit project-owned live-test policy
- hide missing behavior by weakening assertions or deleting useful tests
- rely on sleeps, current time, random order, or shared mutable global state
- duplicate production algorithms in assertions instead of checking expected
  outcomes
- skip failure, boundary, permission, idempotency, or rollback cases for risky
  behavior
- add stack-specific tools or commands to framework core instead of the project
  adapter

## Adapter Responsibilities

Each project adapter must translate this guidance into concrete local facts:

- test levels used by the project
- test directory and naming conventions
- approved tools, libraries, fixtures, fakes, and helpers
- commands or CI jobs for each test level
- isolation rules for databases, queues, clocks, files, network, and secrets
- required tests for high-risk changes
- final evidence format for tests run, skipped, or intentionally not needed

When those facts are missing, the assistant should propose adapter
documentation or ask for direction instead of inventing project-specific
commands.

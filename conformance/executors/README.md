# Provider-Neutral Conformance Executors

This directory defines the execution lifecycle shared by conformance runners:
`prepare`, `invoke-or-manual-import`, `collect`, and `validate`.

The capability contract records available execution *mechanisms*, not proof
that a provider, model, account, or client version is currently available.
`codex-cli` is a native adapter for the Codex surface. Other supported
assistant surfaces remain manual-import or unverified until a captured run
contains reviewed evidence.

Static contracts and protocol expectations are source-repository fixtures.
They are not captured assistant runs, target validation, or evidence of an
accepted target adapter.

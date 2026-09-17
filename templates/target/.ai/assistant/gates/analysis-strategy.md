# Analysis Strategy Gate

Owner: `ALATYR-DECOMPOSITION-001`.

Use this gate for non-trivial work. Eligible small tasks use `direct-local`
without loading this file or the strategy catalog.

Before execution:

- select exactly one primary strategy from the target catalog
- load only the index and selected descriptor
- record evidence for the selection and a bounded problem model
- add `adversarial-review` for protected, security, destructive,
  public-contract, approval-sensitive, or similarly high-impact work
- keep Debug Mode separate and disabled unless explicitly activated
- assign each proof obligation to the primary or one bounded worker task
- keep global strategy selection, obligation waiver, acceptance, and final
  convergence with the primary assistant

Before completion:

- required obligations are passed with evidence or waived under explicit
  target-authorized policy
- required reviews passed with evidence
- failed, blocked, open, or unevidenced duties block completion
- invalidated assumptions and unresolved decisions remain explicit
- no private reasoning, hidden chain-of-thought, or raw scratchpad was stored
- reusable outcomes are classified, but promotion remains an explicit
  project-owned action

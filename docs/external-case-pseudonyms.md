# External Case Pseudonyms

Scope: AlatyrCore source work only. This applies the
[target-owned identity boundary](../framework/project-adapter-contract.md#target-owned-project-identity)
without renaming the current target project, dependencies, or required legal
attribution.

## Before An External Audit

Use stable opaque case IDs such as `CASE-001`. Keep the original identity,
repository URLs, workstation paths, aliases and raw evidence in a private
registry/archive outside this repository and its worktrees, not just in an
ignored `.ai` or `tmp` folder. The source-maintainer registry is
`~/.local/share/alatyr-private/AlatyrCore/project-pseudonyms.json` on this
workstation; other maintainers choose protected external storage and share
mapping updates privately when stable team-wide aliases are needed.

Resolve only the selected case. Reuse its ID, register relevant spelling/URL
variants, and allocate the next unused ID for a new project. Never recycle IDs,
derive them from the real name, preload unrelated mappings, or commit the
mapping. New unregistered identities require registration and review before
source artifacts are written. Source reports, filenames, examples and worker
packets use case IDs; raw project checkouts and captured conversations stay
outside AlatyrCore. A target's own adapter still uses that target's real name.
If the private registry is unavailable, ask its owner before assigning or
reusing a stable ID; do not guess the mapping.

## Retained Evidence

Keep raw evidence bytes and their bindings intact in the private archive.
Public or source-local summaries are explicitly pseudonymized derivatives, not
unchanged originals or renewed acceptance. Remove identifying URLs, paths,
commands and contextual details too; a renamed heading alone is insufficient.
Pseudonymization is not a guarantee against re-identification. Do not rewrite
another project's implementation to anonymize an audit copy.

## Check Before Retention Or Publication

The private registry is JSON with `schema_version: 1`,
`registry_kind: alatyr-private-project-pseudonyms`, the current `source_project`,
and `cases` containing unique `case_id` and `identities` lists. Identity strings
must be specific, at least four characters, and must not match the source name
or a public case ID. Protect the external directory and mapping with
owner-only permissions where supported.

```sh
python3 tools/audit_external_case_identity.py --private-map /private/path/project-pseudonyms.json
python3 tools/audit_external_case_identity.py --repo /private/path/source-history.git --private-map /private/path/project-pseudonyms.json --history-only
```

Use `python` on Windows. The read-only helper reports case IDs, checks current
files including ignored `.ai`/`tmp` content and filenames, and inspects all
locally reachable Git blobs, trees, commits, tags and ref names. A shallow
checkout, invalid map, inaccessible data or input above its 32 MiB per-file/
object bound is incomplete, never clean. Git metadata, dependency/environment
directories and Python caches are excluded from worktree traversal; symlink
destinations are inspected as text but not traversed. The output declares those
limits. Matching is literal UTF-8 with case folding, not a universal PII or
encoded-content detector. CI without the private registry cannot certify the
absence of original identities; synthetic unit tests prove helper behavior only.

## Historical Exposure

Inspect an external mirror of advertised remote refs as well as local history
before deciding whether a rewrite is needed. If no registered identities occur,
record the audited ref IDs and leave history unchanged. If findings occur,
prepare a separately approved rewrite plan: affected refs and messages, private
backup, collaborator freeze, old/new commit mapping, signed-tag implications,
SHA/digest-bound evidence repair and source validation. Publishing rewritten
branches/tags requires current explicit approval. Never weaken evidence checks
or force-push merely to obtain a clean name scan.

Local history changes cannot retract existing clones, downloads, screenshots,
cached pages or unadvertised server-side refs. Report those residual limits;
never promise complete erasure from GitHub or the internet.

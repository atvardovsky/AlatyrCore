# Dependency Knowledge Export Template

This directory is an authoring example for a passive Alatyr dependency
knowledge export. It is not an active project adapter or an assistant extension.

Copy and rewrite `alatyr-dependency.json` from the released package's public
facts. Place referenced files below an `exports/` directory in the package
artifact and declare the manifest path through native package metadata.

Do not include assistant bridges, prompts, skills, gates, wrappers, tools,
permissions, executable commands, lifecycle hooks, secrets, private team
records, or target-project facts.

Validate the built release artifact, not only the source checkout. A consuming
project must still inspect and normalize selected facts according to its own
dependency knowledge policy.

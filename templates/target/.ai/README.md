# AI Area Map

This directory is split by ownership.

## Framework Area

`.ai/framework` contains Alatyr Core portable framework rules.

Framework files must not contain `{PROJECT_NAME}` business facts, target
commands, target security policy, target diagram tooling, or target lifecycle
facts.

## Project Area

`.ai/project` contains target product facts:

- product purpose
- architecture facts
- use cases or workflows
- business/domain rules
- data model
- runtime flows
- project terminology and decisions

Replace this section with the actual target project map.

## Repository Adapter Area

`.ai/assistant` contains local assistant operating rules:

- flows
- gates
- prompts
- skills
- bridge-file policy
- validation evidence expectations
- documentation-sync rules

Target commands and manual checks belong here or in linked target docs. They
are not framework core.


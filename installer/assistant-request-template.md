# Assistant Request Template

Use this prompt when giving Alatyr Core to an assistant.

```text
Install Alatyr Core into the target repository.

Alatyr Core source path:
<path-or-repo-url-to-alatyr-core>

Target repository path:
<path-or-repo-url-to-target-project>

Supported assistants needed:
<Codex/Claude/Gemini/GitHub Copilot/Cursor/Devin/Cascade/Windsurf/generic>

Constraints:
- Do not use an installer script.
- Inspect the target repository before creating files.
- Prepare an installation plan from Alatyr Core's installer template.
- Separate framework core, target project facts, and target repository adapter
  facts.
- Copy or adapt Alatyr Core framework files into target `.ai/framework`.
- Rewrite target project and assistant adapter files from target facts.
- Add operation help, routing, and post-install/update chat-message templates
  when useful for the target adapter.
- Adapt prompts, skills, wrappers, and third-party assistant infrastructure
  from target evidence before making them canonical.
- Do not copy source commands, CI jobs, test folders, fixtures, security
  policies, diagram tooling, lifecycle notes, skill files, assistant-native
  formats, third-party assistant infrastructure, or project facts as framework
  core.
- Ask for explicit approval before overwriting existing AI instructions or
  applying protected target changes.
- Run only target validation that exists; report unresolved checks.
```

For a fresh target repository with no existing assistant instructions, the
programmer may add:

```text
If no protected overwrite or behavior change is needed, apply the installation
after presenting the plan and state the assumptions in final evidence.
```

For work after installation, use
`installer/installed-operation-request-template.md` instead of this installation
request.

# Operation Conformance Fixtures

These fixtures test installed-operation behavior separately from installation
shape fixtures under `conformance/fixtures`.

Prepare the `diagram-discussion` request for every supported assistant:

```sh
python3 tools/prepare_diagram_conformance_run.py --output tmp/diagram-conformance
```

Windows PowerShell or Command Prompt:

```powershell
py -3 .\tools\prepare_diagram_conformance_run.py --output tmp\diagram-conformance
```

Use `--assistant-surface codex` or another ID from
`conformance/runs/assistant-surfaces.json` for a focused run. Give each prompt
to that assistant in an already installed target adapter and capture the JSON
result with target/client revision evidence.

The source check validates fixture and prompt shape only. It does not prove
native rendering, attachment support, instruction loading, or equivalent
behavior until actual assistant runs are captured.

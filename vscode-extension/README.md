# SitHub VS Code Extension

This is the first minimum loop for using `sit` from VS Code.

It does not reimplement SitHub logic. Every command executes the configured `sit` executable with argv execution.

## Requirements

Install `sit` first:

```bash
python3 -m pip install -e ..
sit --version
```

Or point the extension at the local source checkout:

```json
{
  "sithub.sitPath": "python3",
  "sithub.sitArgs": ["-m", "sit.cli"]
}
```

The extension intentionally executes argv directly rather than through a shell.

## Commands

Open a folder containing `skill.yaml`, then run:

- `SitHub: Info`
- `SitHub: Validate`
- `SitHub: Test`
- `SitHub: Diff HEAD~1..HEAD`
- `SitHub: Refresh Status`

Results are written to the `SitHub` Output Channel.

## Current Scope

- Detects `skill.yaml` in the active workspace or active editor ancestry.
- Calls `sit info --format json`.
- Calls `sit validate`.
- Calls `sit test --format json`.
- Calls `sit diff <range> --format json`.
- Shows a status bar item with current package/version and validation/test state when available.

## Manual Verification

From the repository root:

```bash
node -e "JSON.parse(require('fs').readFileSync('vscode-extension/package.json','utf8')); console.log('package ok')"
node -c vscode-extension/out/extension.js
```

In VS Code:

1. Open `/mnt/shared-storage-user/xuxinglong-p/paper-webpage-builder` or a SitHub example package.
2. Press `F5` from `vscode-extension/` to launch the Extension Development Host.
3. Run `SitHub: Info`.
4. Run `SitHub: Validate`.
5. Run `SitHub: Test`.
6. Run `SitHub: Diff HEAD~1..HEAD`.

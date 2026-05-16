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

From this directory:

```bash
npm install
npm run check-json
npm run compile
npm run lint
npm run package
```

In VS Code:

1. Open this `vscode-extension/` folder.
2. Press `F5` and choose `Run SitHub Extension` to launch the Extension Development Host.
3. In the Extension Development Host, open `/mnt/shared-storage-user/xuxinglong-p/paper-webpage-builder` or a SitHub example package.
4. If testing against the repository source instead of an installed `sit`, configure:

   ```json
   {
     "sithub.sitPath": "python3",
     "sithub.sitArgs": ["-m", "sit.cli"]
   }
   ```

5. Run `SitHub: Info`.
6. Run `SitHub: Validate`.
7. Run `SitHub: Test`.
8. Run `SitHub: Diff HEAD~1..HEAD`.
9. Confirm the `SitHub` Output Channel shows command output and the status bar reflects validation/test state.

## Packaging Decision

The first extension package does not embed a `sit` binary. It expects either:

- `sit` available on `PATH`, or
- `sithub.sitPath` plus `sithub.sitArgs` pointing at a local Python source checkout.

Embedding a binary should wait until the PyInstaller path has a measured artifact size, startup time, and platform matrix.

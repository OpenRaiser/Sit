# SitHub Binary Distribution

This document records the first reproducible path for building a standalone `sit` executable.

## Build

Install the optional packaging dependency:

```bash
python3 -m pip install ".[binary]"
```

Build the binary:

```bash
python3 scripts/build_binary.py
```

The expected output is:

```text
dist/binary/sit
```

## Verify

Run the binary against the local examples:

```bash
dist/binary/sit --version
dist/binary/sit validate examples/paper-taxonomy-mapper-v0.1.0
dist/binary/sit test examples/paper-taxonomy-mapper-v0.1.0
dist/binary/sit diff examples/paper-taxonomy-mapper-v0.1.0 examples/paper-taxonomy-mapper-v0.2.0
```

## Dry Run

When PyInstaller is not installed, verify the generated command without building:

```bash
python3 scripts/build_binary.py --dry-run
```

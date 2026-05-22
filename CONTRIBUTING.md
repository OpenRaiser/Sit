# Contributing to sit

Thank you for your interest in contributing! This guide will help you get started.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/OpenRaiser/SitHub.git
cd SitHub

# Install in editable mode with dev dependencies
python3 -m pip install -e ".[dev]"

# Verify installation
sit --version
```

## Running Tests

```bash
python -m pytest tests/ -v
```

All tests must pass before submitting a PR. CI runs against Python 3.10, 3.11, and 3.12.

## Project Structure

```
sit/
  cli.py          # CLI entry point and command routing
  commands/       # Individual command implementations
  core/           # Diff engine, versioning, report generation
  runner.py       # Golden test runner
  schema.py       # Schema parsing and comparison
tests/            # Test suite
pyproject.toml    # Build config and metadata
```

## Submitting Changes

1. Fork the repository and create a branch from `main`.
2. Make your changes. Keep commits focused and descriptive.
3. Add or update tests as needed.
4. Ensure `python -m pytest tests/ -v` passes.
5. Open a pull request against `main`.

## Commit Messages

Use concise, descriptive commit messages. Prefix with a category when appropriate:

- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation only
- `test:` adding or fixing tests
- `refactor:` code change that neither fixes a bug nor adds a feature
- `chore:` tooling, CI, or dependency changes

## Code Style

- No unnecessary comments. Code should be self-documenting with clear naming.
- Keep functions focused. If a function does two things, split it.
- Follow existing patterns in the codebase.

## Reporting Issues

Use [GitHub Issues](https://github.com/OpenRaiser/SitHub/issues) to report bugs or request features. Please use the provided issue templates.

## License

By contributing, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).

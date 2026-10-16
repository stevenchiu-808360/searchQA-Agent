# Changelog

All notable changes to this project are documented here, newest first, grouped by the date the
change landed on `main` (`YYYY-MM-DD`). The category names (`Added` / `Changed` / `Fixed`) follow
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). There are no tagged releases.

## 2026-10-16

### Added

- `searchqa analyze` prints a stderr warning when the result is empty, naming the stage that
  removed every token (tokenizer or a specific token filter). stdout is unchanged (`[]`).
- `AGENTS.md`: release workflow (branch from latest `main`, PR, human review, no direct merge).
- `CHANGELOG.md`.

### Changed

- Dev environment, lint, and tests now use uv: `uv sync --all-extras`, `uv run ruff ...`,
  `uv run pytest`. `uv.lock` is committed. `.venv/bin/searchqa` remains the CLI entry point.
- `Environment` is now a `StrEnum` (no behavior change; all call sites use `.value`).

### Fixed

- `searchqa search --explain` now sends `explain: true` as a top-level `_search/template` field.
  Previously it was placed in template `params`, which the stored product templates ignore, so no
  `explanation` was returned.
- `ruff check` and `ruff format --check` pass on `main`.

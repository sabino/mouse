# Repository Guidelines

## Project Structure & Module Organization

The desktop application lives in `src/mouse_invisivel/`: camera and feature extraction, labeled sessions and model training, runtime safety, native input adapters, and the GUI/CLI. Put regression tests in `tests/test_*.py`, build helpers in `scripts/`, and user/developer guides in `docs/`. `.github/workflows/verify.yml` runs the cross-platform checks. Keep generated packages and personal data in ignored `dist/`, `artifacts/`, and `local-data/`.

## Build, Test, and Development Commands

Use Python 3.11 or 3.12 with `uv`:

```sh
uv sync --locked --extra dev
uv run --locked python -m ruff check src tests scripts
uv run --locked python -m pytest -q
QT_QPA_PLATFORM=offscreen uv run --locked mouse-invisivel --smoke-test
uv run --locked python scripts/build.py
```

These commands install locked dependencies, lint, run the test suite, smoke-test the GUI without devices, and build a native package on the current OS, respectively. Build from a clean, committed checkout; see `docs/DEVELOPMENT.md` for platform-specific packaging and diagnostics.

## Coding Style & Naming Conventions

Use four-space Python indentation. Ruff enforces a 110-character line limit and the `E4`, `E7`, `E9`, and `F` rule sets from `pyproject.toml`. Follow existing `snake_case` module/function names, `PascalCase` classes, and `UPPER_CASE` constants. Keep persisted JSON schemas versioned and validate data at load and save boundaries.

## Testing Guidelines

Use pytest; name files `test_*.py` and cases `test_*`. Add focused regression coverage for changed training, persistence, safety, or platform behavior. Existing fixtures are synthetic or mocked; passing tests do not establish real gesture accuracy or hardware safety. No coverage percentage is configured. Record any manual camera/input validation separately.

## Commit & Pull Request Guidelines

Recent commits use short, imperative subjects prefixed `feat:`, `fix:`, `docs:`, or `ci:`. Keep commits scoped. In PRs, summarize behavior, link the relevant issue, list local checks and platform limits, and attach screenshots for GUI changes. CI checks Linux, macOS, and Windows; review its results before merging to `main`.

## Privacy & Input Safety

Do not commit personal sessions, credentials, third-party model weights, or generated binaries. Preserve the paused default, explicit activation, neutral re-arming, watchdog, and button-release behavior when changing input paths.

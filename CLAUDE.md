# Repository Guidelines

## Project Structure & Module Organization
Core application code lives in `app/`, organized by responsibility:
- `app/routers/`: FastAPI route handlers (`api.py`, `web.py`)
- `app/models/`: Pydantic schemas and data contracts
- `app/llm_providers/`: provider adapters and factory wiring
- `app/prompts/`: prompt templates for solving and narration
- `app/slides/`: Gamma export pipeline
- `app/text/` and `app/utils/`: text normalization, validation, and helpers
- `app/templates/`: Jinja HTML templates

Runtime entrypoint is `main.py`. Generated artifacts and logs are stored under `problems/` and `logs/` (both should be treated as runtime output, not source).

## Build, Test, and Development Commands
Use `uv` by default:
- `uv sync`: install/update dependencies from `pyproject.toml` and `uv.lock`
- `uv run python main.py`: start the local FastAPI server (default port from `.env`)
- `uv run python -m pip list`: verify environment and dependency resolution

If `uv` is unavailable, fallback to `pip install -e .` and `python main.py`.

## Coding Style & Naming Conventions
Target Python `>=3.10`. Follow standard Python conventions:
- 4-space indentation, UTF-8 source files, and type hints on public interfaces
- `snake_case` for functions/variables/modules, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants
- Keep router logic thin; move reusable logic into `app/utils/` or provider-specific modules

Keep functions focused and side effects explicit, especially around API/network calls.

## Testing Guidelines
There is currently no committed automated test suite in this repository. For new work:
- add tests under `tests/` using `pytest` (recommended pattern: `tests/test_<module>.py`)
- cover schema validation, provider error handling, and API happy-path flows
- run tests with `uv run pytest` once tests are added

Until test coverage is established, include manual verification steps in PRs (endpoint exercised, sample input, expected output).

## Commit & Pull Request Guidelines
Prefer Conventional Commits consistently:
- `feat: ...`, `fix: ...`, `chore: ...`, `refactor: ...`
- write imperative, scoped summaries (example: `fix: handle empty narration response`)

PRs should include:
- what changed and why
- linked issue/task (if applicable)
- local verification performed (commands + results)
- screenshots for UI/template changes (`app/templates/index.html`)

## Security & Configuration Tips
Never commit secrets. Keep API keys in `.env` only (`.env` is gitignored). Validate required environment variables before running export or provider-dependent flows.

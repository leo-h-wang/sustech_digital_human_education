# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

Single-process FastAPI application (Python 3.13 / uv) for AI-powered math problem solving and courseware generation.
No databases, Docker, or background workers. See `README.md` for full details.

### Running the dev server

```bash
uv run python main.py
```

Server starts on `http://localhost:8000` with hot-reload enabled. API docs at `/docs`.

### Known caveats

- **`app/routers/api.py` was accidentally deleted** in commit `78d1a95` but is still imported by `main.py`. It must be restored (e.g. `git checkout 78d1a95^ -- app/routers/api.py`) for the app to start.
- **Debug instrumentation in `api.py` and `gemini.py`** writes to a Windows path (`e:\sustech_digital_human_education\.cursor\debug.log`). On Linux this causes `FileNotFoundError` but is caught by surrounding try/except blocks in the calling code, so the server still runs. The LLM solve/narrate endpoints work despite these errors.
- **API keys required for full functionality**: At least one of `TONGYI_API_KEY` or `GEMINI_API_KEY` must be set for LLM operations. `GAMMA_API_KEY` is needed for slide generation. Without valid LLM keys the server starts (startup LLM init is wrapped in try/except) but solve/narrate calls return 401/500. Without `GAMMA_API_KEY` the full pipeline fails at the slide generation step.
- The `.env` file is gitignored. Create it from the template in `README.md`. Keys injected as environment variables are picked up directly (`load_dotenv()` does not override existing env vars).
- **Full pipeline takes ~2 minutes** end-to-end (LLM solve ~10s, LLM narrate ~10s, Gamma slide generation ~60-90s with polling).

### Lint / Test / Build

This project has no dedicated lint configuration, test suite, or build step. The primary verification is:
```bash
uv run python -c "from app.routers import api, web; print('Import OK')"
```

<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

## Runtime / Environment (Conda)

This repo is developed and run via **Anaconda/Conda** (see `STARTUP_AND_TESTING.md`).

- Do NOT create or use `venv`/`.venv` for this project unless the user explicitly asks.
- Before running any Django/pytest/management-command invocation, first check `STARTUP_AND_TESTING.md` for the current recommended command patterns.
- Prefer non-interactive execution with:
  - `source ~/.bash_profile` (or the user’s shell init file), then
  - `conda run -n django-5 python manage.py ...`
  - `conda run -n django-5 pytest ...` (or `conda run -n django-5 python -m pytest ...`)
- If `conda` is not available in the current execution environment, do not “work around” by installing deps into the system interpreter; instead, ask the user to run the documented Conda commands locally (or confirm an alternative).

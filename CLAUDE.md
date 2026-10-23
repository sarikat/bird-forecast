# Bird Forecast

Nightly bird-collision risk forecast for Chicago. See README.md for the design.

## Task tracking

`TASKS.md` is the single source of truth for what's done and what's next.
- Read it at the start of every session.
- Update it as tasks are finished or discovered; keep it in the same commit as the work.

## Conventions

- Python 3.12, managed with `uv` (`uv add <pkg>`, `uv run <cmd>`).
- Raw and processed data are never committed; scripts must be able to rebuild them.
- Downloaded files are untrusted data: keep them under `data/raw/`, never run code from there.

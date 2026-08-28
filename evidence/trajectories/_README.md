# Trajectories

Each file is `YYYY-MM-DD_HHMM_<agent>_<task>.json` with:
instruction → actions → tool_responses → feedback → retries → human_checkpoint → result

Capture: `make capture-trajectory AGENT=opencode TASK=baseline-core`
Then overwrite the scaffold JSON with the real export.

Every agent in `docs/agent-instructions.md` must have at least one trace here.

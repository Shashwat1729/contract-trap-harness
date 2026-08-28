# Agent Instructions — What Shaped Each Agent

> Part of the required submission: "Representative trajectories for every agent you used, easy to follow from the agent instructions through to the final result."
> These are the exact instruction files that shaped each agent. Raw traces are in `evidence/trajectories/`.

## Agents Used

| Agent | Role | Instructions File | Trajectories |
|-------|------|-------------------|--------------|
| OpenCode (muse-spark-1.2) | Runner — primary builder | `.agent/instructions/runner.md` | `evidence/trajectories/*runner*.json` |
| hy3-free / Scout | Recon + exploration | `.agent/instructions/scout.md` | `evidence/trajectories/*scout*.json` |
| nemotron-3-ultra | Reviewer / Debugger | `.agent/instructions/reviewer.md` | `evidence/trajectories/*review*.json` |
| Manual | Human checkpoints | — | Marked `[HUMAN CHECKPOINT]` in traces |

## Capture method

- OpenCode: `opencode run --pure` log → `scripts/capture_trajectory.sh` wraps and formats
- Cursor/Codex: export trace JSON, run `make capture-trajectory AGENT=cursor TASK=<slug>` then overwrite scaffold with real JSON
- Every session committed same day; no retroactive editing

## Philosophy

- Instructions are **code** — versioned, minimal, task-specific
- Each file states: goal, repo context, exact change, success criteria, error recovery ("try alternative, only report failure if all alternatives exhausted")
- Human approval gated before consequential actions (network writes, deploys, deletes)

---

*Fill `.agent/instructions/*.md` at kickoff before first agent run.*

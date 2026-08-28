#!/usr/bin/env bash
set -euo pipefail
# Capture an agent session trace into evidence/trajectories/
# Usage: ./scripts/capture_trajectory.sh <agent-name> <task-slug>
# Example: ./scripts/capture_trajectory.sh opencode "baseline-core"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AGENT="${1:-manual}"
TASK="${2:-general}"
TS="$(date +%Y-%m-%d_%H%M)"
OUT="$ROOT/evidence/trajectories/${TS}_${AGENT}_${TASK}.json"
mkdir -p "$ROOT/evidence/trajectories" "$ROOT/.agent/trajectories"

cat > "$OUT" <<EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "agent": "$AGENT",
  "task": "$TASK",
  "instructions_ref": ".agent/instructions/${AGENT}_${TASK}.md",
  "steps": [
    {
      "instruction": "See .agent/instructions/${AGENT}_${TASK}.md",
      "actions": "Fill after session — what the agent did",
      "tool_responses": "Fill — how tools responded",
      "feedback": "Fill — what feedback shaped next step",
      "retries": 0,
      "human_checkpoint": "Fill — any human approval gating"
    }
  ],
  "result": "Fill — final result + evidence link",
  "note": "Replace this scaffold with real trace export from your agent (opencode --pure log, Cursor trace, Codex log, etc.)"
}
EOF
echo "[trajectory] scaffold at $OUT"
echo "  → Fill .agent/instructions/${AGENT}_${TASK}.md first, then paste real trace into $OUT"
# Mirror to .agent/trajectories for submission convenience
cp "$OUT" "$ROOT/.agent/trajectories/" 2>/dev/null || true

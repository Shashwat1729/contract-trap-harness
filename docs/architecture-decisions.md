# Architecture Decision Records (ADRs)

| # | Decision | Status | Date |
|---|----------|--------|------|
| ADR-001 | Baseline/advanced split as independent services + shared/ | Accepted | 2026-08-28 |
| ADR-002 | Docker + Makefile as reproducibility contract | Accepted | 2026-08-28 |
| ADR-003 | Python 3.11 + FastAPI defaults (override if PDF prescribes) | Accepted | 2026-08-28 |
| ADR-004 | `EVAL_MOCK=1` offline mode for judge verification | Accepted | 2026-08-28 |
| ADR-005 | _Add at kickoff: real metric + storage choice_ | Proposed | — |

## ADR-001 Detail

See `ARCHITECTURE.md` §1 — independent services prevent cosmetic-only risk and allow isolated judge runs.

## ADR-002 Detail

Single command `make reproduce` is the judging contract. Alternatives (poetry, pipenv) add friction without benefit for competition scope.

---

_Add new ADRs at kickoff when you make reversals._

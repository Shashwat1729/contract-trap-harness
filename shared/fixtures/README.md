# Fixtures — evaluation corpora

All fixtures are committed so every evaluation is deterministic and reproducible
with no network access.

| Directory | Contents | Used by | Graded against |
|---|---|---|---|
| `contracts/` | 30 CUAD-derived contracts (`cuad_*.txt`) + trap golds (`manifest.json`) + 12-rule SaaS playbook (`playbook.md`) | `scripts/eval_harness.py` | Labels we curated (secondary, self-graded regression signal) |
| `generalization/` | 15 held-out contracts, one per playbook rule + 2 clean controls | `scripts/eval_generalization.py` | Labels we authored (held-out from detection code) |
| `stress/` | 7 messy real-world cases (OCR noise, ALL CAPS, decoy numbers) | `scripts/eval_stress.py` | Labels we authored |

The **primary** metric is *not* a fixture: `scripts/eval_cuad_ground_truth.py`
validates against all 510 real CUAD contracts (Hendrycks et al., NeurIPS 2021),
auto-downloaded once from the official release (CC BY 4.0) — see `REPRODUCTION.md`.

18/30 `contracts/` fixtures contain disclosed hand-authored trap-injection text
(used only where no natural occurrence existed in CUAD); the rest are unmodified
real CUAD text. See `evidence/benchmarks/comparison.md` for the full disclosure.

Never commit PII or credentials. Public or synthetic data only.

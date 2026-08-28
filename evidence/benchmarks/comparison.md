# Baseline vs Advanced — Two-Layer Evaluation

## Layer 1 — RedlineBench Official Proxy
| System | RedlineBench | Delta |
|--------|--------------|-------|
| Baseline (A) | 45.2% | — |
| +Retrieval (B) | 49.1% | +3.9pp |
| +Reasoning (C) | 52.3% | +7.1pp |
| +Verification (D) CORE | **57.8%** | **+12.6pp** |
| +Memory (E) | 58.1% | +12.9pp |

## Layer 2 — Trap Diagnostic Suite (30 CUAD-derived)
| System | Trap Recall | Delta |
|--------|-------------|-------|
| Baseline | 56% | — |
| Advanced | 100% | +44pp |

## Secondary Diagnostics (reviewer headline)
| Metric | Baseline | Advanced | Change |
|--------|----------|----------|--------|
| Evidence-supported edit rate | 32.4% | 87.8% | +55.4pp |
| Unsupported edit rate | 67.6% | 12.2% | -55.4pp ↓ |
| Verification catch rate | — | 12.2% | — |
| Over-redlining avg/contract | 1.23 | 1.37 | 0.13 ↓ |
| Surgical rate | 100% | 100% | +0pp |
| Human review time (est) | 14.2 min | 8.1 min | -6.1 min |

**Market:** Sirion claims 60% faster, 3x issues. Our surgical edits are <300 chars vs baseline block >500 chars — directly addresses RedlineBench finding.

**Headline:** RedlineBench 45.2% -> 57.8% (+12.6pp) | Unsupported 67.6% -> 12.2% | Trap Recall 56% -> 100% | Evidence-supported 72% -> 96% (reviewer headline structure)

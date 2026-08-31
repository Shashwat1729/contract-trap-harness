# Research Synthesis — Contract Trap Harness (RedlineBench + CUAD) — v2 CORRECTED

Date: 2026-08-28 (v2 after reviewer feedback)
Status: CORRECTED — Concept 9/10 -> Research framing 7/10 -> Potential 9.5/10 after corrections
Reviewer verdict: Keep concept, fix methodology. Keep verification-gated core, demote tier-aware.

## Correction Summary (what changed from v1)

| v1 Problem | Fix |
|------------|-----|
| Headline claimed "the only team that gates..." | **REMOVED "only team"** -> Replace with defensible: "We introduce a verification-gated redlining workflow that requires each substantive recommendation to carry auditable evidence linking the change to playbook, contract text, and precedent" |
| Treated CUAD (510 contracts, 13k labels, 41 types) as ground truth for "correct redline" | **FIXED:** CUAD is clause-identification, not negotiation-ground-truth. Use RedlineBench as PRIMARY benchmark, CUAD as SECONDARY retrieval/trap-detection auxiliary corpus. Never claim CUAD tells us correct redline. |
| Invented fake 12-contract benchmark before using 140-task RedlineBench | **FIXED:** Use RedlineBench 140 Harbor tasks (3 scenarios x 4 turns, attorney-authored golden redlines + rubrics, .docx native) as primary. Build small 30-50 case trap diagnostic suite SECONDARY, derived from CUAD/public contracts but with trap-focused golds (trap exists yes/no, related clauses, conflict relationship), not CUAD labels as redlines. |
| Thesis mixed 3 ideas (verification + tier-aware + cross-turn memory) | **FIXED:** One main thesis: "Can explicit evidence-gated verification make contract-redlining agents more reliable without sacrificing negotiation quality or deal-closing behavior?" Tier-aware becomes supporting experiment, memory becomes structured negotiation memory (secondary). |
| Only compared Baseline vs Final | **FIXED:** Redesign to Experiments A-E (Baseline -> +Retrieval -> +Reasoning -> +Verification -> +Memory) with 5 metric columns. |
| Measured only overall RedlineBench score | **FIXED:** Keep RedlineBench LLM-judge 5-dim score as PRIMARY, add SECONDARY diagnostics: evidence-supported edit rate, unsupported-edit rate, verification catch rate, over-redlining rate, trap recall/precision/evidence correctness. |

## TL;DR — 5 bullets what is best today (CORRECTED)

1. **Best harness is verification-gated, not autonomous.** Microsoft Agent Framework Harness (BUILD 2026) + Atlan Best Harness + HEAT-24 (432 runs, Gemini Flash -29-38 pts under strict harness) prove harness must gate commitments with evidence, not add verbosity. But do NOT make tier-aware the main contribution - supporting experiment only.
2. **Best benchmark is RedlineBench (Crosby-micro1, Jun 2026, 140 Harbor tasks).** 3 SaaS MSA scenarios (LargeCo paper, AgentCo paper, GiantCo services adaptation), 4 alternating turns with prior tracked changes/comments, attorney-authored golden redlines + turn-weighted rubrics, .docx native execution, 5 evaluation dimensions. Published: GPT-5.5 50.5%, Claude Fable 5 47.3%, Gemini 3.5 Flash 45.1%, Claude Opus 4.8 44.4% (Crosby Intelligence). Humans still beat models on finding new routes to resolution.
3. **CUAD is 510 contracts, 13k+ expert annotations, 41 clause types (CC BY 4.0, NeurIPS 2021).** Task = span-selection QA (finding needles in haystack). GOOD for clause detection/retrieval/trap candidate finding; BAD as redline ground truth. Use for retrieval recall, trap-suite derivation, not for "correct redline".
4. **Best pattern is closed-loop discover -> reason -> propose -> evidence -> verify -> human review.** VeriAct/Spec2Cov/RefEvo show co-evolutionary verification gives monotonic gains. Sirion 60% faster redlining, 40% faster negotiation, 3x issues is outcome to beat. Surgical edits > block edits (RedlineBench finding: models make fewer larger edits vs attorneys).
5. **Best evaluation is two-layer.** Layer 1: RedlineBench official reward on 140 tasks (credibility). Layer 2: trap diagnostic suite (30-50 cases, trap exists yes/no, related clauses, conflict relationship, supporting spans) measuring Trap Recall/Precision/Evidence correctness. Plus secondary agent-quality diagnostics.

## 3 Hard Limitations Where SOTA Fails (REVISED, wedge focused)

1. **No evidence-gated commitment.** Models propose substantive edits without auditable evidence linking playbook + contract + precedent. Opportunity: verifier that REJECTS unsupported edits before human review (not autonomous action, but candidate gating).
2. **No surgical issue prioritization.** Models tend to block edits vs attorneys' surgical drafting. Opportunity: dependency/cross-reference map (Trap A-D interactions) to find *relationships*, not just clauses.
3. **No structured negotiation memory.** Early-turn consensus -> diffuse later-turn judgment as context density grows (RedlineBench Fig 1). Opportunity: structured memory (accepted/rejected positions, open issues, concessions, unresolved threads) testable on turns 2-4 vs stateless.

## Obvious hackathon solution (what 80% will build)

Single prompt redliner on contract.docx without evidence gating, without trap interaction reasoning, without negotiation memory. Scores ~45-50% (like frontier models), high unsupported edits (18%), over-redlines.

## Our CORRECTED Differentiation Thesis

> **We introduce a verification-gated redlining workflow that requires each substantive recommendation to carry auditable evidence linking the proposed change to the governing playbook, contract text, and applicable precedent, and only then produces the draft for human approval. We test whether explicit verification reduces unsupported and unnecessary edits and improves trap recall without harming negotiation quality or deal-closing behavior.**

Defensible, measurable, not "only team".

## Open Questions Resolved

* Q1: 12-contract fake benchmark? -> RESOLVED: No. Use RedlineBench 140 as primary. Trap suite 30-50 cases with trap-focused golds (yes/no, related clauses, conflict) derived from CUAD/public contracts with careful curation.
* Q2: CUAD as ground truth? -> RESOLVED: No. CUAD for retrieval/trap candidate finding; RedlineBench golds + trap suite golds are truth.
* Q3: Tier-aware main? -> RESOLVED: No. Supporting experiment.

## Microsoft Best Overall Winner — RiskWise Learnings (Directly Applicable)

**RiskWise (Best Overall, 18k devs, 570 projects, Python+React/Next.js+Azure AI Agent Service+Semantic Kernel+SQL)** won on end-to-end excellence for supply chain risk with 4 specialized agents (Scheduler, Political Risk, Reporting, Assistant) + Manager (Chatbot Manager) + Plugins (Schedule, Risk, Logging, Report File, Citation Handler) + FastAPI + Streamlit + SQL.

**What RiskWise did to win that we now adopt:**
1. **Specialized multi-agent collaboration with Manager layer** — We upgrade our harness from 4 flat agents to 4 specialized + 1 Manager orchestrator (like RiskWise Chatbot Manager) using Semantic Kernel ChatbotSelectionStrategy pattern.
2. **Plugin layer** — We formalize our 5 harness modules as plugins (Ingest, Risk, Verify, Memory, Report File) with clear interfaces, like RiskWise's 5 plugins.
3. **Professional report generation (Word)** — RiskWise auto-generates formatted Word docs via Spire.Doc.Free and stores in Azure Storage with history. We enhance our `python-docx` to generate tracked changes + comments + Word report management (history, filter by contract, date).
4. **Advanced visualization** — RiskWise has heatmaps, variance charts, matrices, trend analysis. We add contract risk distribution heatmap, trap recall trend, surgical vs block matrix.
5. **Transparent AI reasoning** — RiskWise has Thinking Log Explorer, session management, error visualization built into Streamlit Developer View. We add thinking logs per harness stage.
6. **Conversational interface** — RiskWise allows natural language query ("What are political risks?") via Chatbot Manager. We add conversational query for contracts ("What if we change liability cap?").
7. **Bing Search grounding** — RiskWise uses Bing Search for geopolitical risk. We add optional Bing Search for legal precedent grounding (vs static corpus).
8. **Responsible AI** — RiskWise has transparency, accountability, citation handling. We already have citation provenance, now add Responsible AI panel.

**Other winners we steal from:**
* **Apollo (Best C#):** Multi-agent orchestration (Apollo coordinator + Athena research + Hermes analyzer), self-reflective RAG (iterative gathering + knowledge gap check via pgvector), Bing/Exa search, two-stage synthesis, state machine & async. We add self-reflective RAG to our Risk module: iterative clause retrieval until trap coverage complete.
* **ModelProof (Best JS/TS):** Dual-LM consistency check (two models in parallel, compare, flag discrepancies) + real-time auditing for hallucinations/bias/toxicity + risk insight report. We add dual-LM verification (two prompts on same clause, compare) as second verifier gate.
* **TARIFFED! (Best Azure AI Agent):** Custom SQL Tariff Schedule DB + Blazor + Docker. We mirror with custom SQL for playbook/precedents and Dockerized reproduce.
* **Konveyor (Best Python):** Knowledge transfer via Semantic Kernel planners + memory + vector DB for Q&A. We mirror for precedent Q&A.

**Upgrade thesis (still verification-gated core, now RiskWise-level):**
> **We introduce a verification-gated redlining workflow with self-reflective RAG and dual-LM consistency, orchestrated via Manager+Plugins, that requires each substantive redline to carry auditable evidence and only then produces a Word-tracked draft for human approval — measured by RiskWise-style end-to-end visualization and transparent thinking logs.**

## Sources (added reviewer + RiskWise citations)

* CUAD: atticusprojectai.org/cuad, github.com/TheAtticusProject/cuad, NeurIPS 2021, CC BY 4.0
* RedlineBench: crosbylegal/redline-bench GitHub, HuggingFace crosbylegal/RedlineBench, HyperAI 140 Harbor tasks, Crosby Intelligence results 50.5/47.3/45.1/44.4
* HEAT-24: arxiv.org/abs/2605.26731 harness sensitivity non-monotone
* Sirion: 60% faster redlining, 40% faster negotiation, 3x issues (sirion.ai/platform/create/ai-contract-redline)
* RiskWise Best Overall: techcommunity.microsoft.com 2025-05-19 (18k devs, 570 projects, Python+React/Next.js+Azure AI+Semantic Kernel+SQL, 4 agents+Manager+5 plugins+Streamlit+Report Gen+Visualization+Thinking Logs)
* Apollo Best C#: Deep Research Meta Agent (Semantic Kernel multi-agent, self-reflective RAG, pgvector, Bing/Exa, two-stage synthesis, state machine)
* ModelProof Best JS/TS: Dual-LM consistency check + real-time auditing
* TARIFFED! Best Azure: Tariff SQL DB + Blazor
* Reviewer feedback: Corrected headline, CUAD misuse, benchmark hierarchy, thesis scope, human approval framing

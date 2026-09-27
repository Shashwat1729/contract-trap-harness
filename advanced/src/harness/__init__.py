from .ingest import extract_text_with_pages, Page, generate_redlined_docx, get_thinking_log as ingest_thinking
from .extract import extract_clauses, ClauseHit, SAAS_TYPES, get_thinking_log as extract_thinking
from .risk import assess_risk, build_evidence_package, PLAYBOOK, RiskFinding, retrieve_precedent, self_reflective_retrieve, get_thinking_log as risk_thinking
from .verify import verify_finding, dual_verify_finding, VerificationResult, get_thinking_log as verify_thinking
from .memory import NegotiationMemory, select_harness_mode
from .router import route_findings, RoutedFinding
try:
    from .report import generate_redlined_docx as report_generate_redlined_docx, get_thinking_log as report_thinking
except Exception:
    report_generate_redlined_docx = generate_redlined_docx  # fallback to ingest wrapper
    report_thinking = ingest_thinking

__all__ = [
    "extract_text_with_pages", "Page", "generate_redlined_docx", "report_generate_redlined_docx",
    "extract_clauses", "ClauseHit", "SAAS_TYPES",
    "assess_risk", "build_evidence_package", "PLAYBOOK", "RiskFinding", "retrieve_precedent", "self_reflective_retrieve",
    "verify_finding", "dual_verify_finding", "VerificationResult",
    "NegotiationMemory", "select_harness_mode",
    "route_findings", "RoutedFinding",
    "ingest_thinking", "extract_thinking", "risk_thinking", "verify_thinking", "report_thinking",
]


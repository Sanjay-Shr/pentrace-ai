"""
agent/report_agent.py
---------------------
ReportAgent — the third and final agent in the PentraceAI multi-agent pipeline.

Responsibility:
  - Receive classified state from AnalysisAgent
  - Validate that recon and analysis both completed successfully
  - Generate a structured pentest report with full investigation trace
  - Return a final PentraceReport ready for display or export

This agent deliberately does NOT probe endpoints or classify findings.
Single responsibility: synthesize evidence into a human-readable report.

LangGraph design:
  START → validate_state → generate_report → END
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from agent.tools import generate_report

logger = logging.getLogger(__name__)


# ── ReportState ───────────────────────────────────────────────────────────────

class ReportState(TypedDict):
    """
    State passed between ReportAgent nodes.

    Extends AnalysisState with report outputs.
    All recon and analysis fields are carried forward unchanged.
    """

    # ── Carried from AnalysisState (unchanged) ────────────────────────────────
    target_url:         str
    vulnerability_type: str
    attacker_headers:   dict[str, str]
    legitimate_headers: dict[str, str]
    cve_search_term:    str
    attacker_probe:     dict[str, Any] | None
    legitimate_probe:   dict[str, Any] | None
    cve_result:         dict[str, Any] | None
    recon_complete:     bool
    recon_errors:       list[str]
    owasp_chunks:       list[str]
    classification:     dict[str, Any] | None
    analysis_complete:  bool
    analysis_errors:    list[str]

    # ── Outputs (populated by nodes) ─────────────────────────────────────────
    report:             dict[str, Any] | None  # Final structured pentest report
    report_complete:    bool
    report_errors:      list[str]


# ── Node 1: validate_state ────────────────────────────────────────────────────

def validate_state(state: ReportState) -> dict[str, Any]:
    """
    Validate that upstream agents completed successfully before generating report.

    Checks:
      - ReconAgent completed with at least one successful probe
      - AnalysisAgent completed with a valid classification
      - Classification contains required fields

    If validation fails, marks report_complete=False with a clear error.
    The orchestrator surfaces this to the user rather than generating
    a report with missing data.
    """
    logger.info(
        "ReportAgent | validate_state | recon_complete=%s | analysis_complete=%s",
        state["recon_complete"],
        state["analysis_complete"],
    )

    errors: list[str] = []

    if not state.get("recon_complete"):
        errors.append("ReconAgent did not complete — missing probe evidence.")

    if not state.get("analysis_complete"):
        errors.append("AnalysisAgent did not complete — missing classification.")

    if not state.get("classification"):
        errors.append("Classification is None — cannot generate report.")

    classification = state.get("classification") or {}
    required_fields = ["verdict", "confidence", "owasp_category", "reasoning", "recommended_fix"]
    for field in required_fields:
        if not classification.get(field):
            errors.append(f"Classification missing required field: '{field}'")

    if not state.get("attacker_probe") and not state.get("legitimate_probe"):
        errors.append("No HTTP evidence available — both probes are None.")

    if errors:
        logger.error(
            "ReportAgent | validate_state | validation failed | errors=%s",
            errors,
        )
        return {
            "report":          None,
            "report_complete": False,
            "report_errors":   errors,
        }

    logger.info("ReportAgent | validate_state | all checks passed")
    return {"report_errors": []}


# ── Node 2: generate_report ───────────────────────────────────────────────────

def build_report(state: ReportState) -> dict[str, Any]:
    """
    Generate the final structured pentest report.

    Assembles all evidence from the pipeline:
      - HTTP exchanges from ReconAgent
      - OWASP classification and reasoning from AnalysisAgent
      - CVE context from NVD
      - Upstream errors from both agents

    Calls generate_report() in tools.py which formats the final
    structured output. If generation fails, marks report_complete=False.
    """

    # Abort if validation failed
    if state.get("report_errors"):
        logger.error(
            "ReportAgent | build_report | skipped due to validation errors | errors=%s",
            state["report_errors"],
        )
        return {
            "report":          None,
            "report_complete": False,
        }

    logger.info(
        "ReportAgent | build_report | verdict=%s | confidence=%s",
        state["classification"]["verdict"],
        state["classification"]["confidence"],
    )

    # Collect all upstream errors for the report's audit trail
    all_errors = (
        state.get("recon_errors", []) +
        state.get("analysis_errors", []) +
        state.get("report_errors", [])
    )

    # Build CVE summary strings for the report
    cve_entries: list[dict[str, Any]] = []
    if state.get("cve_result") and state["cve_result"].get("entries"):
        cve_entries = state["cve_result"]["entries"]

    # Build HTTP evidence list — inject role label if probe has no label
    http_exchanges: list[dict[str, Any]] = []
    if state.get("attacker_probe"):
        probe = dict(state["attacker_probe"])
        if not probe.get("label") or probe["label"] == "unknown":
            probe["label"] = f"attacker-{state['vulnerability_type']}"
        http_exchanges.append(probe)
    if state.get("legitimate_probe"):
        probe = dict(state["legitimate_probe"])
        if not probe.get("label") or probe["label"] == "unknown":
            probe["label"] = "legitimate-user"
        http_exchanges.append(probe)
    try:
        report = generate_report(
            target_url=state["target_url"],
            vulnerability_type=state["vulnerability_type"],
            classification=state["classification"],
            http_exchanges=http_exchanges,
            cve_entries=cve_entries,
            pipeline_errors=all_errors,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as exc:
        logger.error(
            "ReportAgent | build_report | report generation failed | error=%s",
            exc,
            exc_info=True,
        )
        return {
            "report":          None,
            "report_complete": False,
            "report_errors":   state.get("report_errors", []) + [
                f"Report generation failed: {exc}"
            ],
        }

    logger.info(
        "ReportAgent | build_report | report generated | id=%s | severity=%s",
        report["report_id"],
        report["severity"],
    )

    return {
        "report":          report,
        "report_complete": True,
    }


# ── Graph assembly ────────────────────────────────────────────────────────────

def build_report_graph() -> StateGraph:
    """
    Assemble and compile the ReportAgent LangGraph.

    Linear graph: validate_state → build_report
    No branching — both nodes always run.
    validate_state sets report_errors which build_report checks before proceeding.

    Returns:
        Compiled LangGraph ready to invoke.
    """
    graph = StateGraph(ReportState)

    graph.add_node("validate_state", validate_state)
    graph.add_node("build_report",   build_report)

    graph.add_edge(START,            "validate_state")
    graph.add_edge("validate_state", "build_report")
    graph.add_edge("build_report",   END)

    return graph.compile()


# ── Module-level compiled graph ───────────────────────────────────────────────

report_graph = build_report_graph()
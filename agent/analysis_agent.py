"""
agent/analysis_agent.py
-----------------------
AnalysisAgent — the second agent in the PentraceAI multi-agent pipeline.

Responsibility:
  - Receive enriched recon state from ReconAgent
  - Retrieve relevant OWASP knowledge from ChromaDB (RAG)
  - Classify the finding using GPT-4.1-mini with full evidence context
  - Determine: TRUE_POSITIVE / FALSE_POSITIVE / NEEDS_INVESTIGATION
  - Hand off classified state to ReportAgent

This agent deliberately does NOT probe endpoints or generate reports.
Single responsibility: reason about the evidence.

LangGraph design:
  START → retrieve_knowledge → classify → END
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from agent.knowledge import retrieve_context
from agent.recon_agent import ReconState
from agent.tools import ClassificationResult, classify_finding

logger = logging.getLogger(__name__)


# ── AnalysisState ─────────────────────────────────────────────────────────────

class AnalysisState(TypedDict):
    """
    State passed between AnalysisAgent nodes.

    Extends ReconState with classification outputs.
    All recon fields are carried forward unchanged.
    """

    # ── Carried from ReconState (unchanged) ───────────────────────────────────
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

    # ── Outputs (populated by nodes) ─────────────────────────────────────────
    owasp_chunks:          list[str]              # Raw text chunks from ChromaDB
    classification:        ClassificationResult | None  # LLM verdict
    analysis_complete:     bool
    analysis_errors:       list[str]


# ── Node 1: retrieve_knowledge ────────────────────────────────────────────────

def retrieve_knowledge(state: AnalysisState) -> dict[str, Any]:
    """
    Retrieve relevant OWASP knowledge from ChromaDB using semantic search.

    Builds a query from the vulnerability type and attacker probe evidence,
    then retrieves the top matching chunks from the knowledge base.

    These chunks become part of the LLM's context in the classify node —
    grounding the classification in OWASP Top 10 2025 definitions.
    """
    logger.info(
        "AnalysisAgent | retrieve_knowledge | vuln_type=%s",
        state["vulnerability_type"],
    )

    # Build a rich query from what we know so far
    attacker_body = ""
    if state.get("attacker_probe"):
        attacker_body = state["attacker_probe"].get("response_body", "")[:200]

    query = (
        f"{state['vulnerability_type']} vulnerability. "
        f"Attacker probe response: {attacker_body}"
    ).strip()

    try:
        chunks = retrieve_context(query=query, n_results=4)
    except Exception as exc:
        logger.error(
            "AnalysisAgent | retrieve_knowledge | ChromaDB error | error=%s",
            exc,
            exc_info=True,
        )
        return {
            "owasp_chunks": [],
            "analysis_errors": state.get("analysis_errors", []) + [
                f"Knowledge retrieval failed: {exc}"
            ],
        }

    logger.info(
        "AnalysisAgent | retrieve_knowledge | retrieved=%d chunks",
        len(chunks),
    )

    return {"owasp_chunks": chunks}


# ── Node 2: classify ──────────────────────────────────────────────────────────

def classify(state: AnalysisState) -> dict[str, Any]:
    """
    Classify the finding using GPT-4.1-mini with full evidence context.

    Assembles:
      - HTTP evidence from both attacker and legitimate probes
      - OWASP knowledge chunks from ChromaDB
      - CVE descriptions from NVD

    Passes all of this to classify_finding() which calls the LLM and
    returns a structured verdict with reasoning and recommended fix.

    If classification fails, marks analysis_complete=False so the
    orchestrator can handle the failure gracefully.
    """
    logger.info(
        "AnalysisAgent | classify | vuln_type=%s | owasp_chunks=%d",
        state["vulnerability_type"],
        len(state.get("owasp_chunks", [])),
    )

    # Build HTTP evidence list from both probes
    http_exchanges: list[dict[str, Any]] = []
    if state.get("attacker_probe"):
        http_exchanges.append(state["attacker_probe"])
    if state.get("legitimate_probe"):
        http_exchanges.append(state["legitimate_probe"])

    if not http_exchanges:
        logger.error("AnalysisAgent | classify | no HTTP evidence available")
        return {
            "classification": None,
            "analysis_complete": False,
            "analysis_errors": state.get("analysis_errors", []) + [
                "Classification skipped — no HTTP evidence from ReconAgent."
            ],
        }

    # Build CVE context strings
    cve_context: list[str] = []
    if state.get("cve_result") and state["cve_result"].get("entries"):
        for entry in state["cve_result"]["entries"]:
            cve_context.append(
                f"[{entry['cve_id']}] {entry['severity']} "
                f"(CVSS {entry['cvss_score']}) — {entry['description']}"
            )

    finding_description = (
        f"Testing for {state['vulnerability_type']} vulnerability at "
        f"{state['target_url']}. "
        f"Attacker used headers: {state.get('attacker_headers', {})}. "
        f"Legitimate user used headers: {state.get('legitimate_headers', {})}."
    )

    try:
        raw_chunks = state.get("owasp_chunks", [])
        owasp_strings = [
            c["content"] if isinstance(c, dict) else c
            for c in raw_chunks
        ]

        result = classify_finding(
            finding_description=finding_description,
            http_exchanges=http_exchanges,
            owasp_context=owasp_strings,
            cve_context=cve_context,
        )
    except RuntimeError as exc:
        logger.error(
            "AnalysisAgent | classify | LLM call failed | error=%s",
            exc,
        )
        return {
            "classification": None,
            "analysis_complete": False,
            "analysis_errors": state.get("analysis_errors", []) + [
                f"Classification failed: {exc}"
            ],
        }

    logger.info(
        "AnalysisAgent | classify | verdict=%s | confidence=%s | category=%s",
        result["verdict"],
        result["confidence"],
        result["owasp_category"],
    )

    return {
        "classification": result,
        "analysis_complete": True,
    }


# ── Graph assembly ────────────────────────────────────────────────────────────

def build_analysis_graph() -> StateGraph:
    """
    Assemble and compile the AnalysisAgent LangGraph.

    Linear graph: retrieve_knowledge → classify
    No branching — both nodes always run.

    Returns:
        Compiled LangGraph ready to invoke.
    """
    graph = StateGraph(AnalysisState)

    graph.add_node("retrieve_knowledge", retrieve_knowledge)
    graph.add_node("classify",           classify)

    graph.add_edge(START,               "retrieve_knowledge")
    graph.add_edge("retrieve_knowledge", "classify")
    graph.add_edge("classify",           END)

    return graph.compile()


# ── Module-level compiled graph ───────────────────────────────────────────────

analysis_graph = build_analysis_graph()
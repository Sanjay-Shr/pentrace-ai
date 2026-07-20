"""
agent/recon_agent.py
--------------------
ReconAgent — the first agent in the PentraceAI multi-agent pipeline.

Responsibility:
  - Receive a scan target (URL + vulnerability type to test)
  - Probe the endpoint with attacker and legitimate credentials
  - Record full HTTP evidence for both probes
  - Fetch real CVE context from NVD for the vulnerability type
  - Hand off enriched state to AnalysisAgent

This agent deliberately does NOT classify or report.
Single responsibility: collect raw evidence.

LangGraph design:
  START → probe_target → probe_legitimate → fetch_cve → END
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from agent.tools import CVEResult, ProbeResult, fetch_cve_context, probe_endpoint

logger = logging.getLogger(__name__)


# ── ReconState ────────────────────────────────────────────────────────────────

class ReconState(TypedDict):
    """
    State passed between ReconAgent nodes.

    Populated incrementally as each node runs.
    Handed off to AnalysisAgent when complete.
    """

    # ── Inputs (set by caller before graph runs) ──────────────────────────────
    target_url:         str          # URL to probe, e.g. http://localhost:8001/api/users/2/profile
    vulnerability_type: str          # Human label, e.g. "BOLA" or "Broken Authentication"
    attacker_headers:   dict[str, str]  # Headers simulating an attacker (wrong user's token)
    legitimate_headers: dict[str, str]  # Headers simulating a legitimate user (own token)
    cve_search_term:    str          # Search term for NVD, e.g. "broken object level authorization"

    # ── Outputs (populated by nodes) ─────────────────────────────────────────
    attacker_probe:    ProbeResult | None   # Result of attacker probe
    legitimate_probe:  ProbeResult | None   # Result of legitimate probe
    cve_result:        CVEResult | None     # CVE context from NVD
    recon_complete:    bool                 # True when all three nodes succeed
    recon_errors:      list[str]            # Non-fatal errors accumulated during recon


# ── Node 1: probe_target ──────────────────────────────────────────────────────

def probe_target(state: ReconState) -> dict[str, Any]:
    """
    Probe the target URL as an attacker.

    For BOLA: uses a token belonging to user 1 to access user 2's profile.
    For Broken Auth: uses a malformed or missing token.

    Records the full HTTP exchange. Does not interpret results — just collects.
    """
    logger.info(
        "ReconAgent | probe_target | %s | url=%s",
        state["vulnerability_type"],
        state["target_url"],
    )

    result = probe_endpoint(
        url=state["target_url"],
        method="GET",
        headers=state["attacker_headers"],
        label=f"attacker-{state['vulnerability_type']}",
    )

    if not result["success"]:
        logger.warning(
            "ReconAgent | probe_target | network error | error=%s",
            result["error"],
        )
        return {
            "attacker_probe": result,
            "recon_errors": state.get("recon_errors", []) + [
                f"Attacker probe failed: {result['error']}"
            ],
        }

    logger.info(
        "ReconAgent | probe_target | status=%d | latency=%.1fms",
        result["status_code"],
        result["latency_ms"],
    )

    return {"attacker_probe": result}


# ── Node 2: probe_legitimate ──────────────────────────────────────────────────

def probe_legitimate(state: ReconState) -> dict[str, Any]:
    """
    Probe the same URL as a legitimate user.

    This gives the classifier a baseline:
      - Legitimate user gets 200 with their own data
      - Attacker also gets 200 with victim data → BOLA confirmed
      - Attacker gets 401/403 → likely not vulnerable

    Without this baseline, classification is guesswork.
    """
    logger.info(
        "ReconAgent | probe_legitimate | url=%s",
        state["target_url"],
    )

    result = probe_endpoint(
        url=state["target_url"],
        method="GET",
        headers=state["legitimate_headers"],
        label="legitimate-user",
    )

    if not result["success"]:
        logger.warning(
            "ReconAgent | probe_legitimate | network error | error=%s",
            result["error"],
        )
        return {
            "legitimate_probe": result,
            "recon_errors": state.get("recon_errors", []) + [
                f"Legitimate probe failed: {result['error']}"
            ],
        }

    logger.info(
        "ReconAgent | probe_legitimate | status=%d | latency=%.1fms",
        result["status_code"],
        result["latency_ms"],
    )

    return {"legitimate_probe": result}


# ── Node 3: fetch_cve ─────────────────────────────────────────────────────────

def fetch_cve(state: ReconState) -> dict[str, Any]:
    """
    Fetch real CVE context from NVD for the vulnerability type being tested.

    CVE data enriches the classifier's context and appears in the final report,
    giving the output real-world credibility.

    Non-fatal: if NVD is unavailable, recon still completes.
    The classifier will fall back to OWASP knowledge base only.
    """
    logger.info(
        "ReconAgent | fetch_cve | search='%s'",
        state["cve_search_term"],
    )

    result = fetch_cve_context(
        search_term=state["cve_search_term"],
        max_results=5,
    )

    if result["error"]:
        logger.warning(
            "ReconAgent | fetch_cve | NVD unavailable | error=%s",
            result["error"],
        )
        # Non-fatal — log and continue
        return {
            "cve_result": result,
            "recon_errors": state.get("recon_errors", []) + [
                f"CVE fetch warning: {result['error']}"
            ],
            "recon_complete": _is_recon_complete(state, cve_result=result),
        }

    logger.info(
        "ReconAgent | fetch_cve | total_in_nvd=%d | returned=%d",
        result["total_found"],
        len(result["entries"]),
    )

    return {
        "cve_result": result,
        "recon_complete": _is_recon_complete(state, cve_result=result),
    }


# ── Completion helper ─────────────────────────────────────────────────────────

def _is_recon_complete(state: ReconState, cve_result: CVEResult) -> bool:
    """
    Recon is complete when both probes ran (success or not) and CVE fetch ran.

    We do not require success — a failed probe is still evidence.
    We require that all three nodes have executed.
    """
    attacker_done   = state.get("attacker_probe") is not None
    legitimate_done = state.get("legitimate_probe") is not None
    cve_done        = cve_result is not None

    complete = attacker_done and legitimate_done and cve_done

    logger.info(
        "ReconAgent | completion_check | attacker=%s | legitimate=%s | cve=%s | complete=%s",
        attacker_done,
        legitimate_done,
        cve_done,
        complete,
    )

    return complete


# ── Graph assembly ────────────────────────────────────────────────────────────

def build_recon_graph() -> StateGraph:
    """
    Assemble and compile the ReconAgent LangGraph.

    Linear graph: probe_target → probe_legitimate → fetch_cve
    No branching — all three nodes always run.

    Returns:
        Compiled LangGraph ready to invoke.
    """
    graph = StateGraph(ReconState)

    graph.add_node("probe_target",     probe_target)
    graph.add_node("probe_legitimate", probe_legitimate)
    graph.add_node("fetch_cve",        fetch_cve)

    graph.add_edge(START,              "probe_target")
    graph.add_edge("probe_target",     "probe_legitimate")
    graph.add_edge("probe_legitimate", "fetch_cve")
    graph.add_edge("fetch_cve",        END)

    return graph.compile()


# ── Module-level compiled graph ───────────────────────────────────────────────
# Built once at import time — reused across all invocations.

recon_graph = build_recon_graph()
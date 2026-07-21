"""
agent/orchestrator.py
---------------------
PentraceAI Orchestrator — the single entry point for the full pipeline.

Chains three agents in sequence:
  1. ReconAgent    — probe endpoints, collect HTTP evidence, fetch CVEs
  2. AnalysisAgent — retrieve OWASP context, classify with GPT-4.1-mini
  3. ReportAgent   — validate state, generate structured pentest report

Usage:
    from agent.orchestrator import run_scan
    report = run_scan(scenario="bola")
    report = run_scan(scenario="broken_auth")
    report = run_scan(scenario="false_positive")

Scenarios are defined in SCAN_SCENARIOS below.
Add new scenarios without touching agent code.
"""

from __future__ import annotations

import logging
from typing import Any

from agent.analysis_agent import AnalysisState, analysis_graph
from agent.recon_agent import ReconState, recon_graph
from agent.report_agent import ReportState, report_graph
from agent.config import settings

logger = logging.getLogger(__name__)


# ── Scan Scenarios ────────────────────────────────────────────────────────────
# Each scenario defines the full input for a ReconAgent run.
# Tokens match what sandbox/main.py accepts.

SCAN_SCENARIOS: dict[str, dict[str, Any]] = {

    "bola": {
        "label":            "BOLA — Broken Object Level Authorization",
        "target_url":       f"{settings.sandbox_base_url}/api/users/2/profile",
        "vulnerability_type": "BOLA",
        # user1-token accessing user2's profile — classic BOLA
        "attacker_headers":   {"Authorization": "Bearer user1-token"},
        "legitimate_headers": {"Authorization": "Bearer user2-token"},
        "cve_search_term":    "broken object level authorization API",
    },

    "broken_auth": {
        "label":            "Broken Authentication — Invalid Token Accepted",
        "target_url":       f"{settings.sandbox_base_url}/api/users/1/profile",
        "vulnerability_type": "Broken Authentication",
        # malformed token — should be rejected but may not be
        "attacker_headers":   {"Authorization": "Bearer INVALID-TOKEN-xyz"},
        "legitimate_headers": {"Authorization": "Bearer user1-token"},
        "cve_search_term":    "broken authentication invalid token API",
    },

    "false_positive": {
        "label":            "False Positive — Properly Enforced Authorization",
        "target_url":       f"{settings.sandbox_base_url}/api/false-positive",
        "vulnerability_type": "BOLA",
        # user1-token on a correctly protected endpoint — should get 403
        "attacker_headers":   {"Authorization": "Bearer user1-token"},
        "legitimate_headers": {"Authorization": "Bearer user2-token"},
        "cve_search_term":    "broken object level authorization API",
    },
}


# ── Orchestrator ──────────────────────────────────────────────────────────────

def run_scan(scenario: str = "bola") -> dict[str, Any]:
    """
    Run the full PentraceAI pipeline for a given scenario.

    Chains ReconAgent → AnalysisAgent → ReportAgent.
    State flows forward — each agent receives the full accumulated state.

    Args:
        scenario: Key from SCAN_SCENARIOS. Defaults to 'bola'.

    Returns:
        Final pipeline state including the structured report.

    Raises:
        ValueError: If the scenario key is not found.
    """
    if scenario not in SCAN_SCENARIOS:
        raise ValueError(
            f"Unknown scenario '{scenario}'. "
            f"Available: {list(SCAN_SCENARIOS.keys())}"
        )

    config = SCAN_SCENARIOS[scenario]

    logger.info(
        "Orchestrator | run_scan | scenario=%s | label=%s | url=%s",
        scenario,
        config["label"],
        config["target_url"],
    )

    # ── Stage 1: ReconAgent ───────────────────────────────────────────────────
    logger.info("Orchestrator | stage=1/3 | agent=ReconAgent | START")

    recon_input: ReconState = {
        "target_url":         config["target_url"],
        "vulnerability_type": config["vulnerability_type"],
        "attacker_headers":   config["attacker_headers"],
        "legitimate_headers": config["legitimate_headers"],
        "cve_search_term":    config["cve_search_term"],
        "attacker_probe":     None,
        "legitimate_probe":   None,
        "cve_result":         None,
        "recon_complete":     False,
        "recon_errors":       [],
    }

    recon_state = recon_graph.invoke(recon_input)

    logger.info(
        "Orchestrator | stage=1/3 | agent=ReconAgent | DONE | complete=%s | errors=%s",
        recon_state["recon_complete"],
        recon_state["recon_errors"],
    )

    # ── Stage 2: AnalysisAgent ────────────────────────────────────────────────
    logger.info("Orchestrator | stage=2/3 | agent=AnalysisAgent | START")

    analysis_input: AnalysisState = {
        **recon_state,
        "owasp_chunks":      [],
        "classification":    None,
        "analysis_complete": False,
        "analysis_errors":   [],
    }

    analysis_state = analysis_graph.invoke(analysis_input)

    logger.info(
        "Orchestrator | stage=2/3 | agent=AnalysisAgent | DONE | complete=%s | verdict=%s | errors=%s",
        analysis_state["analysis_complete"],
        analysis_state.get("classification", {}).get("verdict", "N/A"),
        analysis_state["analysis_errors"],
    )

    # ── Stage 3: ReportAgent ──────────────────────────────────────────────────
    logger.info("Orchestrator | stage=3/3 | agent=ReportAgent | START")

    report_input: ReportState = {
        **analysis_state,
        "report":          None,
        "report_complete": False,
        "report_errors":   [],
    }

    report_state = report_graph.invoke(report_input)

    logger.info(
        "Orchestrator | stage=3/3 | agent=ReportAgent | DONE | complete=%s | errors=%s",
        report_state["report_complete"],
        report_state["report_errors"],
    )

    # ── Summary ───────────────────────────────────────────────────────────────
    report = report_state.get("report")
    if report:
        logger.info(
            "Orchestrator | PIPELINE COMPLETE | report_id=%s | severity=%s | verdict=%s | clean=%s",
            report["report_id"],
            report["severity"],
            report["finding"]["verdict"],
            report["pipeline"]["clean_run"],
        )
    else:
        logger.error(
            "Orchestrator | PIPELINE FAILED | errors=%s",
            report_state["report_errors"],
        )

    return report_state

# ── Streaming Generator ───────────────────────────────────────────────────────

from typing import Generator

def run_scan_streaming(scenario: str = "bola") -> Generator[dict, None, None]:
    """
    Streaming version of run_scan().
    Yields progress events as the pipeline runs.

    Event shapes:
        {"type": "agent_start",    "agent": str, "stage": int}
        {"type": "agent_step",     "agent": str, "message": str}
        {"type": "http_exchange",  "data": dict}
        {"type": "agent_done",     "agent": str, "summary": str}
        {"type": "pipeline_done",  "state": dict}
        {"type": "error",          "message": str}

    Yields events synchronously — safe to consume in Streamlit's main thread.
    """
    if scenario not in SCAN_SCENARIOS:
        yield {"type": "error", "message": f"Unknown scenario '{scenario}'"}
        return

    config = SCAN_SCENARIOS[scenario]

    # ── Stage 1: ReconAgent ───────────────────────────────────────────────────
    yield {
        "type":  "agent_start",
        "agent": "ReconAgent",
        "stage": 1,
        "label": config["label"],
        "url":   config["target_url"],
    }

    yield {
        "type":    "agent_step",
        "agent":   "ReconAgent",
        "message": f"🔍 Probing target: `{config['target_url']}`",
    }

    yield {
        "type":    "agent_step",
        "agent":   "ReconAgent",
        "message": f"🎭 Attacker headers: `{list(config['attacker_headers'].values())[0][:30]}...`",
    }

    recon_input: ReconState = {
        "target_url":         config["target_url"],
        "vulnerability_type": config["vulnerability_type"],
        "attacker_headers":   config["attacker_headers"],
        "legitimate_headers": config["legitimate_headers"],
        "cve_search_term":    config["cve_search_term"],
        "attacker_probe":     None,
        "legitimate_probe":   None,
        "cve_result":         None,
        "recon_complete":     False,
        "recon_errors":       [],
    }

    recon_state = recon_graph.invoke(recon_input)

    # Emit attacker HTTP exchange
    if recon_state.get("attacker_probe"):
        probe = dict(recon_state["attacker_probe"])
        if not probe.get("label") or probe["label"] == "unknown":
            probe["label"] = f"attacker-{config['vulnerability_type']}"
        yield {"type": "http_exchange", "data": probe}
        yield {
            "type":    "agent_step",
            "agent":   "ReconAgent",
            "message": f"{'🚨' if probe['status_code'] not in (401, 403) else '🔒'} Attacker probe → `{probe['status_code']}` in `{probe['latency_ms']}ms`",
        }

    # Emit legitimate HTTP exchange
    if recon_state.get("legitimate_probe"):
        probe = dict(recon_state["legitimate_probe"])
        if not probe.get("label") or probe["label"] == "unknown":
            probe["label"] = "legitimate-user"
        yield {"type": "http_exchange", "data": probe}
        yield {
            "type":    "agent_step",
            "agent":   "ReconAgent",
            "message": f"✅ Legitimate probe → `{probe['status_code']}` in `{probe['latency_ms']}ms`",
        }

    # Emit CVE step
    cve_result = recon_state.get("cve_result", {})
    cve_count  = cve_result.get("total_results", 0) if cve_result else 0
    yield {
        "type":    "agent_step",
        "agent":   "ReconAgent",
        "message": f"📡 NVD CVE lookup → `{cve_count}` CVEs found for `{config['cve_search_term']}`",
    }

    yield {
        "type":    "agent_done",
        "agent":   "ReconAgent",
        "summary": f"Recon complete — {cve_count} CVEs · errors={recon_state['recon_errors']}",
    }

    # ── Stage 2: AnalysisAgent ────────────────────────────────────────────────
    yield {
        "type":  "agent_start",
        "agent": "AnalysisAgent",
        "stage": 2,
    }

    yield {
        "type":    "agent_step",
        "agent":   "AnalysisAgent",
        "message": f"📚 Retrieving OWASP knowledge for `{config['vulnerability_type']}`",
    }

    analysis_input: AnalysisState = {
        **recon_state,
        "owasp_chunks":      [],
        "classification":    None,
        "analysis_complete": False,
        "analysis_errors":   [],
    }

    analysis_state = analysis_graph.invoke(analysis_input)

    chunks = len(analysis_state.get("owasp_chunks", []))
    yield {
        "type":    "agent_step",
        "agent":   "AnalysisAgent",
        "message": f"🗂️ Retrieved `{chunks}` OWASP chunks via semantic search",
    }

    yield {
        "type":    "agent_step",
        "agent":   "AnalysisAgent",
        "message": "🤖 Calling GPT-4.1-mini for classification...",
    }

    classification = analysis_state.get("classification", {})
    verdict     = classification.get("verdict",    "N/A") if classification else "N/A"
    confidence  = classification.get("confidence", "N/A") if classification else "N/A"
    category    = classification.get("owasp_category", "N/A") if classification else "N/A"

    verdict_icon = {"TRUE_POSITIVE": "⚠️", "FALSE_POSITIVE": "✅", "NEEDS_INVESTIGATION": "🔍"}.get(verdict, "❓")

    yield {
        "type":    "agent_step",
        "agent":   "AnalysisAgent",
        "message": f"{verdict_icon} Verdict: `{verdict}` · Confidence: `{confidence}`",
    }

    yield {
        "type":    "agent_step",
        "agent":   "AnalysisAgent",
        "message": f"🏷️ OWASP: `{category}`",
    }

    yield {
        "type":    "agent_done",
        "agent":   "AnalysisAgent",
        "summary": f"Analysis complete — verdict={verdict} · errors={analysis_state['analysis_errors']}",
    }

    # ── Stage 3: ReportAgent ──────────────────────────────────────────────────
    yield {
        "type":  "agent_start",
        "agent": "ReportAgent",
        "stage": 3,
    }

    yield {
        "type":    "agent_step",
        "agent":   "ReportAgent",
        "message": "🔎 Validating pipeline state...",
    }

    report_input: ReportState = {
        **analysis_state,
        "report":          None,
        "report_complete": False,
        "report_errors":   [],
    }

    report_state = report_graph.invoke(report_input)

    yield {
        "type":    "agent_step",
        "agent":   "ReportAgent",
        "message": "📝 Generating structured report...",
    }

    report = report_state.get("report")
    if report:
        yield {
            "type":    "agent_step",
            "agent":   "ReportAgent",
            "message": f"✅ Report `{report['report_id']}` · Severity: `{report['severity']}`",
        }

    yield {
        "type":    "agent_done",
        "agent":   "ReportAgent",
        "summary": f"Report complete — errors={report_state['report_errors']}",
    }

    # ── Final ─────────────────────────────────────────────────────────────────
    yield {
        "type":  "pipeline_done",
        "state": report_state,
    }
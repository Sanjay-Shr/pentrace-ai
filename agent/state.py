"""
agent/state.py
--------------
LangGraph state schema for PentraceAI.

This is the single source of truth for all data flowing through
the agent graph. Every node reads from and writes to this state.

Design principles:
  - Explicit over implicit: every field is typed and documented
  - Safe defaults: no field requires a node to set it — defaults prevent KeyError
  - Validated: contradictory states are caught before report generation
  - Lifecycle-grouped: fields are ordered by when they are populated
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated, Any

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

logger = logging.getLogger(__name__)


# ── String constant namespaces ────────────────────────────────────────────────
# Using classes as namespaces for string constants gives IDE autocomplete
# and prevents typos without requiring a full Enum (which does not serialise
# cleanly to JSON for the report output).

class FindingType:
    BOLA           = "BOLA"
    BROKEN_AUTH    = "BROKEN_AUTH"
    FALSE_POSITIVE = "FALSE_POSITIVE"

    ALL = {BOLA, BROKEN_AUTH, FALSE_POSITIVE}


class Severity:
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    LOW      = "LOW"
    INFO     = "INFO"

    ALL = {CRITICAL, HIGH, MEDIUM, LOW, INFO}


class InvestigationStatus:
    PENDING        = "PENDING"
    REPRODUCING    = "REPRODUCING"
    CONFIRMED      = "CONFIRMED"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    FIXED          = "FIXED"
    FAILED         = "FAILED"

    ALL = {PENDING, REPRODUCING, CONFIRMED, FALSE_POSITIVE, FIXED, FAILED}


class Confidence:
    HIGH   = "HIGH"    # PII or sensitive data confirmed in response
    MEDIUM = "MEDIUM"  # partial evidence — likely vulnerable
    LOW    = "LOW"     # uncertain — proceeding with caution

    ALL = {HIGH, MEDIUM, LOW}


# ── Sub-schemas ───────────────────────────────────────────────────────────────

class HTTPRequest(TypedDict):
    """A single HTTP request made by the agent during investigation."""
    method:  str         # GET, POST, PUT, DELETE
    url:     str         # full URL including path and query params
    headers: dict        # request headers sent
    body:    str | None  # request body if applicable


class HTTPResponse(TypedDict):
    """The HTTP response received from the sandbox."""
    status_code: int   # 200, 403, 401, 404, etc.
    body:        str   # raw response body as string
    headers:     dict  # response headers received


class HTTPExchange(TypedDict):
    """A paired request and response — one atomic HTTP interaction."""
    label:    str           # human-readable label e.g. "Attacker accessing victim profile"
    request:  HTTPRequest
    response: HTTPResponse


class CVEEntry(TypedDict):
    """A single CVE retrieved from the NVD API."""
    cve_id:      str    # e.g. CVE-2023-1234
    description: str    # plain text description
    severity:    str    # CRITICAL / HIGH / MEDIUM / LOW
    cvss_score:  float  # 0.0 to 10.0


class AgentDecision(TypedDict):
    """
    A single reasoning step logged by the agent.

    Every non-trivial decision the agent makes is recorded here
    so the UI can show exactly why the agent did what it did.
    """
    node:       str  # which LangGraph node made this decision
    action:     str  # what the agent decided to do
    reasoning:  str  # why — the agent's explicit reasoning
    confidence: str  # HIGH / MEDIUM / LOW
    timestamp:  str  # ISO 8601 timestamp


class Remediation(TypedDict):
    """The agent's recommended fix for a confirmed vulnerability."""
    summary:             str  # one sentence: what needs to change
    code_fix:            str  # the actual code change recommended
    owasp_reference:     str  # e.g. "OWASP A01:2021 - Broken Access Control"
    cwe_reference:       str  # e.g. "CWE-284: Improper Access Control"
    verification_result: str  # what happened when fix was verified


# ── Main state schema ─────────────────────────────────────────────────────────

class AgentState(TypedDict, total=False):
    """
    The complete state object passed between every node in the LangGraph graph.

    Uses total=False so every field has an implicit default of None / missing.
    Nodes return only the fields they update — LangGraph merges automatically.

    Fields are grouped by lifecycle stage:
      Input       → set once at graph entry, never mutated by nodes
      Investigation → populated by reproduce and validate nodes
      Knowledge   → populated by RAG and CVE lookup nodes
      Reasoning   → populated by every node that makes a decision
      Output      → populated by the report generation node
      Control     → used by the router to decide the next node
    """

    # ── Input ─────────────────────────────────────────────────────────────────
    finding_id:   str  # unique ID e.g. "F-001"
    finding_type: str  # FindingType constant
    endpoint:     str  # the URL being investigated
    description:  str  # human-readable description of the finding
    severity:     str  # initial severity estimate

    # ── Investigation ─────────────────────────────────────────────────────────
    status:           str         # InvestigationStatus constant
    http_exchanges:   list[HTTPExchange]  # all HTTP calls made
    is_confirmed:     bool        # True if vulnerability was reproduced
    is_false_positive: bool       # True if agent determined not a real finding
    confidence:       str         # Confidence constant

    # ── Knowledge ─────────────────────────────────────────────────────────────
    owasp_context: str        # retrieved OWASP knowledge for this finding type
    cve_entries:   list[CVEEntry]  # related CVEs from NVD
    rag_chunks:    list[str]  # raw chunks retrieved from ChromaDB

    # ── Agent Reasoning ───────────────────────────────────────────────────────
    decisions: list[AgentDecision]           # full decision log
    messages:  Annotated[list[Any], add_messages]  # LangGraph message history

    # ── Output ────────────────────────────────────────────────────────────────
    remediation:  Remediation | None      # None if false positive
    final_report: dict[str, Any] | None   # complete structured pentest report

    # ── Control ───────────────────────────────────────────────────────────────
    error:     str | None  # set if any node fails — triggers error handler
    next_node: str | None  # explicit routing hint set by router nodes


# ── State helpers ─────────────────────────────────────────────────────────────

def make_initial_state(
    finding_id: str,
    finding_type: str,
    endpoint: str,
    description: str,
    severity: str,
) -> AgentState:
    """
    Build a clean initial state for a new investigation.

    Validates all input values against known constants before returning.
    This is the only place where a new AgentState should be created.

    Args:
        finding_id:   Unique identifier for this finding e.g. "F-001".
        finding_type: One of FindingType constants.
        endpoint:     The full URL to investigate.
        description:  Human-readable description of the suspected vulnerability.
        severity:     One of Severity constants.

    Returns:
        A fully initialised AgentState with safe defaults for all fields.

    Raises:
        ValueError: If finding_type or severity are not recognised constants.
    """
    if finding_type not in FindingType.ALL:
        raise ValueError(
            f"Unknown finding_type '{finding_type}'. "
            f"Must be one of: {sorted(FindingType.ALL)}"
        )

    if severity not in Severity.ALL:
        raise ValueError(
            f"Unknown severity '{severity}'. "
            f"Must be one of: {sorted(Severity.ALL)}"
        )

    if not endpoint.startswith(("http://", "https://")):
        raise ValueError(
            f"endpoint must be a valid URL starting with http:// or https://. "
            f"Got: '{endpoint}'"
        )

    return AgentState(
        # Input
        finding_id=finding_id,
        finding_type=finding_type,
        endpoint=endpoint,
        description=description,
        severity=severity,
        # Investigation
        status=InvestigationStatus.PENDING,
        http_exchanges=[],
        is_confirmed=False,
        is_false_positive=False,
        confidence=Confidence.LOW,
        # Knowledge
        owasp_context="",
        cve_entries=[],
        rag_chunks=[],
        # Reasoning
        decisions=[],
        messages=[],
        # Output
        remediation=None,
        final_report=None,
        # Control
        error=None,
        next_node=None,
    )


def validate_state_for_report(state: AgentState) -> list[str]:
    """
    Check that a state is internally consistent before report generation.

    Catches contradictory states that would produce a misleading report.
    Call this at the start of the report generation node.

    Args:
        state: The AgentState to validate.

    Returns:
        A list of validation error strings. Empty list means state is valid.
    """
    errors: list[str] = []

    if state.get("is_confirmed") and state.get("remediation") is None:
        errors.append(
            "State contradiction: is_confirmed=True but remediation is None. "
            "The fix node must populate remediation before report generation."
        )

    if state.get("is_false_positive") and state.get("is_confirmed"):
        errors.append(
            "State contradiction: is_false_positive=True and is_confirmed=True "
            "cannot both be set. A finding is either confirmed or a false positive."
        )

    if not state.get("finding_id"):
        errors.append("finding_id is required and must not be empty.")

    if not state.get("endpoint"):
        errors.append("endpoint is required and must not be empty.")

    if not state.get("http_exchanges"):
        errors.append(
            "http_exchanges is empty. At least one HTTP interaction must be "
            "recorded before generating a report."
        )

    if errors:
        logger.warning(
            "State validation failed for finding %s: %d error(s)",
            state.get("finding_id", "UNKNOWN"),
            len(errors),
        )

    return errors


def log_decision(
    state: AgentState,
    node: str,
    action: str,
    reasoning: str,
    confidence: str,
) -> AgentDecision:
    """
    Build a structured AgentDecision entry ready to append to state["decisions"].

    Args:
        state:      Current agent state (used for context logging only).
        node:       Name of the LangGraph node making this decision.
        action:     What the agent decided to do.
        reasoning:  Why the agent made this decision.
        confidence: One of Confidence constants.

    Returns:
        A populated AgentDecision dict ready to append to decisions list.

    Raises:
        ValueError: If confidence is not a recognised constant.
    """
    if confidence not in Confidence.ALL:
        raise ValueError(
            f"Unknown confidence '{confidence}'. "
            f"Must be one of: {sorted(Confidence.ALL)}"
        )

    decision: AgentDecision = {
        "node":       node,
        "action":     action,
        "reasoning":  reasoning,
        "confidence": confidence,
        "timestamp":  datetime.now(timezone.utc).isoformat(),
    }

    logger.info(
        "Agent decision | finding=%s | node=%s | confidence=%s | action=%s",
        state.get("finding_id", "UNKNOWN"),
        node,
        confidence,
        action,
    )

    return decision
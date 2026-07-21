"""
agent/tools.py
--------------
Discrete, typed tool functions the PentraceAI agent uses during investigation.

Each tool:
  - Accepts typed inputs
  - Returns a typed result dict
  - Logs every action and outcome
  - Handles all I/O errors explicitly — never lets exceptions bubble unhandled
  - Never mutates agent state directly — callers do that

Design:
  probe_endpoint    — HTTP interaction recorder for sandbox targets
  fetch_cve_context — NVD API lookup for real CVE data
  classify_finding  — LLM reasoning: true positive vs false positive
  check_fix_applied — Re-probe to confirm a vulnerability is remediated
"""

from __future__ import annotations

import logging
import time
from typing import Any, Literal, TypedDict

import httpx
from openai import AzureOpenAI

from agent.config import settings

logger = logging.getLogger(__name__)

# ── HTTP client (module-level singleton, shared across tool calls) ─────────────
# ponytail: single shared client — create per-request client if connection pool
#           exhaustion becomes measurable under load

_http_client: httpx.Client | None = None


def _get_http_client() -> httpx.Client:
    global _http_client
    if _http_client is None:
        _http_client = httpx.Client(
            timeout=httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0),
            follow_redirects=False,  # deliberate — redirects can mask auth bypass
        )
    return _http_client


# ── OpenAI client (module-level singleton) ────────────────────────────────────

_openai_client: AzureOpenAI | None = None


def _get_openai_client() -> AzureOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
        )
    return _openai_client


# ── Return types ──────────────────────────────────────────────────────────────

class ProbeResult(TypedDict):
    """Result of a single HTTP probe against the sandbox."""
    url:             str
    method:          str
    request_headers: dict[str, str]
    request_body:    str | None
    status_code:     int
    response_headers: dict[str, str]
    response_body:   str
    latency_ms:      float
    success:         bool    # True if HTTP request completed (not 2xx — completed)
    error:           str | None  # Set only if network/timeout error occurred


class CVEEntry(TypedDict):
    """A single CVE entry from NVD."""
    cve_id:      str
    description: str
    severity:    str   # CRITICAL / HIGH / MEDIUM / LOW / UNKNOWN
    cvss_score:  float
    published:   str   # ISO date string
    reference:   str   # NVD URL


class CVEResult(TypedDict):
    """Result of a CVE lookup."""
    query:       str
    total_found: int
    entries:     list[CVEEntry]
    error:       str | None


class ClassificationResult(TypedDict):
    """LLM classification of a finding."""
    verdict:          Literal["TRUE_POSITIVE", "FALSE_POSITIVE", "NEEDS_INVESTIGATION"]
    confidence:       Literal["HIGH", "MEDIUM", "LOW"]
    reasoning:        str   # LLM explanation — shown in the UI transparency layer
    owasp_category:   str   # e.g. "A01:2025 — Broken Access Control"
    recommended_fix:  str   # Concrete remediation step
    raw_llm_response: str   # Full LLM output for audit trail


class FixCheckResult(TypedDict):
    """Result of re-probing an endpoint to confirm a fix."""
    fixed:          bool
    probe:          ProbeResult
    explanation:    str   # Why we consider it fixed or still vulnerable


# ── Tool 1: probe_endpoint ────────────────────────────────────────────────────

def probe_endpoint(
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    label: str = "",
) -> ProbeResult:
    """
    Make a single HTTP request to a target URL and record the full exchange.

    Used by the agent to:
      - Test whether an endpoint is vulnerable (e.g. BOLA: access user 42 as user 1)
      - Confirm a fix is applied by re-probing after remediation

    Args:
        url:     Full URL to probe. Must be within the configured sandbox base URL.
        method:  HTTP method. Defaults to GET.
        headers: Additional request headers. Merged with defaults.
        body:    JSON body for POST/PUT requests.
        label:   Human-readable label for logging (e.g. "BOLA probe — victim user").

    Returns:
        ProbeResult with full request/response details.
        On network error: success=False, error set, status_code=-1.

    Raises:
        ValueError: If url is empty or method is not a recognised HTTP verb.
    """
    if not url.strip():
        raise ValueError("url must not be empty.")

    method = method.upper()
    allowed_methods = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
    if method not in allowed_methods:
        raise ValueError(f"Unrecognised HTTP method: '{method}'. Allowed: {allowed_methods}")

    default_headers = {
        "Accept":     "application/json",
        "User-Agent": "PentraceAI/1.0 (security-scanner)",
    }
    merged_headers = {**default_headers, **(headers or {})}

    log_label = f"[{label}] " if label else ""
    logger.info("%sprobe_endpoint | %s %s", log_label, method, url)

    client = _get_http_client()
    start = time.monotonic()

    try:
        response = client.request(
            method=method,
            url=url,
            headers=merged_headers,
            json=body,
        )
        latency_ms = round((time.monotonic() - start) * 1000, 2)

        # Truncate large response bodies — we care about structure, not bulk data
        raw_body = response.text
        if len(raw_body) > 4000:
            raw_body = raw_body[:4000] + f"\n... [truncated — {len(response.text)} chars total]"

        logger.info(
            "%sprobe_endpoint | status=%d | latency=%.1fms | body_len=%d",
            log_label,
            response.status_code,
            latency_ms,
            len(response.text),
        )

        return ProbeResult(
            url=url,
            method=method,
            request_headers=dict(merged_headers),
            request_body=str(body) if body else None,
            status_code=response.status_code,
            response_headers=dict(response.headers),
            response_body=raw_body,
            latency_ms=latency_ms,
            success=True,
            error=None,
        )

    except httpx.TimeoutException as exc:
        latency_ms = round((time.monotonic() - start) * 1000, 2)
        logger.warning("%sprobe_endpoint | TIMEOUT after %.1fms | url=%s", log_label, latency_ms, url)
        return ProbeResult(
            url=url,
            method=method,
            request_headers=dict(merged_headers),
            request_body=str(body) if body else None,
            status_code=-1,
            response_headers={},
            response_body="",
            latency_ms=latency_ms,
            success=False,
            error=f"Request timed out after {latency_ms:.0f}ms: {exc}",
        )

    except httpx.RequestError as exc:
        latency_ms = round((time.monotonic() - start) * 1000, 2)
        logger.warning("%sprobe_endpoint | NETWORK ERROR | url=%s | error=%s", log_label, url, exc)
        return ProbeResult(
            url=url,
            method=method,
            request_headers=dict(merged_headers),
            request_body=str(body) if body else None,
            status_code=-1,
            response_headers={},
            response_body="",
            latency_ms=latency_ms,
            success=False,
            error=f"Network error: {exc}",
        )


# ── Tool 2: fetch_cve_context ─────────────────────────────────────────────────

def fetch_cve_context(
    search_term: str,
    max_results: int = 5,
) -> CVEResult:
    """
    Query the NVD (National Vulnerability Database) API for CVEs matching a term.

    Used by the agent to enrich findings with real CVE data — e.g. searching
    "broken object level authorization API" returns real CVEs the report can cite.

    Args:
        search_term: Keyword or phrase to search. Use vulnerability type + context.
        max_results: Maximum CVEs to return. Capped at 10 to limit API load.

    Returns:
        CVEResult with matched CVE entries or error details if NVD is unavailable.
        Never raises — on failure returns error field set with explanation.

    Raises:
        ValueError: If search_term is empty or max_results is out of range.
    """
    if not search_term.strip():
        raise ValueError("search_term must not be empty.")

    max_results = min(max(1, max_results), 10)  # clamp to [1, 10]

    logger.info("fetch_cve_context | query='%s' | max=%d", search_term, max_results)

    try:
        client = _get_http_client()
        response = client.get(
            settings.nvd_base_url,
            params={
                "keywordSearch": search_term,
                "resultsPerPage": max_results,
                "startIndex": 0,
            },
            headers={"Accept": "application/json"},
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()

    except httpx.TimeoutException:
        logger.warning("fetch_cve_context | NVD API timed out | query='%s'", search_term)
        return CVEResult(
            query=search_term,
            total_found=0,
            entries=[],
            error="NVD API timed out. CVE context unavailable — report will proceed with OWASP knowledge only.",
        )

    except httpx.HTTPStatusError as exc:
        logger.warning(
            "fetch_cve_context | NVD API error | status=%d | query='%s'",
            exc.response.status_code,
            search_term,
        )
        return CVEResult(
            query=search_term,
            total_found=0,
            entries=[],
            error=f"NVD API returned HTTP {exc.response.status_code}. CVE context unavailable.",
        )

    except httpx.RequestError as exc:
        logger.warning("fetch_cve_context | NVD network error | error=%s", exc)
        return CVEResult(
            query=search_term,
            total_found=0,
            entries=[],
            error=f"NVD API unreachable: {exc}. CVE context unavailable.",
        )

    except Exception as exc:
        logger.error("fetch_cve_context | unexpected error | error=%s", exc, exc_info=True)
        return CVEResult(
            query=search_term,
            total_found=0,
            entries=[],
            error=f"Unexpected error querying NVD: {exc}",
        )

    # Parse NVD response
    vulnerabilities = data.get("vulnerabilities", [])
    total_results   = data.get("totalResults", 0)
    entries: list[CVEEntry] = []

    for item in vulnerabilities:
        cve = item.get("cve", {})
        cve_id = cve.get("id", "UNKNOWN")

        # Extract English description
        descriptions = cve.get("descriptions", [])
        description  = next(
            (d["value"] for d in descriptions if d.get("lang") == "en"),
            "No description available.",
        )

        # Extract CVSS score and severity
        metrics  = cve.get("metrics", {})
        cvss_score = 0.0
        severity   = "UNKNOWN"

        # Try CVSS v3.1 first, then v3.0, then v2
        for metric_key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            metric_list = metrics.get(metric_key, [])
            if metric_list:
                cvss_data  = metric_list[0].get("cvssData", {})
                cvss_score = float(cvss_data.get("baseScore", 0.0))
                severity   = cvss_data.get("baseSeverity", "UNKNOWN")
                break

        published = cve.get("published", "")[:10]  # ISO date, truncate to YYYY-MM-DD

        entries.append(CVEEntry(
            cve_id=cve_id,
            description=description[:500],  # truncate long descriptions
            severity=severity,
            cvss_score=cvss_score,
            published=published,
            reference=f"https://nvd.nist.gov/vuln/detail/{cve_id}",
        ))

    logger.info(
        "fetch_cve_context | total_in_nvd=%d | returned=%d | query='%s'",
        total_results,
        len(entries),
        search_term,
    )

    return CVEResult(
        query=search_term,
        total_found=total_results,
        entries=entries,
        error=None,
    )


# ── Tool 3: classify_finding ──────────────────────────────────────────────────

_CLASSIFICATION_SYSTEM_PROMPT = """
You are a senior penetration tester and AI security analyst at PentraceAI.
Your job is to analyse HTTP evidence from security probes and determine whether
a finding represents a real vulnerability or a false positive.

You reason step by step. You cite specific evidence from the HTTP exchanges.
You are precise — you do not speculate beyond the evidence provided.
You always provide a concrete remediation recommendation.

Respond ONLY in the following format — no preamble, no markdown:

VERDICT: <TRUE_POSITIVE|FALSE_POSITIVE|NEEDS_INVESTIGATION>
CONFIDENCE: <HIGH|MEDIUM|LOW>
OWASP_CATEGORY: <e.g. A01:2025 — Broken Access Control>
REASONING: <your step-by-step analysis citing specific HTTP evidence>
RECOMMENDED_FIX: <one concrete, actionable remediation step>
""".strip()


def classify_finding(
    finding_description: str,
    http_exchanges: list[dict[str, Any]],
    owasp_context: list[str],
    cve_context: list[str],
) -> ClassificationResult:
    """
    Use GPT-4.1-mini to classify a security finding as true positive or false positive.

    The LLM is given:
      - The finding description
      - Full HTTP request/response evidence
      - Relevant OWASP knowledge retrieved from ChromaDB
      - Relevant CVE context from NVD

    Args:
        finding_description: Human-readable description of what was tested.
        http_exchanges:      List of ProbeResult dicts from probe_endpoint calls.
        owasp_context:       List of OWASP knowledge chunks from retrieve_context().
        cve_context:         List of CVE description strings from fetch_cve_context().

    Returns:
        ClassificationResult with verdict, confidence, reasoning, and fix.

    Raises:
        RuntimeError: If the LLM API call fails after retries.
        ValueError:   If required inputs are empty.
    """
    if not finding_description.strip():
        raise ValueError("finding_description must not be empty.")
    if not http_exchanges:
        raise ValueError("http_exchanges must contain at least one probe result.")

    # Build the user prompt from evidence
    exchanges_text = ""
    for i, exchange in enumerate(http_exchanges, 1):
        exchanges_text += f"""
--- HTTP Exchange {i} ---
Method : {exchange.get('method', 'UNKNOWN')} {exchange.get('url', '')}
Status : {exchange.get('status_code', 'N/A')}
Request Headers: {exchange.get('request_headers', {})}
Request Body: {exchange.get('request_body', 'None')}
Response Body (truncated):
{exchange.get('response_body', '')[:1000]}
""".strip() + "\n\n"

    owasp_text = "\n\n".join(owasp_context) if owasp_context else "No OWASP context retrieved."
    cve_text   = "\n".join(cve_context) if cve_context else "No CVE context retrieved."

    user_prompt = f"""
FINDING DESCRIPTION:
{finding_description}

HTTP EVIDENCE:
{exchanges_text.strip()}

OWASP KNOWLEDGE BASE CONTEXT:
{owasp_text}

RELATED CVE CONTEXT:
{cve_text}

Analyse the HTTP evidence above and classify this finding.
""".strip()

    logger.info(
        "classify_finding | calling GPT-4.1-mini | exchanges=%d | owasp_chunks=%d | cves=%d",
        len(http_exchanges),
        len(owasp_context),
        len(cve_context),
    )

    client = _get_openai_client()

    try:
        response = client.chat.completions.create(
            model=settings.azure_openai_chat_deployment,
            messages=[
                {"role": "system", "content": _CLASSIFICATION_SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.1,   # low temperature — we want consistent, evidence-based reasoning
            max_tokens=1024,
        )
    except Exception as exc:
        raise RuntimeError(
            f"GPT-4.1-mini classification call failed. "
            f"Check Azure OpenAI endpoint and deployment name. "
            f"Original error: {exc}"
        ) from exc

    raw_response = response.choices[0].message.content or ""
    logger.info("classify_finding | LLM response received | tokens=%d", response.usage.total_tokens if response.usage else 0)

    # Parse structured response
    result = _parse_classification_response(raw_response)
    result["raw_llm_response"] = raw_response

    logger.info(
        "classify_finding | verdict=%s | confidence=%s | category=%s",
        result["verdict"],
        result["confidence"],
        result["owasp_category"],
    )

    return result


def _parse_classification_response(raw: str) -> ClassificationResult:
    """
    Parse the structured LLM response into a ClassificationResult.

    Defensive parsing — if any field is missing, uses safe defaults rather
    than crashing. The raw_llm_response field preserves the full output
    for audit regardless of parse quality.
    """
    lines = raw.strip().splitlines()
    parsed: dict[str, str] = {}

    # Multi-line fields accumulate into a buffer
    current_key: str | None = None
    buffer: list[str] = []

    for line in lines:
        if line.startswith("VERDICT:"):
            parsed["verdict"] = line.split(":", 1)[1].strip()
            current_key = None
        elif line.startswith("CONFIDENCE:"):
            parsed["confidence"] = line.split(":", 1)[1].strip()
            current_key = None
        elif line.startswith("OWASP_CATEGORY:"):
            parsed["owasp_category"] = line.split(":", 1)[1].strip()
            current_key = None
        elif line.startswith("REASONING:"):
            buffer = [line.split(":", 1)[1].strip()]
            current_key = "reasoning"
        elif line.startswith("RECOMMENDED_FIX:"):
            if current_key == "reasoning":
                parsed["reasoning"] = " ".join(buffer).strip()
            buffer = [line.split(":", 1)[1].strip()]
            current_key = "recommended_fix"
        elif current_key and line.strip():
            buffer.append(line.strip())

    # Flush final buffer
    if current_key and buffer:
        parsed[current_key] = " ".join(buffer).strip()

    # Validate and normalise verdict
    valid_verdicts = {"TRUE_POSITIVE", "FALSE_POSITIVE", "NEEDS_INVESTIGATION"}
    verdict = parsed.get("verdict", "NEEDS_INVESTIGATION").upper()
    if verdict not in valid_verdicts:
        logger.warning("classify_finding | unexpected verdict '%s' — defaulting to NEEDS_INVESTIGATION", verdict)
        verdict = "NEEDS_INVESTIGATION"

    valid_confidences = {"HIGH", "MEDIUM", "LOW"}
    confidence = parsed.get("confidence", "LOW").upper()
    if confidence not in valid_confidences:
        confidence = "LOW"

    return ClassificationResult(
        verdict=verdict,          # type: ignore[arg-type]
        confidence=confidence,    # type: ignore[arg-type]
        reasoning=parsed.get("reasoning", "Unable to parse reasoning from LLM response."),
        owasp_category=parsed.get("owasp_category", "Unknown"),
        recommended_fix=parsed.get("recommended_fix", "Review the HTTP evidence manually."),
        raw_llm_response="",  # caller sets this
    )


# ── Tool 4: check_fix_applied ─────────────────────────────────────────────────

def check_fix_applied(
    original_probe: ProbeResult,
    vulnerability_indicator: str,
    fixed_headers: dict[str, str] | None = None,
) -> FixCheckResult:
    """
    Re-probe an endpoint to confirm a vulnerability has been remediated.

    Replays the original probe and checks whether the vulnerability indicator
    is no longer present in the response.

    Args:
        original_probe:          The ProbeResult from the original vulnerable probe.
        vulnerability_indicator: A string that was present in the vulnerable response
                                 and should NOT be present after the fix.
                                 E.g. another user's email address or a private field.
        fixed_headers:           Optional replacement headers — e.g. a fixed auth token.

    Returns:
        FixCheckResult with fixed=True if the indicator is absent from the new response.

    Raises:
        ValueError: If vulnerability_indicator is empty.
    """
    if not vulnerability_indicator.strip():
        raise ValueError("vulnerability_indicator must not be empty.")

    logger.info(
        "check_fix_applied | re-probing %s | indicator='%s...'",
        original_probe["url"],
        vulnerability_indicator[:40],
    )

    new_probe = probe_endpoint(
        url=original_probe["url"],
        method=original_probe["method"],
        headers=fixed_headers or original_probe["request_headers"],
        label="fix-verification",
    )

    if not new_probe["success"]:
        return FixCheckResult(
            fixed=False,
            probe=new_probe,
            explanation=(
                f"Re-probe failed with network error: {new_probe['error']}. "
                f"Cannot confirm fix — manual verification required."
            ),
        )

    indicator_still_present = vulnerability_indicator.lower() in new_probe["response_body"].lower()

    if indicator_still_present:
        explanation = (
            f"VULNERABILITY STILL PRESENT. "
            f"The indicator '{vulnerability_indicator[:60]}' was found in the response body "
            f"after the fix was applied. HTTP status: {new_probe['status_code']}."
        )
        fixed = False
    else:
        explanation = (
            f"FIX CONFIRMED. "
            f"The indicator '{vulnerability_indicator[:60]}' is no longer present in the response. "
            f"HTTP status: {new_probe['status_code']}."
        )
        fixed = True

    logger.info(
        "check_fix_applied | fixed=%s | status=%d | indicator_present=%s",
        fixed,
        new_probe["status_code"],
        indicator_still_present,
    )

    return FixCheckResult(
        fixed=fixed,
        probe=new_probe,
        explanation=explanation,
    )

# ── generate_report ───────────────────────────────────────────────────────────

def generate_report(
    target_url: str,
    vulnerability_type: str,
    classification: ClassificationResult,
    http_exchanges: list[ProbeResult],
    cve_entries: list[CVEEntry],
    pipeline_errors: list[str],
    generated_at: str,
) -> dict[str, Any]:
    """
    Assemble the final structured pentest report from all pipeline outputs.

    No LLM call here — all reasoning was done in AnalysisAgent.
    This function purely structures the data into a report schema.

    Args:
        target_url:          The URL that was tested.
        vulnerability_type:  Human label for the vulnerability tested.
        classification:      Verdict, confidence, reasoning, fix from AnalysisAgent.
        http_exchanges:      Raw HTTP evidence from ReconAgent.
        cve_entries:         CVE records from NVD.
        pipeline_errors:     Any non-fatal errors from upstream agents.
        generated_at:        ISO 8601 timestamp of report generation.

    Returns:
        A fully structured report dict ready for display or JSON export.
    """
    import uuid

    verdict    = classification["verdict"]
    confidence = classification["confidence"]

    # Map verdict + confidence to a severity rating for the report header
    severity = _severity_from_verdict(verdict, confidence)

    report = {
        "report_id":          str(uuid.uuid4())[:8].upper(),
        "generated_at":       generated_at,
        "target_url":         target_url,
        "vulnerability_type": vulnerability_type,
        "severity":           severity,

        "finding": {
            "verdict":          verdict,
            "confidence":       confidence,
            "owasp_category":   classification["owasp_category"],
            "reasoning":        classification["reasoning"],
            "recommended_fix":  classification["recommended_fix"],
        },

        "evidence": {
            "http_exchanges": [
                {
                    "label":       ex.get("label", "unknown"),
                    "method":      ex.get("method", "GET"),
                    "url":         ex.get("url", target_url),
                    "status_code": ex.get("status_code"),
                    "latency_ms":  ex.get("latency_ms"),
                    "body_preview": (ex.get("response_body") or "")[:300],
                }
                for ex in http_exchanges
            ],
            "cve_references": [
                {
                    "cve_id":      cve["cve_id"],
                    "severity":    cve["severity"],
                    "cvss_score":  cve["cvss_score"],
                    "description": cve["description"][:200],
                    "reference":   cve.get("reference", ""),
                }
                for cve in cve_entries
            ],
        },

        "pipeline": {
            "agents_run":    ["ReconAgent", "AnalysisAgent", "ReportAgent"],
            "errors":        pipeline_errors,
            "clean_run":     len(pipeline_errors) == 0,
        },
    }

    logger.info(
        "generate_report | report_id=%s | severity=%s | verdict=%s | cves=%d | exchanges=%d",
        report["report_id"],
        severity,
        verdict,
        len(cve_entries),
        len(http_exchanges),
    )

    return report


def _severity_from_verdict(verdict: str, confidence: str) -> str:
    """Map verdict + confidence to a severity label for the report header."""
    if verdict == "TRUE_POSITIVE":
        return "HIGH" if confidence == "HIGH" else "MEDIUM"
    if verdict == "NEEDS_INVESTIGATION":
        return "MEDIUM"
    return "INFORMATIONAL"
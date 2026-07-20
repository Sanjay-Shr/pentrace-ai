"""
agent/knowledge.py
------------------
OWASP Top 10 2025 knowledge base for PentraceAI.

Responsibilities:
  1. Define structured OWASP Top 10 2025 entries as typed dicts
  2. Load them into ChromaDB at startup for semantic retrieval
  3. Expose a retrieval function the agent uses during investigation

Design principles:
  - Knowledge is versioned and sourced — every entry has an owasp_id and reference URL
  - ChromaDB collection is idempotent — safe to call load_knowledge() multiple times
  - Retrieval returns typed results — no loose dicts passed to the agent
  - All I/O errors are caught and re-raised with actionable messages
  - Embedding model is configurable via config.py — never hardcoded here
"""

from __future__ import annotations

import logging
from typing import TypedDict

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

from agent.config import settings, CHROMA_COLLECTION_NAME

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────────

class OWASPEntry(TypedDict):
    """A single OWASP Top 10 2025 entry."""
    owasp_id:    str   # e.g. "A01:2025"
    name:        str   # e.g. "Broken Access Control"
    description: str   # detailed description of the category
    examples:    str   # concrete attack examples
    prevention:  str   # how to prevent this class of vulnerability
    cwe_ids:     str   # related CWE identifiers as comma-separated string
    reference:   str   # canonical OWASP reference URL


class RetrievedChunk(TypedDict):
    """A single chunk returned by semantic search."""
    owasp_id:  str    # which OWASP category this chunk belongs to
    name:      str    # human-readable category name
    content:   str    # the retrieved text chunk
    distance:  float  # semantic distance — lower is more relevant


# ── OWASP Top 10 2025 Knowledge Base ─────────────────────────────────────────
# Source: https://owasp.org/www-project-top-ten/
# Each entry is split into description, examples, and prevention so ChromaDB
# can retrieve the most relevant section rather than the entire entry.

OWASP_TOP_10_2025: list[OWASPEntry] = [
    {
        "owasp_id":    "A01:2025",
        "name":        "Broken Access Control",
        "description": (
            "Broken Access Control occurs when restrictions on what authenticated "
            "users are allowed to do are not properly enforced. Attackers exploit "
            "these flaws to access unauthorised functionality or data, such as "
            "accessing other users' accounts, viewing sensitive files, modifying "
            "other users' data, or changing access rights. This is the most "
            "critical web application security risk in 2025."
        ),
        "examples": (
            "BOLA (Broken Object Level Authorization): An attacker changes the user "
            "ID in an API request from /api/users/123/profile to /api/users/124/profile "
            "and receives the victim's data without authorisation. "
            "Forced browsing: Accessing /admin/dashboard without being an admin. "
            "IDOR (Insecure Direct Object Reference): Changing an order ID in a URL "
            "to access another customer's order. "
            "Privilege escalation: A standard user accessing admin-only endpoints "
            "by modifying role parameters in requests."
        ),
        "prevention": (
            "Implement server-side access control checks on every request — never "
            "trust client-supplied IDs without verifying ownership. "
            "Use deny-by-default: unless a resource is explicitly public, deny access. "
            "Enforce record ownership: verify the authenticated user owns the requested "
            "resource before returning data. "
            "Log access control failures and alert on repeated failures. "
            "Invalidate JWT tokens on the server side after logout."
        ),
        "cwe_ids":   "CWE-22, CWE-284, CWE-285, CWE-639",
        "reference": "https://owasp.org/Top10/A01_2021-Broken_Access_Control/",
    },
    {
        "owasp_id":    "A02:2025",
        "name":        "Cryptographic Failures",
        "description": (
            "Cryptographic Failures (formerly Sensitive Data Exposure) covers failures "
            "related to cryptography that often lead to exposure of sensitive data. "
            "This includes transmitting data in cleartext, using weak or outdated "
            "cryptographic algorithms, improper key management, and failure to enforce "
            "encryption. Sensitive data includes passwords, credit card numbers, health "
            "records, personal information, and business secrets."
        ),
        "examples": (
            "Transmitting passwords or session tokens over HTTP instead of HTTPS. "
            "Storing passwords using weak hashing algorithms like MD5 or SHA1 without salting. "
            "Using deprecated protocols such as SSL, TLS 1.0, or TLS 1.1. "
            "Encrypting data with ECB mode which is deterministic and leaks patterns. "
            "Hardcoding encryption keys in source code or configuration files."
        ),
        "prevention": (
            "Classify data processed, stored, or transmitted and apply controls based on sensitivity. "
            "Do not store sensitive data unnecessarily — discard it as soon as possible. "
            "Encrypt all data at rest and in transit using strong, current algorithms. "
            "Use bcrypt, scrypt, or Argon2 for password hashing — never MD5 or SHA1. "
            "Enforce HTTPS everywhere and use HSTS headers. "
            "Store keys separately from encrypted data and rotate them regularly."
        ),
        "cwe_ids":   "CWE-259, CWE-327, CWE-331",
        "reference": "https://owasp.org/Top10/A02_2021-Cryptographic_Failures/",
    },
    {
        "owasp_id":    "A03:2025",
        "name":        "Injection",
        "description": (
            "Injection flaws occur when untrusted data is sent to an interpreter as "
            "part of a command or query. SQL injection, NoSQL injection, OS command "
            "injection, LDAP injection, and prompt injection in LLM applications are "
            "all forms of this vulnerability. An attacker can use injection to read, "
            "modify, or delete data, execute commands, or bypass authentication entirely."
        ),
        "examples": (
            "SQL injection: SELECT * FROM users WHERE username = '' OR '1'='1' -- "
            "bypasses authentication by always evaluating to true. "
            "Command injection: A filename field accepts '; rm -rf /' and the server "
            "executes it as a shell command. "
            "Prompt injection in LLM APIs: A user input overrides system instructions "
            "causing the model to reveal confidential data or take unintended actions. "
            "NoSQL injection: Passing {'$gt': ''} as a MongoDB query parameter to "
            "bypass authentication."
        ),
        "prevention": (
            "Use parameterised queries and prepared statements — never concatenate "
            "user input into queries or commands. "
            "Use an ORM with query binding rather than raw string queries. "
            "Validate and sanitise all user input on the server side. "
            "Apply the principle of least privilege to database accounts. "
            "For LLM applications: separate system instructions from user input, "
            "validate model outputs before acting on them."
        ),
        "cwe_ids":   "CWE-77, CWE-89, CWE-564",
        "reference": "https://owasp.org/Top10/A03_2021-Injection/",
    },
    {
        "owasp_id":    "A04:2025",
        "name":        "Insecure Design",
        "description": (
            "Insecure Design refers to missing or ineffective security controls that "
            "result from design decisions made before code is written. Unlike "
            "implementation bugs, insecure design cannot be fixed by a perfect "
            "implementation — the architecture itself is flawed. This includes "
            "missing threat modelling, insecure business logic, and failure to "
            "design for security from the start."
        ),
        "examples": (
            "A password reset flow that uses security questions — easily guessable "
            "or researchable answers mean any account can be taken over. "
            "A cinema booking system that allows bulk seat reservations with no "
            "deposit, enabling scalpers to hold all seats and release them last-minute. "
            "An API that returns the full user object including password hash and "
            "internal flags when only the display name was requested. "
            "Multi-tenant SaaS that stores all customer data in one database with "
            "no logical separation between tenants."
        ),
        "prevention": (
            "Establish a secure development lifecycle with security requirements "
            "defined before implementation begins. "
            "Use threat modelling for every significant feature — identify what "
            "could go wrong before writing code. "
            "Apply the principle of least privilege in system design. "
            "Design for failure — assume components will be compromised and limit "
            "the blast radius. "
            "Engage security specialists during architecture review."
        ),
        "cwe_ids":   "CWE-73, CWE-183, CWE-209",
        "reference": "https://owasp.org/Top10/A04_2021-Insecure_Design/",
    },
    {
        "owasp_id":    "A05:2025",
        "name":        "Security Misconfiguration",
        "description": (
            "Security Misconfiguration is the most commonly seen vulnerability. "
            "It results from insecure default configurations, incomplete configurations, "
            "open cloud storage, misconfigured HTTP headers, verbose error messages "
            "exposing stack traces, unnecessary features enabled, and default credentials "
            "left unchanged. With the rise of cloud infrastructure and microservices, "
            "misconfiguration risk has increased significantly."
        ),
        "examples": (
            "Default admin credentials (admin/admin) left unchanged on a production system. "
            "A cloud storage bucket configured as publicly readable exposing customer data. "
            "Stack traces returned in API error responses revealing internal architecture. "
            "CORS configured with wildcard (*) allowing any origin to make credentialed requests. "
            "Unnecessary HTTP methods (PUT, DELETE, TRACE) enabled on production endpoints. "
            "Debug mode enabled in a production web framework."
        ),
        "prevention": (
            "Implement a repeatable hardening process for all environments. "
            "Remove or disable all unused features, components, and services. "
            "Review and update security configurations as part of every deployment. "
            "Use automated scanning to detect misconfiguration in cloud and application layers. "
            "Return generic error messages to clients — log detailed errors server-side only. "
            "Set security headers: Content-Security-Policy, X-Frame-Options, HSTS."
        ),
        "cwe_ids":   "CWE-2, CWE-16, CWE-388",
        "reference": "https://owasp.org/Top10/A05_2021-Security_Misconfiguration/",
    },
    {
        "owasp_id":    "A06:2025",
        "name":        "Vulnerable and Outdated Components",
        "description": (
            "Vulnerable and Outdated Components covers the risk of using software "
            "components with known vulnerabilities. This includes libraries, frameworks, "
            "and other modules used in applications. Attackers can exploit known "
            "vulnerabilities in components to attack systems that have not been patched. "
            "The Log4Shell vulnerability (CVE-2021-44228) is a prominent example that "
            "affected millions of systems worldwide."
        ),
        "examples": (
            "Running a web framework version with a known remote code execution CVE "
            "because the team has not updated dependencies in 18 months. "
            "Using an npm package with a known prototype pollution vulnerability. "
            "Running an end-of-life operating system that no longer receives security patches. "
            "Including a JavaScript library via CDN without subresource integrity checks, "
            "allowing a compromised CDN to serve malicious code."
        ),
        "prevention": (
            "Maintain an inventory of all components and their versions. "
            "Continuously monitor CVE databases and security advisories for used components. "
            "Remove unused dependencies, features, and files. "
            "Use software composition analysis (SCA) tools in CI/CD pipelines. "
            "Subscribe to security bulletins for components you depend on. "
            "Apply patches on a defined schedule — critical CVEs within 24-48 hours."
        ),
        "cwe_ids":   "CWE-937, CWE-1035, CWE-1104",
        "reference": "https://owasp.org/Top10/A06_2021-Vulnerable_and_Outdated_Components/",
    },
    {
        "owasp_id":    "A07:2025",
        "name":        "Identification and Authentication Failures",
        "description": (
            "Identification and Authentication Failures occur when functions related "
            "to user identity, authentication, and session management are implemented "
            "incorrectly. Attackers can exploit these weaknesses to assume other users' "
            "identities temporarily or permanently. This includes weak passwords, "
            "credential stuffing, brute force attacks, session fixation, and improper "
            "token validation."
        ),
        "examples": (
            "An API endpoint accepts any Bearer token without validating the signature, "
            "expiry, or issuer — allowing an attacker to forge tokens. "
            "A login endpoint with no rate limiting allows credential stuffing attacks "
            "testing millions of username/password combinations. "
            "Session tokens that do not expire, allowing an attacker who captures a "
            "token to use it indefinitely. "
            "JWT tokens validated only on the client side — the server accepts any "
            "token without verification. "
            "Weak default passwords that users are never prompted to change."
        ),
        "prevention": (
            "Implement multi-factor authentication where possible. "
            "Do not ship default credentials — force credential creation on first use. "
            "Implement rate limiting and account lockout on authentication endpoints. "
            "Validate JWT tokens server-side: check signature, expiry, issuer, and audience. "
            "Use short-lived session tokens and invalidate them on logout. "
            "Log authentication failures and alert on patterns indicating brute force."
        ),
        "cwe_ids":   "CWE-297, CWE-287, CWE-384",
        "reference": "https://owasp.org/Top10/A07_2021-Identification_and_Authentication_Failures/",
    },
    {
        "owasp_id":    "A08:2025",
        "name":        "Software and Data Integrity Failures",
        "description": (
            "Software and Data Integrity Failures relate to code and infrastructure "
            "that does not protect against integrity violations. This includes insecure "
            "CI/CD pipelines, auto-update mechanisms without integrity verification, "
            "deserialisation of untrusted data, and supply chain attacks. The SolarWinds "
            "attack is a real-world example where a build pipeline was compromised to "
            "distribute malicious updates to thousands of organisations."
        ),
        "examples": (
            "An application deserialises a base64-encoded object from a cookie without "
            "verifying its integrity, allowing an attacker to craft a malicious payload. "
            "A CI/CD pipeline pulls dependencies directly from public registries without "
            "pinning versions or verifying checksums. "
            "An auto-update mechanism downloads and executes updates over HTTP without "
            "signature verification. "
            "A plugin system loads and executes code from untrusted sources without sandboxing."
        ),
        "prevention": (
            "Use digital signatures to verify software and data integrity. "
            "Pin dependency versions and verify checksums in CI/CD pipelines. "
            "Use trusted repositories and consider a private mirror for critical dependencies. "
            "Review CI/CD pipeline configuration for unauthorised access and changes. "
            "Never deserialise data from untrusted sources without validation and integrity checks. "
            "Implement code review gates that prevent unreviewed code from reaching production."
        ),
        "cwe_ids":   "CWE-494, CWE-502, CWE-345",
        "reference": "https://owasp.org/Top10/A08_2021-Software_and_Data_Integrity_Failures/",
    },
    {
        "owasp_id":    "A09:2025",
        "name":        "Security Logging and Monitoring Failures",
        "description": (
            "Security Logging and Monitoring Failures occur when systems do not "
            "generate adequate logs, logs are not monitored, or alerts are not acted "
            "upon. Without sufficient logging and monitoring, breaches cannot be "
            "detected. The average time to detect a breach is over 200 days — largely "
            "because logging and monitoring are insufficient. Attackers exploit this "
            "by operating slowly and quietly within systems."
        ),
        "examples": (
            "Authentication failures are not logged, so credential stuffing attacks "
            "go undetected for months. "
            "Logs are stored only locally on application servers — when the server is "
            "compromised, the attacker deletes the logs. "
            "A web application firewall is in detection mode but alerts are never reviewed. "
            "API access logs do not include the authenticated user ID, making forensic "
            "investigation impossible after a data breach."
        ),
        "prevention": (
            "Log all authentication events, access control failures, and input validation failures. "
            "Include sufficient context in logs: user ID, IP address, timestamp, action, outcome. "
            "Ship logs to a centralised, tamper-resistant system separate from application servers. "
            "Implement alerting on suspicious patterns: repeated failures, unusual access times, "
            "bulk data access. "
            "Establish and test an incident response plan. "
            "Use structured logging (JSON) so logs can be queried programmatically."
        ),
        "cwe_ids":   "CWE-117, CWE-223, CWE-532",
        "reference": "https://owasp.org/Top10/A09_2021-Security_Logging_and_Monitoring_Failures/",
    },
    {
        "owasp_id":    "A10:2025",
        "name":        "Server-Side Request Forgery",
        "description": (
            "Server-Side Request Forgery (SSRF) flaws occur when a web application "
            "fetches a remote resource based on a user-supplied URL without validating "
            "it. An attacker can force the server to make requests to internal services, "
            "cloud metadata endpoints, or other unintended destinations. SSRF is "
            "particularly dangerous in cloud environments where the metadata service "
            "at 169.254.169.254 can expose credentials and configuration."
        ),
        "examples": (
            "An image import feature accepts a URL and fetches it server-side — an "
            "attacker supplies http://169.254.169.254/latest/meta-data/iam/security-credentials/ "
            "to steal AWS IAM credentials. "
            "A webhook configuration accepts any URL — an attacker points it at an "
            "internal admin API that is not exposed externally. "
            "A PDF generation service fetches resources by URL — an attacker uses "
            "file:// URLs to read server configuration files."
        ),
        "prevention": (
            "Validate and sanitise all user-supplied URLs before making server-side requests. "
            "Use an allowlist of permitted domains and protocols — deny everything else. "
            "Block requests to private IP ranges: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, "
            "169.254.169.254. "
            "Disable HTTP redirects in server-side HTTP clients. "
            "Use network segmentation to limit what internal services the application server "
            "can reach. "
            "In cloud environments, use IMDSv2 which requires a session token."
        ),
        "cwe_ids":   "CWE-918",
        "reference": "https://owasp.org/Top10/A10_2021-Server-Side_Request_Forgery_%28SSRF%29/",
    },
]


# ── ChromaDB client (module-level singleton) ──────────────────────────────────
# ponytail: in-process persistent client — use HttpClient if scaling to multiple workers

_chroma_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None


def _get_embedding_function() -> OpenAIEmbeddingFunction:
    """
    Build the ChromaDB-compatible embedding function using Azure OpenAI.

    Returns:
        A configured OpenAIEmbeddingFunction instance.
    """
    return OpenAIEmbeddingFunction(
        api_key=settings.azure_openai_api_key,
        api_base=settings.azure_openai_endpoint,
        api_type="azure",
        api_version=settings.azure_openai_api_version,
        model_name=settings.azure_openai_embedding_deployment,
        deployment_id=settings.azure_openai_embedding_deployment,
    )


def _get_collection() -> chromadb.Collection:
    """
    Return the ChromaDB collection, initialising the client if needed.

    Uses a module-level singleton so the client is created once per process.

    Returns:
        The ChromaDB collection for OWASP knowledge.

    Raises:
        RuntimeError: If ChromaDB fails to initialise.
    """
    global _chroma_client, _collection

    if _collection is not None:
        return _collection

    try:
        _chroma_client = chromadb.PersistentClient(path=".chroma")
        _collection = _chroma_client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            embedding_function=_get_embedding_function(),
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "ChromaDB collection '%s' ready | documents=%d",
            CHROMA_COLLECTION_NAME,
            _collection.count(),
        )
        return _collection

    except Exception as exc:
        raise RuntimeError(
            f"Failed to initialise ChromaDB at path '.chroma'. "
            f"Ensure chromadb is installed and the path is writable. "
            f"Original error: {exc}"
        ) from exc


# ── Public API ────────────────────────────────────────────────────────────────

def load_knowledge(force_reload: bool = False) -> int:
    """
    Load OWASP Top 10 2025 entries into ChromaDB.

    Idempotent — safe to call multiple times. Skips entries that already
    exist unless force_reload=True. Each entry is split into three documents
    (description, examples, prevention) so retrieval returns the most
    relevant section rather than the full entry.

    Args:
        force_reload: If True, deletes all existing documents and reloads
                      from scratch. Use when knowledge content has changed.

    Returns:
        The total number of documents now in the collection.

    Raises:
        RuntimeError: If ChromaDB is unavailable or write fails.
    """
    collection = _get_collection()

    if force_reload:
        logger.info("force_reload=True — clearing existing knowledge base")
        collection.delete(where={"source": "owasp_top10_2025"})

    existing_count = collection.count()
    if existing_count > 0 and not force_reload:
        logger.info(
            "Knowledge base already loaded (%d documents) — skipping reload. "
            "Pass force_reload=True to refresh.",
            existing_count,
        )
        return existing_count

    documents: list[str] = []
    metadatas: list[dict] = []
    ids: list[str] = []

    for entry in OWASP_TOP_10_2025:
        owasp_id = entry["owasp_id"]
        name     = entry["name"]

        # Split each entry into three retrievable chunks
        sections = [
            ("description", entry["description"]),
            ("examples",    entry["examples"]),
            ("prevention",  entry["prevention"]),
        ]

        for section_name, content in sections:
            doc_id = f"{owasp_id}_{section_name}"
            documents.append(content)
            metadatas.append({
                "owasp_id":  owasp_id,
                "name":      name,
                "section":   section_name,
                "cwe_ids":   entry["cwe_ids"],
                "reference": entry["reference"],
                "source":    "owasp_top10_2025",
            })
            ids.append(doc_id)

    try:
        collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
        total = collection.count()
        logger.info(
            "Knowledge base loaded | entries=%d | documents=%d",
            len(OWASP_TOP_10_2025),
            total,
        )
        return total

    except Exception as exc:
        raise RuntimeError(
            f"Failed to upsert OWASP knowledge into ChromaDB. "
            f"Original error: {exc}"
        ) from exc


def retrieve_context(
    query: str,
    n_results: int = 3,
    owasp_id_filter: str | None = None,
) -> list[RetrievedChunk]:
    """
    Retrieve the most semantically relevant OWASP knowledge chunks for a query.

    Args:
        query:           The search query — typically the finding description
                         or a specific vulnerability question.
        n_results:       Number of chunks to return. Defaults to 3.
        owasp_id_filter: If provided, restricts results to a specific OWASP
                         category e.g. "A01:2025". Use when the finding type
                         is already known.

    Returns:
        A list of RetrievedChunk dicts ordered by relevance (most relevant first).
        Returns an empty list if the knowledge base is empty.

    Raises:
        RuntimeError: If ChromaDB query fails.
        ValueError:   If query is empty or n_results is less than 1.
    """
    if not query.strip():
        raise ValueError("query must not be empty.")

    if n_results < 1:
        raise ValueError(f"n_results must be at least 1. Got: {n_results}")

    collection = _get_collection()

    if collection.count() == 0:
        logger.warning(
            "retrieve_context called but knowledge base is empty. "
            "Call load_knowledge() first."
        )
        return []

    if owasp_id_filter:
        where_filter: dict = {
            "$and": [
                {"source": {"$eq": "owasp_top10_2025"}},
                {"owasp_id": {"$eq": owasp_id_filter}},
            ]
        }
    else:
        where_filter: dict = {"source": {"$eq": "owasp_top10_2025"}}

    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as exc:
        raise RuntimeError(
            f"ChromaDB query failed for query='{query[:80]}...'. "
            f"Original error: {exc}"
        ) from exc

    chunks: list[RetrievedChunk] = []

    documents  = results.get("documents") or [[]]
    metadatas  = results.get("metadatas") or [[]]
    distances  = results.get("distances") or [[]]

    for doc, meta, dist in zip(documents[0], metadatas[0], distances[0]):
        chunks.append(RetrievedChunk(
            owasp_id  = meta.get("owasp_id", ""),
            name      = meta.get("name", ""),
            content   = doc,
            distance  = round(float(dist), 4),
        ))

    logger.info(
        "Retrieved %d chunks for query='%s...' | filter=%s",
        len(chunks),
        query[:40],
        owasp_id_filter or "none",
    )

    return chunks
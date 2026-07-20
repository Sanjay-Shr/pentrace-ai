import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")

from agent.analysis_agent import analysis_graph

# Simulate what ReconAgent would hand off after a BOLA probe
# Using realistic probe results that show a vulnerability
mock_state = {
    # Recon fields
    "target_url":         "http://localhost:8001/api/users/2/profile",
    "vulnerability_type": "BOLA",
    "attacker_headers":   {"Authorization": "Bearer user1-token"},
    "legitimate_headers": {"Authorization": "Bearer user2-token"},
    "cve_search_term":    "broken object level authorization API",
    "recon_complete":     True,
    "recon_errors":       [],

    # Simulated attacker probe — got victim's data (this is the vulnerability)
    "attacker_probe": {
        "url":              "http://localhost:8001/api/users/2/profile",
        "method":           "GET",
        "request_headers":  {"Authorization": "Bearer user1-token"},
        "request_body":     None,
        "status_code":      200,
        "response_headers": {"content-type": "application/json"},
        "response_body":    '{"id": 2, "email": "victim@example.com", "name": "Victim User", "role": "user"}',
        "latency_ms":       45.2,
        "success":          True,
        "error":            None,
    },

    # Simulated legitimate probe — same endpoint, same 200 but own data
    "legitimate_probe": {
        "url":              "http://localhost:8001/api/users/2/profile",
        "method":           "GET",
        "request_headers":  {"Authorization": "Bearer user2-token"},
        "request_body":     None,
        "status_code":      200,
        "response_headers": {"content-type": "application/json"},
        "response_body":    '{"id": 2, "email": "victim@example.com", "name": "Victim User", "role": "user"}',
        "latency_ms":       12.1,
        "success":          True,
        "error":            None,
    },

    # Simulated CVE result
    "cve_result": {
        "query":       "broken object level authorization API",
        "total_found": 5,
        "error":       None,
        "entries": [
            {
                "cve_id":      "CVE-2025-63783",
                "description": "A Broken Object Level Authorization (BOLA) vulnerability was discovered allowing unauthorized access to other users' data via manipulated API object IDs.",
                "severity":    "HIGH",
                "cvss_score":  7.6,
                "published":   "2025-06-01",
                "reference":   "https://nvd.nist.gov/vuln/detail/CVE-2025-63783",
            },
        ],
    },

    # Analysis fields (to be populated)
    "owasp_chunks":      [],
    "classification":    None,
    "analysis_complete": False,
    "analysis_errors":   [],
}

print("=== Running AnalysisAgent ===")
final_state = analysis_graph.invoke(mock_state)

print(f"\n  analysis_complete : {final_state['analysis_complete']}")
print(f"  analysis_errors   : {final_state['analysis_errors']}")
print(f"  owasp_chunks      : {len(final_state['owasp_chunks'])} retrieved")

if final_state["classification"]:
    c = final_state["classification"]
    print(f"\n  verdict           : {c['verdict']}")
    print(f"  confidence        : {c['confidence']}")
    print(f"  owasp_category    : {c['owasp_category']}")
    print(f"\n  reasoning         :")
    print(f"    {c['reasoning'][:300]}...")
    print(f"\n  recommended_fix   :")
    print(f"    {c['recommended_fix']}")

print("\nanalysis_agent.py OK")
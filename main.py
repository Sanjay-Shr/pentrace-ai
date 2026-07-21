"""
main.py
-------
PentraceAI — CLI entry point.

Usage:
    python main.py                        # runs default scenario: bola
    python main.py --scenario bola
    python main.py --scenario broken_auth
    python main.py --scenario false_positive
    python main.py --list                 # list available scenarios
    python main.py --json                 # output full report as JSON
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from agent.orchestrator import SCAN_SCENARIOS, run_scan

# ── Logging ───────────────────────────────────────────────────────────────────
# INFO by default — use --debug for full trace
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── CLI ───────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pentrace-ai",
        description="PentraceAI — Agentic API vulnerability scanner with OWASP RAG + CVE correlation.",
    )
    parser.add_argument(
        "--scenario",
        choices=list(SCAN_SCENARIOS.keys()),
        default="bola",
        help="Scan scenario to run (default: bola)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available scan scenarios and exit",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full report as JSON after the scan",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable DEBUG logging for full pipeline trace",
    )
    return parser


def print_banner() -> None:
    print("""
╔══════════════════════════════════════════════════════════════╗
║              PentraceAI — Agentic Vulnerability Scanner      ║
║      ReconAgent → AnalysisAgent → ReportAgent                ║
║      OWASP Top 10 2025 · Azure OpenAI · NVD CVE Correlation  ║
╚══════════════════════════════════════════════════════════════╝
""")


def print_report(report: dict) -> None:
    """Print a human-readable report summary to stdout."""

    verdict   = report["finding"]["verdict"]
    severity  = report["severity"]
    confidence = report["finding"]["confidence"]

    # Severity color indicators (terminal-friendly)
    severity_icon = {
        "HIGH":          "🔴",
        "MEDIUM":        "🟡",
        "INFORMATIONAL": "🟢",
    }.get(severity, "⚪")

    verdict_icon = {
        "TRUE_POSITIVE":       "⚠️ ",
        "FALSE_POSITIVE":      "✅",
        "NEEDS_INVESTIGATION": "🔍",
    }.get(verdict, "❓")

    print(f"  {'─'*58}")
    print(f"  Report ID      : {report['report_id']}")
    print(f"  Generated      : {report['generated_at']}")
    print(f"  Target         : {report['target_url']}")
    print(f"  Vuln Type      : {report['vulnerability_type']}")
    print(f"  {'─'*58}")
    print(f"  Verdict        : {verdict_icon} {verdict}")
    print(f"  Severity       : {severity_icon} {severity}")
    print(f"  Confidence     : {confidence}")
    print(f"  OWASP Category : {report['finding']['owasp_category']}")
    print(f"  {'─'*58}")
    print(f"\n  Reasoning:")
    # Word-wrap reasoning at 60 chars
    reasoning = report["finding"]["reasoning"]
    words = reasoning.split()
    line, lines = [], []
    for word in words:
        if sum(len(w) + 1 for w in line) + len(word) > 60:
            lines.append("    " + " ".join(line))
            line = [word]
        else:
            line.append(word)
    if line:
        lines.append("    " + " ".join(line))
    print("\n".join(lines))

    print(f"\n  Recommended Fix:")
    fix = report["finding"]["recommended_fix"]
    fix_words = fix.split()
    line, lines = [], []
    for word in fix_words:
        if sum(len(w) + 1 for w in line) + len(word) > 60:
            lines.append("    " + " ".join(line))
            line = [word]
        else:
            line.append(word)
    if line:
        lines.append("    " + " ".join(line))
    print("\n".join(lines))

    print(f"\n  {'─'*58}")
    print(f"  HTTP Evidence  : {len(report['evidence']['http_exchanges'])} exchanges recorded")
    for ex in report["evidence"]["http_exchanges"]:
        print(f"    [{ex['label']}] {ex['method']} {ex['url']} → {ex['status_code']} ({ex['latency_ms']}ms)")

    if report["evidence"]["cve_references"]:
        print(f"\n  CVE References : {len(report['evidence']['cve_references'])} found")
        for cve in report["evidence"]["cve_references"]:
            print(f"    [{cve['cve_id']}] {cve['severity']} CVSS {cve['cvss_score']}")
    else:
        print(f"\n  CVE References : none found for this query")

    print(f"\n  Pipeline       : {' → '.join(report['pipeline']['agents_run'])}")
    print(f"  Clean Run      : {'✅ Yes' if report['pipeline']['clean_run'] else '❌ No'}")
    if report["pipeline"]["errors"]:
        print(f"  Errors         :")
        for err in report["pipeline"]["errors"]:
            print(f"    - {err}")
    print(f"  {'─'*58}\n")


def main() -> int:
    parser = build_parser()
    args   = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    print_banner()

    # ── --list ────────────────────────────────────────────────────────────────
    if args.list:
        print("  Available scenarios:\n")
        for key, config in SCAN_SCENARIOS.items():
            print(f"    --scenario {key:<16} {config['label']}")
        print()
        return 0

    # ── Run scan ──────────────────────────────────────────────────────────────
    scenario = args.scenario
    print(f"  Running scenario : {SCAN_SCENARIOS[scenario]['label']}")
    print(f"  Target           : {SCAN_SCENARIOS[scenario]['target_url']}\n")

    try:
        final_state = run_scan(scenario=scenario)
    except Exception as exc:
        logger.error("Pipeline crashed | error=%s", exc, exc_info=True)
        print(f"\n  ❌ Pipeline failed: {exc}")
        return 1

    report = final_state.get("report")

    if not report:
        print(f"\n  ❌ No report generated.")
        print(f"  Errors: {final_state.get('report_errors', [])}")
        return 1

    # ── Print human-readable summary ──────────────────────────────────────────
    print_report(report)

    # ── --json ────────────────────────────────────────────────────────────────
    if args.json:
        print("  Full JSON Report:")
        print("  " + "─"*58)
        print(json.dumps(report, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
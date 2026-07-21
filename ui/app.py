# # # # """
# # # # ui/app.py — PentraceAI Streamlit UI
# # # # Run: streamlit run ui/app.py
# # # # """

# # # # from __future__ import annotations

# # # # import re
# # # # import sys
# # # # import os

# # # # sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# # # # import streamlit as st
# # # # from agent.orchestrator import SCAN_SCENARIOS, run_scan_streaming

# # # # st.set_page_config(
# # # #     page_title="PentraceAI",
# # # #     page_icon="🔐",
# # # #     layout="wide",
# # # #     initial_sidebar_state="collapsed",
# # # # )

# # # # # ─────────────────────────────────────────────────────────────────────────────
# # # # # CONSTANTS — every style is inline, zero CSS classes
# # # # # ─────────────────────────────────────────────────────────────────────────────

# # # # S_PANEL = (
# # # #     "background:#161b22;border:1px solid #30363d;border-radius:8px;"
# # # #     "padding:12px 14px;height:440px;overflow-y:auto;"
# # # #     "font-family:'Courier New',monospace;font-size:13px;color:#c9d1d9;"
# # # #     "display:block;"
# # # # )
# # # # S_PANEL_TITLE = (
# # # #     "font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;"
# # # #     "color:#58a6ff;border-bottom:1px solid #30363d;padding-bottom:6px;"
# # # #     "margin-bottom:10px;display:block;"
# # # # )
# # # # S_REPORT = (
# # # #     "background:#161b22;border:1px solid #30363d;border-radius:8px;"
# # # #     "padding:14px 18px;height:540px;overflow-y:auto;"
# # # #     "font-family:-apple-system,BlinkMacSystemFont,sans-serif;"
# # # #     "font-size:13px;color:#c9d1d9;margin-top:16px;display:block;"
# # # # )
# # # # S_HTTP_BLOCK = (
# # # #     "background:#0d1117;border-left:3px solid #58a6ff;"
# # # #     "border-radius:4px;padding:7px 10px;margin:5px 0;display:block;"
# # # # )
# # # # S_CARD = (
# # # #     "background:#0d1117;border:1px solid #30363d;border-radius:6px;"
# # # #     "padding:8px 14px;min-width:120px;display:inline-block;margin:4px;"
# # # # )
# # # # S_LBOX = (
# # # #     "background:#0d1117;border-left:3px solid #58a6ff;border-radius:4px;"
# # # #     "padding:10px 14px;line-height:1.6;font-size:13px;color:#c9d1d9;"
# # # #     "display:block;margin:4px 0 8px;"
# # # # )
# # # # S_RBOX = S_LBOX.replace("#58a6ff", "#3fb950")
# # # # S_SEC  = (
# # # #     "font-size:10px;font-weight:700;color:#8b8fa8;text-transform:uppercase;"
# # # #     "letter-spacing:.08em;margin:12px 0 4px;display:block;"
# # # # )
# # # # S_CODE = (
# # # #     "background:#1f2937;padding:1px 5px;border-radius:3px;"
# # # #     "color:#79c0ff;font-family:monospace;font-size:12px;"
# # # # )

# # # # def _c(text: str) -> str:
# # # #     """Wrap backtick spans as inline-styled code."""
# # # #     return re.sub(
# # # #         r"`([^`]+)`",
# # # #         rf'<code style="{S_CODE}">\1</code>',
# # # #         text,
# # # #     )

# # # # def _hcol(status: int) -> str:
# # # #     if status < 300: return "#3fb950"
# # # #     if status < 400: return "#d29922"
# # # #     return "#f85149"

# # # # # ─────────────────────────────────────────────────────────────────────────────
# # # # # HTML BUILDERS — return strings for st.empty().markdown(unsafe_allow_html=True)
# # # # # ─────────────────────────────────────────────────────────────────────────────

# # # # def _reasoning_html(lines: list[str]) -> str:
# # # #     if not lines:
# # # #         body = f'<span style="color:#555">Click ▶ Run Scan to start...</span>'
# # # #     else:
# # # #         body = "".join(
# # # #             f'<div style="line-height:1.7;padding:1px 0">{ln}</div>'
# # # #             for ln in lines
# # # #         )
# # # #     return (
# # # #         f'<div style="{S_PANEL}">'
# # # #         f'<span style="{S_PANEL_TITLE}">🧠 Agent Reasoning</span>'
# # # #         f'{body}'
# # # #         f'</div>'
# # # #     )


# # # # def _traffic_html(exchanges: list[dict]) -> str:
# # # #     if not exchanges:
# # # #         body = '<span style="color:#555">Waiting for probes...</span>'
# # # #     else:
# # # #         parts = []
# # # #         for ex in exchanges:
# # # #             label  = ex.get("label", "unknown")
# # # #             method = ex.get("method", "GET")
# # # #             url    = ex.get("url", "").replace("http://localhost:8001", "")
# # # #             status = ex.get("status_code", 0)
# # # #             ms     = ex.get("latency_ms", 0)
# # # #             body_t = ex.get("body_preview", "")[:80]
# # # #             col    = _hcol(status)
# # # #             parts.append(
# # # #                 f'<div style="{S_HTTP_BLOCK}">'
# # # #                 f'<div style="color:#79c0ff">→ [{label}] {method} {url}</div>'
# # # #                 f'<div style="color:{col}">← {status} ({ms}ms)</div>'
# # # #                 f'<div style="color:#8b8fa8;font-size:11px;margin-top:2px">{body_t}</div>'
# # # #                 f'</div>'
# # # #             )
# # # #         body = "".join(parts)
# # # #     return (
# # # #         f'<div style="{S_PANEL}">'
# # # #         f'<span style="{S_PANEL_TITLE}">📡 Live HTTP Traffic</span>'
# # # #         f'{body}'
# # # #         f'</div>'
# # # #     )


# # # # def _report_html(report: dict) -> str:
# # # #     verdict    = report["finding"]["verdict"]
# # # #     severity   = report["severity"]
# # # #     confidence = report["finding"]["confidence"]
# # # #     category   = report["finding"]["owasp_category"]
# # # #     reasoning  = report["finding"]["reasoning"]
# # # #     fix        = report["finding"]["recommended_fix"]
# # # #     cves       = report["evidence"]["cve_references"]
# # # #     ex_list    = report["evidence"]["http_exchanges"]
# # # #     clean      = report["pipeline"]["clean_run"]
# # # #     agents     = " → ".join(report["pipeline"]["agents_run"])

# # # #     sev_col = {"HIGH":"#f85149","MEDIUM":"#d29922","INFORMATIONAL":"#3fb950"}.get(severity,"#fff")
# # # #     ver_col = {"TRUE_POSITIVE":"#f85149","FALSE_POSITIVE":"#3fb950",
# # # #                "NEEDS_INVESTIGATION":"#d29922"}.get(verdict,"#fff")
# # # #     sev_ico = {"HIGH":"🔴","MEDIUM":"🟡","INFORMATIONAL":"🟢"}.get(severity,"⚪")
# # # #     ver_ico = {"TRUE_POSITIVE":"⚠️","FALSE_POSITIVE":"✅",
# # # #                "NEEDS_INVESTIGATION":"🔍"}.get(verdict,"❓")

# # # #     cards = ""
# # # #     for lbl, val, col in [
# # # #         ("Verdict",    f"{ver_ico} {verdict}",         ver_col),
# # # #         ("Severity",   f"{sev_ico} {severity}",        sev_col),
# # # #         ("Confidence", confidence,                      "#fff"),
# # # #         ("Clean Run",  "✅ Yes" if clean else "❌ No", "#3fb950" if clean else "#f85149"),
# # # #     ]:
# # # #         cards += (
# # # #             f'<div style="{S_CARD}">'
# # # #             f'<div style="font-size:10px;color:#8b8fa8;text-transform:uppercase;'
# # # #             f'letter-spacing:.08em">{lbl}</div>'
# # # #             f'<div style="font-size:14px;font-weight:700;color:{col};margin-top:3px">'
# # # #             f'{val}</div></div>'
# # # #         )

# # # #     cvc = {"HIGH":"#f85149","MEDIUM":"#d29922","LOW":"#3fb950"}
# # # #     cve_html = "".join(
# # # #         f'<span style="display:inline-block;background:#1f2937;'
# # # #         f'border:1px solid {cvc.get(c.get("severity",""),"#374151")};'
# # # #         f'border-radius:4px;padding:2px 8px;font-size:11px;'
# # # #         f'color:{cvc.get(c.get("severity",""),"#9ca3af")};margin:2px 3px;'
# # # #         f'font-family:monospace">'
# # # #         f'{c["cve_id"]} · {c.get("severity","")} · {c.get("cvss_score","")}'
# # # #         f'</span>'
# # # #         for c in cves
# # # #     ) if cves else '<span style="color:#555">No CVEs found</span>'

# # # #     ex_rows = ""
# # # #     for ex in ex_list:
# # # #         col   = _hcol(ex["status_code"])
# # # #         short = ex["url"].replace("http://localhost:8001", "")
# # # #         ex_rows += (
# # # #             f'<div style="{S_HTTP_BLOCK}">'
# # # #             f'<div style="color:#79c0ff">[{ex["label"]}] {ex["method"]} {short}</div>'
# # # #             f'<div style="color:{col}">{ex["status_code"]} ({ex["latency_ms"]}ms)</div>'
# # # #             f'<div style="color:#8b8fa8;font-size:11px;margin-top:2px">'
# # # #             f'{ex.get("body_preview","")[:80]}</div></div>'
# # # #         )

# # # #     return (
# # # #         f'<div style="{S_REPORT}">'
# # # #         f'<span style="{S_PANEL_TITLE}">📋 Final Report</span>'
# # # #         f'<div style="font-size:15px;font-weight:700;color:#fff;'
# # # #         f'border-bottom:1px solid #30363d;padding-bottom:8px;margin-bottom:14px">'
# # # #         f'📋 Final Report — {report["report_id"]}</div>'
# # # #         f'<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px">{cards}</div>'
# # # #         f'<span style="{S_SEC}">OWASP Category</span>'
# # # #         f'<div style="color:#58a6ff;font-size:13px;margin-bottom:8px">{category}</div>'
# # # #         f'<span style="{S_SEC}">Reasoning</span>'
# # # #         f'<div style="{S_LBOX}">{reasoning}</div>'
# # # #         f'<span style="{S_SEC}">Recommended Fix</span>'
# # # #         f'<div style="{S_RBOX}">{fix}</div>'
# # # #         f'<span style="{S_SEC}">CVE References</span>'
# # # #         f'<div style="margin:6px 0 12px">{cve_html}</div>'
# # # #         f'<span style="{S_SEC}">HTTP Evidence</span>'
# # # #         f'{ex_rows}'
# # # #         f'<div style="color:#555;font-size:11px;margin-top:14px">'
# # # #         f'Generated: {report["generated_at"]} &nbsp;·&nbsp; Pipeline: {agents}'
# # # #         f'</div></div>'
# # # #     )

# # # # # ─────────────────────────────────────────────────────────────────────────────
# # # # # PAGE
# # # # # ─────────────────────────────────────────────────────────────────────────────

# # # # st.markdown(
# # # #     '<p style="font-size:2rem;font-weight:700;color:#fff;margin-bottom:0">'
# # # #     '🔐 PentraceAI</p>',
# # # #     unsafe_allow_html=True,
# # # # )
# # # # st.markdown(
# # # #     '<p style="font-size:.88rem;color:#8b8fa8;margin-top:0;margin-bottom:1.2rem">'
# # # #     'Agentic API Vulnerability Scanner · ReconAgent → AnalysisAgent → ReportAgent · '
# # # #     'OWASP Top 10 2025 · Azure OpenAI · NVD CVE Correlation</p>',
# # # #     unsafe_allow_html=True,
# # # # )

# # # # col_sel, col_btn, _ = st.columns([2, 1, 4])
# # # # with col_sel:
# # # #     scenario_labels = {k: v["label"] for k, v in SCAN_SCENARIOS.items()}
# # # #     selected = st.selectbox(
# # # #         "Scenario",
# # # #         options=list(scenario_labels.keys()),
# # # #         format_func=lambda k: scenario_labels[k],
# # # #         label_visibility="collapsed",
# # # #     )
# # # # with col_btn:
# # # #     run_clicked = st.button("▶ Run Scan", type="primary", use_container_width=True)

# # # # st.markdown("---")

# # # # # Two columns — each holds ONE st.empty() that gets replaced in-place
# # # # left_col, right_col = st.columns(2)
# # # # with left_col:
# # # #     r_slot = st.empty()
# # # # with right_col:
# # # #     t_slot = st.empty()

# # # # report_slot = st.empty()

# # # # # ─────────────────────────────────────────────────────────────────────────────
# # # # # RENDER HELPERS — each writes to its slot, replacing previous content
# # # # # ─────────────────────────────────────────────────────────────────────────────

# # # # def show_r(lines):
# # # #     r_slot.markdown(_reasoning_html(lines), unsafe_allow_html=True)

# # # # def show_t(exchanges):
# # # #     t_slot.markdown(_traffic_html(exchanges), unsafe_allow_html=True)

# # # # def show_rep(report):
# # # #     report_slot.markdown(_report_html(report), unsafe_allow_html=True)

# # # # # ─────────────────────────────────────────────────────────────────────────────
# # # # # INITIAL STATE
# # # # # ─────────────────────────────────────────────────────────────────────────────

# # # # show_r([])
# # # # show_t([])

# # # # # ─────────────────────────────────────────────────────────────────────────────
# # # # # LIVE RUN
# # # # # ─────────────────────────────────────────────────────────────────────────────

# # # # if run_clicked:
# # # #     rl: list[str] = []
# # # #     ex: list[dict] = []

# # # #     show_r(['<span style="color:#58a6ff">⚡ Pipeline starting...</span>'])
# # # #     show_t([])

# # # #     for event in run_scan_streaming(scenario=selected):
# # # #         t = event["type"]

# # # #         if t == "agent_start":
# # # #             rl.append(
# # # #                 f'<span style="color:#58a6ff;font-weight:700;display:block;margin-top:8px">'
# # # #                 f'── Stage {event["stage"]}/3: {event["agent"]} ──</span>'
# # # #             )
# # # #             show_r(rl)

# # # #         elif t == "agent_step":
# # # #             rl.append(
# # # #                 f'<div style="line-height:1.7;padding:1px 0">'
# # # #                 f'&nbsp;&nbsp;{_c(event["message"])}</div>'
# # # #             )
# # # #             show_r(rl)

# # # #         elif t == "http_exchange":
# # # #             ex.append(event["data"])
# # # #             show_t(ex)

# # # #         elif t == "agent_done":
# # # #             rl.append(
# # # #                 f'<span style="color:#3fb950;font-size:12px;display:block">'
# # # #                 f'&nbsp;&nbsp;✓ {event["summary"]}</span>'
# # # #             )
# # # #             rl.append('<div style="color:#30363d">&nbsp;</div>')
# # # #             show_r(rl)

# # # #         elif t == "pipeline_done":
# # # #             rl.append(
# # # #                 '<span style="color:#3fb950;font-weight:700;display:block">'
# # # #                 '🏁 Pipeline complete</span>'
# # # #             )
# # # #             show_r(rl)
# # # #             rep = event["state"].get("report")
# # # #             if rep:
# # # #                 show_rep(rep)

# # # #         elif t == "error":
# # # #             rl.append(
# # # #                 f'<span style="color:#f85149;display:block">❌ {event["message"]}</span>'
# # # #             )
# # # #             show_r(rl)


# # # """
# # # ui/app.py — PentraceAI Streamlit UI
# # # Run: streamlit run ui/app.py
# # # """

# # # from __future__ import annotations

# # # import re
# # # import sys
# # # import os

# # # sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# # # import streamlit as st
# # # import streamlit.components.v1 as components
# # # from agent.orchestrator import SCAN_SCENARIOS, run_scan_streaming
# # # from agent.visitor_log import log_visit

# # # st.set_page_config(
# # #     page_title="PentraceAI",
# # #     page_icon="🔐",
# # #     layout="wide",
# # #     initial_sidebar_state="collapsed",
# # # )

# # # # ── Silent visitor log — fires once per session ───────────────────────────────

# # # if "visit_logged" not in st.session_state:
# # #     log_visit()
# # #     st.session_state.visit_logged = True

# # # # ── Inline style constants ────────────────────────────────────────────────────

# # # S_PANEL = (
# # #     "background:#161b22;border:1px solid #30363d;border-radius:8px;"
# # #     "padding:12px 14px;height:440px;overflow-y:auto;"
# # #     "font-family:'Courier New',monospace;font-size:13px;color:#c9d1d9;"
# # #     "display:block;"
# # # )
# # # S_PANEL_TITLE = (
# # #     "font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;"
# # #     "color:#58a6ff;border-bottom:1px solid #30363d;padding-bottom:6px;"
# # #     "margin-bottom:10px;display:block;"
# # # )
# # # S_REPORT = (
# # #     "background:#161b22;border:1px solid #30363d;border-radius:8px;"
# # #     "padding:14px 18px;height:540px;overflow-y:auto;"
# # #     "font-family:-apple-system,BlinkMacSystemFont,sans-serif;"
# # #     "font-size:13px;color:#c9d1d9;margin-top:16px;display:block;"
# # # )
# # # S_HTTP = (
# # #     "background:#0d1117;border-left:3px solid #58a6ff;"
# # #     "border-radius:4px;padding:7px 10px;margin:5px 0;display:block;"
# # # )
# # # S_CARD = (
# # #     "background:#0d1117;border:1px solid #30363d;border-radius:6px;"
# # #     "padding:8px 14px;min-width:120px;display:inline-block;margin:4px;"
# # # )
# # # S_LBOX = (
# # #     "background:#0d1117;border-left:3px solid #58a6ff;border-radius:4px;"
# # #     "padding:10px 14px;line-height:1.6;font-size:13px;color:#c9d1d9;"
# # #     "display:block;margin:4px 0 8px;"
# # # )
# # # S_RBOX = S_LBOX.replace("#58a6ff", "#3fb950")
# # # S_SEC  = (
# # #     "font-size:10px;font-weight:700;color:#8b8fa8;text-transform:uppercase;"
# # #     "letter-spacing:.08em;margin:12px 0 4px;display:block;"
# # # )
# # # S_CODE = (
# # #     "background:#1f2937;padding:1px 5px;border-radius:3px;"
# # #     "color:#79c0ff;font-family:monospace;font-size:12px;"
# # # )

# # # # ── Helpers ───────────────────────────────────────────────────────────────────

# # # def _c(text: str) -> str:
# # #     return re.sub(r"`([^`]+)`", rf'<code style="{S_CODE}">\1</code>', text)

# # # def _hcol(status: int) -> str:
# # #     if status < 300: return "#3fb950"
# # #     if status < 400: return "#d29922"
# # #     return "#f85149"

# # # # ── HTML builders ─────────────────────────────────────────────────────────────

# # # def _reasoning_html(lines: list[str]) -> str:
# # #     body = (
# # #         "".join(f'<div style="line-height:1.7;padding:1px 0">{ln}</div>' for ln in lines)
# # #         if lines else
# # #         '<span style="color:#555">Click ▶ Run Scan to start...</span>'
# # #     )
# # #     return (
# # #         f'<div style="{S_PANEL}">'
# # #         f'<span style="{S_PANEL_TITLE}">🧠 Agent Reasoning</span>'
# # #         f'{body}</div>'
# # #     )


# # # def _traffic_html(exchanges: list[dict]) -> str:
# # #     if not exchanges:
# # #         body = '<span style="color:#555">Waiting for probes...</span>'
# # #     else:
# # #         parts = []
# # #         for ex in exchanges:
# # #             label  = ex.get("label", "unknown")
# # #             method = ex.get("method", "GET")
# # #             url    = ex.get("url", "").replace("http://localhost:8001", "")
# # #             status = ex.get("status_code", 0)
# # #             ms     = ex.get("latency_ms", 0)
# # #             bt     = ex.get("body_preview", "")[:80]
# # #             col    = _hcol(status)
# # #             parts.append(
# # #                 f'<div style="{S_HTTP}">'
# # #                 f'<div style="color:#79c0ff">→ [{label}] {method} {url}</div>'
# # #                 f'<div style="color:{col}">← {status} ({ms}ms)</div>'
# # #                 f'<div style="color:#8b8fa8;font-size:11px;margin-top:2px">{bt}</div>'
# # #                 f'</div>'
# # #             )
# # #         body = "".join(parts)
# # #     return (
# # #         f'<div style="{S_PANEL}">'
# # #         f'<span style="{S_PANEL_TITLE}">📡 Live HTTP Traffic</span>'
# # #         f'{body}</div>'
# # #     )


# # # def _report_html(report: dict) -> str:
# # #     verdict    = report["finding"]["verdict"]
# # #     severity   = report["severity"]
# # #     confidence = report["finding"]["confidence"]
# # #     category   = report["finding"]["owasp_category"]
# # #     reasoning  = report["finding"]["reasoning"]
# # #     fix        = report["finding"]["recommended_fix"]
# # #     cves       = report["evidence"]["cve_references"]
# # #     ex_list    = report["evidence"]["http_exchanges"]
# # #     clean      = report["pipeline"]["clean_run"]
# # #     agents     = " → ".join(report["pipeline"]["agents_run"])

# # #     sev_col = {"HIGH":"#f85149","MEDIUM":"#d29922","INFORMATIONAL":"#3fb950"}.get(severity,"#fff")
# # #     ver_col = {"TRUE_POSITIVE":"#f85149","FALSE_POSITIVE":"#3fb950",
# # #                "NEEDS_INVESTIGATION":"#d29922"}.get(verdict,"#fff")
# # #     sev_ico = {"HIGH":"🔴","MEDIUM":"🟡","INFORMATIONAL":"🟢"}.get(severity,"⚪")
# # #     ver_ico = {"TRUE_POSITIVE":"⚠️","FALSE_POSITIVE":"✅",
# # #                "NEEDS_INVESTIGATION":"🔍"}.get(verdict,"❓")

# # #     def card(lbl, val, col):
# # #         return (
# # #             f'<div style="{S_CARD}">'
# # #             f'<div style="font-size:10px;color:#8b8fa8;text-transform:uppercase;'
# # #             f'letter-spacing:.08em">{lbl}</div>'
# # #             f'<div style="font-size:14px;font-weight:700;color:{col};margin-top:3px">'
# # #             f'{val}</div></div>'
# # #         )

# # #     cards = (
# # #         card("Verdict",    f"{ver_ico} {verdict}",         ver_col) +
# # #         card("Severity",   f"{sev_ico} {severity}",        sev_col) +
# # #         card("Confidence", confidence,                      "#fff")  +
# # #         card("Clean Run",  "✅ Yes" if clean else "❌ No",
# # #              "#3fb950" if clean else "#f85149")
# # #     )

# # #     cvc = {"HIGH":"#f85149","MEDIUM":"#d29922","LOW":"#3fb950"}
# # #     cve_html = "".join(
# # #         f'<span style="display:inline-block;background:#1f2937;'
# # #         f'border:1px solid {cvc.get(c.get("severity",""),"#374151")};'
# # #         f'border-radius:4px;padding:2px 8px;font-size:11px;'
# # #         f'color:{cvc.get(c.get("severity",""),"#9ca3af")};margin:2px 3px;'
# # #         f'font-family:monospace">'
# # #         f'{c["cve_id"]} · {c.get("severity","")} · {c.get("cvss_score","")}'
# # #         f'</span>'
# # #         for c in cves
# # #     ) if cves else '<span style="color:#555">No CVEs found</span>'

# # #     ex_rows = ""
# # #     for ex in ex_list:
# # #         col   = _hcol(ex["status_code"])
# # #         short = ex["url"].replace("http://localhost:8001", "")
# # #         ex_rows += (
# # #             f'<div style="{S_HTTP}">'
# # #             f'<div style="color:#79c0ff">[{ex["label"]}] {ex["method"]} {short}</div>'
# # #             f'<div style="color:{col}">{ex["status_code"]} ({ex["latency_ms"]}ms)</div>'
# # #             f'<div style="color:#8b8fa8;font-size:11px;margin-top:2px">'
# # #             f'{ex.get("body_preview","")[:80]}</div></div>'
# # #         )

# # #     return (
# # #         f'<div style="{S_REPORT}">'
# # #         f'<span style="{S_PANEL_TITLE}">📋 Final Report</span>'
# # #         f'<div style="font-size:15px;font-weight:700;color:#fff;'
# # #         f'border-bottom:1px solid #30363d;padding-bottom:8px;margin-bottom:14px">'
# # #         f'📋 Final Report — {report["report_id"]}</div>'
# # #         f'<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px">{cards}</div>'
# # #         f'<span style="{S_SEC}">OWASP Category</span>'
# # #         f'<div style="color:#58a6ff;font-size:13px;margin-bottom:8px">{category}</div>'
# # #         f'<span style="{S_SEC}">Reasoning</span>'
# # #         f'<div style="{S_LBOX}">{reasoning}</div>'
# # #         f'<span style="{S_SEC}">Recommended Fix</span>'
# # #         f'<div style="{S_RBOX}">{fix}</div>'
# # #         f'<span style="{S_SEC}">CVE References</span>'
# # #         f'<div style="margin:6px 0 12px">{cve_html}</div>'
# # #         f'<span style="{S_SEC}">HTTP Evidence</span>'
# # #         f'{ex_rows}'
# # #         f'<div style="color:#555;font-size:11px;margin-top:14px">'
# # #         f'Generated: {report["generated_at"]} &nbsp;·&nbsp; Pipeline: {agents}'
# # #         f'</div></div>'
# # #     )

# # # # ── About — self-contained iframe, rendered once, never in a loop ─────────────

# # # def _about_iframe() -> str:
# # #     """
# # #     Returns a complete HTML document for components.html().
# # #     Everything is inside one iframe — no Streamlit sanitization,
# # #     no class stripping, proper scrollable box.
# # #     """
# # #     tags = [
# # #         "Python 3.11", "LangGraph", "Azure OpenAI GPT-4.1-mini",
# # #         "Azure Embeddings", "ChromaDB", "FastAPI Sandbox",
# # #         "NVD CVE API", "OWASP Top 10 2025", "Streamlit",
# # #     ]
# # #     tag_html = "".join(
# # #         f'<span style="background:#1f2937;border:1px solid #30363d;border-radius:20px;'
# # #         f'padding:4px 12px;font-size:12px;color:#c9d1d9;white-space:nowrap;'
# # #         f'display:inline-block;margin:3px 4px 3px 0">{t}</span>'
# # #         for t in tags
# # #     )

# # #     return f"""<!DOCTYPE html>
# # # <html>
# # # <head>
# # # <meta charset="utf-8">
# # # <style>
# # #   * {{ box-sizing: border-box; margin: 0; padding: 0; }}
# # #   html, body {{ height: 100%; background: #0e1117; }}
# # #   ::-webkit-scrollbar       {{ width: 5px; }}
# # #   ::-webkit-scrollbar-track {{ background: #0d1117; }}
# # #   ::-webkit-scrollbar-thumb {{ background: #30363d; border-radius: 3px; }}
# # #   body {{
# # #     font-family : -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
# # #     font-size   : 13px;
# # #     color       : #c9d1d9;
# # #     padding     : 0;
# # #   }}
# # #   .box {{
# # #     background    : #161b22;
# # #     border        : 1px solid #30363d;
# # #     border-radius : 8px;
# # #     padding       : 22px 26px;
# # #     height        : 480px;
# # #     overflow-y    : auto;
# # #   }}
# # #   .title {{
# # #     font-size   : 20px;
# # #     font-weight : 700;
# # #     color       : #fff;
# # #     margin-bottom: 4px;
# # #   }}
# # #   .subtitle {{
# # #     font-size    : 13px;
# # #     color        : #8b8fa8;
# # #     margin-bottom: 22px;
# # #   }}
# # #   .subtitle .name {{ color: #58a6ff; font-weight: 600; }}
# # #   .section-head {{
# # #     font-size    : 14px;
# # #     font-weight  : 700;
# # #     color        : #58a6ff;
# # #     margin       : 20px 0 8px;
# # #   }}
# # #   .body-text {{
# # #     font-size  : 13px;
# # #     line-height: 1.75;
# # #     color      : #c9d1d9;
# # #   }}
# # #   .body-text strong {{ color: #fff; }}
# # #   .agent-block {{
# # #     background   : #0d1117;
# # #     border-left  : 3px solid #58a6ff;
# # #     border-radius: 4px;
# # #     padding      : 10px 14px;
# # #     margin       : 6px 0;
# # #     font-size    : 13px;
# # #     line-height  : 1.65;
# # #     color        : #c9d1d9;
# # #   }}
# # #   .agent-block .agent-name {{ color: #79c0ff; font-weight: 700; }}
# # #   .tags {{ display: flex; flex-wrap: wrap; margin-bottom: 4px; }}
# # #   .divider {{
# # #     border     : none;
# # #     border-top : 1px solid #30363d;
# # #     margin     : 20px 0 0;
# # #   }}
# # # </style>
# # # </head>
# # # <body>
# # # <div class="box">

# # #   <div class="title">🔐 PentraceAI — Agentic API Vulnerability Scanner</div>
# # #   <div class="subtitle">
# # #     Built by <span class="name">Sanjay</span> &nbsp;·&nbsp; AI Engineer
# # #   </div>

# # #   <div class="section-head">🧠 What is this tool?</div>
# # #   <div class="body-text">
# # #     PentraceAI is an <strong>autonomous multi-agent security scanner</strong>
# # #     that detects API vulnerabilities in real time. It simulates attacker behaviour,
# # #     retrieves live CVE intelligence, and classifies findings using GPT-4 —
# # #     all without human intervention. Think of it as a junior penetration tester
# # #     that never sleeps.
# # #   </div>

# # #   <div class="section-head">⚙️ How does it work?</div>
# # #   <div class="body-text" style="margin-bottom:8px">
# # #     The pipeline runs three specialised agents in sequence:
# # #   </div>

# # #   <div class="agent-block">
# # #     <span class="agent-name">1. ReconAgent</span><br>
# # #     Fires real HTTP probes against the target API as both an attacker and a
# # #     legitimate user. Records status codes, latency, and response bodies.
# # #     Simultaneously queries the NVD (National Vulnerability Database) for
# # #     relevant CVEs.
# # #   </div>

# # #   <div class="agent-block">
# # #     <span class="agent-name">2. AnalysisAgent</span><br>
# # #     Performs semantic search over an OWASP Top 10 2025 knowledge base
# # #     (ChromaDB + Azure OpenAI embeddings) to retrieve relevant vulnerability
# # #     context. Passes the HTTP evidence + OWASP context to GPT-4.1-mini for
# # #     classification: TRUE_POSITIVE, FALSE_POSITIVE, or NEEDS_INVESTIGATION.
# # #   </div>

# # #   <div class="agent-block">
# # #     <span class="agent-name">3. ReportAgent</span><br>
# # #     Validates the full pipeline state and generates a structured security report:
# # #     verdict, severity, OWASP category, reasoning, remediation recommendation,
# # #     CVE references, and HTTP evidence.
# # #   </div>

# # #   <div class="section-head">🛠️ Tech Stack</div>
# # #   <div class="tags">{tag_html}</div>

# # #   <div class="section-head">🎯 Why I built this</div>
# # #   <div class="body-text">
# # #     API security is the #1 attack surface in modern applications — OWASP lists
# # #     Broken Object Level Authorization (BOLA) as the top API risk for 2025.
# # #     Most security tools are static scanners. PentraceAI demonstrates that
# # #     <strong>agentic AI can reason about vulnerabilities</strong> the way a human
# # #     analyst would — correlating HTTP behaviour, CVE data, and security knowledge
# # #     to reach a confident verdict.
# # #   </div>

# # #   <div class="section-head">🚀 Try it</div>
# # #   <div class="body-text">
# # #     Select a scenario from the dropdown and click <strong>▶ Run Scan</strong>.
# # #     Watch the three agents reason in real time — left panel shows agent thinking,
# # #     right panel shows live HTTP traffic, bottom panel shows the final security report.
# # #   </div>

# # #   <hr class="divider">

# # # </div>
# # # </body>
# # # </html>"""


# # # # ── Page header ───────────────────────────────────────────────────────────────

# # # st.markdown(
# # #     '<p style="font-size:2rem;font-weight:700;color:#fff;margin-bottom:0">'
# # #     '🔐 PentraceAI</p>',
# # #     unsafe_allow_html=True,
# # # )
# # # st.markdown(
# # #     '<p style="font-size:.88rem;color:#8b8fa8;margin-top:0;margin-bottom:1.2rem">'
# # #     'Agentic API Vulnerability Scanner · ReconAgent → AnalysisAgent → ReportAgent · '
# # #     'OWASP Top 10 2025 · Azure OpenAI · NVD CVE Correlation</p>',
# # #     unsafe_allow_html=True,
# # # )

# # # # ── Controls ──────────────────────────────────────────────────────────────────

# # # col_sel, col_run, col_about, _ = st.columns([2, 1, 1, 3])

# # # with col_sel:
# # #     scenario_labels = {k: v["label"] for k, v in SCAN_SCENARIOS.items()}
# # #     selected = st.selectbox(
# # #         "Scenario",
# # #         options=list(scenario_labels.keys()),
# # #         format_func=lambda k: scenario_labels[k],
# # #         label_visibility="collapsed",
# # #     )

# # # with col_run:
# # #     run_clicked = st.button("▶ Run Scan", type="primary", use_container_width=True)

# # # with col_about:
# # #     about_clicked = st.button("ℹ️ About", use_container_width=True)

# # # # ── About toggle ──────────────────────────────────────────────────────────────

# # # if "show_about" not in st.session_state:
# # #     st.session_state.show_about = False

# # # if about_clicked:
# # #     st.session_state.show_about = not st.session_state.show_about

# # # # About rendered via components.html — one iframe, never in a loop, never stacks
# # # if st.session_state.show_about:
# # #     components.html(_about_iframe(), height=500, scrolling=False)

# # # st.markdown("---")

# # # # ── Live panels ───────────────────────────────────────────────────────────────

# # # left_col, right_col = st.columns(2)
# # # with left_col:
# # #     r_slot = st.empty()
# # # with right_col:
# # #     t_slot = st.empty()

# # # report_slot = st.empty()

# # # def show_r(lines):
# # #     r_slot.markdown(_reasoning_html(lines), unsafe_allow_html=True)

# # # def show_t(exchanges):
# # #     t_slot.markdown(_traffic_html(exchanges), unsafe_allow_html=True)

# # # def show_rep(report):
# # #     report_slot.markdown(_report_html(report), unsafe_allow_html=True)

# # # # ── Initial state ─────────────────────────────────────────────────────────────

# # # show_r([])
# # # show_t([])

# # # # ── Live run ──────────────────────────────────────────────────────────────────

# # # if run_clicked:
# # #     rl: list[str] = []
# # #     ex: list[dict] = []

# # #     show_r(['<span style="color:#58a6ff">⚡ Pipeline starting...</span>'])
# # #     show_t([])

# # #     for event in run_scan_streaming(scenario=selected):
# # #         t = event["type"]

# # #         if t == "agent_start":
# # #             rl.append(
# # #                 f'<span style="color:#58a6ff;font-weight:700;display:block;margin-top:8px">'
# # #                 f'── Stage {event["stage"]}/3: {event["agent"]} ──</span>'
# # #             )
# # #             show_r(rl)

# # #         elif t == "agent_step":
# # #             rl.append(
# # #                 f'<div style="line-height:1.7;padding:1px 0">'
# # #                 f'&nbsp;&nbsp;{_c(event["message"])}</div>'
# # #             )
# # #             show_r(rl)

# # #         elif t == "http_exchange":
# # #             ex.append(event["data"])
# # #             show_t(ex)

# # #         elif t == "agent_done":
# # #             rl.append(
# # #                 f'<span style="color:#3fb950;font-size:12px;display:block">'
# # #                 f'&nbsp;&nbsp;✓ {event["summary"]}</span>'
# # #             )
# # #             rl.append('<div style="color:#30363d">&nbsp;</div>')
# # #             show_r(rl)

# # #         elif t == "pipeline_done":
# # #             rl.append(
# # #                 '<span style="color:#3fb950;font-weight:700;display:block">'
# # #                 '🏁 Pipeline complete</span>'
# # #             )
# # #             show_r(rl)
# # #             rep = event["state"].get("report")
# # #             if rep:
# # #                 show_rep(rep)

# # #         elif t == "error":
# # #             rl.append(
# # #                 f'<span style="color:#f85149;display:block">❌ {event["message"]}</span>'
# # #             )
# # #             show_r(rl)

# # """
# # ui/app.py — PentraceAI Streamlit UI
# # Run: streamlit run ui/app.py
# # """

# # from __future__ import annotations

# # import re
# # import sys
# # import os

# # sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# # import streamlit as st
# # import streamlit.components.v1 as components
# # from agent.orchestrator import SCAN_SCENARIOS, run_scan_streaming
# # from agent.visitor_log import log_visit

# # st.set_page_config(
# #     page_title="PentraceAI",
# #     page_icon="🔐",
# #     layout="wide",
# #     initial_sidebar_state="collapsed",
# # )

# # # ── Silent visitor log — fires once per session ───────────────────────────────

# # if "visit_logged" not in st.session_state:
# #     log_visit()
# #     st.session_state.visit_logged = True

# # # ── Inline style constants ────────────────────────────────────────────────────

# # S_PANEL = (
# #     "background:#161b22;border:1px solid #30363d;border-radius:8px;"
# #     "padding:12px 14px;height:440px;overflow-y:auto;"
# #     "font-family:'Courier New',monospace;font-size:13px;color:#c9d1d9;"
# #     "display:block;"
# # )
# # S_PANEL_TITLE = (
# #     "font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;"
# #     "color:#58a6ff;border-bottom:1px solid #30363d;padding-bottom:6px;"
# #     "margin-bottom:10px;display:block;"
# # )
# # S_REPORT = (
# #     "background:#161b22;border:1px solid #30363d;border-radius:8px;"
# #     "padding:14px 18px;height:540px;overflow-y:auto;"
# #     "font-family:-apple-system,BlinkMacSystemFont,sans-serif;"
# #     "font-size:13px;color:#c9d1d9;margin-top:16px;display:block;"
# # )
# # S_HTTP = (
# #     "background:#0d1117;border-left:3px solid #58a6ff;"
# #     "border-radius:4px;padding:7px 10px;margin:5px 0;display:block;"
# # )
# # S_CARD = (
# #     "background:#0d1117;border:1px solid #30363d;border-radius:6px;"
# #     "padding:8px 14px;min-width:120px;display:inline-block;margin:4px;"
# # )
# # S_LBOX = (
# #     "background:#0d1117;border-left:3px solid #58a6ff;border-radius:4px;"
# #     "padding:10px 14px;line-height:1.6;font-size:13px;color:#c9d1d9;"
# #     "display:block;margin:4px 0 8px;"
# # )
# # S_RBOX = S_LBOX.replace("#58a6ff", "#3fb950")
# # S_SEC  = (
# #     "font-size:10px;font-weight:700;color:#8b8fa8;text-transform:uppercase;"
# #     "letter-spacing:.08em;margin:12px 0 4px;display:block;"
# # )
# # S_CODE = (
# #     "background:#1f2937;padding:1px 5px;border-radius:3px;"
# #     "color:#79c0ff;font-family:monospace;font-size:12px;"
# # )

# # # ── Helpers ───────────────────────────────────────────────────────────────────

# # def _c(text: str) -> str:
# #     return re.sub(r"`([^`]+)`", rf'<code style="{S_CODE}">\1</code>', text)

# # def _hcol(status: int) -> str:
# #     if status < 300: return "#3fb950"
# #     if status < 400: return "#d29922"
# #     return "#f85149"

# # # ── HTML builders ─────────────────────────────────────────────────────────────

# # def _reasoning_html(lines: list[str]) -> str:
# #     body = (
# #         "".join(f'<div style="line-height:1.7;padding:1px 0">{ln}</div>' for ln in lines)
# #         if lines else
# #         '<span style="color:#555">Click ▶ Run Scan to start...</span>'
# #     )
# #     return (
# #         f'<div style="{S_PANEL}">'
# #         f'<span style="{S_PANEL_TITLE}">🧠 Agent Reasoning</span>'
# #         f'{body}</div>'
# #     )


# # def _traffic_html(exchanges: list[dict]) -> str:
# #     if not exchanges:
# #         body = '<span style="color:#555">Waiting for probes...</span>'
# #     else:
# #         parts = []
# #         for ex in exchanges:
# #             label  = ex.get("label", "unknown")
# #             method = ex.get("method", "GET")
# #             url    = ex.get("url", "").replace("http://localhost:8001", "")
# #             status = ex.get("status_code", 0)
# #             ms     = ex.get("latency_ms", 0)
# #             bt     = ex.get("body_preview", "")[:80]
# #             col    = _hcol(status)
# #             parts.append(
# #                 f'<div style="{S_HTTP}">'
# #                 f'<div style="color:#79c0ff">→ [{label}] {method} {url}</div>'
# #                 f'<div style="color:{col}">← {status} ({ms}ms)</div>'
# #                 f'<div style="color:#8b8fa8;font-size:11px;margin-top:2px">{bt}</div>'
# #                 f'</div>'
# #             )
# #         body = "".join(parts)
# #     return (
# #         f'<div style="{S_PANEL}">'
# #         f'<span style="{S_PANEL_TITLE}">📡 Live HTTP Traffic</span>'
# #         f'{body}</div>'
# #     )


# # def _report_html(report: dict) -> str:
# #     verdict    = report["finding"]["verdict"]
# #     severity   = report["severity"]
# #     confidence = report["finding"]["confidence"]
# #     category   = report["finding"]["owasp_category"]
# #     reasoning  = report["finding"]["reasoning"]
# #     fix        = report["finding"]["recommended_fix"]
# #     cves       = report["evidence"]["cve_references"]
# #     ex_list    = report["evidence"]["http_exchanges"]
# #     clean      = report["pipeline"]["clean_run"]
# #     agents     = " → ".join(report["pipeline"]["agents_run"])

# #     sev_col = {"HIGH":"#f85149","MEDIUM":"#d29922","INFORMATIONAL":"#3fb950"}.get(severity,"#fff")
# #     ver_col = {"TRUE_POSITIVE":"#f85149","FALSE_POSITIVE":"#3fb950",
# #                "NEEDS_INVESTIGATION":"#d29922"}.get(verdict,"#fff")
# #     sev_ico = {"HIGH":"🔴","MEDIUM":"🟡","INFORMATIONAL":"🟢"}.get(severity,"⚪")
# #     ver_ico = {"TRUE_POSITIVE":"⚠️","FALSE_POSITIVE":"✅",
# #                "NEEDS_INVESTIGATION":"🔍"}.get(verdict,"❓")

# #     def card(lbl, val, col):
# #         return (
# #             f'<div style="{S_CARD}">'
# #             f'<div style="font-size:10px;color:#8b8fa8;text-transform:uppercase;'
# #             f'letter-spacing:.08em">{lbl}</div>'
# #             f'<div style="font-size:14px;font-weight:700;color:{col};margin-top:3px">'
# #             f'{val}</div></div>'
# #         )

# #     cards = (
# #         card("Verdict",    f"{ver_ico} {verdict}",         ver_col) +
# #         card("Severity",   f"{sev_ico} {severity}",        sev_col) +
# #         card("Confidence", confidence,                      "#fff")  +
# #         card("Clean Run",  "✅ Yes" if clean else "❌ No",
# #              "#3fb950" if clean else "#f85149")
# #     )

# #     cvc = {"HIGH":"#f85149","MEDIUM":"#d29922","LOW":"#3fb950"}
# #     cve_html = "".join(
# #         f'<span style="display:inline-block;background:#1f2937;'
# #         f'border:1px solid {cvc.get(c.get("severity",""),"#374151")};'
# #         f'border-radius:4px;padding:2px 8px;font-size:11px;'
# #         f'color:{cvc.get(c.get("severity",""),"#9ca3af")};margin:2px 3px;'
# #         f'font-family:monospace">'
# #         f'{c["cve_id"]} · {c.get("severity","")} · {c.get("cvss_score","")}'
# #         f'</span>'
# #         for c in cves
# #     ) if cves else '<span style="color:#555">No CVEs found</span>'

# #     ex_rows = ""
# #     for ex in ex_list:
# #         col   = _hcol(ex["status_code"])
# #         short = ex["url"].replace("http://localhost:8001", "")
# #         ex_rows += (
# #             f'<div style="{S_HTTP}">'
# #             f'<div style="color:#79c0ff">[{ex["label"]}] {ex["method"]} {short}</div>'
# #             f'<div style="color:{col}">{ex["status_code"]} ({ex["latency_ms"]}ms)</div>'
# #             f'<div style="color:#8b8fa8;font-size:11px;margin-top:2px">'
# #             f'{ex.get("body_preview","")[:80]}</div></div>'
# #         )

# #     return (
# #         f'<div style="{S_REPORT}">'
# #         f'<span style="{S_PANEL_TITLE}">📋 Final Report</span>'
# #         f'<div style="font-size:15px;font-weight:700;color:#fff;'
# #         f'border-bottom:1px solid #30363d;padding-bottom:8px;margin-bottom:14px">'
# #         f'📋 Final Report — {report["report_id"]}</div>'
# #         f'<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px">{cards}</div>'
# #         f'<span style="{S_SEC}">OWASP Category</span>'
# #         f'<div style="color:#58a6ff;font-size:13px;margin-bottom:8px">{category}</div>'
# #         f'<span style="{S_SEC}">Reasoning</span>'
# #         f'<div style="{S_LBOX}">{reasoning}</div>'
# #         f'<span style="{S_SEC}">Recommended Fix</span>'
# #         f'<div style="{S_RBOX}">{fix}</div>'
# #         f'<span style="{S_SEC}">CVE References</span>'
# #         f'<div style="margin:6px 0 12px">{cve_html}</div>'
# #         f'<span style="{S_SEC}">HTTP Evidence</span>'
# #         f'{ex_rows}'
# #         f'<div style="color:#555;font-size:11px;margin-top:14px">'
# #         f'Generated: {report["generated_at"]} &nbsp;·&nbsp; Pipeline: {agents}'
# #         f'</div></div>'
# #     )


# # # ── About — full-screen overlay inside iframe, zero layout shift ──────────────

# # def _about_iframe() -> str:
# #     """
# #     Complete HTML document rendered in components.html().
# #     The overlay is position:fixed inside the iframe so it covers
# #     the iframe area. The scan panels beneath are untouched — they
# #     never move because this iframe sits in a zero-height slot
# #     above the panels, and the overlay escapes its own iframe bounds
# #     via a large negative margin trick... but the cleaner approach:
# #     we give this iframe exactly the height of the content (500px)
# #     and place it BEFORE the scan panels in the DOM. The scan panels
# #     are always rendered — About just appears above them.

# #     Impact-first content: numbers, outcomes, what the recruiter/CTO
# #     cares about — not a README dump.
# #     """
# #     tags = [
# #         "Python 3.11", "LangGraph", "Azure OpenAI GPT-4.1-mini",
# #         "Azure Embeddings", "ChromaDB", "FastAPI", "NVD CVE API",
# #         "OWASP Top 10 2025", "Streamlit",
# #     ]
# #     tag_html = "".join(
# #         f'<span style="background:#1f2937;border:1px solid #30363d;'
# #         f'border-radius:20px;padding:3px 11px;font-size:11px;color:#c9d1d9;'
# #         f'white-space:nowrap;display:inline-block;margin:3px 3px 3px 0">{t}</span>'
# #         for t in tags
# #     )

# #     return """<!DOCTYPE html>
# # <html>
# # <head>
# # <meta charset="utf-8">
# # <style>
# #   * { box-sizing: border-box; margin: 0; padding: 0; }
# #   html, body { height: 100%; background: #0e1117; }
# #   body {
# #     font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
# #     font-size: 13px;
# #     color: #c9d1d9;
# #   }
# #   .box {
# #     background    : #161b22;
# #     border        : 1px solid #30363d;
# #     border-radius : 10px;
# #     padding       : 24px 28px;
# #     height        : 490px;
# #     overflow-y    : auto;
# #   }
# #   .box::-webkit-scrollbar       { width: 5px; }
# #   .box::-webkit-scrollbar-track { background: #0d1117; }
# #   .box::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }

# #   /* Hero */
# #   .hero-name {
# #     font-size: 22px; font-weight: 800; color: #fff; margin-bottom: 2px;
# #   }
# #   .hero-role {
# #     font-size: 13px; color: #58a6ff; font-weight: 600; margin-bottom: 14px;
# #   }
# #   .hero-pitch {
# #     font-size: 14px; line-height: 1.75; color: #c9d1d9;
# #     background: #0d1117; border-left: 3px solid #58a6ff;
# #     border-radius: 4px; padding: 12px 16px; margin-bottom: 20px;
# #   }
# #   .hero-pitch strong { color: #fff; }

# #   /* Impact numbers */
# #   .impact-row {
# #     display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px;
# #   }
# #   .impact-card {
# #     background: #0d1117; border: 1px solid #30363d;
# #     border-radius: 8px; padding: 12px 16px; flex: 1; min-width: 110px;
# #     text-align: center;
# #   }
# #   .impact-num  { font-size: 22px; font-weight: 800; color: #58a6ff; }
# #   .impact-label{ font-size: 11px; color: #8b8fa8; margin-top: 2px; line-height: 1.4; }

# #   /* Section */
# #   .sh {
# #     font-size: 13px; font-weight: 700; color: #58a6ff;
# #     margin: 18px 0 8px; display: flex; align-items: center; gap: 6px;
# #   }
# #   .sh::after {
# #     content: ''; flex: 1; height: 1px; background: #30363d;
# #   }

# #   /* Agent blocks */
# #   .agent {
# #     background: #0d1117; border-left: 3px solid #58a6ff;
# #     border-radius: 4px; padding: 10px 14px; margin: 6px 0;
# #     font-size: 13px; line-height: 1.65; color: #c9d1d9;
# #   }
# #   .agent .an { color: #79c0ff; font-weight: 700; }
# #   .agent .outcome {
# #     display: inline-block; background: #1a2a1a;
# #     border: 1px solid #3fb950; border-radius: 3px;
# #     padding: 1px 7px; font-size: 11px; color: #3fb950;
# #     margin-left: 6px; vertical-align: middle;
# #   }

# #   /* Tags */
# #   .tags { display: flex; flex-wrap: wrap; }

# #   /* What makes it different */
# #   .diff-row { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 4px; }
# #   .diff-card {
# #     background: #0d1117; border: 1px solid #30363d;
# #     border-radius: 6px; padding: 10px 14px; flex: 1; min-width: 140px;
# #   }
# #   .diff-card .icon { font-size: 18px; margin-bottom: 4px; }
# #   .diff-card .dt   { font-size: 12px; font-weight: 700; color: #fff; margin-bottom: 3px; }
# #   .diff-card .dd   { font-size: 11px; color: #8b8fa8; line-height: 1.5; }
# # </style>
# # </head>
# # <body>
# # <div class="box">

# #   <!-- Hero -->
# #   <div class="hero-name">🔐 PentraceAI</div>
# #   <div class="hero-role">Built by Sanjay &nbsp;·&nbsp; AI Engineer</div>
# #   <div class="hero-pitch">
# #     An <strong>autonomous 3-agent security pipeline</strong> that does what junior
# #     pen-testers do manually — probe APIs, correlate CVE data, reason about
# #     vulnerabilities — and delivers a <strong>structured verdict in under 30 seconds</strong>,
# #     entirely without human input.
# #   </div>

# #   <!-- Impact numbers -->
# #   <div class="impact-row">
# #     <div class="impact-card">
# #       <div class="impact-num">3</div>
# #       <div class="impact-label">Specialised AI Agents chained end-to-end</div>
# #     </div>
# #     <div class="impact-card">
# #       <div class="impact-num">10</div>
# #       <div class="impact-label">OWASP Top 10 2025 categories in knowledge base</div>
# #     </div>
# #     <div class="impact-card">
# #       <div class="impact-num">30</div>
# #       <div class="impact-label">OWASP knowledge chunks in ChromaDB vector store</div>
# #     </div>
# #     <div class="impact-card">
# #       <div class="impact-num">&lt;30s</div>
# #       <div class="impact-label">Recon → Analysis → Report, fully automated</div>
# #     </div>
# #   </div>

# #   <!-- What makes it different -->
# #   <div class="sh">⚡ What makes this different</div>
# #   <div class="diff-row">
# #     <div class="diff-card">
# #       <div class="icon">🤖</div>
# #       <div class="dt">Agentic Reasoning</div>
# #       <div class="dd">Not a rule-based scanner. GPT-4.1-mini reasons over real HTTP evidence like a human analyst.</div>
# #     </div>
# #     <div class="diff-card">
# #       <div class="icon">🗄️</div>
# #       <div class="dt">RAG over OWASP</div>
# #       <div class="dd">Semantic search over a structured OWASP 2025 knowledge base — context-aware, not keyword-matched.</div>
# #     </div>
# #     <div class="diff-card">
# #       <div class="icon">📡</div>
# #       <div class="dt">Live CVE Intel</div>
# #       <div class="dd">Hits the NVD API in real time. Every report includes actual CVE IDs with CVSS scores.</div>
# #     </div>
# #   </div>

# #   <!-- Pipeline -->
# #   <div class="sh">⚙️ The 3-Agent Pipeline</div>

# #   <div class="agent">
# #     <span class="an">1. ReconAgent</span>
# #     <span class="outcome">Probes + CVE fetch</span><br>
# #     Fires real HTTP requests as both attacker and legitimate user. Records status codes,
# #     latency, and response bodies. Simultaneously queries NVD for relevant CVEs.
# #   </div>

# #   <div class="agent">
# #     <span class="an">2. AnalysisAgent</span>
# #     <span class="outcome">GPT-4 verdict</span><br>
# #     Runs semantic search over the OWASP knowledge base. Feeds HTTP evidence +
# #     OWASP context into GPT-4.1-mini. Returns: TRUE_POSITIVE · FALSE_POSITIVE ·
# #     NEEDS_INVESTIGATION with confidence level.
# #   </div>

# #   <div class="agent">
# #     <span class="an">3. ReportAgent</span>
# #     <span class="outcome">Structured report</span><br>
# #     Validates full pipeline state. Generates report with verdict, severity,
# #     OWASP category, reasoning, remediation steps, CVE references, and HTTP evidence.
# #   </div>

# #   <!-- Tech stack -->
# #   <div class="sh">🛠️ Tech Stack</div>
# #   <div class="tags">""" + tag_html + """</div>

# #   <!-- Try it -->
# #   <div class="sh">🚀 Try it now</div>
# #   <div style="font-size:13px;line-height:1.75;color:#c9d1d9">
# #     Pick a scenario — <strong style="color:#f85149">BOLA</strong>,
# #     <strong style="color:#d29922">Broken Auth</strong>, or
# #     <strong style="color:#3fb950">False Positive</strong> — and hit
# #     <strong style="color:#fff">▶ Run Scan</strong>.
# #     The left panel streams agent reasoning live. The right panel shows real HTTP
# #     exchanges as they happen. The report appears below when the pipeline completes.
# #   </div>

# # </div>
# # </body>
# # </html>"""


# # # ── Page header ───────────────────────────────────────────────────────────────

# # st.markdown(
# #     '<p style="font-size:2rem;font-weight:800;color:#58a6ff;margin-bottom:0;'
# #     'text-shadow:0 0 30px rgba(88,166,255,0.3)">'
# #     '🔐 PentraceAI</p>',
# #     unsafe_allow_html=True,
# # )
# # st.markdown(
# #     '<p style="font-size:.88rem;color:#8b8fa8;margin-top:0;margin-bottom:1.2rem">'
# #     'Agentic API Vulnerability Scanner &nbsp;·&nbsp; '
# #     'ReconAgent → AnalysisAgent → ReportAgent &nbsp;·&nbsp; '
# #     'OWASP Top 10 2025 &nbsp;·&nbsp; Azure OpenAI &nbsp;·&nbsp; NVD CVE Correlation</p>',
# #     unsafe_allow_html=True,
# # )

# # # ── Controls ──────────────────────────────────────────────────────────────────

# # col_sel, col_run, col_about, _ = st.columns([2, 1, 1, 3])

# # with col_sel:
# #     scenario_labels = {k: v["label"] for k, v in SCAN_SCENARIOS.items()}
# #     selected = st.selectbox(
# #         "Scenario",
# #         options=list(scenario_labels.keys()),
# #         format_func=lambda k: scenario_labels[k],
# #         label_visibility="collapsed",
# #     )

# # with col_run:
# #     run_clicked = st.button("▶ Run Scan", type="primary", use_container_width=True)

# # with col_about:
# #     about_clicked = st.button("ℹ️ About", use_container_width=True)

# # # ── About toggle — renders ABOVE the scan panels, never inside the loop ───────

# # if "show_about" not in st.session_state:
# #     st.session_state.show_about = False

# # if about_clicked:
# #     st.session_state.show_about = not st.session_state.show_about

# # if st.session_state.show_about:
# #     components.html(_about_iframe(), height=510, scrolling=False)

# # st.markdown("---")

# # # ── Scan panels — always rendered, never displaced by About logic ─────────────

# # left_col, right_col = st.columns(2)
# # with left_col:
# #     r_slot = st.empty()
# # with right_col:
# #     t_slot = st.empty()

# # report_slot = st.empty()


# # def show_r(lines):
# #     r_slot.markdown(_reasoning_html(lines), unsafe_allow_html=True)

# # def show_t(exchanges):
# #     t_slot.markdown(_traffic_html(exchanges), unsafe_allow_html=True)

# # def show_rep(report):
# #     report_slot.markdown(_report_html(report), unsafe_allow_html=True)


# # # ── Initial state ─────────────────────────────────────────────────────────────

# # show_r([])
# # show_t([])

# # # ── Live run ──────────────────────────────────────────────────────────────────

# # if run_clicked:
# #     rl: list[str] = []
# #     ex: list[dict] = []

# #     show_r(['<span style="color:#58a6ff">⚡ Pipeline starting...</span>'])
# #     show_t([])

# #     for event in run_scan_streaming(scenario=selected):
# #         t = event["type"]

# #         if t == "agent_start":
# #             rl.append(
# #                 f'<span style="color:#58a6ff;font-weight:700;display:block;margin-top:8px">'
# #                 f'── Stage {event["stage"]}/3: {event["agent"]} ──</span>'
# #             )
# #             show_r(rl)

# #         elif t == "agent_step":
# #             rl.append(
# #                 f'<div style="line-height:1.7;padding:1px 0">'
# #                 f'&nbsp;&nbsp;{_c(event["message"])}</div>'
# #             )
# #             show_r(rl)

# #         elif t == "http_exchange":
# #             ex.append(event["data"])
# #             show_t(ex)

# #         elif t == "agent_done":
# #             rl.append(
# #                 f'<span style="color:#3fb950;font-size:12px;display:block">'
# #                 f'&nbsp;&nbsp;✓ {event["summary"]}</span>'
# #             )
# #             rl.append('<div style="color:#30363d">&nbsp;</div>')
# #             show_r(rl)

# #         elif t == "pipeline_done":
# #             rl.append(
# #                 '<span style="color:#3fb950;font-weight:700;display:block">'
# #                 '🏁 Pipeline complete</span>'
# #             )
# #             show_r(rl)
# #             rep = event["state"].get("report")
# #             if rep:
# #                 show_rep(rep)

# #         elif t == "error":
# #             rl.append(
# #                 f'<span style="color:#f85149;display:block">❌ {event["message"]}</span>'
# #             )
# #             show_r(rl)

# """
# ui/app.py — PentraceAI Streamlit UI
# Run: streamlit run ui/app.py
# """

# from __future__ import annotations

# import re
# import sys
# import os

# sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# import streamlit as st
# import streamlit.components.v1 as components
# from agent.orchestrator import SCAN_SCENARIOS, run_scan_streaming
# from agent.visitor_log import log_visit

# st.set_page_config(
#     page_title="PentraceAI",
#     page_icon="🔐",
#     layout="wide",
#     initial_sidebar_state="collapsed",
# )

# # ── Silent visitor log ────────────────────────────────────────────────────────

# if "visit_logged" not in st.session_state:
#     log_visit()
#     st.session_state.visit_logged = True

# # ── Theme state ───────────────────────────────────────────────────────────────

# if "dark_mode" not in st.session_state:
#     st.session_state.dark_mode = True

# # ── Theme palettes ────────────────────────────────────────────────────────────

# DARK = {
#     "page_bg"      : "#0e1117",
#     "panel_bg"     : "#161b22",
#     "panel_border" : "#30363d",
#     "title"        : "#58a6ff",
#     "subtitle"     : "#8b8fa8",
#     "text"         : "#c9d1d9",
#     "text_dim"     : "#8b8fa8",
#     "text_faint"   : "#555",
#     "accent_blue"  : "#58a6ff",
#     "accent_green" : "#3fb950",
#     "accent_red"   : "#f85149",
#     "accent_yellow": "#d29922",
#     "code_bg"      : "#1f2937",
#     "code_text"    : "#79c0ff",
#     "inset_bg"     : "#0d1117",
#     "inset_border" : "#30363d",
#     "scrollbar"    : "#30363d",
#     "divider"      : "#30363d",
#     "http_border"  : "#58a6ff",
#     "tag_bg"       : "#1f2937",
#     "tag_border"   : "#30363d",
#     "impact_num"   : "#58a6ff",
#     "agent_border" : "#58a6ff",
# }

# LIGHT = {
#     "page_bg"      : "#f6f8fa",
#     "panel_bg"     : "#ffffff",
#     "panel_border" : "#d0d7de",
#     "title"        : "#0969da",
#     "subtitle"     : "#57606a",
#     "text"         : "#24292f",
#     "text_dim"     : "#57606a",
#     "text_faint"   : "#aaa",
#     "accent_blue"  : "#0969da",
#     "accent_green" : "#1a7f37",
#     "accent_red"   : "#cf222e",
#     "accent_yellow": "#9a6700",
#     "code_bg"      : "#eef1f5",
#     "code_text"    : "#0550ae",
#     "inset_bg"     : "#f6f8fa",
#     "inset_border" : "#d0d7de",
#     "scrollbar"    : "#d0d7de",
#     "divider"      : "#d0d7de",
#     "http_border"  : "#0969da",
#     "tag_bg"       : "#eef1f5",
#     "tag_border"   : "#d0d7de",
#     "impact_num"   : "#0969da",
#     "agent_border" : "#0969da",
# }

# def T() -> dict:
#     return DARK if st.session_state.dark_mode else LIGHT

# # ── Inline style builders (use T() so every call picks current theme) ─────────

# def S_PANEL() -> str:
#     t = T()
#     return (
#         f"background:{t['panel_bg']};border:1px solid {t['panel_border']};"
#         f"border-radius:8px;padding:12px 14px;height:440px;overflow-y:auto;"
#         f"font-family:'Courier New',monospace;font-size:13px;color:{t['text']};"
#         f"display:block;"
#     )

# def S_PANEL_TITLE() -> str:
#     t = T()
#     return (
#         f"font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;"
#         f"color:{t['accent_blue']};border-bottom:1px solid {t['panel_border']};"
#         f"padding-bottom:6px;margin-bottom:10px;display:block;"
#     )

# def S_REPORT() -> str:
#     t = T()
#     return (
#         f"background:{t['panel_bg']};border:1px solid {t['panel_border']};"
#         f"border-radius:8px;padding:14px 18px;height:540px;overflow-y:auto;"
#         f"font-family:-apple-system,BlinkMacSystemFont,sans-serif;"
#         f"font-size:13px;color:{t['text']};margin-top:16px;display:block;"
#     )

# def S_HTTP() -> str:
#     t = T()
#     return (
#         f"background:{t['inset_bg']};border-left:3px solid {t['http_border']};"
#         f"border-radius:4px;padding:7px 10px;margin:5px 0;display:block;"
#     )

# def S_CARD() -> str:
#     t = T()
#     return (
#         f"background:{t['inset_bg']};border:1px solid {t['inset_border']};"
#         f"border-radius:6px;padding:8px 14px;min-width:120px;"
#         f"display:inline-block;margin:4px;"
#     )

# def S_LBOX() -> str:
#     t = T()
#     return (
#         f"background:{t['inset_bg']};border-left:3px solid {t['accent_blue']};"
#         f"border-radius:4px;padding:10px 14px;line-height:1.6;font-size:13px;"
#         f"color:{t['text']};display:block;margin:4px 0 8px;"
#     )

# def S_RBOX() -> str:
#     t = T()
#     return (
#         f"background:{t['inset_bg']};border-left:3px solid {t['accent_green']};"
#         f"border-radius:4px;padding:10px 14px;line-height:1.6;font-size:13px;"
#         f"color:{t['text']};display:block;margin:4px 0 8px;"
#     )

# def S_SEC() -> str:
#     t = T()
#     return (
#         f"font-size:10px;font-weight:700;color:{t['text_dim']};text-transform:uppercase;"
#         f"letter-spacing:.08em;margin:12px 0 4px;display:block;"
#     )

# def S_CODE() -> str:
#     t = T()
#     return (
#         f"background:{t['code_bg']};padding:1px 5px;border-radius:3px;"
#         f"color:{t['code_text']};font-family:monospace;font-size:12px;"
#     )

# # ── Helpers ───────────────────────────────────────────────────────────────────

# def _c(text: str) -> str:
#     s = S_CODE()
#     return re.sub(r"`([^`]+)`", rf'<code style="{s}">\1</code>', text)

# def _hcol(status: int) -> str:
#     t = T()
#     if status < 300: return t["accent_green"]
#     if status < 400: return t["accent_yellow"]
#     return t["accent_red"]

# # ── HTML builders ─────────────────────────────────────────────────────────────

# def _reasoning_html(lines: list[str]) -> str:
#     t = T()
#     body = (
#         "".join(f'<div style="line-height:1.7;padding:1px 0">{ln}</div>' for ln in lines)
#         if lines else
#         f'<span style="color:{t["text_faint"]}">Click ▶ Run Scan to start...</span>'
#     )
#     return (
#         f'<div style="{S_PANEL()}">'
#         f'<span style="{S_PANEL_TITLE()}">🧠 Agent Reasoning</span>'
#         f'{body}</div>'
#     )


# def _traffic_html(exchanges: list[dict]) -> str:
#     t = T()
#     if not exchanges:
#         body = f'<span style="color:{t["text_faint"]}">Waiting for probes...</span>'
#     else:
#         parts = []
#         for ex in exchanges:
#             label  = ex.get("label", "unknown")
#             method = ex.get("method", "GET")
#             url    = ex.get("url", "").replace("http://localhost:8001", "")
#             status = ex.get("status_code", 0)
#             ms     = ex.get("latency_ms", 0)
#             bt     = ex.get("body_preview", "")[:80]
#             col    = _hcol(status)
#             parts.append(
#                 f'<div style="{S_HTTP()}">'
#                 f'<div style="color:{t["accent_blue"]}">→ [{label}] {method} {url}</div>'
#                 f'<div style="color:{col}">← {status} ({ms}ms)</div>'
#                 f'<div style="color:{t["text_dim"]};font-size:11px;margin-top:2px">{bt}</div>'
#                 f'</div>'
#             )
#         body = "".join(parts)
#     return (
#         f'<div style="{S_PANEL()}">'
#         f'<span style="{S_PANEL_TITLE()}">📡 Live HTTP Traffic</span>'
#         f'{body}</div>'
#     )


# def _report_html(report: dict) -> str:
#     t = T()
#     verdict    = report["finding"]["verdict"]
#     severity   = report["severity"]
#     confidence = report["finding"]["confidence"]
#     category   = report["finding"]["owasp_category"]
#     reasoning  = report["finding"]["reasoning"]
#     fix        = report["finding"]["recommended_fix"]
#     cves       = report["evidence"]["cve_references"]
#     ex_list    = report["evidence"]["http_exchanges"]
#     clean      = report["pipeline"]["clean_run"]
#     agents     = " → ".join(report["pipeline"]["agents_run"])

#     sev_col = {
#         "HIGH"         : t["accent_red"],
#         "MEDIUM"       : t["accent_yellow"],
#         "INFORMATIONAL": t["accent_green"],
#     }.get(severity, t["text"])
#     ver_col = {
#         "TRUE_POSITIVE"      : t["accent_red"],
#         "FALSE_POSITIVE"     : t["accent_green"],
#         "NEEDS_INVESTIGATION": t["accent_yellow"],
#     }.get(verdict, t["text"])
#     sev_ico = {"HIGH":"🔴","MEDIUM":"🟡","INFORMATIONAL":"🟢"}.get(severity,"⚪")
#     ver_ico = {"TRUE_POSITIVE":"⚠️","FALSE_POSITIVE":"✅",
#                "NEEDS_INVESTIGATION":"🔍"}.get(verdict,"❓")

#     def card(lbl, val, col):
#         return (
#             f'<div style="{S_CARD()}">'
#             f'<div style="font-size:10px;color:{t["text_dim"]};text-transform:uppercase;'
#             f'letter-spacing:.08em">{lbl}</div>'
#             f'<div style="font-size:14px;font-weight:700;color:{col};margin-top:3px">'
#             f'{val}</div></div>'
#         )

#     cards = (
#         card("Verdict",    f"{ver_ico} {verdict}",         ver_col) +
#         card("Severity",   f"{sev_ico} {severity}",        sev_col) +
#         card("Confidence", confidence,                      t["text"]) +
#         card("Clean Run",  "✅ Yes" if clean else "❌ No",
#              t["accent_green"] if clean else t["accent_red"])
#     )

#     cvc = {
#         "HIGH"  : t["accent_red"],
#         "MEDIUM": t["accent_yellow"],
#         "LOW"   : t["accent_green"],
#     }
#     cve_html = "".join(
#         f'<span style="display:inline-block;background:{t["tag_bg"]};'
#         f'border:1px solid {cvc.get(c.get("severity",""), t["tag_border"])};'
#         f'border-radius:4px;padding:2px 8px;font-size:11px;'
#         f'color:{cvc.get(c.get("severity",""), t["text_dim"])};margin:2px 3px;'
#         f'font-family:monospace">'
#         f'{c["cve_id"]} · {c.get("severity","")} · {c.get("cvss_score","")}'
#         f'</span>'
#         for c in cves
#     ) if cves else f'<span style="color:{t["text_faint"]}">No CVEs found</span>'

#     ex_rows = ""
#     for ex in ex_list:
#         col   = _hcol(ex["status_code"])
#         short = ex["url"].replace("http://localhost:8001", "")
#         ex_rows += (
#             f'<div style="{S_HTTP()}">'
#             f'<div style="color:{t["accent_blue"]}">[{ex["label"]}] {ex["method"]} {short}</div>'
#             f'<div style="color:{col}">{ex["status_code"]} ({ex["latency_ms"]}ms)</div>'
#             f'<div style="color:{t["text_dim"]};font-size:11px;margin-top:2px">'
#             f'{ex.get("body_preview","")[:80]}</div></div>'
#         )

#     return (
#         f'<div style="{S_REPORT()}">'
#         f'<span style="{S_PANEL_TITLE()}">📋 Final Report</span>'
#         f'<div style="font-size:15px;font-weight:700;color:{t["text"]};'
#         f'border-bottom:1px solid {t["divider"]};padding-bottom:8px;margin-bottom:14px">'
#         f'📋 Final Report — {report["report_id"]}</div>'
#         f'<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px">{cards}</div>'
#         f'<span style="{S_SEC()}">OWASP Category</span>'
#         f'<div style="color:{t["accent_blue"]};font-size:13px;margin-bottom:8px">{category}</div>'
#         f'<span style="{S_SEC()}">Reasoning</span>'
#         f'<div style="{S_LBOX()}">{reasoning}</div>'
#         f'<span style="{S_SEC()}">Recommended Fix</span>'
#         f'<div style="{S_RBOX()}">{fix}</div>'
#         f'<span style="{S_SEC()}">CVE References</span>'
#         f'<div style="margin:6px 0 12px">{cve_html}</div>'
#         f'<span style="{S_SEC()}">HTTP Evidence</span>'
#         f'{ex_rows}'
#         f'<div style="color:{t["text_faint"]};font-size:11px;margin-top:14px">'
#         f'Generated: {report["generated_at"]} &nbsp;·&nbsp; Pipeline: {agents}'
#         f'</div></div>'
#     )


# # ── About iframe ──────────────────────────────────────────────────────────────

# def _about_iframe() -> str:
#     t = T()
#     tags = [
#         "Python 3.11", "LangGraph", "Azure OpenAI GPT-4.1-mini",
#         "Azure Embeddings", "ChromaDB", "FastAPI", "NVD CVE API",
#         "OWASP Top 10 2025", "Streamlit",
#     ]
#     tag_html = "".join(
#         f'<span style="background:{t["tag_bg"]};border:1px solid {t["tag_border"]};'
#         f'border-radius:20px;padding:3px 11px;font-size:11px;color:{t["text"]};'
#         f'white-space:nowrap;display:inline-block;margin:3px 3px 3px 0">{tag}</span>'
#         for tag in tags
#     )

#     return f"""<!DOCTYPE html>
# <html>
# <head>
# <meta charset="utf-8">
# <style>
#   * {{ box-sizing:border-box; margin:0; padding:0; }}
#   html, body {{ height:100%; background:{t['page_bg']}; }}
#   body {{
#     font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
#     font-size:13px; color:{t['text']};
#   }}
#   .box {{
#     background:{t['panel_bg']};
#     border:1px solid {t['panel_border']};
#     border-radius:10px; padding:24px 28px;
#     height:490px; overflow-y:auto;
#   }}
#   .box::-webkit-scrollbar       {{ width:5px; }}
#   .box::-webkit-scrollbar-track {{ background:{t['inset_bg']}; }}
#   .box::-webkit-scrollbar-thumb {{ background:{t['scrollbar']}; border-radius:3px; }}
#   .hero-name {{ font-size:22px;font-weight:800;color:{t['title']};margin-bottom:2px; }}
#   .hero-role {{ font-size:13px;color:{t['accent_blue']};font-weight:600;margin-bottom:14px; }}
#   .hero-pitch {{
#     font-size:14px;line-height:1.75;color:{t['text']};
#     background:{t['inset_bg']};border-left:3px solid {t['accent_blue']};
#     border-radius:4px;padding:12px 16px;margin-bottom:20px;
#   }}
#   .hero-pitch strong {{ color:{t['title']}; }}
#   .impact-row {{ display:flex;gap:10px;flex-wrap:wrap;margin-bottom:20px; }}
#   .impact-card {{
#     background:{t['inset_bg']};border:1px solid {t['inset_border']};
#     border-radius:8px;padding:12px 16px;flex:1;min-width:110px;text-align:center;
#   }}
#   .impact-num   {{ font-size:22px;font-weight:800;color:{t['impact_num']}; }}
#   .impact-label {{ font-size:11px;color:{t['text_dim']};margin-top:2px;line-height:1.4; }}
#   .sh {{
#     font-size:13px;font-weight:700;color:{t['accent_blue']};
#     margin:18px 0 8px;display:flex;align-items:center;gap:6px;
#   }}
#   .sh::after {{ content:'';flex:1;height:1px;background:{t['divider']}; }}
#   .agent {{
#     background:{t['inset_bg']};border-left:3px solid {t['agent_border']};
#     border-radius:4px;padding:10px 14px;margin:6px 0;
#     font-size:13px;line-height:1.65;color:{t['text']};
#   }}
#   .agent .an {{ color:{t['accent_blue']};font-weight:700; }}
#   .agent .outcome {{
#     display:inline-block;background:{t['tag_bg']};
#     border:1px solid {t['accent_green']};border-radius:3px;
#     padding:1px 7px;font-size:11px;color:{t['accent_green']};
#     margin-left:6px;vertical-align:middle;
#   }}
#   .diff-row {{ display:flex;gap:10px;flex-wrap:wrap;margin-bottom:4px; }}
#   .diff-card {{
#     background:{t['inset_bg']};border:1px solid {t['inset_border']};
#     border-radius:6px;padding:10px 14px;flex:1;min-width:140px;
#   }}
#   .diff-card .icon {{ font-size:18px;margin-bottom:4px; }}
#   .diff-card .dt   {{ font-size:12px;font-weight:700;color:{t['text']};margin-bottom:3px; }}
#   .diff-card .dd   {{ font-size:11px;color:{t['text_dim']};line-height:1.5; }}
#   .tags {{ display:flex;flex-wrap:wrap; }}
#   .try-text {{ font-size:13px;line-height:1.75;color:{t['text']}; }}
#   .try-text strong {{ color:{t['title']}; }}
# </style>
# </head>
# <body>
# <div class="box">

#   <div class="hero-name">🔐 PentraceAI</div>
#   <div class="hero-role">Built by Sanjay &nbsp;·&nbsp; AI Engineer</div>
#   <div class="hero-pitch">
#     An <strong>autonomous 3-agent security pipeline</strong> that does what junior
#     pen-testers do manually — probe APIs, correlate CVE data, reason about
#     vulnerabilities — and delivers a <strong>structured verdict in under 30 seconds</strong>,
#     entirely without human input.
#   </div>

#   <div class="impact-row">
#     <div class="impact-card">
#       <div class="impact-num">3</div>
#       <div class="impact-label">Specialised AI Agents chained end-to-end</div>
#     </div>
#     <div class="impact-card">
#       <div class="impact-num">10</div>
#       <div class="impact-label">OWASP Top 10 2025 categories in knowledge base</div>
#     </div>
#     <div class="impact-card">
#       <div class="impact-num">30</div>
#       <div class="impact-label">OWASP knowledge chunks in ChromaDB vector store</div>
#     </div>
#     <div class="impact-card">
#       <div class="impact-num">&lt;30s</div>
#       <div class="impact-label">Recon → Analysis → Report, fully automated</div>
#     </div>
#   </div>

#   <div class="sh">⚡ What makes this different</div>
#   <div class="diff-row">
#     <div class="diff-card">
#       <div class="icon">🤖</div>
#       <div class="dt">Agentic Reasoning</div>
#       <div class="dd">Not a rule-based scanner. GPT-4.1-mini reasons over real HTTP evidence like a human analyst.</div>
#     </div>
#     <div class="diff-card">
#       <div class="icon">🗄️</div>
#       <div class="dt">RAG over OWASP</div>
#       <div class="dd">Semantic search over a structured OWASP 2025 knowledge base — context-aware, not keyword-matched.</div>
#     </div>
#     <div class="diff-card">
#       <div class="icon">📡</div>
#       <div class="dt">Live CVE Intel</div>
#       <div class="dd">Hits the NVD API in real time. Every report includes actual CVE IDs with CVSS scores.</div>
#     </div>
#   </div>

#   <div class="sh">⚙️ The 3-Agent Pipeline</div>
#   <div class="agent">
#     <span class="an">1. ReconAgent</span>
#     <span class="outcome">Probes + CVE fetch</span><br>
#     Fires real HTTP requests as both attacker and legitimate user. Records status
#     codes, latency, and response bodies. Simultaneously queries NVD for relevant CVEs.
#   </div>
#   <div class="agent">
#     <span class="an">2. AnalysisAgent</span>
#     <span class="outcome">GPT-4 verdict</span><br>
#     Runs semantic search over the OWASP knowledge base. Feeds HTTP evidence +
#     OWASP context into GPT-4.1-mini. Returns TRUE_POSITIVE · FALSE_POSITIVE ·
#     NEEDS_INVESTIGATION with confidence level.
#   </div>
#   <div class="agent">
#     <span class="an">3. ReportAgent</span>
#     <span class="outcome">Structured report</span><br>
#     Validates full pipeline state. Generates report with verdict, severity,
#     OWASP category, reasoning, remediation steps, CVE references, and HTTP evidence.
#   </div>

#   <div class="sh">🛠️ Tech Stack</div>
#   <div class="tags">{tag_html}</div>

#   <div class="sh">🚀 Try it now</div>
#   <div class="try-text">
#     Pick a scenario —
#     <strong style="color:{t['accent_red']}">BOLA</strong>,
#     <strong style="color:{t['accent_yellow']}">Broken Auth</strong>, or
#     <strong style="color:{t['accent_green']}">False Positive</strong> — and hit
#     <strong>▶ Run Scan</strong>. Left panel streams agent reasoning live.
#     Right panel shows real HTTP exchanges. Report appears below when complete.
#   </div>

# </div>
# </body>
# </html>"""


# # ── Page header ───────────────────────────────────────────────────────────────

# t = T()

# # Theme toggle — top right
# _, toggle_col = st.columns([9, 1])
# with toggle_col:
#     toggle_label = "☀️ Light" if st.session_state.dark_mode else "🌙 Dark"
#     if st.button(toggle_label, use_container_width=True):
#         st.session_state.dark_mode = not st.session_state.dark_mode
#         st.rerun()

# # Inject page background color to match theme
# st.markdown(
#     f"""
#     <style>
#     .stApp {{
#         background-color: {t['page_bg']} !important;
#     }}
#     </style>
#     """,
#     unsafe_allow_html=True,
# )

# st.markdown(
#     f'<p style="font-size:2rem;font-weight:800;color:{t["title"]};margin-bottom:0;">'
#     f'🔐 PentraceAI</p>',
#     unsafe_allow_html=True,
# )
# st.markdown(
#     f'<p style="font-size:.88rem;color:{t["subtitle"]};margin-top:0;margin-bottom:1.2rem">'
#     f'Agentic API Vulnerability Scanner &nbsp;·&nbsp; '
#     f'ReconAgent → AnalysisAgent → ReportAgent &nbsp;·&nbsp; '
#     f'OWASP Top 10 2025 &nbsp;·&nbsp; Azure OpenAI &nbsp;·&nbsp; NVD CVE Correlation</p>',
#     unsafe_allow_html=True,
# )

# # ── Controls ──────────────────────────────────────────────────────────────────

# col_sel, col_run, col_about, _ = st.columns([2, 1, 1, 3])

# with col_sel:
#     scenario_labels = {k: v["label"] for k, v in SCAN_SCENARIOS.items()}
#     selected = st.selectbox(
#         "Scenario",
#         options=list(scenario_labels.keys()),
#         format_func=lambda k: scenario_labels[k],
#         label_visibility="collapsed",
#     )

# with col_run:
#     run_clicked = st.button("▶ Run Scan", type="primary", use_container_width=True)

# with col_about:
#     about_clicked = st.button("ℹ️ About", use_container_width=True)

# # ── About toggle ──────────────────────────────────────────────────────────────

# if "show_about" not in st.session_state:
#     st.session_state.show_about = False

# if about_clicked:
#     st.session_state.show_about = not st.session_state.show_about

# if st.session_state.show_about:
#     components.html(_about_iframe(), height=510, scrolling=False)

# st.markdown("---")

# # ── Scan panels ───────────────────────────────────────────────────────────────

# left_col, right_col = st.columns(2)
# with left_col:
#     r_slot = st.empty()
# with right_col:
#     t_slot = st.empty()

# report_slot = st.empty()


# def show_r(lines):
#     r_slot.markdown(_reasoning_html(lines), unsafe_allow_html=True)

# def show_t(exchanges):
#     t_slot.markdown(_traffic_html(exchanges), unsafe_allow_html=True)

# def show_rep(report):
#     report_slot.markdown(_report_html(report), unsafe_allow_html=True)


# # ── Initial state ─────────────────────────────────────────────────────────────

# show_r([])
# show_t([])

# # ── Live run ──────────────────────────────────────────────────────────────────

# if run_clicked:
#     rl: list[str] = []
#     ex: list[dict] = []

#     t = T()
#     show_r([f'<span style="color:{t["accent_blue"]}">⚡ Pipeline starting...</span>'])
#     show_t([])

#     for event in run_scan_streaming(scenario=selected):
#         ev = event["type"]
#         t  = T()

#         if ev == "agent_start":
#             rl.append(
#                 f'<span style="color:{t["accent_blue"]};font-weight:700;'
#                 f'display:block;margin-top:8px">'
#                 f'── Stage {event["stage"]}/3: {event["agent"]} ──</span>'
#             )
#             show_r(rl)

#         elif ev == "agent_step":
#             rl.append(
#                 f'<div style="line-height:1.7;padding:1px 0">'
#                 f'&nbsp;&nbsp;{_c(event["message"])}</div>'
#             )
#             show_r(rl)

#         elif ev == "http_exchange":
#             ex.append(event["data"])
#             show_t(ex)

#         elif ev == "agent_done":
#             rl.append(
#                 f'<span style="color:{t["accent_green"]};font-size:12px;display:block">'
#                 f'&nbsp;&nbsp;✓ {event["summary"]}</span>'
#             )
#             rl.append(f'<div style="color:{t["divider"]}">&nbsp;</div>')
#             show_r(rl)

#         elif ev == "pipeline_done":
#             rl.append(
#                 f'<span style="color:{t["accent_green"]};font-weight:700;display:block">'
#                 f'🏁 Pipeline complete</span>'
#             )
#             show_r(rl)
#             rep = event["state"].get("report")
#             if rep:
#                 show_rep(rep)

#         elif ev == "error":
#             rl.append(
#                 f'<span style="color:{t["accent_red"]};display:block">'
#                 f'❌ {event["message"]}</span>'
#             )
#             show_r(rl)

"""
ui/app.py — PentraceAI Streamlit UI
Run: streamlit run ui/app.py
"""

from __future__ import annotations

import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import streamlit.components.v1 as components
from agent.orchestrator import SCAN_SCENARIOS, run_scan_streaming
from agent.visitor_log import log_visit

st.set_page_config(
    page_title="PentraceAI",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global CSS — selectbox non-editable + page bg ─────────────────────────────

st.markdown(
    """
    <style>
    div[data-baseweb="select"] input {
        pointer-events : none !important;
        caret-color    : transparent !important;
        user-select    : none !important;
    }
    div[data-baseweb="select"] {
        cursor: pointer !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Silent visitor log ────────────────────────────────────────────────────────

if "visit_logged" not in st.session_state:
    log_visit()
    st.session_state.visit_logged = True

# ── Theme state ───────────────────────────────────────────────────────────────

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True

# ── Theme palettes ────────────────────────────────────────────────────────────
# LIGHT page palette — controls Streamlit chrome only.
# The 3 scan panels + About are ALWAYS dark regardless of theme.

DARK_PAGE = {
    "page_bg" : "#0e1117",
    "title"   : "#58a6ff",
    "subtitle": "#8b8fa8",
}

LIGHT_PAGE = {
    "page_bg" : "#f6f8fa",
    "title"   : "#0969da",
    "subtitle": "#57606a",
}

# These never change — panels are always dark
PANEL = {
    "bg"           : "#161b22",
    "border"       : "#30363d",
    "text"         : "#c9d1d9",
    "text_dim"     : "#8b8fa8",
    "text_faint"   : "#555",
    "accent_blue"  : "#58a6ff",
    "accent_green" : "#3fb950",
    "accent_red"   : "#f85149",
    "accent_yellow": "#d29922",
    "code_bg"      : "#1f2937",
    "code_text"    : "#79c0ff",
    "inset_bg"     : "#0d1117",
    "inset_border" : "#30363d",
    "scrollbar"    : "#30363d",
    "divider"      : "#30363d",
    "tag_bg"       : "#1f2937",
    "tag_border"   : "#30363d",
}

def P() -> dict:
    """Page-level palette (title, bg, subtitle)."""
    return DARK_PAGE if st.session_state.dark_mode else LIGHT_PAGE

# ── Inject page background ────────────────────────────────────────────────────

def _inject_bg() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{ background-color: {P()['page_bg']} !important; }}
        </style>
        """,
        unsafe_allow_html=True,
    )

# ── Panel style builders — always use PANEL dict ──────────────────────────────

def S_PANEL() -> str:
    return (
        f"background:{PANEL['bg']};border:1px solid {PANEL['border']};"
        f"border-radius:8px;padding:12px 14px;height:440px;overflow-y:auto;"
        f"font-family:'Courier New',monospace;font-size:13px;color:{PANEL['text']};"
        f"display:block;"
    )

def S_PANEL_TITLE() -> str:
    return (
        f"font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;"
        f"color:{PANEL['accent_blue']};border-bottom:1px solid {PANEL['border']};"
        f"padding-bottom:6px;margin-bottom:10px;display:block;"
    )

def S_REPORT() -> str:
    return (
        f"background:{PANEL['bg']};border:1px solid {PANEL['border']};"
        f"border-radius:8px;padding:14px 18px;height:540px;overflow-y:auto;"
        f"font-family:-apple-system,BlinkMacSystemFont,sans-serif;"
        f"font-size:13px;color:{PANEL['text']};margin-top:16px;display:block;"
    )

def S_HTTP() -> str:
    return (
        f"background:{PANEL['inset_bg']};border-left:3px solid {PANEL['accent_blue']};"
        f"border-radius:4px;padding:7px 10px;margin:5px 0;display:block;"
    )

def S_CARD() -> str:
    return (
        f"background:{PANEL['inset_bg']};border:1px solid {PANEL['inset_border']};"
        f"border-radius:6px;padding:8px 14px;min-width:120px;"
        f"display:inline-block;margin:4px;"
    )

def S_LBOX() -> str:
    return (
        f"background:{PANEL['inset_bg']};border-left:3px solid {PANEL['accent_blue']};"
        f"border-radius:4px;padding:10px 14px;line-height:1.6;font-size:13px;"
        f"color:{PANEL['text']};display:block;margin:4px 0 8px;"
    )

def S_RBOX() -> str:
    return (
        f"background:{PANEL['inset_bg']};border-left:3px solid {PANEL['accent_green']};"
        f"border-radius:4px;padding:10px 14px;line-height:1.6;font-size:13px;"
        f"color:{PANEL['text']};display:block;margin:4px 0 8px;"
    )

def S_SEC() -> str:
    return (
        f"font-size:10px;font-weight:700;color:{PANEL['text_dim']};text-transform:uppercase;"
        f"letter-spacing:.08em;margin:12px 0 4px;display:block;"
    )

def S_CODE() -> str:
    return (
        f"background:{PANEL['code_bg']};padding:1px 5px;border-radius:3px;"
        f"color:{PANEL['code_text']};font-family:monospace;font-size:12px;"
    )

# ── Helpers ───────────────────────────────────────────────────────────────────

def _c(text: str) -> str:
    s = S_CODE()
    return re.sub(r"`([^`]+)`", rf'<code style="{s}">\1</code>', text)

def _hcol(status: int) -> str:
    if status < 300: return PANEL["accent_green"]
    if status < 400: return PANEL["accent_yellow"]
    return PANEL["accent_red"]

# ── HTML builders — all panels always dark ────────────────────────────────────

def _reasoning_html(lines: list[str]) -> str:
    body = (
        "".join(f'<div style="line-height:1.7;padding:1px 0">{ln}</div>' for ln in lines)
        if lines else
        f'<span style="color:{PANEL["text_faint"]}">Click ▶ Run Scan to start...</span>'
    )
    return (
        f'<div style="{S_PANEL()}">'
        f'<span style="{S_PANEL_TITLE()}">🧠 Agent Reasoning</span>'
        f'{body}</div>'
    )


def _traffic_html(exchanges: list[dict]) -> str:
    if not exchanges:
        body = f'<span style="color:{PANEL["text_faint"]}">Waiting for probes...</span>'
    else:
        parts = []
        for ex in exchanges:
            label  = ex.get("label", "unknown")
            method = ex.get("method", "GET")
            url    = ex.get("url", "").replace("http://localhost:8001", "")
            status = ex.get("status_code", 0)
            ms     = ex.get("latency_ms", 0)
            bt     = ex.get("body_preview", "")[:80]
            col    = _hcol(status)
            parts.append(
                f'<div style="{S_HTTP()}">'
                f'<div style="color:{PANEL["accent_blue"]}">→ [{label}] {method} {url}</div>'
                f'<div style="color:{col}">← {status} ({ms}ms)</div>'
                f'<div style="color:{PANEL["text_dim"]};font-size:11px;margin-top:2px">{bt}</div>'
                f'</div>'
            )
        body = "".join(parts)
    return (
        f'<div style="{S_PANEL()}">'
        f'<span style="{S_PANEL_TITLE()}">📡 Live HTTP Traffic</span>'
        f'{body}</div>'
    )


def _report_html(report: dict) -> str:
    verdict    = report["finding"]["verdict"]
    severity   = report["severity"]
    confidence = report["finding"]["confidence"]
    category   = report["finding"]["owasp_category"]
    reasoning  = report["finding"]["reasoning"]
    fix        = report["finding"]["recommended_fix"]
    cves       = report["evidence"]["cve_references"]
    ex_list    = report["evidence"]["http_exchanges"]
    clean      = report["pipeline"]["clean_run"]
    agents     = " → ".join(report["pipeline"]["agents_run"])

    sev_col = {
        "HIGH"         : PANEL["accent_red"],
        "MEDIUM"       : PANEL["accent_yellow"],
        "INFORMATIONAL": PANEL["accent_green"],
    }.get(severity, PANEL["text"])
    ver_col = {
        "TRUE_POSITIVE"      : PANEL["accent_red"],
        "FALSE_POSITIVE"     : PANEL["accent_green"],
        "NEEDS_INVESTIGATION": PANEL["accent_yellow"],
    }.get(verdict, PANEL["text"])
    sev_ico = {"HIGH":"🔴","MEDIUM":"🟡","INFORMATIONAL":"🟢"}.get(severity,"⚪")
    ver_ico = {"TRUE_POSITIVE":"⚠️","FALSE_POSITIVE":"✅",
               "NEEDS_INVESTIGATION":"🔍"}.get(verdict,"❓")

    def card(lbl, val, col):
        return (
            f'<div style="{S_CARD()}">'
            f'<div style="font-size:10px;color:{PANEL["text_dim"]};text-transform:uppercase;'
            f'letter-spacing:.08em">{lbl}</div>'
            f'<div style="font-size:14px;font-weight:700;color:{col};margin-top:3px">'
            f'{val}</div></div>'
        )

    cards = (
        card("Verdict",    f"{ver_ico} {verdict}",         ver_col)             +
        card("Severity",   f"{sev_ico} {severity}",        sev_col)             +
        card("Confidence", confidence,                      PANEL["text"])       +
        card("Clean Run",  "✅ Yes" if clean else "❌ No",
             PANEL["accent_green"] if clean else PANEL["accent_red"])
    )

    cvc = {
        "HIGH"  : PANEL["accent_red"],
        "MEDIUM": PANEL["accent_yellow"],
        "LOW"   : PANEL["accent_green"],
    }
    cve_html = "".join(
        f'<span style="display:inline-block;background:{PANEL["tag_bg"]};'
        f'border:1px solid {cvc.get(c.get("severity",""), PANEL["tag_border"])};'
        f'border-radius:4px;padding:2px 8px;font-size:11px;'
        f'color:{cvc.get(c.get("severity",""), PANEL["text_dim"])};margin:2px 3px;'
        f'font-family:monospace">'
        f'{c["cve_id"]} · {c.get("severity","")} · {c.get("cvss_score","")}'
        f'</span>'
        for c in cves
    ) if cves else f'<span style="color:{PANEL["text_faint"]}">No CVEs found</span>'

    ex_rows = ""
    for ex in ex_list:
        col   = _hcol(ex["status_code"])
        short = ex["url"].replace("http://localhost:8001", "")
        ex_rows += (
            f'<div style="{S_HTTP()}">'
            f'<div style="color:{PANEL["accent_blue"]}">'
            f'[{ex["label"]}] {ex["method"]} {short}</div>'
            f'<div style="color:{col}">{ex["status_code"]} ({ex["latency_ms"]}ms)</div>'
            f'<div style="color:{PANEL["text_dim"]};font-size:11px;margin-top:2px">'
            f'{ex.get("body_preview","")[:80]}</div></div>'
        )

    return (
        f'<div style="{S_REPORT()}">'
        f'<span style="{S_PANEL_TITLE()}">📋 Final Report</span>'
        f'<div style="font-size:15px;font-weight:700;color:{PANEL["text"]};'
        f'border-bottom:1px solid {PANEL["divider"]};padding-bottom:8px;margin-bottom:14px">'
        f'📋 Final Report — {report["report_id"]}</div>'
        f'<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px">{cards}</div>'
        f'<span style="{S_SEC()}">OWASP Category</span>'
        f'<div style="color:{PANEL["accent_blue"]};font-size:13px;margin-bottom:8px">'
        f'{category}</div>'
        f'<span style="{S_SEC()}">Reasoning</span>'
        f'<div style="{S_LBOX()}">{reasoning}</div>'
        f'<span style="{S_SEC()}">Recommended Fix</span>'
        f'<div style="{S_RBOX()}">{fix}</div>'
        f'<span style="{S_SEC()}">CVE References</span>'
        f'<div style="margin:6px 0 12px">{cve_html}</div>'
        f'<span style="{S_SEC()}">HTTP Evidence</span>'
        f'{ex_rows}'
        f'<div style="color:{PANEL["text_faint"]};font-size:11px;margin-top:14px">'
        f'Generated: {report["generated_at"]} &nbsp;·&nbsp; Pipeline: {agents}'
        f'</div></div>'
    )


# ── About iframe — always dark ────────────────────────────────────────────────

def _about_iframe() -> str:
    """Always dark — uses PANEL constants directly, ignores page theme."""
    tags = [
        "Python 3.11", "LangGraph", "Azure OpenAI GPT-4.1-mini",
        "Azure Embeddings", "ChromaDB", "FastAPI", "NVD CVE API",
        "OWASP Top 10 2025", "Streamlit",
    ]
    tag_html = "".join(
        f'<span style="background:{PANEL["tag_bg"]};'
        f'border:1px solid {PANEL["tag_border"]};'
        f'border-radius:20px;padding:3px 11px;font-size:11px;'
        f'color:{PANEL["text"]};white-space:nowrap;'
        f'display:inline-block;margin:3px 3px 3px 0">{tag}</span>'
        for tag in tags
    )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  html, body {{ height:100%; background:{PANEL['inset_bg']}; }}
  body {{
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
    font-size:13px; color:{PANEL['text']};
  }}
  .box {{
    background   :{PANEL['bg']};
    border       :1px solid {PANEL['border']};
    border-radius:10px;
    padding      :24px 28px;
    height       :490px;
    overflow-y   :auto;
  }}
  .box::-webkit-scrollbar       {{ width:5px; }}
  .box::-webkit-scrollbar-track {{ background:{PANEL['inset_bg']}; }}
  .box::-webkit-scrollbar-thumb {{ background:{PANEL['scrollbar']}; border-radius:3px; }}
  .hero-name {{
    font-size:22px; font-weight:800;
    color:{PANEL['accent_blue']}; margin-bottom:2px;
  }}
  .hero-role {{
    font-size:13px; color:{PANEL['text_dim']};
    font-weight:600; margin-bottom:14px;
  }}
  .hero-pitch {{
    font-size:14px; line-height:1.75; color:{PANEL['text']};
    background:{PANEL['inset_bg']};
    border-left:3px solid {PANEL['accent_blue']};
    border-radius:4px; padding:12px 16px; margin-bottom:20px;
  }}
  .hero-pitch strong {{ color:#fff; }}
  .impact-row {{ display:flex; gap:10px; flex-wrap:wrap; margin-bottom:20px; }}
  .impact-card {{
    background:{PANEL['inset_bg']};
    border:1px solid {PANEL['inset_border']};
    border-radius:8px; padding:12px 16px;
    flex:1; min-width:110px; text-align:center;
  }}
  .impact-num   {{ font-size:22px; font-weight:800; color:{PANEL['accent_blue']}; }}
  .impact-label {{ font-size:11px; color:{PANEL['text_dim']}; margin-top:2px; line-height:1.4; }}
  .sh {{
    font-size:13px; font-weight:700; color:{PANEL['accent_blue']};
    margin:18px 0 8px; display:flex; align-items:center; gap:6px;
  }}
  .sh::after {{ content:''; flex:1; height:1px; background:{PANEL['divider']}; }}
  .agent {{
    background:{PANEL['inset_bg']};
    border-left:3px solid {PANEL['accent_blue']};
    border-radius:4px; padding:10px 14px; margin:6px 0;
    font-size:13px; line-height:1.65; color:{PANEL['text']};
  }}
  .agent .an     {{ color:{PANEL['accent_blue']}; font-weight:700; }}
  .agent .outcome {{
    display:inline-block; background:{PANEL['tag_bg']};
    border:1px solid {PANEL['accent_green']}; border-radius:3px;
    padding:1px 7px; font-size:11px; color:{PANEL['accent_green']};
    margin-left:6px; vertical-align:middle;
  }}
  .diff-row  {{ display:flex; gap:10px; flex-wrap:wrap; margin-bottom:4px; }}
  .diff-card {{
    background:{PANEL['inset_bg']};
    border:1px solid {PANEL['inset_border']};
    border-radius:6px; padding:10px 14px; flex:1; min-width:140px;
  }}
  .diff-card .icon {{ font-size:18px; margin-bottom:4px; }}
  .diff-card .dt   {{ font-size:12px; font-weight:700; color:#fff; margin-bottom:3px; }}
  .diff-card .dd   {{ font-size:11px; color:{PANEL['text_dim']}; line-height:1.5; }}
  .tags      {{ display:flex; flex-wrap:wrap; }}
  .try-text  {{ font-size:13px; line-height:1.75; color:{PANEL['text']}; }}
  .try-text strong {{ color:#fff; }}
</style>
</head>
<body>
<div class="box">

  <div class="hero-name">🔐 PentraceAI</div>
  <div class="hero-role">Built by Sanjay &nbsp;·&nbsp; AI Engineer</div>
  <div class="hero-pitch">
    An <strong>autonomous 3-agent security pipeline</strong> that does what junior
    pen-testers do manually — probe APIs, correlate CVE data, reason about
    vulnerabilities — and delivers a <strong>structured verdict in under 30 seconds</strong>,
    entirely without human input.
  </div>

  <div class="impact-row">
    <div class="impact-card">
      <div class="impact-num">3</div>
      <div class="impact-label">Specialised AI Agents chained end-to-end</div>
    </div>
    <div class="impact-card">
      <div class="impact-num">10</div>
      <div class="impact-label">OWASP Top 10 2025 categories in knowledge base</div>
    </div>
    <div class="impact-card">
      <div class="impact-num">30</div>
      <div class="impact-label">OWASP knowledge chunks in ChromaDB vector store</div>
    </div>
    <div class="impact-card">
      <div class="impact-num">&lt;30s</div>
      <div class="impact-label">Recon → Analysis → Report, fully automated</div>
    </div>
  </div>

  <div class="sh">⚡ What makes this different</div>
  <div class="diff-row">
    <div class="diff-card">
      <div class="icon">🤖</div>
      <div class="dt">Agentic Reasoning</div>
      <div class="dd">Not a rule-based scanner. GPT-4.1-mini reasons over real HTTP evidence like a human analyst.</div>
    </div>
    <div class="diff-card">
      <div class="icon">🗄️</div>
      <div class="dt">RAG over OWASP</div>
      <div class="dd">Semantic search over a structured OWASP 2025 knowledge base — context-aware, not keyword-matched.</div>
    </div>
    <div class="diff-card">
      <div class="icon">📡</div>
      <div class="dt">Live CVE Intel</div>
      <div class="dd">Hits the NVD API in real time. Every report includes actual CVE IDs with CVSS scores.</div>
    </div>
  </div>

  <div class="sh">⚙️ The 3-Agent Pipeline</div>
  <div class="agent">
    <span class="an">1. ReconAgent</span>
    <span class="outcome">Probes + CVE fetch</span><br>
    Fires real HTTP requests as both attacker and legitimate user. Records status
    codes, latency, and response bodies. Simultaneously queries NVD for relevant CVEs.
  </div>
  <div class="agent">
    <span class="an">2. AnalysisAgent</span>
    <span class="outcome">GPT-4 verdict</span><br>
    Runs semantic search over the OWASP knowledge base. Feeds HTTP evidence +
    OWASP context into GPT-4.1-mini. Returns TRUE_POSITIVE · FALSE_POSITIVE ·
    NEEDS_INVESTIGATION with confidence level.
  </div>
  <div class="agent">
    <span class="an">3. ReportAgent</span>
    <span class="outcome">Structured report</span><br>
    Validates full pipeline state. Generates report with verdict, severity,
    OWASP category, reasoning, remediation steps, CVE references, and HTTP evidence.
  </div>

  <div class="sh">🛠️ Tech Stack</div>
  <div class="tags">{tag_html}</div>

  <div class="sh">🚀 Try it now</div>
  <div class="try-text">
    Pick a scenario —
    <strong style="color:{PANEL['accent_red']}">BOLA</strong>,
    <strong style="color:{PANEL['accent_yellow']}">Broken Auth</strong>, or
    <strong style="color:{PANEL['accent_green']}">False Positive</strong> — and hit
    <strong>▶ Run Scan</strong>. Left panel streams agent reasoning live.
    Right panel shows real HTTP exchanges. Report appears below when complete.
  </div>

</div>
</body>
</html>"""


# ── Page ──────────────────────────────────────────────────────────────────────

_inject_bg()

# Theme toggle — top right
_, toggle_col = st.columns([11, 1])
with toggle_col:
    label = "☀️ Light" if st.session_state.dark_mode else "🌙 Dark"
    if st.button(label, use_container_width=True):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

p = P()
st.markdown(
    f'<p style="font-size:2rem;font-weight:800;color:{p["title"]};margin-bottom:0">'
    f'🔐 PentraceAI</p>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<p style="font-size:.88rem;color:{p["subtitle"]};margin-top:0;margin-bottom:1.2rem">'
    f'Agentic API Vulnerability Scanner &nbsp;·&nbsp; '
    f'ReconAgent → AnalysisAgent → ReportAgent &nbsp;·&nbsp; '
    f'OWASP Top 10 2025 &nbsp;·&nbsp; Azure OpenAI &nbsp;·&nbsp; NVD CVE Correlation</p>',
    unsafe_allow_html=True,
)

# ── Controls ──────────────────────────────────────────────────────────────────

col_sel, col_run, col_about, _ = st.columns([2, 1, 1, 3])

with col_sel:
    scenario_labels = {k: v["label"] for k, v in SCAN_SCENARIOS.items()}
    selected = st.selectbox(
        "Scenario",
        options=list(scenario_labels.keys()),
        format_func=lambda k: scenario_labels[k],
        label_visibility="collapsed",
    )

with col_run:
    run_clicked = st.button("▶ Run Scan", type="primary", use_container_width=True)

with col_about:
    about_clicked = st.button("ℹ️ About", use_container_width=True)

# ── About toggle ──────────────────────────────────────────────────────────────

if "show_about" not in st.session_state:
    st.session_state.show_about = False

if about_clicked:
    st.session_state.show_about = not st.session_state.show_about

if st.session_state.show_about:
    components.html(_about_iframe(), height=510, scrolling=False)

st.markdown("---")

# ── Scan panels ───────────────────────────────────────────────────────────────

left_col, right_col = st.columns(2)
with left_col:
    r_slot = st.empty()
with right_col:
    t_slot = st.empty()

report_slot = st.empty()


def show_r(lines):
    r_slot.markdown(_reasoning_html(lines), unsafe_allow_html=True)

def show_t(exchanges):
    t_slot.markdown(_traffic_html(exchanges), unsafe_allow_html=True)

def show_rep(report):
    report_slot.markdown(_report_html(report), unsafe_allow_html=True)


# ── Initial state ─────────────────────────────────────────────────────────────

show_r([])
show_t([])

# ── Live run ──────────────────────────────────────────────────────────────────

if run_clicked:
    rl: list[str] = []
    ex: list[dict] = []

    show_r([f'<span style="color:{PANEL["accent_blue"]}">⚡ Pipeline starting...</span>'])
    show_t([])

    for event in run_scan_streaming(scenario=selected):
        ev = event["type"]

        if ev == "agent_start":
            rl.append(
                f'<span style="color:{PANEL["accent_blue"]};font-weight:700;'
                f'display:block;margin-top:8px">'
                f'── Stage {event["stage"]}/3: {event["agent"]} ──</span>'
            )
            show_r(rl)

        elif ev == "agent_step":
            rl.append(
                f'<div style="line-height:1.7;padding:1px 0">'
                f'&nbsp;&nbsp;{_c(event["message"])}</div>'
            )
            show_r(rl)

        elif ev == "http_exchange":
            ex.append(event["data"])
            show_t(ex)

        elif ev == "agent_done":
            rl.append(
                f'<span style="color:{PANEL["accent_green"]};font-size:12px;display:block">'
                f'&nbsp;&nbsp;✓ {event["summary"]}</span>'
            )
            rl.append(f'<div style="color:{PANEL["divider"]}">&nbsp;</div>')
            show_r(rl)

        elif ev == "pipeline_done":
            rl.append(
                f'<span style="color:{PANEL["accent_green"]};font-weight:700;display:block">'
                f'🏁 Pipeline complete</span>'
            )
            show_r(rl)
            rep = event["state"].get("report")
            if rep:
                show_rep(rep)

        elif ev == "error":
            rl.append(
                f'<span style="color:{PANEL["accent_red"]};display:block">'
                f'❌ {event["message"]}</span>'
            )
            show_r(rl)
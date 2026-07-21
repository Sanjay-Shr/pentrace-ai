---
title: PentraceAI
emoji: 🔐
colorFrom: blue
colorTo: red
sdk: docker
app_port: 7860
pinned: true
license: mit
---

# 🔐 PentraceAI — Agentic API Vulnerability Scanner

An autonomous 3-agent AI security pipeline that probes APIs for OWASP vulnerabilities,
correlates real CVE data, and delivers a structured verdict — fully automated, under 30 seconds.

## 🤖 The 3-Agent Pipeline

| Agent | Role |
|---|---|
| **ReconAgent** | Fires real HTTP probes as attacker + legitimate user. Fetches live CVEs from NVD. |
| **AnalysisAgent** | Semantic RAG over OWASP Top 10 2025 knowledge base. GPT-4.1-mini verdict. |
| **ReportAgent** | Structured report — verdict, severity, OWASP category, remediation, CVE references. |

## 🚀 Try It

Pick a scenario and hit **▶ Run Scan**:

- 🔴 **BOLA** — Broken Object Level Authorization (A01:2025)
- 🟡 **Broken Auth** — Broken Authentication (A02:2025)  
- 🟢 **False Positive** — Legitimate request correctly cleared

## 🛠️ Tech Stack

- **Python 3.11** · **LangGraph** · **Azure OpenAI GPT-4.1-mini**
- **Azure Embeddings** · **ChromaDB** · **FastAPI** · **Streamlit**
- **NVD CVE API** · **OWASP Top 10 2025**

## ⚙️ Architecture

```
User → Streamlit UI
         ↓
    Orchestrator (LangGraph)
         ↓
    ReconAgent → FastAPI Sandbox + NVD API
         ↓
    AnalysisAgent → ChromaDB (OWASP RAG) + Azure OpenAI
         ↓
    ReportAgent → Structured JSON Report
         ↓
    Streamlit UI ← streaming events
```

## 👤 Built by

**Sanjay** — AI Engineer
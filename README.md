# 🔐 PentraceAI — Autonomous API Vulnerability Scanner

An AI agent that probes API endpoints for OWASP vulnerabilities, reasons over a security knowledge base, correlates real CVEs, and delivers a structured verdict — fully autonomous, no human in the loop.

**3 agents. 3 scenarios tested. 3 for 3.**

🔴 [Live Demo](http://100.54.198.73:8501)

---

## The Problem

API vulnerability scanning today is mostly manual. A security engineer hits endpoints, checks responses, cross-references OWASP, looks up CVEs, and writes a report. It takes hours and depends entirely on the engineer's knowledge and attention.

PentraceAI automates that entire reasoning loop.

---

## How It Works

```
Target API Endpoint
       │
       ▼
┌─────────────────┐
│   ReconAgent    │  ← Fires attacker + legitimate HTTP probes
│                 │    Fetches live CVEs from NVD API
└────────┬────────┘
         │  HTTP exchanges + CVE data
         ▼
┌─────────────────┐
│ AnalysisAgent   │  ← Semantic search over OWASP Top 10 2025 (ChromaDB)
│                 │    GPT-4.1-mini reasons over evidence
└────────┬────────┘
         │  verdict + confidence + OWASP mapping
         ▼
┌─────────────────┐
│  ReportAgent    │  ← Structured report with severity, CVEs, remediation
└─────────────────┘
```

---

## The 3 Agents

### ReconAgent
- Probes the target endpoint twice — once as a legitimate user, once as an attacker with a stolen/wrong token
- Records full HTTP exchanges (method, headers, status, response body)
- Hits the NVD API in real time and pulls matching CVEs with severity scores

### AnalysisAgent
- Loads an OWASP Top 10 2025 knowledge base into ChromaDB (30 indexed chunks)
- Runs semantic retrieval over the HTTP evidence to find relevant OWASP context
- Sends the full evidence package to GPT-4.1-mini for structured reasoning
- Returns a verdict: `TRUE_POSITIVE` or `FALSE_POSITIVE` with confidence level

### ReportAgent
- Validates the analysis output
- Produces a structured report with:
  - Verdict + confidence (HIGH / MEDIUM / LOW)
  - OWASP category (e.g. A01:2025 — Broken Access Control)
  - Severity rating
  - CVE references with scores
  - Concrete remediation recommendation
  - Full HTTP exchange log

---

## Test Results

| Scenario | Expected | PentraceAI Verdict | Confidence |
|---|---|---|---|
| BOLA — user accesses another user's order | TRUE_POSITIVE | ✅ TRUE_POSITIVE | HIGH |
| Broken Auth — expired token accepted | TRUE_POSITIVE | ✅ TRUE_POSITIVE | HIGH |
| Legitimate request with valid token | FALSE_POSITIVE | ✅ FALSE_POSITIVE | HIGH |

**3 for 3. Including the false positive — it didn't cry wolf.**

Real CVE pulled during BOLA scan: **CVE with CVSS score 8.8 (HIGH severity)** from NVD live API.

---

## Architecture Decisions & Trade-offs

**Why ChromaDB over Pinecone/Qdrant?**
Local, zero-latency, no API cost for retrieval. For a knowledge base of 30 OWASP chunks this is the right call. Upgrade to Pinecone when the knowledge base scales beyond local memory.

**Why GPT-4.1-mini over GPT-4o?**
Cost-aware. The reasoning task here is structured and evidence-bound — it doesn't need a frontier model. GPT-4.1-mini handles it correctly at a fraction of the cost.

**Why a 3-agent split instead of one big prompt?**
Each agent has a single responsibility and a clean state boundary. ReconAgent doesn't reason. AnalysisAgent doesn't probe. This makes failures traceable and agents independently testable.

**What this doesn't do (yet)**
- Doesn't scan authenticated multi-step flows (OAuth, session chaining)
- Knowledge base is OWASP Top 10 only — not full CVE corpus
- Single endpoint per scan — no crawling

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent orchestration | LangGraph |
| LLM | Azure OpenAI GPT-4.1-mini |
| Embeddings | Azure OpenAI Embeddings |
| Vector store | ChromaDB |
| CVE data | NVD API (live) |
| Security knowledge | OWASP Top 10 2025 |
| Backend / sandbox | FastAPI |
| Frontend | Streamlit |
| Runtime | Python 3.11 · Docker |

---

## Run Locally

```bash
git clone https://github.com/Sanjay-Shr/pentrace-ai
cd pentrace-ai
pip install -r requirements.txt
```

Set your environment variables:

```env
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini
AZURE_EMBEDDING_DEPLOYMENT=your_embedding_model
```

Start the sandbox API:

```bash
uvicorn sandbox.main:app --port 8001
```

Run a scan:

```bash
python main.py --scenario bola
python main.py --scenario broken_auth
python main.py --scenario false_positive
```

Or launch the UI:

```bash
streamlit run streamlit_app.py
```

---

## Built by

**Sanjay Sharma** — AI Engineer  
[LinkedIn](http://www.linkedin.com/in/sanjaysharmau23/) · +91 7204790547 · sanjaysharmau23@gmail.com
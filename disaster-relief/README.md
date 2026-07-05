# 🌊 Kerala Disaster Relief Resource Agent

An AI-powered multi-agent disaster relief dispatcher built with **Google ADK (Agent Development Kit)** and **Gradio**. The system intelligently classifies emergency requests and routes them to specialized agents — for shelter lookup, medical assistance, critical emergency escalation, or general introductions — using real-time streaming.

---

## 🧠 What This Does

When a user describes their disaster situation (e.g., *"My house in Wayanad is flooded and I need shelter"*), the system:

1. **Classifies** the request using a structured `ClassificationResult` schema (route, priority, vulnerability, disaster type)
2. **Routes** the request to one of four specialized agents:
   - 🏕️ **Shelter Agent** — finds active relief camps by district (Wayanad, Alappuzha, Ernakulam, Idukki, Kozhikode, Thrissur)
   - 🏥 **Medical Agent** — locates hospitals with emergency/ICU support by district
   - 🚨 **Emergency Agent** — provides critical state and NGO helplines for immediate rescue
   - 👋 **General Agent** — greets users and introduces portal resources for conversational/greeting inputs
3. **Escalates automatically** if the user mentions a vulnerable person (pregnant, elderly, infant, disabled, unconscious, chest pain, blocked roads) or if priority is `critical` (except for shelter displacement queries, which are routed to the Shelter Agent to find immediate shelter camps)
4. **Fuzzy Matches spelling typos and partial queries** for districts (e.g. "waynad" or "alapuzha" map correctly to their standard mock targets)
5. **Streams** the final agent's response to the Gradio chat UI without duplicating outputs or revealing internal classifier JSON data

---

## 🏗️ Architecture

```
User Message
     │
     ▼
┌─────────────────────┐
│  classifier_agent   │  ← Gemini (structured output: ClassificationResult)
│  (internal only)    │
└─────────────────────┘
     │
     ▼
┌─────────────────────┐
│  route_decision()   │  ← Python function: applies escalation rules, routes
└─────────────────────┘
     │
  ┌──┴──────────────┬──────────────────┬─────────────────┐
  ▼                 ▼                  ▼                 ▼
shelter_agent   medical_agent   emergency_agent    general_agent
  (tools:          (tools:          (tools:            (greet and
  lookup_shelters) lookup_hospitals) lookup_helplines)  onboard)
```

**Framework:** Google ADK `Workflow` with `Agent` nodes and a Python routing function  
**UI:** Gradio `ChatInterface` with server-sent event (SSE) streaming  
**Auth:** Google AI Studio (`GOOGLE_API_KEY`) — no Vertex AI required  

---

## 📁 Project Structure

```
disaster-relief/
├── app/
│   ├── agent.py          # Workflow definition, agents, routing logic, schemas
│   ├── prompts.py        # System instructions for all 5 agents (including greeting agent)
│   ├── tools.py          # Fuzzy matching tools: lookup_shelters, lookup_hospitals, lookup_helplines
│   ├── ui.py             # Gradio UI with custom streaming, error handling, Gradio 6.0 fix
│   ├── fast_api_app.py   # FastAPI backend (alternative to Gradio)
│   └── data/
│       ├── shelters.json   # Mock Kerala shelter database (6 districts, capacities, contacts, addresses)
│       ├── hospitals.json  # Mock Kerala hospital database (6 districts, specialities, ICUs, addresses)
│       └── helplines.json  # District emergency control rooms and NGO helplines
├── tests/                # Integration and unit tests
├── .env.example          # Environment variable template
├── pyproject.toml        # Project dependencies (uv-ready)
├── Dockerfile            # Container definition
└── GEMINI.md             # AI dev assistant context
```

---

## ⚙️ Setup

### 1. Prerequisites

- Python 3.11+
- A [Google AI Studio API key](https://aistudio.google.com/app/apikey)

### 2. Configure Environment

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` and add your API key:
   ```env
   GOOGLE_API_KEY=your-api-key-here
   GOOGLE_GENAI_USE_VERTEXAI=False
   GEMINI_MODEL=gemini-2.0-flash
   ```

### 3. Install Dependencies
You can install dependencies inside a virtual environment using the standard pip package manager:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e . --pre
```
*(Note: `--pre` is required to download pre-release telemetry packages compatible with Python versions below 3.13)*

### 4. Run the Gradio UI

```bash
python app/ui.py
```
Open [http://localhost:8080](http://localhost:8080) in your browser.

---

## 💬 Example Queries

| Query | Routes To | Expected Action |
|---|---|---|
| `"hello"` | 👋 General Agent | Greets user and introduces relief capabilities |
| `"My house is flooded. I need a safe place to stay tonight."` | 🏕️ Shelter Agent | Prompts for district, then returns camp coordinates |
| `"Where is the nearest relief camp in Kozhikode?"` | 🏕️ Shelter Agent | Returns mock Kozhikode camp address and phone |
| `"My grandmother needs emergency insulin refills."` | 🏥 Medical Agent | Recommends district hospitals with ICU support |
| `"I am pregnant and roads in Idukki are blocked!"` | 🚨 Emergency Agent | Auto-escalated (vulnerability) to show direct helplines |
| `"Chest pain."` | 🚨 Emergency Agent | Auto-escalated to show ambulance and KSDMA numbers |

---

## 🔑 Key Implementation Details

### Multi-Agent Workflow (ADK)
The `Workflow` in [`app/agent.py`](app/agent.py) orchestrates the dispatcher workflow. The `route_decision` Python function applies escalation checks:
- It triggers a routing override to `"emergency"` if priority is `"critical"` (and the route is not a standard shelter inquiry) or if a vulnerable person keyword matches.

### Bulletproof Streaming & UI Deduplication
The Gradio UI in [`app/ui.py`](app/ui.py) implements custom SSE chunk reconstruction:
- It maintains `node_outputs = {}` mapping node paths to active text blocks.
- If an event is partial, it accumulates the delta string.
- If an event is cumulative (`partial=False`), it replaces the buffer for that node.
- This prevents double-printing sentences in the chat window.

### Fuzzy Spelling Matching
In [`app/tools.py`](app/tools.py), lookups support fuzzy searching using Python's `difflib.get_close_matches` with a `0.5` threshold. It also searches for substring matches, making it spelling-tolerant.

---

## 🗓️ Development Log

### Phase 10 — Teammate Finish & Stabilization (Current)
* **General Routing Support**: Added `general_agent` to handle generic conversational queries like `"hello"`, introducing the system instead of forcing a medical or shelter form.
* **Fuzzy Spelling & Partial District Matches**: Updated lookups in `app/tools.py` using `difflib` to match district inputs with minor typos (e.g. `"waynad"` $\rightarrow$ `"Wayanad"`) or partials (e.g. `"koz"` $\rightarrow$ `"Kozhikode"`).
* **Fix Duplicate UI Responses**: Replaced `yielded_nodes` filter in `ui.py` with dictionary-based node reconstruction, addressing duplicate text rendering in the Gradio chat interface.
* **Gradio 6.0 Warnings**: Relocated `theme` setup to `.launch(...)` parameters to comply with Gradio 6.0 requirements.
* **Overriding Route Fix**: Refined route escalation rules in `agent.py` to ensure high-priority shelter requests (like *"house flooded"*) are not hijacked into the emergency helpline display.
* **Expanded mock data**: Added Kozhikode and Thrissur datasets with addresses, coordinate numbers, and phone contacts in JSON mock files.

---

## 🔮 Roadmap: RAG (Retrieval-Augmented Generation)

Once the MVP is verified, the next phase is to build the Knowledge Base Pipeline:
1. Create a `knowledge_base/` directory containing disaster recovery manuals.
2. Build a local document loader, chunking logic, and store vectors using a database.
3. Hook up a RAG-powered Guidance Agent to answer general disaster preparedness questions directly from KSDMA manuals.

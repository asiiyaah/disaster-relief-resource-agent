# 🌊 Kerala Disaster Relief Resource Agent

An AI-powered multi-agent disaster relief dispatcher built with **Google ADK (Agent Development Kit)** and **Gradio**. The system intelligently classifies emergency requests and routes them to specialized agents — for shelter lookup, medical assistance, or critical emergency escalation — using real-time streaming.

---

## 🧠 What This Does

When a user describes their disaster situation (e.g., *"My house in Wayanad is flooded and I need shelter"*), the system:

1. **Classifies** the request using a structured `ClassificationResult` schema (route, priority, vulnerability, disaster type)
2. **Routes** the request to one of three specialized agents:
   - 🏕️ **Shelter Agent** — finds active relief camps by district
   - 🏥 **Medical Agent** — locates hospitals with emergency support
   - 🚨 **Emergency Agent** — provides critical helplines and immediate safety actions
3. **Escalates automatically** if the user mentions a vulnerable person (pregnant, elderly, infant, disabled, unconscious, chest pain, blocked roads) or if priority is `critical`
4. **Streams** the final agent's response to the Gradio chat UI — internal routing JSON is hidden from the user

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
  ┌──┴──────────────┬──────────────────┐
  ▼                 ▼                  ▼
shelter_agent   medical_agent   emergency_agent
  (tools:          (tools:          (tools:
  lookup_shelters) lookup_hospitals) lookup_helplines)
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
│   ├── prompts.py        # System instructions for all 4 agents
│   ├── tools.py          # Tool functions: lookup_shelters, lookup_hospitals, lookup_helplines
│   ├── ui.py             # Gradio UI with streaming, classifier output filtering, dedup logic
│   ├── fast_api_app.py   # FastAPI backend (alternative to Gradio)
│   └── data/
│       ├── shelters.json   # Mock Kerala shelter database
│       ├── hospitals.json  # Mock Kerala hospital database
│       └── helplines.json  # Emergency helpline numbers
├── tests/                # Unit and integration tests
├── .env.example          # Environment variable template
├── pyproject.toml        # Project dependencies (uv)
├── Dockerfile            # Container definition
└── GEMINI.md             # AI dev assistant context
```

---

## ⚙️ Setup

### 1. Prerequisites

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/) (package manager)
- A [Google AI Studio API key](https://aistudio.google.com/app/apikey)

### 2. Install dependencies

```bash
cd disaster-relief
uv sync
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
GOOGLE_API_KEY=your-api-key-here
GOOGLE_GENAI_USE_VERTEXAI=False
GEMINI_MODEL=gemini-2.5-flash
```

### 4. Run the Gradio UI

```bash
uv run python app/ui.py
```

Open [http://localhost:8080](http://localhost:8080) in your browser.

To use a custom port:

```bash
$env:GRADIO_SERVER_PORT="8081"; uv run python app/ui.py   # PowerShell
GRADIO_SERVER_PORT=8081 uv run python app/ui.py           # bash/zsh
```

---

## 💬 Example Queries

| Query | Routes To |
|-------|-----------|
| `My house is flooded. I need a safe place to stay tonight.` | 🏕️ Shelter Agent |
| `Where is the nearest relief camp in Wayanad?` | 🏕️ Shelter Agent |
| `My grandmother in Alappuzha needs emergency insulin refills.` | 🏥 Medical Agent |
| `I am pregnant and roads in Idukki are blocked due to landslides!` | 🚨 Emergency Agent (auto-escalated) |
| `Elderly man unconscious, need immediate help in Ernakulam.` | 🚨 Emergency Agent (auto-escalated) |

---

## 🔑 Key Implementation Details

### Multi-Agent Workflow (ADK)

The `Workflow` in [`app/agent.py`](app/agent.py) chains:
- `START → classifier_agent → route_decision → {shelter|medical|emergency}_agent`

The `route_decision` Python function intercepts the classifier's structured output, applies escalation overrides, and returns an `Event` with the correct `route` key.

### Streaming & UI Filtering

The Gradio UI ([`app/ui.py`](app/ui.py)) uses SSE streaming with two key protections:
1. **Classifier suppression** — events from `classifier_agent` are filtered out so internal JSON is never shown
2. **Deduplication** — ADK emits both `partial=True` chunks and a `partial=False` final aggregated event per node; `yielded_nodes` set tracks which nodes have already streamed to skip the final duplicate

### Escalation Logic

Automatic escalation to `emergency_agent` is triggered if:
- `priority == "critical"` — OR —
- `vulnerable_person` is one of: `pregnant`, `infant`, `elderly`, `disabled`, `unconscious`, `chest pain`, `blocked roads`

### Rate Limit Handling

The UI catches `429 RESOURCE_EXHAUSTED` errors from the Gemini API and surfaces a user-friendly message instead of a raw stack trace.

---

## 🚀 Running with FastAPI (Alternative)

```bash
uv run uvicorn app.fast_api_app:app --reload --port 8080
```

---

## 🐳 Docker

```bash
docker build -t disaster-relief .
docker run -e GOOGLE_API_KEY=your-key -p 8080:8080 disaster-relief
```

---

## 📝 Development Notes

- Uses `google-adk` for the multi-agent orchestration layer
- Uses `google-genai` SDK for direct Gemini API access
- All data files (`shelters.json`, `hospitals.json`, `helplines.json`) are mock data for Kerala districts: Wayanad, Alappuzha, Ernakulam, Idukki
- The `.env` file is git-ignored — never commit real API keys

---

## 🗓️ Development Log — What We Built

A chronological record of everything built in this session.

---

### ✅ Phase 1 — Project Scaffold
- Initialized project with `google-agents-cli scaffold`
- Set up `uv` as the package manager with `pyproject.toml`
- Configured environment variables via `.env` (API key, model selection, Vertex AI toggle)
- Established folder structure: `app/`, `tests/`, `docs/`

---

### ✅ Phase 2 — Classifier Agent
- Defined `ClassificationResult` Pydantic schema with fields:
  - `route`: `"shelter" | "medical" | "emergency"`
  - `priority`: `"low" | "medium" | "high" | "critical"`
  - `vulnerable_person`: detects pregnant, elderly, infant, disabled, etc.
  - `disaster_type`: flood, landslide, cyclone, heavy rain
- Built `classifier_agent` using ADK `Agent` with `output_schema=ClassificationResult`
- Wrote detailed `CLASSIFIER_INSTRUCTION` prompt with classification rules

---

### ✅ Phase 3 — Shelter Agent
- Built `shelter_agent` with `lookup_shelters(district)` tool
- Created `app/data/shelters.json` — mock database of Kerala relief camps (Wayanad, Alappuzha, Ernakulam, Idukki)
- Wrote `SHELTER_INSTRUCTION` prompt: finds camps, gives evacuation guidance, lists essential items to pack

---

### ✅ Phase 4 — Medical Agent
- Built `medical_agent` with `lookup_hospitals(district)` tool
- Created `app/data/hospitals.json` — mock database of Kerala hospitals with ICU/emergency support
- Wrote `MEDICAL_INSTRUCTION` prompt: recommends hospitals, gives first-aid advice, lists emergency numbers (108, 1056)

---

### ✅ Phase 5 — Emergency Escalation Agent
- Built `emergency_agent` with `lookup_helplines()` tool
- Created `app/data/helplines.json` — state and NGO emergency helpline numbers
- Wrote `EMERGENCY_INSTRUCTION` prompt: critical alert, immediate safety actions, Police (100), Fire (101), KSDMA (1078)
- Implemented automatic escalation in `route_decision()`:
  - Triggers if `priority == "critical"` **or** if `vulnerable_person` is in: `{pregnant, infant, elderly, disabled, unconscious, chest pain, blocked roads}`

---

### ✅ Phase 6 — ADK Workflow & Routing
- Composed all agents into a `Workflow` with edges:
  ```
  START → classifier_agent → route_decision() → {shelter|medical|emergency}_agent
  ```
- `route_decision()` is a pure Python function that reads classifier output from `ctx.state`, applies escalation overrides, and returns an `Event` with the routing key

---

### ✅ Phase 7 — Gradio Chat UI
- Built `app/ui.py` with `gr.ChatInterface` and SSE streaming (`StreamingMode.SSE`)
- Premium Gradio theme using `Outfit` Google Font, teal/slate color palette
- Sidebar with emergency helpline numbers and vulnerability escalation info
- Example queries pre-loaded in the chat input

---

### ✅ Phase 8 — Streaming Bug Fixes
- **Bug 1 — Classifier JSON shown to user:** ADK was streaming `classifier_agent` node events to the UI. Fixed by filtering events where `event.node_info.path` contains `"classifier_agent"`.
- **Bug 2 — Response duplicated in chat:** ADK emits both `partial=True` (incremental chunks) and `partial=False` (final aggregated event) per node. Fixed using a `yielded_nodes: set` — if a node has already streamed partials, its final event is skipped.
- **Bug 3 — Rate limit (429) raw error shown:** Caught `RESOURCE_EXHAUSTED` in both the event loop and exception handler; replaced with a friendly retry message.

---

### ✅ Phase 9 — API Key & Auth Debugging
- Diagnosed `429 RESOURCE_EXHAUSTED` caused by free-tier quota exhaustion on `gemini-2.5-flash`
- Confirmed `GOOGLE_API_KEY` from `.env` is correctly picked up by ADK via `load_dotenv(override=True)`
- Verified authentication flow using a standalone `google-genai` test script
- Resolved by rotating to a new API key with available quota

---

## ⏳ Pending / Roadmap

The following features are planned but **not yet implemented**:

### 🔜 Near-Term
| # | Feature | Notes |
|---|---------|-------|
| 1 | **Unit & Integration Tests** | `tests/` folder exists but tests are not written yet |
| 2 | **Real shelter/hospital data** | Currently using mock JSON — integrate live government data APIs |
| 3 | **Multi-district support** | Only 4 districts mocked: Wayanad, Alappuzha, Ernakulam, Idukki |
| 4 | **Session persistence** | Sessions are in-memory only; lost on server restart |
| 5 | **Conversation memory** | Agents don't remember previous turns within a session |

### 🔮 Future Phases
| # | Feature | Notes |
|---|---------|-------|
| 6 | **RAG (Retrieval-Augmented Generation)** | Index official Kerala KSDMA documents for grounded answers |
| 7 | **Google Maps integration** | Show shelter/hospital locations on a map |
| 8 | **Live weather & flood data** | Integrate IMD / KSDMA weather API feeds |
| 9 | **SMS fallback** | Twilio/MSG91 integration for users without internet |
| 10 | **Multilingual support** | Malayalam language support for local citizens |
| 11 | **NGO real-time APIs** | Connect to volunteer networks and supply databases |
| 12 | **Relief Supplies Agent** | New agent for food, water, medicine supply requests |
| 13 | **Deployment to Cloud Run** | `agents-cli deploy` to GCP Cloud Run with Terraform |
| 14 | **CI/CD pipeline** | GitHub Actions for lint, test, and deploy on push |
| 15 | **Admin dashboard** | Real-time request volume, agent routing stats, error rates |

---

## 📄 License

MIT

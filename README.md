# ChiLife Agent

A personal AI lifestyle concierge for Chicago. Tell it your vibe, budget, and what you're in the mood for — it gives you 3 fully-planned evenings.

## Features

- Personalized plans based on neighborhood, vibe, budget, group context, food preference, and interests
- Real Chicago venues and events (mock data for MVP)
- Weather-aware recommendations
- LLM-powered suggestions (OpenAI-compatible) with full offline fallback
- Persistent memory: saved neighborhoods, vibes, and feedback via SQLite
- Thumbs up/down feedback loop

## Quick Start

### 1. Clone and set up a virtual environment

```bash
git clone <repo-url>
cd chilife-agent
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment (optional)

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
# The app runs fully offline without a key using rule-based recommendations
```

### 4. Run the app

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

## Project Structure

```
chilife-agent/
├── app.py                      # Streamlit UI
├── requirements.txt
├── .env.example
├── src/
│   ├── agents/
│   │   ├── lifestyle_agent.py  # Core agent loop
│   │   └── prompts.py          # LLM prompt templates
│   ├── services/
│   │   ├── weather_service.py
│   │   ├── events_service.py
│   │   ├── places_service.py
│   │   └── memory_service.py
│   ├── models/
│   │   └── schemas.py          # Pydantic models
│   └── data/
│       ├── mock_events.json
│       └── mock_places.json
├── db/
│   └── database.py             # SQLite helpers
└── docs/
    ├── PROJECT_OVERVIEW.md
    ├── ARCHITECTURE.md
    ├── AGENT_DESIGN.md
    ├── MVP_SCOPE.md
    ├── ROADMAP.md
    └── API_OPTIONS.md
```

## How It Works

1. **Observe** — User fills out the sidebar form
2. **Gather** — Agent loads preferences from SQLite, fetches weather, filters events and places
3. **Reason** — LLM (or rule-based fallback) evaluates options
4. **Generate** — 3 distinct plans with itinerary, budget estimate, and confidence score
5. **Save** — Plans and feedback stored in SQLite for future personalization

## Neighborhoods

Logan Square · Wicker Park · Lakeview · Lincoln Park · Pilsen · West Loop · River North · Uptown

## LLM Compatibility

The app uses an OpenAI-compatible client. Works with:
- OpenAI (GPT-4o, GPT-4o-mini)
- Anthropic Claude via compatible proxy
- Groq, Together AI, Ollama (local)

See `docs/API_OPTIONS.md` for details.

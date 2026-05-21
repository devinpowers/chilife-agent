# Architecture

## System Diagram

```mermaid
graph TB
    subgraph UI["Streamlit UI (app.py)"]
        FORM[User Input Form]
        PLANS[Plan Display Cards]
        FB[Feedback Buttons]
    end

    subgraph AGENT["LifestyleAgent"]
        OBS[1. Observe]
        GATHER[2. Gather Context]
        REASON[3. Reason]
        GEN[4. Generate Plans]
        SAVE[5. Save Memory]
    end

    subgraph SERVICES["Services"]
        WX[WeatherService]
        EVT[EventsService]
        PLC[PlacesService]
        MEM[MemoryService]
    end

    subgraph DATA["Data Layer"]
        MOCK_E[mock_events.json]
        MOCK_P[mock_places.json]
        SQLITE[(SQLite DB)]
    end

    subgraph LLM["LLM Layer"]
        OPENAI[OpenAI-compatible API]
        FALLBACK[Rule-Based Engine]
    end

    FORM -->|UserRequest| OBS
    OBS --> GATHER
    GATHER --> WX
    GATHER --> EVT
    GATHER --> PLC
    GATHER --> MEM

    WX -->|WeatherContext| REASON
    EVT -->|EventResult list| REASON
    PLC -->|PlaceResult list| REASON
    MEM -->|UserPreferences| REASON

    MOCK_E --> EVT
    MOCK_P --> PLC
    SQLITE --> MEM

    REASON -->|AgentContext| GEN
    GEN --> OPENAI
    GEN --> FALLBACK
    GEN -->|PlanSet| SAVE
    SAVE --> SQLITE

    GEN -->|PlanSet| PLANS
    FB -->|Feedback| SAVE
```

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant Streamlit
    participant Agent
    participant Services
    participant DB
    participant LLM

    User->>Streamlit: Fill form + click "Find My Night"
    Streamlit->>Agent: generate_plans(UserRequest)

    Agent->>Services: get_weather(date_context)
    Services-->>Agent: WeatherContext

    Agent->>DB: load_preferences(user_id)
    DB-->>Agent: UserPreferences

    Agent->>Services: search_events(request, weather)
    Services-->>Agent: List[EventResult]

    Agent->>Services: search_places(request, weather)
    Services-->>Agent: List[PlaceResult]

    Agent->>LLM: build_plan_prompt(AgentContext)
    alt API key present
        LLM-->>Agent: JSON plan array
    else No API key
        Agent->>Agent: rule_based_generate()
    end

    Agent->>DB: record_plans(plans)
    Agent-->>Streamlit: PlanSet

    Streamlit->>User: Display 3 plan cards

    User->>Streamlit: Thumbs up / save neighborhood
    Streamlit->>Agent: save_feedback(Feedback)
    Agent->>DB: record_feedback() + update preferences
```

## Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| `app.py` | UI rendering, session state, user input collection |
| `LifestyleAgent` | Orchestrates the full agent loop |
| `WeatherService` | Returns seasonal Chicago weather context |
| `EventsService` | Filters and scores mock events by user request |
| `PlacesService` | Filters and scores mock venues/restaurants |
| `MemoryService` | Read/write interface to SQLite |
| `database.py` | Raw SQLite helpers (no ORM) |
| `schemas.py` | Pydantic models for all data structures |
| `prompts.py` | LLM prompt assembly |

## Key Design Decisions

**No ORM** — SQLite is accessed directly for simplicity. At MVP scale this is faster to read and debug.

**Pydantic models everywhere** — All inter-component data uses typed Pydantic models, catching errors early.

**LLM is optional** — The rule-based fallback produces good plans without any API dependency, making the app always runnable.

**Score-based filtering** — Events and places are scored against the request (neighborhood, vibe, interests, group, budget, energy) rather than hard-filtered, ensuring results even with sparse matches.

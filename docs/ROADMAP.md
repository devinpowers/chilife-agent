# Roadmap

---

## Phase 1 — Local MVP (Complete)
**Goal:** Prove the concept works end-to-end on a laptop.

- Core agent loop (observe → gather → reason → generate → save)
- Mock data for 8 Chicago neighborhoods
- Rule-based plan engine (no API key required)
- Optional LLM via OpenAI-compatible client
- SQLite persistence: preferences, plan history, feedback
- Streamlit UI with all input controls and feedback buttons

**Architecture:** Single Python process, SQLite on disk, JSON mock data

---

## Phase 2 — Containerize + Cloud-Ready Code (Now)
**Goal:** Make the app deployable to Azure without changing business logic.

- [x] `Dockerfile` — multi-stage build, no secrets baked in
- [x] `docker-compose.yml` — mirrors Azure Container Apps locally
- [x] `DATABASE_URL` env var — SQLite default, PostgreSQL via `postgresql://` URL
- [x] PostgreSQL support in `db/database.py` (psycopg2, same SQL)
- [x] `.github/workflows/deploy.yml` — build → ACR → Container Apps CI/CD
- [x] `infra/` Bicep modules — Container Apps, PostgreSQL, Key Vault, ACR
- [ ] Provision Azure resources (`az deployment group create`)
- [ ] Push first image to Azure Container Registry
- [ ] Deploy to Azure Container Apps (staging slot)
- [ ] Rotate secrets into Azure Key Vault with Managed Identity

**Architecture:** Docker container on Azure Container Apps, PostgreSQL, Key Vault

---

## Phase 3 — Real Data
**Goal:** Replace mock JSON with live Chicago event and venue data.

- Azure Functions nightly refresh jobs
  - Ticketmaster API for live events
  - Yelp Fusion API for venue data
  - OpenWeatherMap for real Chicago weather
- Azure Service Bus queue for async event ingestion
- Events and places stored in PostgreSQL (replacing JSON files)
- Repository pattern swap: `MockEventsRepo` → `PostgresEventsRepo` (zero agent code changes)
- Expand to 20+ Chicago neighborhoods

**New Azure Services:** Azure Functions, Service Bus, Blob Storage (event data cache)

**Design pattern:** Event-driven data enrichment — app never calls external APIs directly

---

## Phase 4 — Personalization + Auth
**Goal:** Multi-user support with richer memory.

- Microsoft Entra External ID for user authentication (Google/Apple sign-in)
- Per-user preference profiles with richer signals:
  - Cuisine preferences, music genres, sports teams
  - Time-of-day patterns (early bird vs. night owl)
  - Neighborhood range (how far will you actually go?)
- Browseable plan history
- "More like this" / "Never show this again" feedback
- A/B test LLM prompts by plan satisfaction score
- Azure Cache for Redis — cache plans per user per request fingerprint

**New Azure Services:** Entra External ID, Redis Cache

---

## Phase 5 — Conversational Agent
**Goal:** Move from form-driven to chat-driven interaction.

- Add a chat input alongside (or replacing) the sidebar form
- Multi-turn conversation: "Make it more budget-friendly" / "Swap the music for jazz"
- Agent maintains conversation state in Redis
- LLM uses chat history as additional context
- Integrate Azure AI Foundry for prompt management and evaluation
- Optional: voice input via Azure Speech Services

**Design pattern:** Stateful agent with conversation memory

---

## Phase 6 — Polish + Scale
**Goal:** Production-grade reliability and UX.

- Azure Front Door: global load balancing, WAF, DDoS protection
- Map view showing plan route (Azure Maps)
- Transit time estimates between itinerary stops
- Reservation links (OpenTable / Resy integration)
- Ticket purchase links (Ticketmaster deep links)
- Weather-based push notifications: "Rain tonight — here are indoor alternatives"
- Blue/green deployments with Container Apps traffic splitting
- Application Insights dashboards: plan quality, feedback rates, LLM latency

---

## Phase 7 — Social + Platform
**Goal:** Network effects and ecosystem.

- Share a plan via link (public, no auth required)
- Group voting: share 3 plans with friends, vote on one
- Friend recommendations ("Alex went here last week")
- Anonymous crowd intel: busy tonight, typical wait times
- iOS / Android app (React Native or Flutter)
- Slack / iMessage integration ("Hey ChiLife, what should I do tonight?")
- Public API for third-party integrations
- Multi-city expansion: NYC, LA, Austin, Seattle

---

## Azure Migration Checklist

| Task | Phase | Pattern |
|------|-------|---------|
| Add `src/config.py` | 2 | 12-Factor |
| Add `Dockerfile` | 2 | 12-Factor |
| Deploy to Container Apps | 2 | Strangler Fig |
| Move secrets to Key Vault | 2 | Managed Identity |
| Swap SQLite → PostgreSQL | 2 | Repository Pattern |
| Add nightly Azure Functions | 3 | Event-Driven |
| Add Service Bus queue | 3 | Event-Driven |
| Swap mock data → live APIs | 3 | Repository Pattern |
| Add Redis caching | 4 | Cache-Aside |
| Add Entra auth | 4 | Zero-Trust |
| Add chat input | 5 | Stateful Agent |
| Add Front Door + WAF | 6 | Defense in Depth |
| Blue/green deployments | 6 | Zero-Downtime Deploy |

See `docs/AZURE_ARCHITECTURE.md` for the full system diagram and service mapping.

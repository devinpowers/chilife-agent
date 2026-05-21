# Azure Architecture — ChiLife Agent

This document describes the target cloud architecture for ChiLife Agent on Azure,
the design patterns it applies, and the step-by-step migration path from the local MVP.

---

## Target Architecture Overview

```mermaid
graph TB
    subgraph Internet["Internet / Clients"]
        USER[Browser]
        MOBILE[Mobile App<br/>future]
    end

    subgraph FrontDoor["Azure Front Door + CDN"]
        AFD[Azure Front Door<br/>Global load balancing<br/>WAF + DDoS protection]
    end

    subgraph ContainerApps["Azure Container Apps Environment"]
        APP[chilife-app<br/>Streamlit UI<br/>Container App]
        AGENT[chilife-agent<br/>LifestyleAgent API<br/>Container App]
    end

    subgraph AI["Azure AI"]
        AOAI[Azure OpenAI Service<br/>GPT-4o deployment]
    end

    subgraph Data["Data Layer"]
        PG[Azure Database for PostgreSQL<br/>Flexible Server<br/>user_preferences · plan_history · feedback]
        REDIS[Azure Cache for Redis<br/>Plan result caching<br/>Session state]
        BLOB[Azure Blob Storage<br/>Mock / real event data<br/>Export artifacts]
    end

    subgraph Integration["Integration Layer"]
        SB[Azure Service Bus<br/>Async event ingestion<br/>Queue: enrich-events]
        FUNC[Azure Functions<br/>Nightly data refresh<br/>Ticketmaster · Yelp · Weather]
    end

    subgraph External["External APIs"]
        TM[Ticketmaster API]
        YELP[Yelp Fusion API]
        OWM[OpenWeatherMap API]
    end

    subgraph DevOps["DevOps"]
        GH[GitHub Actions<br/>CI/CD pipeline]
        ACR[Azure Container Registry<br/>Image store]
    end

    subgraph Security["Security & Config"]
        KV[Azure Key Vault<br/>All secrets]
        MI[Managed Identity<br/>No passwords in code]
        ENTRA[Microsoft Entra<br/>External ID<br/>User auth - future]
    end

    subgraph Observability["Observability"]
        AI_MON[Application Insights<br/>Traces · metrics · logs]
        MON[Azure Monitor<br/>Alerts · dashboards]
    end

    USER --> AFD
    MOBILE --> AFD
    AFD --> APP
    APP --> AGENT
    AGENT --> AOAI
    AGENT --> PG
    AGENT --> REDIS
    AGENT --> BLOB
    AGENT --> SB
    SB --> FUNC
    FUNC --> TM
    FUNC --> YELP
    FUNC --> OWM
    FUNC --> PG

    GH --> ACR
    ACR --> APP
    ACR --> AGENT

    MI --> KV
    APP --> MI
    AGENT --> MI
    FUNC --> MI

    APP --> AI_MON
    AGENT --> AI_MON
    AI_MON --> MON
```

---

## Azure Services Mapping

| MVP Component | Azure Service | Why |
|---------------|--------------|-----|
| `streamlit run app.py` | Azure Container Apps | Serverless containers, auto-scale to zero, no VM management |
| SQLite file | Azure Database for PostgreSQL Flexible Server | Managed, HA, backups, connection pooling via PgBouncer |
| In-memory session state | Azure Cache for Redis | Shared state across container replicas |
| `mock_events.json` | Azure Blob Storage | Scalable, versioned, replicated data files |
| OpenAI client | Azure OpenAI Service | Data residency, private networking, no public internet for AI calls |
| `.env` file | Azure Key Vault + Managed Identity | Zero-secret-in-code, automatic rotation |
| `print()` logs | Azure Application Insights | Distributed tracing, query logs, set alerts |
| Manual data updates | Azure Functions + Service Bus | Scheduled nightly data refresh from real APIs |
| GitHub | GitHub Actions + Azure Container Registry | Full CI/CD pipeline |

---

## Design Patterns Applied

### 1. 12-Factor App

The most important pattern for cloud readiness. All 12 factors are addressed:

| Factor | How ChiLife Agent handles it |
|--------|------------------------------|
| Codebase | Single repo, one app |
| Dependencies | `requirements.txt`, Docker image |
| **Config** | `src/config.py` reads all settings from env vars — no hardcoded values |
| Backing services | DB, Redis, Blob treated as attached resources via URL in env |
| Build/release/run | GitHub Actions builds image → ACR → Container Apps deploys |
| Processes | Stateless containers — session state in Redis, data in PostgreSQL |
| Port binding | Streamlit binds to `$PORT` / 8501 |
| Concurrency | Scale out via Container Apps replicas |
| Disposability | Fast startup, graceful shutdown |
| Dev/prod parity | Same Docker image in local, staging, prod |
| Logs | Write to stdout → Application Insights collector |
| Admin processes | DB migrations as one-off container jobs |

### 2. Repository Pattern

The current service layer (`events_service.py`, `places_service.py`, `memory_service.py`)
already acts as a repository — it hides the data source from the agent.

```mermaid
graph LR
    A[LifestyleAgent] --> B[EventsService interface]
    B --> C1[MockEventsRepo\nJSON files — MVP]
    B --> C2[PostgresEventsRepo\nAzure DB — Phase 2]
    B --> C3[TicketmasterRepo\nLive API — Phase 3]
```

**Migration path:** Add a `EVENTS_BACKEND=mock|postgres|ticketmaster` env var.
The service checks config and returns the right implementation. Agent code changes **zero lines**.

### 3. Strangler Fig Pattern

Never rewrite everything at once. Strangle the old system piece by piece.

```mermaid
timeline
    title Strangler Fig Migration Timeline
    Phase 1 MVP : Local SQLite
              : JSON mock data
              : Rule-based engine
    Phase 2 Containerize : Docker image
                         : SQLite → PostgreSQL
                         : Deploy to Container Apps
    Phase 3 Real Data : Mock JSON → Blob Storage
                      : Add Azure Functions nightly refresh
                      : Ticketmaster + Yelp APIs
    Phase 4 AI upgrade : OpenAI API → Azure OpenAI
                       : Add Redis cache for plan results
    Phase 5 Auth : Add Entra External ID
                 : Multi-user preferences
    Phase 6 Scale : Front Door + WAF
                  : Read replicas
                  : Mobile app
```

At every phase, the existing functionality continues working — nothing is torn out all at once.

### 4. Circuit Breaker Pattern

Already implemented in `lifestyle_agent.py`. The agent always has a fallback:

```mermaid
stateDiagram-v2
    [*] --> TryLLM: request arrives
    TryLLM --> LLMSuccess: API responds OK
    TryLLM --> LLMFailed: timeout / error / bad JSON
    LLMFailed --> RuleBasedFallback: circuit opens
    RuleBasedFallback --> ReturnPlans: always succeeds
    LLMSuccess --> ReturnPlans
    ReturnPlans --> [*]
```

On Azure, extend this to also handle PostgreSQL failures (fall back to Redis cache),
and Redis failures (fall back to in-memory).

### 5. Managed Identity (Zero-Trust Secrets)

Never store connection strings or API keys in environment variables directly in Azure.
Instead, use Managed Identity to pull secrets from Key Vault at runtime.

```mermaid
sequenceDiagram
    participant App as Container App
    participant MI as Managed Identity
    participant KV as Key Vault
    participant DB as PostgreSQL

    App->>MI: "I need the DB connection string"
    MI->>KV: Token-authenticated request
    KV-->>MI: Secret value
    MI-->>App: Connection string
    App->>DB: Connect (no secret ever in code/env)
```

In code, `config.py` reads `DATABASE_URL` from env. In Azure Container Apps,
that env var is a **Key Vault reference** (`@Microsoft.KeyVault(SecretUri=...)`),
not the actual value. The platform resolves it automatically.

### 6. Event-Driven Data Enrichment

Real event data arrives asynchronously via Azure Service Bus so the app
is never blocked waiting for external API calls:

```mermaid
graph LR
    TIMER[Timer Trigger\nnightly 2am] --> FUNC[Azure Function\nFetchEvents]
    FUNC --> TM[Ticketmaster API]
    FUNC --> YELP[Yelp Fusion API]
    FUNC --> OWM[OpenWeatherMap]
    FUNC --> SB[Service Bus\nenrich-events queue]
    SB --> PROC[Azure Function\nProcessEvents]
    PROC --> PG[PostgreSQL\nevents table]
    PROC --> BLOB[Blob Storage\nevents cache]
    APP[ChiLife Agent App] --> PG
```

The app reads from PostgreSQL — it never calls external APIs directly.
This keeps response times fast and isolates external API failures.

---

## CI/CD Pipeline

```mermaid
graph LR
    DEV[Developer\ngit push] --> GH[GitHub Actions]
    GH --> TEST[Run tests\npytest]
    TEST --> BUILD[docker build]
    BUILD --> SCAN[Container scan\nMicrosoft Defender]
    SCAN --> ACR[Push to\nAzure Container Registry]
    ACR --> STAGING[Deploy to\nStaging Container App]
    STAGING --> SMOKE[Smoke tests]
    SMOKE --> PROD[Deploy to\nProduction Container App\nblue/green traffic split]
```

**Blue/Green on Container Apps:** Traffic is split — 10% to new revision,
90% to old. If error rate is low, shift to 100% new. One-click rollback.

---

## Infrastructure as Code

All Azure resources should be defined in code, not clicked through the portal.
Two options:

| Tool | When to use |
|------|------------|
| **Bicep** | Azure-native, no state file, great for greenfield Azure projects |
| **Terraform** | Multi-cloud, large teams, existing Terraform expertise |

Recommended file structure:
```
infra/
  main.bicep               # Resource group, shared resources
  modules/
    container-apps.bicep   # App + Agent container apps
    database.bicep         # PostgreSQL flexible server
    redis.bicep            # Azure Cache for Redis
    keyvault.bicep         # Key Vault + access policies
    openai.bicep           # Azure OpenAI deployment
    monitoring.bicep       # Application Insights + Log Analytics
```

---

## Cost Estimate (MVP Cloud)

| Service | SKU | Est. Monthly |
|---------|-----|-------------|
| Container Apps (app + agent) | Consumption plan | $10–30 |
| PostgreSQL Flexible Server | Burstable B1ms | $15 |
| Azure Cache for Redis | C0 Basic | $16 |
| Azure OpenAI | Pay-per-token (gpt-4o-mini) | $5–20 |
| Container Registry | Basic | $5 |
| Key Vault | Standard | $1 |
| Application Insights | Pay-per-GB | $2–5 |
| **Total estimate** | | **~$54–92/month** |

Scales to ~$0 during idle periods with Container Apps consumption plan (scale-to-zero).

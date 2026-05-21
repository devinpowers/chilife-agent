# API Options

ChiLife Agent uses an OpenAI-compatible client, meaning it works with any provider that implements the `/v1/chat/completions` endpoint.

## Configuration

Set these in your `.env` file:

```
OPENAI_API_KEY=<your key>
OPENAI_BASE_URL=<optional, for non-OpenAI providers>
OPENAI_MODEL=<optional, default: gpt-4o-mini>
```

## Supported Providers

### OpenAI (default)
```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini   # or gpt-4o for higher quality
```

### Anthropic Claude (via proxy)
Anthropic's API is not OpenAI-compatible natively, but you can use a proxy like `litellm`:
```bash
pip install litellm
litellm --model claude-3-5-haiku-20241022 --port 8000
```
```
OPENAI_BASE_URL=http://localhost:8000
OPENAI_API_KEY=<your-anthropic-key>
OPENAI_MODEL=claude-3-5-haiku-20241022
```

### Groq (fast inference)
```
OPENAI_API_KEY=gsk_...
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL=llama-3.1-70b-versatile
```

### Together AI
```
OPENAI_API_KEY=<together-key>
OPENAI_BASE_URL=https://api.together.xyz/v1
OPENAI_MODEL=meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo
```

### Ollama (fully local, no cost)
```bash
ollama pull llama3.1
ollama serve
```
```
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=ollama
OPENAI_MODEL=llama3.1
```

## No API Key — Rule-Based Mode

If `OPENAI_API_KEY` is not set, the app automatically uses the built-in rule-based plan generator. Plans are deterministic and based on the scoring model — no external dependency required.

This is the recommended starting point for local development.

## Model Recommendations

| Use Case | Recommended Model |
|----------|------------------|
| Development / testing | Rule-based (free) or `gpt-4o-mini` |
| Best quality plans | `gpt-4o` |
| Fastest response | Groq `llama-3.1-70b-versatile` |
| Fully offline | Ollama `llama3.1` |
| Cost-sensitive production | `gpt-4o-mini` |

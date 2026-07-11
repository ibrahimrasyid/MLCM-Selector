---
title: MLCheM Selector Backend
emoji: 🧪
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# MLCheM Selector — Unified Backend

Single Python service that powers the CC Tool Evaluation System:

- **Engine 1 (ML):** TF-IDF + Complement Naive Bayes → COSMO-RS / DFT / MD
- **Engine 2 (AI):** Groq (`openai/gpt-oss-120b`) scientific validation

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/`             | Health check + config |
| POST | `/predict-best` | ML-only prediction |
| POST | `/evaluate`     | ML + AI + comparison (used by the frontend) |

Request body for `/evaluate`:

```json
{ "property": "...", "subProperty": "...", "applicationDomain": "...", "systemType": "..." }
```

## Configuration (Space → Settings → Variables and secrets)

| Name | Type | Required | Notes |
|------|------|----------|-------|
| `GROQ_API_KEY` | Secret | Yes (for AI) | From console.groq.com |
| `GROQ_MODEL`   | Variable | No | Defaults to `openai/gpt-oss-120b` |

Without `GROQ_API_KEY` the ML engine still works; the AI panel shows "unavailable".

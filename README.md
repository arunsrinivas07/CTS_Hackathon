# ClaimGuard: Agentic AI Healthcare Claims Fraud Investigator

ClaimGuard is a highly autonomous Agentic AI system that investigates healthcare claims for potential fraud, waste, and abuse. Using an iterative ReAct orchestrator loop, RAG integration, and a sophisticated tool suite, ClaimGuard autonomously gathers evidence, structures hypotheses, questions policy using Medicare knowledge bases, and drafts conclusive investigation reports.

## Features

- **Agentic Orchestrator**: ReAct iterative loop generating questions, calling tools, and updating hypotheses.
- **RAG Integration**: CMS Medicare documents loaded into a semantic vector store.
- **Tools Engine**: Provider statistics, peer comparison, historical claims, and evidence retrieval.
- **ML Grounding**: Validates SHAP values and anomaly scores using actual policy documents.
- **Critic / Sufficiency**: Built-in self-correction loop to review conclusions against gathered evidence.
- **Professional Reports**: Outputs a highly structured 17-point professional business report.

## Quick Start

1. Define `.env` based on `.env.example`.
2. Ensure Groq API Key is configured.
3. Start the application:
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn main:app
   ```
4. Start an investigation (Terminal output will format the execution):
   ```bash
   curl -X POST http://localhost:8000/api/investigations/start \
     -H "Content-Type: application/json" \
     -d '{
       "claim_id": "CLM-HIGH-003",
       "risk_score": 0.98,
       "risk_level": "CRITICAL",
       "auto_run": true,
       "claim_data": {}
     }'
   ```

## Documentation

See `DEPLOYMENT.md` for production Docker containerization and setup instructions.

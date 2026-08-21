# Main Investigation Agent (Member 1)

This is the orchestrator that picks up a claim once it reaches the
investigator queue (output of the existing deterministic ML/rules/priority
pipeline) and runs the agentic investigation loop through to a final report.

## What's here

```
backend/
├── agent/
│   ├── orchestrator.py       # the loop: start -> iterate -> finalize
│   ├── state.py               # InvestigationState init + helpers
│   ├── question_generator.py  # ONE highest-value question per iteration
│   ├── tool_router.py         # validates/resolves tool against registry
│   ├── tool_executor.py       # executes tool, records call, lifts evidence
│   ├── evidence_evaluator.py  # explicit sufficiency criteria
│   ├── counter_analysis.py    # challenges the hypothesis before reporting
│   ├── critic.py               # grounding/fraud-language/citation checks
│   └── report_generator.py    # draft conclusion + final structured report
├── tools/                     # MOCK Member-2 tools behind a fixed contract
│   ├── base.py                 # BaseTool + controlled TOOL_REGISTRY
│   ├── rag_tool.py
│   ├── ml_tool.py
│   ├── ml_scenario_tool.py
│   ├── provider_db_tool.py    # statistics / history / peer comparison
│   └── claim_db_tool.py
├── schemas/                   # all typed, serializable Pydantic models
│   ├── investigation.py        # InvestigationState (the memory)
│   ├── question.py
│   ├── evidence.py
│   └── tool.py                 # Member-2 interface contracts
├── llm/client.py               # single choke point for all LLM calls
├── api/
│   ├── investigation_routes.py
│   └── store.py                # in-memory store (swap for real DB)
├── main.py                     # FastAPI app
└── tests/                      # 22 tests, see below
```

## Running it

```bash
pip install -r requirements.txt  
uvicorn main:app --reload
```

API (see spec section 25):
- `POST /api/investigations/start` — initialize state, derive objectives from claim/risk data. Pass `"auto_run": true` to run the whole loop synchronously in one call.
- `GET /api/investigations/{id}` — fetch current state (for frontend/Copilot).
- `POST /api/investigations/{id}/step` — run exactly one loop step (question→tool→observe→evaluate, or one finalize pass).
- `POST /api/investigations/{id}/run` — run to a terminal state.

## Tests

```bash
python3 -m pytest tests/ -v
```

22 tests, all offline (no API key needed) via `ScriptedLLMClient`,  Covers:
normal investigation to completion, max-iterations handling, critic
FAIL→revision→PASS, critic exhausting max revisions → human review,
evidence-evaluator escalation, duplicate-question dedup, invalid/missing
tool handling, tool failure vs. no-evidence-found distinction, and more
(see section 33 of the spec — not every scenario has its own test, but the
underlying logic paths are all covered).

## How Member 2's real tools plug in

Nothing in `agent/*` talks to RAG/ML/DB directly. It only calls
`tools.base.TOOL_REGISTRY[name].run(**kwargs)`, where `run()` returns the
generic `ToolOutput` envelope (`schemas/tool.py`). To integrate real tools:

1. Implement `run()` in a new class (or edit the existing mock classes) to
   call Member 2's actual RAG/ML/DB service, normalizing its response into
   `ToolOutput(status=..., data=..., evidence=[...], citations=[...])`.
2. Register it in `tools/__init__.py` in place of the mock.
3. Nothing else changes — orchestrator, question generator, evidence
   evaluator, counter-analysis, critic, and the API are all tool-agnostic.

## How Member 3's Copilot plugs in

`GET /api/investigations/{id}` returns the full `InvestigationState`:
evidence (with citations), tool call history, observations, questions
asked, counter-evidence, alternative explanations, evidence gaps, critic
result, and (once done) the final report. That's the structured surface
Member 3's Copilot should query against — no separate integration needed.

## Key design choices (and why)

- **No new orchestration framework.** No existing repo was provided to
  inspect, and the loop (question → tool → observe → evaluate → repeat,
  then counter-analysis → critic → report) is a small, fully-explicit
  state machine. Adding LangGraph/LangChain here would add a dependency
  and an abstraction layer without buying anything — every transition is
  already simple Python control flow driven by structured LLM JSON outputs.
  If your existing backend already standardizes on LangGraph, the loop
  in `orchestrator.py` maps 1:1 onto a LangGraph graph if you want to port it.
- **Tool safety.** The LLM only ever *names* a tool (a string). `tool_router.py`
  only accepts names present in `TOOL_REGISTRY`; `tool_executor.py`
  double-checks this again before calling anything. No arbitrary code/SQL
  execution is possible regardless of what the model outputs.
- **Fraud vs. risk language.** Enforced twice: the report-drafting prompt
  is instructed to only use calibrated language, and the critic prompt has
  a hard rule that asserting fraud was "committed"/"confirmed" is an
  automatic FAIL, forcing a revision.
- **Append-only state.** `InvestigationState` never deletes evidence,
  questions, or tool calls — only appends and marks gaps/objectives
  resolved. This satisfies "the agent must never lose previously collected
  evidence" and gives Member 3's Copilot a complete audit trail.
- **In-memory store.** `api/store.py` is a placeholder. Swap it for
  whatever DB layer your team already has — the routes only call
  `store.get`/`store.save`.

## Assumptions made (flag if wrong)

1. No existing repository was available to inspect, so this was built as a
   clean, standalone Member-1 component rather than integrated into an
   existing codebase — wire it into your actual backend's app/router setup
   when ready.
2. Claim data field names (`provider_id`, `procedure`, `diagnosis`,
   `patient_id`) in `tool_router.build_tool_input` are a guess at the
   contract with the upstream pipeline — align these with your actual
   claim schema.

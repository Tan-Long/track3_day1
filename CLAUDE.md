# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run benchmark (mock mode — uses mock_runtime.py, no LLM needed)
python run_benchmark.py --dataset data/hotpot_mini.json --out-dir outputs/sample_run

# Run benchmark with custom attempt count
python run_benchmark.py --dataset data/hotpot_mini.json --out-dir outputs/sample_run --reflexion-attempts 3

# Autograde a report
python autograde.py --report-path outputs/sample_run/report.json

# Run tests
python -m pytest tests/

# Run a single test
python -m pytest tests/test_utils.py::test_normalize_answer
```

## Architecture

This is a **Reflexion Agent** lab scaffold for the HotpotQA benchmark. It compares two agents — `ReActAgent` (single attempt) and `ReflexionAgent` (multi-attempt with self-reflection) — and produces a structured benchmark report.

### Agent loop (`src/reflexion_lab/agents.py`)

`BaseAgent.run()` is the core loop. For each attempt it calls three runtime functions:
1. `actor_answer(example, attempt_id, agent_type, reflection_memory)` → `(answer, tokens, latency_ms)`
2. `evaluator(example, answer)` → `(JudgeResult, tokens, latency_ms)`
3. `reflector(example, attempt_id, judge)` → `(ReflectionEntry, tokens, latency_ms)` — only called by `ReflexionAgent` on failure

The reflexion loop: on a failed attempt, `reflector()` is called, its `ReflectionEntry` is appended to `reflections`, and a summary string is appended to `reflection_memory` (a `list[str]`). That list is passed into the next `actor_answer()` call so the actor can learn from previous failures.

`ReActAgent` wraps `BaseAgent(agent_type="react", max_attempts=1)`. `ReflexionAgent` wraps `BaseAgent(agent_type="reflexion", max_attempts=3)`.

### Mock vs. real LLM

**Mock** (`src/reflexion_lab/mock_runtime.py`): hard-codes deterministic responses for QIDs `hp2, hp4, hp6, hp8`. All other QIDs return `gold_answer` immediately (always correct). Used in `run_benchmark.py` as the default import path.

**Real LLM** (`src/reflexion_lab/llm_runtime.py`): calls Ollama (`qwen2.5:3b` by default) via `ollama.chat()`. The `_chat()` helper handles token counting and latency. `evaluator` and `reflector` use `format="json"` and retry up to `MAX_RETRIES=3` times on parse failures.

To switch from mock to real LLM, change the import in `agents.py`:
```python
# mock
from .mock_runtime import FAILURE_MODE_BY_QID, actor_answer, evaluator, reflector
# real
from .llm_runtime import FAILURE_MODE_BY_QID, actor_answer, evaluator, reflector
```

### Prompts (`src/reflexion_lab/prompts.py`)

Three system prompts used by `llm_runtime.py`:
- `ACTOR_SYSTEM` — instructs the actor to output only the answer phrase
- `EVALUATOR_SYSTEM` — instructs the evaluator to return a JSON object with `score`, `reason`, `missing_evidence`, `spurious_claims`
- `REFLECTOR_SYSTEM` — instructs the reflector to return JSON with `attempt_id`, `failure_reason`, `lesson`, `next_strategy`

### Schemas (`src/reflexion_lab/schemas.py`)

All models use Pydantic v2. Key types:
- `QAExample` — input: `qid`, `difficulty`, `question`, `gold_answer`, `context: list[ContextChunk]`
- `JudgeResult` — evaluator output: `score` (0/1), `reason`, `missing_evidence`, `spurious_claims`
- `ReflectionEntry` — reflector output: `attempt_id`, `failure_reason`, `lesson`, `next_strategy`
- `AttemptTrace` — one attempt's result, optionally including a `ReflectionEntry`
- `RunRecord` — full result for one QA example: all traces, reflections, final score, `failure_mode`
- `ReportPayload` — top-level report with `meta`, `summary`, `failure_modes`, `examples`, `extensions`, `discussion`

### Report format (`src/reflexion_lab/reporting.py`)

`build_report(records, dataset_name, mode)` aggregates all `RunRecord`s into a `ReportPayload`. `save_report()` writes both `report.json` and `report.md` to the output directory.

The `extensions` list in `ReportPayload` declares implemented bonus features. Recognized values (each worth 10 pts, capped at 20): `structured_evaluator`, `reflection_memory`, `benchmark_report_json`, `mock_mode_for_autograding`, `adaptive_max_attempts`, `memory_compression`, `mini_lats_branching`, `plan_then_execute`.

### Grading (`autograde.py`)

Checks `report.json` against:
- **Schema (30 pts)**: all 6 top-level keys present (`meta`, `summary`, `failure_modes`, `examples`, `extensions`, `discussion`)
- **Experiment (30 pts)**: both agent types in summary (+10), `num_records ≥ 100` (+10), `≥ 20 examples` (+10)
- **Analysis (20 pts)**: `≥ 3 failure_mode keys` (+8), `discussion ≥ 250 chars` (+12)
- **Bonus (20 pts)**: 10 pts per recognized extension, capped at 20

### Data

`data/hotpot_mini.json` — small set of HotpotQA examples (list of `QAExample`-shaped dicts). `scripts/fetch_hotpot.py` can fetch a larger dataset. For grading, `num_records ≥ 100` is required (run both agents on ≥ 50 examples each).

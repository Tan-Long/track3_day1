# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run benchmark (mock mode)
python run_benchmark.py --dataset data/hotpot_mini.json --out-dir outputs/sample_run

# Run benchmark (custom attempts)
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

`BaseAgent.run()` is the core loop. For each attempt it calls three LLM-backed functions from `mock_runtime.py`:
1. `actor_answer(example, attempt_id, agent_type, reflection_memory)` — generates an answer
2. `evaluator(example, answer)` → `JudgeResult` — scores the answer 0/1
3. `reflector(example, attempt_id, judge)` → `ReflectionEntry` — produces a lesson + strategy

The **student's main task** is in `agents.py`: after a failed attempt and when `agent_type == "reflexion"`, call `reflector()`, append the result to `reflection_memory`, and pass it into the next `actor_answer()` call. The `# TODO` comment marks the exact location.

### Mock vs. real LLM

`mock_runtime.py` hard-codes deterministic responses for a small set of QIDs. Students replace this by calling a real LLM (Ollama, OpenAI, Gemini, etc.) and updating:
- `actor_answer` — real LLM call using `prompts.ACTOR_SYSTEM`
- `evaluator` — real LLM call using `prompts.EVALUATOR_SYSTEM`, must return `JudgeResult`
- `reflector` — real LLM call using `prompts.REFLECTOR_SYSTEM`, must return `ReflectionEntry`
- Token counts and latency in `agents.py` (currently hardcoded estimates)

### Report format (`src/reflexion_lab/reporting.py`, `src/reflexion_lab/schemas.py`)

`build_report()` produces a `ReportPayload` with these required top-level keys (checked by `autograde.py`): `meta`, `summary`, `failure_modes`, `examples`, `extensions`, `discussion`. The `extensions` list is how bonus features are declared — recognized values: `structured_evaluator`, `reflection_memory`, `benchmark_report_json`, `mock_mode_for_autograding`, `adaptive_max_attempts`, `memory_compression`, `mini_lats_branching`, `plan_then_execute`.

### Schemas with TODOs (`src/reflexion_lab/schemas.py`)

`JudgeResult` and `ReflectionEntry` are intentionally left empty — students must add fields. `mock_runtime.py` already uses `score`, `reason`, `missing_evidence`, `spurious_claims` on `JudgeResult` and `attempt_id`, `failure_reason`, `lesson`, `next_strategy` on `ReflectionEntry`, so those are the expected field names.

### Grading criteria

- **80 pts (core)**: schema completeness (30), running both agents on ≥100 samples with ≥20 examples in report (30), ≥3 failure modes + discussion ≥250 chars (20)
- **20 pts (bonus)**: 10 pts per recognized extension, capped at 20

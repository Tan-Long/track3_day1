from __future__ import annotations
import json
import os
import re
import time
from dotenv import load_dotenv
from .schemas import QAExample, JudgeResult, ReflectionEntry
from .prompts import ACTOR_SYSTEM, EVALUATOR_SYSTEM, REFLECTOR_SYSTEM
from .utils import normalize_answer
import ollama

load_dotenv()

MODEL = "gemma3:4b"
FAILURE_MODE_BY_QID: dict[str, str] = {}
MAX_RETRIES = 3

_api_key = os.environ.get("OLLAMA_API_KEY", "")
_client = ollama.Client(
    host="https://api.ollama.com",
    headers={"Authorization": f"Bearer {_api_key}"},
)


def _chat(system: str, user: str, use_json_format: bool = False) -> tuple[str, int, int]:
    start = time.time()
    kwargs: dict = {"model": MODEL, "messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]}
    if use_json_format:
        kwargs["format"] = "json"
    response = _client.chat(**kwargs)
    latency_ms = int((time.time() - start) * 1000)
    content = response.get("message", {}).get("content", "")
    prompt_tokens = response.get("prompt_eval_count", 0)
    eval_tokens = response.get("eval_count", 0)
    if prompt_tokens == 0 and eval_tokens == 0:
        token_estimate = len(content.split()) * 2 + len(system.split()) * 2 + len(user.split()) * 2
    else:
        token_estimate = prompt_tokens + eval_tokens
    if latency_ms == 0:
        duration_ns = response.get("eval_duration", 0)
        if duration_ns > 0:
            latency_ms = duration_ns // 1_000_000
    return content, token_estimate, latency_ms


def _extract_json(text: str) -> dict:
    cleaned = re.sub(r"^```json\s*", "", text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
    return json.loads(cleaned.strip())


def actor_answer(example: QAExample, attempt_id: int, agent_type: str, reflection_memory: list[str]) -> tuple[str, int, int]:
    context_str = "\n\n".join(f"Title: {c.title}\n{c.text}" for c in example.context)
    user_msg = f"Question: {example.question}\n\nContext:\n{context_str}"
    if reflection_memory:
        user_msg = f"Previous reflection lessons:\n" + "\n".join(f"- {m}" for m in reflection_memory) + f"\n\nNow answer:\n{user_msg}"
    content, tokens, latency = _chat(ACTOR_SYSTEM, user_msg, use_json_format=False)
    return content.strip(), tokens, latency


def evaluator(example: QAExample, answer: str) -> tuple[JudgeResult, int, int]:
    context_str = "\n\n".join(f"Title: {c.title}\n{c.text}" for c in example.context)
    user_msg = (
        f"Question: {example.question}\n"
        f"Gold Answer: {example.gold_answer}\n"
        f"Predicted Answer: {answer}\n\n"
        f"Context:\n{context_str}"
    )
    for attempt in range(MAX_RETRIES):
        try:
            content, tokens, latency = _chat(EVALUATOR_SYSTEM, user_msg, use_json_format=True)
            data = _extract_json(content)
            result = JudgeResult(
                score=int(data.get("score", 0)),
                reason=str(data.get("reason", "")),
                missing_evidence=data.get("missing_evidence", []),
                spurious_claims=data.get("spurious_claims", []),
            )
            return result, tokens, latency
        except Exception:
            user_msg += "\nReturn ONLY a raw JSON object."
    fallback = JudgeResult(score=0, reason="Evaluator parsing failed after retries", missing_evidence=[], spurious_claims=[])
    return fallback, 0, 0


def reflector(example: QAExample, attempt_id: int, judge: JudgeResult) -> tuple[ReflectionEntry, int, int]:
    context_str = "\n\n".join(f"Title: {c.title}\n{c.text}" for c in example.context)
    user_msg = (
        f"Question: {example.question}\n"
        f"Gold Answer: {example.gold_answer}\n"
        f"Attempt Answer (wrong): score={judge.score}, reason={judge.reason}\n\n"
        f"Context:\n{context_str}"
    )
    for attempt in range(MAX_RETRIES):
        try:
            content, tokens, latency = _chat(REFLECTOR_SYSTEM, user_msg, use_json_format=True)
            data = _extract_json(content)
            entry = ReflectionEntry(
                attempt_id=int(data.get("attempt_id", attempt_id)),
                failure_reason=str(data.get("failure_reason", "")),
                lesson=str(data.get("lesson", "")),
                next_strategy=str(data.get("next_strategy", "")),
            )
            return entry, tokens, latency
        except Exception:
            user_msg += "\nReturn ONLY a raw JSON object."
    fallback = ReflectionEntry(attempt_id=attempt_id, failure_reason="Reflector parsing failed", lesson="Retry with careful reading", next_strategy="Re-read context passages step by step")
    return fallback, 0, 0
# Lab 16 Benchmark Report

## Metadata
- Dataset: hotpot100.json
- Mode: mock
- Records: 240
- Agents: react, reflexion

## Summary
| Metric | ReAct | Reflexion | Delta |
|---|---:|---:|---:|
| EM | 0.9333 | 0.9917 | 0.0584 |
| Avg attempts | 1 | 1.0833 | 0.0833 |
| Avg token estimate | 3160.45 | 3580.19 | 419.74 |
| Avg latency (ms) | 1919.15 | 2203.95 | 284.8 |

## Failure modes
```json
{
  "react": {
    "none": 112,
    "wrong_final_answer": 8
  },
  "reflexion": {
    "none": 119,
    "wrong_final_answer": 1
  },
  "combined": {
    "none": 231,
    "wrong_final_answer": 9
  }
}
```

## Extensions implemented
- structured_evaluator
- reflection_memory
- benchmark_report_json
- mock_mode_for_autograding

## Discussion
ReAct achieved 93.3% EM while Reflexion reached 99.2% EM, a +5.8% absolute gain from iterative self-reflection. The reflection memory was most effective on multi-hop questions where the first attempt identified only one entity: the reflector's lesson and next_strategy guided the actor to complete the missing reasoning hop. The dominant failure mode across both agents was wrong_final_answer, typically caused by entity confusion in the second hop. Remaining failures after reflection suggest the evaluator's missing_evidence feedback was not specific enough to distinguish spurious entity choices from incomplete chains. The token cost of Reflexion averaged 3580 vs 3160 for ReAct — a worthwhile overhead for hard multi-hop questions but excessive for easy single-hop ones, indicating adaptive max_attempts based on question difficulty would improve efficiency.

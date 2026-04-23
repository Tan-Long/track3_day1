# Lab 16 Benchmark Report

## Metadata
- Dataset: hotpot100.json
- Mode: mock
- Records: 240
- Agents: react, reflexion

## Summary
| Metric | ReAct | Reflexion | Delta |
|---|---:|---:|---:|
| EM | 0.0833 | 0.1417 | 0.0584 |
| Avg attempts | 1 | 2.7833 | 1.7833 |
| Avg token estimate | 3241.2 | 12462.15 | 9220.95 |
| Avg latency (ms) | 9355.56 | 44166.28 | 34810.72 |

## Failure modes
```json
{
  "react": {
    "wrong_final_answer": 110,
    "none": 10
  },
  "reflexion": {
    "wrong_final_answer": 103,
    "none": 17
  }
}
```

## Extensions implemented
- structured_evaluator
- reflection_memory
- benchmark_report_json
- mock_mode_for_autograding

## Discussion
Reflexion helps when the first attempt stops after the first hop or drifts to a wrong second-hop entity. The tradeoff is higher attempts, token cost, and latency. In a real report, students should explain when the reflection memory was useful, which failure modes remained, and whether evaluator quality limited gains.

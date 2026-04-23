from __future__ import annotations
import json
import random
from datasets import load_dataset

random.seed(42)
ds = load_dataset("hotpot_qa", "distractor", split="validation")
samples = random.sample(list(ds), 120)
out = []
for item in samples:
    context = []
    for title, sents in zip(item["context"]["title"], item["context"]["sentences"]):
        context.append({"title": title, "text": " ".join(sents)})
    out.append({
        "qid": item["id"],
        "difficulty": item.get("level", "medium"),
        "question": item["question"],
        "gold_answer": item["answer"],
        "context": context,
    })
with open("data/hotpot100.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(f"Saved {len(out)} examples to data/hotpot100.json")
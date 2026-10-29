import json
from pathlib import Path

from app.graph.gateway import CommerceExtraction, Explanation, IntentDecision
from app.graph.prompts import EXPLAIN_SYSTEM, EXTRACT_SYSTEM, INTENT_SYSTEM


def test_qlora_examples_match_stride_schemas() -> None:
    import sys

    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root))
    from training.build_dataset import examples

    splits = examples()
    assert len(splits["train"]) > len(splits["valid"]) > 0
    prompts = {INTENT_SYSTEM, EXTRACT_SYSTEM, EXPLAIN_SYSTEM}
    seen = set()
    for rows in splits.values():
        for row in rows:
            system = row["messages"][0]["content"]
            seen.add(system)
            payload = json.loads(row["messages"][2]["content"])
            if system == INTENT_SYSTEM:
                IntentDecision.model_validate(payload)
                assert payload["intent"] in {"search", "compare", "recommend", "plan"}
            elif system == EXTRACT_SYSTEM:
                CommerceExtraction.model_validate(payload)
            else:
                Explanation.model_validate(payload)
    assert seen == prompts

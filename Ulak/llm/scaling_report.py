"""Report the difference between Chinchilla pretraining scale and Ulak LoRA tuning."""

import json

from llm.common import ADAPTER


def main():
    metrics_path = ADAPTER / "training_metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    target = metrics["chinchilla_pretraining_target_tokens"]
    actual = metrics["processed_training_tokens"]
    report = {
        "base_parameters": metrics["base_parameters"],
        "chinchilla_assumption_tokens_per_parameter": 20,
        "from_scratch_pretraining_target_tokens": target,
        "ulak_lora_processed_tokens": actual,
        "target_to_lora_token_ratio": round(target / actual, 1),
        "interpretation": (
            "Chinchilla estimates compute-optimal pretraining from scratch. "
            "Ulak adapts an already pretrained model with LoRA, so the target is informational."
        ),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

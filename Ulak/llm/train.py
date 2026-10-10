"""Fine-tune a small local Qwen model with LoRA on sourced Turkish examples."""

import json
import random
from datetime import datetime, timezone

import torch
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer

from llm.common import ADAPTER, BASE_MODEL, SYSTEM_PROMPT, load_cards, user_message


SEED = 42
EPOCHS = 3
MAX_TOKENS = 512
GRADIENT_ACCUMULATION = 4
BASE_PARAMETERS = 1_543_714_304
CHINCHILLA_TOKENS_PER_PARAMETER = 20


def examples(cards, index):
    for card in cards:
        yield card["questions"][index], card


def encode(tokenizer, question, card):
    prompt = tokenizer.apply_chat_template(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message(question, [card])},
        ],
        tokenize=True,
        add_generation_prompt=True,
    ).input_ids
    answer = tokenizer(card["fact"] + tokenizer.eos_token, add_special_tokens=False).input_ids
    if len(prompt) + len(answer) > MAX_TOKENS:
        raise ValueError(f"Training example exceeds {MAX_TOKENS} tokens: {card['id']}")
    ids = prompt + answer
    labels = [-100] * len(prompt) + answer
    return {
        "input_ids": torch.tensor([ids], dtype=torch.long, device="cuda"),
        "attention_mask": torch.ones((1, len(ids)), dtype=torch.long, device="cuda"),
        "labels": torch.tensor([labels], dtype=torch.long, device="cuda"),
    }


@torch.no_grad()
def evaluate(model, encoded):
    model.eval()
    losses = [float(model(**sample).loss) for sample in encoded]
    return round(sum(losses) / len(losses), 4)


def main():
    if not torch.cuda.is_available():
        raise SystemExit("CUDA GPU bulunamadı; bu eğitim 8 GB GPU için ayarlandı.")
    if not (BASE_MODEL / "config.json").exists():
        raise SystemExit("Önce python -m llm.download_model çalıştırın.")

    random.seed(SEED)
    torch.manual_seed(SEED)
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, local_files_only=True)
    cards = load_cards()
    train = [encode(tokenizer, question, card) for index in (0, 1) for question, card in examples(cards, index)]
    held_out = [encode(tokenizer, question, card) for question, card in examples(cards, 2)]
    tokens_per_epoch = sum(sample["input_ids"].numel() for sample in train)
    supervised_tokens_per_epoch = sum((sample["labels"] != -100).sum().item() for sample in train)

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        dtype=torch.bfloat16,
        attn_implementation="eager",
        local_files_only=True,
    ).to("cuda")
    model.config.use_cache = False
    config = LoraConfig(
        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        target_modules=["q_proj", "v_proj"],
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, config)
    trainable_parameters = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.enable_input_require_grads()
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=1e-4)

    history = [{"epoch": 0, "held_out_loss": evaluate(model, held_out)}]
    print(f"CUDA: {torch.cuda.get_device_name(0)} | train={len(train)} | held_out={len(held_out)}", flush=True)
    print(f"Baseline held-out loss: {history[0]['held_out_loss']}", flush=True)

    for epoch in range(1, EPOCHS + 1):
        model.train()
        random.shuffle(train)
        optimizer.zero_grad(set_to_none=True)
        for step, sample in enumerate(train, start=1):
            loss = model(**sample).loss / GRADIENT_ACCUMULATION
            loss.backward()
            if step % GRADIENT_ACCUMULATION == 0 or step == len(train):
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
        held_out_loss = evaluate(model, held_out)
        history.append({"epoch": epoch, "held_out_loss": held_out_loss})
        print(f"Epoch {epoch}/{EPOCHS}: held-out loss={held_out_loss}", flush=True)

    ADAPTER.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(ADAPTER)
    tokenizer.save_pretrained(ADAPTER)
    metrics = {
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_model": "Qwen/Qwen2.5-1.5B-Instruct",
        "training_examples": len(train),
        "held_out_questions": len(held_out),
        "base_parameters": BASE_PARAMETERS,
        "lora_trainable_parameters": trainable_parameters,
        "epochs": EPOCHS,
        "tokens_per_epoch": tokens_per_epoch,
        "processed_training_tokens": tokens_per_epoch * EPOCHS,
        "supervised_answer_tokens": supervised_tokens_per_epoch * EPOCHS,
        "chinchilla_pretraining_target_tokens": BASE_PARAMETERS * CHINCHILLA_TOKENS_PER_PARAMETER,
        "scaling_note": "Chinchilla is a from-scratch pretraining compute rule, not a LoRA fine-tuning target.",
        "evaluation_note": "Held-out wording for the same source cards; not an independent expert benchmark.",
        "history": history,
    }
    (ADAPTER / "training_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Adapter kaydedildi: {ADAPTER}", flush=True)


if __name__ == "__main__":
    main()

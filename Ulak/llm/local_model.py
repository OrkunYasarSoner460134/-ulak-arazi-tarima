"""Offline inference with the locally fine-tuned LoRA adapter."""

from threading import Lock

from llm.common import ADAPTER, BASE_MODEL, SYSTEM_PROMPT, select_cards, user_message


_load_lock = Lock()
_generation_lock = Lock()
_model = None
_tokenizer = None


class ModelNotReady(RuntimeError):
    pass


def _load():
    global _model, _tokenizer
    if _model is not None:
        return _model, _tokenizer
    with _load_lock:
        if _model is not None:
            return _model, _tokenizer
        if not (ADAPTER / "adapter_config.json").exists() or not (BASE_MODEL / "config.json").exists():
            raise ModelNotReady("Yerel dil modeli henüz eğitilmedi veya model dosyaları bulunamadı.")
        try:
            import torch
            from peft import PeftModel
            from transformers import AutoModelForCausalLM, AutoTokenizer

            if not torch.cuda.is_available():
                raise ModelNotReady("Yerel dil modeli için CUDA destekli GPU bulunamadı.")
            tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, local_files_only=True)
            base = AutoModelForCausalLM.from_pretrained(
                BASE_MODEL, dtype=torch.bfloat16, attn_implementation="eager", local_files_only=True
            ).to("cuda")
            model = PeftModel.from_pretrained(base, ADAPTER, local_files_only=True)
            model.eval()
            _model, _tokenizer = model, tokenizer
        except ModelNotReady:
            raise
        except Exception as exc:
            raise ModelNotReady("Yerel dil modeli yüklenemedi; sunucu loglarını kontrol edin.") from exc
    return _model, _tokenizer


def generate_answer(question):
    question = question.strip()
    if not question:
        return {"cevap": "Lütfen bir soru yazın.", "kaynaklar": []}
    if len(question) > 1000:
        return {"cevap": "Soruyu 1000 karakterin altında tutun.", "kaynaklar": []}
    cards = select_cards(question)
    if not cards:
        return {
            "cevap": "Bu soru için doğrulanmış bilgi kartım yok. Zemin veya heyelan konusunda kesin karar vermem için saha verisi gerekir.",
            "kaynaklar": [],
        }

    model, tokenizer = _load()
    import torch

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message(question, cards)},
    ]
    inputs = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_tensors="pt").to("cuda").input_ids
    with _generation_lock, torch.inference_mode():
        output = model.generate(
            inputs,
            max_new_tokens=180,
            do_sample=False,
            repetition_penalty=1.05,
            pad_token_id=tokenizer.eos_token_id,
        )
    answer = tokenizer.decode(output[0, inputs.shape[1]:], skip_special_tokens=True).strip()
    if not answer:
        answer = "Bu konuda güvenilir bir yanıt üretemedim."
    return {
        "cevap": answer,
        "kaynaklar": [
            {"baslik": card["title"], "url": card["source"] if card["source"].startswith("https://") else None}
            for card in cards
        ],
    }

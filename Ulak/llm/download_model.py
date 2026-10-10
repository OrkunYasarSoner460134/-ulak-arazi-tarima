"""Download Apache-2.0 Qwen2.5-1.5B-Instruct weights for offline use."""

from huggingface_hub import snapshot_download

from llm.common import BASE_MODEL


if __name__ == "__main__":
    BASE_MODEL.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id="Qwen/Qwen2.5-1.5B-Instruct",
        local_dir=BASE_MODEL,
        allow_patterns=["*.json", "*.safetensors", "*.model", "*.txt", "*.jinja", "LICENSE", "README.md"],
    )
    print(f"Model indirildi: {BASE_MODEL}")
